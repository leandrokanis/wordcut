"""The files of the data folder that go with a sermon or a cut when its rows are deleted."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from wordcut.db import cuts, renders, sermons, tasks
from wordcut.files import remove_within
from wordcut.home import Home


def export_files(home: Home, connection: sqlite3.Connection, cut_id: int) -> list[Path]:
    """The cut's media folder and the files its exports name."""
    return [
        home.cut_media(cut_id),
        *(home.root / row.path for row in renders.of_cut(connection, cut_id)),
    ]


def cut_files(home: Home, connection: sqlite3.Connection, cut_id: int) -> list[Path]:
    """The export files of the cut and the logs of its tasks."""
    return [
        *export_files(home, connection, cut_id),
        *(home.task_log(task.id) for task in tasks.of_resource(connection, "cut", cut_id)),
    ]


def exports_by_cut(
    home: Home, connection: sqlite3.Connection, sermon_id: int
) -> dict[int, list[Path]]:
    """The export files of each cut of the sermon, by cut ID."""
    return {
        cut.id: export_files(home, connection, cut.id)
        for cut in cuts.of_sermon(connection, sermon_id)
    }


def remove_exports_of_gone_cuts(
    home: Home, connection: sqlite3.Connection, sermon_id: int, before: dict[int, list[Path]]
) -> None:
    """Remove the export files, as ``exports_by_cut`` gave them ``before``, of the cuts the
    sermon no longer has; call it once their delete is committed."""
    remaining = {cut.id for cut in cuts.of_sermon(connection, sermon_id)}
    remove_within(
        home.root,
        [path for cut_id, paths in before.items() if cut_id not in remaining for path in paths],
    )


def sermon_files(home: Home, connection: sqlite3.Connection, sermon_id: int) -> list[Path]:
    """The sermon's media folder, the video it names, the logs of its tasks and the files
    of each of its cuts."""
    row = sermons.by_id(connection, sermon_id)
    video = [] if row is None or row.video_path is None else [home.root / row.video_path]
    return [
        home.sermon_media(sermon_id),
        *video,
        *(home.task_log(task.id) for task in tasks.of_resource(connection, "sermon", sermon_id)),
        *(
            path
            for cut in cuts.of_sermon(connection, sermon_id)
            for path in cut_files(home, connection, cut.id)
        ),
    ]
