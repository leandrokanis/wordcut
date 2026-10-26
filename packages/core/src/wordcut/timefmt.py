"""Timestamp parsing and formatting (``HH:MM:SS.mmm``)."""

from __future__ import annotations

import re

# [[HH:]MM:]SS[.fraction]: ASCII digits only, the fraction only on the seconds.
_TIMESTAMP = re.compile(r"(?:(?:([0-9]+):)?([0-9]+):)?([0-9]+(?:\.[0-9]+)?)")
MINUTES_PER_HOUR = 60
SECONDS_PER_MINUTE = 60


def parse_timestamp(text: str) -> float:
    """Seconds from ``SS``, ``MM:SS`` or ``HH:MM:SS``, the seconds with optional decimals.

    The leading component may be any size (``75:30`` is 75 minutes); the ones after it
    stay below 60.
    """
    match = _TIMESTAMP.fullmatch(text.strip())
    if match is None:
        raise ValueError(f"tempo inválido: {text!r}")
    hours_text, minutes_text, seconds_text = match.groups()
    hours, minutes, seconds = int(hours_text or 0), int(minutes_text or 0), float(seconds_text)
    if (hours_text is not None and minutes >= MINUTES_PER_HOUR) or (
        minutes_text is not None and seconds >= SECONDS_PER_MINUTE
    ):
        raise ValueError(f"tempo fora do relógio: {text!r}")
    return (hours * MINUTES_PER_HOUR + minutes) * SECONDS_PER_MINUTE + seconds


def format_timestamp(seconds: float) -> str:
    milliseconds = round(seconds * 1000)
    hours, rest = divmod(milliseconds, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    return f"{hours:02d}:{minutes:02d}:{rest / 1000:06.3f}"
