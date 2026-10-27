"""The minimum role of every route (feature 1.2.a), checked against the routes the app has."""

import re
from contextlib import closing
from pathlib import Path
from typing import Any

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from wordcut.db import connect
from wordcut.home import Home
from wordcut.service.members import list_members
from wordcut.service.presets import list_presets
from wordcut.service.settings import show_settings
from wordcut.service.tasks import list_tasks
from wordcut_api.app import create_app
from wordcut_api.routes import ROUTERS
from wordcut_api.settings import ApiSettings

ASSISTANT = "assistant"
ADMIN = "admin"

# Feature 1.2.a: an assistant creates, processes, chooses, fixes the form of and exports cuts;
# suggestions, settings, criteria, presets and the team are the administrator's (ADR-0021).
PERMISSIONS: dict[tuple[str, str], str] = {
    ("GET", "/api/me"): ASSISTANT,
    ("POST", "/api/sermons"): ASSISTANT,
    ("GET", "/api/sermons"): ASSISTANT,
    ("GET", "/api/sermons/{sermon_id}"): ASSISTANT,
    ("PATCH", "/api/sermons/{sermon_id}"): ASSISTANT,
    ("GET", "/api/sermons/{sermon_id}/video"): ASSISTANT,
    ("POST", "/api/sermons/{sermon_id}/process"): ASSISTANT,
    ("POST", "/api/sermons/{sermon_id}/suggest"): ADMIN,
    ("POST", "/api/sermons/{sermon_id}/prepare"): ASSISTANT,
    ("GET", "/api/sermons/{sermon_id}/thumbnails"): ASSISTANT,
    ("GET", "/api/sermons/{sermon_id}/thumbnails.json"): ASSISTANT,
    ("GET", "/api/sermons/{sermon_id}/waveform"): ASSISTANT,
    ("GET", "/api/sermons/{sermon_id}/cuts"): ASSISTANT,
    ("POST", "/api/sermons/{sermon_id}/cuts"): ADMIN,
    ("GET", "/api/tasks"): ASSISTANT,
    ("GET", "/api/tasks/{task_id}"): ASSISTANT,
    ("GET", "/api/tasks/{task_id}/events"): ASSISTANT,
    ("GET", "/api/status"): ASSISTANT,
    ("GET", "/api/cuts/{cut_id}"): ASSISTANT,
    ("GET", "/api/cuts/{cut_id}/preview"): ASSISTANT,
    ("POST", "/api/cuts/{cut_id}/choose"): ASSISTANT,
    ("POST", "/api/cuts/{cut_id}/discard"): ASSISTANT,
    ("POST", "/api/cuts/{cut_id}/restore"): ASSISTANT,
    ("PUT", "/api/cuts/{cut_id}/words/{word_id}"): ASSISTANT,
    ("PUT", "/api/cuts/{cut_id}/segments"): ADMIN,
    ("PATCH", "/api/cuts/{cut_id}/range"): ADMIN,
    ("GET", "/api/cuts/{cut_id}/caption"): ASSISTANT,
    ("PATCH", "/api/cuts/{cut_id}/caption"): ASSISTANT,
    ("DELETE", "/api/cuts/{cut_id}/caption"): ASSISTANT,
    ("POST", "/api/cuts/{cut_id}/renders"): ASSISTANT,
    ("GET", "/api/cuts/{cut_id}/renders"): ASSISTANT,
    ("GET", "/api/cuts/{cut_id}/renders/estimate"): ASSISTANT,
    ("GET", "/api/renders/{render_id}"): ASSISTANT,
    ("GET", "/api/renders/{render_id}/file"): ASSISTANT,
    ("GET", "/api/settings"): ADMIN,
    ("PATCH", "/api/settings"): ADMIN,
    ("PUT", "/api/settings/llm-key"): ADMIN,
    ("PUT", "/api/settings/youtube-cookies"): ADMIN,
    ("GET", "/api/criteria"): ADMIN,
    ("GET", "/api/presets"): ADMIN,
    ("POST", "/api/presets"): ADMIN,
    ("GET", "/api/presets/{preset_id}"): ADMIN,
    ("PATCH", "/api/presets/{preset_id}"): ADMIN,
    ("POST", "/api/presets/{preset_id}/set-default"): ADMIN,
    ("DELETE", "/api/presets/{preset_id}"): ADMIN,
    ("GET", "/api/members"): ADMIN,
    ("POST", "/api/members"): ADMIN,
    ("POST", "/api/members/set-role"): ADMIN,
    ("POST", "/api/members/remove"): ADMIN,
}
ADMIN_ROUTES = [route for route, role in PERMISSIONS.items() if role == ADMIN]
ASSISTANT_ROUTES = [route for route, role in PERMISSIONS.items() if role == ASSISTANT]

