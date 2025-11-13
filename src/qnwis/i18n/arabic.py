"""
Arabic language utilities for QNWIS (M1).

Provides Arabic text detection, formatting, and RTL support.
"""

import re
from typing import Tuple

# Arabic Unicode ranges
ARABIC_RANGES = [
    (0x0600, 0x06FF),  # Arabic
    (0x0750, 0x077F),  # Arabic Supplement
    (0x08A0, 0x08FF),  # Arabic Extended-A
    (0xFB50, 0xFDFF),  # Arabic Presentation Forms-A
    (0xFE70, 0xFEFF),  # Arabic Presentation Forms-B
]


def is_arabic(text: str) -> bool:
    """
    Check if text contains Arabic characters.
    
    Args:
        text: Text to check
        
    Returns:
        True if text contains Arabic, False otherwise
    """
    if not text:
        return False
    
    for char in text:
        code_point = ord(char)
        for start, end in ARABIC_RANGES:
            if start <= code_point <= end:
                return True
    
    return False


def detect_language(text: str) -> str:
    """
    Detect if text is primarily Arabic or English.
    
    Args:
        text: Text to analyze
        
    Returns:
        "ar" if Arabic, "en" otherwise
    """
    if not text:
        return "en"
    
    # Count Arabic vs non-Arabic characters
    arabic_count = 0
    total_chars = 0
    
    for char in text:
        if char.isalpha():
            total_chars += 1
            if is_arabic(char):
                arabic_count += 1
    
    if total_chars == 0:
        return "en"
    
    # If more than 30% Arabic, consider it Arabic text
    arabic_ratio = arabic_count / total_chars
    return "ar" if arabic_ratio > 0.3 else "en"


def format_arabic_text(text: str, add_rtl_markers: bool = True) -> str:
    """
    Format Arabic text for display with proper RTL markers.
    
    Args:
        text: Text to format
        add_rtl_markers: Whether to add RTL Unicode markers
        
    Returns:
        Formatted text
    """
    if not text or not is_arabic(text):
        return text
    
    if add_rtl_markers:
        # Add RTL marker at start
        rtl_mark = "\u200F"  # RIGHT-TO-LEFT MARK
        return f"{rtl_mark}{text}"
    
    return text


def create_bilingual_text(english: str, arabic: str, separator: str = " | ") -> str:
    """
    Create bilingual text display (English | Arabic).
    
    Args:
        english: English text
        arabic: Arabic text
        separator: Separator between languages
        
    Returns:
        Bilingual formatted text
    """
    formatted_arabic = format_arabic_text(arabic)
    return f"{english}{separator}{formatted_arabic}"


def get_text_direction_html(text: str) -> str:
    """
    Get HTML dir attribute value for text.
    
    Args:
        text: Text to check
        
    Returns:
        "rtl" or "ltr"
    """
    return "rtl" if detect_language(text) == "ar" else "ltr"
