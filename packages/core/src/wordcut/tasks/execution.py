"""Run a task in the foreground or in a detached process (docs/cli.md §6, ADR-0007)."""

from __future__ import annotations

import math
import os
import sys
import threading
import time
import traceback
from collections.abc import Callable, Iterator
from contextlib import closing, contextmanager
from dataclasses import dataclass
from datetime import datetime
from subprocess import DEVNULL, STDOUT, Popen
from typing import Any, BinaryIO

from wordcut.db import connect, tasks
from wordcut.db.tasks import NewTask, TaskRow
from wordcut.errors import WordcutError
from wordcut.home import PRIVATE_FOLDER_MODE, Home
from wordcut.lock import HeldLock, ProcessingLock
from wordcut.tasks import (
    Progress,
    ProgressListener,
    Resource,
    Result,
    TaskContext,
    TaskKind,
    kind,
)
from wordcut.tasks.processes import this_host

RUNNER_MODULE = "wordcut.tasks.runner"
LOG_FILE_MODE = 0o600

# Progress is stored at most this often, or when its message changes, to spare the database.
PROGRESS_STORE_INTERVAL_SECONDS = 0.5


def start(
    home: Home,
    kind_name: str,
    resource: Resource,
    params: dict[str, Any],
    *,
    detach: bool,
    on_progress: ProgressListener | None = None,
    admit: Callable[[], None] | None = None,
) -> TaskRow:
    """Start a task of ``kind_name`` on ``resource``.

    A kind that needs the lock raises ``busy`` before any task is recorded. ``admit`` runs
    next, under the lock: what it raises refuses the task before it is recorded. With ``detach``,
    a process in a session of its own runs the task and the running task returns at once.
    Otherwise the task runs here, ``on_progress`` hears its progress, and the succeeded task
    returns; a failure raises its ``WordcutError``, and Ctrl+C raises ``KeyboardInterrupt``
    once the task is recorded ``failed`` as ``interrupted``.
    """
    task_kind = kind(kind_name)
    with _lock_for(home, task_kind, resource) as held:
        if admit is not None:
            admit()
        task = _create(home, task_kind, resource, params)
        if held is not None:
            held.assign(task.id)
        if detach:
            return _launch(home, task, held)
        outcome = _execute(home, task, task_kind, on_progress)
    finished = _record(home, task.id, outcome)
    if outcome.interrupted:
        raise KeyboardInterrupt
    if outcome.error is not None:
        raise outcome.error
    return finished


def resume(home: Home, task_id: int, lock_descriptor: int | None) -> Outcome:
    """Run, in the detached process, the task ``start`` launched (``wordcut.tasks.runner``)."""
    with closing(connect(home)) as connection:
        task = tasks.by_id(connection, task_id)
    assert task is not None
    with _inherited_lock(home, lock_descriptor):
        outcome = _execute(home, task, kind(task.kind), None)
    _record(home, task.id, outcome)
    return outcome


def _create(home: Home, task_kind: TaskKind, resource: Resource, params: dict[str, Any]) -> TaskRow:
    """Record the task as running in this process; a detached launch changes the PID later."""
    new = NewTask(
        kind=task_kind.name,
        resource_type=resource.type,
        resource_id=resource.id,
        params=params,
        pid=os.getpid(),
        host=this_host(),
        started_at=_now(),
    )
    with closing(connect(home)) as connection:
        return tasks.insert(connection, new)


