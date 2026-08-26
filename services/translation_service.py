import re
import logging
from config import SUPPORTED_LANGUAGES

logger = logging.getLogger(__name__)

# Unicode character script ranges for accurate zero-overhead language detection
UNICODE_RANGES = {
    "te": (0x0C00, 0x0C7F, "Telugu"),
    "hi": (0x0900, 0x097F, "Hindi"),
    "ta": (0x0B80, 0x0BFF, "Tamil"),
    "kn": (0x0C80, 0x0CFF, "Kannada"),
    "ml": (0x0D00, 0x0D7F, "Malayalam"),
    "bn": (0x0980, 0x09FF, "Bengali"),
    "gu": (0x0A80, 0x0AFF, "Gujarati"),
    "pa": (0x0A00, 0x0A7F, "Punjabi"),
    "ar": (0x0600, 0x06FF, "Arabic/Urdu"),
    "zh": (0x4E00, 0x9FFF, "Chinese"),
    "ja": (0x3040, 0x30FF, "Japanese"),
    "ko": (0xAC00, 0xD7AF, "Korean"),
}


def detect_language(text):
    """
    Detects the primary language code of the provided text based on Unicode character distributions.
    Returns ISO language code (e.g., 'te', 'hi', 'en', etc.)
    """
    if not text or not text.strip():
        return "en"

    counts = {code: 0 for code in UNICODE_RANGES}
    latin_count = 0

    for char in text:
        code_point = ord(char)
        found = False
        for code, (start, end, _) in UNICODE_RANGES.items():
            if start <= code_point <= end:
                counts[code] += 1
                found = True
                break
        if not found:
            if (65 <= code_point <= 90) or (97 <= code_point <= 122):
                latin_count += 1

    # Check non-Latin scripts first
    max_script_code, max_script_count = max(counts.items(), key=lambda x: x[1])
    if max_script_count >= 3 or (max_script_count > 0 and max_script_count >= latin_count * 0.3):
        return max_script_code

    # Check common European language patterns in Latin script
    text_lower = text.lower()
    if re.search(r'\b(que|por|para|como|con|los|las|del|una|este)\b', text_lower):
        return "es"  # Spanish
    elif re.search(r'\b(le|la|les|pour|avec|dans|sur|est|une|des)\b', text_lower):
        return "fr"  # French
    elif re.search(r'\b(der|die|das|und|nicht|mit|für|auf|ein|eine)\b', text_lower):
        return "de"  # German
    elif re.search(r'\b(não|com|para|uma|este|pelo|mais)\b', text_lower):
        return "pt"  # Portuguese

    return "en"


def get_language_name(lang_code):
    """Returns human-readable name of the language."""
    return SUPPORTED_LANGUAGES.get(lang_code, "English")


def build_multilingual_system_instruction(user_preferred_lang="auto", detected_lang=None):
    """
    Builds system instruction to ensure responses match user language naturally and handle cross-lingual contexts.
    """
    target_lang = user_preferred_lang if user_preferred_lang != "auto" else (detected_lang or "en")
    lang_name = get_language_name(target_lang)

    instruction = f"""
Language Handling Directive:
- The user is conversing in or prefers: {lang_name} (Code: {target_lang}).
- Automatically respond in fluent, grammatically natural, and culturally appropriate {lang_name}.
- Cross-Language Document Q&A: If the user provides a document in English (or any other language) and asks questions in {lang_name}, thoroughly read the source document, retrieve facts accurately, and formulate the complete answer in {lang_name} while retaining precise technical terms and page citations.
- When translating, preserve formatting, code snippets, numbers, tables, and mathematical formulas verbatim.
"""
    return instruction.strip()
