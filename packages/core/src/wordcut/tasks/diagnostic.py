"""The ``diagnostic`` task: waits, reports progress and fails on request.

It exercises the task machinery end to end without YouTube or a GPU, and is not exposed by
any command. Parameters: ``seconds`` to wait; ``fail_with`` an error code to fail with;
``crash`` true to fail with an unexpected exception.
"""

from __future__ import annotations

import time

from wordcut.errors import WordcutError
from wordcut.tasks import Result, TaskContext, TaskKind, register

STEP_SECONDS = 0.1
WAITING_MESSAGE = "aguardando"
DONE_MESSAGE = "pronto"


def _run(ctx: TaskContext) -> Result:
    seconds = float(ctx.params.get("seconds", 0))
    steps = max(1, round(seconds / STEP_SECONDS))
    for step in range(steps):
        ctx.progress(step / steps, WAITING_MESSAGE)
        time.sleep(seconds / steps)
    if ctx.params.get("crash"):
        raise RuntimeError(f"diagnostic crash on {ctx.resource}")
    fail_with = ctx.params.get("fail_with")
    if fail_with:
        raise WordcutError(fail_with, "Falha pedida ao diagnóstico.", {"requested": True})
    ctx.progress(1.0, DONE_MESSAGE)
    return {"waited_seconds": seconds}


DIAGNOSTIC = register(TaskKind(name="diagnostic", run=_run))
