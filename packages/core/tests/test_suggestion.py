import json
import sqlite3
from collections.abc import Iterator
from contextlib import closing
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from wordcut import suggestion
from wordcut.db import connect, cuts, sermons, transcripts
from wordcut.db.cuts import NewCut, Segment
from wordcut.db.presets import SecondsRange
from wordcut.db.sermons import NewSermon, SuggestionError
from wordcut.db.transcripts import SentenceRow
from wordcut.errors import WordcutError
from wordcut.home import Home
from wordcut.processing.sentences import Sentence
from wordcut.service.cuts import create_cut, discard_cut, restore_cut
from wordcut.service.presets import create_preset, default_preset, update_preset
from wordcut.service.sermons import show_sermon
from wordcut.service.settings import store_llm_key, update_settings
from wordcut.suggestion import SuggestionModel, suggest
from wordcut.suggestion.response import InvalidResponse, parse_response
from wordcut.transcript import Word

# Fictitious: no test ever reaches OpenRouter.
SENTINEL_KEY = "sk-or-v1-sentinela-ficticia-7f3a"
MODEL = "provedor/modelo-de-teste"
SENTENCE_SECONDS = 10.0
SENTENCE_COUNT = 12
PROCESSED_AT = datetime(2026, 10, 26, 21, 0, tzinfo=timezone.utc)
# The cuts a replacing suggestion finds: only the unedited suggestion may go.
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
    """Stands in for ``suggestion.default_model``: hands out ``model`` and keeps its arguments."""

    model: SuggestionModel
    built_with: list[tuple[str, str]] = field(default_factory=list)

    def __call__(self, llm_model: str, key: str) -> SuggestionModel:
        self.built_with.append((llm_model, key))
        return self.model


def answer(*cuts: tuple[str, list[int]]) -> str:
    return json.dumps({"cuts": [{"title": title, "sentences": ids} for title, ids in cuts]})


