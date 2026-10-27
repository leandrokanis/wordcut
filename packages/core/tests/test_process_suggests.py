import json
import sqlite3
from collections.abc import Iterator
from contextlib import closing
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import httpx
import pytest

from wordcut import processing, suggestion
from wordcut.db import connect, transcripts
from wordcut.db.tasks import TaskRow
from wordcut.home import Home
from wordcut.processing import OnProgress
from wordcut.service.presets import build_prompt, default_preset
from wordcut.service.sermons import create_sermon, show_sermon
from wordcut.service.settings import store_llm_key, update_settings
from wordcut.suggestion import SuggestionModel
from wordcut.suggestion.model import OpenRouterModel
from wordcut.tasks import Resource
from wordcut.tasks.execution import start
from wordcut.transcript import Transcript, Word
from wordcut.youtube import LiveInfo

LINK = "https://youtu.be/Ab3_x-9QzLk"
FINISHED_LIVE = LiveInfo(
    title="Culto de domingo",
    service_date=date(2026, 10, 18),
    duration=7718.0,
    live_status="was_live",
)
SECTION_START = 970.0
# Fictitious: no test ever reaches OpenRouter.
SENTINEL_KEY = "sk-or-v1-sentinela-ficticia-7f3a"
MODEL = "provedor/modelo-de-teste"
SENTENCES = 10


class FakeLive:
    def info(self, url: str) -> LiveInfo:
        return FINISHED_LIVE


class FakeGateways:
    """Ten one-word sentences of 9.5 s each, every 10 s from 1000 s of the live."""

    def download_section(
        self, url: str, start: float, end: float, output: Path, *, on_progress: OnProgress
    ) -> Path:
        return output

    def download_audio_window(
        self, url: str, start: float, end: float, output: Path, *, on_progress: OnProgress
    ) -> Path:
        return output

    def locate(self, recording: Path, clip: Path, expected_start: float, search: float) -> float:
        return expected_start

    def transcribe(self, media: Path, workdir: Path, *, on_progress: OnProgress) -> Transcript:
        words = tuple(
            Word(f"Frase{number}.", 1000.0 + 10 * number, 1009.5 + 10 * number).shifted(
                -SECTION_START
            )
            for number in range(SENTENCES)
        )
        return Transcript(words=words, language="pt", model="fake")

    def duration(self, media: Path) -> float:
        return 200.0

    def cut(self, source: Path, start: float, end: float, output: Path) -> Path:
        output.write_bytes(b"sermon")
        return output


@dataclass
class ScriptedModel:
    """``SuggestionModel`` double: gives its answers in turn and keeps the messages it got."""

    answers: list[str]
    calls: list[tuple[str, str]] = field(default_factory=list)

    def complete(self, system: str, user: str) -> str:
        self.calls.append((system, user))
        return self.answers.pop(0)


@dataclass
class ModelFactory:
    """Stands in for ``suggestion.default_model``: hands out ``model`` and keeps its arguments."""

    model: ScriptedModel
    built_with: list[tuple[str, str]] = field(default_factory=list)

    def __call__(self, llm_model: str, key: str) -> SuggestionModel:
        self.built_with.append((llm_model, key))
        return self.model


def answer(*cuts: tuple[str, list[int]]) -> str:
    return json.dumps({"cuts": [{"title": title, "sentences": ids} for title, ids in cuts]})


@pytest.fixture
def home(wordcut_home: Path, monkeypatch: pytest.MonkeyPatch) -> Home:
    monkeypatch.setattr(processing, "default_gateways", lambda whisper_model: FakeGateways())
    return Home(wordcut_home)


@pytest.fixture
def connection(home: Home) -> Iterator[sqlite3.Connection]:
    with closing(connect(home)) as opened:
        yield opened


@pytest.fixture
def configured(connection: sqlite3.Connection) -> None:
    update_settings(connection, llm_model=MODEL)
    store_llm_key(SENTINEL_KEY)


def install(monkeypatch: pytest.MonkeyPatch, *answers: str) -> ModelFactory:
    factory = ModelFactory(ScriptedModel(list(answers)))
    monkeypatch.setattr(suggestion, "default_model", factory)
    return factory


def trimmed_sermon(connection: sqlite3.Connection) -> int:
    sermon_id: int = create_sermon(
        connection, FakeLive(), LINK, start=1000.0, end=1100.0, home=Home.from_environment()
    )["id"]
    return sermon_id


def process(home: Home, sermon_id: int, *, force: bool = False) -> TaskRow:
    return start(home, "process", Resource("sermon", sermon_id), {"force": force}, detach=False)


def shown(connection: sqlite3.Connection, home: Home, sermon_id: int) -> dict[str, Any]:
    return show_sermon(connection, sermon_id, home=home)


