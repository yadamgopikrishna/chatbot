import os
import logging
from PIL import Image

logger = logging.getLogger(__name__)

def prepare_ocr_prompt(language="auto", target_type="general"):
    """
    Constructs a high-precision multimodal OCR extraction prompt.
    """
    lang_instruction = ""
    if language != "auto" and language:
        lang_instruction = f"Pay special attention to characters in {language}."

    if target_type == "table":
        type_instruction = "Extract all tabular data into clean Markdown table format with headers."
    elif target_type == "receipt":
        type_instruction = "Extract all receipt details including merchant name, date, line items, prices, tax, and total amount."
    elif target_type == "form":
        type_instruction = "Extract all form fields, labels, and filled values into a structured key-value list."
    else:
        type_instruction = "Extract all text verbatim preserving paragraph breaks, lists, and formatting."

    prompt = f"""
You are an expert high-accuracy Multilingual OCR Engine.
Task: Perform optical character recognition on the provided document/image.
{type_instruction}
{lang_instruction}

Guidelines:
1. Extract every piece of readable text accurately.
2. Preserve numbers, dates, punctuation, and language scripts accurately (Telugu, Hindi, Tamil, Kannada, Malayalam, Bengali, Marathi, Gujarati, Urdu, Punjabi, English, etc.).
3. If tabular data is present, format it using GitHub markdown tables.
4. Do not summarize or omit text unless completely unreadable.
"""
    return prompt.strip()
