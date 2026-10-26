import sqlite3
from collections.abc import Iterator
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from wordcut.criteria import catalog
from wordcut.db import connect
from wordcut.db.presets import SecondsRange
from wordcut.errors import WordcutError
from wordcut.home import Home
from wordcut.service.presets import (
    create_preset,
    default_preset,
    delete_preset,
    list_presets,
    parse_level,
    parse_protected_words,
    parse_seconds_range,
    set_default,
    show_preset,
    update_preset,
)


@pytest.fixture
def connection(wordcut_home: Path) -> Iterator[sqlite3.Connection]:
    with closing(connect(Home(wordcut_home))) as opened:
        yield opened


def test_a_new_installation_lists_the_factory_preset_with_every_criterion_at_its_default(
    connection: sqlite3.Connection,
) -> None:
    [factory] = list_presets(connection)

    assert {key: value for key, value in factory.items() if key not in TIMES} == {
        "id": factory["id"],
        "name": "Padrão",
        "is_default": True,
        "levels": catalog().default_levels(),
        "duration_allowed": {"min": 40, "max": 75},
        "duration_ideal": {"min": 55, "max": 65},
        "reorder": True,
        "protected_words": ["não", "mas", "se"],
        "instructions": "",
    }


TIMES = ("created_at", "updated_at")


def factory_id(connection: sqlite3.Connection) -> int:
    [factory] = list_presets(connection)
    preset_id: int = factory["id"]
    return preset_id


def test_show_gives_the_same_preset_the_list_gives(connection: sqlite3.Connection) -> None:
    assert [show_preset(connection, factory_id(connection))] == list_presets(connection)


def test_showing_an_unknown_preset_is_not_found(connection: sqlite3.Connection) -> None:
    with pytest.raises(WordcutError) as raised:
        show_preset(connection, 999)

    assert (raised.value.code, raised.value.details) == ("not_found", {"preset_id": 999})


def store_levels(connection: sqlite3.Connection, preset_id: int, levels: str) -> None:
    """Levels as an older or newer version of the code left them in the database."""
    with connection:
        connection.execute("UPDATE presets SET levels = ? WHERE id = ?", (levels, preset_id))


def test_a_criterion_the_stored_preset_lacks_is_read_with_its_default_level(
    connection: sqlite3.Connection,
) -> None:
    preset_id = factory_id(connection)
    store_levels(connection, preset_id, '{"allegory": "lenient"}')

    levels = show_preset(connection, preset_id)["levels"]

    assert levels == {**catalog().default_levels(), "allegory": "lenient"}


def test_a_criterion_removed_from_the_code_is_left_out_of_show_and_list(
    connection: sqlite3.Connection,
) -> None:
    preset_id = factory_id(connection)
    store_levels(connection, preset_id, '{"removed_criterion": "strict", "allegory": "strict"}')

    shown = show_preset(connection, preset_id)["levels"]
    [listed] = list_presets(connection)

    assert (list(shown), listed["levels"]) == (list(catalog().default_levels()), shown)


def editable(preset: dict[str, Any]) -> dict[str, Any]:
    """What a copy carries over: everything but identity, name, default flag and times."""
    return {
        key: value
        for key, value in preset.items()
        if key not in ("id", "name", "is_default", "created_at", "updated_at")
    }


def test_a_created_preset_is_a_copy_of_the_default_that_is_not_the_default(
    connection: sqlite3.Connection,
) -> None:
    default = show_preset(connection, factory_id(connection))

    created = create_preset(connection, "Estudo bíblico")

    assert (created["name"], created["is_default"], editable(created)) == (
        "Estudo bíblico",
        False,
        editable(default),
    )


LATER = datetime(2026, 10, 27, 9, 30, tzinfo=timezone.utc)


def test_an_update_changes_every_field_given_and_is_kept_after_reopening(
    wordcut_home: Path,
) -> None:
    home = Home(wordcut_home)
    with closing(connect(home)) as connection:
        created = create_preset(connection, "Estudo bíblico")
        update_preset(
            connection,
            created["id"],
            name="Culto da família",
            levels={"allegory": "strict", "christological": "lenient"},
            duration_allowed=SecondsRange(45, 80),
            duration_ideal=SecondsRange(60, 75),
            reorder=False,
            protected_words=["não", "mas"],
            instructions="Prefira trechos de aplicação.",
            now=LATER,
        )

    with closing(connect(home)) as connection:
        shown = show_preset(connection, created["id"])

    assert shown == {
        **created,
        "name": "Culto da família",
        "levels": {**created["levels"], "allegory": "strict", "christological": "lenient"},
        "duration_allowed": {"min": 45, "max": 80},
        "duration_ideal": {"min": 60, "max": 75},
        "reorder": False,
        "protected_words": ["não", "mas"],
        "instructions": "Prefira trechos de aplicação.",
        "updated_at": LATER.isoformat(),
    }


