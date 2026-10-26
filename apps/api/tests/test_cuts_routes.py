from contextlib import closing
from typing import Any

import pytest
from fastapi.testclient import TestClient

from wordcut.cuts.caption import DEFAULT_CAPTION
from wordcut.db import connect
from wordcut.home import Home
from wordcut.service.cuts import (
    caption_of,
    fix_word,
    list_cuts,
    preview_cut,
    show_cut,
    update_caption,
)
from wordcut.service.sermons import CUT_STATES


def test_listing_answers_the_cuts_as_the_cli_lists_them_the_discarded_last(
    assistant: TestClient, home: Home, processed_sermon_id: int, add_cut: Any
) -> None:
    discarded = add_cut("discarded", "Descartado")
    kept = add_cut("suggested", "Sugerido")

    response = assistant.get(f"/api/sermons/{processed_sermon_id}/cuts")

    with closing(connect(home)) as connection:
        expected = list_cuts(connection, processed_sermon_id)
    assert (
        response.status_code,
        response.json(),
        [item["id"] for item in expected["items"]],
    ) == (200, expected, [kept, discarded])


def test_listing_by_status_answers_only_the_cuts_in_that_status(
    assistant: TestClient, processed_sermon_id: int, add_cut: Any
) -> None:
    add_cut("suggested")
    chosen = add_cut("chosen")

    response = assistant.get(
        f"/api/sermons/{processed_sermon_id}/cuts", params={"status": "chosen"}
    )

    assert [item["id"] for item in response.json()["items"]] == [chosen]


def test_a_status_outside_the_choices_is_invalid_argument_with_the_choices_without_echo(
    assistant: TestClient, processed_sermon_id: int
) -> None:
    typed = "segredo-digitado-errado"

    response = assistant.get(f"/api/sermons/{processed_sermon_id}/cuts", params={"status": typed})

    assert (response.status_code, response.json(), typed in response.text) == (
        400,
        {
            "error": {
                "code": "invalid_argument",
                "message": f"Valor inválido para status; use um de: {', '.join(CUT_STATES)}.",
                "details": {"argument": "status", "choices": list(CUT_STATES)},
            }
        },
        False,
    )


def test_listing_the_cuts_of_a_missing_sermon_is_not_found_with_its_id(
    assistant: TestClient,
) -> None:
    response = assistant.get("/api/sermons/99/cuts")

    assert (response.status_code, response.json()["error"]["details"]) == (
        404,
        {"sermon_id": 99},
    )


def without_paths(cut: dict[str, Any]) -> dict[str, Any]:
    """The cut ``show_cut`` gives, its exports without the local ``path`` (ADR-0021)."""
    exports = [{k: v for k, v in item.items() if k != "path"} for item in cut["renders"]]
    return {**cut, "renders": exports}


def test_showing_a_cut_answers_it_as_the_cli_shows_it_without_the_local_paths(
    assistant: TestClient, home: Home, cut_id: int, export: Any
) -> None:
    export(cut_id)

    response = assistant.get(f"/api/cuts/{cut_id}")

    with closing(connect(home)) as connection:
        expected = show_cut(connection, cut_id, home=home)
    assert (
        response.status_code,
        response.json(),
        len(expected["renders"]),
        str(home.root) in response.text,
    ) == (200, without_paths(expected), 1, False)


def test_showing_a_missing_cut_is_not_found_with_its_id(assistant: TestClient) -> None:
    response = assistant.get("/api/cuts/99")

    assert (response.status_code, response.json()) == (
        404,
        {
            "error": {
                "code": "not_found",
                "message": "Corte 99 não existe.",
                "details": {"cut_id": 99},
            }
        },
    )


def test_a_cut_id_that_is_not_a_number_is_invalid_argument_without_echo(
    assistant: TestClient,
) -> None:
    typed = "segredo-no-caminho"

    response = assistant.get(f"/api/cuts/{typed}")

    assert (response.status_code, response.json()["error"]["details"], typed in response.text) == (
        400,
        {"argument": "cut_id"},
        False,
    )


def test_the_preview_answers_the_sequence_the_cli_previews_even_with_the_lock_held(
    assistant: TestClient, home: Home, cut_id: int, lock_owner: Any
) -> None:
    lock_owner("render", "cut 99")

    response = assistant.get(f"/api/cuts/{cut_id}/preview")

    with closing(connect(home)) as connection:
        expected = preview_cut(connection, cut_id)
    assert (response.status_code, response.json()) == (200, expected)


