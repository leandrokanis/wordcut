import json
import sqlite3
import subprocess
from collections.abc import Callable, Iterator
from contextlib import closing
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import pytest

from wordcut import suggestion
from wordcut.db import connect, cuts, sermons, transcripts
from wordcut.db.cuts import NewCut, Segment
from wordcut.db.presets import SecondsRange
from wordcut.db.sermons import NewSermon
from wordcut.home import Home
from wordcut.processing.sentences import Sentence
from wordcut.service.presets import create_preset, show_preset, update_preset
from wordcut.service.settings import store_llm_key, update_settings
from wordcut.suggestion import SuggestionModel
from wordcut.suggestion.model import OpenRouterModel
from wordcut.suggestion.request import build_request
from wordcut.transcript import Word
from wordcut_cli import main

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

    answers: list[str]
    calls: list[tuple[str, str]] = field(default_factory=list)

    def complete(self, system: str, user: str) -> str:
        self.calls.append((system, user))
        return self.answers.pop(0)


@dataclass
class ModelFactory:
    """Stands in for ``suggestion.default_model``: hands out ``model``."""

    model: SuggestionModel

    def __call__(self, llm_model: str, key: str) -> SuggestionModel:
        return self.model


def answer(*cuts: tuple[str, list[int]]) -> str:
    return json.dumps({"cuts": [{"title": title, "sentences": ids} for title, ids in cuts]})


def install(monkeypatch: pytest.MonkeyPatch, *answers: str) -> ScriptedModel:
    model = ScriptedModel(list(answers))
    monkeypatch.setattr(suggestion, "default_model", ModelFactory(model))
    return model


@pytest.fixture
def connection(wordcut_home: Path) -> Iterator[sqlite3.Connection]:
    with closing(connect(Home(wordcut_home))) as opened:
        yield opened


@pytest.fixture
def configured(connection: sqlite3.Connection) -> None:
    update_settings(connection, llm_model=MODEL)
    store_llm_key(SENTINEL_KEY)


def processed_sermon(connection: sqlite3.Connection) -> str:
    """A ``processed`` sermon of ``SENTENCE_COUNT`` 10 s sentences, with the earlier cuts."""
    sermon = sermons.insert(
        connection,
        NewSermon(
            youtube_id="Ab3_x-9QzLk",
            url="https://youtu.be/Ab3_x-9QzLk",
            title="Culto",
            service_date=date(2026, 10, 18),
            live_duration=7718.0,
            live_finished=True,
            created_at=datetime(2026, 10, 26, tzinfo=timezone.utc),
        ),
    )
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
    return str(sermon.id)


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


def run_json(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, Any]:
    exit_code = main(argv)
    return exit_code, json.loads(capsys.readouterr().out)


def shown_cuts(sermon_id: str, capsys: pytest.CaptureFixture[str]) -> list[dict[str, Any]]:
    cut_list: list[dict[str, Any]] = run_json(["sermon", "show", sermon_id, "--json"], capsys)[1][
        "cuts"
    ]
    return cut_list


