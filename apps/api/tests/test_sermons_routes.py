from contextlib import closing
from datetime import date, datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from wordcut.db import connect, sermons, transcripts
from wordcut.db.sermons import NewSermon
from wordcut.home import Home
from wordcut.lock import ProcessingLock
from wordcut.processing.sentences import Sentence
from wordcut.service.sermons import SERMON_STATES, create_sermon, list_sermons, show_sermon
from wordcut.service.settings import store_llm_key, update_settings
from wordcut.service.tasks import list_tasks
from wordcut.tasks import Resource
from wordcut.transcript import Word
from wordcut.youtube import LiveInfo, YouTubeError
from wordcut_api import deps

LINK = "https://youtu.be/Ab3_x-9QzLk"
OTHER_LINK = "https://youtu.be/Zz9_y-8PwKm"
NOW = datetime(2026, 10, 26, 19, 40, tzinfo=timezone(timedelta(hours=-3)))
# Arbitrary, non-repeating bytes standing for the processed 16:9 video.
VIDEO = bytes(range(256)) * 4 + b"amen"
WORDS = (Word("Irmãos,", 0.0, 0.5), Word("graça.", 0.5, 1.0), Word("Amém.", 99.0, 100.0))
SENTENCES = (Sentence(0, 1, 0.0, 1.0, "Irmãos, graça."), Sentence(2, 2, 99.0, 100.0, "Amém."))
FINISHED_LIVE = LiveInfo(
    title="Culto de domingo",
    service_date=date(2026, 10, 18),
    duration=7200.0,
    live_status="was_live",
)


class FakeLive:
    """``LiveSource`` double: answers ``info`` or raises ``error``, counting the calls."""

    def __init__(self) -> None:
        self.info_answer = FINISHED_LIVE
        self.error: YouTubeError | None = None
        self.calls = 0

    def info(self, url: str) -> LiveInfo:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.info_answer


@pytest.fixture
def live(monkeypatch: pytest.MonkeyPatch) -> FakeLive:
    fake = FakeLive()
    monkeypatch.setattr(deps, "live_source", lambda: fake)
    return fake


def processed_sermon(home: Home, title: str = "Culto de domingo") -> int:
    """The ID of a processed sermon with a transcript of two sentences and its video."""
    new = NewSermon(
        youtube_id="Ab3_x-9QzLk",
        url=LINK,
        title=title,
        service_date=FINISHED_LIVE.service_date,
        live_duration=FINISHED_LIVE.duration,
        live_finished=True,
        created_at=NOW,
    )
    with closing(connect(home)) as connection:
        sermon_id = sermons.insert(connection, new).id
        sermons.update_range(connection, sermon_id, 1000.0, 1100.0, "trimmed", NOW)
        video = home.sermon_media(sermon_id) / "sermon.mp4"
        video.parent.mkdir(parents=True)
        video.write_bytes(VIDEO)
        with connection:
            transcripts.replace(connection, sermon_id, WORDS, SENTENCES)
            sermons.record_processed(
                connection, sermon_id, 1000.0, 1100.0, str(video.relative_to(home.root)), NOW
            )
    return sermon_id


def test_creating_a_sermon_answers_201_with_the_sermon_the_cli_shows(
    assistant: TestClient, live: FakeLive, home: Home
) -> None:
    response = assistant.post("/api/sermons", json={"url": LINK})

    with closing(connect(home)) as connection:
        again = create_sermon(connection, live, LINK)
    assert (response.status_code, response.json()) == (201, {**again, "created": True})


def test_the_same_video_again_answers_200_with_created_false_without_asking_youtube(
    assistant: TestClient, live: FakeLive
) -> None:
    first = assistant.post("/api/sermons", json={"url": LINK}).json()

    response = assistant.post("/api/sermons", json={"url": LINK})

    assert (response.status_code, response.json(), live.calls) == (
        200,
        {**first, "created": False},
        1,
    )


