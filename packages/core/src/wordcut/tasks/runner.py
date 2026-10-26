"""Entry point of a detached task process (ADR-0007, ADR-0013).

``python -m wordcut.tasks.runner <task_id> [<lock_descriptor>]`` runs the task recorded as
``task_id`` in the data folder of ``WORDCUT_HOME``. ``lock_descriptor`` is the inherited
descriptor of the processing lock, given for kinds that need the lock.
"""

from __future__ import annotations

import sys

from wordcut.home import Home
from wordcut.tasks.execution import resume


def main(argv: list[str]) -> int:
    task_id, *lock = (int(argument) for argument in argv)
    outcome = resume(Home.from_environment(), task_id, lock[0] if lock else None)
    if outcome.traceback is not None:
        sys.stderr.write(outcome.traceback)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
