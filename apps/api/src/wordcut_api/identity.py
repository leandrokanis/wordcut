"""Who is asking: the e-mail in the Cloudflare Access token (ADR-0009).

Access signs a JWT with the keys of the team and sends it in ``Cf-Access-Jwt-Assertion``;
the API trusts only the e-mail of a token that this module verified.
"""

from __future__ import annotations

import json
import time
import urllib.request
from collections.abc import Callable
from typing import Any, Protocol

import jwt
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey

from wordcut.errors import WordcutError
from wordcut.network import refuse_when_forbidden

# Cloudflare Access signs its tokens with RS256 only; accepting any other "alg" lets a token
# be forged with the public key as an HMAC secret, or unsigned.
ALGORITHM = "RS256"
REQUIRED_CLAIMS = ["aud", "exp", "iss"]
CERTS_PATH = "/cdn-cgi/access/certs"
CACHE_SECONDS = 600
FETCH_TIMEOUT_SECONDS = 10

# Fetches the JSON of a URL; raises ``network_error`` when it cannot.
Fetch = Callable[[str], dict[str, Any]]


def fetch_json(url: str) -> dict[str, Any]:
    """The JSON at ``url``, over the network; refused while the network is forbidden."""
    refuse_when_forbidden("Cloudflare Access")
    try:
        with urllib.request.urlopen(url, timeout=FETCH_TIMEOUT_SECONDS) as response:
            document: dict[str, Any] = json.load(response)
    except (OSError, ValueError):
        raise _keys_unavailable() from None
    return document


class KeySource(Protocol):
    """The public keys of the Access team, by key id (``kid``)."""

    def public_key(self, kid: str) -> RSAPublicKey | None:
        """The key ``kid`` names, or ``None`` when the team has no such key."""


class AccessKeys:
    """The public keys of the team ``team_domain``, fetched from Access and kept for 10 min.

    ``fetch`` reaches the certs endpoint and ``clock`` gives seconds; tests pass doubles.
    """

    def __init__(
        self,
        team_domain: str,
        *,
        fetch: Fetch = fetch_json,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._url = f"https://{team_domain}{CERTS_PATH}"
        self._fetch = fetch
        self._clock = clock
        self._keys: dict[str, RSAPublicKey] = {}
        self._fetched_at: float | None = None

    def public_key(self, kid: str) -> RSAPublicKey | None:
        """The key ``kid`` names; a key id not seen yet fetches again, to follow a rotation."""
        if self._expired() or kid not in self._keys:
            self._refresh()
        return self._keys.get(kid)

    def _expired(self) -> bool:
        return self._fetched_at is None or self._clock() - self._fetched_at >= CACHE_SECONDS

    def _refresh(self) -> None:
        try:
            jwks = jwt.PyJWKSet.from_dict(self._fetch(self._url))
        except jwt.PyJWKSetError:
            raise _keys_unavailable() from None
        self._keys = {
            jwk.key_id: jwk.key
            for jwk in jwks.keys
            if jwk.key_id is not None and isinstance(jwk.key, RSAPublicKey)
        }
        self._fetched_at = self._clock()


def verify(token: str, *, keys: KeySource, team_domain: str, audience: str) -> str:
    """The e-mail of ``token``, a JWT that Access signed for ``audience``.

    Raises ``unauthenticated`` for any token Access did not sign for this team and audience,
    never repeating the token.
    """
    try:
        key = keys.public_key(_key_id(token))
        if key is None:
            raise unauthenticated()
        claims = jwt.decode(
            token,
            key,
            algorithms=[ALGORITHM],
            audience=audience,
            issuer=f"https://{team_domain}",
            options={"require": REQUIRED_CLAIMS},
        )
    # The token is a secret: the error of the library is not chained.
    except jwt.PyJWTError:
        raise unauthenticated() from None
    return _email(claims)


def _key_id(token: str) -> str:
    kid = jwt.get_unverified_header(token).get("kid")
    if not isinstance(kid, str):
        raise unauthenticated()
    return kid


def _email(claims: dict[str, Any]) -> str:
    email = claims.get("email")
    if not isinstance(email, str) or not email:
        raise unauthenticated()
    return email


def _keys_unavailable() -> WordcutError:
    return WordcutError("network_error", "Não foi possível obter as chaves do Cloudflare Access.")


def unauthenticated() -> WordcutError:
    return WordcutError("unauthenticated", "Acesso não identificado; entre pelo Cloudflare Access.")
