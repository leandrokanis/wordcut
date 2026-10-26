import sqlite3
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path
from typing import Any

import pytest

from wordcut.criteria import LEVELS, TEXTS, catalog
from wordcut.db import connect
from wordcut.db.presets import SecondsRange
from wordcut.home import Home
from wordcut.service.presets import build_prompt, default_preset, update_preset


@pytest.fixture
def connection(wordcut_home: Path) -> Iterator[sqlite3.Connection]:
    with closing(connect(Home(wordcut_home))) as opened:
        yield opened


def other_levels(criterion_level: str) -> list[str]:
    return [level for level in LEVELS if level != criterion_level]


def mixed_levels() -> dict[str, str]:
    """A level for each criterion, cycling through the three so none is left untested."""
    return {
        criterion.id: LEVELS[index % len(LEVELS)]
        for index, criterion in enumerate(catalog().criteria)
    }


def test_the_prompt_has_the_piece_of_the_preset_level_of_each_criterion_and_no_other(
    connection: sqlite3.Connection,
) -> None:
    levels = mixed_levels()
    preset = update_preset(connection, default_preset(connection)["id"], levels=levels)

    prompt = build_prompt(preset)

    for criterion in catalog().criteria:
        chosen = levels[criterion.id]
        others = [criterion.fragment(level) in prompt for level in other_levels(chosen)]
        assert (criterion.fragment(chosen) in prompt, others) == (True, [False, False])


def option(name: str) -> str:
    """The text of an edit option as it ships, before its slots are filled."""
    return (TEXTS / "options" / f"{name}.md").read_text(encoding="utf-8").strip()


def test_with_reorder_on_the_prompt_has_the_reordering_safeguards(
    connection: sqlite3.Connection,
) -> None:
    prompt = build_prompt(default_preset(connection))

    assert (option("reorder") in prompt, option("no_reorder") in prompt) == (True, False)


def test_with_reorder_off_the_prompt_forbids_reordering_instead(
    connection: sqlite3.Connection,
) -> None:
    preset = update_preset(connection, default_preset(connection)["id"], reorder=False)

    prompt = build_prompt(preset)

    assert (option("reorder") in prompt, option("no_reorder") in prompt) == (False, True)


def test_the_prompt_lists_the_protected_words_of_the_preset(
    connection: sqlite3.Connection,
) -> None:
    preset = update_preset(
        connection, default_preset(connection)["id"], protected_words=["não", "jamais"]
    )

    prompt = build_prompt(preset)

    assert ('"não", "jamais"' in prompt, '"mas"' in prompt) == (True, False)


INSTRUCTIONS_LABEL = "Instruções adicionais do administrador"


def test_the_instructions_come_labelled_as_the_administrator_s_after_the_criteria(
    connection: sqlite3.Connection,
) -> None:
    instructions = "Prefira trechos sobre a Ceia."
    preset = update_preset(connection, default_preset(connection)["id"], instructions=instructions)

    prompt = build_prompt(preset)

    last_criterion = prompt.index(catalog().criteria[-1].fragment("moderate"))
    label = prompt.find(INSTRUCTIONS_LABEL)
    assert last_criterion < label < prompt.find(instructions)


def test_without_instructions_the_prompt_has_no_empty_label(
    connection: sqlite3.Connection,
) -> None:
    assert INSTRUCTIONS_LABEL not in build_prompt(default_preset(connection))


def test_the_prompt_has_every_line_of_the_base_prompt(connection: sqlite3.Connection) -> None:
    prompt = build_prompt(default_preset(connection))
    base = (TEXTS / "base.md").read_text(encoding="utf-8")
    fixed = [line for line in base.splitlines() if line and "${" not in line]

    assert [line for line in fixed if line not in prompt] == []


def test_the_prompt_has_the_durations_of_the_preset_and_not_the_factory_ones(
    connection: sqlite3.Connection,
) -> None:
    preset = update_preset(
        connection,
        default_preset(connection)["id"],
        duration_allowed=SecondsRange(45, 80),
        duration_ideal=SecondsRange(60, 75),
    )

    prompt = build_prompt(preset)

    assert [text in prompt for text in ("45–80 s", "60–75 s", "40–75", "55–65")] == [
        True,
        True,
        False,
        False,
    ]


def test_the_prompt_takes_a_missing_criterion_at_its_default_and_ignores_a_removed_one(
    connection: sqlite3.Connection,
) -> None:
    preset: dict[str, Any] = {
        **default_preset(connection),
        "levels": {"removed_criterion": "strict", "allegory": "strict"},
    }

    prompt = build_prompt(preset)

    christological = catalog().criterion("christological")
    assert christological is not None
    assert (
        christological.fragment(christological.default_level) in prompt,
        "removed_criterion" in prompt,
    ) == (True, False)


def test_building_the_prompt_reaches_no_network(
    connection: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    preset = default_preset(connection)

    def refuse(*args: object, **kwargs: object) -> None:
        raise AssertionError("build_prompt reached the network")

    monkeypatch.setattr("socket.socket", refuse)
    monkeypatch.setattr("socket.create_connection", refuse)

    assert build_prompt(preset).startswith("Objetivo:")
