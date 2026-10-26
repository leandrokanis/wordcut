"""What commands that launch a task share: ``--wait`` and the progress lines (docs/cli.md §6).

A command adds ``--wait`` with ``add_wait_option`` and returns ``launch(ctx, wait, start)``,
where ``start`` starts its task, detached or in the foreground.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from typing import Any, Protocol

from wordcut.db.tasks import TaskRow
from wordcut.service.tasks import launched_task
from wordcut.tasks import Progress, ProgressListener
from wordcut_cli.contract import Context


class StartTask(Protocol):
    """Starts the command's task, detached or in the foreground (``wordcut.tasks.execution``)."""

    def __call__(self, *, detach: bool, on_progress: ProgressListener | None = ...) -> TaskRow: ...


def add_wait_option(command: argparse.ArgumentParser) -> None:
    command.add_argument(
        "--wait",
        action="store_true",
        help="espera o fim da tarefa, com o progresso no stderr, e devolve o resultado",
    )


def launch(ctx: Context, wait: bool, start: StartTask) -> dict[str, Any]:
    """Without ``wait``, the launched task at once; with it, the task's result (§6.2, §6.3)."""
    if not wait:
        return launched_task(start(detach=True))
    return start(detach=False, on_progress=progress_printer(ctx)).result or {}


def progress_printer(ctx: Context) -> Callable[[Progress], None]:
    """Write each progress to stderr as ``[kind] message 42%``; ``--quiet`` silences it."""

    def show(progress: Progress) -> None:
        if not ctx.quiet:
            print(
                f"[{progress.kind}] {progress.message} {percent(progress.fraction)}",
                file=sys.stderr,
            )

    return show


def render_result(result: dict[str, Any]) -> str:
    """The result of a finished task, one ``field: value`` per line."""
    lines = [f"{field}: {value}" for field, value in result.items()]
    return "\n".join(lines) or "Tarefa concluída."


def resource_label(task: dict[str, Any]) -> str:
    """The resource of a shown task, from its ``<type>_id`` field, as ``sermon 12``."""
    [(field, value)] = [(field, value) for field, value in task.items() if field.endswith("_id")]
    return f"{field.removesuffix('_id')} {value}"


def percent(fraction: float) -> str:
    return f"{round(fraction * 100)}%"
