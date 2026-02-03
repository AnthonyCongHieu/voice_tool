# -*- coding: utf-8 -*-
"""
Voice Tools V3 - Configuration
Simple frame-based silence processing
"""

# === FRAME CONFIGURATION (30fps standard) ===
FRAME_RATE = 30
FRAME_MS = 1000 // FRAME_RATE  # ~33ms per frame

# === SILENCE PROCESSING THRESHOLDS ===
# Default dB threshold for silence detection (giảm từ -45 để detect silence có tạp âm)
DEFAULT_SILENCE_THRESH = -37

# Minimum silence length to detect (in frames)
MIN_SILENCE_FRAMES = 4  # ~133ms

# === FRAME LOGIC RULES ===
# V2 Logic:
# - 0-10 frames: Keep as-is
# - 11-20 frames: Reduce to 8-10 frames random
# - 21-24 frames: Keep as-is
# - >24 frames: Cut to 24 frames (800ms)

PARA_CUT_MS = FRAME_MS * 24        # 800ms - paragraph pause
PHRASE_MIN_MS = FRAME_MS * 8       # 266ms - minimum mid-sentence
PHRASE_MAX_MS = FRAME_MS * 10      # 333ms - maximum mid-sentence

# === OUTPUT SETTINGS ===
OUTPUT_FORMATS = ["mp3", "wav"]

# === HEAD/TAIL PRESERVATION ===
# Keep natural audio at start/end of silence for smoother cuts
HEAD_MS_LONG = 200   # For paragraph pauses
TAIL_MS_LONG = 100
HEAD_MS_SHORT = 100  # For phrase pauses
TAIL_MS_SHORT = 50
