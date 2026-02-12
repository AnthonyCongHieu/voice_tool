"""Default configuration for punctuation mapping and target silences."""

from __future__ import annotations

from typing import Dict, Tuple

DEFAULT_PUNCT_SILENCE_MS: Dict[str, list[str]] = {
    "STRONG": [".", "?", "!", "\n"],
    "MEDIUM": [",", ";"],
    "ELLIPSIS": ["…"],
}

# Ranges in milliseconds (min, max)
DEFAULT_TARGET_SILENCE_MS: Dict[str, Tuple[int, int]] = {
    "STRONG": (700, 900),
    "MEDIUM": (250, 400),
    "ELLIPSIS": (450, 650),
}


def midpoint_targets(ranges: Dict[str, Tuple[int, int]]) -> Dict[str, int]:
    """Return midpoint value for each silence range."""
    return {k: int((v[0] + v[1]) / 2) for k, v in ranges.items()}
