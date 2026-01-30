# -*- coding: utf-8 -*-
"""
Voice Tools V3 - Audio Processor
V2 Logic + Smart Mode with script alignment
"""

import random
from typing import List, Tuple, Optional, Callable
from pydub import AudioSegment
from pydub.silence import detect_silence

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    FRAME_RATE, FRAME_MS, MIN_SILENCE_FRAMES, PARA_CUT_MS,
    PHRASE_MIN_MS, PHRASE_MAX_MS,
    HEAD_MS_LONG, TAIL_MS_LONG, HEAD_MS_SHORT, TAIL_MS_SHORT
)


# Type aliases
SilenceRange = Tuple[int, int]
ProgressCallback = Callable[[int, str], None]


def process_audio_fast(
    input_path: str,
    output_path: str,
    silence_thresh: int = -45,
    output_format: str = "mp3",
    progress_callback: Optional[ProgressCallback] = None,
    cancel_flag: Optional[Callable[[], bool]] = None
) -> AudioSegment:
    """
    Fast Mode: V2 frame-based silence processing.
    No transcription needed, purely audio-based.
    """
    if progress_callback:
        progress_callback(0, "Loading audio...")
    
    audio = AudioSegment.from_file(input_path)
    
    if cancel_flag and cancel_flag():
        raise InterruptedError("Cancelled by user")
    
    if progress_callback:
        progress_callback(5, "Detecting silence...")
    
    min_silence_len = FRAME_MS * MIN_SILENCE_FRAMES
    silence_ranges = [
        (int(s), int(e)) for s, e in detect_silence(
            audio_segment=audio,
            min_silence_len=min_silence_len,
            silence_thresh=silence_thresh,
            seek_step=1
        )
    ]
    
    if progress_callback:
        progress_callback(10, f"Found {len(silence_ranges)} silence ranges")
    
    result = AudioSegment.empty()
    last_end = 0
    total = len(silence_ranges)
    
    for i, (start, end) in enumerate(silence_ranges):
        if cancel_flag and cancel_flag():
            raise InterruptedError("Cancelled by user")
        
        silence_len = end - start
        frame_len = silence_len // FRAME_MS
        
        if start > last_end:
            result += audio[last_end:start]
        
        result += _apply_v2_logic(audio, start, end, frame_len, silence_len)
        last_end = end
        
        if progress_callback and total > 0:
            percent = 10 + int((i + 1) / total * 85)
            progress_callback(percent, f"Processing {i+1}/{total}...")
    
    if last_end < len(audio):
        result += audio[last_end:]
    
    if progress_callback:
        progress_callback(98, "Exporting...")
    
    result.export(out_f=output_path, format=output_format)
    
    if progress_callback:
        progress_callback(100, "Done!")
    
    return result


# Frame constants for hybrid logic (30fps)
FRAME_MS_CONST = 33  # ~33ms per frame at 30fps
END_SENTENCE_FRAMES = 24  # 800ms for end of sentence
MID_SENTENCE_MIN_FRAMES = 7  # 233ms min for mid-sentence
MID_SENTENCE_MAX_FRAMES = 9  # 300ms max for mid-sentence


def get_punctuation_config(punct: str) -> dict:
    """
    Get punctuation configuration for hybrid logic.
    Returns: {'type': 'end'|'mid'|'none', 'max_frames': int, 'min_frames': int}
    """
    if not punct:
        return {'type': 'none', 'max_frames': None, 'min_frames': None}
    
    # End of sentence: . ? ! ...
    if punct in '.!?' or punct == '...':
        return {
            'type': 'end',
            'max_frames': END_SENTENCE_FRAMES,  # 24 frames = 800ms
            'min_frames': END_SENTENCE_FRAMES
        }
    
    # Mid-sentence: , : ;
    if punct in ',:;':
        return {
            'type': 'mid',
            'max_frames': MID_SENTENCE_MAX_FRAMES,  # 9 frames = 300ms
            'min_frames': MID_SENTENCE_MIN_FRAMES   # 7 frames = 233ms
        }
    
    return {'type': 'none', 'max_frames': None, 'min_frames': None}


def get_pause_duration_for_punctuation(punct: str) -> Optional[int]:
    """
    Legacy function for backward compatibility.
    Returns target pause in ms based on punctuation.
    """
    config = get_punctuation_config(punct)
    if config['type'] == 'end':
        return config['max_frames'] * FRAME_MS_CONST  # 800ms
    elif config['type'] == 'mid':
        return random.randint(config['min_frames'], config['max_frames']) * FRAME_MS_CONST
    return None


