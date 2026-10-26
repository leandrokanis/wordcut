import re
import sqlite3
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path
from typing import Annotated, Any

import pytest
from fastapi import Depends, FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from wordcut.db import connect
from wordcut.errors import WordcutError
from wordcut.home import Home
from wordcut.network import FORBID_NETWORK
from wordcut.service.members import add_member, set_role
from wordcut_api.app import create_app
from wordcut_api.auth import Member, require
from wordcut_api.routes import ROUTERS
from wordcut_api.settings import ApiSettings

TOKEN_HEADER = "Cf-Access-Jwt-Assertion"


@pytest.fixture
def connection(wordcut_home: Path) -> Iterator[sqlite3.Connection]:
    with closing(connect(Home(wordcut_home))) as opened:
        yield opened


@pytest.fixture
def access(team: Any) -> ApiSettings:
    return ApiSettings(access_team_domain=team.domain, access_audience=team.audience)


ADMIN_ROUTE = "/api/test-admin"
ASSISTANT_ROUTE = "/api/test-assistant"


def with_role_routes(app: FastAPI) -> FastAPI:
    """Mount a route per minimum role; this issue has no business route yet."""

    @app.get(ADMIN_ROUTE)
    def admin_only(member: Annotated[Member, Depends(require("admin"))]) -> dict[str, str]:
        return {"done_by": member.email}

    @app.get(ASSISTANT_ROUTE)
    def assistant_up(member: Annotated[Member, Depends(require("assistant"))]) -> dict[str, str]:
        return {"done_by": member.email}

    return app


@pytest.fixture
def client(access: ApiSettings, team_keys: Any) -> TestClient:
    return TestClient(with_role_routes(create_app(settings=access, keys=team_keys)))


@pytest.mark.parametrize("role", ["assistant", "admin"])
def test_a_member_with_a_valid_token_sees_the_email_and_role(
    role: str, connection: sqlite3.Connection, client: TestClient, sign: Any
) -> None:
    add_member(connection, "membro@exemplo.org", role)

    response = client.get("/api/me", headers={TOKEN_HEADER: sign("membro@exemplo.org")})

    assert (response.status_code, response.json()) == (
        200,
        {"email": "membro@exemplo.org", "role": role},
    )


def test_the_role_comes_from_the_team_not_from_the_token(
    connection: sqlite3.Connection, client: TestClient, sign: Any
) -> None:
    add_member(connection, "admin@exemplo.org", "admin")
    add_member(connection, "membro@exemplo.org", "assistant")
    token = sign("membro@exemplo.org")
    set_role(connection, "membro@exemplo.org", "admin")

    response = client.get("/api/me", headers={TOKEN_HEADER: token})

    assert response.json()["role"] == "admin"


@pytest.mark.parametrize("route", ["/api/me", ADMIN_ROUTE])
def test_a_request_without_the_access_token_is_unauthenticated(
    route: str, client: TestClient
) -> None:
    response = client.get(route)

    assert (response.status_code, response.json()["error"]["code"]) == (401, "unauthenticated")


REJECTED_TOKENS = {
    "signed by another key": lambda sign, stranger_key: sign(key=stranger_key),
    "expired": lambda sign, stranger_key: sign(exp=1),
    "without an expiry": lambda sign, stranger_key: sign(exp=None),
    "for another audience": lambda sign, stranger_key: sign(aud=["outro-aud"]),
}


@pytest.mark.parametrize("rejected", REJECTED_TOKENS.values(), ids=REJECTED_TOKENS)
def test_a_rejected_token_is_unauthenticated_and_never_repeated(
    rejected: Any,
    connection: sqlite3.Connection,
    client: TestClient,
    sign: Any,
    stranger_key: Any,
    caplog: pytest.LogCaptureFixture,
) -> None:
    # The signed e-mail is an admin: only the token itself may be refused.
    add_member(connection, "assistente@exemplo.org", "admin")
    token = rejected(sign, stranger_key)

    response = client.get("/api/me", headers={TOKEN_HEADER: token})

    assert (
        response.status_code,
        response.json()["error"]["code"],
        token in response.text + caplog.text,
    ) == (
        401,
        "unauthenticated",
        False,
    )


