import json
from contextlib import AbstractContextManager, closing, nullcontext
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from wordcut.home import Home
from wordcut.lock import ProcessingLock
from wordcut.youtube import LiveInfo
from wordcut_cli import deps, main

LINK = "https://youtu.be/Ab3_x-9QzLk"
TWO_HOUR_LIVE = LiveInfo(
    title="Culto de domingo",
    service_date=date(2026, 10, 18),
    duration=7200.0,
    live_status="was_live",
)


class FakeLive:
    """``LiveSource`` double that always answers the same live."""

    def __init__(self, info: LiveInfo = TWO_HOUR_LIVE) -> None:
        self.answer = info

    def info(self, url: str) -> LiveInfo:
        return self.answer


@pytest.fixture
def live(monkeypatch: pytest.MonkeyPatch, wordcut_home: Path) -> FakeLive:
    fake = FakeLive()
    monkeypatch.setattr(deps, "live_source", lambda: fake)
    return fake


@pytest.fixture
def sermon_id(live: FakeLive, capsys: pytest.CaptureFixture[str]) -> str:
    assert main(["sermon", "create", LINK, "--json"]) == 0
    created: dict[str, Any] = json.loads(capsys.readouterr().out)
    return str(created["id"])


def put_in_state(sermon_id: str, status: str) -> None:
    """Stand in for the processing flow (item 5), which does not exist yet."""
    with closing(deps.connection()) as connection, connection:
        connection.execute("UPDATE sermons SET status = ? WHERE id = ?", (status, sermon_id))


def trim(sermon_id: str, *options: str) -> list[str]:
    return ["sermon", "trim", sermon_id, "--start", "1:02:10", "--end", "1:48:30", *options]


def run_json(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, Any]:
    exit_code = main(argv)
    return exit_code, json.loads(capsys.readouterr().out)


