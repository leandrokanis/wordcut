"""The machine-wide processing lock: one heavy operation at a time (ADR-0006).

``ProcessingLock.acquire`` takes an exclusive, non-blocking ``flock`` on
``<home>/processing.lock`` and writes the holder's description into that file. The kernel
releases the lock when the holder process dies, so a stale description is never reported:
``holder`` reads the file only while the lock is actually held.
"""

from __future__ import annotations

import fcntl
import json
import os
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass, replace
from datetime import datetime

from wordcut.errors import WordcutError
from wordcut.home import Home

LOCK_FILE_MODE = 0o600


@dataclass(frozen=True)
class LockHolder:
    """Who holds the lock; a field is ``None`` while the holder has not written it yet."""

    kind: str | None
    resource: str | None
    pid: int | None
    started_at: str | None
    task_id: int | None = None


class HeldLock:
    """The lock taken through ``descriptor``; it stays held until every copy is closed."""

    def __init__(self, descriptor: int) -> None:
        self.descriptor = descriptor
        self._holder: LockHolder | None = None
        self._released = False

    def describe(self, holder: LockHolder) -> None:
        self._holder = holder
        _describe(self.descriptor, holder)

    def assign(self, task_id: int) -> None:
        """Describe the holder as the task ``task_id``."""
        assert self._holder is not None
        self.describe(replace(self._holder, task_id=task_id))

    def release(self) -> None:
        """Close this process's copy of the descriptor; a task process may keep another."""
        if not self._released:
            os.close(self.descriptor)
            self._released = True


class ProcessingLock:
    def __init__(self, home: Home) -> None:
        self._home = home

    @contextmanager
    def acquire(self, kind: str, resource: str) -> Iterator[HeldLock]:
        """Hold the lock for the block, or raise ``busy`` at once if another process has it."""
        self._home.ensure()
        # Do not open with O_TRUNC: a refused attempt would erase the holder's description.
        held = HeldLock(os.open(self._home.lock_file, os.O_RDWR | os.O_CREAT, LOCK_FILE_MODE))
        try:
            self._lock_exclusively(held.descriptor)
            held.describe(LockHolder(kind, resource, os.getpid(), _now()))
            yield held
        finally:
            held.release()

    @contextmanager
    def adopt(self, descriptor: int) -> Iterator[HeldLock]:
        """Hold the lock the launching process passed on as ``descriptor``, see ADR-0013.

        The description keeps the operation, the task and the start time, with this
        process's PID.
        """
        held = HeldLock(descriptor)
        try:
            self._lock_exclusively(descriptor)
            inherited = _parse_holder(os.pread(descriptor, os.fstat(descriptor).st_size, 0))
            held.describe(replace(inherited, pid=os.getpid()))
            yield held
        finally:
            held.release()

    def holder(self) -> LockHolder | None:
        """The current holder, or ``None`` when the lock is free."""
        try:
            descriptor = os.open(self._home.lock_file, os.O_RDONLY)
        except FileNotFoundError:
            return None
        try:
            if _is_free(descriptor):
                return None
            return _parse_holder(os.read(descriptor, os.fstat(descriptor).st_size))
        finally:
            os.close(descriptor)

    def _lock_exclusively(self, descriptor: int) -> None:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise _busy(self.holder()) from None


def _is_free(descriptor: int) -> bool:
    try:
        fcntl.flock(descriptor, fcntl.LOCK_SH | fcntl.LOCK_NB)
    except BlockingIOError:
        return False
    fcntl.flock(descriptor, fcntl.LOCK_UN)
    return True


def _describe(descriptor: int, holder: LockHolder) -> None:
    os.ftruncate(descriptor, 0)
    # pwrite at 0: a second description must not land after the first one's end.
    os.pwrite(descriptor, json.dumps(asdict(holder)).encode(), 0)


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _parse_holder(raw: bytes) -> LockHolder:
    try:
        description = json.loads(raw)
    except ValueError:
        description = {}
    if not isinstance(description, dict):
        description = {}
    return LockHolder(
        kind=_text(description.get("kind")),
        resource=_text(description.get("resource")),
        pid=_integer(description.get("pid")),
        started_at=_text(description.get("started_at")),
        task_id=_integer(description.get("task_id")),
    )


def _text(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _integer(value: object) -> int | None:
    return value if isinstance(value, int) else None


def _busy(holder: LockHolder | None) -> WordcutError:
    details = asdict(holder) if holder else {}
    return WordcutError("busy", "A máquina está ocupada com outro processamento.", details)