def test_an_email_outside_the_team_is_forbidden_without_repeating_it(
    connection: sqlite3.Connection,
    client: TestClient,
    sign: Any,
    caplog: pytest.LogCaptureFixture,
) -> None:
    add_member(connection, "membro@exemplo.org", "admin")

    response = client.get("/api/me", headers={TOKEN_HEADER: sign("estranho@exemplo.org")})

    assert (response.status_code, response.json(), "estranho" in caplog.text) == (
        403,
        {"error": {"code": "forbidden", "message": "Este e-mail não está na equipe."}},
        False,
    )


def test_an_assistant_is_forbidden_in_a_route_for_administrators(
    connection: sqlite3.Connection, client: TestClient, sign: Any
) -> None:
    add_member(connection, "membro@exemplo.org", "assistant")

    response = client.get(ADMIN_ROUTE, headers={TOKEN_HEADER: sign("membro@exemplo.org")})

    assert (response.status_code, response.json()["error"]["code"]) == (403, "forbidden")


def test_an_admin_gets_the_answer_of_a_route_for_administrators(
    connection: sqlite3.Connection, client: TestClient, sign: Any
) -> None:
    add_member(connection, "admin@exemplo.org", "admin")

    response = client.get(ADMIN_ROUTE, headers={TOKEN_HEADER: sign("admin@exemplo.org")})

    assert (response.status_code, response.json()) == (200, {"done_by": "admin@exemplo.org"})


def test_an_admin_gets_the_answer_of_a_route_for_assistants(
    connection: sqlite3.Connection, client: TestClient, sign: Any
) -> None:
    add_member(connection, "admin@exemplo.org", "admin")

    response = client.get(ASSISTANT_ROUTE, headers={TOKEN_HEADER: sign("admin@exemplo.org")})

    assert (response.status_code, response.json()) == (200, {"done_by": "admin@exemplo.org"})


def test_the_email_header_without_the_token_is_unauthenticated(
    connection: sqlite3.Connection, client: TestClient
) -> None:
    add_member(connection, "admin@exemplo.org", "admin")

    response = client.get(
        "/api/me", headers={"Cf-Access-Authenticated-User-Email": "admin@exemplo.org"}
    )

    assert (response.status_code, response.json()["error"]["code"]) == (401, "unauthenticated")


def test_the_dev_email_identifies_a_member_without_access_and_warns_at_startup(
    connection: sqlite3.Connection, caplog: pytest.LogCaptureFixture
) -> None:
    add_member(connection, "dev@exemplo.org", "admin")
    app = create_app(settings=ApiSettings(dev_email="dev@exemplo.org"))

    response = TestClient(app).get("/api/me")

    assert (response.json(), "WORDCUT_DEV_EMAIL" in caplog.text) == (
        {"email": "dev@exemplo.org", "role": "admin"},
        True,
    )


def test_the_dev_email_is_ignored_when_access_is_configured(
    connection: sqlite3.Connection, access: ApiSettings, team_keys: Any
) -> None:
    add_member(connection, "dev@exemplo.org", "admin")
    settings = ApiSettings(
        access_team_domain=access.access_team_domain,
        access_audience=access.access_audience,
        dev_email="dev@exemplo.org",
    )

    response = TestClient(create_app(settings=settings, keys=team_keys)).get("/api/me")

    assert (response.status_code, response.json()["error"]["code"]) == (401, "unauthenticated")


def test_without_access_nor_dev_email_nobody_is_identified(
    connection: sqlite3.Connection,
) -> None:
    add_member(connection, "dev@exemplo.org", "admin")

    response = TestClient(create_app(settings=ApiSettings())).get("/api/me")

    assert (response.status_code, response.json()["error"]["code"]) == (401, "unauthenticated")


def test_a_dev_email_outside_the_team_is_forbidden(connection: sqlite3.Connection) -> None:
    add_member(connection, "admin@exemplo.org", "admin")

    response = TestClient(create_app(settings=ApiSettings(dev_email="dev@exemplo.org"))).get(
        "/api/me"
    )

    assert (response.status_code, response.json()["error"]["code"]) == (403, "forbidden")