def _launch(home: Home, task: TaskRow, held: HeldLock | None) -> TaskRow:
    """Start the detached process of ``task``, which takes the lock over from ``held``."""
    command = [sys.executable, "-m", RUNNER_MODULE, str(task.id)]
    inherited = () if held is None else (held.descriptor,)
    command.extend(str(descriptor) for descriptor in inherited)
    with _open_log(home, task.id) as log:
        try:
            process = Popen(
                command,
                start_new_session=True,
                stdin=DEVNULL,
                stdout=log,
                stderr=STDOUT,
                pass_fds=inherited,
                env={**os.environ, "WORDCUT_HOME": str(home.root)},
            )
        except Exception:
            # Otherwise the task would look alive for as long as the launcher runs.
            failure = WordcutError("internal_error", "Não foi possível iniciar a tarefa.")
            _record(home, task.id, Outcome(error=failure))
            raise
    if held is not None:
        # Once the launcher's copy is closed, the lock lives exactly as long as the task process.
        held.release()
    threading.Thread(target=process.wait, daemon=True).start()
    with closing(connect(home)) as connection:
        tasks.set_pid(connection, task.id, process.pid)
        launched = tasks.by_id(connection, task.id)
    assert launched is not None
    return launched


def _open_log(home: Home, task_id: int) -> BinaryIO:
    path = home.task_log(task_id)
    path.parent.mkdir(mode=PRIVATE_FOLDER_MODE, exist_ok=True)
    return open(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, LOG_FILE_MODE), "wb")


@contextmanager
def _inherited_lock(home: Home, descriptor: int | None) -> Iterator[None]:
    if descriptor is None:
        yield
        return
    with ProcessingLock(home).adopt(descriptor):
        yield


@contextmanager
def _lock_for(home: Home, task_kind: TaskKind, resource: Resource) -> Iterator[HeldLock | None]:
    if not task_kind.needs_lock:
        yield None
        return
    with ProcessingLock(home).acquire(task_kind.name, str(resource)) as held:
        yield held


@dataclass(frozen=True)
class Outcome:
    """How a task ended; ``traceback`` is the text of an unexpected exception, for the log."""

    result: Result | None = None
    error: WordcutError | None = None
    traceback: str | None = None
    interrupted: bool = False


def _execute(
    home: Home, task: TaskRow, task_kind: TaskKind, on_progress: ProgressListener | None
) -> Outcome:
    recorder = _ProgressRecorder(home, task, on_progress)
    resource = Resource(task.resource_type, task.resource_id)
    try:
        return Outcome(
            result=task_kind.run(TaskContext(home, resource, task.params, recorder.report))
        )
    except WordcutError as failure:
        return Outcome(error=failure)
    except KeyboardInterrupt:
        stopped = WordcutError("interrupted", "A tarefa foi interrompida pelo usuário.")
        return Outcome(error=stopped, interrupted=True)
    except Exception as unexpected:
        internal = WordcutError("internal_error", "Erro interno inesperado na tarefa.")
        internal.__cause__ = unexpected
        return Outcome(error=internal, traceback=traceback.format_exc())


def _record(home: Home, task_id: int, outcome: Outcome) -> TaskRow:
    """Store how the task ended; called once its lock is released, see ADR-0013."""
    with closing(connect(home)) as connection:
        if outcome.error is None:
            tasks.finish_succeeded(connection, task_id, outcome.result or {}, _now())
        else:
            error = outcome.error
            tasks.finish_failed(
                connection, task_id, error.code, error.message, error.details, _now()
            )
        finished = tasks.by_id(connection, task_id)
    assert finished is not None
    return finished


def _now() -> datetime:
    return datetime.now().astimezone().replace(microsecond=0)


class _ProgressRecorder:
    """Stores the progress of ``task`` and then tells ``listener``, throttled."""

    def __init__(self, home: Home, task: TaskRow, listener: ProgressListener | None) -> None:
        self._home = home
        self._task = task
        self._listener = listener
        self._last_message: str | None = None
        self._last_stored_at = -math.inf

    def report(self, fraction: float, message: str) -> None:
        moment = time.monotonic()
        is_due = moment - self._last_stored_at >= PROGRESS_STORE_INTERVAL_SECONDS
        if not is_due and message == self._last_message:
            return
        self._last_message, self._last_stored_at = message, moment
        with closing(connect(self._home)) as connection:
            tasks.record_progress(connection, self._task.id, fraction, message)
        if self._listener is not None:
            self._listener(Progress(self._task.id, self._task.kind, fraction, message))
