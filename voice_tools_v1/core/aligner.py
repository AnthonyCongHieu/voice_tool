# -*- coding: utf-8 -*-
"""
Voice Tools V3 - Script Aligner
Aligns transcription with user script to detect punctuation
"""

import re
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class AlignedWord:
    """Word with timing and punctuation info"""
    text: str
    start_ms: int
    end_ms: int
    punctuation_after: str = ""  # "." "," "?" "!" "..." or ""


def normalize_text(text: str) -> str:
    """Normalize text for comparison"""
    # Remove punctuation and lowercase
    text = re.sub(r'[^\w\s]', '', text)
    return text.lower().strip()


def extract_words_with_punctuation(script: str) -> List[Tuple[str, str]]:
    """
    Extract words and their following punctuation from script.
    Returns: [(word, punctuation), ...]
    """
    # Pattern to match word + optional punctuation (including : and ;)
    pattern = r'(\w+)([.,!?;:…]+)?'
    matches = re.findall(pattern, script)
    
    result = []
    for word, punct in matches:
        # Normalize punctuation
        if '...' in punct or '…' in punct:
            punct = '...'
        elif punct:
            punct = punct[0]  # Take first punctuation char
        result.append((word.lower(), punct))
    
    # Debug: Print extracted words
    print(f"[ALIGNER] Extracted {len(result)} words from script")
    
    return result


def align_transcript_with_script(
    transcript_words: List[dict],  # [{text, start, end}, ...]
    script: str
) -> List[AlignedWord]:
    """
    Align transcribed words with script to get punctuation info.
    
    Args:
        transcript_words: Words from faster-whisper with timestamps
        script: User's script with punctuation
    
    Returns:
        List of AlignedWord with punctuation from script
    """
    # Extract words and punctuation from script
    script_words = extract_words_with_punctuation(script)
    
    aligned = []
    script_idx = 0
    matched_count = 0
    punct_count = 0
    
    for tw in transcript_words:
        word_text = normalize_text(tw.get('text', tw.get('word', '')))
        # Whisper uses seconds, we use milliseconds. Always convert.
        start_ms = int(tw.get('start', 0) * 1000)
        end_ms = int(tw.get('end', 0) * 1000)
        
        punct = ""
        
        # Try to find matching word in script
        if script_idx < len(script_words):
            script_word, script_punct = script_words[script_idx]
            
            # Fuzzy match (handle minor transcription errors)
            if word_text == script_word or _fuzzy_match(word_text, script_word):
                punct = script_punct
                script_idx += 1
                matched_count += 1
                if punct:
                    punct_count += 1
                    print(f"[ALIGN] '{word_text}' -> '{script_word}' + '{punct}' at {end_ms}ms")
            else:
                # Try next few words (in case of missed words)
                for lookahead in range(1, min(4, len(script_words) - script_idx)):
                    sw, sp = script_words[script_idx + lookahead]
                    if word_text == sw or _fuzzy_match(word_text, sw):
                        punct = sp
                        script_idx += lookahead + 1
                        matched_count += 1
                        if punct:
                            punct_count += 1
                            print(f"[ALIGN] '{word_text}' -> '{sw}' + '{punct}' (lookahead) at {end_ms}ms")
                        break
        
        aligned.append(AlignedWord(
            text=tw.get('text', tw.get('word', '')).strip(),
            start_ms=start_ms,
            end_ms=end_ms,
            punctuation_after=punct
        ))
    
    print(f"[ALIGNER] Matched {matched_count}/{len(transcript_words)} words, found {punct_count} punctuation marks")
    return aligned