FAKE_KEY = "sk-or-v1-ficticia-permissoes-0123456789abcdef-WXYZ"
# Netscape cookie file (https://curl.se/docs/http-cookies.html): seven TAB-separated fields.
FAKE_COOKIES = ".youtube.com\tTRUE\t/\tTRUE\t1893456000\tSID-FICTICIO\tvalor-ficticio-perm\n"
# Valid bodies that would change something, were the role allowed to.
CHANGING_BODIES: dict[tuple[str, str], dict[str, Any]] = {
    ("POST", "/api/sermons/{sermon_id}/cuts"): {"start": 0, "end": 30},
    ("PATCH", "/api/cuts/{cut_id}/range"): {"by": 5},
    ("PATCH", "/api/settings"): {"llm_model": "provedor/modelo-de-teste"},
    ("PUT", "/api/settings/llm-key"): {"value": FAKE_KEY},
    ("PUT", "/api/settings/youtube-cookies"): {"value": FAKE_COOKIES},
    ("POST", "/api/presets"): {"name": "Criado sem permissão"},
    ("PATCH", "/api/presets/{preset_id}"): {"name": "Renomeado sem permissão"},
    ("POST", "/api/members"): {"email": "novo@exemplo.org", "role": "admin"},
    ("POST", "/api/members/set-role"): {"email": "assistente@exemplo.org", "role": "admin"},
    ("POST", "/api/members/remove"): {"email": "admin@exemplo.org"},
}
WRITES = {"POST", "PUT", "PATCH", "DELETE"}


def app_routes() -> set[tuple[str, str]]:
    """Method and path of every route of ``ROUTERS``, read from the routers themselves so a
    route left out of the OpenAPI schema is not missed, and of ``/api/me``."""
    return {
        (method, route.path)
        for router in ROUTERS
        for route in router.routes
        if isinstance(route, APIRoute)
        for method in route.methods
    } | {("GET", "/api/me")}


def call(
    client: TestClient, route: tuple[str, str], resource_id: str = "99", body: Any = None
) -> Any:
    """Call ``route`` with ``resource_id`` in each path parameter and a JSON body on a write:
    FastAPI checks the identity before a body valid as JSON is read."""
    method, path = route
    url = re.sub(r"\{[^}]+\}", resource_id, path)
    if method not in WRITES:
        return client.request(method, url)
    return client.request(method, url, json={} if body is None else body)


def test_the_table_has_every_route_of_the_app_and_nothing_more() -> None:
    assert app_routes() == set(PERMISSIONS)


def test_every_route_in_the_table_requires_someone_identified(wordcut_home: Path) -> None:
    client = TestClient(create_app(settings=ApiSettings()))

    answers = {route: call(client, route).status_code for route in PERMISSIONS}

    assert answers == dict.fromkeys(PERMISSIONS, 401)


def everything_the_admin_owns(home: Home, config: Path) -> Any:
    with closing(connect(home)) as connection:
        return (
            show_settings(connection),
            list_presets(connection),
            list_members(connection),
            sorted(config.rglob("*")) if config.exists() else [],
            list_tasks(home),
        )


@pytest.mark.parametrize("resource_id", ["1", "99"], ids=["existing id", "missing id"])
def test_an_assistant_is_forbidden_in_every_route_of_the_administrator_changing_nothing(
    resource_id: str,
    assistant: TestClient,
    admin: TestClient,
    home: Home,
    wordcut_config: Path,
    harmless_tasks: list[Any],
) -> None:
    before = everything_the_admin_owns(home, wordcut_config)

    answers = {
        route: call(assistant, route, resource_id, CHANGING_BODIES.get(route))
        for route in ADMIN_ROUTES
    }

    assert (
        {
            route: (answer.status_code, answer.json()["error"]["code"])
            for route, answer in answers.items()
        },
        everything_the_admin_owns(home, wordcut_config),
        harmless_tasks,
    ) == (dict.fromkeys(ADMIN_ROUTES, (403, "forbidden")), before, [])


def test_an_assistant_passes_in_every_route_of_the_assistant(
    assistant: TestClient, harmless_tasks: list[Any]
) -> None:
    answers = {route: call(assistant, route).status_code for route in ASSISTANT_ROUTES}

    refused = {route: status for route, status in answers.items() if status in {401, 403, 500}}
    assert (refused, harmless_tasks) == ({}, [])


def test_an_admin_passes_in_every_route(admin: TestClient, harmless_tasks: list[Any]) -> None:
    answers = {route: call(admin, route).status_code for route in PERMISSIONS}

    refused = {route: status for route, status in answers.items() if status in {401, 403, 500}}
    assert (refused, harmless_tasks) == ({}, [])


def test_the_app_includes_no_router_but_those_of_routers(wordcut_home: Path) -> None:
    app = create_app(settings=ApiSettings())

    included = [route for route in app.routes if not isinstance(route, APIRoute)]
    own = {route.path for route in app.routes if isinstance(route, APIRoute)}

    # FastAPI keeps each included router as one entry of ``app.routes``.
    assert (len(included), own) == (len(ROUTERS), {"/api/health", "/api/me"})
