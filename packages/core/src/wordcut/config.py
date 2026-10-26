"""Where the secrets of a Wordcut installation live and how they are written (docs/cli.md §14).

Secrets are files of ``config_dir()`` with mode 600, replaced whole by ``write_secret``. The
code hands the cookies to yt-dlp by path and reads the LLM key only to show it masked and to
call the LLM; neither ever reaches an output, a log or an error (docs/cli.md §16).
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from wordcut.errors import WordcutError
from wordcut.home import PRIVATE_FOLDER_MODE

YOUTUBE_COOKIES_FILE = "youtube-cookies.txt"
LLM_KEY_FILE = "openrouter-key"

SECRET_FILE_MODE = 0o600

MASK = "••••"
VISIBLE_KEY_CHARACTERS = 4
# A shorter key would show more than half of itself through the mask.
MIN_KEY_LENGTH_TO_SHOW = 8


def config_dir() -> Path:
    """``WORDCUT_CONFIG`` when set (``/config`` in the containers), else ``~/.config/wordcut``."""
    override = os.environ.get("WORDCUT_CONFIG")
    return Path(override) if override else Path.home() / ".config/wordcut"


def youtube_cookies() -> Path:
    return config_dir() / YOUTUBE_COOKIES_FILE


def has_youtube_cookies() -> bool:
    return youtube_cookies().is_file()


def llm_key_file() -> Path:
    return config_dir() / LLM_KEY_FILE


def masked_llm_key() -> str | None:
    """The stored LLM key as ``"••••"`` and its last characters; ``None`` without a key."""
    try:
        key = llm_key_file().read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    if len(key) < MIN_KEY_LENGTH_TO_SHOW:
        return MASK
    return MASK + key[-VISIBLE_KEY_CHARACTERS:]


def write_secret(path: Path, content: str) -> None:
    """Replace ``path`` with ``content``, readable only by its owner, all at once.

    Raises ``WordcutError("config_not_writable")`` when the folder takes no writes (the
    containers mount it read-only); the error never carries ``content``.
    """
    try:
        _replace_privately(path, content)
    except OSError:
        raise WordcutError(
            "config_not_writable",
            f"Não foi possível gravar em {path.parent}; a pasta de configuração precisa aceitar"
            " escrita.",
            {"path": str(path.parent)},
        ) from None


def _replace_privately(path: Path, content: str) -> None:
    path.parent.mkdir(mode=PRIVATE_FOLDER_MODE, parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as file:
            os.fchmod(file.fileno(), SECRET_FILE_MODE)
            file.write(content)
        os.replace(temporary, path)
    except BaseException:
        os.unlink(temporary)
        raise
