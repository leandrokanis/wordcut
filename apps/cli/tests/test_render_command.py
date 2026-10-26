import json
import subprocess
from collections.abc import Callable
from contextlib import closing
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from wordcut.db import connect, cuts, renders, sermons, transcripts
from wordcut.db.cuts import NewCut, Segment
from wordcut.db.renders import NewRender
from wordcut.db.sermons import NewSermon
from wordcut.home import Home
from wordcut.transcript import Word
from wordcut_cli import main

StartLockOwner = Callable[[str, str], subprocess.Popen[str]]

NOW = datetime(2026, 10, 26, 22, 40, tzinfo=timezone(timedelta(hours=-3)))
SPOKEN = (
    Word("Irmãos,", 0.3, 0.8),
    Word("graça", 0.9, 1.2),
    Word("e", 1.25, 1.3),
    Word("paz.", 1.35, 1.9),
)
OPTIONS = {"fillers": "remove", "pauses": "short", "caption": True, "quality": "high"}
READABLE_NAME = "2026-10-18 - Graça que alcança.mp4"
# Arbitrary, non-repeating bytes standing for an exported 9:16 video.
VIDEO = bytes(range(256)) * 4 + b"amen"


@pytest.fixture
def cut_id(wordcut_home: Path) -> int:
    """A cut titled "Graça que alcança" of a sermon of 2026-10-18 titled "Culto de domingo"."""
    with closing(connect(Home(wordcut_home))) as connection, connection:
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
        word = [row.id for row in transcripts.words_of(connection, sermon.id)]
        new = NewCut(
            "chosen", "Graça que alcança", (Segment(word[0], word[3]),), word[0], word[3], "llm",
            None,
        )  # fmt: skip
        [created] = cuts.insert_many(connection, sermon.id, [new], NOW)
    return created


def exported(home: Path, cut_id: int, created_at: datetime = NOW) -> int:
    """An export of the cut recorded as the ``render`` task does, its file holding ``VIDEO``."""
    where = Home(home)
    with closing(connect(where)) as connection, connection:
        render_id = renders.insert(connection, NewRender(cut_id, "", 31.5, OPTIONS, created_at))
        file = where.cut_media(cut_id) / f"{render_id}.mp4"
        renders.set_path(connection, render_id, str(file.relative_to(where.root)))
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_bytes(VIDEO)
    return render_id


def run_json(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, Any]:
    exit_code = main(argv)
    return exit_code, json.loads(capsys.readouterr().out)


