import json
from contextlib import closing
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pytest

from wordcut.db import connect, cuts, sermons
from wordcut.db.cuts import NewCut, Segment
from wordcut.db.sermons import SuggestionError
from wordcut.home import Home
from wordcut.youtube import LiveInfo, YouTubeError
from wordcut_cli import deps, main

VIDEO = "Ab3_x-9QzLk"
LINK = f"https://www.youtube.com/watch?v={VIDEO}"
FINISHED_LIVE = LiveInfo(
    title="Culto de domingo",
    service_date=date(2026, 10, 18),
    duration=7718.0,
    live_status="was_live",
)


class FakeLive:
    """``LiveSource`` double that answers ``info`` and counts the calls."""

    def __init__(self, info: LiveInfo = FINISHED_LIVE) -> None:
        self.answer = info
        self.calls = 0

    def info(self, url: str) -> LiveInfo:
        self.calls += 1
        return self.answer


LIVE_ON_AIR = LiveInfo.from_metadata(
    {"title": "Culto ao vivo", "timestamp": 1792361083, "live_status": "is_live"}
)


@pytest.fixture
def live(monkeypatch: pytest.MonkeyPatch, wordcut_home: Path) -> FakeLive:
    fake = FakeLive()
    monkeypatch.setattr(deps, "live_source", lambda: fake)
    return fake


def run_json(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, Any]:
    exit_code = main(argv)
    return exit_code, json.loads(capsys.readouterr().out)


