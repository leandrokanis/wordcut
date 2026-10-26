"""The guard that keeps a run off the real network (ADR-0017).

While ``WORDCUT_FORBID_NETWORK`` is set, the factories of the real outside world refuse with
``network_error`` before building anything. The test suite sets it, and every process the
suite starts inherits it, a detached task included.
"""

from __future__ import annotations

import os

from wordcut.errors import WordcutError

FORBID_NETWORK = "WORDCUT_FORBID_NETWORK"


def refuse_when_forbidden(service: str) -> None:
    """Raise ``network_error`` instead of reaching ``service`` while the network is forbidden."""
    if FORBID_NETWORK in os.environ:
        raise WordcutError(
            "network_error",
            f"Rede proibida neste ambiente ({FORBID_NETWORK}): {service} não foi chamado.",
            {"forbidden_by": FORBID_NETWORK},
        )
