"""The configuration of the API, read from the environment."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class ApiSettings:
    """How the API identifies who is asking (ADR-0009).

    ``access_team_domain`` is the host of the Cloudflare Access team, such as
    ``equipe.cloudflareaccess.com``, and ``access_audience`` the AUD tag of the application.
    """

    access_team_domain: str | None = None
    access_audience: str | None = None
    dev_email: str | None = None

    @classmethod
    def from_environment(cls, environ: Mapping[str, str] = os.environ) -> ApiSettings:
        """Read ``WORDCUT_ACCESS_TEAM_DOMAIN``, ``WORDCUT_ACCESS_AUD`` and ``WORDCUT_DEV_EMAIL``.

        A variable set to an empty value counts as not set.
        """
        return cls(
            access_team_domain=environ.get("WORDCUT_ACCESS_TEAM_DOMAIN") or None,
            access_audience=environ.get("WORDCUT_ACCESS_AUD") or None,
            dev_email=environ.get("WORDCUT_DEV_EMAIL") or None,
        )
