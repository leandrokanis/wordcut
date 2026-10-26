import json
import sqlite3
import subprocess
import sys
from collections.abc import Callable, Iterator
from contextlib import closing
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from wordcut import suggestion
from wordcut.db import connect, cuts, sermons, tasks, transcripts
from wordcut.db.cuts import NewCut, Segment
from wordcut.db.presets import SecondsRange
from wordcut.db.sermons import NewSermon, SuggestionError
from wordcut.db.tasks import NewTask
from wordcut.errors import WordcutError
from wordcut.home import Home
from wordcut.lock import ProcessingLock
from wordcut.processing.sentences import Sentence
from wordcut.service.presets import (
    create_preset,
    default_preset,
    delete_preset,
    show_preset,
    update_preset,
)
from wordcut.service.sermons import show_sermon
from wordcut.service.settings import store_llm_key, update_settings
from wordcut.service.suggestion import start_suggestion
from wordcut.service.tasks import show_task, wait_task
from wordcut.suggestion import SuggestionModel
from wordcut.suggestion.request import build_request
from wordcut.tasks import Progress, execution
from wordcut.tasks.processes import this_host
from wordcut.transcript import Word

# Fictitious key; while the suite runs, the real LLM refuses to be built (ADR-0017).
SENTINEL_KEY = "sk-or-v1-sentinela-ficticia-7f3a"
MODEL = "provedor/modelo-de-teste"
SENTENCE_SECONDS = 10.0
SENTENCE_COUNT = 12
PROCESSED_AT = datetime(2026, 10, 26, 21, 0, tzinfo=timezone.utc)
# The cuts a new suggestion finds: only the unedited suggestion may go.
EARLIER_CUTS = (
    ("Sugerido antigo", "suggested"),
    ("Sugerido editado", "suggested"),
    ("Escolhido", "chosen"),
    ("Descartado", "discarded"),
)


@dataclass
class ScriptedModel:
    """``SuggestionModel`` double: gives its answers in turn and keeps the messages it got."""

    answers: list[str | WordcutError]
    calls: list[tuple[str, str]] = field(default_factory=list)

    def complete(self, system: str, user: str) -> str:
        self.calls.append((system, user))
        answer = self.answers.pop(0)
        if isinstance(answer, WordcutError):
            raise answer
        return answer


@dataclass
class ModelFactory:
    """Stands in for ``suggestion.default_model``: hands out ``model``."""

    model: SuggestionModel

    def __call__(self, llm_model: str, key: str) -> SuggestionModel:
        return self.model


def answer(*cuts: tuple[str, list[int]]) -> str:
    return json.dumps({"cuts": [{"title": title, "sentences": ids} for title, ids in cuts]})


def install(monkeypatch: pytest.MonkeyPatch, *answers: str | WordcutError) -> ScriptedModel:
    model = ScriptedModel(list(answers))
    monkeypatch.setattr(suggestion, "default_model", ModelFactory(model))
    return model


@pytest.fixture
def home(wordcut_home: Path) -> Home:
    return Home(wordcut_home)


@pytest.fixture
def connection(home: Home) -> Iterator[sqlite3.Connection]:
    with closing(connect(home)) as opened:
        yield opened


@pytest.fixture
def configured(connection: sqlite3.Connection) -> None:
    update_settings(connection, llm_model=MODEL)
    store_llm_key(SENTINEL_KEY)


def new_sermon(youtube_id: str) -> NewSermon:
    return NewSermon(
        youtube_id=youtube_id,
        url=f"https://youtu.be/{youtube_id}",
        title="Culto",
        service_date=date(2026, 10, 18),
        live_duration=7718.0,
        live_finished=True,
        created_at=datetime(2026, 10, 26, tzinfo=timezone.utc),
    )


