import sqlite3
from collections.abc import Iterator
from contextlib import closing
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from wordcut.db import connect, sermons, transcripts
from wordcut.db.sermons import NewSermon
from wordcut.db.transcripts import SentenceRow
from wordcut.home import Home
from wordcut.processing.sentences import Sentence
from wordcut.service.presets import build_prompt, default_preset
from wordcut.suggestion.request import build_request
from wordcut.transcript import Word

WORDS = (
    Word("Irmãos,", 0.3, 0.7),
    Word("graça.", 0.8, 1.3),
    Word("Cristo", 61.2, 61.6),
    Word("vive.", 61.7, 62.4),
)
SENTENCES = (
    Sentence(first_word=0, last_word=1, start=0.3, end=1.3, text="Irmãos, graça."),
    Sentence(first_word=2, last_word=3, start=61.2, end=62.4, text="Cristo vive."),
)


@pytest.fixture
def connection(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with closing(connect(Home(tmp_path))) as opened:
        yield opened


def sentences_of_a_sermon(connection: sqlite3.Connection) -> list[SentenceRow]:
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
    with connection:
        transcripts.replace(connection, sermon.id, WORDS, SENTENCES)
    return transcripts.sentences_of(connection, sermon.id)


def test_the_user_message_numbers_every_sentence_from_1_in_order_without_times(
    connection: sqlite3.Connection,
) -> None:
    request = build_request(default_preset(connection), sentences_of_a_sermon(connection))

    assert request.user == "1: Irmãos, graça.\n2: Cristo vive."


def test_the_system_message_is_the_preset_prompt_then_the_answer_schema_by_whole_sentences(
    connection: sqlite3.Connection,
) -> None:
    preset = default_preset(connection)

    system = build_request(preset, sentences_of_a_sermon(connection)).system

    prompt, separator, answer_format = system.partition(build_prompt(preset) + "\n\n")
    assert (
        prompt,
        bool(separator),
        '{"cuts": [{"title":' in answer_format,
        '"sentences": [' in answer_format,
        "frases inteiras" in answer_format,
    ) == ("", True, True, True, True)
