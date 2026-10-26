import sqlite3
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from wordcut.db import connect
from wordcut.errors import WordcutError
from wordcut.home import Home
from wordcut.service.members import add_member, list_members, remove_member, role_of, set_role

BRASILIA = timezone(timedelta(hours=-3))
ADDED = datetime(2026, 10, 26, 19, 40, tzinfo=BRASILIA)
CHANGED = ADDED + timedelta(days=1)


@pytest.fixture
def connection(wordcut_home: Path) -> Iterator[sqlite3.Connection]:
    with closing(connect(Home(wordcut_home))) as opened:
        yield opened


def test_an_added_member_is_listed_with_the_email_in_lower_case_the_role_and_the_dates(
    connection: sqlite3.Connection,
) -> None:
    add_member(connection, "  Assistente@Exemplo.ORG ", "assistant", now=ADDED)

    assert list_members(connection) == [
        {
            "email": "assistente@exemplo.org",
            "role": "assistant",
            "created_at": "2026-10-26T19:40:00-03:00",
            "updated_at": "2026-10-26T19:40:00-03:00",
        }
    ]


def test_the_members_table_keeps_only_the_email_the_role_and_the_dates(
    connection: sqlite3.Connection,
) -> None:
    columns = [row[1] for row in connection.execute("PRAGMA table_info(members)")]

    assert columns == ["email", "role", "created_at", "updated_at"]


def test_members_are_listed_by_email_whatever_the_order_they_were_added(
    connection: sqlite3.Connection,
) -> None:
    for email in ("editor2@exemplo.org", "admin@exemplo.org", "assistente@exemplo.org"):
        add_member(connection, email, "assistant", now=ADDED)

    assert [member["email"] for member in list_members(connection)] == [
        "admin@exemplo.org",
        "assistente@exemplo.org",
        "editor2@exemplo.org",
    ]


@pytest.mark.parametrize(
    "email",
    [
        "",
        "   ",
        "admin",
        "admin@",
        "@exemplo.org",
        "admin@exemplo",
        "ad min@exemplo.org",
        "admin@@exemplo.org",
        "admin@exemplo@exemplo.org",
    ],
)
def test_an_invalid_email_is_an_invalid_argument_and_nothing_is_added(
    connection: sqlite3.Connection, email: str
) -> None:
    with pytest.raises(WordcutError) as raised:
        add_member(connection, email, "assistant", now=ADDED)

    assert (raised.value.code, raised.value.details, list_members(connection)) == (
        "invalid_argument",
        {"argument": "email"},
        [],
    )


def test_an_email_already_in_the_team_in_another_case_is_an_invalid_argument_not_a_duplicate(
    connection: sqlite3.Connection,
) -> None:
    add_member(connection, "assistente@exemplo.org", "assistant", now=ADDED)

    with pytest.raises(WordcutError) as raised:
        add_member(connection, " ASSISTENTE@exemplo.org", "admin", now=ADDED)

    assert (raised.value.code, raised.value.details, len(list_members(connection))) == (
        "invalid_argument",
        {"argument": "email"},
        1,
    )


ROLE_ERROR = {"argument": "role", "choices": ["assistant", "admin"]}


@pytest.mark.parametrize("role", ["owner", "Admin", ""])
def test_adding_with_a_role_other_than_assistant_or_admin_is_an_invalid_argument(
    connection: sqlite3.Connection, role: str
) -> None:
    with pytest.raises(WordcutError) as raised:
        add_member(connection, "admin@exemplo.org", role, now=ADDED)

    assert (raised.value.code, raised.value.details, list_members(connection)) == (
        "invalid_argument",
        ROLE_ERROR,
        [],
    )


def test_set_role_finds_the_member_in_another_case_and_changes_the_role_and_updated_at_only(
    connection: sqlite3.Connection,
) -> None:
    add_member(connection, "assistente@exemplo.org", "assistant", now=ADDED)

    changed = set_role(connection, " Assistente@EXEMPLO.org", "admin", now=CHANGED)

    assert (
        [changed]
        == list_members(connection)
        == [
            {
                "email": "assistente@exemplo.org",
                "role": "admin",
                "created_at": "2026-10-26T19:40:00-03:00",
                "updated_at": "2026-10-27T19:40:00-03:00",
            }
        ]
    )


