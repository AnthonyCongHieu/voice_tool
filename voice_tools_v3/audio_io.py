"""Audio I/O utilities using ffmpeg and soundfile."""

from __future__ import annotations

import os
import subprocess
import tempfile
from uuid import uuid4



def to_mono_48k(in_path: str) -> str:
    """Convert input audio to mono 48kHz WAV using ffmpeg.

    Returns path to the converted temporary file.
    """
    out_path = os.path.join(tempfile.gettempdir(), f"vpmn_{uuid4().hex}.wav")
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        in_path,
        "-ac",
        "1",
        "-ar",
        "48000",
        out_path,
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return out_path


def duration_ms(wav_path: str) -> int:
    """Return duration of a WAV file in milliseconds."""
    import soundfile as sf  # local import to avoid hard dependency at import time

    data, sr = sf.read(wav_path)
    return int(len(data) / sr * 1000)
