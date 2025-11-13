"""
Translation system for QNWIS Arabic/English bilingual support (M1).
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Arabic translations for UI elements
TRANSLATIONS = {
    "en": {
        # Common UI elements
        "welcome": "Welcome to Qatar National Workforce Intelligence System",
        "ask_question": "Ask a question",
        "loading": "Analyzing...",
        "error_occurred": "An error occurred",
        "try_again": "Please try again",
        
        # Analysis sections
        "executive_summary": "Executive Summary",
        "key_metrics": "Key Metrics",
        "findings": "Findings",
        "recommendations": "Recommendations",
        "data_sources": "Data Sources",
        
        # Confidence levels
        "very_high_confidence": "Very High Confidence",
        "high_confidence": "High Confidence",
        "medium_confidence": "Medium Confidence",
        "moderate_confidence": "Moderate Confidence",
        "low_confidence": "Low Confidence",
        
        # Agent names
        "labour_economist": "Labour Economist",
        "nationalization": "Nationalization Expert",
        "skills_agent": "Skills & Education Specialist",
        "pattern_detective": "Pattern Detection",
        "national_strategy": "National Strategy Advisor",
        
        # Metrics
        "unemployment_rate": "Unemployment Rate",
        "qatarization_rate": "Qatarization Rate",
        "workforce": "Workforce",
        "skills_gap": "Skills Gap",
        
        # Actions
        "export_pdf": "Export to PDF",
        "view_history": "View History",
        "show_details": "Show Details",
    },
    "ar": {
        # Common UI elements
        "welcome": "مرحباً بكم في النظام الوطني لذكاء القوى العاملة في قطر",
        "ask_question": "اطرح سؤالاً",
        "loading": "جاري التحليل...",
        "error_occurred": "حدث خطأ",
        "try_again": "يرجى المحاولة مرة أخرى",
        
        # Analysis sections
        "executive_summary": "الملخص التنفيذي",
        "key_metrics": "المؤشرات الرئيسية",
        "findings": "النتائج",
        "recommendations": "التوصيات",
        "data_sources": "مصادر البيانات",
        
        # Confidence levels
        "very_high_confidence": "ثقة عالية جداً",
        "high_confidence": "ثقة عالية",
        "medium_confidence": "ثقة متوسطة",
        "moderate_confidence": "ثقة معتدلة",
        "low_confidence": "ثقة منخفضة",
        
        # Agent names
        "labour_economist": "خبير اقتصاد العمل",
        "nationalization": "خبير التوطين",
        "skills_agent": "أخصائي المهارات والتعليم",
        "pattern_detective": "كشف الأنماط",
        "national_strategy": "مستشار الاستراتيجية الوطنية",
        
        # Metrics
        "unemployment_rate": "معدل البطالة",
        "qatarization_rate": "معدل التوطين",
        "workforce": "القوى العاملة",
        "skills_gap": "فجوة المهارات",
        
        # Actions
        "export_pdf": "تصدير إلى PDF",
        "view_history": "عرض السجل",
        "show_details": "عرض التفاصيل",
    }
}


class Translator:
    """
    Bilingual translator for Arabic/English UI.
    
    Provides ministry-grade translation for Qatar's government system.
    """
    
    def __init__(self, default_language: str = "en"):
        """
        Initialize translator.
        
        Args:
            default_language: Default language code (en or ar)
        """
        self.default_language = default_language
        self.current_language = default_language
        logger.info(f"Translator initialized with default language: {default_language}")
    
    def set_language(self, language: str) -> None:
        """
        Set current language.
        
        Args:
            language: Language code (en or ar)
        """
        if language not in ["en", "ar"]:
            logger.warning(f"Unsupported language: {language}, using default")
            return
        
        self.current_language = language
        logger.info(f"Language set to: {language}")
    
    def translate(self, key: str, language: Optional[str] = None) -> str:
        """
        Translate a key to current or specified language.
        
        Args:
            key: Translation key
            language: Optional language override
            
        Returns:
            Translated string
        """
        lang = language or self.current_language
        
        if lang not in TRANSLATIONS:
            lang = self.default_language
        
        translation = TRANSLATIONS[lang].get(key)
        
        if translation is None:
            logger.warning(f"Missing translation for key: {key} in language: {lang}")
            # Fallback to English
            translation = TRANSLATIONS["en"].get(key, key)
        
        return translation
    
    def get_direction(self, language: Optional[str] = None) -> str:
        """
        Get text direction for language.
        
        Args:
            language: Language code (optional)
            
        Returns:
            "rtl" for Arabic, "ltr" for English
        """
        lang = language or self.current_language
        return "rtl" if lang == "ar" else "ltr"
    
    def is_rtl(self, language: Optional[str] = None) -> bool:
        """
        Check if language is right-to-left.
        
        Args:
            language: Language code (optional)
            
        Returns:
            True if RTL, False otherwise
        """
        return self.get_direction(language) == "rtl"


# Global translator instance
_translator: Optional[Translator] = None


def get_translator(language: str = "en") -> Translator:
    """
    Get or create global translator instance.
    
    Args:
        language: Default language
        
    Returns:
        Translator instance
    """
    global _translator
    if _translator is None:
        _translator = Translator(default_language=language)
    return _translator


def translate(key: str, language: Optional[str] = None) -> str:
    """
    Convenience function for translation.
    
    Args:
        key: Translation key
        language: Optional language code
        
    Returns:
        Translated string
    """
    translator = get_translator()
    return translator.translate(key, language)
