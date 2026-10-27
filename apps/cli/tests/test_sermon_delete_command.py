import json
import os
import socket
from contextlib import closing
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from wordcut.db import connect, sermons, tasks
from wordcut.db.sermons import NewSermon
from wordcut.db.tasks import NewTask
from wordcut.home import Home
from wordcut_cli import main

NOW = datetime(2026, 10, 27, 9, 30, tzinfo=timezone.utc)


def stored_sermon(home: Path) -> int:
    with closing(connect(Home(home))) as connection, connection:
        sermon = sermons.insert(
            connection,
            NewSermon(
                youtube_id="Ab3_x-9QzLk",
                url="https://youtu.be/Ab3_x-9QzLk",
                title="Culto de domingo",
                service_date=date(2026, 10, 18),
                live_duration=7718.0,
                live_finished=True,
                created_at=NOW,
            ),
        )
    return sermon.id


def run_json(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, Any]:
    exit_code = main(argv)
    return exit_code, json.loads(capsys.readouterr().out)


def test_sermon_delete_with_json_prints_the_deleted_id_and_the_sermon_is_gone(
    wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    sermon_id = stored_sermon(wordcut_home)

    deleted = run_json(["sermon", "delete", str(sermon_id), "--json"], capsys)
    shown = run_json(["sermon", "show", str(sermon_id), "--json"], capsys)

    assert (deleted, shown[0], shown[1].get("error", {}).get("code")) == (
        (0, {"id": sermon_id, "deleted": True}),
        3,
        "not_found",
    )


def test_sermon_delete_of_a_sermon_that_does_not_exist_exits_3_with_not_found(
    wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code, printed = run_json(["sermon", "delete", "404", "--json"], capsys)

    assert (exit_code, printed["error"]["code"]) == (3, "not_found")


def test_sermon_delete_with_a_task_running_exits_4_with_busy_and_keeps_the_sermon(
    wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    sermon_id = stored_sermon(wordcut_home)
    with closing(connect(Home(wordcut_home))) as connection:
        new = NewTask("process", "sermon", sermon_id, {}, os.getpid(), socket.gethostname(), NOW)
        task = tasks.insert(connection, new)

    exit_code, printed = run_json(["sermon", "delete", str(sermon_id), "--json"], capsys)
    kept = run_json(["sermon", "show", str(sermon_id), "--json"], capsys)[0]

    assert (exit_code, printed["error"]["code"], printed["error"]["details"], kept) == (
        4,
        "busy",
        {"task_id": task.id, "kind": "process", "started_at": NOW.isoformat()},
        0,
    )


def test_sermon_delete_without_json_says_in_words_what_was_deleted(
    wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    sermon_id = stored_sermon(wordcut_home)

    exit_code = main(["sermon", "delete", str(sermon_id)])

    assert (exit_code, capsys.readouterr().out) == (
        0,
        f"Pregação {sermon_id} apagada, com seus cortes e arquivos.\n",
    )


def test_sermon_delete_help_says_it_is_for_the_administrator_with_an_example(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["sermon", "delete", "--help"])

    help_text = capsys.readouterr().out
    assert (exit_code, "administrador" in help_text, "wordcut sermon delete 12" in help_text) == (
        0,
        True,
        True,
    )
