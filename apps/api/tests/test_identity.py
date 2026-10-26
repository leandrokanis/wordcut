import base64
import hmac
import json
import time
from collections.abc import Callable
from typing import Any

import pytest
from cryptography.hazmat.primitives import serialization
from jwt.algorithms import RSAAlgorithm

from wordcut.errors import WordcutError
from wordcut.network import FORBID_NETWORK
from wordcut_api.identity import AccessKeys, KeySource, verify

BadToken = Callable[[Any, Any], str]


def verified(token: str, keys: KeySource, team: Any) -> str:
    return verify(token, keys=keys, team_domain=team.domain, audience=team.audience)


def encoded(part: dict[str, Any] | bytes) -> str:
    raw = part if isinstance(part, bytes) else json.dumps(part).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def forged(header: dict[str, Any], claims: dict[str, Any], secret: bytes | None) -> str:
    """A token with ``header`` as given, HMAC-signed with ``secret``, or unsigned."""
    signing_input = f"{encoded(header)}.{encoded(claims)}"
    signature = b"" if secret is None else hmac.digest(secret, signing_input.encode(), "sha256")
    return f"{signing_input}.{encoded(signature)}"


def valid_claims(team: Any) -> dict[str, Any]:
    return {
        "aud": [team.audience],
        "iss": f"https://{team.domain}",
        "email": "assistente@exemplo.org",
        "exp": int(time.time()) + 300,
    }


def public_pem(team_key: Any) -> bytes:
    return team_key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )


BAD_TOKENS: dict[str, Callable[..., str]] = {
    "signed by another key": lambda sign, stranger_key, **_: sign(key=stranger_key),
    "expired": lambda sign, **_: sign(exp=int(time.time()) - 60),
    "without an expiry": lambda sign, **_: sign(exp=None),
    "for another audience": lambda sign, **_: sign(aud=["outro-aud"]),
    "from another issuer": lambda sign, **_: sign(iss="https://outra.exemplo.invalid"),
    "with an unknown key id": lambda sign, **_: sign(kid="chave-desconhecida"),
    "without an e-mail": lambda sign, **_: sign(email=None),
    "malformed": lambda **_: "nao-e-um-jwt",
    "unsigned (alg none)": lambda team, **_: forged(
        {"alg": "none", "typ": "JWT", "kid": "chave-1"}, valid_claims(team), None
    ),
    "HS256 with the public key as secret": lambda team, team_key, **_: forged(
        {"alg": "HS256", "typ": "JWT", "kid": "chave-1"}, valid_claims(team), public_pem(team_key)
    ),
}


def test_a_valid_access_token_gives_the_verified_email(
    sign: Any, team_keys: KeySource, team: Any
) -> None:
    assert verified(sign("assistente@exemplo.org"), team_keys, team) == "assistente@exemplo.org"


@pytest.mark.parametrize("bad_token", BAD_TOKENS.values(), ids=BAD_TOKENS)
def test_a_token_access_did_not_sign_for_this_team_is_unauthenticated_without_the_token(
    bad_token: Callable[..., str],
    sign: Any,
    team: Any,
    team_key: Any,
    stranger_key: Any,
    team_keys: KeySource,
    caplog: pytest.LogCaptureFixture,
) -> None:
    token = bad_token(sign=sign, team=team, team_key=team_key, stranger_key=stranger_key)

    with pytest.raises(WordcutError) as raised:
        verified(token, team_keys, team)

    shown = json.dumps(raised.value.to_dict()) + str(raised.value) + caplog.text
    assert (raised.value.code, token in shown) == ("unauthenticated", False)


CERTS_PATH = "/cdn-cgi/access/certs"
CACHE_SECONDS = 600


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


class TeamCerts:
    """The certs endpoint of the team: the JWKS of ``keys`` at its URL, fetches counted."""

    def __init__(self, team: Any, keys: dict[str, Any]) -> None:
        self.url = f"https://{team.domain}{CERTS_PATH}"
        self.keys = keys
        self.fetches = 0

    def __call__(self, url: str) -> dict[str, Any]:
        assert url == self.url
        self.fetches += 1
        return {"keys": [self._jwk(kid, key) for kid, key in self.keys.items()]}

    @staticmethod
    def _jwk(kid: str, key: Any) -> dict[str, Any]:
        jwk: dict[str, Any] = RSAAlgorithm.to_jwk(key.public_key(), as_dict=True)
        return {**jwk, "kid": kid, "alg": "RS256", "use": "sig"}


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def certs(team: Any, team_key: Any) -> TeamCerts:
    return TeamCerts(team, {"chave-1": team_key})


@pytest.fixture
def access_keys(team: Any, certs: TeamCerts, clock: Clock) -> AccessKeys:
    return AccessKeys(team.domain, fetch=certs, clock=clock)


def test_the_keys_are_fetched_once_for_ten_minutes(
    sign: Any, team: Any, certs: TeamCerts, clock: Clock, access_keys: AccessKeys
) -> None:
    verified(sign(), access_keys, team)
    clock.now = CACHE_SECONDS - 1
    verified(sign(), access_keys, team)

    assert certs.fetches == 1


def test_the_keys_are_fetched_again_after_ten_minutes(
    sign: Any, team: Any, certs: TeamCerts, clock: Clock, access_keys: AccessKeys
) -> None:
    verified(sign(), access_keys, team)
    clock.now = CACHE_SECONDS
    verified(sign(), access_keys, team)

    assert certs.fetches == 2


def test_a_new_key_id_fetches_the_keys_again_to_follow_a_rotation(
    sign: Any, team: Any, stranger_key: Any, certs: TeamCerts, access_keys: AccessKeys
) -> None:
    verified(sign(), access_keys, team)
    certs.keys = {"chave-2": stranger_key}

    email = verified(sign(key=stranger_key, kid="chave-2"), access_keys, team)

    assert (email, certs.fetches) == ("assistente@exemplo.org", 2)


def test_a_key_id_unknown_after_fetching_again_is_unauthenticated(
    sign: Any, team: Any, certs: TeamCerts, access_keys: AccessKeys
) -> None:
    verified(sign(), access_keys, team)

    with pytest.raises(WordcutError) as raised:
        verified(sign(kid="chave-desconhecida"), access_keys, team)

    assert (raised.value.code, certs.fetches) == ("unauthenticated", 2)


def test_certs_without_usable_keys_are_a_network_error(
    sign: Any, team: Any, certs: TeamCerts, access_keys: AccessKeys
) -> None:
    certs.keys = {}

    with pytest.raises(WordcutError) as raised:
        verified(sign(), access_keys, team)

    assert raised.value.code == "network_error"


def test_the_real_keys_refuse_before_reaching_access_while_the_network_is_forbidden(
    sign: Any, team: Any
) -> None:
    with pytest.raises(WordcutError) as raised:
        verified(sign(), AccessKeys(team.domain), team)

    assert (raised.value.code, raised.value.details) == (
        "network_error",
        {"forbidden_by": FORBID_NETWORK},
    )
