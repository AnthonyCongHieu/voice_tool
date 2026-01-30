# -*- coding: utf-8 -*-
"""
Voice Tools V3 - Transcriber
Lightweight Faster-Whisper integration for Smart Mode
With Model Caching for better performance
"""

import os
import sys
from typing import List, Optional, Callable
from dataclasses import dataclass


@dataclass
class TranscriptWord:
    """Word with timing"""
    text: str
    start: float  # seconds
    end: float    # seconds


# Model cache for singleton pattern
_cached_model = None
_cached_model_size = None


def get_whisper_model(model_size: str = "medium"):
    """
    Get or create Whisper model (singleton pattern).
    Caches model to avoid reloading on each transcription.
    
    Args:
        model_size: "small" (fastest), "medium" (balanced), "large-v3" (most accurate)
    """
    global _cached_model, _cached_model_size
    
    # Return cached model if same size requested
    if _cached_model is not None and _cached_model_size == model_size:
        return _cached_model
    
    from faster_whisper import WhisperModel
    
    # Determine compute type based on model size
    compute_type = "float16" if model_size != "small" else "int8"
    
    _cached_model = WhisperModel(
        model_size,
        device="cuda",
        compute_type=compute_type,
        download_root=os.path.join(os.path.expanduser("~"), ".cache", "whisper")
    )
    _cached_model_size = model_size
    
    return _cached_model


def transcribe_audio(
    audio_path: str,
    progress_callback: Optional[Callable[[str], None]] = None,
    model_size: str = "medium"
) -> List[dict]:
    """
    Transcribe audio using Faster-Whisper.
    Returns list of words with timestamps.
    
    Args:
        audio_path: Path to audio file
        progress_callback: Optional callback for progress updates
        model_size: "small", "medium", or "large-v3"
    """
    if progress_callback:
        progress_callback(f"Loading Whisper ({model_size})...")
    
    model = get_whisper_model(model_size)
    
    if progress_callback:
        progress_callback("Transcribing...")
    
    segments, info = model.transcribe(
        audio_path,
        language="vi",
        word_timestamps=True,
        vad_filter=True,
        beam_size=5 if model_size == "large-v3" else 3  # Faster for smaller models
    )
    
    # Extract words
    words = []
    for segment in segments:
        if segment.words:
            for word in segment.words:
                words.append({
                    'text': word.word.strip(),
                    'start': word.start,
                    'end': word.end
                })
        
        if progress_callback:
            progress_callback(f"Transcribed: {segment.end:.1f}s")
    
    if progress_callback:
        progress_callback(f"Done: {len(words)} words")
    
    return words


def preload_model(model_size: str = "medium"):
    """Preload model at app startup for instant transcription later."""
    get_whisper_model(model_size)
