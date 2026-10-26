"""Exporting a cut: the ``render`` task, its estimate and the exports it records
(docs/cli.md §8.7, §9)."""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from contextlib import closing
from datetime import datetime
from typing import Any

from wordcut.cuts.assembly import assemble
from wordcut.cuts.caption import stored_caption
from wordcut.db import connect, cuts, renders, transcripts, word_fixes
from wordcut.db.cuts import CutRow
from wordcut.db.tasks import TaskRow
from wordcut.errors import WordcutError
from wordcut.home import Home
from wordcut.rendering.estimate import estimated_duration
from wordcut.rendering.options import merged, validated
from wordcut.service.cuts import existing_cut, shown_render, update_caption
from wordcut.service.sermons import sermon_video
from wordcut.tasks import ProgressListener, Resource, execution


def start_render(
    home: Home,
    cut_id: int,
    changes: Mapping[str, Any],
    *,
    detach: bool,
    on_progress: ProgressListener | None = None,
) -> TaskRow:
    """Start the ``render`` task of the cut with the options ``changes`` changes, as
    ``tasks.execution.start`` does.

    ``changes`` may turn the caption on or off (``caption``), which changes the cut's caption
    style as ``cut caption --on/--off`` does; the other options are saved on the cut. Both are
    saved under the lock, once the task is admitted.
    """
    caption, options_changes = _split(changes)
    validated(options_changes)
    with closing(connect(home)) as connection:
        _exportable(connection, home, cut_id)

    def admit() -> None:
        with closing(connect(home)) as connection:
            row = _exportable(connection, home, cut_id)
            options = merged(row.render_options, options_changes)
            moment = _now()
            with connection:
                cuts.set_render_options(connection, cut_id, options.as_dict(), moment)
            if caption is not None:
                update_caption(connection, cut_id, {"enabled": caption}, moment)

    return execution.start(
        home,
        "render",
        Resource("cut", cut_id),
        {},
        detach=detach,
        on_progress=on_progress,
        admit=admit,
    )


def estimate_render(
    connection: sqlite3.Connection, cut_id: int, changes: Mapping[str, Any]
) -> dict[str, Any]:
    """How long the export with ``changes`` would last, and its options, without rendering,
    saving or taking the lock (FR-009)."""
    caption, options_changes = _split(changes)
    validated(options_changes)
    row = existing_cut(connection, cut_id)
    options = merged(row.render_options, options_changes)
    words = transcripts.words_of(connection, row.sermon_id)
    cut = assemble(row.segments, words, word_fixes.of_cut(connection, cut_id))
    shown = stored_caption(row.caption).enabled if caption is None else caption
    return {
        "duration": estimated_duration(cut, words, options),
        "options": options.summary(caption=shown),
    }


def show_render(connection: sqlite3.Connection, home: Home, render_id: int) -> dict[str, Any]:
    """The export ``render_id`` (docs/cli.md §9)."""
    row = renders.by_id(connection, render_id)
    if row is None:
        raise WordcutError(
            "not_found", f"Exportação {render_id} não existe.", {"render_id": render_id}
        )
    return shown_render(row, home)


def _exportable(connection: sqlite3.Connection, home: Home, cut_id: int) -> CutRow:
    """The cut, once it exists and its sermon is processed with its video in place."""
    row = existing_cut(connection, cut_id)
    sermon_video(connection, home, row.sermon_id)
    return row


def _split(changes: Mapping[str, Any]) -> tuple[bool | None, dict[str, Any]]:
    """The caption switch of ``changes``, if any, and the export options."""
    options = dict(changes)
    return options.pop("caption", None), options


def _now() -> datetime:
    return datetime.now().astimezone().replace(microsecond=0)