def calculate_hybrid_pause(
    original_silence_ms: int,
    punct: str,
    frame_ms: int = FRAME_MS
) -> int:
    """
    Calculate pause duration using hybrid Frame + Punctuation logic.
    
    Logic:
    - End of sentence (.?!...): Cap at 24 frames (800ms)
    - Mid-sentence (,:;): Random 7-9 frames (233-300ms)
    - No punctuation (fallback): Frame-based logic
      - 0-7 frames: Keep as-is
      - 7.1-23 frames: Random to 7-9 frames
      - 24+ frames: Cap at 24 frames
    """
    frame_len = original_silence_ms // frame_ms
    config = get_punctuation_config(punct)
    
    if config['type'] == 'end':
        # End of sentence: Cap at 24 frames max
        if frame_len > END_SENTENCE_FRAMES:
            return END_SENTENCE_FRAMES * frame_ms
        elif frame_len >= MID_SENTENCE_MIN_FRAMES:
            return original_silence_ms  # Keep natural if reasonable
        else:
            return original_silence_ms  # Keep short pauses
            
    elif config['type'] == 'mid':
        # Mid-sentence: Cap at 7-9 frames
        if frame_len > MID_SENTENCE_MAX_FRAMES:
            target_frames = random.randint(MID_SENTENCE_MIN_FRAMES, MID_SENTENCE_MAX_FRAMES)
            return target_frames * frame_ms
        elif frame_len <= MID_SENTENCE_MIN_FRAMES:
            return original_silence_ms  # Keep short pauses
        else:
            return original_silence_ms  # Already in range
            
    else:
        # Fallback: Pure frame-based logic
        if frame_len <= 7:
            return original_silence_ms  # Keep as-is
        elif frame_len <= 23:
            target_frames = random.randint(MID_SENTENCE_MIN_FRAMES, MID_SENTENCE_MAX_FRAMES)
            return target_frames * frame_ms
        else:
            return END_SENTENCE_FRAMES * frame_ms  # Cap at 24 frames


