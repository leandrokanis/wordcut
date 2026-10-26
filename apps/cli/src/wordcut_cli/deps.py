"""The outside world the commands use; tests replace these factories (``monkeypatch``)."""

from __future__ import annotations

import sqlite3

from wordcut.db import connect
from wordcut.home import Home
from wordcut.youtube import LiveSource, YouTube


def live_source() -> LiveSource:
    return YouTube()


def connection() -> sqlite3.Connection:
    """The database of the data folder (``WORDCUT_HOME``), created and migrated if needed."""
    return connect(Home.from_environment())