def test_set_role_of_an_email_not_in_the_team_is_not_found(
    connection: sqlite3.Connection,
) -> None:
    add_member(connection, "admin@exemplo.org", "admin", now=ADDED)

    with pytest.raises(WordcutError) as raised:
        set_role(connection, "editor2@exemplo.org", "admin", now=CHANGED)

    assert (raised.value.code, raised.value.details) == ("not_found", {"argument": "email"})


def test_set_role_to_a_role_other_than_assistant_or_admin_is_an_invalid_argument(
    connection: sqlite3.Connection,
) -> None:
    add_member(connection, "admin@exemplo.org", "admin", now=ADDED)

    with pytest.raises(WordcutError) as raised:
        set_role(connection, "admin@exemplo.org", "owner", now=CHANGED)

    assert (raised.value.code, raised.value.details, list_members(connection)[0]["role"]) == (
        "invalid_argument",
        ROLE_ERROR,
        "admin",
    )


def test_removing_a_member_in_another_case_takes_it_off_the_list_even_with_no_admin(
    connection: sqlite3.Connection,
) -> None:
    add_member(connection, "assistente@exemplo.org", "assistant", now=ADDED)
    add_member(connection, "editor2@exemplo.org", "assistant", now=ADDED)

    removed = remove_member(connection, "Assistente@Exemplo.org ")

    assert (removed, list_members(connection)) == (
        {"email": "assistente@exemplo.org", "removed": True},
        [
            {
                "email": "editor2@exemplo.org",
                "role": "assistant",
                "created_at": "2026-10-26T19:40:00-03:00",
                "updated_at": "2026-10-26T19:40:00-03:00",
            }
        ],
    )


def test_removing_an_email_not_in_the_team_is_not_found(
    connection: sqlite3.Connection,
) -> None:
    with pytest.raises(WordcutError) as raised:
        remove_member(connection, "editor2@exemplo.org")

    assert (raised.value.code, raised.value.details) == ("not_found", {"argument": "email"})


@pytest.mark.parametrize(
    "others", [[], ["assistente@exemplo.org"]], ids=["alone", "with_assistant"]
)
def test_removing_the_only_admin_is_last_admin_and_changes_nothing(
    connection: sqlite3.Connection, others: list[str]
) -> None:
    add_member(connection, "admin@exemplo.org", "admin", now=ADDED)
    for email in others:
        add_member(connection, email, "assistant", now=ADDED)
    before = list_members(connection)

    with pytest.raises(WordcutError) as raised:
        remove_member(connection, "admin@exemplo.org")

    assert (raised.value.code, raised.value.exit_code, list_members(connection)) == (
        "last_admin",
        5,
        before,
    )


@pytest.mark.parametrize(
    "others", [[], ["assistente@exemplo.org"]], ids=["alone", "with_assistant"]
)
def test_demoting_the_only_admin_is_last_admin_and_changes_nothing(
    connection: sqlite3.Connection, others: list[str]
) -> None:
    add_member(connection, "admin@exemplo.org", "admin", now=ADDED)
    for email in others:
        add_member(connection, email, "assistant", now=ADDED)
    before = list_members(connection)

    with pytest.raises(WordcutError) as raised:
        set_role(connection, "admin@exemplo.org", "assistant", now=CHANGED)

    assert (raised.value.code, raised.value.exit_code, list_members(connection)) == (
        "last_admin",
        5,
        before,
    )


def demote(connection: sqlite3.Connection, email: str) -> None:
    set_role(connection, email, "assistant", now=CHANGED)


def remove(connection: sqlite3.Connection, email: str) -> None:
    remove_member(connection, email)


@pytest.mark.parametrize("operation", [demote, remove])
def test_with_two_admins_either_one_can_be_demoted_or_removed(
    connection: sqlite3.Connection, operation: Callable[[sqlite3.Connection, str], None]
) -> None:
    add_member(connection, "admin@exemplo.org", "admin", now=ADDED)
    add_member(connection, "editor2@exemplo.org", "admin", now=ADDED)

    operation(connection, "editor2@exemplo.org")

    assert [m["email"] for m in list_members(connection) if m["role"] == "admin"] == [
        "admin@exemplo.org"
    ]