def test_suggest_with_a_preset_and_wait_replaces_the_unedited_suggestions_with_the_new_cuts(
    connection: sqlite3.Connection,
    configured: None,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    sermon_id = processed_sermon(connection)
    preset_id = other_preset(connection)
    model = install(monkeypatch, answer(("Novo", [3, 4, 5, 6, 7])))
    kept = [cut for cut in shown_cuts(sermon_id, capsys) if cut["title"] != "Sugerido antigo"]
    sentences = transcripts.sentences_of(connection, int(sermon_id))

    exit_code = main(
        ["sermon", "suggest", sermon_id, "--preset", str(preset_id), "--wait", "--json"]
    )

    out, err = capsys.readouterr()
    result = json.loads(out)
    after = shown_cuts(sermon_id, capsys)
    new = [cut for cut in after if cut not in kept]
    assert (
        exit_code,
        model.calls[0][0],
        [cut for cut in after if cut in kept],
        result,
        [(cut["title"], cut["status"], cut["preset_id"]) for cut in new],
        err.splitlines(),
    ) == (
        0,
        build_request(show_preset(connection, preset_id), sentences).system,
        kept,
        {
            "sermon_id": int(sermon_id),
            "preset_id": preset_id,
            "suggested_cuts": new,
            "suggestion_warnings": [],
        },
        [("Novo", "suggested", preset_id)],
        ["[suggest] sugerindo 0%"],
    )


def test_quiet_suggest_with_wait_prints_no_progress(
    connection: sqlite3.Connection,
    configured: None,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    sermon_id = processed_sermon(connection)
    install(monkeypatch, answer(("Novo", [3, 4, 5, 6, 7, 8])))

    exit_code = main(["sermon", "suggest", sermon_id, "--wait", "--json", "--quiet"])

    assert (exit_code, capsys.readouterr().err) == (0, "")


def test_suggest_without_wait_answers_the_running_task(
    connection: sqlite3.Connection,
    configured: None,
    harmless_tasks: list[subprocess.Popen[bytes]],
    capsys: pytest.CaptureFixture[str],
) -> None:
    sermon_id = processed_sermon(connection)

    exit_code, task = run_json(["sermon", "suggest", sermon_id, "--json"], capsys)

    assert (exit_code, task) == (
        0,
        {
            "task_id": task["task_id"],
            "kind": "suggest",
            "status": "running",
            "sermon_id": int(sermon_id),
        },
    )


def test_suggest_runs_while_another_process_holds_the_processing_lock(
    connection: sqlite3.Connection,
    configured: None,
    monkeypatch: pytest.MonkeyPatch,
    lock_owner: Callable[[str, str], subprocess.Popen[str]],
    capsys: pytest.CaptureFixture[str],
) -> None:
    sermon_id = processed_sermon(connection)
    lock_owner("render", "cut 34")
    install(monkeypatch, answer(("Novo", [3, 4, 5, 6, 7, 8])))

    exit_code, result = run_json(["sermon", "suggest", sermon_id, "--wait", "--json"], capsys)

    assert (exit_code, [cut["title"] for cut in result["suggested_cuts"]]) == (0, ["Novo"])


def suggest_tasks(capsys: pytest.CaptureFixture[str]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = run_json(["task", "list", "--kind", "suggest", "--json"], capsys)[
        1
    ]["items"]
    return items


@pytest.mark.parametrize(
    ("argv", "status", "exit_code", "code", "details"),
    [
        (["404"], "processed", 3, "not_found", {"sermon_id": 404}),
        (["{sermon}", "--preset", "404"], "processed", 3, "not_found", {"preset_id": 404}),
        (["{sermon}"], "trimmed", 5, "sermon_not_processed", {"sermon_id": 1, "status": "trimmed"}),
    ],
    ids=["sermon not found", "preset not found", "sermon not processed"],
)
def test_a_refused_suggestion_exits_with_its_code_and_records_no_task(
    connection: sqlite3.Connection,
    configured: None,
    capsys: pytest.CaptureFixture[str],
    argv: list[str],
    status: str,
    exit_code: int,
    code: str,
    details: dict[str, Any],
) -> None:
    sermon_id = processed_sermon(connection)
    with connection:
        sermons.set_status(connection, int(sermon_id), status, PROCESSED_AT)
    command = [argument.format(sermon=sermon_id) for argument in argv]

    exit_status, refused = run_json(["sermon", "suggest", *command, "--wait", "--json"], capsys)

    assert (
        exit_status,
        refused["error"]["code"],
        refused["error"]["details"],
        suggest_tasks(capsys),
    ) == (exit_code, code, details, [])


def test_without_the_llm_configured_suggest_exits_5_and_changes_nothing(
    connection: sqlite3.Connection, capsys: pytest.CaptureFixture[str]
) -> None:
    store_llm_key(SENTINEL_KEY)
    sermon_id = processed_sermon(connection)
    before = run_json(["sermon", "show", sermon_id, "--json"], capsys)[1]

    exit_code, refused = run_json(["sermon", "suggest", sermon_id, "--wait", "--json"], capsys)

    assert (
        exit_code,
        refused["error"]["code"],
        refused["error"]["details"],
        run_json(["sermon", "show", sermon_id, "--json"], capsys)[1],
        suggest_tasks(capsys),
    ) == (5, "llm_not_configured", {"missing": ["llm_model"]}, before, [])


def test_an_llm_failure_exits_6_with_llm_error_and_leaves_the_cuts(
    connection: sqlite3.Connection,
    configured: None,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    sermon_id = processed_sermon(connection)
    before = shown_cuts(sermon_id, capsys)
    install(monkeypatch, "Primeira.", "Segunda.")

    exit_code, failed = run_json(["sermon", "suggest", sermon_id, "--wait", "--json"], capsys)

    [task] = suggest_tasks(capsys)
    assert (
        exit_code,
        failed["error"]["code"],
        shown_cuts(sermon_id, capsys),
        (task["status"], task["error"]["code"]),
    ) == (6, "llm_error", before, ("failed", "llm_error"))


def test_a_second_suggestion_while_one_runs_exits_4_busy_naming_the_running_task(
    connection: sqlite3.Connection,
    configured: None,
    harmless_tasks: list[subprocess.Popen[bytes]],
    capsys: pytest.CaptureFixture[str],
) -> None:
    sermon_id = processed_sermon(connection)
    running = run_json(["sermon", "suggest", sermon_id, "--json"], capsys)[1]

    exit_code, refused = run_json(["sermon", "suggest", sermon_id, "--json"], capsys)

    assert (
        exit_code,
        refused["error"]["code"],
        refused["error"]["details"]["task_id"],
        [task["id"] for task in suggest_tasks(capsys)],
    ) == (4, "busy", running["task_id"], [running["task_id"]])


def test_suggest_help_says_it_is_for_the_administrator_in_portuguese(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["sermon", "suggest", "--help"])

    help_text = capsys.readouterr().out
    assert (
        exit_code,
        "administrador" in help_text,
        "nova sugestão de cortes" in help_text,
        "wordcut sermon suggest 12" in help_text,
    ) == (0, True, True, True)


def test_suggest_without_json_tells_the_new_cuts_and_the_launched_task_readably(
    connection: sqlite3.Connection,
    configured: None,
    harmless_tasks: list[subprocess.Popen[bytes]],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    sermon_id = processed_sermon(connection)
    install(monkeypatch, answer(("Novo", [3, 4, 5, 6, 7, 8])))
    main(["sermon", "suggest", sermon_id, "--wait", "--quiet"])
    finished = capsys.readouterr().out

    main(["sermon", "suggest", sermon_id])

    launched = capsys.readouterr().out
    running = next(task for task in suggest_tasks(capsys) if task["status"] == "running")
    assert (finished.splitlines()[:2], launched) == (
        [f"1 corte sugerido para a pregação {sermon_id} com o preset 1.", "5  Novo"],
        f"Tarefa {running['id']} iniciada: sugestão de cortes da pregação {sermon_id}."
        f" Acompanhe com wordcut task wait {running['id']}.\n",
    )


def echoing_the_key(llm_model: str, key: str) -> SuggestionModel:
    """The real model on a transport that refuses with the key in the body; no network."""

    def refuse(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": f"Chave {SENTINEL_KEY} inválida"}})

    return OpenRouterModel(llm_model, key, httpx.Client(transport=httpx.MockTransport(refuse)))


@pytest.mark.parametrize(
    ("outcome", "exit_codes"),
    [
        ("succeeded", [0, 0]),
        ("llm_error", [6, 6]),
        ("llm_not_configured", [5, 5]),
        ("launched", [0, 4]),
        ("busy", [4, 4]),
    ],
)
def test_no_output_of_suggest_carries_the_llm_key(
    connection: sqlite3.Connection,
    harmless_tasks: list[subprocess.Popen[bytes]],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    outcome: str,
    exit_codes: list[int],
) -> None:
    store_llm_key(SENTINEL_KEY)
    if outcome != "llm_not_configured":
        update_settings(connection, llm_model=MODEL)
    sermon_id = processed_sermon(connection)
    if outcome == "llm_error":
        monkeypatch.setattr(suggestion, "default_model", echoing_the_key)
    else:
        install(monkeypatch, *[answer(("Novo", [3, 4, 5, 6, 7, 8]))] * 2)
    if outcome == "busy":
        main(["sermon", "suggest", sermon_id])
    wait = ["--wait"] if outcome in ("succeeded", "llm_error", "llm_not_configured") else []

    exited = [
        main(["sermon", "suggest", sermon_id, *wait, *json_option])
        for json_option in ([], ["--json"])
    ]

    out, err = capsys.readouterr()
    assert (exited, SENTINEL_KEY in out + err) == (exit_codes, False)
