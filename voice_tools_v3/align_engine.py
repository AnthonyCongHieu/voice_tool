"""Alignment engine using WhisperX or faster-whisper with naive fallback."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .audio_io import duration_ms


@dataclass
class Word:
    text: str
    start_ms: int
    end_ms: int
    conf: float = 1.0


def _naive_align(wav_path: str, script_text: str) -> List[Word]:
    """Very naive alignment distributing words evenly over duration."""
    total_dur = duration_ms(wav_path)
    tokens = [w for w in script_text.split() if w]
    if not tokens:
        return []
    step = total_dur // max(len(tokens), 1)
    words = []
    current = 0
    for tok in tokens:
        start = current
        end = current + step
        words.append(Word(tok, start, end))
        current = end
    # last word end at total duration
    if words:
        words[-1].end_ms = total_dur
    return words


def align_with_script(wav_path: str, script_text: str) -> List[Word]:
    """Align audio with script returning word-level timestamps.

    Tries WhisperX, then faster-whisper; falls back to naive distribution if
    heavy models are not installed. This keeps the CLI functional even without
    ML dependencies, though accuracy will be poor without them.
    """
    try:
        import whisperx  # type: ignore

        model = whisperx.load_model("large-v2", device="cpu", language="vi")
        result = model.transcribe(wav_path)
        align_model, metadata = whisperx.load_align_model(language="vi", device="cpu")
        aligned = whisperx.align(result["segments"], align_model, metadata, wav_path, device="cpu")
        words = [
            Word(w["text"], int(w["start"] * 1000), int(w["end"] * 1000), float(w.get("confidence", 1.0)))
            for seg in aligned["segments"]
            for w in seg["words"]
        ]
        return words
    except Exception:
        pass
    try:
        from faster_whisper import WhisperModel  # type: ignore

        model = WhisperModel("small", device="cpu")
        segments, _ = model.transcribe(wav_path, language="vi")
        words: List[Word] = []
        for seg in segments:
            for w in seg.words:
                words.append(Word(w.word, int(w.start * 1000), int(w.end * 1000), float(w.probability)))
        return words
    except Exception:
        pass

    return _naive_align(wav_path, script_text)
