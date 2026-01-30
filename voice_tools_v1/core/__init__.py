# -*- coding: utf-8 -*-
"""
Voice Tools V3 - Core Module
Supports Fast Mode and Smart Script Mode
"""

from .processor import process_audio_fast, process_audio_smart, get_audio_info
from .transcriber import transcribe_audio
from .aligner import align_transcript_with_script

__all__ = ["process_audio_fast", "process_audio_smart", "get_audio_info", "transcribe_audio", "align_transcript_with_script"]
