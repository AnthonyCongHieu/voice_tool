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


# Frame constants for V3 Logic (30fps)
FRAME_MS = 33  # ~33ms per frame at 30fps

# END punctuation (. ! ? ...) → luôn 24 frames = 800ms
END_SENTENCE_FRAMES = 24
END_EXTEND_THRESHOLD = 22  # >=22f → extend lên 24f

# MID punctuation (, : ;) → 6-7.5 frames = 200-250ms
MID_SENTENCE_MIN_FRAMES = 6   # 200ms
MID_SENTENCE_MAX_FRAMES = 8   # ~250ms (7.5 rounded up)
MID_SKIP_THRESHOLD = 6        # <=6f → keep as-is

# NO punctuation (TTS error detection) → word-gap based
# Chỉ xử lý gap >= 300ms (silence không mong muốn)
TTS_ERROR_THRESHOLD_MS = 300  # Gap >= 300ms = TTS error (thay vì 100ms)
TTS_ERROR_TARGET_MS = 100     # Reduce to 100ms (3 frames) - đủ tự nhiên
TTS_ERROR_HEAD_MS = 50        # Giữ 50ms đầu để voice fade out
TTS_ERROR_TAIL_MS = 50        # Giữ 50ms cuối để voice fade in

# Silence Injection constants
INJECT_BUFFER_MS = 50      # Buffer sau word.end_ms khi inject (tránh cắt vào từ)
CROSSFADE_MS = 15          # Fade để tránh click khi cắt
DEFAULT_SILENCE_THRESH = -37  # Giảm từ -45 để detect silence có tạp âm


