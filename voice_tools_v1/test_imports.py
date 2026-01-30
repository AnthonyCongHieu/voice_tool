# -*- coding: utf-8 -*-
# Test script for Hybrid Frame-Punctuation Logic
import sys
sys.path.insert(0, r'e:\tool edit\voice_tool\voice_tools_v1')

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

print("=" * 70)
print("HYBRID FRAME-PUNCTUATION LOGIC TEST")
print("=" * 70)

# Import
from core.processor import (
    get_punctuation_config, 
    calculate_hybrid_pause,
    get_pause_duration_for_punctuation,
    FRAME_MS, END_SENTENCE_FRAMES, MID_SENTENCE_MIN_FRAMES, MID_SENTENCE_MAX_FRAMES
)

print(f"\nConstants: FRAME_MS={FRAME_MS}, END={END_SENTENCE_FRAMES}f, MID_MIN={MID_SENTENCE_MIN_FRAMES}f, MID_MAX={MID_SENTENCE_MAX_FRAMES}f")

# Test 1: Punctuation Config
print("\n[TEST 1] Punctuation Configuration:")
test_puncts = ['.', '?', '!', '...', ',', ':', ';', '', 'x']
for p in test_puncts:
    config = get_punctuation_config(p)
    print(f"  '{p}' -> type={config['type']}, frames={config['min_frames']}-{config['max_frames']}")

# Test 2: Hybrid Pause Calculation
print("\n[TEST 2] Hybrid Pause Calculation (FRAME_MS=33):")

test_cases = [
    # (original_silence_ms, punct, expected_behavior)
    (100, '.', "End: keep short"),      # 3 frames - keep
    (300, '.', "End: keep natural"),    # 9 frames - keep  
    (1000, '.', "End: cap at 24f"),     # 30 frames - cap
    (100, ',', "Mid: keep short"),      # 3 frames - keep
    (500, ',', "Mid: reduce to 7-9f"),  # 15 frames - reduce
    (100, '', "Fallback: keep 0-7f"),   # 3 frames - keep
    (400, '', "Fallback: reduce"),      # 12 frames - reduce
    (1000, '', "Fallback: cap 24f"),    # 30 frames - cap
]

for orig_ms, punct, desc in test_cases:
    result = calculate_hybrid_pause(orig_ms, punct, FRAME_MS)
    orig_frames = orig_ms // FRAME_MS
    result_frames = result // FRAME_MS
    print(f"  {orig_ms}ms ({orig_frames}f) + '{punct}' -> {result}ms ({result_frames}f) | {desc}")

# Test 3: Legacy Function
print("\n[TEST 3] Legacy get_pause_duration_for_punctuation:")
for p in ['.', ',', '...', '', ':']:
    result = get_pause_duration_for_punctuation(p)
    print(f"  '{p}' -> {result}ms")

print("\n" + "=" * 70)
print("ALL TESTS COMPLETED")
print("=" * 70)
