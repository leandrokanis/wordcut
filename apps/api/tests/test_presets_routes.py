from contextlib import closing
from typing import Any

import pytest
from fastapi.testclient import TestClient

from wordcut.db import connect
from wordcut.home import Home
from wordcut.service.presets import list_criteria, list_presets, show_preset


def test_the_criteria_answer_as_the_cli_lists_them_without_prompt_text(
    admin: TestClient,
) -> None:
    response = admin.get("/api/criteria")

    items = response.json()["items"]
    assert (
        response.status_code,
        response.json(),
        {key for item in items for key in item},
    ) == (200, {"items": list_criteria()}, {"id", "name", "type", "default_level"})


def test_the_presets_answer_as_the_cli_lists_them(admin: TestClient, home: Home) -> None:
    response = admin.get("/api/presets")

    with closing(connect(home)) as connection:
        expected = list_presets(connection)
    assert (response.status_code, response.json(), len(expected)) == (
        200,
        {"items": expected},
        1,
    )


def default_id(client: TestClient) -> int:
    return int(next(item["id"] for item in client.get("/api/presets").json()["items"]))


def test_a_preset_answers_as_the_cli_shows_it(admin: TestClient, home: Home) -> None:
    preset_id = default_id(admin)

    response = admin.get(f"/api/presets/{preset_id}")

    with closing(connect(home)) as connection:
        expected = show_preset(connection, preset_id)
    assert (response.status_code, response.json()) == (200, expected)


def test_creating_a_preset_answers_201_with_a_copy_of_the_default_that_is_not_default(
    admin: TestClient,
) -> None:
    default = admin.get(f"/api/presets/{default_id(admin)}").json()

    response = admin.post("/api/presets", json={"name": "Estudo bíblico"})

    created = response.json()
    shown = admin.get(f"/api/presets/{created['id']}").json()
    assert (
        response.status_code,
        created,
        created["is_default"],
        created["levels"],
        created["name"],
    ) == (201, shown, False, default["levels"], "Estudo bíblico")


def test_creating_a_preset_from_another_copies_that_one(admin: TestClient) -> None:
    source = admin.post("/api/presets", json={"name": "Origem"}).json()
    admin.patch(f"/api/presets/{source['id']}", json={"instructions": "Prefira trechos curtos."})

    response = admin.post("/api/presets", json={"name": "Cópia", "from_id": source["id"]})

    assert response.json()["instructions"] == "Prefira trechos curtos."


def test_creating_a_preset_from_a_missing_one_is_not_found_naming_it(admin: TestClient) -> None:
    response = admin.post("/api/presets", json={"name": "Cópia", "from_id": 99})

    assert (response.status_code, response.json()["error"]["details"]) == (
        404,
        {"preset_id": 99},
    )


def test_changing_a_preset_answers_it_as_the_cli_changes_it(admin: TestClient, home: Home) -> None:
    preset = admin.post("/api/presets", json={"name": "Estudo"}).json()
    criterion = list_criteria()[0]["id"]
    changes: dict[str, Any] = {
        "name": "Estudo bíblico",
        "levels": {criterion: "strict"},
        "duration_allowed": {"min": 40, "max": 90},
        "duration_ideal": {"min": 55, "max": 65},
        "reorder": False,
        "protected_words": ["não", "mas"],
        "instructions": "Prefira trechos curtos.",
    }

    response = admin.patch(f"/api/presets/{preset['id']}", json=changes)

    with closing(connect(home)) as connection:
        expected = show_preset(connection, preset["id"])
    changed = {name: expected[name] for name in changes}
    assert (response.status_code, response.json(), changed) == (
        200,
        expected,
        {**changes, "levels": {**expected["levels"], criterion: "strict"}},
    )


@pytest.mark.parametrize(
    ("changes", "argument"),
    [
        ({}, "name, levels, duration_allowed, duration_ideal, reorder, protected_words,"
             " instructions"),
        ({"name": "Padrão repetido"}, "name"),
        ({"levels": {"criterio-inexistente": "strict"}}, "levels"),
        ({"duration_ideal": {"min": 10, "max": 200}}, "duration_ideal"),
        ({"duration_ideal": {"min": "55", "max": 65}}, "min"),
        ({"reorder": "false"}, "reorder"),
        ({"instructions": None}, "instructions"),
    ],
    ids=["no field", "repeated name", "missing criterion", "ideal outside allowed",
         "seconds as text", "switch as text", "null"],
)  # fmt: skip
def test_a_refused_preset_change_is_invalid_argument_naming_the_field_changing_nothing(
    changes: dict[str, Any], argument: str, admin: TestClient
) -> None:
    admin.post("/api/presets", json={"name": "Padrão repetido"})
    preset = admin.post("/api/presets", json={"name": "Alvo"}).json()

    response = admin.patch(f"/api/presets/{preset['id']}", json=changes)

    assert (
        response.status_code,
        response.json()["error"]["details"]["argument"],
        admin.get(f"/api/presets/{preset['id']}").json(),
    ) == (400, argument, preset)


def test_making_a_preset_the_default_answers_it_and_the_previous_one_stops_being(
    admin: TestClient,
) -> None:
    previous = default_id(admin)
    preset = admin.post("/api/presets", json={"name": "Novo padrão"}).json()

    response = admin.post(f"/api/presets/{preset['id']}/set-default")

    assert (
        response.status_code,
        response.json()["is_default"],
        admin.get(f"/api/presets/{previous}").json()["is_default"],
    ) == (200, True, False)


def test_deleting_a_preset_answers_200_with_it_deleted(admin: TestClient) -> None:
    preset = admin.post("/api/presets", json={"name": "Temporário"}).json()

    response = admin.delete(f"/api/presets/{preset['id']}")

    assert (
        response.status_code,
        response.json(),
        admin.get(f"/api/presets/{preset['id']}").status_code,
    ) == (200, {"id": preset["id"], "deleted": True}, 404)


def test_deleting_the_default_preset_is_refused(admin: TestClient) -> None:
    preset_id = default_id(admin)

    response = admin.delete(f"/api/presets/{preset_id}")

    assert (
        response.status_code,
        response.json()["error"]["code"],
        admin.get(f"/api/presets/{preset_id}").status_code,
    ) == (409, "default_preset", 200)
