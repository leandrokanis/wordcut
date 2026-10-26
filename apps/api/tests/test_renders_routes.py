import os
import signal
import subprocess
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from wordcut.db import connect, sermons
from wordcut.home import Home
from wordcut.service.rendering import estimate_render, show_render
from wordcut.service.renders import list_renders
from wordcut.service.tasks import list_tasks

NOW = datetime(2026, 10, 26, 22, 40, tzinfo=timezone(timedelta(hours=-3)))
# The bytes the ``export`` fixture writes in the file of an export.
VIDEO = bytes(range(256)) * 4 + b"amen"


def test_exporting_answers_202_with_the_launched_task_found_among_the_tasks(
    assistant: TestClient, cut_id: int, harmless_tasks: list[Any]
) -> None:
    response = assistant.post(f"/api/cuts/{cut_id}/renders")

    task = response.json()
    found = assistant.get(f"/api/tasks/{task['task_id']}").json()
    assert (
        response.status_code,
        task,
        len(harmless_tasks),
        (found["kind"], found["status"], found["cut_id"]),
    ) == (
        202,
        {"task_id": task["task_id"], "kind": "render", "status": "running", "cut_id": cut_id},
        1,
        ("render", "running", cut_id),
    )


def test_the_options_of_an_export_are_saved_on_the_cut(
    assistant: TestClient, cut_id: int, harmless_tasks: list[Any]
) -> None:
    assistant.post(f"/api/cuts/{cut_id}/renders", json={"pauses": "short", "fade": False})

    options = assistant.get(f"/api/cuts/{cut_id}").json()["render_options"]

    assert (options["pauses"], options["fade"], options["fillers"]) == ("short", False, "remove")


def test_exporting_without_the_caption_turns_it_off_and_marks_the_cut_edited(
    assistant: TestClient, cut_id: int, harmless_tasks: list[Any]
) -> None:
    assistant.post(f"/api/cuts/{cut_id}/renders", json={"caption": False})

    shown = assistant.get(f"/api/cuts/{cut_id}").json()

    assert (shown["caption"]["enabled"], shown["render_options"]["caption"], shown["edited"]) == (
        False,
        False,
        True,
    )


def test_an_export_without_a_body_repeats_the_options_saved_last(
    assistant: TestClient, cut_id: int, harmless_tasks: list[Any]
) -> None:
    assistant.post(f"/api/cuts/{cut_id}/renders", json={"pauses": "short", "quality": "small"})
    saved = assistant.get(f"/api/cuts/{cut_id}").json()["render_options"]
    end(harmless_tasks)

    response = assistant.post(f"/api/cuts/{cut_id}/renders")

    shown = assistant.get(f"/api/cuts/{cut_id}").json()["render_options"]
    assert (response.status_code, shown, len(harmless_tasks)) == (202, saved, 2)


def end(tasks: list[subprocess.Popen[bytes]]) -> None:
    """End the task processes, as a finished task does, which frees the lock."""
    for process in tasks:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()


def test_an_export_option_outside_its_choices_is_refused_with_them_launching_and_saving_nothing(
    assistant: TestClient, home: Home, cut_id: int, harmless_tasks: list[Any]
) -> None:
    before = assistant.get(f"/api/cuts/{cut_id}").json()

    response = assistant.post(
        f"/api/cuts/{cut_id}/renders", json={"fade": False, "pauses": "nenhuma"}
    )

    assert (
        response.status_code,
        response.json()["error"]["details"],
        list_tasks(home),
        harmless_tasks,
        assistant.get(f"/api/cuts/{cut_id}").json(),
    ) == (
        400,
        {"argument": "pauses", "choices": ["original", "natural", "short"]},
        {"items": []},
        [],
        before,
    )


@pytest.mark.parametrize(
    "body",
    [{"segredo-digitado": 1}, {"fade": "false"}, {"fade": None}],
    ids=["unknown field", "switch as text", "null"],
)
def test_a_malformed_export_body_is_invalid_argument_without_echo_launching_nothing(
    body: dict[str, Any], assistant: TestClient, home: Home, cut_id: int, harmless_tasks: list[Any]
) -> None:
    response = assistant.post(f"/api/cuts/{cut_id}/renders", json=body)

    assert (
        response.status_code,
        response.json()["error"]["code"],
        "segredo" in response.text,
        list_tasks(home),
    ) == (400, "invalid_argument", False, {"items": []})


def test_exporting_while_the_machine_is_busy_records_nothing(
    assistant: TestClient, home: Home, cut_id: int, lock_owner: Any, harmless_tasks: list[Any]
) -> None:
    lock_owner("process", "sermon 99")
    before = assistant.get(f"/api/cuts/{cut_id}").json()

    response = assistant.post(
        f"/api/cuts/{cut_id}/renders", json={"caption": False, "pauses": "short"}
    )

    error = response.json()["error"]
    assert (
        response.status_code,
        error["code"],
        error["details"]["resource"],
        list_tasks(home),
        harmless_tasks,
        assistant.get(f"/api/cuts/{cut_id}").json(),
    ) == (409, "busy", "sermon 99", {"items": []}, [], before)


