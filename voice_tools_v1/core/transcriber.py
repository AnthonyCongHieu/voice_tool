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
    import sys
    
    # Determine base path for models
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
    models_dir = os.path.join(base_path, "models")
    os.makedirs(models_dir, exist_ok=True)
    
    # Determine compute type
    compute_type = "float16" if model_size != "small" else "int8"
    
    # Paths to check (Priority: Local -> System Cache)
    possible_roots = [
        models_dir, # ./models
        os.path.join(os.path.expanduser("~"), ".cache", "whisper"), # Default cache
        os.path.join(os.path.expanduser("~"), ".cache", "huggingface", "hub") # HF cache
    ]
    
    selected_root = models_dir # Default to local for download
    found_existing = False
    
    print(f"\n[AI] Searching for model '{model_size}'...")
    
    for root in possible_roots:
        if os.path.exists(root):
            # Check if likely contains the model (simple check)
            # Faster-whisper folder names usually start with "models--"
            # We just check if the folder exists for now to prefer existing cache
            print(f"  - Checking: {root}")
            # If standard whisper cache exists and not empty, use it to avoid re-download
            if len(os.listdir(root)) > 0: 
                selected_root = root
                found_existing = True
                print(f"  -> Found potential cache at: {root}")
                break
    
    if not found_existing:
         print(f"[AI] Model not found locally. Will download to: {selected_root}")
         print("[AI] This make take a few minutes (approx 2GB)...")

    try:
        _cached_model = WhisperModel(
            model_size,
            device="cuda",
            compute_type=compute_type,
            download_root=selected_root,
            local_files_only=False
        )
        print(f"[AI] Model '{model_size}' loaded successfully from {selected_root}!")
        _cached_model_size = model_size
        return _cached_model
        
    except Exception as e:
        print(f"[ERROR] Failed to load model: {e}")
        # Build friendly error message
        raise RuntimeError(f"Model Load Failed: {str(e)}\nPath: {models_dir}")


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
    
    # Try transcribing with VAD enabled (default)
    try:
        segments, info = model.transcribe(
            audio_path,
            language="vi",
            word_timestamps=True,
            vad_filter=True,
            beam_size=5 if model_size == "large-v3" else 3
        )
        
        # Generator verification inside try block
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

    except Exception as e:
        error_msg = str(e)
        if "ONNX" in error_msg or "silero" in error_msg.lower():
            if progress_callback:
                progress_callback("[WARN] VAD Error (ONNX). Retrying without VAD...")
            
            # Fallback: Disable VAD
            segments, info = model.transcribe(
                audio_path,
                language="vi",
                word_timestamps=True,
                vad_filter=False, # Disable VAD
                beam_size=5 if model_size == "large-v3" else 3
            )
            
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
                     progress_callback(f"Transcribed (No VAD): {segment.end:.1f}s")
        else:
            raise e # Re-raise if not ONNX error

    if progress_callback:
        progress_callback(f"Done: {len(words)} words")
    
    return words


def preload_model(model_size: str = "medium"):
    """Preload model at app startup for instant transcription later."""
    get_whisper_model(model_size)
