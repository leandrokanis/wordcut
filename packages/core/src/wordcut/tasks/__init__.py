"""Task kinds: the heavy operations that run as tasks (docs/cli.md §6, ADR-0007).

A kind is registered once with ``register`` and found again by name with ``kind``, which
is how a detached task process rebuilds the operation from the task's row alone. The kinds
of the core are listed in ``BUILTIN_KIND_MODULES`` and loaded on the first lookup.
"""

from __future__ import annotations

import importlib
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from wordcut.home import Home

BUILTIN_KIND_MODULES = ("wordcut.tasks.diagnostic",)

Result = dict[str, Any]


@dataclass(frozen=True)
class Resource:
    """What a task works on, such as sermon 12."""

    type: str
    id: int

    def __str__(self) -> str:
        return f"{self.type} {self.id}"


@dataclass(frozen=True)
class Progress:
    task_id: int
    kind: str
    fraction: float
    message: str


ProgressListener = Callable[[Progress], None]


class TaskContext:
    """What a running task receives: where the data is, its resource and its parameters."""

    def __init__(
        self,
        home: Home,
        resource: Resource,
        params: dict[str, Any],
        report: Callable[[float, str], None],
    ) -> None:
        self.home = home
        self.resource = resource
        self.params = params
        self._report = report

    def progress(self, fraction: float, message: str) -> None:
        """Tell how far the task is, from 0 to 1, and what it is doing, in Portuguese."""
        self._report(fraction, message)


@dataclass(frozen=True)
class TaskKind:
    """A heavy operation: ``run`` returns the task's result or raises ``WordcutError``."""

    name: str
    run: Callable[[TaskContext], Result]
    needs_lock: bool = True


_registry: dict[str, TaskKind] = {}
_builtins_loaded = False


def register(task_kind: TaskKind) -> TaskKind:
    _registry[task_kind.name] = task_kind
    return task_kind


def kind(name: str) -> TaskKind:
    """The kind registered as ``name``; ``ValueError`` if there is none."""
    _load_builtin_kinds()
    try:
        return _registry[name]
    except KeyError:
        raise ValueError(f"unknown task kind: {name}") from None


def _load_builtin_kinds() -> None:
    global _builtins_loaded
    if _builtins_loaded:
        return
    for module in BUILTIN_KIND_MODULES:
        importlib.import_module(module)
    _builtins_loaded = True
