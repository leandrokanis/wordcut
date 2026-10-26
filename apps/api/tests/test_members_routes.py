from contextlib import closing
from typing import Any

import pytest
from fastapi.testclient import TestClient

from wordcut.db import connect
from wordcut.home import Home
from wordcut.service.members import list_members


def test_the_team_answers_as_the_cli_lists_it_by_email(
    admin: TestClient, home: Home, assistant: TestClient
) -> None:
    response = admin.get("/api/members")

    with closing(connect(home)) as connection:
        expected = list_members(connection)
    assert (response.status_code, response.json(), [item["email"] for item in expected]) == (
        200,
        {"items": expected},
        ["admin@exemplo.org", "assistente@exemplo.org"],
    )


def test_letting_an_email_in_answers_201_with_the_member_in_lower_case(
    admin: TestClient,
) -> None:
    response = admin.post("/api/members", json={"email": " Novo@Exemplo.org ", "role": "assistant"})

    member = response.json()
    assert (response.status_code, member["email"], member["role"], member in members(admin)) == (
        201,
        "novo@exemplo.org",
        "assistant",
        True,
    )


def members(client: TestClient) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = client.get("/api/members").json()["items"]
    return items


@pytest.mark.parametrize(
    ("body", "details"),
    [
        ({"email": "admin@exemplo.org", "role": "admin"}, {"argument": "email"}),
        ({"email": "sem-arroba-segredo", "role": "admin"}, {"argument": "email"}),
        (
            {"email": "novo@exemplo.org", "role": "dono"},
            {"argument": "role", "choices": ["assistant", "admin"]},
        ),
        ({"email": "novo@exemplo.org"}, {"argument": "role"}),
    ],
    ids=["already in the team", "malformed", "role outside the choices", "no role"],
)
def test_a_refused_member_is_invalid_argument_without_echo_and_the_team_stays(
    body: dict[str, str], details: dict[str, Any], admin: TestClient
) -> None:
    before = members(admin)

    response = admin.post("/api/members", json=body)

    assert (
        response.status_code,
        response.json()["error"]["details"],
        "segredo" in response.text or "dono" in response.text,
        members(admin),
    ) == (400, details, False, before)


def test_changing_a_role_answers_the_member_with_the_new_role(
    admin: TestClient, assistant: TestClient
) -> None:
    response = admin.post(
        "/api/members/set-role", json={"email": "assistente@exemplo.org", "role": "admin"}
    )

    assert (response.status_code, response.json()["role"]) == (200, "admin")


def test_taking_a_member_off_answers_it_removed(admin: TestClient, assistant: TestClient) -> None:
    response = admin.post("/api/members/remove", json={"email": "assistente@exemplo.org"})

    assert (
        response.status_code,
        response.json(),
        [item["email"] for item in members(admin)],
    ) == (200, {"email": "assistente@exemplo.org", "removed": True}, ["admin@exemplo.org"])


@pytest.mark.parametrize(
    ("action", "body"),
    [
        ("set-role", {"email": "admin@exemplo.org", "role": "assistant"}),
        ("remove", {"email": "admin@exemplo.org"}),
    ],
    ids=["demoting", "removing"],
)
def test_the_last_administrator_is_kept(
    action: str, body: dict[str, str], admin: TestClient, assistant: TestClient
) -> None:
    before = members(admin)

    response = admin.post(f"/api/members/{action}", json=body)

    assert (response.status_code, response.json()["error"]["code"], members(admin)) == (
        409,
        "last_admin",
        before,
    )


@pytest.mark.parametrize(
    ("action", "body"),
    [
        ("set-role", {"email": "fora-segredo@exemplo.org", "role": "admin"}),
        ("remove", {"email": "fora-segredo@exemplo.org"}),
    ],
    ids=["changing the role", "removing"],
)
def test_an_email_outside_the_team_is_not_found_without_echo(
    action: str, body: dict[str, str], admin: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    response = admin.post(f"/api/members/{action}", json=body)

    assert (
        response.status_code,
        response.json()["error"]["details"],
        "fora-segredo" in response.text + caplog.text,
    ) == (404, {"argument": "email"}, False)