def test_youtube_failing_to_answer_is_a_bad_gateway_with_youtube_error(
    assistant: TestClient, live: FakeLive
) -> None:
    live.error = YouTubeError("Vídeo indisponível.")

    response = assistant.post("/api/sermons", json={"url": LINK})

    assert (response.status_code, response.json()["error"]["code"]) == (502, "youtube_error")


def test_listing_answers_the_sermons_as_the_cli_lists_them_latest_service_first(
    assistant: TestClient, live: FakeLive, home: Home
) -> None:
    assistant.post("/api/sermons", json={"url": LINK})
    live.info_answer = LiveInfo("Culto de quarta", date(2026, 10, 21), 5400.0, "was_live")
    assistant.post("/api/sermons", json={"url": OTHER_LINK})

    response = assistant.get("/api/sermons")

    with closing(connect(home)) as connection:
        expected = list_sermons(connection, home=home)
    assert (
        response.status_code,
        response.json(),
        [item["title"] for item in expected["items"]],
    ) == (
        200,
        expected,
        ["Culto de quarta", "Culto de domingo"],
    )


def test_listing_by_status_answers_only_the_sermons_in_that_status(
    assistant: TestClient, live: FakeLive, home: Home
) -> None:
    created = assistant.post("/api/sermons", json={"url": LINK}).json()
    trimmed = assistant.post("/api/sermons", json={"url": OTHER_LINK}).json()
    with closing(connect(home)) as connection:
        sermons.update_range(connection, trimmed["id"], 1000.0, 1100.0, "trimmed", NOW)

    response = assistant.get("/api/sermons", params={"status": "created"})

    assert [item["id"] for item in response.json()["items"]] == [created["id"]]


def test_a_status_outside_the_choices_is_invalid_argument_with_the_choices_without_echo(
    assistant: TestClient,
) -> None:
    typed = "segredo-digitado-errado"

    response = assistant.get("/api/sermons", params={"status": typed})

    assert (response.status_code, response.json(), typed in response.text) == (
        400,
        {
            "error": {
                "code": "invalid_argument",
                "message": f"Valor inválido para status; use um de: {', '.join(SERMON_STATES)}.",
                "details": {"argument": "status", "choices": list(SERMON_STATES)},
            }
        },
        False,
    )


def test_showing_a_sermon_answers_it_as_the_cli_shows_it(
    assistant: TestClient, live: FakeLive, home: Home
) -> None:
    created = assistant.post("/api/sermons", json={"url": LINK}).json()

    response = assistant.get(f"/api/sermons/{created['id']}")

    with closing(connect(home)) as connection:
        expected = show_sermon(connection, created["id"], home=home)
    assert (response.status_code, response.json()) == (200, expected)


def test_showing_with_the_transcript_adds_the_sentences_as_the_cli_shows_them(
    assistant: TestClient, home: Home
) -> None:
    sermon_id = processed_sermon(home)

    response = assistant.get(f"/api/sermons/{sermon_id}", params={"transcript": "true"})

    with closing(connect(home)) as connection:
        expected = show_sermon(connection, sermon_id, home=home, transcript=True)
    assert (response.json(), len(response.json()["sentences"])) == (expected, 2)


def test_showing_a_missing_sermon_is_not_found_with_its_id(assistant: TestClient) -> None:
    response = assistant.get("/api/sermons/99")

    assert (response.status_code, response.json()) == (
        404,
        {
            "error": {
                "code": "not_found",
                "message": "Pregação 99 não existe.",
                "details": {"sermon_id": 99},
            }
        },
    )


def test_an_id_that_is_not_a_number_is_invalid_argument_without_echo(
    assistant: TestClient,
) -> None:
    typed = "segredo-no-caminho"

    response = assistant.get(f"/api/sermons/{typed}")

    assert (response.status_code, response.json(), typed in response.text) == (
        400,
        {
            "error": {
                "code": "invalid_argument",
                "message": "Valor inválido para sermon_id.",
                "details": {"argument": "sermon_id"},
            }
        },
        False,
    )