def test_trim_with_json_answers_the_trimmed_sermon_as_show_does(
    sermon_id: str, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code, trimmed = run_json(
        ["sermon", "trim", sermon_id, "--start", "1:02:10", "--end", "1:48:30", "--json"], capsys
    )

    shown = run_json(["sermon", "show", sermon_id, "--json"], capsys)[1]
    borders = {field: shown[field] for field in ("status", "live_start", "live_end", "duration")}
    assert (exit_code, trimmed, borders) == (
        0,
        shown,
        {"status": "trimmed", "live_start": 3730.0, "live_end": 6510.0, "duration": 2780.0},
    )


REPROCESS_WARNING = (
    "aviso: A pregação já foi processada; as bordas novas valem depois de"
    " wordcut sermon process --force.\n"
)


@pytest.mark.parametrize("quiet", [[], ["--quiet"]])
def test_trimming_a_processed_sermon_warns_on_stderr_even_when_quiet_and_keeps_stdout_json(
    sermon_id: str, quiet: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    put_in_state(sermon_id, "processed")

    exit_code = main([*quiet, *trim(sermon_id, "--json")])

    captured = capsys.readouterr()
    assert (exit_code, json.loads(captured.out)["status"], captured.err) == (
        0,
        "processed",
        REPROCESS_WARNING,
    )


def test_trimming_a_sermon_not_yet_processed_warns_nothing(
    sermon_id: str, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(trim(sermon_id, "--json"))

    assert (exit_code, capsys.readouterr().err) == (0, "")


@pytest.mark.parametrize(
    ("start", "end", "borders"),
    [
        ("1:02:10.250", "1:48:30", (3730.25, 6510.0)),
        ("62:10", "108:30.5", (3730.0, 6510.5)),
        ("3730", "6510.2", (3730.0, 6510.2)),
    ],
)
def test_borders_are_accepted_as_hours_minutes_or_seconds(
    sermon_id: str,
    start: str,
    end: str,
    borders: tuple[float, float],
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code, trimmed = run_json(
        ["sermon", "trim", sermon_id, "--start", start, "--end", end, "--json"], capsys
    )

    assert (exit_code, (trimmed["live_start"], trimmed["live_end"])) == (0, borders)


@pytest.mark.parametrize(
    ("start", "end", "argument"),
    [("abc", "1:48:30", "--start"), ("1:02:10", "inf", "--end"), ("1:-5", "1:48:30", "--start")],
)
def test_border_in_an_unknown_format_is_an_invalid_argument_naming_the_option(
    sermon_id: str, start: str, end: str, argument: str, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code, failure = run_json(
        ["sermon", "trim", sermon_id, "--start", start, "--end", end, "--json"], capsys
    )

    assert (exit_code, failure["error"]["code"], failure["error"]["details"]) == (
        2,
        "invalid_argument",
        {"argument": argument},
    )


@pytest.mark.parametrize(
    ("options", "argument"),
    [(["--end", "1:48:30"], "--start"), (["--start", "1:02:10"], "--end")],
)
def test_trim_without_both_borders_is_an_invalid_argument_naming_the_missing_one(
    sermon_id: str, options: list[str], argument: str, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code, failure = run_json(["sermon", "trim", sermon_id, *options, "--json"], capsys)

    assert (exit_code, failure["error"]["code"], failure["error"]["details"]) == (
        2,
        "invalid_argument",
        {"argument": argument},
    )


def held_while(status: str, sermon_id: str) -> AbstractContextManager[object]:
    """The lock held for a ``processing`` sermon, as its task holds it."""
    if status != "processing":
        return nullcontext()
    return ProcessingLock(Home.from_environment()).acquire("process", f"sermon {sermon_id}")


@pytest.mark.parametrize(
    ("status", "target", "end", "exit_code", "code"),
    [
        ("created", "999", "1:48:30", 3, "not_found"),
        ("created", "1", "1:03:09", 5, "sermon_too_short"),
        ("processing", "1", "1:48:30", 4, "busy"),
        ("created", "1", "2:00:01", 2, "invalid_argument"),
    ],
)
def test_refused_trim_exits_with_the_contract_code_and_leaves_the_sermon_as_it_was(
    sermon_id: str,
    status: str,
    target: str,
    end: str,
    exit_code: int,
    code: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with held_while(status, sermon_id):
        put_in_state(sermon_id, status)
        before = run_json(["sermon", "show", sermon_id, "--json"], capsys)[1]

        refused = run_json(
            ["sermon", "trim", target, "--start", "1:02:10", "--end", end, "--json"], capsys
        )

        after = run_json(["sermon", "show", sermon_id, "--json"], capsys)[1]
    assert (refused[0], refused[1]["error"]["code"], after) == (exit_code, code, before)


def test_trim_without_json_describes_the_sermon_as_show_does(
    sermon_id: str, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(trim(sermon_id))

    assert (exit_code, capsys.readouterr().out) == (
        0,
        "Pregação 1: Culto de domingo\n"
        "Culto: 18/10/2026\n"
        "Live: 2:00:00, terminada\n"
        "Estado: delimitada\n"
        "Bordas: 1:02:10 a 1:48:30 da live\n"
        "Cortes: nenhum\n"
        "Timeline: preparando\n",
    )


BORDERS = ["--start", "1:02:10", "--end", "1:48:30"]


def test_create_with_borders_answers_a_new_trimmed_sermon(
    live: FakeLive, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code, created = run_json(["sermon", "create", LINK, *BORDERS, "--json"], capsys)

    shown = run_json(["sermon", "show", str(created["id"]), "--json"], capsys)[1]
    assert (
        exit_code,
        created["created"],
        created["status"],
        "needs_reprocess" in created,
        (shown["live_start"], shown["live_end"]),
    ) == (0, True, "trimmed", False, (3730.0, 6510.0))


@pytest.mark.parametrize(
    ("options", "missing"),
    [(["--start", "1:02:10"], "--end"), (["--end", "1:48:30"], "--start")],
)
def test_create_with_a_single_border_names_the_missing_one_and_creates_nothing(
    live: FakeLive, options: list[str], missing: str, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code, failure = run_json(["sermon", "create", LINK, *options, "--json"], capsys)

    assert (
        exit_code,
        failure["error"]["code"],
        failure["error"]["details"],
        run_json(["sermon", "list", "--json"], capsys)[1],
    ) == (2, "invalid_argument", {"argument": missing}, {"items": []})


@pytest.mark.parametrize(
    ("end", "exit_code", "code"),
    [("1:03:09", 5, "sermon_too_short"), ("2:00:01", 2, "invalid_argument")],
)
def test_create_with_refused_borders_exits_with_the_trim_error_and_creates_nothing(
    live: FakeLive, end: str, exit_code: int, code: str, capsys: pytest.CaptureFixture[str]
) -> None:
    refused = run_json(
        ["sermon", "create", LINK, "--start", "1:02:10", "--end", end, "--json"], capsys
    )

    assert (
        refused[0],
        refused[1]["error"]["code"],
        run_json(["sermon", "list", "--json"], capsys)[1],
    ) == (exit_code, code, {"items": []})


def test_create_with_borders_of_a_processed_sermon_warns_and_answers_the_existing_one(
    sermon_id: str, capsys: pytest.CaptureFixture[str]
) -> None:
    put_in_state(sermon_id, "processed")

    exit_code = main(["sermon", "create", LINK, *BORDERS, "--json"])

    captured = capsys.readouterr()
    again = json.loads(captured.out)
    assert (exit_code, again["created"], again["status"], captured.err) == (
        0,
        False,
        "processed",
        REPROCESS_WARNING,
    )