@pytest.fixture
def connection(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with closing(connect(Home(tmp_path))) as opened:
        yield opened


@pytest.fixture
def configured(connection: sqlite3.Connection) -> None:
    update_settings(connection, llm_model=MODEL)
    store_llm_key(SENTINEL_KEY)


def install(monkeypatch: pytest.MonkeyPatch, *answers: str | WordcutError) -> ScriptedModel:
    model = ScriptedModel(list(answers))
    monkeypatch.setattr(suggestion, "default_model", ModelFactory(model))
    return model


def timed_words(count: int) -> tuple[list[Word], list[Sentence]]:
    """``count`` sentences of two words each, ``SENTENCE_SECONDS`` long, back to back."""
    words: list[Word] = []
    sentences: list[Sentence] = []
    for index in range(count):
        start = index * SENTENCE_SECONDS
        end = start + SENTENCE_SECONDS
        words += [Word("Frase", start, start + 1.0), Word(f"{index + 1}.", start + 1.0, end)]
        sentences.append(Sentence(2 * index, 2 * index + 1, start, end, f"Frase {index + 1}."))
    return words, sentences


def processed_sermon(connection: sqlite3.Connection, count: int = SENTENCE_COUNT) -> int:
    """A sermon whose sentence IDs are not their positions: its transcript was recorded twice."""
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
    words, sentences = timed_words(count)
    for _ in range(2):
        with connection:
            transcripts.replace(connection, sermon.id, words, sentences)
    return sermon.id


def sentence(connection: sqlite3.Connection, sermon_id: int, number: int) -> SentenceRow:
    return transcripts.sentences_of(connection, sermon_id)[number - 1]


def home_of(connection: sqlite3.Connection) -> Home:
    """The data folder of the database ``connection`` is open on."""
    [(_, _, database)] = connection.execute("PRAGMA database_list").fetchall()
    return Home(Path(database).parent)


def shown_cuts(connection: sqlite3.Connection, sermon_id: int) -> list[dict[str, Any]]:
    cuts: list[dict[str, Any]] = show_sermon(connection, sermon_id, home=home_of(connection))[
        "cuts"
    ]
    return cuts


def preset_allowing(connection: sqlite3.Connection, allowed: SecondsRange) -> dict[str, Any]:
    """A new preset that allows cuts of ``allowed`` seconds, estimated after the cleanup."""
    created = create_preset(connection, f"Permite {allowed.min}-{allowed.max} s")
    return update_preset(
        connection, created["id"], duration_allowed=allowed, duration_ideal=allowed
    )


def test_a_valid_answer_is_saved_as_suggested_cuts_with_one_segment_per_run_of_sentences(
    connection: sqlite3.Connection, configured: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    sermon_id = processed_sermon(connection)
    model = install(monkeypatch, answer(("Graça que alcança", [3, 4, 5, 9, 10])))
    preset = default_preset(connection)
    first, third, fifth, ninth, tenth = (
        sentence(connection, sermon_id, number) for number in (1, 3, 5, 9, 10)
    )
    assert first.id != 1

    suggest(connection, sermon_id, preset)

    [cut] = shown_cuts(connection, sermon_id)
    del cut["id"]
    assert (len(model.calls), cut) == (
        1,
        {
            "status": "suggested",
            "title": "Graça que alcança",
            "segments": [
                {"from_word": third.first_word_id, "to_word": fifth.last_word_id},
                {"from_word": ninth.first_word_id, "to_word": tenth.last_word_id},
            ],
            "range_start_word": third.first_word_id,
            "range_end_word": tenth.last_word_id,
            "source": "llm",
            "preset_id": preset["id"],
            "edited": False,
        },
    )


def test_the_real_model_is_refused_inside_the_test_suite() -> None:
    with pytest.raises(AssertionError, match="default_model"):
        suggestion.default_model(MODEL, SENTINEL_KEY)


def test_a_reordered_cut_keeps_its_play_order_and_spans_its_range_in_sermon_order(
    connection: sqlite3.Connection, configured: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    sermon_id = processed_sermon(connection)
    install(monkeypatch, answer(("Gancho no fim", [9, 10, 3])))
    third, ninth, tenth = (sentence(connection, sermon_id, number) for number in (3, 9, 10))

    suggest(connection, sermon_id, preset_allowing(connection, SecondsRange(10, 600)))

    [cut] = shown_cuts(connection, sermon_id)
    assert (cut["segments"], cut["range_start_word"], cut["range_end_word"]) == (
        [
            {"from_word": ninth.first_word_id, "to_word": tenth.last_word_id},
            {"from_word": third.first_word_id, "to_word": third.last_word_id},
        ],
        third.first_word_id,
        tenth.last_word_id,
    )


def test_the_model_is_built_with_the_configured_model_and_key(
    connection: sqlite3.Connection, configured: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    factory = ModelFactory(ScriptedModel([answer()]))
    monkeypatch.setattr(suggestion, "default_model", factory)

    suggest(connection, processed_sermon(connection), default_preset(connection))

    assert factory.built_with == [(MODEL, SENTINEL_KEY)]


def test_an_answer_outside_the_schema_is_asked_again_once_with_the_reason(
    connection: sqlite3.Connection, configured: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    sermon_id = processed_sermon(connection)
    refused = answer(("Inexistente", [3, SENTENCE_COUNT + 1]))
    model = install(monkeypatch, refused, answer(("Segunda", [3, 4, 5, 6, 7, 8])))
    with pytest.raises(InvalidResponse) as reason:
        parse_response(refused, SENTENCE_COUNT, reorder=False)

    suggest(connection, sermon_id, default_preset(connection))

    [(first_system, first_user), (second_system, second_user)] = model.calls
    assert (
        second_system == first_system,
        second_user.startswith(first_user + "\n\n"),
        str(reason.value) in second_user.removeprefix(first_user),
        [cut["title"] for cut in shown_cuts(connection, sermon_id)],
    ) == (True, True, True, ["Segunda"])


def test_a_cited_sentence_that_does_not_exist_costs_an_attempt(
    connection: sqlite3.Connection, configured: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    sermon_id = processed_sermon(connection)
    model = install(
        monkeypatch,
        answer(("Inexistente", [3, SENTENCE_COUNT + 1])),
        answer(("Segunda", [3, 4, 5, 6, 7, 8])),
    )

    suggest(connection, sermon_id, default_preset(connection))

    assert (len(model.calls), [cut["title"] for cut in shown_cuts(connection, sermon_id)]) == (
        2,
        ["Segunda"],
    )


def test_two_answers_outside_the_schema_are_an_llm_error_kept_on_the_sermon_without_cuts(
    connection: sqlite3.Connection, configured: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    sermon_id = processed_sermon(connection)
    model = install(monkeypatch, "Primeira.", "Segunda.", answer(("Terceira", [3])))

    with pytest.raises(WordcutError) as raised:
        suggest(connection, sermon_id, default_preset(connection))

    shown = show_sermon(connection, sermon_id, home=home_of(connection))
    assert (
        raised.value.code,
        len(model.calls),
        shown["cuts"],
        shown["suggestion_error"],
    ) == (
        "llm_error",
        2,
        [],
        {"code": "llm_error", "message": raised.value.message},
    )


def test_an_llm_error_from_the_model_is_not_asked_again(
    connection: sqlite3.Connection, configured: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    sermon_id = processed_sermon(connection)
    refused = WordcutError("llm_error", "O OpenRouter recusou o pedido (HTTP 500).")
    model = install(monkeypatch, refused, answer(("Segunda", [3, 4, 5, 6, 7, 8])))

    with pytest.raises(WordcutError) as raised:
        suggest(connection, sermon_id, default_preset(connection))

    shown = show_sermon(connection, sermon_id, home=home_of(connection))
    assert (raised.value, len(model.calls), shown["cuts"], shown["suggestion_error"]) == (
        refused,
        1,
        [],
        {"code": "llm_error", "message": refused.message},
    )


@pytest.mark.parametrize(
    ("model_name", "key", "missing"),
    [
        (None, SENTINEL_KEY, ["llm_model"]),
        (MODEL, None, ["llm_key"]),
        (None, None, ["llm_model", "llm_key"]),
    ],
    ids=["no model", "no key", "neither"],
)
def test_without_the_model_or_the_key_the_llm_is_not_called_and_the_error_says_what_is_missing(
    connection: sqlite3.Connection,
    monkeypatch: pytest.MonkeyPatch,
    model_name: str | None,
    key: str | None,
    missing: list[str],
) -> None:
    if model_name is not None:
        update_settings(connection, llm_model=model_name)
    if key is not None:
        store_llm_key(key)
    sermon_id = processed_sermon(connection)
    factory = ModelFactory(ScriptedModel([answer(("Corte", [3, 4, 5, 6]))]))
    monkeypatch.setattr(suggestion, "default_model", factory)

    with pytest.raises(WordcutError) as raised:
        suggest(connection, sermon_id, default_preset(connection))

    shown = show_sermon(connection, sermon_id, home=home_of(connection))
    assert (
        raised.value.code,
        raised.value.exit_code,
        raised.value.details,
        factory.built_with,
        SENTINEL_KEY in json.dumps(raised.value.to_dict()),
        shown["cuts"],
        shown["suggestion_error"],
    ) == (
        "llm_not_configured",
        5,
        {"missing": missing},
        [],
        False,
        [],
        {"code": "llm_not_configured", "message": raised.value.message},
    )


def test_cuts_whose_estimated_duration_falls_outside_the_allowed_one_are_dropped_with_a_warning(
    connection: sqlite3.Connection, configured: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Sentences of 10 s; estimated = raw seconds x 0.82; allowed 41-82 s, both inclusive.
    sermon_id = processed_sermon(connection)
    preset = preset_allowing(connection, SecondsRange(41, 82))
    install(
        monkeypatch,
        answer(
            ("Raw 100 s, estimated 82 s", list(range(1, 11))),
            ("Raw 110 s, estimated 90.2 s", list(range(1, 12))),
            ("Raw 50 s, estimated 41 s", [1, 2, 3, 4, 5]),
            ("Raw 40 s, estimated 32.8 s", [1, 2, 3, 4]),
            ("Two segments, 50 s apart from the gap", [1, 2, 3, 4, 12]),
        ),
    )

    result = suggest(connection, sermon_id, preset)

    assert (
        [cut["title"] for cut in shown_cuts(connection, sermon_id)],
        [(warning["title"], warning["estimated_duration"]) for warning in result.warnings],
    ) == (
        [
            "Raw 100 s, estimated 82 s",
            "Raw 50 s, estimated 41 s",
            "Two segments, 50 s apart from the gap",
        ],
        [("Raw 110 s, estimated 90.2 s", 90.2), ("Raw 40 s, estimated 32.8 s", 32.8)],
    )


@pytest.mark.parametrize(
    "answered",
    [answer(), answer(("Curto demais", [1]))],
    ids=["no cuts", "every cut dropped"],
)
def test_a_valid_answer_without_cuts_to_keep_saves_nothing_and_is_no_error(
    connection: sqlite3.Connection,
    configured: None,
    monkeypatch: pytest.MonkeyPatch,
    answered: str,
) -> None:
    sermon_id = processed_sermon(connection)
    install(monkeypatch, answered)

    result = suggest(connection, sermon_id, default_preset(connection))

    shown = show_sermon(connection, sermon_id, home=home_of(connection))
    assert (result.saved, shown["cuts"], shown["suggestion_error"]) == (0, [], None)


def test_a_successful_suggestion_clears_the_previous_ones_error(
    connection: sqlite3.Connection, configured: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    sermon_id = processed_sermon(connection)
    install(monkeypatch, "Primeira.", "Segunda.", answer(("Terceira", [3, 4, 5, 6, 7, 8])))
    with pytest.raises(WordcutError):
        suggest(connection, sermon_id, default_preset(connection))

    suggest(connection, sermon_id, default_preset(connection))

    shown = show_sermon(connection, sermon_id, home=home_of(connection))
    assert ([cut["title"] for cut in shown["cuts"]], shown["suggestion_error"]) == (
        ["Terceira"],
        None,
    )


def recorded_processed(connection: sqlite3.Connection) -> int:
    """A ``processed`` sermon, as a replacing suggestion requires, with the earlier cuts."""
    sermon_id = processed_sermon(connection)
    first, last = sentence(connection, sermon_id, 1), sentence(connection, sermon_id, 2)
    earlier = [
        NewCut(
            status=status,
            title=title,
            segments=(Segment(first.first_word_id, last.last_word_id),),
            range_start_word=first.first_word_id,
            range_end_word=last.last_word_id,
            source="llm",
            preset_id=None,
        )
        for title, status in EARLIER_CUTS
    ]
    with connection:
        sermons.record_processed(connection, sermon_id, 970.0, 1090.0, "sermon.mp4", PROCESSED_AT)
        cuts.insert_many(connection, sermon_id, earlier, PROCESSED_AT)
        connection.execute("UPDATE cuts SET edited = 1 WHERE title = 'Sugerido editado'")
        sermons.record_suggestion_error(
            connection, sermon_id, SuggestionError("llm_error", "A anterior falhou.")
        )
    return sermon_id


def kept_cuts(connection: sqlite3.Connection, sermon_id: int) -> list[dict[str, Any]]:
    """The cuts a replacing suggestion keeps: every one but the unedited suggestion."""
    return [cut for cut in shown_cuts(connection, sermon_id) if cut["title"] != "Sugerido antigo"]


def test_a_replacing_suggestion_swaps_the_unedited_suggestions_for_the_new_cuts(
    connection: sqlite3.Connection, configured: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    sermon_id = recorded_processed(connection)
    kept = kept_cuts(connection, sermon_id)
    preset = preset_allowing(connection, SecondsRange(10, 600))
    install(monkeypatch, answer(("Novo", [3, 4, 5])))

    result = suggest(connection, sermon_id, preset, replace_suggested=True)

    shown = show_sermon(connection, sermon_id, home=home_of(connection))
    [new] = [cut for cut in shown["cuts"] if cut not in kept]
    assert (
        [cut for cut in shown["cuts"] if cut in kept] == kept,
        (new["id"], new["title"], new["status"], new["source"], new["preset_id"]),
        shown["suggestion_error"],
    ) == (True, (result.cut_ids[0], "Novo", "suggested", "llm", preset["id"]), None)


@pytest.mark.parametrize(
    ("answers", "configure", "code"),
    [
        (["Primeira.", "Segunda."], True, "llm_error"),
        ([WordcutError("llm_error", "O OpenRouter recusou o pedido.")], True, "llm_error"),
        ([], False, "llm_not_configured"),
    ],
    ids=["two answers outside the schema", "transport error", "not configured"],
)
def test_a_failed_replacing_suggestion_leaves_every_cut_as_it_was(
    connection: sqlite3.Connection,
    monkeypatch: pytest.MonkeyPatch,
    answers: list[str | WordcutError],
    configure: bool,
    code: str,
) -> None:
    if configure:
        update_settings(connection, llm_model=MODEL)
        store_llm_key(SENTINEL_KEY)
    sermon_id = recorded_processed(connection)
    before = shown_cuts(connection, sermon_id)
    install(monkeypatch, *answers)

    with pytest.raises(WordcutError) as raised:
        suggest(connection, sermon_id, default_preset(connection), replace_suggested=True)

    shown = show_sermon(connection, sermon_id, home=home_of(connection))
    assert (raised.value.code, shown["cuts"], shown["suggestion_error"]["code"]) == (
        code,
        before,
        code,
    )


def test_a_replacing_suggestion_keeps_the_suggestions_of_another_sermon(
    connection: sqlite3.Connection, configured: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    sermon_id = recorded_processed(connection)
    other = sermons.insert(
        connection,
        NewSermon(
            youtube_id="Zz9_y-8PqRs",
            url="https://youtu.be/Zz9_y-8PqRs",
            title="Outro culto",
            service_date=date(2026, 10, 25),
            live_duration=7200.0,
            live_finished=True,
            created_at=datetime(2026, 10, 26, tzinfo=timezone.utc),
        ),
    )
    with connection:
        cuts.insert_many(
            connection,
            other.id,
            [NewCut("suggested", "De outra pregação", (Segment(1, 2),), 1, 2, "llm", None)],
            PROCESSED_AT,
        )
    elsewhere = shown_cuts(connection, other.id)
    install(monkeypatch, answer(("Novo", [3, 4, 5, 6, 7, 8])))

    suggest(connection, sermon_id, default_preset(connection), replace_suggested=True)

    assert shown_cuts(connection, other.id) == elsewhere


def test_a_replacing_suggestion_keeps_a_cut_the_admin_created_even_discarded_and_restored(
    connection: sqlite3.Connection, configured: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    sermon_id = recorded_processed(connection)
    created = create_cut(connection, sermon_id, 30.0, 70.0)["id"]
    discard_cut(connection, created)
    restore_cut(connection, created)
    [before] = [cut for cut in shown_cuts(connection, sermon_id) if cut["id"] == created]
    install(monkeypatch, answer(("Novo", [3, 4, 5, 6, 7, 8])))

    suggest(connection, sermon_id, default_preset(connection), replace_suggested=True)

    assert [cut for cut in shown_cuts(connection, sermon_id) if cut["id"] == created] == [before]


def test_a_valid_answer_without_cuts_to_keep_still_replaces_the_unedited_suggestions(
    connection: sqlite3.Connection, configured: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    sermon_id = recorded_processed(connection)
    kept = kept_cuts(connection, sermon_id)
    install(monkeypatch, answer(("Curto demais", [1])))

    result = suggest(connection, sermon_id, default_preset(connection), replace_suggested=True)

    shown = show_sermon(connection, sermon_id, home=home_of(connection))
    assert (
        result.cut_ids,
        [warning["title"] for warning in result.warnings],
        shown["cuts"],
        shown["suggestion_error"],
    ) == ((), ["Curto demais"], kept, None)


@dataclass
class ReprocessingModel:
    """Answers ``answered`` once another connection has changed the sermon with ``change``."""

    home: Home
    sermon_id: int
    change: str
    answered: str

    def complete(self, system: str, user: str) -> str:
        with closing(connect(self.home)) as other, other:
            if self.change == "reprocessed":
                later = PROCESSED_AT.replace(hour=22)
                sermons.record_processed(other, self.sermon_id, 970.0, 1090.0, "sermon.mp4", later)
            else:
                sermons.set_status(other, self.sermon_id, "processing", PROCESSED_AT)
        return self.answered


@pytest.mark.parametrize("change", ["reprocessed", "processing"])
def test_a_replacing_suggestion_saves_nothing_when_the_sermon_was_reprocessed_meanwhile(
    connection: sqlite3.Connection,
    configured: None,
    monkeypatch: pytest.MonkeyPatch,
    change: str,
) -> None:
    sermon_id = recorded_processed(connection)
    before = show_sermon(connection, sermon_id, home=home_of(connection))
    model = ReprocessingModel(home_of(connection), sermon_id, change, answer(("Novo", [3, 4, 5])))
    monkeypatch.setattr(suggestion, "default_model", ModelFactory(model))

    with pytest.raises(WordcutError) as raised:
        suggest(connection, sermon_id, default_preset(connection), replace_suggested=True)

    shown = show_sermon(connection, sermon_id, home=home_of(connection))
    assert (raised.value.code, shown["cuts"], shown["suggestion_error"]) == (
        "sermon_not_processed",
        before["cuts"],
        before["suggestion_error"],
    )