def test_trimming_answers_the_trimmed_sermon_as_the_next_show_gives_it(
    assistant: TestClient, live: FakeLive
) -> None:
    created = assistant.post("/api/sermons", json={"url": LINK}).json()

    response = assistant.patch(f"/api/sermons/{created['id']}", json={"start": 1000.5, "end": 1100})

    shown = assistant.get(f"/api/sermons/{created['id']}").json()
    assert (response.status_code, response.json(), shown["status"], shown["live_start"]) == (
        200,
        shown,
        "trimmed",
        1000.5,
    )


def test_trimming_a_processed_sermon_answers_it_without_needs_reprocess(
    assistant: TestClient, home: Home
) -> None:
    sermon_id = processed_sermon(home)

    response = assistant.patch(f"/api/sermons/{sermon_id}", json={"start": 990, "end": 1110})

    shown = assistant.get(f"/api/sermons/{sermon_id}").json()
    assert (response.json(), shown["status"]) == (shown, "processed")


def test_trimming_without_the_end_is_invalid_argument_naming_it(
    assistant: TestClient, live: FakeLive
) -> None:
    created = assistant.post("/api/sermons", json={"url": LINK}).json()

    response = assistant.patch(f"/api/sermons/{created['id']}", json={"start": 1000})

    assert (response.status_code, response.json()) == (
        400,
        {
            "error": {
                "code": "invalid_argument",
                "message": "Argumento obrigatório ausente: end.",
                "details": {"argument": "end"},
            }
        },
    )


@pytest.mark.parametrize(
    ("borders", "refused"),
    [
        ({"start": 1000, "end": 1059.9}, (409, "sermon_too_short")),
        ({"start": 7100, "end": 7300}, (400, "invalid_argument")),
        ({"start": "1000", "end": 1100}, (400, "invalid_argument")),
    ],
    ids=["shorter than a minute", "outside the live", "seconds as text"],
)
def test_trimming_refuses_borders_the_cli_refuses(
    borders: dict[str, object], refused: tuple[int, str], assistant: TestClient, live: FakeLive
) -> None:
    created = assistant.post("/api/sermons", json={"url": LINK}).json()

    response = assistant.patch(f"/api/sermons/{created['id']}", json=borders)

    assert (response.status_code, response.json()["error"]["code"]) == refused


def test_trimming_a_sermon_being_processed_is_busy(assistant: TestClient, home: Home) -> None:
    sermon_id = processed_sermon(home)
    with closing(connect(home)) as connection, connection:
        sermons.set_status(connection, sermon_id, "processing", NOW)
    # A read leaves a sermon processing only while the lock is held for it.
    with ProcessingLock(home).acquire("process", str(Resource("sermon", sermon_id))):
        response = assistant.patch(f"/api/sermons/{sermon_id}", json={"start": 990, "end": 1110})

    assert (response.status_code, response.json()["error"]["code"]) == (409, "busy")


@pytest.mark.parametrize("title", ["Culto de domingo", "Pregação de sábado"])
def test_the_video_of_a_processed_sermon_downloads_with_the_readable_name(
    title: str, assistant: TestClient, home: Home
) -> None:
    sermon_id = processed_sermon(home, title=title)

    response = assistant.get(f"/api/sermons/{sermon_id}/video")

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


def test_the_video_of_a_processed_sermon_downloads_even_with_the_lock_held(
    assistant: TestClient, home: Home, lock_owner: Any
) -> None:
    sermon_id = processed_sermon(home)
    lock_owner("process", "sermon 99")

    response = assistant.get(f"/api/sermons/{sermon_id}/video")

    assert (response.status_code, response.content) == (200, VIDEO)


def test_the_video_of_a_sermon_not_processed_is_refused(
    assistant: TestClient, live: FakeLive
) -> None:
    created = assistant.post("/api/sermons", json={"url": LINK}).json()

    response = assistant.get(f"/api/sermons/{created['id']}/video")

    assert (response.status_code, response.json()["error"]["code"]) == (
        409,
        "sermon_not_processed",
    )