@pytest.mark.parametrize(("transition", "status"), [("choose", "chosen"), ("discard", "discarded")])
def test_a_transition_answers_200_with_the_cut_as_the_next_show_gives_it_same_segments(
    transition: str, status: str, assistant: TestClient, cut_id: int, export: Any
) -> None:
    export(cut_id)
    before = assistant.get(f"/api/cuts/{cut_id}").json()

    response = assistant.post(f"/api/cuts/{cut_id}/{transition}")

    shown = assistant.get(f"/api/cuts/{cut_id}").json()
    assert (response.status_code, response.json(), shown["status"], shown["segments"]) == (
        200,
        shown,
        status,
        before["segments"],
    )


@pytest.mark.parametrize(
    ("status", "restored"),
    [("discarded", "suggested"), ("chosen", "chosen")],
    ids=["discarded comes back", "not discarded stays"],
)
def test_restoring_undoes_a_discard_only(
    status: str, restored: str, assistant: TestClient, add_cut: Any
) -> None:
    cut = add_cut(status)

    response = assistant.post(f"/api/cuts/{cut}/restore")

    assert (response.status_code, response.json()["status"]) == (200, restored)


def word_ids(client: TestClient, cut_id: int) -> list[int]:
    return [word["word_id"] for word in client.get(f"/api/cuts/{cut_id}").json()["words"]]


def test_fixing_a_word_answers_the_word_as_the_cli_fixes_it(
    assistant: TestClient, home: Home, cut_id: int
) -> None:
    word = word_ids(assistant, cut_id)[1]

    response = assistant.put(f"/api/cuts/{cut_id}/words/{word}", json={"text": "Graça"})

    with closing(connect(home)) as connection:
        expected = fix_word(connection, cut_id, word, "Graça")
    assert (response.status_code, response.json(), expected["corrected"]) == (
        200,
        expected,
        "Graça",
    )


def test_a_fixed_word_shows_corrected_in_the_cut_and_in_the_preview_even_with_the_lock_held(
    assistant: TestClient, cut_id: int, lock_owner: Any
) -> None:
    word = word_ids(assistant, cut_id)[1]
    lock_owner("render", "cut 99")

    response = assistant.put(f"/api/cuts/{cut_id}/words/{word}", json={"text": "Graça"})

    shown = assistant.get(f"/api/cuts/{cut_id}").json()
    preview = assistant.get(f"/api/cuts/{cut_id}/preview").json()
    assert (
        response.status_code,
        [item["corrected"] for item in shown["words"]],
        preview["segments"][0]["text"],
    ) == (200, [None, "Graça", None, None], "Irmãos, Graça e paz.")


def test_a_spelling_too_different_is_refused_without_echo_and_changes_nothing(
    assistant: TestClient, cut_id: int
) -> None:
    word = word_ids(assistant, cut_id)[1]
    before = assistant.get(f"/api/cuts/{cut_id}").json()
    typed = "desgraçadamente"

    response = assistant.put(f"/api/cuts/{cut_id}/words/{word}", json={"text": typed})

    error = response.json()["error"]
    assert (
        response.status_code,
        error["code"],
        error["details"],
        typed in response.text,
        assistant.get(f"/api/cuts/{cut_id}").json(),
    ) == (
        409,
        "spelling_too_different",
        {"distance": 10, "limit": 1, "original": "graça"},
        False,
        before,
    )


def test_fixing_a_word_back_to_the_original_removes_the_fix(
    assistant: TestClient, cut_id: int
) -> None:
    word = word_ids(assistant, cut_id)[1]
    assistant.put(f"/api/cuts/{cut_id}/words/{word}", json={"text": "Graça"})

    response = assistant.put(f"/api/cuts/{cut_id}/words/{word}", json={"text": "graça"})

    shown = assistant.get(f"/api/cuts/{cut_id}").json()
    assert (response.json()["corrected"], shown["words"][1]["corrected"]) == (None, None)


@pytest.mark.parametrize("typed", ["", "Graça plena"], ids=["empty", "two words"])
def test_a_fix_that_is_not_one_word_is_invalid_argument_naming_text_without_echo(
    typed: str, assistant: TestClient, cut_id: int
) -> None:
    word = word_ids(assistant, cut_id)[1]

    response = assistant.put(f"/api/cuts/{cut_id}/words/{word}", json={"text": typed})

    assert (
        response.status_code,
        response.json()["error"]["details"],
        bool(typed) and typed in response.text,
    ) == (400, {"argument": "text"}, False)


def test_a_word_outside_the_segments_of_the_cut_is_invalid_argument_naming_word_id(
    assistant: TestClient, cut_id: int
) -> None:
    response = assistant.put(f"/api/cuts/{cut_id}/words/99", json={"text": "Graça"})

    assert (response.status_code, response.json()["error"]["details"]) == (
        400,
        {"argument": "word_id"},
    )


def test_the_caption_answers_the_style_as_the_cli_shows_it(
    assistant: TestClient, home: Home, cut_id: int
) -> None:
    response = assistant.get(f"/api/cuts/{cut_id}/caption")

    with closing(connect(home)) as connection:
        expected = caption_of(connection, cut_id)
    assert (response.status_code, response.json()) == (200, expected)


