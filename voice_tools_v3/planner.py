"""Planning of speech and silence segments."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from .align_engine import Word
from .config import DEFAULT_PUNCT_SILENCE_MS
from .punctuation import SentenceAnchor


@dataclass
class PlanItem:
    kind: str  # "speech" | "silence"
    start_ms: int = 0
    end_ms: int = 0
    dur_ms: int = 0


def build_plan(
    words: List[Word],
    anchors: List[SentenceAnchor],
    target_silence_ms: Dict[str, int],
    punct_map: Dict[str, list[str]] | None = None,
) -> List[PlanItem]:
    """Create sequence of speech and silence items."""
    if not words:
        return []

    if punct_map is None:
        punct_map = DEFAULT_PUNCT_SILENCE_MS

    # Map punctuation char -> group
    punct_group: Dict[str, str] = {}
    for group, chars in punct_map.items():
        for ch in chars:
            punct_group[ch] = group

    # Determine sentence bounds
    sentence_bounds = []  # list of (start_ms, end_ms, punct)
    prev_idx = 0
    for anch in anchors:
        end_idx = anch.idx
        # skip punctuation that maps to a word index we've already passed
        # or that falls beyond the available words
        if end_idx >= len(words) or end_idx < prev_idx:
            continue
        start_ms = words[prev_idx].start_ms
        end_ms = words[end_idx].end_ms
        sentence_bounds.append((start_ms, end_ms, anch.punct))
        prev_idx = end_idx + 1
    # tail
    if prev_idx < len(words):
        sentence_bounds.append((words[prev_idx].start_ms, words[-1].end_ms, None))

    plan: List[PlanItem] = []
    for i, (start_ms, end_ms, punct) in enumerate(sentence_bounds):
        plan.append(PlanItem(kind="speech", start_ms=start_ms, end_ms=end_ms, dur_ms=end_ms - start_ms))
        if punct and i < len(sentence_bounds) - 1:
            group = punct_group.get(punct)
            if group and group in target_silence_ms:
                dur = target_silence_ms[group]
                plan.append(PlanItem(kind="silence", dur_ms=dur))
    return plan