@pytest.mark.parametrize(
    ("email", "role"),
    [("admin@exemplo.org", "admin"), ("assistente@exemplo.org", "assistant")],
)
def test_set_role_to_the_role_the_member_has_succeeds_and_changes_nothing(
    connection: sqlite3.Connection, email: str, role: str
) -> None:
    add_member(connection, "admin@exemplo.org", "admin", now=ADDED)
    add_member(connection, "assistente@exemplo.org", "assistant", now=ADDED)
    before = list_members(connection)

    shown = set_role(connection, email, role, now=CHANGED)

    assert (shown in before, list_members(connection)) == (True, before)


def add_twice(connection: sqlite3.Connection) -> None:
    add_member(connection, "editor2@exemplo.org", "assistant", now=ADDED)
    add_member(connection, "Editor2@exemplo.org", "assistant", now=ADDED)


def add_invalid(connection: sqlite3.Connection) -> None:
    add_member(connection, "editor2@exemplo", "assistant", now=ADDED)


def set_role_of_unknown(connection: sqlite3.Connection) -> None:
    set_role(connection, "Editor2@exemplo.org", "admin", now=CHANGED)


def remove_unknown(connection: sqlite3.Connection) -> None:
    remove_member(connection, "Editor2@exemplo.org")


def remove_last_admin(connection: sqlite3.Connection) -> None:
    add_member(connection, "editor2@exemplo.org", "admin", now=ADDED)
    remove_member(connection, "Editor2@exemplo.org")


def demote_last_admin(connection: sqlite3.Connection) -> None:
    add_member(connection, "editor2@exemplo.org", "admin", now=ADDED)
    set_role(connection, "Editor2@exemplo.org", "assistant", now=CHANGED)


@pytest.mark.parametrize(
    "failing",
    [
        add_twice,
        add_invalid,
        set_role_of_unknown,
        remove_unknown,
        remove_last_admin,
        demote_last_admin,
    ],
)
def test_no_error_repeats_the_email(
    connection: sqlite3.Connection, failing: Callable[[sqlite3.Connection], None]
) -> None:
    with pytest.raises(WordcutError) as raised:
        failing(connection)

    assert "editor2" not in str(raised.value.to_dict()).lower()


def test_role_of_gives_the_role_of_the_email_in_any_case(
    connection: sqlite3.Connection,
) -> None:
    add_member(connection, "admin@exemplo.org", "admin", now=ADDED)
    add_member(connection, "assistente@exemplo.org", "assistant", now=ADDED)

    assert (
        role_of(connection, " ADMIN@exemplo.org"),
        role_of(connection, "Assistente@Exemplo.Org"),
    ) == ("admin", "assistant")


@pytest.mark.parametrize("email", ["editor2@exemplo.org", "", "   ", "admin", "admin@@exemplo.org"])
def test_role_of_an_email_not_in_the_team_or_malformed_is_none(
    connection: sqlite3.Connection, email: str
) -> None:
    add_member(connection, "admin@exemplo.org", "admin", now=ADDED)

    assert role_of(connection, email) is None


def admins(connection: sqlite3.Connection) -> list[str]:
    return [member["email"] for member in list_members(connection) if member["role"] == "admin"]


def test_two_admins_demoted_at_the_same_time_from_two_connections_leave_one_admin(
    connection: sqlite3.Connection, wordcut_home: Path
) -> None:
    add_member(connection, "admin@exemplo.org", "admin", now=ADDED)
    add_member(connection, "editor2@exemplo.org", "admin", now=ADDED)
    # The API, in another connection, is demoting the other admin: its check already passed
    # and its write is not committed yet.
    api = sqlite3.connect(Home(wordcut_home).database, isolation_level=None)
    api.execute("BEGIN IMMEDIATE")
    api.execute("UPDATE members SET role = 'assistant' WHERE email = 'editor2@exemplo.org'")
    codes: list[str | None] = []

    def demote_from_the_cli() -> None:
        with closing(connect(Home(wordcut_home))) as cli:
            try:
                set_role(cli, "admin@exemplo.org", "assistant", now=CHANGED)
                codes.append(None)
            except WordcutError as error:
                codes.append(error.code)

    cli_thread = threading.Thread(target=demote_from_the_cli)
    cli_thread.start()
    time.sleep(0.5)
    api.execute("COMMIT")
    api.close()
    cli_thread.join()

    assert (codes, admins(connection)) == (["last_admin"], ["admin@exemplo.org"])
