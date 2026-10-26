import json
from pathlib import Path
from typing import Any

import pytest

from wordcut_cli import main


@pytest.fixture(autouse=True)
def home(wordcut_home: Path) -> Path:
    return wordcut_home


def run_json(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, Any]:
    exit_code = main([*argv, "--json"])
    return exit_code, json.loads(capsys.readouterr().out)


def test_an_added_member_is_listed_with_the_email_in_lower_case_the_role_and_the_date(
    capsys: pytest.CaptureFixture[str],
) -> None:
    added_code, added = run_json(
        ["member", "add", "Assistente@Exemplo.org", "--role", "assistant"], capsys
    )
    listed_code, listed = run_json(["member", "list"], capsys)

    assert (added_code, listed_code, listed) == (0, 0, {"items": [added]})
    assert (added["email"], added["role"], sorted(added)) == (
        "assistente@exemplo.org",
        "assistant",
        ["created_at", "email", "role", "updated_at"],
    )


def test_set_role_changes_the_role_and_remove_takes_the_member_off_the_list(
    capsys: pytest.CaptureFixture[str],
) -> None:
    run_json(["member", "add", "admin@exemplo.org", "--role", "admin"], capsys)
    run_json(["member", "add", "assistente@exemplo.org", "--role", "assistant"], capsys)

    changed_code, changed = run_json(
        ["member", "set-role", "Assistente@exemplo.org", "admin"], capsys
    )
    removed_code, removed = run_json(["member", "remove", "ASSISTENTE@exemplo.org"], capsys)
    _, listed = run_json(["member", "list"], capsys)

    assert (
        changed_code,
        changed["role"],
        removed_code,
        removed,
        [item["email"] for item in listed["items"]],
    ) == (
        0,
        "admin",
        0,
        {"email": "assistente@exemplo.org", "removed": True},
        ["admin@exemplo.org"],
    )


@pytest.mark.parametrize("action", [[], ["list"], ["add"], ["set-role"], ["remove"]])
def test_the_help_of_the_group_and_of_each_action_says_administrator_with_an_example(
    action: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(["member", *action, "--help"])

    help_text = capsys.readouterr().out
    example = help_text.partition("Exemplo:")[2]
    assert (
        exit_code,
        "— administrador" in " ".join(help_text.split()),
        example.strip().startswith(" ".join(["wordcut", "member", *action])),
        "@exemplo.org" in example or action == ["list"],
    ) == (0, True, True, True)


@pytest.mark.parametrize(
    "action",
    [["remove", "Admin@exemplo.org"], ["set-role", "Admin@exemplo.org", "assistant"]],
    ids=["remove", "set-role"],
)
def test_removing_or_demoting_the_only_admin_is_last_admin_with_exit_code_5(
    action: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    run_json(["member", "add", "admin@exemplo.org", "--role", "admin"], capsys)
    run_json(["member", "add", "assistente@exemplo.org", "--role", "assistant"], capsys)

    exit_code, printed = run_json(["member", *action], capsys)

    assert (exit_code, printed["error"]["code"]) == (5, "last_admin")


ROLE_CHOICES = ["assistant", "admin"]


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (["add", "editor2@exemplo", "--role", "admin"], (2, "invalid_argument", None)),
        (["add", "Admin@exemplo.org", "--role", "admin"], (2, "invalid_argument", None)),
        (["add", "editor2@exemplo.org", "--role", "owner"], (2, "invalid_argument", ROLE_CHOICES)),
        (["add", "editor2@exemplo.org"], (2, "invalid_argument", None)),
        (["set-role", "admin@exemplo.org", "owner"], (2, "invalid_argument", ROLE_CHOICES)),
        (["set-role", "editor2@exemplo.org", "admin"], (3, "not_found", None)),
        (["remove", "editor2@exemplo.org"], (3, "not_found", None)),
    ],
    ids=[
        "add-invalid-email",
        "add-repeated",
        "add-invalid-role",
        "add-without-role",
        "set-role-invalid-role",
        "set-role-unknown",
        "remove-unknown",
    ],
)
def test_wrong_member_arguments_are_invalid_or_not_found(
    argv: list[str], expected: tuple[int, str, list[str] | None], capsys: pytest.CaptureFixture[str]
) -> None:
    run_json(["member", "add", "admin@exemplo.org", "--role", "admin"], capsys)

    exit_code, printed = run_json(["member", *argv], capsys)

    error = printed["error"]
    assert (exit_code, error["code"], error.get("details", {}).get("choices")) == expected


@pytest.mark.parametrize("output", [["--json"], []], ids=["json", "text"])
@pytest.mark.parametrize(
    "argv",
    [
        ["add", "editor2@exemplo", "--role", "admin"],
        ["add", "editor2@exemplo.org", "--role", "owner"],
        ["set-role", "editor2@exemplo.org", "admin"],
        ["remove", "editor2@exemplo.org"],
        ["remove", "Admin@exemplo.org"],
    ],
    ids=["invalid", "invalid-role", "set-role-unknown", "remove-unknown", "last-admin"],
)
def test_no_error_output_repeats_the_email_typed(
    argv: list[str], output: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    run_json(["member", "add", "admin@exemplo.org", "--role", "admin"], capsys)

    exit_code = main(["member", *argv, *output])

    printed = capsys.readouterr()
    typed = argv[1].lower()
    assert (exit_code != 0, typed in (printed.out + printed.err).lower()) == (True, False)


def test_an_empty_team_lists_no_items_and_says_so_in_text(
    capsys: pytest.CaptureFixture[str],
) -> None:
    json_code, printed = run_json(["member", "list"], capsys)
    text_code = main(["member", "list"])

    text = capsys.readouterr()
    assert (json_code, printed, text_code, text.out.strip() != "", text.err) == (
        0,
        {"items": []},
        0,
        True,
        "",
    )


def test_json_works_before_the_group_too(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["--json", "member", "add", "admin@exemplo.org", "--role", "admin"])

    assert (exit_code, json.loads(capsys.readouterr().out)["role"]) == (0, "admin")


def test_without_json_the_result_is_text_on_stdout_and_an_error_only_on_stderr(
    capsys: pytest.CaptureFixture[str],
) -> None:
    added_code = main(["member", "add", "admin@exemplo.org", "--role", "admin"])
    added = capsys.readouterr()
    failed_code = main(["member", "remove", "admin@exemplo.org"])
    failed = capsys.readouterr()

    assert (
        added_code,
        "admin@exemplo.org" in added.out,
        added.err,
        failed_code,
        failed.out,
        failed.err != "",
    ) == (0, True, "", 5, "", True)
