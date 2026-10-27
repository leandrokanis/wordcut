import json
import os
import socket
from contextlib import closing
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from wordcut.db import connect, cuts, sermons, tasks, transcripts
from wordcut.db.cuts import NewCut, Segment
from wordcut.db.sermons import NewSermon
from wordcut.db.tasks import NewTask
from wordcut.home import Home
from wordcut.transcript import Word
from wordcut_cli import main

NOW = datetime(2026, 10, 27, 9, 30, tzinfo=timezone.utc)
SPOKEN = (Word("Graça", 0.3, 0.8), Word("e", 0.9, 1.0), Word("paz.", 1.1, 1.9))


def stored_cut(home: Path) -> int:
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
        transcripts.replace(connection, sermon.id, SPOKEN, ())
        first, _, last = [word.id for word in transcripts.words_of(connection, sermon.id)]
        new = NewCut("chosen", "Graça", (Segment(first, last),), first, last, "llm", None)
        [cut_id] = cuts.insert_many(connection, sermon.id, [new], NOW)
    return cut_id


def run_json(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, Any]:
    exit_code = main(argv)
    return exit_code, json.loads(capsys.readouterr().out)


def test_cut_delete_with_json_prints_the_deleted_id_and_the_cut_is_gone(
    wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cut_id = stored_cut(wordcut_home)

    deleted = run_json(["cut", "delete", str(cut_id), "--json"], capsys)
    shown = run_json(["cut", "show", str(cut_id), "--json"], capsys)

    assert (deleted, shown[0], shown[1].get("error", {}).get("code")) == (
        (0, {"id": cut_id, "deleted": True}),
        3,
        "not_found",
    )


def test_cut_delete_of_a_cut_that_does_not_exist_exits_3_with_not_found(
    wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code, printed = run_json(["cut", "delete", "404", "--json"], capsys)

    assert (exit_code, printed["error"]["code"]) == (3, "not_found")


def test_cut_delete_while_the_cut_is_exported_exits_4_with_busy_and_keeps_the_cut(
    wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cut_id = stored_cut(wordcut_home)
    with closing(connect(Home(wordcut_home))) as connection:
        new = NewTask("render", "cut", cut_id, {}, os.getpid(), socket.gethostname(), NOW)
        task = tasks.insert(connection, new)

    exit_code, printed = run_json(["cut", "delete", str(cut_id), "--json"], capsys)
    kept = run_json(["cut", "show", str(cut_id), "--json"], capsys)[0]

    assert (exit_code, printed["error"]["code"], printed["error"]["details"], kept) == (
        4,
        "busy",
        {"task_id": task.id, "kind": "render", "started_at": NOW.isoformat()},
        0,
    )


def test_cut_delete_without_json_says_in_words_what_was_deleted(
    wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cut_id = stored_cut(wordcut_home)

    exit_code = main(["cut", "delete", str(cut_id)])

    assert (exit_code, capsys.readouterr().out) == (
        0,
        f"Corte {cut_id} apagado, com suas exportações.\n",
    )


def test_cut_delete_help_says_it_is_for_the_administrator_with_an_example(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["cut", "delete", "--help"])

    help_text = capsys.readouterr().out
    assert (exit_code, "administrador" in help_text, "wordcut cut delete 34" in help_text) == (
        0,
        True,
        True,
    )
