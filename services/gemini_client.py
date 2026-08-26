import os
import io
import time
import json
import logging
from PIL import Image
from config import DEFAULT_MODEL, AVAILABLE_MODELS

logger = logging.getLogger(__name__)

# Fallback sequence to recover from rate limits (429) across different model quotas
FALLBACK_SEQUENCE = [
    "gemini-2.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.7-flash",
    "gemini-2.5-pro"
]



def clean_key(raw_key):
    """Sanitizes raw API key string to strict ASCII alphanumeric/symbol characters."""
    if not raw_key:
        return ""
    cleaned = "".join(c for c in str(raw_key) if ord(c) < 128)
    return cleaned.strip().strip('"').strip("'").strip()


def get_client(custom_api_key=None):
    """
    Initializes and returns a Google GenAI Client instance.
    Checks custom_api_key, os.environ, and .env dynamically.
    """
    api_key = clean_key(
        custom_api_key
        or os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
    )

    if not api_key:
        return None, "GEMINI_API_KEY is not configured. Please enter your API key in the Settings modal or .env file."

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        return client, None
    except Exception as e:
        safe_err = repr(e)
        logger.error("Failed to initialize Google GenAI Client: %s", safe_err)
        return None, f"Failed to initialize Gemini Client: {safe_err}"


def parse_gemini_error(err_obj):
    """Extracts a clean, actionable error message from Gemini API exceptions."""
    err_str = str(err_obj) if err_obj else ""
    if "API_KEY_INVALID" in err_str or "API key not valid" in err_str or "400" in err_str or "INVALID_ARGUMENT" in err_str:
        return "⚠️ **Invalid API Key**: The provided Gemini API Key was rejected by Google AI Studio. Please verify and re-enter your key in **Settings (⚙️)**."
    elif "RESOURCE_EXHAUSTED" in err_str or "429" in err_str:
        return (
            "⚠️ **Gemini Free-Tier Rate Limit Reached (429)**\n\n"
            "Google AI Studio free tier limits requests to **15 per minute (RPM)** or **1,500 daily requests**.\n\n"
            "**Quick solutions:**\n"
            "1. ⏳ **Wait 30–60 seconds** for the rate limit window to reset.\n"
            "2. ⚡ Switch model to **Gemini 3.5 Flash Lite** in the top header selector.\n"
            "3. 🔑 Add a new/fresh API key in **Settings (⚙️)** from [Google AI Studio](https://aistudio.google.com/app/apikey)."
        )
    elif "503" in err_str or "Service Unavailable" in err_str:
        return "⚠️ **Google AI Service Temporary Busy**: Google AI servers are temporarily experiencing high traffic. Please retry in a few seconds."
    elif "codec can't encode" in err_str or "UnicodeEncodeError" in err_str or "ascii" in err_str:
        return "⚠️ **Input Formatting Notice**: Non-standard characters or invalid key format detected. Please verify your query or API Key in Settings (⚙️)."
    elif "NOT_FOUND" in err_str or "404" in err_str:
        return "⚠️ **Model Not Found**: The requested Gemini model is currently unavailable."
    else:
        return f"⚠️ **AI Service Notice**: {err_str[:160]}"


