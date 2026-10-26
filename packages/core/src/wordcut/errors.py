"""Domain errors with a stable code and the process exit code each code maps to.

Every adapter (CLI, API) reports failures through ``WordcutError``: programs decide by
``code`` and exit code, people read ``message`` (Portuguese). See docs/cli.md §5.
"""

from __future__ import annotations

from typing import Any

# docs/cli.md §5.1 and §5.3: existing codes must never change their exit code.
EXIT_CODES: dict[str, int] = {
    "internal_error": 1,
    "interrupted": 1,
    "invalid_argument": 2,
    "not_found": 3,
    "busy": 4,
    "live_not_finished": 5,
    "sermon_not_trimmed": 5,
    "sermon_too_short": 5,
    "sermon_not_processed": 5,
    "would_discard_edits": 5,
    "spelling_too_different": 5,
    "default_preset": 5,
    "last_admin": 5,
    "youtube_error": 6,
    "llm_error": 6,
    "network_error": 6,
}


class WordcutError(Exception):
    """A failure the user can react to, identified by a code listed in ``EXIT_CODES``."""

    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        if code not in EXIT_CODES:
            raise ValueError(f"unknown error code: {code}")
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details

    @property
    def exit_code(self) -> int:
        return EXIT_CODES[self.code]

    def to_dict(self) -> dict[str, Any]:
        """The ``{"code", "message", "details"?}`` object of docs/cli.md §5.2."""
        error: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.details is not None:
            error["details"] = self.details
        return error
