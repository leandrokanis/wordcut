"""Fixtures shared by the Python test suites of the monorepo."""

from __future__ import annotations

import contextlib
import os
import signal
import subprocess
import sys
from collections.abc import Callable, Iterator
from pathlib import Path
from types import FrameType
from typing import Any

import pytest

LOCK_OWNER = """
import sys, time
from wordcut.home import Home
from wordcut.lock import ProcessingLock
with ProcessingLock(Home.from_environment()).acquire(sys.argv[1], sys.argv[2]):
    print("ready", flush=True)
    time.sleep(600)
"""

# Stands in for a detached task process: holds what it inherits (the lock) and does nothing.
HARMLESS_TASK = [sys.executable, "-c", "import time; time.sleep(60)"]

# A test that waits on another process fails instead of hanging the whole suite.
TIME_LIMIT_SECONDS = 20

StartLockOwner = Callable[[str, str], "subprocess.Popen[str]"]


@pytest.fixture(autouse=True)
def no_real_processing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail a test that would process with YouTube, WhisperX and ffmpeg for real."""
    from wordcut import processing

    def refuse() -> processing.ProcessingGateways:
        raise AssertionError("test reached real processing; replace processing.default_gateways")

    monkeypatch.setattr(processing, "default_gateways", refuse)


@pytest.fixture
def wordcut_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "wordcut"
    monkeypatch.setenv("WORDCUT_HOME", str(root))
    return root


@pytest.fixture
def time_limit() -> Iterator[None]:
    """Fail the test with ``TimeoutError`` once it runs longer than ``TIME_LIMIT_SECONDS``."""

    def time_out(signum: int, frame: FrameType | None) -> None:
        raise TimeoutError(f"test took longer than {TIME_LIMIT_SECONDS} s")

    previous = signal.signal(signal.SIGALRM, time_out)
    signal.alarm(TIME_LIMIT_SECONDS)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)


@pytest.fixture
def lock_owner(wordcut_home: Path, time_limit: None) -> Iterator[StartLockOwner]:
    """Start another process that holds the processing lock of ``wordcut_home``."""
    owners: list[subprocess.Popen[str]] = []

    def start(kind: str, resource: str) -> subprocess.Popen[str]:
        owner = subprocess.Popen(
            [sys.executable, "-c", LOCK_OWNER, kind, resource], stdout=subprocess.PIPE, text=True
        )
        owners.append(owner)
        assert owner.stdout is not None
        assert owner.stdout.readline() == "ready\n"
        return owner

    try:
        yield start
    finally:
        for owner in owners:
            owner.kill()
            owner.wait()


@pytest.fixture
def detached_tasks(
    wordcut_home: Path, time_limit: None, monkeypatch: pytest.MonkeyPatch
) -> Iterator[list[subprocess.Popen[bytes]]]:
    """The processes of the tasks the test launches detached, killed and reaped at its end."""
    from wordcut.tasks import execution

    launched: list[subprocess.Popen[bytes]] = []
    launch = execution.Popen

    def record(*args: Any, **kwargs: Any) -> subprocess.Popen[bytes]:
        process = launch(*args, **kwargs)
        launched.append(process)
        return process

    monkeypatch.setattr(execution, "Popen", record)
    try:
        yield launched
    finally:
        for process in launched:
            # The task process leads its own session, so its group id is its PID.
            with contextlib.suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
            process.wait()


@pytest.fixture
def harmless_tasks(
    wordcut_home: Path, time_limit: None, monkeypatch: pytest.MonkeyPatch
) -> Iterator[list[subprocess.Popen[bytes]]]:
    """Tasks launched detached run a harmless process instead, killed and reaped at the end.

    The task stays ``running`` and its lock held, and nothing of the task's kind runs.
    """
    from wordcut.tasks import execution

    launched: list[subprocess.Popen[bytes]] = []

    def launch(command: list[str], **kwargs: Any) -> subprocess.Popen[bytes]:
        process = subprocess.Popen(HARMLESS_TASK, **kwargs)
        launched.append(process)
        return process

    monkeypatch.setattr(execution, "Popen", launch)
    try:
        yield launched
    finally:
        for process in launched:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
            process.wait()
