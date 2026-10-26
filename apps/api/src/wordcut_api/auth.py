"""FastAPI dependencies that tell who is asking and what the member may do (feature 1.2.a).

A route takes ``CurrentMember`` to require any member of the team, or
``Depends(require("admin"))`` to require an administrator.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from contextlib import closing
from dataclasses import dataclass
from typing import Annotated, Protocol

from fastapi import Depends, Request

from wordcut import db
from wordcut.errors import WordcutError
from wordcut.home import Home
from wordcut.service.members import ADMIN, role_of
from wordcut_api.identity import AccessKeys, KeySource, unauthenticated, verify
from wordcut_api.settings import ApiSettings

logger = logging.getLogger(__name__)

# Cloudflare Access sends the signed token in this header (ADR-0009).
TOKEN_HEADER = "Cf-Access-Jwt-Assertion"


@dataclass(frozen=True)
class Member:
    email: str
    role: str


class Identification(Protocol):
    """Finds the verified e-mail of a request; ``unauthenticated`` when there is none."""

    def email(self, headers: Mapping[str, str]) -> str: ...


@dataclass(frozen=True)
class AccessIdentification:
    """The e-mail of the token Cloudflare Access signed for the application."""

    team_domain: str
    audience: str
    keys: KeySource

    def email(self, headers: Mapping[str, str]) -> str:
        token = headers.get(TOKEN_HEADER)
        if token is None:
            raise unauthenticated()
        return verify(token, keys=self.keys, team_domain=self.team_domain, audience=self.audience)


@dataclass(frozen=True)
class DevIdentification:
    """A fixed e-mail for local development, without Access (ADR-0009)."""

    dev_email: str

    def email(self, headers: Mapping[str, str]) -> str:
        return self.dev_email


class NoIdentification:
    """Neither Access nor a development e-mail: nobody is identified."""

    def email(self, headers: Mapping[str, str]) -> str:
        raise unauthenticated()


def identification(settings: ApiSettings, keys: KeySource | None) -> Identification:
    """How the API configured by ``settings`` identifies who is asking.

    Access configured by half refuses to start: it must not fall back to the development
    e-mail nor accept a token without checking its audience.
    """
    if (settings.access_team_domain is None) != (settings.access_audience is None):
        raise WordcutError(
            "invalid_argument", "Configure WORDCUT_ACCESS_TEAM_DOMAIN e WORDCUT_ACCESS_AUD juntos."
        )
    if settings.access_team_domain is not None and settings.access_audience is not None:
        return AccessIdentification(
            settings.access_team_domain,
            settings.access_audience,
            keys or AccessKeys(settings.access_team_domain),
        )
    if settings.dev_email is None:
        return NoIdentification()
    logger.warning(
        "WORDCUT_DEV_EMAIL ativo: toda requisição vale como o e-mail fixo, sem Cloudflare"
        " Access. Nunca use em produção."
    )
    return DevIdentification(settings.dev_email)


def current_member(request: Request) -> Member:
    """The member asking; ``unauthenticated`` or ``forbidden`` otherwise."""
    identification: Identification = request.app.state.identification
    email = identification.email(request.headers)
    # One connection per request, opened and closed in this call: FastAPI may run a route and
    # its dependencies in different threads, and a SQLite connection stays in its own.
    with closing(db.connect(Home.from_environment())) as connection:
        role = role_of(connection, email)
    if role is None:
        # ADR-0015: the e-mail is personal data and is never repeated in an error.
        raise WordcutError("forbidden", "Este e-mail não está na equipe.")
    return Member(email, role)


CurrentMember = Annotated[Member, Depends(current_member)]


def require(role: str) -> Callable[[Member], Member]:
    """A dependency that lets through a member with ``role``; an admin may do everything."""

    def member_with_role(member: CurrentMember) -> Member:
        if member.role not in (role, ADMIN):
            raise WordcutError("forbidden", "Seu papel não permite esta ação.")
        return member

    return member_with_role
