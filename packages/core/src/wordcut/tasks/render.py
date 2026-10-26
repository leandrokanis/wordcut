"""The ``render`` task: export a cut in 9:16 from its current state (docs/cli.md §8.7).

The task reads the cut when it runs: its segments, spelling fixes, caption style and the export
options ``service.rendering.start_render`` saved on it under the lock. The video is made in the
cut's media folder and moved to ``<render_id>.mp4`` in the transaction that records the export,
so a failed or interrupted export leaves neither a row nor a file (ADR-0018). The result is
``{"render_id": …}``.
"""

from __future__ import annotations

import os
import shutil
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import Any

from wordcut import rendering
from wordcut.cuts.assembly import assemble
from wordcut.cuts.caption import stored_caption
from wordcut.db import connect, cuts, renders, transcripts, word_fixes
from wordcut.db.renders import NewRender
from wordcut.home import Home
from wordcut.rendering import pipeline
from wordcut.rendering.options import merged
from wordcut.service.sermons import sermon_video
from wordcut.tasks import Result, TaskContext, TaskKind, register

SAVING = (0.99, "gravando")
STAGED_FILE = "rendering.mp4"
WORK_FOLDER = "work"


def _run(ctx: TaskContext) -> Result:
    cut_id = ctx.resource.id
    with closing(connect(ctx.home)) as connection:
        row = cuts.by_id(connection, cut_id)
        assert row is not None, "start_render admits only an existing cut"
        video = sermon_video(connection, ctx.home, row.sermon_id).path
        words = transcripts.words_of(connection, row.sermon_id)
        cut = assemble(row.segments, words, word_fixes.of_cut(connection, cut_id))
    caption = stored_caption(row.caption)
    options = merged(row.render_options, {})
    folder = ctx.home.cut_media(cut_id)
    folder.mkdir(parents=True, exist_ok=True)
    staged = folder / STAGED_FILE
    staged.unlink(missing_ok=True)
    work = folder / WORK_FOLDER
    shutil.rmtree(work, ignore_errors=True)
    try:
        duration = pipeline.render_cut(
            rendering.default_gateways(),
            video,
            words,
            cut,
            caption,
            options,
            work,
            staged,
            ctx.progress,
        )
        ctx.progress(*SAVING)
        summary = options.summary(caption=caption.enabled)
        return {"render_id": _recorded(ctx.home, cut_id, staged, duration, summary)}
    finally:
        staged.unlink(missing_ok=True)


def _recorded(
    home: Home, cut_id: int, staged: Path, duration: float, options: dict[str, Any]
) -> int:
    """Record the export and move ``staged`` to its file in the same transaction; a file
    whose row is not committed is removed."""
    moved: Path | None = None
    with closing(connect(home)) as connection:
        try:
            with connection:
                new = NewRender(cut_id, _relative(home, staged), duration, options, _now())
                render_id = renders.insert(connection, new)
                final = staged.with_name(f"{render_id}.mp4")
                renders.set_path(connection, render_id, _relative(home, final))
                os.replace(staged, final)
                moved = final
        except BaseException:
            if moved is not None:
                moved.unlink(missing_ok=True)
            raise
    return render_id


def _relative(home: Home, path: Path) -> str:
    return str(path.relative_to(home.root))


def _now() -> datetime:
    return datetime.now().astimezone().replace(microsecond=0)


RENDER = register(TaskKind(name="render", run=_run))
