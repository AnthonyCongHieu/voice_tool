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


def get_whisper_model(model_size: str = "medium", log_callback=None):
    """
    Get or create Whisper model (singleton pattern).
    Caches model to avoid reloading on each transcription.
    
    Args:
        model_size: "small" (fastest), "medium" (balanced), "large-v3-turbo" (best, fast)
        log_callback: Optional function to log messages to UI
    """
    global _cached_model, _cached_model_size
    
    def _log(msg):
        print(msg)  # Always print to console
        if log_callback:
            log_callback(msg)
    
    # Return cached model if same size requested
    if _cached_model is not None and _cached_model_size == model_size:
        _log(f"[AI] Using cached model '{model_size}'")
        return _cached_model
    
    from faster_whisper import WhisperModel
    import sys
    
    # Add nvidia CUDA DLLs to PATH for GPU support
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Find nvidia DLLs in multiple possible locations
    possible_site_packages = [
        os.path.join(base_path, "venv", "Lib", "site-packages"),
        os.path.join(sys.prefix, "Lib", "site-packages"),  # Current venv
    ]
    
    nvidia_subdirs = ["cublas", "cudnn", "cuda_runtime"]
    
    for site_pkg in possible_site_packages:
        for subdir in nvidia_subdirs:
            nvidia_path = os.path.join(site_pkg, "nvidia", subdir, "bin")
            if os.path.exists(nvidia_path) and nvidia_path not in os.environ.get('PATH', ''):
                os.environ['PATH'] = nvidia_path + os.pathsep + os.environ.get('PATH', '')
                print(f"[AI] Added CUDA path: {nvidia_path}")
        
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
    
    _log(f"[AI] Searching for model '{model_size}'...")
    
    for root in possible_roots:
        if os.path.exists(root):
            # Check if likely contains the model (simple check)
            # Faster-whisper folder names usually start with "models--"
            # We just check if the folder exists for now to prefer existing cache
            # If standard whisper cache exists and not empty, use it to avoid re-download
            if len(os.listdir(root)) > 0: 
                selected_root = root
                found_existing = True
                break
    
    if not found_existing:
         _log(f"[AI] Model not found locally. Will download...")

    # Always try CUDA first for GPU acceleration
    _log(f"[AI] Loading model '{model_size}'...")
    try:
        _cached_model = WhisperModel(
            model_size,
            device="cuda",
            compute_type=compute_type,
            download_root=selected_root,
            local_files_only=False
        )
        _log(f"[AI] >>> MODEL LOADED ON GPU (CUDA) <<<")
        _log(f"[AI] Device: NVIDIA RTX - Fast mode enabled!")
        _cached_model_size = model_size
        return _cached_model
        
    except Exception as cuda_error:
        error_msg = str(cuda_error).lower()
        
        # CUDA failed - try CPU fallback
        _log(f"[AI] GPU unavailable, using CPU mode (slower)")
        
        try:
            _cached_model = WhisperModel(
                model_size,
                device="cpu",
                compute_type="int8",
                download_root=selected_root,
                local_files_only=False
            )
            _log(f"[AI] >>> MODEL LOADED ON CPU <<<")
            _log(f"[AI] Warning: CPU mode is slower!")
            _cached_model_size = model_size
            return _cached_model
            
        except Exception as cpu_error:
            _log(f"[ERROR] Both GPU and CPU failed!")
            raise RuntimeError(f"Model Load Failed: GPU={cuda_error}, CPU={cpu_error}")


def transcribe_audio(
    audio_path: str,
    progress_callback: Optional[Callable[[str], None]] = None,
    model_size: str = "medium",
    log_callback: Optional[Callable[[str], None]] = None
) -> List[dict]:
    """
    Transcribe audio using Faster-Whisper.
    Returns list of words with timestamps.
    
    Args:
        audio_path: Path to audio file
        progress_callback: Optional callback for progress updates
        model_size: "small", "medium", or "large-v3-turbo"
        log_callback: Optional callback for log messages (to app log area)
    """
    if progress_callback:
        progress_callback(f"Loading Whisper ({model_size})...")
    
    model = get_whisper_model(model_size, log_callback=log_callback)
    
    if progress_callback:
        progress_callback("Transcribing...")
    
    # Try transcribing with VAD enabled (default)
    try:
        segments, info = model.transcribe(
            audio_path,
            language="vi",
            word_timestamps=True,
            vad_filter=True,
            beam_size=3 if "large" in model_size else 2
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
                beam_size=3 if "large" in model_size else 2
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