def generate_chat_response(
    messages,
    system_instruction=None,
    model_name=None,
    images=None,
    custom_api_key=None,
    temperature=0.7
):
    """
    Generates non-streaming AI response with multi-model automatic fallback on rate limits.
    """
    client, err = get_client(custom_api_key)
    if err:
        return {
            "text": f"⚠️ **API Key Notice**: {err}\n\n*Click **Settings (⚙️)** in the sidebar to enter and save your Gemini API Key.*",
            "model": model_name or DEFAULT_MODEL,
            "error": True
        }

    from google.genai import types

    # Prepare contents
    contents = []
    if images:
        for img_path in images:
            if os.path.exists(img_path):
                try:
                    with Image.open(img_path) as pil_img:
                        contents.append(pil_img.copy())
                except Exception as img_err:
                    logger.warning("Could not load image: %s", img_err)

    for msg in messages:
        text = msg.get("content") or msg.get("text", "")
        if text:
            contents.append(str(text))

    config = types.GenerateContentConfig(
        system_instruction=str(system_instruction) if system_instruction else None,
        temperature=temperature
    )

    # Sequence of models to try
    primary_model = model_name if model_name in AVAILABLE_MODELS else DEFAULT_MODEL
    models_to_try = [primary_model] + [m for m in FALLBACK_SEQUENCE if m != primary_model]

    last_error = None
    for model_candidate in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_candidate,
                contents=contents,
                config=config
            )
            return {
                "text": response.text or "No response received.",
                "model": model_candidate,
                "error": False
            }
        except Exception as e:
            err_str = str(e)
            last_error = e
            if "RESOURCE_EXHAUSTED" in err_str or "429" in err_str or "503" in err_str:
                logger.warning("Model %s returned rate limit / busy. Attempting fallback model...", model_candidate)
                time.sleep(0.8)
                continue
            else:
                # Other non-retryable error
                return {
                    "text": parse_gemini_error(e),
                    "model": model_candidate,
                    "error": True
                }

    return {
        "text": parse_gemini_error(last_error),
        "model": primary_model,
        "error": True
    }


def stream_chat_response(
    messages,
    system_instruction=None,
    model_name=None,
    images=None,
    custom_api_key=None,
    temperature=0.7
):
    """
    Generator yielding Server-Sent Events (SSE) data chunks with multi-model rate-limit fallback.
    """
    client, err = get_client(custom_api_key)
    if err:
        error_msg = f"⚠️ **API Key Notice**: {err}\n\n*Click **Settings (⚙️)** in the sidebar to enter and save your Gemini API Key.*"
        yield f"data: {json.dumps({'chunk': error_msg, 'done': True, 'error': True})}\n\n"
        return

    from google.genai import types

    contents = []
    if images:
        for img_path in images:
            if os.path.exists(img_path):
                try:
                    with Image.open(img_path) as pil_img:
                        contents.append(pil_img.copy())
                except Exception as e:
                    logger.warning("Could not open image for Gemini: %s", e)

    for msg in messages:
        text = msg.get("content") or msg.get("text", "")
        if text:
            contents.append(str(text))

    config = types.GenerateContentConfig(
        system_instruction=str(system_instruction) if system_instruction else None,
        temperature=temperature
    )

    primary_model = model_name if model_name in AVAILABLE_MODELS else DEFAULT_MODEL
    models_to_try = [primary_model] + [m for m in FALLBACK_SEQUENCE if m != primary_model]

    streamed_successfully = False
    last_error = None

    for model_candidate in models_to_try:
        try:
            response_stream = client.models.generate_content_stream(
                model=model_candidate,
                contents=contents,
                config=config
            )

            has_chunks = False
            for chunk in response_stream:
                if chunk.text:
                    has_chunks = True
                    yield f"data: {json.dumps({'chunk': chunk.text, 'done': False})}\n\n"

            if has_chunks:
                yield f"data: {json.dumps({'chunk': '', 'done': True, 'model': model_candidate})}\n\n"
                streamed_successfully = True
                break

        except Exception as e:
            err_str = str(e)
            last_error = e
            if "RESOURCE_EXHAUSTED" in err_str or "429" in err_str or "503" in err_str:
                logger.warning("Streaming for %s hit quota/rate limit. Attempting fallback model...", model_candidate)
                time.sleep(0.8)
                continue
            else:
                err_msg = f"\n\n{parse_gemini_error(e)}"
                yield f"data: {json.dumps({'chunk': err_msg, 'done': True, 'error': True})}\n\n"
                streamed_successfully = True
                break

    if not streamed_successfully:
        err_msg = f"\n\n{parse_gemini_error(last_error)}"
        yield f"data: {json.dumps({'chunk': err_msg, 'done': True, 'error': True})}\n\n"
