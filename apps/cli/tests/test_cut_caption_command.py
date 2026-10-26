import json
from contextlib import closing
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from wordcut.db import connect, cuts, sermons, transcripts
from wordcut.db.cuts import CutRow, NewCut, Segment
from wordcut.db.sermons import NewSermon
from wordcut.home import Home
from wordcut.transcript import Word
from wordcut_cli import main

NOW = datetime(2026, 10, 26, 22, 40, tzinfo=timezone.utc)
SPOKEN = (
    Word("Irmãos,", 0.3, 0.8),
    Word("graça", 0.9, 1.2),
    Word("e", 1.25, 1.3),
    Word("paz.", 1.35, 1.9),
)
CHURCH_STYLE = {
    "enabled": True,
    "font": "Open Sans Bold",
    "size": 60,
    "color": "#FFD600",
    "position": "center",
    "offset": 50,
    "border": 3,
    "border_color": "#000000",
    "shadow": "soft",
}


@pytest.fixture
def cut_id(wordcut_home: Path) -> int:
    """A new ``suggested`` cut of a processed sermon, playing all its words."""
    with closing(connect(Home.from_environment())) as connection, connection:
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
        segments = (Segment(word[0], word[3]),)
        new = NewCut("suggested", "Graça que alcança", segments, word[0], word[3], "llm", None)
        [created] = cuts.insert_many(connection, sermon.id, [new], NOW)
        return created


def run_json(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, Any]:
    exit_code = main(argv)
    return exit_code, json.loads(capsys.readouterr().out)


def test_caption_of_a_new_cut_prints_the_church_style_and_exits_0(
    cut_id: int, capsys: pytest.CaptureFixture[str]
) -> None:
    answer = run_json(["cut", "caption", str(cut_id), "--json"], capsys)

    assert answer == (0, CHURCH_STYLE)


def test_caption_with_options_changes_only_those_and_cut_show_carries_the_new_style(
    cut_id: int, capsys: pytest.CaptureFixture[str]
) -> None:
    changed = run_json(
        ["cut", "caption", str(cut_id), "--size", "72", "--color", "#FFFFFF",
         "--position", "bottom", "--shadow", "strong", "--json"],
        capsys,
    )  # fmt: skip
    _, shown = run_json(["cut", "show", str(cut_id), "--json"], capsys)

    expected = {**CHURCH_STYLE, "size": 72, "color": "#FFFFFF", "position": "bottom",
                "offset": 78, "shadow": "strong"}  # fmt: skip
    assert (changed, shown["caption"]) == ((0, expected), expected)


def test_caption_off_then_reset_turns_it_off_and_back_to_the_church_style(
    cut_id: int, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["cut", "caption", str(cut_id), "--size", "90", "--json"])
    capsys.readouterr()

    off = run_json(["cut", "caption", str(cut_id), "--off", "--json"], capsys)
    reset = run_json(["cut", "caption", str(cut_id), "--reset", "--json"], capsys)

    assert (off, reset) == ((0, {**CHURCH_STYLE, "size": 90, "enabled": False}), (0, CHURCH_STYLE))


def test_caption_reset_with_another_option_exits_2_and_changes_nothing(
    cut_id: int, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code, answer = run_json(
        ["cut", "caption", str(cut_id), "--reset", "--size", "72", "--json"], capsys
    )
    _, style = run_json(["cut", "caption", str(cut_id), "--json"], capsys)

    assert (exit_code, answer["error"]["code"], answer["error"]["details"], style) == (
        2,
        "invalid_argument",
        {"argument": "--reset"},
        CHURCH_STYLE,
    )


def test_caption_without_json_prints_the_style_in_words_and_exits_0(
    cut_id: int, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(["cut", "caption", str(cut_id)])

    assert (exit_code, capsys.readouterr().out) == (
        0,
        "Legenda: ligada\n"
        "Fonte: Open Sans Bold, 60 px\n"
        "Cor: #FFD600\n"
        "Posição: centro, altura 50%\n"
        "Contorno: 3 px, #000000\n"
        "Sombra: suave\n",
    )


@pytest.mark.parametrize(
    ("options", "details"),
    [
        (["--on", "--off"], {"argument": "--off"}),
        (["--font", "Comic Sans MS"], {"argument": "font", "choices": ["Open Sans Bold"]}),
        (["--color", "FFF"], {"argument": "color"}),
        (["--border-color", "#12345"], {"argument": "border_color"}),
        (["--size", "23"], {"argument": "size", "min": 24, "max": 160}),
        (["--offset", "91"], {"argument": "offset", "min": 10, "max": 90}),
        (["--border", "13"], {"argument": "border", "min": 0, "max": 12}),
        (
            ["--position", "middle"],
            {"argument": "--position", "choices": ["top", "center", "bottom"]},
        ),
        (["--shadow", "hard"], {"argument": "--shadow", "choices": ["none", "soft", "strong"]}),
    ],
)
def test_caption_with_an_invalid_option_exits_2_and_changes_nothing(
    options: list[str],
    details: dict[str, Any],
    cut_id: int,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code, answer = run_json(["cut", "caption", str(cut_id), *options, "--json"], capsys)
    _, style = run_json(["cut", "caption", str(cut_id), "--json"], capsys)

    error = answer["error"]
    assert (exit_code, error["code"], error["details"], style) == (
        2,
        "invalid_argument",
        details,
        CHURCH_STYLE,
    )


def test_caption_of_a_cut_that_does_not_exist_exits_3(
    wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code, answer = run_json(["cut", "caption", "999", "--size", "72", "--json"], capsys)

    assert (exit_code, answer["error"]["code"]) == (3, "not_found")


def test_caption_on_turns_it_back_on(cut_id: int, capsys: pytest.CaptureFixture[str]) -> None:
    main(["cut", "caption", str(cut_id), "--off"])
    capsys.readouterr()

    answer = run_json(["cut", "caption", str(cut_id), "--on", "--json"], capsys)

    assert answer == (0, CHURCH_STYLE)


def test_caption_without_options_does_not_touch_the_cut(
    cut_id: int, capsys: pytest.CaptureFixture[str]
) -> None:
    before = stored_cut(cut_id)

    main(["cut", "caption", str(cut_id), "--json"])

    assert stored_cut(cut_id) == before


def stored_cut(cut_id: int) -> CutRow | None:
    with closing(connect(Home.from_environment())) as connection:
        return cuts.by_id(connection, cut_id)


def test_caption_help_shows_an_example(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["cut", "caption", "--help"])

    assert (exit_code, "Exemplo:\n  wordcut cut caption 34" in capsys.readouterr().out) == (
        0,
        True,
    )