def test_an_update_leaves_the_fields_not_given_as_they_were(
    connection: sqlite3.Connection,
) -> None:
    created = create_preset(connection, "Estudo bíblico")

    updated = update_preset(connection, created["id"], levels={"allegory": "strict"}, now=LATER)

    assert updated == {
        **created,
        "levels": {**created["levels"], "allegory": "strict"},
        "updated_at": LATER.isoformat(),
    }


def test_set_default_makes_the_preset_the_only_default(connection: sqlite3.Connection) -> None:
    created = create_preset(connection, "Estudo bíblico")

    set_default(connection, created["id"])

    defaults = [preset["id"] for preset in list_presets(connection) if preset["is_default"]]
    assert (defaults, default_preset(connection)["id"]) == ([created["id"]], created["id"])


def test_a_new_preset_copies_the_current_default_not_the_factory_one(
    connection: sqlite3.Connection,
) -> None:
    study = create_preset(connection, "Estudo bíblico")
    edited = update_preset(
        connection,
        study["id"],
        levels={"allegory": "strict"},
        duration_ideal=SecondsRange(60, 75),
        reorder=False,
        protected_words=["não"],
        instructions="Prefira trechos de aplicação.",
    )
    set_default(connection, study["id"])

    created = create_preset(connection, "Culto da família")

    assert editable(created) == editable(edited)


def test_a_new_preset_copies_the_preset_given_as_its_source(
    connection: sqlite3.Connection,
) -> None:
    study = create_preset(connection, "Estudo bíblico")
    edited = update_preset(connection, study["id"], reorder=False, instructions="Só aplicação.")

    created = create_preset(connection, "Culto da família", from_id=study["id"])

    assert (created["is_default"], editable(created)) == (False, editable(edited))


def test_deleting_the_default_preset_is_refused_and_deletes_nothing(
    connection: sqlite3.Connection,
) -> None:
    create_preset(connection, "Estudo bíblico")
    before = list_presets(connection)

    with pytest.raises(WordcutError) as raised:
        delete_preset(connection, factory_id_of(before))

    error = raised.value
    assert (error.code, error.exit_code, list_presets(connection)) == ("default_preset", 5, before)


def factory_id_of(listed: list[dict[str, Any]]) -> int:
    preset_id: int = next(preset["id"] for preset in listed if preset["is_default"])
    return preset_id


def test_a_preset_that_is_not_the_default_is_deleted(connection: sqlite3.Connection) -> None:
    created = create_preset(connection, "Estudo bíblico")

    delete_preset(connection, created["id"])

    assert [preset["name"] for preset in list_presets(connection)] == ["Padrão"]


@pytest.mark.parametrize(
    "act",
    [
        lambda connection: update_preset(connection, 999, reorder=False),
        lambda connection: set_default(connection, 999),
        lambda connection: delete_preset(connection, 999),
        lambda connection: create_preset(connection, "Estudo bíblico", from_id=999),
    ],
    ids=["update", "set-default", "delete", "create --from"],
)
def test_an_unknown_preset_is_not_found_in_every_action(
    connection: sqlite3.Connection, act: Any
) -> None:
    with pytest.raises(WordcutError) as raised:
        act(connection)

    assert (raised.value.code, raised.value.details) == ("not_found", {"preset_id": 999})


INSTRUCTIONS_LIMIT = 4000


