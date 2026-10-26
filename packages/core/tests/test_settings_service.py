import sqlite3
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path

import pytest

from wordcut.db import connect
from wordcut.errors import WordcutError
from wordcut.home import Home
from wordcut.service.settings import (
    show_settings,
    store_llm_key,
    store_youtube_cookies,
    update_settings,
    whisper_model,
)

FAKE_KEY = "sk-ficticia-0000abcd"
FAKE_COOKIES = "# Netscape HTTP Cookie File\r\n.example.com\tTRUE\t/\tTRUE\t0\tSID\tficticio\r\n"


@pytest.fixture
def connection(wordcut_home: Path) -> Iterator[sqlite3.Connection]:
    with closing(connect(Home(wordcut_home))) as opened:
        yield opened


def test_a_new_installation_has_only_the_whisperx_model_set(
    connection: sqlite3.Connection,
) -> None:
    assert show_settings(connection) == {
        "llm_model": None,
        "whisper_model": "large-v3",
        "llm_key": None,
        "youtube_cookies": False,
        "default_preset_id": None,
    }


def test_a_changed_model_is_kept_after_reopening_and_the_other_stays(wordcut_home: Path) -> None:
    home = Home(wordcut_home)
    with closing(connect(home)) as connection:
        update_settings(connection, whisper_model="medium")

    with closing(connect(home)) as connection:
        shown = show_settings(connection)
    assert (shown["llm_model"], shown["whisper_model"]) == (None, "medium")


@pytest.mark.parametrize(
    ("models", "argument"),
    [
        ({}, "llm_model, whisper_model"),
        ({"llm_model": "", "whisper_model": "medium"}, "llm_model"),
        ({"whisper_model": "   "}, "whisper_model"),
    ],
    ids=["no model", "empty LLM model", "blank WhisperX model"],
)
def test_setting_no_model_or_an_empty_one_is_refused_and_changes_nothing(
    connection: sqlite3.Connection, models: dict[str, str], argument: str
) -> None:
    before = show_settings(connection)

    with pytest.raises(WordcutError) as raised:
        update_settings(connection, **models)

    error = raised.value
    assert (error.code, error.details, show_settings(connection)) == (
        "invalid_argument",
        {"argument": argument},
        before,
    )


def test_a_stored_key_is_shown_masked_without_the_blanks_around_it(
    connection: sqlite3.Connection,
) -> None:
    store_llm_key(f"  {FAKE_KEY}\n")

    assert show_settings(connection)["llm_key"] == "••••abcd"


@pytest.mark.parametrize("text", ["", "  \n"], ids=["empty", "blank"])
def test_an_empty_key_is_refused_and_nothing_is_stored(
    connection: sqlite3.Connection, text: str
) -> None:
    with pytest.raises(WordcutError) as raised:
        store_llm_key(text)

    assert (raised.value.code, show_settings(connection)["llm_key"]) == ("invalid_argument", None)


def test_the_key_stays_out_of_the_shown_settings_and_of_the_database(
    wordcut_home: Path, connection: sqlite3.Connection
) -> None:
    store_llm_key(FAKE_KEY)
    update_settings(connection, llm_model="openai/gpt-ficticio")

    shown = show_settings(connection)
    stored = b"".join(path.read_bytes() for path in wordcut_home.glob("wordcut.db*"))
    assert (FAKE_KEY in repr(shown), FAKE_KEY.encode() in stored) == (False, False)


def test_stored_cookies_are_kept_as_they_came_and_shown_only_as_present(
    connection: sqlite3.Connection, wordcut_config: Path
) -> None:
    store_youtube_cookies(FAKE_COOKIES)

    stored = (wordcut_config / "youtube-cookies.txt").read_bytes()
    assert (stored, show_settings(connection)["youtube_cookies"]) == (FAKE_COOKIES.encode(), True)


@pytest.mark.parametrize(
    "text",
    [
        "",
        " \n",
        "# Netscape HTTP Cookie File\n# .example.com\tTRUE\t/\tTRUE\t0\tSID\tficticio\n",
        "SID=ficticio; HSID=ficticio\n",
        ".example.com\tTRUE\t/\tTRUE\t0\tSID\n",
    ],
    ids=["empty", "blank", "only comments", "header style", "six fields"],
)
def test_cookies_without_a_netscape_line_are_refused_and_nothing_is_stored(
    connection: sqlite3.Connection, text: str
) -> None:
    with pytest.raises(WordcutError) as raised:
        store_youtube_cookies(text)

    assert (raised.value.code, show_settings(connection)["youtube_cookies"]) == (
        "invalid_argument",
        False,
    )


def test_the_whisperx_model_to_use_is_large_v3_until_another_is_set(
    connection: sqlite3.Connection,
) -> None:
    before = whisper_model(connection)
    update_settings(connection, whisper_model="medium")

    assert (before, whisper_model(connection)) == ("large-v3", "medium")