def trimmed_sermon(client: TestClient) -> int:
    """The ID of a sermon created from a finished live and trimmed, through the API."""
    created = client.post("/api/sermons", json={"url": LINK}).json()
    client.patch(f"/api/sermons/{created['id']}", json={"start": 1000, "end": 1100})
    return int(created["id"])


def test_processing_answers_202_with_the_launched_task_and_the_sermon_is_processing(
    assistant: TestClient, live: FakeLive, harmless_tasks: list[Any]
) -> None:
    sermon_id = trimmed_sermon(assistant)

    response = assistant.post(f"/api/sermons/{sermon_id}/process")

    task = response.json()
    shown = assistant.get(f"/api/sermons/{sermon_id}").json()
    assert (
        response.status_code,
        task,
        len(harmless_tasks),
        shown["status"],
        shown["last_task"]["id"],
    ) == (
        202,
        {
            "task_id": task["task_id"],
            "kind": "process",
            "status": "running",
            "sermon_id": sermon_id,
        },
        1,
        "processing",
        task["task_id"],
    )


def test_processing_a_processed_sermon_again_needs_force(
    assistant: TestClient, home: Home, harmless_tasks: list[Any]
) -> None:
    sermon_id = processed_sermon(home)

    without = assistant.post(f"/api/sermons/{sermon_id}/process")
    forced = assistant.post(f"/api/sermons/{sermon_id}/process", json={"force": True})

    assert (
        without.status_code,
        without.json()["error"]["code"],
        forced.status_code,
        len(harmless_tasks),
    ) == (409, "would_discard_edits", 202, 1)


def test_processing_a_sermon_without_borders_is_refused(
    assistant: TestClient, live: FakeLive, harmless_tasks: list[Any]
) -> None:
    created = assistant.post("/api/sermons", json={"url": LINK}).json()

    response = assistant.post(f"/api/sermons/{created['id']}/process")

    assert (response.status_code, response.json()["error"]["code"], harmless_tasks) == (
        409,
        "sermon_not_trimmed",
        [],
    )


def test_processing_while_the_live_is_still_on_air_is_refused(
    assistant: TestClient, live: FakeLive, harmless_tasks: list[Any]
) -> None:
    live.info_answer = LiveInfo("Culto ao vivo", date(2026, 10, 25), 7200.0, "is_live")
    sermon_id = trimmed_sermon(assistant)

    response = assistant.post(f"/api/sermons/{sermon_id}/process")

    assert (response.status_code, response.json()["error"]["code"], harmless_tasks) == (
        409,
        "live_not_finished",
        [],
    )


def test_processing_while_the_machine_is_busy_records_no_task(
    assistant: TestClient, live: FakeLive, home: Home, lock_owner: Any, harmless_tasks: list[Any]
) -> None:
    sermon_id = trimmed_sermon(assistant)
    lock_owner("process", "sermon 99")

    response = assistant.post(f"/api/sermons/{sermon_id}/process")

    error = response.json()["error"]
    assert (
        response.status_code,
        error["code"],
        error["details"]["resource"],
        list_tasks(home),
        harmless_tasks,
    ) == (409, "busy", "sermon 99", {"items": []}, [])


def test_processing_while_another_processing_runs_is_busy_naming_that_task(
    assistant: TestClient, live: FakeLive, home: Home, harmless_tasks: list[Any]
) -> None:
    first = assistant.post(f"/api/sermons/{trimmed_sermon(assistant)}/process").json()
    other = assistant.post("/api/sermons", json={"url": OTHER_LINK}).json()
    assistant.patch(f"/api/sermons/{other['id']}", json={"start": 1000, "end": 1100})

    response = assistant.post(f"/api/sermons/{other['id']}/process")

    error = response.json()["error"]
    assert (
        response.status_code,
        error["code"],
        error["details"]["task_id"],
        len(list_tasks(home)["items"]),
        len(harmless_tasks),
    ) == (409, "busy", first["task_id"], 1, 1)


# Fictitious; while the suite runs, the real LLM refuses to be built (ADR-0017).
LLM_KEY = "sk-or-v1-sentinela-ficticia-api"
LLM_MODEL = "provedor/modelo-de-teste"


