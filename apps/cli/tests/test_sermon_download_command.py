import json
import subprocess
from collections.abc import Callable
from contextlib import closing
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from wordcut.db import connect, sermons
from wordcut.home import Home
from wordcut.youtube import LiveInfo
from wordcut_cli import deps, main

LINK = "https://youtu.be/Ab3_x-9QzLk"
FINISHED_LIVE = LiveInfo(
    title="Culto de domingo",
    service_date=date(2026, 10, 18),
    duration=7200.0,
    live_status="was_live",
)
StartLockOwner = Callable[[str, str], subprocess.Popen[str]]

PROCESSED_AT = datetime(2026, 10, 26, 19, 40, tzinfo=timezone(timedelta(hours=-3)))
READABLE_NAME = "2026-10-18 - Culto de domingo.mp4"
# Arbitrary, non-repeating bytes standing for the processed 16:9 video.
VIDEO = bytes(range(256)) * 4 + b"amen"


class FakeLive:
    def info(self, url: str) -> LiveInfo:
        return FINISHED_LIVE


@pytest.fixture
def sermon(
    wordcut_home: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> int:
    """The ID of a processed sermon whose video holds ``VIDEO``."""
    monkeypatch.setattr(deps, "live_source", FakeLive)
    main(["sermon", "create", LINK, "--json"])
    sermon_id: int = json.loads(capsys.readouterr().out)["id"]
    home = Home(wordcut_home)
    video = home.sermon_media(sermon_id) / "sermon.mp4"
    video.parent.mkdir(parents=True)
    video.write_bytes(VIDEO)
    with closing(connect(home)) as connection, connection:
        sermons.record_processed(
            connection,
            sermon_id,
            1000.0,
            1100.0,
            str(video.relative_to(home.root)),
            PROCESSED_AT,
        )
    return sermon_id


@pytest.fixture
def here(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """An empty current folder."""
    folder = tmp_path / "here"
    folder.mkdir()
    monkeypatch.chdir(folder)
    return folder


def run_json(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, Any]:
    exit_code = main(argv)
    return exit_code, json.loads(capsys.readouterr().out)


def test_download_with_json_copies_the_video_to_the_current_folder_with_the_readable_name(
    sermon: int, here: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code, result = run_json(["sermon", "download", str(sermon), "--json"], capsys)

    copied = Path(result["path"])
    assert (exit_code, copied, copied.read_bytes(), result["bytes"]) == (
        0,
        here / READABLE_NAME,
        VIDEO,
        len(VIDEO),
    )


@pytest.mark.parametrize("absolute", [False, True])
def test_download_to_a_file_path_creates_its_folders_and_answers_the_absolute_path(
    sermon: int, here: Path, capsys: pytest.CaptureFixture[str], absolute: bool
) -> None:
    destination = here / "x" / "y" / "pregacao.mp4"
    output = str(destination) if absolute else "x/y/pregacao.mp4"

    exit_code, result = run_json(
        ["sermon", "download", str(sermon), "-o", output, "--json"], capsys
    )

    assert (exit_code, result["path"], destination.read_bytes()) == (0, str(destination), VIDEO)


def test_download_without_json_prints_only_the_absolute_path_of_the_copy(
    sermon: int, here: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(["sermon", "download", str(sermon)])

    output = capsys.readouterr()
    assert (exit_code, output.out, output.err) == (0, f"{here / READABLE_NAME}\n", "")


def test_download_to_an_existing_folder_writes_the_readable_name_inside_it(
    sermon: int, here: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    folder = here / "downloads"
    folder.mkdir()

    exit_code, result = run_json(
        ["sermon", "download", str(sermon), "-o", "downloads", "--json"], capsys
    )

    assert (exit_code, result["path"], (folder / READABLE_NAME).read_bytes()) == (
        0,
        str(folder / READABLE_NAME),
        VIDEO,
    )


def test_a_second_download_gets_2_in_the_name_and_keeps_the_first_file(
    sermon: int, here: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _, first = run_json(["sermon", "download", str(sermon), "--json"], capsys)
    Path(first["path"]).write_bytes(b"edited by the operator")

    exit_code, second = run_json(["sermon", "download", str(sermon), "--json"], capsys)

    assert (exit_code, Path(second["path"]).name, Path(first["path"]).read_bytes()) == (
        0,
        "2026-10-18 - Culto de domingo (2).mp4",
        b"edited by the operator",
    )


@pytest.mark.parametrize(
    "argv",
    [
        ["--json", "sermon", "download"],
        ["sermon", "--json", "download"],
        ["sermon", "download", "--json"],
    ],
)
def test_json_option_is_accepted_before_between_and_after_the_download_action(
    sermon: int, here: Path, capsys: pytest.CaptureFixture[str], argv: list[str]
) -> None:
    exit_code, result = run_json([*argv, str(sermon)], capsys)

    assert (exit_code, result) == (0, {"path": str(here / READABLE_NAME), "bytes": len(VIDEO)})


def test_download_works_while_another_process_holds_the_processing_lock(
    sermon: int,
    here: Path,
    capsys: pytest.CaptureFixture[str],
    lock_owner: StartLockOwner,
) -> None:
    lock_owner("process", "sermon 99")

    exit_code, result = run_json(["sermon", "download", str(sermon), "--json"], capsys)

    assert (exit_code, Path(result["path"]).read_bytes()) == (0, VIDEO)


@pytest.fixture
def unprocessed(
    wordcut_home: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> int:
    """The ID of a sermon just created, not processed."""
    monkeypatch.setattr(deps, "live_source", FakeLive)
    main(["sermon", "create", LINK, "--json"])
    sermon_id: int = json.loads(capsys.readouterr().out)["id"]
    return sermon_id


def test_download_of_a_sermon_not_processed_fails_with_sermon_not_processed_and_exit_5(
    unprocessed: int, here: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code, result = run_json(["sermon", "download", str(unprocessed), "--json"], capsys)

    assert (exit_code, result["error"]["code"], list(here.iterdir())) == (
        5,
        "sermon_not_processed",
        [],
    )


def test_download_of_a_missing_sermon_fails_with_not_found_and_exit_3(
    wordcut_home: Path, here: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code, result = run_json(["sermon", "download", "999", "--json"], capsys)

    assert (exit_code, result["error"]["code"]) == (3, "not_found")


def test_download_of_a_non_numeric_id_is_a_usage_error_with_exit_2(
    wordcut_home: Path, here: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code, result = run_json(["sermon", "download", "abc", "--json"], capsys)

    assert (exit_code, result["error"]["code"]) == (2, "invalid_argument")


def test_download_of_a_sermon_whose_video_left_the_disk_is_the_service_internal_error(
    sermon: int, wordcut_home: Path, here: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (Home(wordcut_home).sermon_media(sermon) / "sermon.mp4").unlink()

    exit_code = main(["sermon", "download", str(sermon), "--json"])

    out = capsys.readouterr().out
    assert (exit_code, json.loads(out), str(wordcut_home) in out) == (
        1,
        {
            "error": {
                "code": "internal_error",
                "message": f"Vídeo da pregação {sermon} não encontrado.",
                "details": {"sermon_id": sermon},
            }
        },
        False,
    )
