"""The ``process`` task: download, transcribe and cut a trimmed sermon (docs/cli.md §7.4).

Parameters: ``force`` true to redo a processed sermon. The sermon is ``processing`` while
the task runs and ends ``processed`` or ``failed``. ``service.processing.start_processing``
checks, under the lock, that the sermon can be processed before the task is recorded. The
transcription uses the WhisperX model of the settings (``service.settings.whisper_model``).
"""

from __future__ import annotations

import os
import shutil
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

from wordcut import processing
from wordcut.db import connect, sermons, transcripts
from wordcut.db.sermons import SermonRow
from wordcut.processing import pipeline
from wordcut.processing.pipeline import Processed
from wordcut.service.sermons import processed_sermon
from wordcut.service.settings import whisper_model
from wordcut.tasks import Result, TaskContext, TaskKind, register

SAVING = (0.95, "gravando")
VIDEO_FILE = "sermon.mp4"
WORK_FOLDER = "work"


def _run(ctx: TaskContext) -> Result:
    sermon_id = ctx.resource.id
    force = bool(ctx.params.get("force"))
    with closing(connect(ctx.home)) as connection:
        sermon = sermons.by_id(connection, sermon_id)
        assert sermon is not None, "start_processing admits only an existing sermon"
        model = whisper_model(connection)
        with connection:
            if force:
                transcripts.delete_of(connection, sermon_id)
            sermons.set_status(connection, sermon_id, "processing", _now())
    try:
        return _processed(ctx, sermon, model)
    except BaseException:
        with closing(connect(ctx.home)) as connection, connection:
            sermons.set_status(connection, sermon_id, "failed", _now())
        raise


def _processed(ctx: TaskContext, sermon: SermonRow, transcription_model: str) -> Result:
    assert sermon.live_start is not None and sermon.live_end is not None
    media = ctx.home.sermon_media(sermon.id)
    work = _fresh_folder(media / WORK_FOLDER)
    made = pipeline.process(
        processing.default_gateways(transcription_model),
        work,
        sermon.url,
        sermon.live_start,
        sermon.live_end,
        ctx.progress,
        live_duration=sermon.live_duration,
    )
    ctx.progress(*SAVING)
    video = media / VIDEO_FILE
    os.replace(made.video, video)
    with closing(connect(ctx.home)) as connection:
        _store(connection, sermon.id, made, str(video.relative_to(ctx.home.root)))
        result = processed_sermon(connection, sermon.id)
    shutil.rmtree(work)
    return result


def _fresh_folder(folder: Path) -> Path:
    """``folder``, emptied of what an earlier processing left behind."""
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)
    return folder


def _store(connection: sqlite3.Connection, sermon_id: int, made: Processed, video: str) -> None:
    with connection:
        transcripts.replace(connection, sermon_id, made.words, made.sentences)
        sermons.record_processed(
            connection, sermon_id, made.sermon_start, made.sermon_end, video, _now()
        )


def _now() -> datetime:
    return datetime.now().astimezone().replace(microsecond=0)


PROCESS = register(TaskKind(name="process", run=_run))
