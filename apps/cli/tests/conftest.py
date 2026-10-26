"""Fixtures of the CLI test suite."""

from __future__ import annotations

import pytest

from wordcut.youtube import LiveInfo
from wordcut_cli import deps


class NoYouTube:
    def info(self, url: str) -> LiveInfo:
        raise AssertionError("test reached YouTube; replace wordcut_cli.deps.live_source")


@pytest.fixture(autouse=True)
def no_real_youtube(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(deps, "live_source", NoYouTube)