def configure_llm(home: Home) -> None:
    with closing(connect(home)) as connection:
        update_settings(connection, llm_model=LLM_MODEL)
    store_llm_key(LLM_KEY)


def test_an_admin_asking_for_a_suggestion_gets_202_with_the_launched_task(
    admin: TestClient, home: Home, harmless_tasks: list[Any]
) -> None:
    sermon_id = processed_sermon(home)
    configure_llm(home)

    response = admin.post(f"/api/sermons/{sermon_id}/suggest")

    task = response.json()
    assert (response.status_code, task, len(harmless_tasks)) == (
        202,
        {
            "task_id": task["task_id"],
            "kind": "suggest",
            "status": "running",
            "sermon_id": sermon_id,
        },
        1,
    )


@pytest.mark.parametrize("existing", [True, False], ids=["existing sermon", "missing sermon"])
def test_an_assistant_asking_for_a_suggestion_is_forbidden_and_no_task_is_recorded(
    existing: bool, assistant: TestClient, home: Home, harmless_tasks: list[Any]
) -> None:
    sermon_id = processed_sermon(home) if existing else 99
    configure_llm(home)

    response = assistant.post(f"/api/sermons/{sermon_id}/suggest")

    assert (response.status_code, response.json()["error"]["code"], list_tasks(home)) == (
        403,
        "forbidden",
        {"items": []},
    )


def test_a_suggestion_with_a_missing_preset_is_not_found_naming_the_preset(
    admin: TestClient, home: Home, harmless_tasks: list[Any]
) -> None:
    sermon_id = processed_sermon(home)
    configure_llm(home)

    response = admin.post(f"/api/sermons/{sermon_id}/suggest", json={"preset_id": 99})

    error = response.json()["error"]
    assert (response.status_code, error["code"], error["details"], harmless_tasks) == (
        404,
        "not_found",
        {"preset_id": 99},
        [],
    )


def test_a_suggestion_for_a_sermon_not_processed_is_refused(
    admin: TestClient, live: FakeLive, home: Home, harmless_tasks: list[Any]
) -> None:
    configure_llm(home)
    created = admin.post("/api/sermons", json={"url": LINK}).json()

    response = admin.post(f"/api/sermons/{created['id']}/suggest")

    assert (response.status_code, response.json()["error"]["code"], harmless_tasks) == (
        409,
        "sermon_not_processed",
        [],
    )


def test_a_suggestion_without_the_llm_configured_is_refused(
    admin: TestClient, home: Home, harmless_tasks: list[Any]
) -> None:
    sermon_id = processed_sermon(home)

    response = admin.post(f"/api/sermons/{sermon_id}/suggest")

    assert (response.status_code, response.json()["error"]["code"], harmless_tasks) == (
        409,
        "llm_not_configured",
        [],
    )


def test_the_task_a_processing_launched_is_found_among_the_tasks(
    assistant: TestClient, live: FakeLive, harmless_tasks: list[Any]
) -> None:
    launched = assistant.post(f"/api/sermons/{trimmed_sermon(assistant)}/process").json()

    task = assistant.get(f"/api/tasks/{launched['task_id']}").json()

    assert (task["kind"], task["status"], task["sermon_id"]) == (
        "process",
        "running",
        launched["sermon_id"],
    )


def test_show_list_and_trim_tell_whether_the_borders_changed_since_processing(
    assistant: TestClient, home: Home
) -> None:
    sermon_id = processed_sermon(home)

    changed = assistant.patch(f"/api/sermons/{sermon_id}", json={"start": 990, "end": 1110})
    shown = assistant.get(f"/api/sermons/{sermon_id}").json()
    listed = assistant.get("/api/sermons").json()["items"]
    put_back = assistant.patch(f"/api/sermons/{sermon_id}", json={"start": 1000, "end": 1100})

    assert (
        changed.json()["borders_changed"],
        shown["borders_changed"],
        [item["borders_changed"] for item in listed],
        put_back.json()["borders_changed"],
    ) == (True, True, [True], False)