def test_list_with_json_gives_the_exports_of_the_cut_the_most_recent_first(
    cut_id: int, wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    older = exported(wordcut_home, cut_id, NOW)
    newer = exported(wordcut_home, cut_id, NOW + timedelta(minutes=5))

    exit_code, result = run_json(["render", "list", "--cut", str(cut_id), "--json"], capsys)

    assert (exit_code, [item["id"] for item in result["items"]]) == (0, [newer, older])


def test_list_without_the_cut_is_a_usage_error_with_exit_2(
    wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code, result = run_json(["render", "list", "--json"], capsys)

    assert (exit_code, result["error"]["code"]) == (2, "invalid_argument")


def test_list_of_a_cut_that_does_not_exist_fails_with_not_found_and_exit_3(
    wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code, result = run_json(["render", "list", "--cut", "999", "--json"], capsys)

    assert (exit_code, result["error"]["code"]) == (3, "not_found")


def test_show_with_json_gives_the_export_with_the_absolute_path_of_its_file(
    cut_id: int, wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    render_id = exported(wordcut_home, cut_id)

    exit_code, result = run_json(["render", "show", str(render_id), "--json"], capsys)

    path = Path(result.pop("path"))
    assert (exit_code, result, path.is_absolute(), path.read_bytes()) == (
        0,
        {
            "id": render_id,
            "cut_id": cut_id,
            "duration": 31.5,
            "created_at": "2026-10-26T22:40:00-03:00",
            "options": OPTIONS,
        },
        True,
        VIDEO,
    )


def test_show_with_a_relative_data_folder_gives_the_absolute_path_of_the_file(
    cut_id: int,
    wordcut_home: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    render_id = exported(wordcut_home, cut_id)
    monkeypatch.chdir(wordcut_home.parent)
    monkeypatch.setenv("WORDCUT_HOME", wordcut_home.name)

    exit_code, result = run_json(["render", "show", str(render_id), "--json"], capsys)

    assert (exit_code, result["path"]) == (
        0,
        str(Home(wordcut_home).cut_media(cut_id) / f"{render_id}.mp4"),
    )


@pytest.fixture
def here(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """An empty current folder."""
    folder = tmp_path / "here"
    folder.mkdir()
    monkeypatch.chdir(folder)
    return folder


@pytest.fixture
def render_id(cut_id: int, wordcut_home: Path) -> int:
    return exported(wordcut_home, cut_id)


def test_download_with_json_copies_the_export_to_the_current_folder_with_the_readable_name(
    render_id: int, here: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code, result = run_json(["render", "download", str(render_id), "--json"], capsys)

    copied = Path(result["path"])
    assert (exit_code, copied, copied.read_bytes(), result["bytes"]) == (
        0,
        here / READABLE_NAME,
        VIDEO,
        len(VIDEO),
    )


@pytest.mark.parametrize("absolute", [False, True])
def test_download_to_a_file_path_creates_its_folders_and_answers_the_absolute_path(
    render_id: int, here: Path, capsys: pytest.CaptureFixture[str], absolute: bool
) -> None:
    destination = here / "x" / "y" / "corte.mp4"
    output = str(destination) if absolute else "x/y/corte.mp4"

    exit_code, result = run_json(
        ["render", "download", str(render_id), "-o", output, "--json"], capsys
    )

    assert (exit_code, result["path"], destination.read_bytes()) == (0, str(destination), VIDEO)


def test_download_without_json_prints_only_the_absolute_path_of_the_copy(
    render_id: int, here: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(["render", "download", str(render_id)])

    output = capsys.readouterr()
    assert (exit_code, output.out, output.err) == (0, f"{here / READABLE_NAME}\n", "")


@pytest.mark.parametrize("output", ["downloads", "novos/"])
def test_download_to_a_folder_writes_the_readable_name_inside_it(
    render_id: int, here: Path, capsys: pytest.CaptureFixture[str], output: str
) -> None:
    (here / "downloads").mkdir()
    folder = here / output.rstrip("/")

    exit_code, result = run_json(
        ["render", "download", str(render_id), "-o", output, "--json"], capsys
    )

    assert (exit_code, result["path"], (folder / READABLE_NAME).read_bytes()) == (
        0,
        str(folder / READABLE_NAME),
        VIDEO,
    )


def test_a_second_download_gets_2_in_the_name_and_keeps_the_first_file(
    render_id: int, here: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _, first = run_json(["render", "download", str(render_id), "--json"], capsys)
    Path(first["path"]).write_bytes(b"edited by the operator")

    exit_code, second = run_json(["render", "download", str(render_id), "--json"], capsys)

    assert (exit_code, Path(second["path"]).name, Path(first["path"]).read_bytes()) == (
        0,
        "2026-10-18 - Graça que alcança (2).mp4",
        b"edited by the operator",
    )


@pytest.mark.parametrize(
    "argv",
    [
        ["--json", "render", "download"],
        ["render", "--json", "download"],
        ["render", "download", "--json"],
    ],
)
def test_json_option_is_accepted_before_between_and_after_the_download_action(
    render_id: int, here: Path, capsys: pytest.CaptureFixture[str], argv: list[str]
) -> None:
    exit_code, result = run_json([*argv, str(render_id)], capsys)

    assert (exit_code, result) == (0, {"path": str(here / READABLE_NAME), "bytes": len(VIDEO)})


def test_list_show_and_download_work_while_another_process_holds_the_processing_lock(
    cut_id: int,
    render_id: int,
    here: Path,
    capsys: pytest.CaptureFixture[str],
    lock_owner: StartLockOwner,
) -> None:
    lock_owner("render", "cut 99")

    exit_codes = [
        run_json(argv, capsys)[0]
        for argv in (
            ["render", "list", "--cut", str(cut_id), "--json"],
            ["render", "show", str(render_id), "--json"],
            ["render", "download", str(render_id), "--json"],
        )
    ]

    assert (exit_codes, (here / READABLE_NAME).read_bytes()) == ([0, 0, 0], VIDEO)


@pytest.mark.parametrize("action", ["show", "download"])
def test_an_export_that_does_not_exist_fails_with_not_found_and_exit_3(
    wordcut_home: Path, here: Path, capsys: pytest.CaptureFixture[str], action: str
) -> None:
    exit_code, result = run_json(["render", action, "999", "--json"], capsys)

    assert (exit_code, result["error"]["code"], list(here.iterdir())) == (3, "not_found", [])


@pytest.mark.parametrize("action", ["show", "download"])
def test_a_non_numeric_id_is_a_usage_error_with_exit_2(
    wordcut_home: Path, here: Path, capsys: pytest.CaptureFixture[str], action: str
) -> None:
    exit_code, result = run_json(["render", action, "abc", "--json"], capsys)

    assert (exit_code, result["error"]["code"]) == (2, "invalid_argument")


def test_download_of_an_export_whose_file_left_the_disk_is_the_service_internal_error(
    cut_id: int, render_id: int, wordcut_home: Path, here: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (Home(wordcut_home).cut_media(cut_id) / f"{render_id}.mp4").unlink()

    exit_code = main(["render", "download", str(render_id), "--json"])

    out = capsys.readouterr().out
    assert (exit_code, json.loads(out), str(wordcut_home) in out, list(here.iterdir())) == (
        1,
        {
            "error": {
                "code": "internal_error",
                "message": f"Arquivo da exportação {render_id} não encontrado.",
                "details": {"render_id": render_id},
            }
        },
        False,
        [],
    )