def get_punctuation_config(punct: str) -> dict:
    """
    Get punctuation configuration for V3 Logic.
    Returns: {'type': 'end'|'mid'|'none', 'target_ms': int, 'min_ms': int}
    """
    if not punct:
        return {'type': 'none', 'target_ms': None, 'min_ms': None}
    
    # End of sentence: . ? ! ... → luôn 24 frames = 800ms
    if punct in '.!?' or punct == '...':
        return {
            'type': 'end',
            'target_ms': END_SENTENCE_FRAMES * FRAME_MS,  # 800ms
            'min_ms': END_EXTEND_THRESHOLD * FRAME_MS     # 733ms threshold
        }
    
    # Mid-sentence: , : ; → 6-8 frames = 200-266ms
    if punct in ',:;':
        return {
            'type': 'mid',
            'target_ms': random.randint(MID_SENTENCE_MIN_FRAMES, MID_SENTENCE_MAX_FRAMES) * FRAME_MS,
            'min_ms': MID_SKIP_THRESHOLD * FRAME_MS  # 200ms - skip nếu đã ngắn
        }
    
    return {'type': 'none', 'target_ms': None, 'min_ms': None}


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
    silence_thresh: int = DEFAULT_SILENCE_THRESH,  # -37dB để detect silence có tạp âm
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
        model_size: "small" (4x faster), "medium" (2x faster), "large-v3-turbo" (best, fastest)
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
    
    min_silence_len = 60  # Giảm từ 100ms để detect pause ngắn hơn
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
    
    transcript_words = transcribe_audio(input_path, prog_wrapper, model_size=model_size, log_callback=_log)
    if cancel_flag and cancel_flag(): raise InterruptedError()
    _log(f"[SMART] Transcribed {len(transcript_words)} words")
    
    # Step 3: Align with script to get punctuation
    if progress_callback: progress_callback(40, "Aligning with script...")
    aligned_words, alignment_report = align_transcript_with_script(transcript_words, script)
    
    # Step 4: Word-First approach - find silences for words with punctuation
    if progress_callback: progress_callback(50, "Mapping words to silences...")
    
    # Create edit points based on WORDS with punctuation
    edit_points = []  # List of {word_end, punct, silence_info, target_pause}
    
    MICRO_SILENCE_THRESHOLD = 30  # Detect silences as short as 30ms for end-of-sentence
    SAFE_INJECTION_GAP_MS = 250   # Nếu gap < 250ms, coi là misalignment -> dùng mid pause
    
    for i, w in enumerate(aligned_words):
        punct = w.punctuation_after
        if not punct:
            continue  # Skip words without punctuation
            
        word_end = w.end_ms
        punct_config = get_punctuation_config(punct)
        
        # Determine next word start time for gap checking
        next_word_start = float('inf')
        if i < len(aligned_words) - 1:
            next_word_start = aligned_words[i+1].start_ms
        
        gap_to_next = next_word_start - word_end
        
        # Find ANY silence that starts near this word's end
        best_silence = None
        best_dist = float('inf')
        search_window = 600  # V3: Expanded to find smaller pauses (was 400ms)
        
        for sil in silences:
            if sil.get('used'):
                continue
            
            dist = sil['start'] - word_end
            
            # Silence must start AFTER word end (allow small overlap for timing drift)
            # V3: Allow more overlap to catch small pauses right at word boundary
            if -200 <= dist <= search_window:
                if abs(dist) < abs(best_dist):
                    best_dist = dist
                    best_silence = sil
        
        if best_silence:
            # Found a silence after this word
            best_silence['used'] = True
            
            # SAFETY CLAMP: Protect word tail (V2: increased buffer)
            # Don't cut more than 50ms into the word time, even if silence starts earlier
            safe_silence_start = max(best_silence['start'], word_end - 50)
            
            if punct_config['type'] == 'end':
                # V4: Frame-based logic - Cuối câu
                # ≥20 frames → 24 frames (800ms)
                # <20 frames → giữ nguyên
                silence_frames = best_silence['len'] / FRAME_MS
                
                if silence_frames >= 20:
                    target_pause = 24 * FRAME_MS  # 800ms
                    _log(f"✓ '{w.text}' + '{punct}' (cuối câu): {silence_frames:.1f}f (≥20) → 24f = {target_pause}ms")
                else:
                    # < 20 frames → giữ nguyên
                    target_pause = best_silence['len']
                    _log(f"✓ '{w.text}' + '{punct}' (cuối câu): {silence_frames:.1f}f (<20) → GIỮ NGUYÊN {target_pause}ms")
                
            elif punct_config['type'] == 'mid':
                # V4: Frame-based logic - Giữa câu
                # ≤6 frames → giữ nguyên
                # 7-19 frames → random 6-8 frames
                # ≥20 frames → 24 frames (chuẩn hóa lỗi TTS)
                silence_frames = best_silence['len'] / FRAME_MS
                
                if silence_frames <= 6:
                    # Giữ nguyên pause ngắn
                    target_pause = best_silence['len']
                    _log(f"✓ '{w.text}' + '{punct}' (giữa câu): {silence_frames:.1f}f (≤6) → GIỮ NGUYÊN {target_pause}ms")
                elif silence_frames < 20:
                    # Random 6-8 frames
                    target_frames = random.randint(6, 8)
                    target_pause = target_frames * FRAME_MS
                    _log(f"✓ '{w.text}' + '{punct}' (giữa câu): {silence_frames:.1f}f (7-19) → RANDOM {target_frames}f = {target_pause}ms")
                else:
                    # ≥20 frames → chuẩn hóa về 24f (đây là lỗi TTS - pause quá dài sau dấu phẩy)
                    target_pause = 24 * FRAME_MS  # 800ms
                    _log(f"⚠ '{w.text}' + '{punct}' (giữa câu): {silence_frames:.1f}f (≥20) → CHUẨN HÓA 24f = {target_pause}ms (lỗi TTS)")
            else:
                target_pause = calculate_hybrid_pause(best_silence['len'], '', FRAME_MS)
            
            edit_points.append({
                'word_end': word_end,
                'word': w.text,
                'punct': punct,
                'silence_start': safe_silence_start, # Used safe start
                'silence_end': best_silence['end'],
                'original_len': best_silence['len'],
                'target_len': target_pause
            })
        else:
            # V3: NO INJECTION - If no natural silence found, SKIP
            # User confirmed voice ALWAYS has natural pauses
            # If we can't find it, expand search or skip, DON'T create artificial pause
            _log(f"⚠ '{w.text}' + '{punct}': No silence found in search window → SKIPPING (no artificial pause)")
    
    # Step 4.5: Detect TTS ERRORS using word-gap analysis
    # Logic: Nếu gap giữa 2 từ >= 300ms VÀ từ trước KHÔNG có punct → TTS error
    # → Reduce gap to 100ms (3 frames) với buffer head/tail 50ms
    
    tts_error_count = 0
    for i in range(len(aligned_words) - 1):
        current_word = aligned_words[i]
        next_word = aligned_words[i + 1]
        
        # Skip nếu current word có punctuation (đó là pause hợp lệ)
        if current_word.punctuation_after:
            continue
        
        # Tính gap giữa 2 từ
        gap_ms = next_word.start_ms - current_word.end_ms
        
        # Chỉ xử lý gap >= 300ms (TTS error)
        if gap_ms >= TTS_ERROR_THRESHOLD_MS:
            # Tìm silence tương ứng trong danh sách silences
            matching_silence = None
            for sil in silences:
                if sil.get('used'):
                    continue
                # Silence nằm trong khoảng gap
                if sil['start'] >= current_word.end_ms - 50 and sil['end'] <= next_word.start_ms + 50:
                    matching_silence = sil
                    sil['used'] = True
                    break
            
            if matching_silence:
                # Tính target: giữ head + tail buffer, giảm phần giữa
                original_len = matching_silence['len']
                # Target = 100ms (3 frames) hoặc giữ nguyên nếu đã <= 100ms
                target_len = min(original_len, TTS_ERROR_TARGET_MS)
                
                edit_points.append({
                    'word_end': current_word.end_ms,
                    'word': current_word.text,
                    'next_word': next_word.text,
                    'punct': '',
                    'silence_start': matching_silence['start'] + TTS_ERROR_HEAD_MS,  # Keep 50ms head
                    'silence_end': matching_silence['end'] - TTS_ERROR_TAIL_MS,      # Keep 50ms tail
                    'original_len': original_len,
                    'target_len': target_len,
                    'tts_error': True,
                    'gap_ms': gap_ms
                })
                
                tts_error_count += 1
                _log(f"[TTS-FIX] '{current_word.text}' → '{next_word.text}': gap {gap_ms}ms --> {target_len}ms")
    
    punct_count = len([ep for ep in edit_points if not ep.get('tts_error')])
    _log(f"[SMART] Found {punct_count} punct edits + {tts_error_count} TTS errors fixed")
    
    # Step 4.8: Filter Tiny Voice Chunks (tránh voice 'island' < 600ms)
    # Sort edit points by time first
    edit_points.sort(key=lambda x: x['silence_start'])
    
    MIN_VOICE_CHUNK_MS = 700  # V2: Balanced filter (700ms ~ 2 từ, less aggressive)
    final_edit_points = []
    last_silence_end = 0
    
    removed_count = 0
    
    for ep in edit_points:
        # Calculate voice duration BEFORE this silence
        voice_len = ep['silence_start'] - last_silence_end
        
        # Chỉ check nếu đây không phải là edit point đầu tiên (voice_len > 0)
        # Nếu voice_chunk quá ngắn (< 600ms ~ 1-2 từ), bỏ qua edit point này (để nối liền voice)
        if 0 < voice_len < MIN_VOICE_CHUNK_MS:
            _log(f"⚡ Removing edit point @ {ep['silence_start']}ms (Voice chunk {voice_len}ms too short)")
            removed_count += 1
            # Không update last_silence_end, coi như silence này chưa từng tồn tại
            # Voice sẽ tiếp tục đến silence tiếp theo
            continue
            
        final_edit_points.append(ep)
        # Update last_silence_end for next iteration
        # Note: logic rebuild dùng target_len, nhưng ở đây ta đang check trên source timeline
        last_silence_end = ep['silence_end']
    
    if removed_count > 0:
        _log(f"[FILTER] Removed {removed_count} tiny voice interrupts")
        edit_points = final_edit_points

    # Step 5: Rebuild audio with adjusted silences

    if progress_callback: progress_callback(70, "Rebuilding audio...")
    
    # Sort edit points by time (again, to be safe)
    edit_points.sort(key=lambda x: x['silence_start'])
    
    result = AudioSegment.empty()
    cursor = 0  # Position in original audio
    previous_was_inject = False  # Track nếu edit point trước là inject
    
    for i, ep in enumerate(edit_points):
        if cancel_flag and cancel_flag(): raise InterruptedError()
        
        # Add audio before this edit point's silence
        if ep['silence_start'] > cursor:
            chunk = audio[cursor:ep['silence_start']]
            
            # V2: NO CROSSFADE - causes "khựng khựng" clicking sound
            # Let natural audio flow without artificial fade
            
            result += chunk
        
        # Add adjusted silence
        target_len = ep['target_len']
        original_len = ep['original_len']
        is_inject = ep.get('inject_mode', False)
        is_no_punct = ep.get('no_punct_mode', False)
        
        if target_len > 0:
            if is_inject:
                # INJECT MODE: Không có silence gốc, cắt và chèn silence mới
                # Áp dụng crossfade để tránh click
                if len(result) > CROSSFADE_MS:
                    # Fade out cuối đoạn trước
                    result = result.fade_out(CROSSFADE_MS)
                
                # Chèn silence thuần túy
                result += AudioSegment.silent(duration=target_len)
                
                # Cursor giữ nguyên tại inject_point (silence_start = silence_end)
                # Audio tiếp theo sẽ được fade in
                
            elif is_no_punct:
                # NO PUNCT MODE: Silence thừa không có dấu câu → minimize
                # Giữ safe_head (30ms) để hết sóng + tiny gap
                safe_head = min(NO_PUNCT_SAFE_HEAD_MS, original_len)
                remaining_gap = max(0, target_len - safe_head)
                
                # Lấy phần đầu của silence gốc (để hết sóng)
                result += audio[ep['silence_start']:ep['silence_start'] + safe_head]
                
                # Thêm gap tối thiểu nếu cần
                if remaining_gap > 0:
                    result += AudioSegment.silent(duration=remaining_gap)
                
            elif original_len > 60:
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
        previous_was_inject = is_inject  # Track cho chunk tiếp theo
        
        if progress_callback and len(edit_points) > 0:
            percent = 70 + int((i + 1) / len(edit_points) * 25)
            progress_callback(percent, f"Processing {i+1}/{len(edit_points)}...")
    
    # Add remaining audio after last edit point
    if cursor < len(audio):
        remaining = audio[cursor:]
        # Fade in nếu edit point cuối là inject
        if previous_was_inject and len(remaining) > CROSSFADE_MS:
            remaining = remaining.fade_in(CROSSFADE_MS)
        result += remaining
    
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
    
    # === MISMATCH SUMMARY ===
    _log("")
    _log("═══════════════════════════════════════")
    _log("📊 ALIGNMENT REPORT")
    _log("═══════════════════════════════════════")
    _log(f"📝 Script: {alignment_report['total_script_words']} từ")
    _log(f"🎤 Whisper: {alignment_report['total_transcript_words']} từ")
    _log(f"✓ Matched: {alignment_report['matched_count']} ({alignment_report['match_rate']:.1f}%)")
    _log(f"✗ Mismatch: {alignment_report['mismatch_count']} từ")
    _log(f"🔣 Punctuation found: {alignment_report['punct_found']}")
    
    if alignment_report['mismatch_count'] > 0:
        _log("")
        _log("⚠ CÁC TỪ KHÔNG MATCH (tối đa 10):")
        for m in alignment_report['mismatched_words']:
            _log(f"  #{m['position']}: '{m['transcript']}' ≠ '{m['expected']}' @ {m['time_ms']}ms")
        
        if alignment_report['match_rate'] < 80:
            _log("")
            _log("⚠ CẢNH BÁO: Match rate < 80%! Kết quả có thể không chính xác.")
            _log("   Kiểm tra lại script có khớp với audio không.")
    
    _log("═══════════════════════════════════════")
    
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
