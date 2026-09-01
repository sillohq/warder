"""Durations and rates, written the way people say them.

``"30m"`` beats ``timedelta(minutes=30)`` in a declaration that someone reads
more often than they write, and ``"5/15m"`` beats a pair of numbers whose
order you have to remember.
"""

from __future__ import annotations

import re

__all__ = ["parse_duration", "parse_rate"]

_UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800, "y": 31_536_000}
_DURATION = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*([smhdwy])\s*$", re.IGNORECASE)
_RATE = re.compile(r"^\s*(\d+)\s*/\s*(.+?)\s*$")


def parse_duration(value: str | int | float | None) -> float | None:
    """``"30m"`` → ``1800.0``. A bare number is seconds; ``None`` passes through.

    Deliberately one unit per value. ``"1h30m"`` would need a grammar, and
    a declaration that wants ninety minutes can say ``"90m"``.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    match = _DURATION.match(str(value))
    if not match:
        raise ValueError(
            f"{value!r} is not a duration. Write a number and one of "
            "s, m, h, d, w, y — for example '30m' or '12h'."
        )
    return float(match.group(1)) * _UNITS[match.group(2).lower()]


def parse_rate(value: str | None) -> tuple[int, float] | None:
    """``"5/15m"`` → ``(5, 900.0)`` — five attempts per fifteen minutes."""
    if value is None:
        return None
    match = _RATE.match(str(value))
    if not match:
        raise ValueError(
            f"{value!r} is not a rate. Write attempts, a slash and a window — "
            "for example '5/15m'."
        )
    window = parse_duration(match.group(2))
    assert window is not None
    return int(match.group(1)), window
