"""The outside world the routes use, called when a request arrives.

Tests replace these factories (``monkeypatch``); a route calls ``deps.live_source()`` in its
body, never through ``Depends``, which would keep the function it was given at definition.
"""

from __future__ import annotations

from wordcut.home import Home
from wordcut.youtube import LiveSource, YouTube


def home() -> Home:
    """The data folder (``WORDCUT_HOME``)."""
    return Home.from_environment()


def live_source() -> LiveSource:
    return YouTube()