def test_changing_part_of_the_caption_answers_the_whole_style_as_the_cli_changes_it(
    assistant: TestClient, home: Home, cut_id: int
) -> None:
    changes = {"size": 72, "color": "#ffffff", "position": "bottom"}

    response = assistant.patch(f"/api/cuts/{cut_id}/caption", json=changes)

    shown = assistant.get(f"/api/cuts/{cut_id}").json()
    with closing(connect(home)) as connection:
        expected = update_caption(connection, cut_id, changes)
    assert (response.status_code, response.json(), shown["caption"], shown["edited"]) == (
        200,
        expected,
        expected,
        True,
    )


def test_changing_the_caption_with_no_field_is_invalid_argument_and_leaves_the_cut_unedited(
    assistant: TestClient, cut_id: int
) -> None:
    response = assistant.patch(f"/api/cuts/{cut_id}/caption", json={})

    shown = assistant.get(f"/api/cuts/{cut_id}").json()
    assert (response.status_code, response.json()["error"]["code"], shown["edited"]) == (
        400,
        "invalid_argument",
        False,
    )


def test_a_caption_value_out_of_range_is_refused_with_the_range_storing_nothing(
    assistant: TestClient, cut_id: int
) -> None:
    before = assistant.get(f"/api/cuts/{cut_id}").json()

    response = assistant.patch(
        f"/api/cuts/{cut_id}/caption", json={"color": "#FFFFFF", "size": 500}
    )

    assert (
        response.status_code,
        response.json()["error"]["details"],
        assistant.get(f"/api/cuts/{cut_id}").json(),
    ) == (400, {"argument": "size", "min": 24, "max": 160}, before)


@pytest.mark.parametrize("field", ["font", "position", "shadow"])
def test_a_caption_choice_outside_the_choices_is_refused_naming_the_choices(
    field: str, assistant: TestClient, cut_id: int
) -> None:
    response = assistant.patch(f"/api/cuts/{cut_id}/caption", json={field: "fora-das-escolhas"})

    details = response.json()["error"]["details"]
    assert (response.status_code, details["argument"], bool(details["choices"])) == (
        400,
        field,
        True,
    )


@pytest.mark.parametrize(
    "changes",
    [{"size": "72"}, {"enabled": "true"}, {"size": None}, {"offset": 50.5}],
    ids=["size as text", "switch as text", "null", "offset not whole"],
)
def test_a_caption_value_of_the_wrong_type_is_invalid_argument_never_a_failure(
    changes: dict[str, Any], assistant: TestClient, cut_id: int
) -> None:
    response = assistant.patch(f"/api/cuts/{cut_id}/caption", json=changes)

    assert (response.status_code, response.json()["error"]["details"]) == (
        400,
        {"argument": next(iter(changes))},
    )


def test_an_unknown_caption_field_is_refused_without_repeating_its_name(
    assistant: TestClient, cut_id: int
) -> None:
    typed = "segredo-digitado"

    response = assistant.patch(f"/api/cuts/{cut_id}/caption", json={"size": 72, typed: 1})

    shown = assistant.get(f"/api/cuts/{cut_id}").json()
    assert (response.status_code, response.json(), typed in response.text, shown["edited"]) == (
        400,
        {
            "error": {
                "code": "invalid_argument",
                "message": "Argumento não reconhecido; veja docs/api.md.",
            }
        },
        False,
        False,
    )


def test_resetting_the_caption_answers_200_with_the_default_style_turned_on(
    assistant: TestClient, cut_id: int
) -> None:
    assistant.patch(f"/api/cuts/{cut_id}/caption", json={"enabled": False, "size": 72})

    response = assistant.delete(f"/api/cuts/{cut_id}/caption")

    shown = assistant.get(f"/api/cuts/{cut_id}/caption").json()
    assert (response.status_code, response.json(), shown) == (
        200,
        DEFAULT_CAPTION.as_dict(),
        DEFAULT_CAPTION.as_dict(),
    )


@pytest.mark.parametrize(
    ("method", "action", "body"),
    [
        ("POST", "choose", None),
        ("POST", "discard", None),
        ("POST", "restore", None),
        ("PATCH", "caption", {"size": 72}),
        ("DELETE", "caption", None),
    ],
)
def test_the_assistant_changes_a_cut_while_the_machine_is_busy(
    method: str,
    action: str,
    body: dict[str, Any] | None,
    assistant: TestClient,
    cut_id: int,
    lock_owner: Any,
) -> None:
    lock_owner("render", "cut 99")

    response = assistant.request(method, f"/api/cuts/{cut_id}/{action}", json=body)

    assert response.status_code == 200
