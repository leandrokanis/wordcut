"""SQL access to the ``words`` and ``sentences`` of a sermon (migration 0004).

Writes run in the caller's transaction (``with connection:``), so that the words, the
sentences and the sermon's state change together.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass

from wordcut.processing.sentences import Sentence
from wordcut.transcript import Word


@dataclass(frozen=True)
class WordRow:
    id: int
    position: int
    text: str
    start: float
    end: float
    score: float | None
    estimated: bool


@dataclass(frozen=True)
class SentenceRow:
    id: int
    position: int
    first_word_id: int
    last_word_id: int
    start: float
    end: float
    text: str


def replace(
    connection: sqlite3.Connection,
    sermon_id: int,
    words: Sequence[Word],
    sentences: Sequence[Sentence],
) -> None:
    """Make ``words`` and ``sentences`` the transcript of the sermon, with new IDs."""
    delete_of(connection, sermon_id)
    word_ids = [
        _insert_word(connection, sermon_id, position, word) for position, word in enumerate(words)
    ]
    for position, sentence in enumerate(sentences):
        connection.execute(
            "INSERT INTO sentences (sermon_id, position, first_word_id, last_word_id, start,"
            ' "end", text) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (
                sermon_id,
                position,
                word_ids[sentence.first_word],
                word_ids[sentence.last_word],
                sentence.start,
                sentence.end,
                sentence.text,
            ),
        )


def delete_of(connection: sqlite3.Connection, sermon_id: int) -> None:
    """Remove the words and sentences of the sermon."""
    connection.execute("DELETE FROM sentences WHERE sermon_id = ?", (sermon_id,))
    connection.execute("DELETE FROM words WHERE sermon_id = ?", (sermon_id,))


def _insert_word(connection: sqlite3.Connection, sermon_id: int, position: int, word: Word) -> int:
    cursor = connection.execute(
        'INSERT INTO words (sermon_id, position, text, start, "end", score, estimated)'
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (sermon_id, position, word.text, word.start, word.end, word.score, word.estimated),
    )
    assert cursor.lastrowid is not None
    return cursor.lastrowid


def words_of(connection: sqlite3.Connection, sermon_id: int) -> list[WordRow]:
    """The words of the sermon in the order they were spoken."""
    found = connection.execute(
        'SELECT id, position, text, start, "end", score, estimated FROM words'
        " WHERE sermon_id = ? ORDER BY position",
        (sermon_id,),
    ).fetchall()
    return [
        WordRow(word_id, position, text, start, end, score, bool(estimated))
        for word_id, position, text, start, end, score, estimated in found
    ]


def sentences_of(connection: sqlite3.Connection, sermon_id: int) -> list[SentenceRow]:
    """The sentences of the sermon in order."""
    found = connection.execute(
        'SELECT id, position, first_word_id, last_word_id, start, "end", text FROM sentences'
        " WHERE sermon_id = ? ORDER BY position",
        (sermon_id,),
    ).fetchall()
    return [SentenceRow(*values) for values in found]