def test_exporting_a_cut_of_a_sermon_not_processed_is_refused(
    assistant: TestClient,
    home: Home,
    cut_id: int,
    processed_sermon_id: int,
    harmless_tasks: list[Any],
) -> None:
    with closing(connect(home)) as connection, connection:
        sermons.set_status(connection, processed_sermon_id, "trimmed", NOW)

    response = assistant.post(f"/api/cuts/{cut_id}/renders")

    assert (response.status_code, response.json()["error"]["code"], harmless_tasks) == (
        409,
        "sermon_not_processed",
        [],
    )


def test_exporting_a_missing_cut_is_not_found(
    assistant: TestClient, wordcut_home: Path, harmless_tasks: list[Any]
) -> None:
    response = assistant.post("/api/cuts/99/renders")

    assert (response.status_code, response.json()["error"]["details"], harmless_tasks) == (
        404,
        {"cut_id": 99},
        [],
    )


def test_the_estimate_answers_as_the_cli_estimates_without_a_task_saving_nor_the_lock(
    assistant: TestClient, home: Home, cut_id: int, lock_owner: Any
) -> None:
    lock_owner("process", "sermon 99")
    before = assistant.get(f"/api/cuts/{cut_id}").json()

    response = assistant.get(
        f"/api/cuts/{cut_id}/renders/estimate", params={"fade": "false", "pauses": "short"}
    )

    with closing(connect(home)) as connection:
        expected = estimate_render(connection, cut_id, {"fade": False, "pauses": "short"})
    assert (
        response.status_code,
        response.json(),
        expected["options"]["fade"],
        list_tasks(home),
        assistant.get(f"/api/cuts/{cut_id}").json(),
    ) == (200, expected, False, {"items": []}, before)


def test_an_estimate_option_outside_its_choices_is_refused_with_them(
    assistant: TestClient, cut_id: int
) -> None:
    response = assistant.get(f"/api/cuts/{cut_id}/renders/estimate", params={"quality": "media"})

    assert (response.status_code, response.json()["error"]["details"]) == (
        400,
        {"argument": "quality", "choices": ["high", "small"]},
    )


def test_an_unknown_estimate_parameter_is_refused_without_repeating_its_name(
    assistant: TestClient, cut_id: int
) -> None:
    typed = "segredo-digitado"

    response = assistant.get(f"/api/cuts/{cut_id}/renders/estimate", params={typed: "1"})

    assert (
        response.status_code,
        response.json()["error"].get("details"),
        typed in response.text,
    ) == (
        400,
        None,
        False,
    )


def without_path(export: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in export.items() if key != "path"}


def test_the_exports_of_a_cut_answer_as_the_cli_lists_them_newest_first_without_paths(
    assistant: TestClient, home: Home, cut_id: int, export: Any
) -> None:
    older = export(cut_id, NOW)
    newer = export(cut_id, NOW + timedelta(minutes=5))

    response = assistant.get(f"/api/cuts/{cut_id}/renders")

    with closing(connect(home)) as connection:
        expected = list_renders(connection, home, cut_id)
    assert (
        response.status_code,
        response.json(),
        [item["id"] for item in expected["items"]],
        str(home.root) in response.text,
    ) == (
        200,
        {"items": [without_path(item) for item in expected["items"]]},
        [newer, older],
        False,
    )


def test_an_export_answers_as_the_cli_shows_it_without_its_path(
    assistant: TestClient, home: Home, cut_id: int, export: Any
) -> None:
    render_id = export(cut_id)

    response = assistant.get(f"/api/renders/{render_id}")

    with closing(connect(home)) as connection:
        expected = show_render(connection, home, render_id)
    assert (response.status_code, response.json(), str(home.root) in response.text) == (
        200,
        without_path(expected),
        False,
    )


@pytest.mark.parametrize(
    ("path", "details"),
    [
        ("/api/renders/99", {"render_id": 99}),
        ("/api/renders/99/file", {"render_id": 99}),
        ("/api/cuts/99/renders", {"cut_id": 99}),
    ],
)
def test_a_missing_export_or_cut_is_not_found_with_its_id(
    path: str, details: dict[str, int], assistant: TestClient
) -> None:
    response = assistant.get(path)

    assert (response.status_code, response.json()["error"]["details"]) == (404, details)


@pytest.mark.parametrize("title", ["Graça que alcança", "Pregação de sábado"])
def test_the_file_of_an_export_downloads_with_the_readable_name_even_with_the_lock_held(
    title: str, assistant: TestClient, add_cut: Any, export: Any, lock_owner: Any
) -> None:
    render_id = export(add_cut("chosen", title))
    lock_owner("render", "cut 99")

    response = assistant.get(f"/api/renders/{render_id}/file")

    assert (
        response.status_code,
        response.content,
        response.headers["content-type"],
        response.headers["content-disposition"],
    ) == (
        200,
        VIDEO,
        "video/mp4",
        # RFC 6266 §4.3: a name with spaces or accents goes UTF-8 and percent-encoded.
        f"attachment; filename*=utf-8''{quote(f'2026-10-18 - {title}.mp4')}",
    )


def test_an_export_whose_file_is_gone_is_an_internal_error_without_the_path(
    assistant: TestClient, home: Home, cut_id: int, export: Any
) -> None:
    render_id = export(cut_id)
    for file in home.cut_media(cut_id).iterdir():
        file.unlink()

    response = assistant.get(f"/api/renders/{render_id}/file")

    assert (
        response.status_code,
        response.json()["error"]["code"],
        response.json()["error"]["details"],
        str(home.root) in response.text,
    ) == (500, "internal_error", {"render_id": render_id}, False)
