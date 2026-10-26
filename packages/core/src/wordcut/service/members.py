"""The team: e-mails allowed in and the role of each one (docs/cli.md §12, feature 1.2.a).

A member is identified by the e-mail, kept in lower case without surrounding spaces, the way
every operation here looks it up. Of personal data, only the e-mail is kept (LGPD).
"""

from __future__ import annotations

import re
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from typing import Any

from wordcut.db import members
from wordcut.db.members import MemberRow
from wordcut.errors import WordcutError

ADMIN = "admin"
ROLES = ("assistant", ADMIN)
# A local part, "@" and a domain with a dot; conservative: Cloudflare Access is what really
# checks the address.
EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


def list_members(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    """Every member, ordered by e-mail."""
    return [_shown(row) for row in members.all_members(connection)]


def add_member(
    connection: sqlite3.Connection, email: str, role: str, now: datetime | None = None
) -> dict[str, Any]:
    """Allow ``email`` in with ``role``. ``now`` defaults to the clock."""
    address = _valid_email(email)
    _check_role(role)
    with _writing(connection):
        if members.by_email(connection, address) is not None:
            raise WordcutError(
                "invalid_argument", "Esse e-mail já está na equipe.", {"argument": "email"}
            )
        row = members.insert(connection, address, role, _now(now))
    return _shown(row)


def set_role(
    connection: sqlite3.Connection, email: str, role: str, now: datetime | None = None
) -> dict[str, Any]:
    """Give the member ``role`` and show the member; the role it already has changes nothing."""
    address = _valid_email(email)
    _check_role(role)
    with _writing(connection):
        row = _existing(connection, address)
        if row.role == role:
            return _shown(row)
        # With two roles, a change of an admin's role is a demotion.
        _check_not_last_admin(connection, row)
        members.update_role(connection, address, role, _now(now))
    return _shown(_existing(connection, address))


def remove_member(connection: sqlite3.Connection, email: str) -> dict[str, Any]:
    """Take the member off the team."""
    address = _valid_email(email)
    with _writing(connection):
        _check_not_last_admin(connection, _existing(connection, address))
        members.delete(connection, address)
    return {"email": address, "removed": True}


def role_of(connection: sqlite3.Connection, email: str) -> str | None:
    """The role of ``email``, the address Cloudflare Access verified, for the API.

    ``None`` when the e-mail is not in the team, a malformed one included: it never raises.
    """
    row = members.by_email(connection, _normalized(email))
    return None if row is None else row.role


@contextmanager
def _writing(connection: sqlite3.Connection) -> Iterator[None]:
    """A write transaction taken before the first read, committed at the end.

    The CLI and the API write to the same file (ADR-0005): with the transaction SQLite opens
    only at the first write, two admins could each be demoted after reading that the other
    is still an admin. ``BEGIN IMMEDIATE`` makes the check of the last admin and the write
    see the same team.
    """
    with connection:
        connection.execute("BEGIN IMMEDIATE")
        yield


def _normalized(email: str) -> str:
    return email.strip().lower()


def _valid_email(email: str) -> str:
    # ADR-0015: the e-mail is personal data and is never repeated in an error.
    normalized = _normalized(email)
    if EMAIL.fullmatch(normalized) is None:
        raise WordcutError(
            "invalid_argument",
            "E-mail inválido; escreva como assistente@exemplo.org.",
            {"argument": "email"},
        )
    return normalized


def _check_role(role: str) -> None:
    if role not in ROLES:
        raise WordcutError(
            "invalid_argument",
            f"Papel inválido; use um de: {', '.join(ROLES)}.",
            {"argument": "role", "choices": list(ROLES)},
        )


def _check_not_last_admin(connection: sqlite3.Connection, row: MemberRow) -> None:
    """FR-003: once the first admin exists, the team never stays without one."""
    if row.role == ADMIN and members.count_with_role(connection, ADMIN) == 1:
        raise WordcutError(
            "last_admin",
            "A equipe precisa de ao menos um administrador; torne outro membro administrador"
            " antes.",
        )


def _existing(connection: sqlite3.Connection, email: str) -> MemberRow:
    row = members.by_email(connection, email)
    if row is None:
        raise WordcutError("not_found", "Esse e-mail não está na equipe.", {"argument": "email"})
    return row


def _now(now: datetime | None) -> datetime:
    return now or datetime.now().astimezone()


def _shown(row: MemberRow) -> dict[str, Any]:
    return {
        "email": row.email,
        "role": row.role,
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
    }