def processed_sermon(connection: sqlite3.Connection, youtube_id: str = "Ab3_x-9QzLk") -> int:
    """A ``processed`` sermon of ``SENTENCE_COUNT`` 10 s sentences, with the earlier cuts."""
    sermon = sermons.insert(connection, new_sermon(youtube_id))
    words: list[Word] = []
    sentences: list[Sentence] = []
    for index in range(SENTENCE_COUNT):
        start = index * SENTENCE_SECONDS
        end = start + SENTENCE_SECONDS
        words += [Word("Frase", start, start + 1.0), Word(f"{index + 1}.", start + 1.0, end)]
        sentences.append(Sentence(2 * index, 2 * index + 1, start, end, f"Frase {index + 1}."))
    with connection:
        transcripts.replace(connection, sermon.id, words, sentences)
        sermons.record_processed(connection, sermon.id, 970.0, 1090.0, "sermon.mp4", PROCESSED_AT)
    first = transcripts.sentences_of(connection, sermon.id)[0]
    earlier = [
        NewCut(
            status=status,
            title=title,
            segments=(Segment(first.first_word_id, first.last_word_id),),
            range_start_word=first.first_word_id,
            range_end_word=first.last_word_id,
            source="llm",
            preset_id=None,
        )
        for title, status in EARLIER_CUTS
    ]
    with connection:
        cuts.insert_many(connection, sermon.id, earlier, PROCESSED_AT)
        connection.execute("UPDATE cuts SET edited = 1 WHERE title = 'Sugerido editado'")
    return sermon.id


def shown(connection: sqlite3.Connection, home: Home, sermon_id: int) -> dict[str, Any]:
    return show_sermon(connection, sermon_id, home=home)


