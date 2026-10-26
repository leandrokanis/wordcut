import sqlite3
from contextlib import closing
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from wordcut.db import MIGRATIONS, connect, tasks
from wordcut.db.tasks import NewTask, TaskRow
from wordcut.home import Home

STARTED_AT = datetime(2026, 10, 26, 22, 40, tzinfo=timezone.utc)

TASK_COLUMNS = {
    "id",
    "kind",
    "resource_type",
    "resource_id",
    "params",
    "status",
    "progress",
    "progress_message",
    "pid",
    "host",
    "started_at",
    "finished_at",
    "error_code",
    "error_message",
    "error_details",
    "result",
}


def test_migration_creates_the_tasks_table_with_every_task_field(tmp_path: Path) -> None:
    with closing(connect(Home(tmp_path))) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(tasks)")}
        version = connection.execute("PRAGMA user_version").fetchone()[0]

    assert (columns, version >= 3) == (TASK_COLUMNS, True)


def test_database_in_schema_2_keeps_its_sermons_when_migrated(tmp_path: Path) -> None:
    home = Home(tmp_path)
    home.ensure()
    with closing(sqlite3.connect(home.database)) as old, old:
        for number in (1, 2):
            script = next(MIGRATIONS.glob(f"000{number}_*.sql")).read_text(encoding="utf-8")
            old.executescript(script)
        old.execute(
            "INSERT INTO sermons (youtube_id, url, title, service_date, live_finished,"
            " created_at, updated_at) VALUES ('Ab3_x-9QzLk', 'https://youtu.be/Ab3_x-9QzLk',"
            " 'Culto de domingo', '2026-10-18', 1, '2026-10-26T19:40:00-03:00',"
            " '2026-10-26T19:40:00-03:00')"
        )
        old.execute("PRAGMA user_version = 2")

    with closing(connect(home)) as connection:
        titles = connection.execute("SELECT title FROM sermons").fetchall()
        tasks = connection.execute("SELECT count(*) FROM tasks").fetchone()

    assert (titles, tasks) == ([("Culto de domingo",)], (0,))


NEW_TASK = NewTask(
    kind="process",
    resource_type="sermon",
    resource_id=12,
    params={"force": True},
    pid=4321,
    host="servidor",
    started_at=STARTED_AT,
)


def test_inserted_task_is_read_back_running_with_every_field(tmp_path: Path) -> None:
    new = NEW_TASK
    with closing(connect(Home(tmp_path))) as connection:
        inserted = tasks.insert(connection, new)
        found = tasks.by_id(connection, inserted.id)

    assert found == TaskRow(
        id=inserted.id,
        kind="process",
        resource_type="sermon",
        resource_id=12,
        params={"force": True},
        status="running",
        progress=0.0,
        progress_message=None,
        pid=4321,
        host="servidor",
        started_at=STARTED_AT,
        finished_at=None,
        error_code=None,
        error_message=None,
        error_details=None,
        result=None,
    )


def test_tasks_are_listed_newest_first_and_in_insertion_order_on_a_tie(tmp_path: Path) -> None:
    later = STARTED_AT + timedelta(minutes=5)
    with closing(connect(Home(tmp_path))) as connection:
        first = tasks.insert(connection, NEW_TASK)
        tied = tasks.insert(connection, replace(NEW_TASK, kind="render", resource_type="cut"))
        newest = tasks.insert(connection, replace(NEW_TASK, started_at=later))

        listed = [task.id for task in tasks.newest_first(connection)]

    assert listed == [newest.id, tied.id, first.id]


def test_tasks_are_listed_only_of_the_status_and_kind_asked_for(tmp_path: Path) -> None:
    with closing(connect(Home(tmp_path))) as connection:
        process = tasks.insert(connection, NEW_TASK)
        render = tasks.insert(connection, replace(NEW_TASK, kind="render", resource_type="cut"))
        tasks.finish_succeeded(connection, render.id, {}, STARTED_AT)
        tasks.insert(connection, replace(NEW_TASK, kind="render", resource_type="cut"))

        found = [
            [task.id for task in tasks.newest_first(connection, status="running", kind="process")],
            [task.id for task in tasks.newest_first(connection, status="succeeded")],
        ]

    assert found == [[process.id], [render.id]]
