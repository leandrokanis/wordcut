"""The team: list the members, let an e-mail in, change a role and take a member off; only
an administrator may (docs/api.md).

The e-mail goes in the body, never in the path: proxies log the path of every request, and
an e-mail is personal data (ADR-0021).
"""

from __future__ import annotations

from contextlib import closing
from typing import Any

from fastapi import APIRouter, Depends

from wordcut import db
from wordcut.service.members import add_member, list_members, remove_member, set_role
from wordcut_api import deps
from wordcut_api.auth import require
from wordcut_api.bodies import Body

router = APIRouter(prefix="/api/members", dependencies=[Depends(require("admin"))])


class MemberRole(Body):
    """A member and the role to give it; the role is a plain string, so the service names
    the choices."""

    email: str
    role: str


class Email(Body):
    email: str


@router.get("")
def listing() -> dict[str, Any]:
    with closing(db.connect(deps.home())) as connection:
        return {"items": list_members(connection)}


@router.post("", status_code=201)
def add(body: MemberRole) -> dict[str, Any]:
    with closing(db.connect(deps.home())) as connection:
        return add_member(connection, body.email, body.role)


@router.post("/set-role")
def change_role(body: MemberRole) -> dict[str, Any]:
    with closing(db.connect(deps.home())) as connection:
        return set_role(connection, body.email, body.role)


@router.post("/remove")
def remove(body: Email) -> dict[str, Any]:
    with closing(db.connect(deps.home())) as connection:
        return remove_member(connection, body.email)