# Vietnamese diacritic normalization map
VIETNAMESE_DIACRITICS = {
    'à': 'a', 'á': 'a', 'ả': 'a', 'ã': 'a', 'ạ': 'a',
    'ă': 'a', 'ằ': 'a', 'ắ': 'a', 'ẳ': 'a', 'ẵ': 'a', 'ặ': 'a',
    'â': 'a', 'ầ': 'a', 'ấ': 'a', 'ẩ': 'a', 'ẫ': 'a', 'ậ': 'a',
    'è': 'e', 'é': 'e', 'ẻ': 'e', 'ẽ': 'e', 'ẹ': 'e',
    'ê': 'e', 'ề': 'e', 'ế': 'e', 'ể': 'e', 'ễ': 'e', 'ệ': 'e',
    'ì': 'i', 'í': 'i', 'ỉ': 'i', 'ĩ': 'i', 'ị': 'i',
    'ò': 'o', 'ó': 'o', 'ỏ': 'o', 'õ': 'o', 'ọ': 'o',
    'ô': 'o', 'ồ': 'o', 'ố': 'o', 'ổ': 'o', 'ỗ': 'o', 'ộ': 'o',
    'ơ': 'o', 'ờ': 'o', 'ớ': 'o', 'ở': 'o', 'ỡ': 'o', 'ợ': 'o',
    'ù': 'u', 'ú': 'u', 'ủ': 'u', 'ũ': 'u', 'ụ': 'u',
    'ư': 'u', 'ừ': 'u', 'ứ': 'u', 'ử': 'u', 'ữ': 'u', 'ự': 'u',
    'ỳ': 'y', 'ý': 'y', 'ỷ': 'y', 'ỹ': 'y', 'ỵ': 'y',
    'đ': 'd',
}


def _normalize_vietnamese(text: str) -> str:
    """Remove Vietnamese diacritics for fuzzy comparison"""
    result = text.lower()
    for accented, base in VIETNAMESE_DIACRITICS.items():
        result = result.replace(accented, base)
    return result


def _fuzzy_match(word1: str, word2: str, threshold: float = 0.75) -> bool:
    """
    Vietnamese-aware fuzzy matching using Levenshtein distance.
    Handles diacritics and transcription errors from Whisper.
    """
    from difflib import SequenceMatcher
    
    if not word1 or not word2:
        return False
    
    # Exact match
    if word1 == word2:
        return True
    
    # Normalize Vietnamese diacritics
    n1 = _normalize_vietnamese(word1)
    n2 = _normalize_vietnamese(word2)
    
    # Match after normalization
    if n1 == n2:
        return True
    
    # One contains the other (for compound words)
    if n1 in n2 or n2 in n1:
        return True
    
    # Levenshtein ratio (more accurate than character overlap)
    ratio = SequenceMatcher(None, n1, n2).ratio()
    return ratio >= threshold


def align_segments_to_script(
    segments_text: List[str], # Text of each audio segment
    script: str
) -> List[str]:
    """
    Align list of segment texts with script to find trailing punctuation for each segment.
    Returns list of punctuation strings corresponding to each segment.
    """
    script_words = extract_words_with_punctuation(script)
    segment_punctuations = []
    
    script_idx = 0
    total_script_words = len(script_words)
    
    for seg_text in segments_text:
        # Extract words from segment text
        seg_words_raw = extract_words_with_punctuation(seg_text) # Re-use this to split words
        seg_words = [w[0] for w in seg_words_raw] # Just words
        
        if not seg_words:
            segment_punctuations.append("")
            continue
            
        # We care about the punctuation of the LAST word in the segment
        last_word_in_seg = seg_words[-1]
        
        # Search for this sequence of words in the script
        # Heuristic: Match distinct words to advance script_idx
        # Then find the punctuation of the last matched word
        
        matched_punct = ""
        
        # Try to match the segment words against script words starting at script_idx
        # We advance script_idx as we match
        
        current_match_idx = script_idx
        
        for w in seg_words:
            # Look ahead a bit to find the word (in case of transcription errors)
            found = False
            for lookahead in range(10): # Look ahead up to 10 words
                if current_match_idx + lookahead >= total_script_words:
                    break
                    
                sc_word, sc_punct = script_words[current_match_idx + lookahead]
                
                if w == sc_word or _fuzzy_match(w, sc_word):
                    # Found match
                    current_match_idx += lookahead
                    if w == last_word_in_seg or _fuzzy_match(w, last_word_in_seg):
                         # This is the last word, grab its punctuation
                         matched_punct = sc_punct
                    
                    current_match_idx += 1 # Advance past this word
                    found = True
                    break
            
            if not found:
                # Word not found in script, ignore it and continue
                pass
        
        # Update main script index for next segment
        script_idx = current_match_idx
        segment_punctuations.append(matched_punct)
        
    return segment_punctuations
