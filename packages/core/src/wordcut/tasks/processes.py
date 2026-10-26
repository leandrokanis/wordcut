"""Whether the process of a task still runs, on this machine (FR-006 of 3.1.a.2)."""

from __future__ import annotations

import os
import socket

ZOMBIE_STATE = "Z"


def this_host() -> str:
    return socket.gethostname()


def is_running(pid: int) -> bool:
    """True while ``pid`` runs; a zombie, ended but not yet reaped, no longer runs."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return not _is_zombie(pid)


def _is_zombie(pid: int) -> bool:
    try:
        stat = f"/proc/{pid}/stat"
        with open(stat, encoding="utf-8", errors="replace") as status:
            line = status.read()
    except OSError:
        return False
    # proc(5): "pid (comm) state ...", and comm may itself hold ") ".
    return line.rpartition(")")[2].split()[:1] == [ZOMBIE_STATE]