@pytest.mark.parametrize(
    "half",
    [
        ApiSettings(access_team_domain="equipe.exemplo.invalid", dev_email="dev@exemplo.org"),
        ApiSettings(access_audience="aud-de-teste", dev_email="dev@exemplo.org"),
    ],
    ids=["team domain only", "audience only"],
)
def test_access_configured_by_half_refuses_to_start(half: ApiSettings) -> None:
    with pytest.raises(WordcutError) as raised:
        create_app(settings=half)

    assert (raised.value.code, raised.value.message) == (
        "invalid_argument",
        "Configure WORDCUT_ACCESS_TEAM_DOMAIN e WORDCUT_ACCESS_AUD juntos.",
    )


def test_keys_out_of_reach_are_a_bad_gateway_without_the_token(
    access: ApiSettings, sign: Any, caplog: pytest.LogCaptureFixture
) -> None:
    token = sign("membro@exemplo.org")

    response = TestClient(create_app(settings=access)).get("/api/me", headers={TOKEN_HEADER: token})

    assert (
        response.status_code,
        response.json()["error"]["code"],
        token in response.text + caplog.text,
    ) == (
        502,
        "network_error",
        False,
    )


def test_health_answers_without_a_token_nor_the_database(
    access: ApiSettings, team_keys: Any, wordcut_home: Path
) -> None:
    response = TestClient(create_app(settings=access, keys=team_keys)).get("/api/health")

    assert (response.status_code, Home(wordcut_home).database.exists()) == (200, False)


def test_the_settings_are_read_from_the_environment(
    connection: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    add_member(connection, "dev@exemplo.org", "assistant")
    monkeypatch.setenv("WORDCUT_DEV_EMAIL", "dev@exemplo.org")

    response = TestClient(create_app()).get("/api/me")

    assert response.json() == {"email": "dev@exemplo.org", "role": "assistant"}


def test_access_read_from_the_environment_reaches_for_the_team_keys(
    monkeypatch: pytest.MonkeyPatch, team: Any, sign: Any
) -> None:
    monkeypatch.setenv("WORDCUT_ACCESS_TEAM_DOMAIN", team.domain)
    monkeypatch.setenv("WORDCUT_ACCESS_AUD", team.audience)
    monkeypatch.setenv("WORDCUT_DEV_EMAIL", "dev@exemplo.org")

    response = TestClient(create_app()).get("/api/me", headers={TOKEN_HEADER: sign()})

    # Only Access fetches the keys of the team, which the network guard refuses here.
    assert response.json()["error"]["details"] == {"forbidden_by": FORBID_NETWORK}


def business_routes() -> list[tuple[str, str]]:
    """Method and path, with ``1`` for each path parameter, of ``/api/me`` and every route of
    ``ROUTERS``, read from the routers: a route left out of the OpenAPI schema counts too."""
    return [("GET", "/api/me")] + [
        (method, re.sub(r"\{[^}]+\}", "1", route.path))
        for router in ROUTERS
        for route in router.routes
        if isinstance(route, APIRoute)
        for method in route.methods
    ]


def test_every_route_but_health_requires_someone_identified(wordcut_home: Path) -> None:
    client = TestClient(create_app(settings=ApiSettings()))

    answers = {
        f"{method} {path}": client.request(method, path).status_code
        for method, path in business_routes()
    }

    assert (len(answers) > 2, set(answers.values())) == (True, {401})


SCHEMA_PATHS = ["/docs", "/openapi.json", "/redoc", "/api/docs", "/api/openapi.json"]


def test_with_access_the_api_schema_and_its_pages_are_not_served(
    access: ApiSettings, team_keys: Any
) -> None:
    client = TestClient(create_app(settings=access, keys=team_keys))

    answers = {path: client.get(path) for path in SCHEMA_PATHS}

    assert {path: (answer.status_code, answer.json()) for path, answer in answers.items()} == {
        path: (404, {"error": {"code": "not_found", "message": "Rota não encontrada."}})
        for path in SCHEMA_PATHS
    }


def test_in_development_the_api_schema_is_served_under_api(wordcut_home: Path) -> None:
    client = TestClient(create_app(settings=ApiSettings(dev_email="dev@exemplo.org")))

    answers = [client.get(path).status_code for path in ("/api/docs", "/api/openapi.json")]

    assert answers == [200, 200]