def process_audio_smart(
    input_path: str,
    output_path: str,
    script: str,
    silence_thresh: int = -45,
    output_format: str = "mp3",
    progress_callback: Optional[ProgressCallback] = None,
    cancel_flag: Optional[Callable[[], bool]] = None,
    log_callback: Optional[Callable[[str], None]] = None,
    model_size: str = "medium"
) -> AudioSegment:
    """
    V5 Smart Mode: Silence-First Approach.
    
    Flow:
    1. Detect all physical silences in audio
    2. Transcribe audio to get word timestamps
    3. Align words with script to get punctuation
    4. For EACH SILENCE:
       - Find the word that ends just before this silence
       - Get punctuation of that word from script
       - Apply hybrid pause duration (punctuation-aware)
    5. Rebuild audio with adjusted silences
    
    Args:
        model_size: "small" (4x faster), "medium" (2x faster), "large-v3" (best accuracy)
    """
    from .transcriber import transcribe_audio
    from .aligner import align_transcript_with_script
    
    # Helper to log to both console and GUI
    def _log(msg):
        print(msg)
        if log_callback:
            log_callback(msg)

    if progress_callback: progress_callback(0, "Loading audio...")
    audio = AudioSegment.from_file(input_path)
    if cancel_flag and cancel_flag(): raise InterruptedError()
    
    # Step 1: Detect ALL physical silences
    if progress_callback: progress_callback(5, "Detecting silences...")
    
    min_silence_len = 100  # Detect pauses > 100ms
    silence_ranges = detect_silence(
        audio,
        min_silence_len=min_silence_len,
        silence_thresh=silence_thresh,
        seek_step=1
    )
    
    # Convert to list of silence dicts
    silences = []
    for s, e in silence_ranges:
        silences.append({
            'start': s,
            'end': e,
            'len': e - s,
            'punct': '',  # Will be filled later
            'target_len': None  # Target duration after processing
        })
    
    _log(f"[SMART] Found {len(silences)} silences in audio")
    if progress_callback: progress_callback(10, f"Found {len(silences)} silences")
    
    # Step 2: Transcribe audio
    if progress_callback: progress_callback(15, "Transcribing...")
    
    def prog_wrapper(msg):
        if progress_callback: progress_callback(25, msg)
    
    transcript_words = transcribe_audio(input_path, prog_wrapper, model_size=model_size)
    if cancel_flag and cancel_flag(): raise InterruptedError()
    _log(f"[SMART] Transcribed {len(transcript_words)} words")
    
    # Step 3: Align with script to get punctuation
    if progress_callback: progress_callback(40, "Aligning with script...")
    aligned_words = align_transcript_with_script(transcript_words, script)
    
    # Step 4: Word-First approach - find silences for words with punctuation
    if progress_callback: progress_callback(50, "Mapping words to silences...")
    
    # Create edit points based on WORDS with punctuation
    edit_points = []  # List of {word_end, punct, silence_info, target_pause}
    
    MICRO_SILENCE_THRESHOLD = 30  # Detect silences as short as 30ms for end-of-sentence
    
    for w in aligned_words:
        punct = w.punctuation_after
        if not punct:
            continue  # Skip words without punctuation
            
        word_end = w.end_ms
        punct_config = get_punctuation_config(punct)
        
        # Find ANY silence that starts near this word's end
        # For end-of-sentence: accept even micro-silences
        # For mid-sentence: need longer silence
        
        best_silence = None
        best_dist = float('inf')
        search_window = 400  # Search within 400ms after word end
        
        for sil in silences:
            if sil.get('used'):
                continue
            
            dist = sil['start'] - word_end
            
            # Silence must start AFTER word end (allow small overlap for timing drift)
            if -100 <= dist <= search_window:
                if abs(dist) < abs(best_dist):
                    best_dist = dist
                    best_silence = sil
        
        if best_silence:
            # Found a silence after this word
            best_silence['used'] = True
            
            if punct_config['type'] == 'end':
                # End of sentence: ALWAYS extend to target, even if silence is tiny
                target_pause = END_SENTENCE_FRAMES * FRAME_MS  # 24 frames = ~800ms
                _log(f"✓ '{w.text}' + '{punct}' (end): {best_silence['len']}ms → {target_pause}ms")
                
            elif punct_config['type'] == 'mid':
                # Mid-sentence: Only adjust if silence is already noticeable (>100ms)
                if best_silence['len'] >= 100:
                    target_pause = calculate_hybrid_pause(best_silence['len'], punct, FRAME_MS)
                    _log(f"✓ '{w.text}' + '{punct}' (mid): {best_silence['len']}ms → {target_pause}ms")
                else:
                    # Keep original short pause for mid-sentence
                    target_pause = best_silence['len']
            else:
                target_pause = calculate_hybrid_pause(best_silence['len'], '', FRAME_MS)
            
            edit_points.append({
                'word_end': word_end,
                'word': w.text,
                'punct': punct,
                'silence_start': best_silence['start'],
                'silence_end': best_silence['end'],
                'original_len': best_silence['len'],
                'target_len': target_pause
            })
        else:
            # No silence found - only log for end-of-sentence (missed opportunities)
            if punct_config['type'] == 'end':
                _log(f"⚠ '{w.text}' + '{punct}': No silence found (speaker continued)")
    
    _log(f"[SMART] Found {len(edit_points)} edit points from {len(aligned_words)} words")
    
    # Step 5: Rebuild audio with adjusted silences

    if progress_callback: progress_callback(70, "Rebuilding audio...")
    
    # Sort edit points by time
    edit_points.sort(key=lambda x: x['silence_start'])
    
    result = AudioSegment.empty()
    cursor = 0  # Position in original audio
    
    for i, ep in enumerate(edit_points):
        if cancel_flag and cancel_flag(): raise InterruptedError()
        
        # Add audio before this edit point's silence
        if ep['silence_start'] > cursor:
            chunk = audio[cursor:ep['silence_start']]
            result += chunk
        
        # Add adjusted silence
        target_len = ep['target_len']
        original_len = ep['original_len']
        
        if target_len > 0:
            if original_len > 60:
                # Has some original silence - preserve head/tail
                head_preserve = min(30, original_len // 2)
                tail_preserve = min(30, original_len // 2)
                
                result += audio[ep['silence_start']:ep['silence_start'] + head_preserve]
                
                mid_silence = max(0, target_len - head_preserve - tail_preserve)
                if mid_silence > 0:
                    result += AudioSegment.silent(duration=mid_silence)
                
                result += audio[ep['silence_end'] - tail_preserve:ep['silence_end']]
            else:
                # Very short original silence - keep original + add extra
                result += audio[ep['silence_start']:ep['silence_end']]
                extra = max(0, target_len - original_len)
                if extra > 0:
                    result += AudioSegment.silent(duration=extra)
        
        cursor = ep['silence_end']
        
        if progress_callback and len(edit_points) > 0:
            percent = 70 + int((i + 1) / len(edit_points) * 25)
            progress_callback(percent, f"Processing {i+1}/{len(edit_points)}...")
    
    # Add remaining audio after last edit point
    if cursor < len(audio):
        result += audio[cursor:]
    
    # Trim trailing silence (keep max 500ms at end)
    tail_check = result[-5000:] if len(result) > 5000 else result
    tail_silences = detect_silence(tail_check, min_silence_len=100, silence_thresh=silence_thresh)
    if tail_silences:
        last_sil = tail_silences[-1]
        chunk_len = min(5000, len(result))
        if last_sil[1] >= chunk_len - 50:  # Silence reaches near end
            sil_dur = last_sil[1] - last_sil[0]
            if sil_dur > 500:
                trim_amount = sil_dur - 500
                result = result[:-trim_amount]
                _log(f"✂ Trimmed {trim_amount}ms trailing silence")
    
    # Export
    if progress_callback: progress_callback(98, "Exporting...")
    result.export(out_f=output_path, format=output_format)
    if progress_callback: progress_callback(100, "Done!")
    
    saved_ms = len(audio) - len(result)
    _log(f"✅ Output: {len(result)}ms (delta: {saved_ms}ms)")
    return result





def _clean_edit_plan(plan: List[dict]) -> List[dict]:
    """
    Sorts and removes overlaps from edit plan.
    Ensures that time flows forward only.
    """
    if not plan: return []
    
    # 1. Sort by play_end time
    plan.sort(key=lambda x: x['play_end'])
    
    final_plan = []
    last_resume = 0
    
    for item in plan:
        play_end = item['play_end']
        resume_at = item['resume_at']
        
        # If this edit tries to end BEFORE the last resume, it's a retrograde. Skip it or Trim it.
        # Case: Overlap
        if play_end < last_resume:
            # If the resume point is also before last_resume, this entire edit is in the past. Skip.
            if resume_at <= last_resume:
                continue
            
            # If it extends beyond, we technically could use the tail, but that implies
            # we failed to match silence properly. Safer to SKIP to avoid stutter.
            # print(f"Skipping overlap: {play_end} < {last_resume}")
            continue
            
        final_plan.append(item)
        last_resume = resume_at
        
    return final_plan


def _apply_v2_logic(
    audio: AudioSegment,
    start: int,
    end: int,
    frame_len: int,
    silence_len: int
) -> AudioSegment:
    """
    V2 Logic for fast mode (no script, pure frame-based).
    
    Logic (30fps):
    - 0-7 frames (0-233ms): Keep as-is
    - 8-23 frames (234-767ms): Reduce to 7-9 frames (233-300ms)
    - 24+ frames (800ms+): Cap at 24 frames (800ms)
    """
    result = AudioSegment.empty()
    
    if frame_len <= MID_SENTENCE_MIN_FRAMES:  # 0-7 frames
        result += audio[start:end]
        
    elif frame_len < END_SENTENCE_FRAMES:  # 8-23 frames
        target_frames = random.randint(MID_SENTENCE_MIN_FRAMES, MID_SENTENCE_MAX_FRAMES)
        target_ms = FRAME_MS * target_frames
        
        head = min(HEAD_MS_SHORT, silence_len)
        tail = min(TAIL_MS_SHORT, max(0, silence_len - head))
        
        start_head = min(end, start + head)
        end_tail = max(start, end - tail)
        
        used_head = start_head - start
        used_tail = end - end_tail
        mid_sil = max(0, target_ms - used_head - used_tail)
        
        result += audio[start:start_head]
        if mid_sil > 0:
            result += AudioSegment.silent(duration=mid_sil)
        result += audio[end_tail:end]
        
    elif frame_len == END_SENTENCE_FRAMES:  # Exactly 24 frames
        result += audio[start:end]
        
    else:
        target_ms = PARA_CUT_MS
        
        head = HEAD_MS_LONG
        tail = TAIL_MS_LONG
        
        start_head = min(end, start + head)
        end_tail = max(start, end - tail)
        
        used_head = start_head - start
        used_tail = end - end_tail
        mid_sil = max(0, target_ms - used_head - used_tail)
        
        result += audio[start:start_head]
        if mid_sil > 0:
            result += AudioSegment.silent(duration=mid_sil)
        result += audio[end_tail:end]
    
    return result


def get_audio_info(audio_path: str) -> dict:
    """Get basic audio file information."""
    audio = AudioSegment.from_file(audio_path)
    return {
        "duration_ms": len(audio),
        "duration_sec": len(audio) / 1000,
        "channels": audio.channels,
        "sample_rate": audio.frame_rate
    }
