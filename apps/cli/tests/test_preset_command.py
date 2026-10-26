import io
import json
import sys
from pathlib import Path
from typing import Any

import pytest

from wordcut_cli import main

LEVELS = ["lenient", "moderate", "strict"]


@pytest.fixture(autouse=True)
def home(wordcut_home: Path) -> Path:
    return wordcut_home


def run_json(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, Any]:
    exit_code = main([*argv, "--json"])
    return exit_code, json.loads(capsys.readouterr().out)


def test_criteria_list_gives_the_eight_filters_and_three_values_with_id_name_type_and_level(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code, printed = run_json(["criteria", "list"], capsys)

    items = printed["items"]
    assert (
        exit_code,
        [item["type"] for item in items].count("filter"),
        [item["type"] for item in items].count("value"),
        {tuple(sorted(item)) for item in items},
        items[0],
    ) == (
        0,
        8,
        3,
        {("default_level", "id", "name", "type")},
        {"id": "triumphalism", "name": "Triunfalismo", "type": "filter", "default_level": "strict"},
    )


def test_preset_list_of_a_new_installation_gives_the_factory_default(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code, printed = run_json(["preset", "list"], capsys)

    [factory] = printed["items"]
    assert (exit_code, factory["name"], factory["is_default"], len(factory["levels"])) == (
        0,
        "Padrão",
        True,
        11,
    )


def test_preset_show_gives_the_preset_with_the_fields_of_the_entity(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code, shown = run_json(["preset", "show", str(factory_id(capsys))], capsys)

    assert (exit_code, sorted(shown)) == (
        0,
        [
            "created_at",
            "duration_allowed",
            "duration_ideal",
            "id",
            "instructions",
            "is_default",
            "levels",
            "name",
            "protected_words",
            "reorder",
            "updated_at",
        ],
    )


def factory_id(capsys: pytest.CaptureFixture[str]) -> int:
    _, printed = run_json(["preset", "list"], capsys)
    preset_id: int = next(item["id"] for item in printed["items"] if item["is_default"])
    return preset_id


def editable(preset: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in preset.items()
        if key not in ("id", "name", "is_default", "created_at", "updated_at")
    }


def test_preset_create_copies_the_default(capsys: pytest.CaptureFixture[str]) -> None:
    _, default = run_json(["preset", "show", str(factory_id(capsys))], capsys)

    exit_code, created = run_json(["preset", "create", "Estudo bíblico"], capsys)

    assert (exit_code, created["name"], created["is_default"], editable(created)) == (
        0,
        "Estudo bíblico",
        False,
        editable(default),
    )


def test_preset_create_from_copies_the_preset_given(capsys: pytest.CaptureFixture[str]) -> None:
    _, study = run_json(["preset", "create", "Estudo bíblico"], capsys)
    run_json(["preset", "update", str(study["id"]), "--no-reorder"], capsys)

    exit_code, created = run_json(
        ["preset", "create", "Culto da família", "--from", str(study["id"])], capsys
    )

    assert (exit_code, created["reorder"]) == (0, False)


def redirect_stdin(monkeypatch: pytest.MonkeyPatch, text: str) -> None:
    """Stdin as when a file is redirected to it (``< arquivo``): not a terminal."""
    monkeypatch.setattr(sys, "stdin", io.StringIO(text))


def test_preset_update_changes_the_fields_given_and_show_reflects_them(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _, created = run_json(["preset", "create", "Estudo bíblico"], capsys)
    redirect_stdin(monkeypatch, "Prefira trechos de aplicação.\n")

    exit_code = main(
        [
            "preset",
            "update",
            str(created["id"]),
            "--level",
            "allegory=strict",
            "--level",
            "christological=lenient",
            "--duration-ideal",
            "60-75",
            "--duration-allowed",
            "45-80",
            "--no-reorder",
            "--protected-words",
            "não,mas",
            "--name",
            "Culto da família",
            "--instructions-file",
            "-",
        ]
    )
    capsys.readouterr()

    _, shown = run_json(["preset", "show", str(created["id"])], capsys)
    assert (exit_code, editable(shown), shown["name"]) == (
        0,
        {
            **editable(created),
            "levels": {**created["levels"], "allegory": "strict", "christological": "lenient"},
            "duration_ideal": {"min": 60, "max": 75},
            "duration_allowed": {"min": 45, "max": 80},
            "reorder": False,
            "protected_words": ["não", "mas"],
            "instructions": "Prefira trechos de aplicação.",
        },
        "Culto da família",
    )


def test_a_level_repeated_for_the_same_criterion_keeps_the_last(
    capsys: pytest.CaptureFixture[str],
) -> None:
    preset_id = str(factory_id(capsys))

    run_json(
        [
            "preset",
            "update",
            preset_id,
            "--level",
            "allegory=lenient",
            "--level",
            "allegory=strict",
        ],
        capsys,
    )

    _, shown = run_json(["preset", "show", preset_id], capsys)
    assert shown["levels"]["allegory"] == "strict"


def test_preset_update_reads_the_instructions_from_a_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    instructions = tmp_path / "instrucoes.txt"
    instructions.write_text("Evite trechos de avisos.", encoding="utf-8")

    exit_code, updated = run_json(
        ["preset", "update", str(factory_id(capsys)), "--instructions-file", str(instructions)],
        capsys,
    )

    assert (exit_code, updated["instructions"]) == (0, "Evite trechos de avisos.")


def test_preset_update_with_a_missing_instructions_file_is_refused_without_naming_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    missing = tmp_path / "sk-ficticia-instrucoes.txt"

    main(["preset", "update", str(factory_id(capsys)), "--instructions-file", str(missing)])
    printed = capsys.readouterr()

    exit_code, error = run_json(
        ["preset", "update", str(factory_id(capsys)), "--instructions-file", str(missing)], capsys
    )
    assert (
        exit_code,
        error["error"]["code"],
        error["error"]["details"],
        "sk-ficticia" in printed.out + printed.err + json.dumps(error),
    ) == (2, "invalid_argument", {"argument": "instructions_file"}, False)


def test_instructions_above_the_limit_are_refused_naming_the_option_of_the_parser(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    redirect_stdin(monkeypatch, "x" * 4001)

    exit_code, printed = run_json(
        ["preset", "update", str(factory_id(capsys)), "--instructions-file", "-"], capsys
    )

    assert (exit_code, printed["error"]["code"], printed["error"]["details"]) == (
        2,
        "invalid_argument",
        {"argument": "instructions_file"},
    )


def test_preset_set_default_changes_the_default_preset_of_settings_show(
    capsys: pytest.CaptureFixture[str],
) -> None:
    _, created = run_json(["preset", "create", "Estudo bíblico"], capsys)

    exit_code, shown = run_json(["preset", "set-default", str(created["id"])], capsys)

    _, settings = run_json(["settings", "show"], capsys)
    assert (exit_code, shown["is_default"], settings["default_preset_id"]) == (
        0,
        True,
        created["id"],
    )


def test_preset_delete_of_the_default_is_a_default_preset_error_with_exit_5(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code, printed = run_json(["preset", "delete", str(factory_id(capsys))], capsys)

    assert (exit_code, printed["error"]["code"]) == (5, "default_preset")


def test_preset_delete_of_another_preset_deletes_it(capsys: pytest.CaptureFixture[str]) -> None:
    _, created = run_json(["preset", "create", "Estudo bíblico"], capsys)

    exit_code, deleted = run_json(["preset", "delete", str(created["id"])], capsys)

    _, listed = run_json(["preset", "list"], capsys)
    assert (exit_code, deleted, [item["name"] for item in listed["items"]]) == (
        0,
        {"id": created["id"], "deleted": True},
        ["Padrão"],
    )


TYPED = "sk-ficticia-0000abcd"
UPDATE_OPTIONS = (
    "name, level, duration_allowed, duration_ideal, reorder, protected_words, instructions_file"
)


@pytest.mark.parametrize(
    ("options", "details"),
    [
        (["--level", f"allegory={TYPED}"], {"argument": "level", "choices": LEVELS}),
        (["--level", f"{TYPED}=strict"], {"argument": "level"}),
        (["--level", TYPED], {"argument": "level"}),
        (["--duration-ideal", TYPED], {"argument": "duration_ideal"}),
        (["--duration-allowed", TYPED], {"argument": "duration_allowed"}),
        (["--duration-ideal", "70-60"], {"argument": "duration_ideal"}),
        (["--duration-allowed", "58-75"], {"argument": "duration_allowed"}),
        (["--name", "   "], {"argument": "name"}),
        ([], {"argument": UPDATE_OPTIONS}),
    ],
    ids=[
        "invalid level",
        "unknown criterion",
        "level without equals",
        "malformed ideal",
        "malformed allowed",
        "ideal min above max",
        "allowed no longer holds the ideal",
        "blank name",
        "no field",
    ],
)
@pytest.mark.parametrize("output", [["--json"], []], ids=["json", "text"])
def test_an_invalid_update_is_a_usage_error_naming_the_option_without_the_typed_value(
    options: list[str],
    details: dict[str, Any],
    output: list[str],
    capsys: pytest.CaptureFixture[str],
) -> None:
    preset_id = str(factory_id(capsys))

    exit_code = main(["preset", "update", preset_id, *options, *output])

    printed = capsys.readouterr()
    error = json.loads(printed.out)["error"] if output else None
    assert (
        exit_code,
        error and (error["code"], error["details"]),
        TYPED in printed.out + printed.err,
    ) == (2, ("invalid_argument", details) if output else None, False)


def test_renaming_to_the_name_of_another_preset_is_a_usage_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    _, created = run_json(["preset", "create", "Estudo bíblico"], capsys)

    exit_code, printed = run_json(
        ["preset", "update", str(created["id"]), "--name", "Padrão"], capsys
    )

    assert (exit_code, printed["error"]["details"], "Padrão" in printed["error"]["message"]) == (
        2,
        {"argument": "name"},
        False,
    )


@pytest.mark.parametrize(
    "argv",
    [
        ["preset", "show", "999"],
        ["preset", "update", "999", "--no-reorder"],
        ["preset", "set-default", "999"],
        ["preset", "delete", "999"],
        ["preset", "create", "Estudo bíblico", "--from", "999"],
    ],
    ids=["show", "update", "set-default", "delete", "create --from"],
)
def test_an_unknown_preset_id_is_not_found_with_exit_3(
    argv: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code, printed = run_json(argv, capsys)

    assert (exit_code, printed["error"]["code"]) == (3, "not_found")


def test_a_preset_id_that_is_not_a_number_is_refused_without_repeating_it(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["preset", "show", TYPED])

    printed = capsys.readouterr()
    assert (exit_code, TYPED in printed.out + printed.err) == (2, False)


@pytest.mark.parametrize(
    "argv",
    [
        ["criteria", "list"],
        ["preset", "list"],
        ["preset", "show"],
        ["preset", "create"],
        ["preset", "update"],
        ["preset", "set-default"],
        ["preset", "delete"],
    ],
    ids=lambda argv: " ".join(argv),
)
def test_each_criteria_and_preset_action_help_says_it_is_for_the_administrator_with_an_example(
    argv: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main([*argv, "--help"])

    help_text = capsys.readouterr().out
    assert (exit_code, "administrador" in help_text, f"wordcut {' '.join(argv)} " in help_text) == (
        0,
        True,
        True,
    )


# docs/prototype/wordcut.html (LEVELS_F, LEVELS_V) and an anchor of texts/base.md: none of
# the prompt text may reach an output (constitution §I).
PROMPT_TEXTS = (
    "Exclui só quando é evidente",
    "Exclui quando é provável",
    "Exclui na menor suspeita",
    "Basta tocar no tema",
    "O valor aparece com clareza",
    "O valor é o centro do corte",
    "Stone-Campbell",
)


@pytest.mark.parametrize(
    "argv",
    [
        ["criteria", "list"],
        ["preset", "list"],
        ["preset", "show", "1"],
        ["preset", "create", "Estudo bíblico"],
        ["preset", "update", "1", "--level", "allegory=strict"],
        ["preset", "update", "1", "--level", "allegory=rigoroso"],
        ["preset", "set-default", "1"],
        ["preset", "delete", "1"],
        ["preset", "show", "999"],
    ],
    ids=lambda argv: " ".join(argv),
)
@pytest.mark.parametrize("output", [["--json"], []], ids=["json", "text"])
def test_no_criteria_or_preset_output_carries_prompt_text(
    argv: list[str], output: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    main([*argv, *output])

    printed = capsys.readouterr()
    assert [text for text in PROMPT_TEXTS if text in printed.out + printed.err] == []