@pytest.mark.parametrize(
    ("changes", "argument"),
    [
        (
            {},
            "name, level, duration_allowed, duration_ideal, reorder, protected_words, instructions",
        ),
        ({"levels": {"inexistent_criterion": "strict"}}, "level"),
        ({"levels": {"allegory": "rigoroso"}}, "level"),
        ({"name": "Padrão"}, "name"),
        ({"name": "   "}, "name"),
        ({"duration_allowed": SecondsRange(80, 45)}, "duration_allowed"),
        ({"duration_ideal": SecondsRange(70, 60)}, "duration_ideal"),
        ({"duration_ideal": SecondsRange(30, 60)}, "duration_ideal"),
        ({"duration_ideal": SecondsRange(60, 80)}, "duration_ideal"),
        ({"duration_allowed": SecondsRange(58, 75)}, "duration_allowed"),
        ({"duration_allowed": SecondsRange(40, 60)}, "duration_allowed"),
        ({"instructions": "x" * (INSTRUCTIONS_LIMIT + 1)}, "instructions"),
    ],
    ids=[
        "no field",
        "unknown criterion",
        "unknown level",
        "repeated name",
        "blank name",
        "allowed min above max",
        "ideal min above max",
        "ideal below allowed",
        "ideal above allowed",
        "allowed above stored ideal",
        "allowed below stored ideal",
        "instructions above the limit",
    ],
)
def test_an_invalid_update_is_refused_naming_the_argument_and_changes_nothing(
    connection: sqlite3.Connection, changes: dict[str, Any], argument: str
) -> None:
    created = create_preset(connection, "Estudo bíblico")

    with pytest.raises(WordcutError) as raised:
        update_preset(connection, created["id"], **changes)

    error = raised.value
    assert (error.code, error.details and error.details["argument"]) == (
        "invalid_argument",
        argument,
    )
    assert show_preset(connection, created["id"]) == created


def test_an_unknown_level_lists_the_valid_levels_without_repeating_the_typed_one(
    connection: sqlite3.Connection,
) -> None:
    with pytest.raises(WordcutError) as raised:
        update_preset(connection, factory_id(connection), levels={"allegory": "rigoroso"})

    error = raised.value
    assert (error.details, "rigoroso" in error.message) == (
        {"argument": "level", "choices": ["lenient", "moderate", "strict"]},
        False,
    )


@pytest.mark.parametrize(
    ("field", "value", "shown"),
    [
        ("duration_ideal", SecondsRange(60, 60), {"min": 60, "max": 60}),
        ("duration_allowed", SecondsRange(55, 65), {"min": 55, "max": 65}),
        ("instructions", "x" * INSTRUCTIONS_LIMIT, "x" * INSTRUCTIONS_LIMIT),
    ],
    ids=["ideal min equal to max", "allowed equal to the ideal", "instructions at the limit"],
)
def test_an_update_at_the_boundary_is_accepted(
    connection: sqlite3.Connection, field: str, value: Any, shown: Any
) -> None:
    created = create_preset(connection, "Estudo bíblico")

    updated = update_preset(connection, created["id"], **{field: value})

    assert updated[field] == shown


@pytest.mark.parametrize("name", ["Padrão", "  "], ids=["repeated", "blank"])
def test_a_preset_created_with_a_repeated_or_blank_name_is_refused(
    connection: sqlite3.Connection, name: str
) -> None:
    with pytest.raises(WordcutError) as raised:
        create_preset(connection, name)

    error = raised.value
    assert (error.code, error.details, len(list_presets(connection))) == (
        "invalid_argument",
        {"argument": "name"},
        1,
    )


def test_protected_words_are_kept_without_blanks_empties_or_repetitions(
    connection: sqlite3.Connection,
) -> None:
    updated = update_preset(
        connection,
        factory_id(connection),
        protected_words=parse_protected_words(" não, mas,, se, não "),
    )

    assert updated["protected_words"] == ["não", "mas", "se"]


def test_a_duration_is_read_as_min_dash_max_in_whole_seconds() -> None:
    assert parse_seconds_range(" 60-75 ", "duration_ideal") == SecondsRange(60, 75)


@pytest.mark.parametrize("text", ["60", "a-b", "-5-10", "60-", "60.5-70", ""])
def test_a_malformed_duration_is_refused_without_repeating_it(text: str) -> None:
    with pytest.raises(WordcutError) as raised:
        parse_seconds_range(text, "duration_ideal")

    error = raised.value
    assert (error.code, error.details, bool(text) and text in error.message) == (
        "invalid_argument",
        {"argument": "duration_ideal"},
        False,
    )


def test_a_level_is_read_as_criterion_equals_level() -> None:
    assert parse_level(" allegory=strict ") == ("allegory", "strict")


def test_a_level_without_the_equals_sign_is_refused_without_repeating_it() -> None:
    with pytest.raises(WordcutError) as raised:
        parse_level("alegoria")

    error = raised.value
    assert (error.code, error.details, "alegoria" in error.message) == (
        "invalid_argument",
        {"argument": "level"},
        False,
    )
