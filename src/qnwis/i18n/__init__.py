"""
Internationalization (i18n) module for QNWIS (M1).

Provides Arabic language support with:
- UI translations (Arabic/English)
- RTL (Right-to-Left) support
- Bilingual output capability
- Language detection

Ministry-grade Arabic localization for Qatar's Ministry of Labour.
"""

from .translator import Translator, get_translator, translate
from .arabic import is_arabic, detect_language, format_arabic_text

__all__ = [
    "Translator",
    "get_translator",
    "translate",
    "is_arabic",
    "detect_language",
    "format_arabic_text"
]