def test_processing_ends_by_saving_the_cuts_the_llm_suggests_with_the_default_preset(
    home: Home, connection: sqlite3.Connection, configured: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    sermon_id = trimmed_sermon(connection)
    factory = install(monkeypatch, answer(("Graça que alcança", [1, 2, 3, 4, 5, 6])))

    task = process(home, sermon_id)

    sermon = shown(connection, home, sermon_id)
    [(system, user)] = factory.model.calls
    del sermon["last_task"]
    assert (
        sermon["status"],
        [(cut["title"], cut["status"], cut["preset_id"]) for cut in sermon["cuts"]],
        system.startswith(build_prompt(default_preset(connection))),
        len(user.splitlines()),
        task.result,
    ) == (
        "processed",
        [("Graça que alcança", "suggested", default_preset(connection)["id"])],
        True,
        SENTENCES,
        {**sermon, "suggestion_warnings": []},
    )


def test_a_failed_suggestion_leaves_the_task_succeeded_and_the_sermon_processed(
    home: Home, connection: sqlite3.Connection, configured: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    sermon_id = trimmed_sermon(connection)
    install(monkeypatch, "Primeira.", "Segunda.")

    task = process(home, sermon_id)

    sermon = shown(connection, home, sermon_id)
    assert (
        (task.status, task.error_code),
        sermon["status"],
        len(transcripts.sentences_of(connection, sermon_id)),
        sermon["cuts"],
        sermon["suggestion_error"]["code"],
        task.result is not None and task.result["suggestion_error"] == sermon["suggestion_error"],
    ) == (("succeeded", None), "processed", SENTENCES, [], "llm_error", True)


def test_without_the_llm_configured_the_sermon_is_processed_without_cuts_nor_a_call(
    home: Home, connection: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    sermon_id = trimmed_sermon(connection)
    factory = install(monkeypatch, answer(("Corte", [1, 2, 3, 4, 5, 6])))

    task = process(home, sermon_id)

    sermon = shown(connection, home, sermon_id)
    assert (
        task.status,
        sermon["status"],
        sermon["cuts"],
        sermon["suggestion_error"]["code"],
        factory.built_with,
    ) == ("succeeded", "processed", [], "llm_not_configured", [])


def test_openrouter_out_of_reach_leaves_the_sermon_processed_not_failed(
    home: Home, connection: sqlite3.Connection, configured: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    def unreachable(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("conexão recusada", request=request)

    def real_model_without_network(llm_model: str, key: str) -> SuggestionModel:
        client = httpx.Client(transport=httpx.MockTransport(unreachable))
        return OpenRouterModel(llm_model, key, client)

    monkeypatch.setattr(suggestion, "default_model", real_model_without_network)
    sermon_id = trimmed_sermon(connection)

    task = process(home, sermon_id)

    sermon = shown(connection, home, sermon_id)
    assert (task.status, sermon["status"], sermon["suggestion_error"]["code"]) == (
        "succeeded",
        "processed",
        "llm_error",
    )


def test_reprocessing_with_force_replaces_the_old_cuts_with_the_new_suggestion(
    home: Home, connection: sqlite3.Connection, configured: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    sermon_id = trimmed_sermon(connection)
    install(
        monkeypatch,
        answer(("Antigo", [1, 2, 3, 4, 5, 6])),
        answer(("Novo", [4, 5, 6, 7, 8, 9])),
    )
    process(home, sermon_id)

    task = process(home, sermon_id, force=True)

    sermon = shown(connection, home, sermon_id)
    assert (task.status, [cut["title"] for cut in sermon["cuts"]]) == ("succeeded", ["Novo"])


def test_the_llm_key_reaches_only_the_request_never_the_task_the_sermon_or_the_log(
    home: Home,
    connection: sqlite3.Connection,
    configured: None,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level("DEBUG")
    authorizations: list[str] = []

    def refusing_and_echoing(request: httpx.Request) -> httpx.Response:
        authorizations.append(request.headers["Authorization"])
        return httpx.Response(401, json={"error": {"message": f"Chave {SENTINEL_KEY} inválida"}})

    def real_model(llm_model: str, key: str) -> SuggestionModel:
        client = httpx.Client(transport=httpx.MockTransport(refusing_and_echoing))
        return OpenRouterModel(llm_model, key, client)

    monkeypatch.setattr(suggestion, "default_model", real_model)
    sermon_id = trimmed_sermon(connection)

    process(home, sermon_id)

    task_rows = connection.execute("SELECT * FROM tasks").fetchall()
    sermon = shown(connection, home, sermon_id)
    exposed = " ".join([str(task_rows), json.dumps(sermon, ensure_ascii=False), caplog.text])
    assert (authorizations, SENTINEL_KEY in exposed, sermon["suggestion_error"]["code"]) == (
        [f"Bearer {SENTINEL_KEY}"],
        False,
        "llm_error",
    )
