"""A new suggestion of cuts for a processed sermon: the ``suggest`` task (docs/cli.md §7.6)."""

from __future__ import annotations

import sqlite3
from contextlib import closing

from wordcut import suggestion
from wordcut.db import connect
from wordcut.db.tasks import TaskRow
from wordcut.errors import WordcutError
from wordcut.home import Home
from wordcut.service.presets import default_preset, show_preset
from wordcut.service.sermons import processed_row
from wordcut.service.tasks import running_task
from wordcut.tasks import ProgressListener, Resource, execution


def start_suggestion(
    home: Home,
    sermon_id: int,
    preset_id: int | None = None,
    *,
    detach: bool,
    on_progress: ProgressListener | None = None,
) -> TaskRow:
    """Start the ``suggest`` task of the sermon with ``preset_id``, or the default preset, as
    ``tasks.execution.start`` does.

    A sermon that does not exist or is not processed, a preset that does not exist, or an LLM
    without model or key is refused before any task is recorded, and so is a second suggestion
    of the sermon while one runs (``busy``). That check and the record are not atomic: two
    launches at the same instant may both pass (docs/cli.md §7.6).
    """
    with closing(connect(home)) as connection:
        processed_row(connection, sermon_id)
        preset = (
            default_preset(connection) if preset_id is None else show_preset(connection, preset_id)
        )
        # Checked here so that a missing setting leaves no failed task and no suggestion_error;
        # the task checks again, for settings changed after the launch.
        suggestion.require_configured(connection)

    def admit() -> None:
        with closing(connect(home)) as connection:
            _refuse_while_suggesting(home, connection, sermon_id)

    return execution.start(
        home,
        "suggest",
        Resource("sermon", sermon_id),
        {"preset_id": preset["id"]},
        detach=detach,
        on_progress=on_progress,
        admit=admit,
    )


def _refuse_while_suggesting(home: Home, connection: sqlite3.Connection, sermon_id: int) -> None:
    """``busy`` while another ``suggest`` task of the sermon runs, once orphans are failed."""
    running = running_task(home, connection, "sermon", sermon_id, "suggest")
    if running is not None:
        raise WordcutError(
            "busy",
            f"A pregação {sermon_id} já tem uma sugestão de cortes em andamento"
            f" (tarefa {running.id}).",
            {
                "task_id": running.id,
                "kind": running.kind,
                "started_at": running.started_at.isoformat(),
            },
        )
