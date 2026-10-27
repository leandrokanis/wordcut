"""The ``prepare`` task: the thumbnails and the waveform of a sermon's timeline (1.1.b.1).

No parameters. The task does not take the processing lock: it downloads only the live's
storyboards and lowest audio and uses no GPU (ADR-0025). The sermon's timeline is
``pending`` while it runs and ends ``ready`` or ``failed``; a failure keeps a generic
message, never the text of what failed, which may carry a path or the cookies' file.
"""

from __future__ import annotations

import shutil
from contextlib import closing
from datetime import datetime

from wordcut import timeline_media
from wordcut.db import connect, sermons
from wordcut.db import timeline_media as timelines
from wordcut.db.timeline_media import TimelineError
from wordcut.errors import WordcutError
from wordcut.home import Home
from wordcut.tasks import Result, TaskContext, TaskKind, register
from wordcut.youtube import YouTubeError

WORK_FOLDER = "timeline-work"
FAILED_MESSAGE = "Não foi possível preparar as miniaturas e a forma de onda da live; tente de novo."
INTERRUPTED = TimelineError("interrupted", "A preparação da timeline foi interrompida.")


def _run(ctx: TaskContext) -> Result:
    sermon_id = ctx.resource.id
    with closing(connect(ctx.home)) as connection:
        sermon = sermons.by_id(connection, sermon_id)
    assert sermon is not None, "prepare_sermon_timeline admits only an existing sermon"
    work = ctx.home.sermon_media(sermon_id) / WORK_FOLDER
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    try:
        made = timeline_media.prepare(
            timeline_media.default_gateways(), work, sermon.url, ctx.progress
        )
        timeline_media.store(made, ctx.home.sermon_timeline(sermon_id))
    except KeyboardInterrupt:
        _record(ctx.home, sermon_id, "failed", INTERRUPTED)
        raise
    except Exception as failure:
        error = TimelineError(_code(failure), FAILED_MESSAGE)
        _record(ctx.home, sermon_id, "failed", error)
        raise WordcutError(error.code, error.message, {"sermon_id": sermon_id}) from None
    finally:
        shutil.rmtree(work, ignore_errors=True)
    _record(ctx.home, sermon_id, "ready")
    return {"sermon_id": sermon_id, "status": "ready", "thumbnails": made.storyboard is not None}


def _code(failure: Exception) -> str:
    if isinstance(failure, WordcutError):
        return failure.code
    if isinstance(failure, YouTubeError):
        return "youtube_error"
    return "internal_error"


def _record(home: Home, sermon_id: int, status: str, error: TimelineError | None = None) -> None:
    with closing(connect(home)) as connection:
        timelines.record(connection, sermon_id, status, _now(), error)


def _now() -> datetime:
    return datetime.now().astimezone().replace(microsecond=0)


PREPARE = register(TaskKind(name="prepare", run=_run, needs_lock=False))
