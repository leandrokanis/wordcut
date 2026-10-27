"""The routes of a sermon's timeline media: prepare it and read its thumbnails and waveform.

The media files are written here by hand; nothing reaches YouTube.
"""

from __future__ import annotations

import json
from typing import Any

from fastapi.testclient import TestClient

from wordcut.home import Home

# Arbitrary bytes standing for the JPEG strip of thumbnails.
STRIP = b"\xff\xd8\xff\xe0strip-of-thumbnails\xff\xd9"
LAYOUT = {"width": 160, "height": 90, "times": [0.0, 30.0, 60.0]}
WAVEFORM = {"buckets": 4, "peaks": [0.0, 0.25, 1.0, 0.5]}
MEDIA = ("thumbnails", "thumbnails.json", "waveform")


def write_media(home: Home, sermon_id: int, *, thumbnails: bool = True) -> None:
    folder = home.sermon_timeline(sermon_id)
    folder.mkdir(parents=True)
    (folder / "waveform.json").write_text(json.dumps(WAVEFORM))
    if thumbnails:
        (folder / "thumbnails.json").write_text(json.dumps(LAYOUT))
        (folder / "thumbnails.jpg").write_bytes(STRIP)


def test_preparing_answers_202_with_the_launched_task(
    assistant: TestClient, processed_sermon_id: int, harmless_tasks: list[Any]
) -> None:
    response = assistant.post(f"/api/sermons/{processed_sermon_id}/prepare")

    task = response.json()
    shown = assistant.get(f"/api/sermons/{processed_sermon_id}").json()
    assert (response.status_code, task, shown["timeline"]) == (
        202,
        {
            "task_id": task["task_id"],
            "kind": "prepare",
            "status": "running",
            "sermon_id": processed_sermon_id,
        },
        {"status": "pending", "error": None, "task_id": task["task_id"]},
    )


def test_preparing_while_one_runs_is_409_busy_naming_that_task(
    assistant: TestClient, processed_sermon_id: int, harmless_tasks: list[Any]
) -> None:
    running = assistant.post(f"/api/sermons/{processed_sermon_id}/prepare").json()

    response = assistant.post(f"/api/sermons/{processed_sermon_id}/prepare")

    error = response.json()["error"]
    assert (response.status_code, error["code"], error["details"]["task_id"]) == (
        409,
        "busy",
        running["task_id"],
    )


def test_preparing_an_unknown_sermon_is_404(assistant: TestClient) -> None:
    response = assistant.post("/api/sermons/99/prepare")

    assert (response.status_code, response.json()["error"]["code"]) == (404, "not_found")


def test_the_prepared_media_is_served_as_the_strip_its_layout_and_the_peaks(
    assistant: TestClient, home: Home, processed_sermon_id: int
) -> None:
    write_media(home, processed_sermon_id)
    base = f"/api/sermons/{processed_sermon_id}"

    strip = assistant.get(f"{base}/thumbnails")
    layout = assistant.get(f"{base}/thumbnails.json")
    peaks = assistant.get(f"{base}/waveform")

    assert (strip.status_code, strip.headers["content-type"], strip.content) == (
        200,
        "image/jpeg",
        STRIP,
    )
    assert (layout.json(), peaks.json()) == (LAYOUT, WAVEFORM)
    assert str(home.root) not in layout.text + peaks.text


def test_media_not_prepared_is_404_with_the_error_object_never_500(
    assistant: TestClient, home: Home, processed_sermon_id: int
) -> None:
    base = f"/api/sermons/{processed_sermon_id}"

    answers = [assistant.get(f"{base}/{media}") for media in MEDIA]

    assert [(answer.status_code, answer.json()["error"]["code"]) for answer in answers] == [
        (404, "not_found")
    ] * 3


def test_a_live_without_storyboard_serves_the_peaks_and_404_for_the_thumbnails(
    assistant: TestClient, home: Home, processed_sermon_id: int
) -> None:
    write_media(home, processed_sermon_id, thumbnails=False)
    base = f"/api/sermons/{processed_sermon_id}"

    answers = [assistant.get(f"{base}/{media}").status_code for media in MEDIA]

    assert answers == [404, 404, 200]


def test_media_of_an_unknown_sermon_is_404(assistant: TestClient) -> None:
    answers = [assistant.get(f"/api/sermons/99/{media}") for media in MEDIA]

    assert [answer.status_code for answer in answers] == [404] * 3
