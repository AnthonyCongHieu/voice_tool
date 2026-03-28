"""Punctuation utilities and sentence anchor extraction."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Tuple

from .align_engine import Word


@dataclass
class SentenceAnchor:
    idx: int
    end_ms: int
    punct: str


def extract_punctuation_points(script_text: str) -> List[Tuple[int, str]]:
    pattern = re.compile(r"[\.\?!,;…\n]")
    return [(m.start(), m.group()) for m in pattern.finditer(script_text)]


def sentence_anchors(words: List[Word], script_text: str) -> List[SentenceAnchor]:
    """Map punctuation to the end_ms of the last word before it."""
    puncts = extract_punctuation_points(script_text)
    word_matches = list(re.finditer(r"\b\w+\b", script_text, flags=re.UNICODE))
    anchors: List[SentenceAnchor] = []
    for pos, punct in puncts:
        word_idx = -1
        for i, m in enumerate(word_matches):
            if m.end() <= pos:
                word_idx = i
            else:
                break
        if 0 <= word_idx < len(words):
            anchors.append(SentenceAnchor(idx=word_idx, end_ms=words[word_idx].end_ms, punct=punct))
    return anchors
