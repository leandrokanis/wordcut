"""Settings of the installation: the models and the secrets (docs/cli.md §11.1, §16).

The models live in the database; the LLM key and the YouTube cookies are files of the
configuration folder (``wordcut.config``) and never come back in clear: the key only masked,
the cookies only as present or absent.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from wordcut import config
from wordcut.db import settings
from wordcut.errors import WordcutError

DEFAULT_WHISPER_MODEL = "large-v3"
NETSCAPE_COOKIE_FIELDS = 7


def show_settings(connection: sqlite3.Connection) -> dict[str, Any]:
    return {
        "llm_model": llm_model(connection),
        "whisper_model": whisper_model(connection),
        "llm_key": config.masked_llm_key(),
        "youtube_cookies": config.has_youtube_cookies(),
        # Presets arrive with item 2.1.a.2; until then no preset is the default.
        "default_preset_id": None,
    }


def llm_model(connection: sqlite3.Connection) -> str | None:
    """The model of the LLM, which has no default: the administrator chooses it."""
    return settings.value_of(connection, "llm_model")


def whisper_model(connection: sqlite3.Connection) -> str:
    """The WhisperX model of the transcription."""
    return settings.value_of(connection, "whisper_model") or DEFAULT_WHISPER_MODEL


def update_settings(
    connection: sqlite3.Connection,
    *,
    llm_model: str | None = None,
    whisper_model: str | None = None,
) -> dict[str, Any]:
    """Store the models given, leave the others as they are, and show the settings.

    At least one model must be given, and none of them blank.
    """
    given = {
        key: value
        for key, value in (("llm_model", llm_model), ("whisper_model", whisper_model))
        if value is not None
    }
    if not given:
        raise WordcutError(
            "invalid_argument",
            "Informe o modelo do LLM, o do WhisperX ou os dois.",
            {"argument": "llm_model, whisper_model"},
        )
    for key, value in given.items():
        if not value.strip():
            raise WordcutError(
                "invalid_argument", "O nome do modelo não pode ficar vazio.", {"argument": key}
            )
    with connection:
        for key, value in given.items():
            settings.store(connection, key, value)
    return show_settings(connection)


def store_llm_key(text: str) -> None:
    """Store the LLM key, without the blanks around it, as a secret file."""
    key = text.strip()
    if not key:
        raise WordcutError("invalid_argument", "A chave do LLM está vazia.", {"argument": "key"})
    config.write_secret(config.llm_key_file(), key)


def store_youtube_cookies(text: str) -> None:
    """Store the YouTube cookies, as they came, as a secret file.

    They must hold at least one cookie in the Netscape format that yt-dlp reads.
    """
    if not any(_is_netscape_cookie(line) for line in text.splitlines()):
        raise WordcutError(
            "invalid_argument",
            "Os cookies precisam estar no formato Netscape (cookies.txt), com ao menos um cookie.",
            {"argument": "cookies"},
        )
    config.write_secret(config.youtube_cookies(), text)


def _is_netscape_cookie(line: str) -> bool:
    # Netscape cookie file, as curl and yt-dlp read it (https://curl.se/docs/http-cookies.html):
    # one cookie per line in seven TAB-separated fields; a line starting with "#" is a comment.
    return not line.startswith("#") and len(line.split("\t")) == NETSCAPE_COOKIE_FIELDS
