"""Where the secrets of a Wordcut installation live (docs/cli.md §14).

The code never reads these files: it only hands their paths to the tools that use them.
"""

from __future__ import annotations

import os
from pathlib import Path

YOUTUBE_COOKIES_FILE = "youtube-cookies.txt"


def config_dir() -> Path:
    """``WORDCUT_CONFIG`` when set (``/config`` in the containers), else ``~/.config/wordcut``."""
    override = os.environ.get("WORDCUT_CONFIG")
    return Path(override) if override else Path.home() / ".config/wordcut"


def youtube_cookies() -> Path:
    return config_dir() / YOUTUBE_COOKIES_FILE
