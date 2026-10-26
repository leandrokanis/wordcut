import fcntl
import os
import re
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

from wordcut.errors import WordcutError
from wordcut.home import Home
from wordcut.lock import LockHolder, ProcessingLock

StartLockOwner = Callable[[str, str], subprocess.Popen[str]]


def test_holder_describes_the_operation_holding_the_lock(tmp_path: Path) -> None:
    lock = ProcessingLock(Home(tmp_path))

    with lock.acquire("process", "sermon 12"):
        holder = lock.holder()

    assert holder is not None
    assert (holder.kind, holder.resource, holder.pid) == ("process", "sermon 12", os.getpid())


def test_holder_describes_another_process_holding_the_lock(
    wordcut_home: Path, lock_owner: StartLockOwner
) -> None:
    owner = lock_owner("render", "cut 34")

    holder = ProcessingLock(Home(wordcut_home)).holder()

    assert holder is not None
    assert (holder.kind, holder.resource, holder.pid) == ("render", "cut 34", owner.pid)


def test_acquiring_a_held_lock_fails_at_once_with_busy_and_the_holder_details(
    wordcut_home: Path, lock_owner: StartLockOwner
) -> None:
    owner = lock_owner("render", "cut 34")
    lock = ProcessingLock(Home(wordcut_home))

    with pytest.raises(WordcutError) as refused, lock.acquire("process", "sermon 12"):
        pass

    details = refused.value.details or {}
    assert (refused.value.code, details["kind"], details["resource"], details["pid"]) == (
        "busy",
        "render",
        "cut 34",
        owner.pid,
    )


def test_refused_attempt_leaves_the_holder_description_intact(
    wordcut_home: Path, lock_owner: StartLockOwner
) -> None:
    lock_owner("render", "cut 34")
    lock = ProcessingLock(Home(wordcut_home))
    before = lock.holder()

    with pytest.raises(WordcutError), lock.acquire("process", "sermon 12"):
        pass

    assert lock.holder() == before


def test_lock_is_free_again_once_its_holder_process_is_killed(
    wordcut_home: Path, lock_owner: StartLockOwner
) -> None:
    owner = lock_owner("render", "cut 34")
    lock = ProcessingLock(Home(wordcut_home))

    owner.kill()
    owner.wait()

    assert lock.holder() is None


def test_lock_can_be_acquired_after_its_holder_process_is_killed(
    wordcut_home: Path, lock_owner: StartLockOwner
) -> None:
    owner = lock_owner("render", "cut 34")
    lock = ProcessingLock(Home(wordcut_home))
    owner.kill()
    owner.wait()

    with lock.acquire("process", "sermon 12"):
        holder = lock.holder()

    assert holder is not None and holder.pid == os.getpid()


def test_leaving_the_block_releases_the_lock(tmp_path: Path) -> None:
    lock = ProcessingLock(Home(tmp_path))

    with lock.acquire("process", "sermon 12"):
        pass

    assert lock.holder() is None


def test_start_time_is_local_iso_8601_with_offset_and_whole_seconds(tmp_path: Path) -> None:
    lock = ProcessingLock(Home(tmp_path))

    with lock.acquire("process", "sermon 12"):
        holder = lock.holder()

    assert holder is not None
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d", holder.started_at or "")


def test_lock_that_was_never_taken_is_free(tmp_path: Path) -> None:
    assert ProcessingLock(Home(tmp_path / "nova")).holder() is None


@pytest.mark.parametrize("content", ["", '{"kind": "pro', "[1, 2]"])
def test_lock_held_before_its_description_is_written_shows_an_unknown_holder(
    tmp_path: Path, content: str
) -> None:
    home = Home(tmp_path)
    home.lock_file.write_text(content)

    with home.lock_file.open() as held:
        fcntl.flock(held, fcntl.LOCK_EX)
        holder = ProcessingLock(home).holder()

    assert holder == LockHolder(kind=None, resource=None, pid=None, started_at=None)
