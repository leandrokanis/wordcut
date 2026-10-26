"""Timestamp parsing and formatting (``HH:MM:SS.mmm``)."""

from __future__ import annotations


def parse_timestamp(text: str) -> float:
    """Seconds from ``SS``, ``MM:SS`` or ``HH:MM:SS``, each with optional decimals."""
    parts = text.strip().split(":")
    if not 1 <= len(parts) <= 3 or not all(parts):
        raise ValueError(f"tempo inválido: {text!r}")
    seconds = 0.0
    for part in parts:
        seconds = seconds * 60 + float(part)
    if seconds < 0:
        raise ValueError(f"tempo negativo: {text!r}")
    return seconds


def format_timestamp(seconds: float) -> str:
    milliseconds = round(seconds * 1000)
    hours, rest = divmod(milliseconds, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    return f"{hours:02d}:{minutes:02d}:{rest / 1000:06.3f}"