def test_create_with_json_prints_the_new_sermon_and_exits_0(
    live: FakeLive, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code, sermon = run_json(["sermon", "create", LINK, "--json"], capsys)

    sermon.pop("created_at")
    assert (exit_code, sermon) == (
        0,
        {
            "id": sermon["id"],
            "youtube_id": VIDEO,
            "url": LINK,
            "title": "Culto de domingo",
            "service_date": "2026-10-18",
            "live_duration": 7718.0,
            "live_finished": True,
            "status": "created",
            "created": True,
        },
    )


@pytest.mark.parametrize(
    "argv",
    [
        ["--json", "sermon", "create", LINK],
        ["sermon", "--json", "create", LINK],
        ["sermon", "create", LINK, "--json"],
    ],
)
def test_json_option_is_accepted_before_between_and_after_the_sermon_action(
    argv: list[str], live: FakeLive, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code, sermon = run_json(argv, capsys)

    assert (exit_code, sermon["youtube_id"]) == (0, VIDEO)


@pytest.mark.parametrize("quiet", [[], ["--quiet"]])
def test_live_still_on_air_warns_on_stderr_even_when_quiet_and_stdout_keeps_only_the_json(
    quiet: list[str], live: FakeLive, capsys: pytest.CaptureFixture[str]
) -> None:
    live.answer = LIVE_ON_AIR

    exit_code = main([*quiet, "sermon", "create", LINK, "--json"])

    captured = capsys.readouterr()
    assert (exit_code, json.loads(captured.out)["live_finished"], captured.err) == (
        0,
        False,
        "aviso: A live ainda não terminou; a pregação foi criada mesmo assim.\n",
    )


def test_same_video_through_another_link_returns_the_existing_sermon(
    live: FakeLive, capsys: pytest.CaptureFixture[str]
) -> None:
    _, first = run_json(["sermon", "create", LINK, "--json"], capsys)

    exit_code, again = run_json(["sermon", "create", f"https://youtu.be/{VIDEO}", "--json"], capsys)

    assert (exit_code, again["id"], again["created"], live.calls) == (0, first["id"], False, 1)


def test_show_with_json_prints_the_sermon_with_empty_borders_and_no_cuts(
    live: FakeLive, capsys: pytest.CaptureFixture[str]
) -> None:
    _, created = run_json(["sermon", "create", LINK, "--json"], capsys)

    exit_code, shown = run_json(["sermon", "show", str(created["id"]), "--json"], capsys)

    assert (exit_code, shown["id"], shown["live_start"], shown["live_end"], shown["cuts"]) == (
        0,
        created["id"],
        None,
        None,
        [],
    )


def live_on(service_date: date) -> LiveInfo:
    return LiveInfo(
        title="Culto", service_date=service_date, duration=3600.0, live_status="was_live"
    )


def create_on(service_date: date, youtube_id: str, live: FakeLive) -> None:
    live.answer = live_on(service_date)
    assert main(["sermon", "create", f"https://youtu.be/{youtube_id}", "--quiet"]) == 0


def test_list_with_json_prints_the_items_newest_service_first(
    live: FakeLive, capsys: pytest.CaptureFixture[str]
) -> None:
    create_on(date(2026, 10, 11), "Aaaaaaaaaa1", live)
    create_on(date(2026, 10, 18), "Aaaaaaaaaa2", live)
    capsys.readouterr()

    exit_code, listing = run_json(["sermon", "list", "--json"], capsys)

    assert (exit_code, [item["service_date"] for item in listing["items"]]) == (
        0,
        ["2026-10-18", "2026-10-11"],
    )


def test_list_with_status_keeps_only_the_sermons_in_that_state(
    live: FakeLive, capsys: pytest.CaptureFixture[str]
) -> None:
    create_on(date(2026, 10, 18), "Aaaaaaaaaa1", live)
    capsys.readouterr()

    assert run_json(["sermon", "list", "--status", "trimmed", "--json"], capsys) == (
        0,
        {"items": []},
    )


@pytest.mark.parametrize(
    ("argv", "exit_code", "error"),
    [
        (["sermon", "create", "https://vimeo.com/123456"], 2, ("invalid_argument", "link")),
        (["sermon", "show", "999"], 3, ("not_found", None)),
        (["sermon", "show", "abc"], 2, ("invalid_argument", "id")),
        (["sermon", "list", "--status", "arquivada"], 2, ("invalid_argument", "--status")),
        (["sermon"], 2, ("invalid_argument", "action")),
    ],
)
def test_sermon_failures_follow_the_error_contract(
    argv: list[str],
    exit_code: int,
    error: tuple[str, str | None],
    live: FakeLive,
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = run_json([*argv, "--json"], capsys)

    reported = result[1]["error"]
    assert (
        result[0],
        reported["code"],
        reported.get("details", {}).get("argument"),
        live.calls,
    ) == (
        exit_code,
        *error,
        0,
    )


class UnreachableYouTube:
    def info(self, url: str) -> LiveInfo:
        raise YouTubeError("O YouTube recusou o pedido.")


def test_youtube_failure_exits_6_and_creates_nothing(
    wordcut_home: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(deps, "live_source", UnreachableYouTube)
    exit_code, failure = run_json(["sermon", "create", LINK, "--json"], capsys)

    assert (
        exit_code,
        failure["error"]["code"],
        run_json(["sermon", "list", "--json"], capsys),
    ) == (
        6,
        "youtube_error",
        (0, {"items": []}),
    )


def test_failure_without_json_leaves_stdout_empty_and_explains_on_stderr(
    live: FakeLive, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(["sermon", "show", "999"])

    captured = capsys.readouterr()
    assert (exit_code, captured.out, captured.err) == (3, "", "erro: Pregação 999 não existe.\n")


def test_create_without_json_summarizes_the_sermon_in_portuguese(
    live: FakeLive, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(["sermon", "create", LINK])

    captured = capsys.readouterr()
    assert (exit_code, captured.out, captured.err) == (
        0,
        "Pregação 1 criada: Culto de domingo, culto de 18/10/2026, live de 2:08:38.\n",
        "",
    )


def test_list_without_json_prints_one_line_per_sermon_newest_first(
    live: FakeLive, capsys: pytest.CaptureFixture[str]
) -> None:
    create_on(date(2026, 10, 11), "Aaaaaaaaaa1", live)
    create_on(date(2026, 10, 18), "Aaaaaaaaaa2", live)
    capsys.readouterr()

    exit_code = main(["sermon", "list"])

    assert (exit_code, capsys.readouterr().out) == (
        0,
        "2  18/10/2026  criada  Culto\n1  11/10/2026  criada  Culto\n",
    )


def test_list_without_json_and_without_sermons_says_so(
    wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(["sermon", "list"])

    assert (exit_code, capsys.readouterr().out) == (0, "Nenhuma pregação.\n")


def test_show_without_json_describes_the_sermon_in_portuguese(
    live: FakeLive, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["sermon", "create", LINK])
    capsys.readouterr()

    exit_code = main(["sermon", "show", "1"])

    assert (exit_code, capsys.readouterr().out) == (
        0,
        "Pregação 1: Culto de domingo\n"
        "Culto: 18/10/2026\n"
        "Live: 2:08:38, terminada\n"
        "Estado: criada\n"
        "Bordas: não definidas\n"
        "Cortes: nenhum\n",
    )


def test_sermon_help_lists_its_actions(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["sermon", "--help"])

    assert (
        exit_code,
        "{create,list,show,trim,process,download,suggest}" in capsys.readouterr().out,
    ) == (
        0,
        True,
    )


@pytest.mark.parametrize(
    "action", ["create", "list", "show", "trim", "process", "download", "suggest"]
)
def test_each_sermon_action_help_shows_an_example_ready_to_copy(
    action: str, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(["sermon", action, "--help"])

    assert (exit_code, f"wordcut sermon {action} " in capsys.readouterr().out) == (0, True)


def record_failed_suggestion(sermon_id: int, message: str) -> None:
    """An earlier suggestion that left one cut, then a later one that failed with ``message``."""
    earlier = NewCut(
        status="suggested",
        title="Graça que alcança",
        segments=(Segment(1, 4),),
        range_start_word=1,
        range_end_word=4,
        source="llm",
        preset_id=None,
    )
    with closing(connect(Home.from_environment())) as connection, connection:
        cuts.insert_many(connection, sermon_id, [earlier], datetime.now().astimezone())
        sermons.record_suggestion_error(
            connection, sermon_id, SuggestionError("llm_not_configured", message)
        )


def test_show_tells_why_the_last_suggestion_failed(
    live: FakeLive, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["sermon", "create", LINK, "--quiet"])
    record_failed_suggestion(1, "Sem a chave do LLM (wordcut settings set-key).")

    exit_code = main(["sermon", "show", "1"])
    readable = capsys.readouterr().out
    _, shown = run_json(["sermon", "show", "1", "--json"], capsys)

    assert (
        exit_code,
        readable.splitlines()[-2:],
        [cut["title"] for cut in shown["cuts"]],
        shown["suggestion_error"],
        shown["cut_counts"],
    ) == (
        0,
        [
            "Cortes: 1",
            "Sugestão de cortes falhou: Sem a chave do LLM (wordcut settings set-key).",
        ],
        ["Graça que alcança"],
        {
            "code": "llm_not_configured",
            "message": "Sem a chave do LLM (wordcut settings set-key).",
        },
        {"suggested": 1, "chosen": 0, "discarded": 0},
    )