def test_a_suggestion_in_the_foreground_replaces_the_suggestions_and_gives_the_new_cuts(
    home: Home, connection: sqlite3.Connection, configured: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    sermon_id = processed_sermon(connection)
    model = install(monkeypatch, answer(("Novo", [3, 4, 5, 6, 7, 8])))
    preset = default_preset(connection)
    sentences = transcripts.sentences_of(connection, sermon_id)

    task = start_suggestion(home, sermon_id, detach=False)

    sermon = shown(connection, home, sermon_id)
    [new] = [cut for cut in sermon["cuts"] if cut["title"] == "Novo"]
    assert (
        task.kind,
        task.status,
        task.result,
        [cut["title"] for cut in sermon["cuts"]],
        model.calls[0][0],
    ) == (
        "suggest",
        "succeeded",
        {
            "sermon_id": sermon_id,
            "preset_id": preset["id"],
            "suggested_cuts": [new],
            "suggestion_warnings": [],
        },
        ["Sugerido editado", "Escolhido", "Descartado", "Novo"],
        build_request(preset, sentences).system,
    )


def other_preset(connection: sqlite3.Connection) -> int:
    """A preset that is not the default, with a prompt of its own."""
    created = create_preset(connection, "Curtos")
    allowed = SecondsRange(30, 90)
    preset_id: int = update_preset(
        connection,
        created["id"],
        duration_allowed=allowed,
        duration_ideal=allowed,
        instructions="Prefira frases de efeito.",
    )["id"]
    return preset_id


def test_a_suggestion_with_a_preset_asks_with_its_prompt_and_saves_cuts_of_that_preset(
    home: Home, connection: sqlite3.Connection, configured: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    sermon_id = processed_sermon(connection)
    preset_id = other_preset(connection)
    model = install(monkeypatch, answer(("Novo", [3, 4, 5, 6, 7])))
    sentences = transcripts.sentences_of(connection, sermon_id)

    task = start_suggestion(home, sermon_id, preset_id, detach=False)

    assert task.result is not None
    [new] = task.result["suggested_cuts"]
    assert (model.calls[0][0], task.result["preset_id"], new["preset_id"]) == (
        build_request(show_preset(connection, preset_id), sentences).system,
        preset_id,
        preset_id,
    )


def test_suggest_is_a_kind_without_the_lock_that_a_new_interpreter_finds() -> None:
    probe = "from wordcut.tasks import kind; print(kind('suggest').needs_lock)"

    found = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True)

    assert (found.returncode, found.stdout) == (0, "False\n")


def test_a_suggestion_runs_while_another_process_holds_the_processing_lock(
    home: Home,
    connection: sqlite3.Connection,
    configured: None,
    monkeypatch: pytest.MonkeyPatch,
    lock_owner: Callable[[str, str], subprocess.Popen[str]],
) -> None:
    sermon_id = processed_sermon(connection)
    owner = lock_owner("render", "cut 34")
    install(monkeypatch, answer(("Novo", [3, 4, 5, 6, 7, 8])))

    task = start_suggestion(home, sermon_id, detach=False)

    holder = ProcessingLock(home).holder()
    assert (task.status, holder is not None and holder.pid) == ("succeeded", owner.pid)


def refusal(home: Home, sermon_id: int, preset_id: int | None = None) -> tuple[Any, ...]:
    """The error ``start_suggestion`` raises, and the tasks recorded after it."""
    with pytest.raises(WordcutError) as refused:
        start_suggestion(home, sermon_id, preset_id, detach=False)
    with closing(connect(home)) as connection:
        recorded = tasks.newest_first(connection)
    return refused.value.code, refused.value.details, recorded


def test_a_sermon_that_does_not_exist_is_refused_without_a_task(
    home: Home, configured: None
) -> None:
    assert refusal(home, 404) == ("not_found", {"sermon_id": 404}, [])


@pytest.mark.parametrize("status", ["created", "trimmed", "processing", "failed"])
def test_a_sermon_not_processed_is_refused_without_a_task(
    home: Home, connection: sqlite3.Connection, configured: None, status: str
) -> None:
    sermon_id = processed_sermon(connection)
    with connection:
        sermons.set_status(connection, sermon_id, status, PROCESSED_AT)

    assert refusal(home, sermon_id) == (
        "sermon_not_processed",
        {"sermon_id": sermon_id, "status": status},
        [],
    )


def test_a_preset_that_does_not_exist_is_refused_without_a_task(
    home: Home, connection: sqlite3.Connection, configured: None
) -> None:
    sermon_id = processed_sermon(connection)

    assert refusal(home, sermon_id, 404) == ("not_found", {"preset_id": 404}, [])


@pytest.mark.parametrize(
    ("model_name", "key", "missing"),
    [(None, SENTINEL_KEY, ["llm_model"]), (MODEL, None, ["llm_key"])],
    ids=["no model", "no key"],
)
def test_without_the_llm_configured_nothing_changes_and_no_task_is_recorded(
    home: Home,
    connection: sqlite3.Connection,
    model_name: str | None,
    key: str | None,
    missing: list[str],
) -> None:
    if model_name is not None:
        update_settings(connection, llm_model=model_name)
    if key is not None:
        store_llm_key(key)
    sermon_id = processed_sermon(connection)
    with connection:
        sermons.record_suggestion_error(
            connection, sermon_id, SuggestionError("llm_error", "A anterior falhou.")
        )
    before = shown(connection, home, sermon_id)

    refused = refusal(home, sermon_id)

    assert (refused, shown(connection, home, sermon_id)) == (
        ("llm_not_configured", {"missing": missing}, []),
        before,
    )


def test_a_second_suggestion_of_a_sermon_while_one_runs_is_busy_naming_the_running_one(
    home: Home,
    connection: sqlite3.Connection,
    configured: None,
    harmless_tasks: list[subprocess.Popen[bytes]],
) -> None:
    sermon_id = processed_sermon(connection)
    running = start_suggestion(home, sermon_id, detach=True)

    refused = refusal(home, sermon_id)

    with closing(connect(home)) as reading:
        assert (refused[:2], tasks.newest_first(reading)) == (
            (
                "busy",
                {
                    "task_id": running.id,
                    "kind": "suggest",
                    "started_at": running.started_at.isoformat(),
                },
            ),
            [running],
        )


def test_a_suggestion_running_for_another_sermon_does_not_block(
    home: Home,
    connection: sqlite3.Connection,
    configured: None,
    monkeypatch: pytest.MonkeyPatch,
    harmless_tasks: list[subprocess.Popen[bytes]],
) -> None:
    sermon_id = processed_sermon(connection)
    start_suggestion(home, processed_sermon(connection, "Zz9_y-8PqRs"), detach=True)
    install(monkeypatch, answer(("Novo", [3, 4, 5, 6, 7, 8])))

    assert start_suggestion(home, sermon_id, detach=False).status == "succeeded"


def test_a_finished_suggestion_of_the_sermon_does_not_block(
    home: Home, connection: sqlite3.Connection, configured: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    sermon_id = processed_sermon(connection)
    install(
        monkeypatch,
        answer(("Primeiro", [3, 4, 5, 6, 7, 8])),
        answer(("Segundo", [3, 4, 5, 6, 7, 8])),
    )
    start_suggestion(home, sermon_id, detach=False)

    assert start_suggestion(home, sermon_id, detach=False).status == "succeeded"


def test_a_suggestion_whose_process_is_gone_does_not_block(
    home: Home, connection: sqlite3.Connection, configured: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    sermon_id = processed_sermon(connection)
    ended = subprocess.Popen(["true"])
    ended.wait()
    tasks.insert(
        connection,
        NewTask(
            kind="suggest",
            resource_type="sermon",
            resource_id=sermon_id,
            params={"preset_id": default_preset(connection)["id"]},
            pid=ended.pid,
            host=this_host(),
            started_at=PROCESSED_AT,
        ),
    )
    install(monkeypatch, answer(("Novo", [3, 4, 5, 6, 7, 8])))

    assert start_suggestion(home, sermon_id, detach=False).status == "succeeded"


def test_the_suggestion_reports_its_stage(
    home: Home, connection: sqlite3.Connection, configured: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    sermon_id = processed_sermon(connection)
    install(monkeypatch, answer(("Novo", [3, 4, 5, 6, 7, 8])))
    heard: list[Progress] = []

    start_suggestion(home, sermon_id, detach=False, on_progress=heard.append)

    assert [(progress.kind, progress.message) for progress in heard] == [("suggest", "sugerindo")]


def test_an_llm_failure_fails_the_task_with_llm_error_and_leaves_the_cuts(
    home: Home, connection: sqlite3.Connection, configured: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    sermon_id = processed_sermon(connection)
    before = shown(connection, home, sermon_id)["cuts"]
    install(monkeypatch, "Primeira.", "Segunda.")
    with pytest.raises(WordcutError):
        start_suggestion(home, sermon_id, detach=False)
    [task] = tasks.newest_first(connection)

    with pytest.raises(WordcutError) as waited:
        wait_task(home, task.id)

    sermon = shown(connection, home, sermon_id)
    assert (
        (task.status, task.error_code, waited.value.code, waited.value.exit_code),
        sermon["cuts"],
        sermon["suggestion_error"]["code"],
    ) == (("failed", "llm_error", "llm_error", 6), before, "llm_error")


def test_a_real_detached_suggestion_meets_the_network_guard_and_leaves_no_process(
    home: Home,
    connection: sqlite3.Connection,
    configured: None,
    detached_tasks: list[subprocess.Popen[bytes]],
) -> None:
    sermon_id = processed_sermon(connection)
    launched = start_suggestion(home, sermon_id, detach=True)

    with pytest.raises(WordcutError) as failed:
        wait_task(home, launched.id)

    [process] = detached_tasks
    assert (failed.value.code, failed.value.details, process.wait()) == (
        "network_error",
        {"forbidden_by": "WORDCUT_FORBID_NETWORK"},
        0,
    )


def test_a_preset_deleted_before_the_task_runs_fails_it_as_not_found(
    home: Home,
    connection: sqlite3.Connection,
    configured: None,
    harmless_tasks: list[subprocess.Popen[bytes]],
) -> None:
    sermon_id = processed_sermon(connection)
    preset_id = other_preset(connection)
    launched = start_suggestion(home, sermon_id, preset_id, detach=True)
    delete_preset(connection, preset_id)

    execution.resume(home, launched.id, None)

    task = show_task(home, launched.id)
    assert (task["status"], task["error"]["code"], task["error"]["details"]) == (
        "failed",
        "not_found",
        {"preset_id": preset_id},
    )


@dataclass
class ReprocessingModel:
    """Answers ``answered`` once another connection has processed the sermon again."""

    home: Home
    sermon_id: int
    answered: str

    def complete(self, system: str, user: str) -> str:
        with closing(connect(self.home)) as other, other:
            later = PROCESSED_AT.replace(hour=22)
            sermons.record_processed(other, self.sermon_id, 970.0, 1090.0, "sermon.mp4", later)
        return self.answered


def test_a_sermon_reprocessed_during_the_suggestion_fails_the_task_without_saving(
    home: Home, connection: sqlite3.Connection, configured: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    sermon_id = processed_sermon(connection)
    before = shown(connection, home, sermon_id)
    model = ReprocessingModel(home, sermon_id, answer(("Novo", [3, 4, 5, 6, 7, 8])))
    monkeypatch.setattr(suggestion, "default_model", ModelFactory(model))

    with pytest.raises(WordcutError):
        start_suggestion(home, sermon_id, detach=False)

    [task] = tasks.newest_first(connection)
    sermon = shown(connection, home, sermon_id)
    assert (
        (task.status, task.error_code),
        sermon["cuts"],
        sermon["suggestion_error"],
    ) == (("failed", "sermon_not_processed"), before["cuts"], before["suggestion_error"])
