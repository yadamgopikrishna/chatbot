import os
import io
import json
import logging
from PIL import Image
from config import DEFAULT_MODEL, AVAILABLE_MODELS

logger = logging.getLogger(__name__)

def clean_key(raw_key):
    """Sanitizes raw API key string to strict ASCII alphanumeric/symbol characters."""
    if not raw_key:
        return ""
    # Strip any non-ASCII characters that might have been copied with the key
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
        return "⚠️ **Invalid API Key**: The provided Gemini API Key was rejected by Google AI Studio. Please verify and re-enter your key in Settings (⚙️)."
    elif "RESOURCE_EXHAUSTED" in err_str or "429" in err_str:
        return "⚠️ **Rate Limit Exceeded**: Gemini API quota or rate limit reached. Please try again in a few moments."
    elif "codec can't encode" in err_str or "UnicodeEncodeError" in err_str or "ascii" in err_str:
        return "⚠️ **Input Formatting Notice**: Non-standard characters or invalid key format detected. Please verify your query or API Key in Settings (⚙️)."
    elif "NOT_FOUND" in err_str or "404" in err_str:
        return "⚠️ **Model Not Found**: The requested Gemini model is currently unavailable."
    else:
        return f"⚠️ **AI Service Notice**: {err_str[:150]}"


def generate_chat_response(
    messages,
    system_instruction=None,
    model_name=None,
    images=None,
    custom_api_key=None,
    temperature=0.7
):
    """
    Generates non-streaming AI response with multimodal support.
    """
    client, err = get_client(custom_api_key)
    if err:
        return {
            "text": f"⚠️ **API Key Notice**: {err}\n\n*Click **Settings (⚙️)** in the sidebar to enter and save your Gemini API Key.*",
            "model": model_name or DEFAULT_MODEL,
            "error": True
        }

    selected_model = model_name if model_name in AVAILABLE_MODELS else DEFAULT_MODEL

    try:
        from google.genai import types

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

        response = client.models.generate_content(
            model=selected_model,
            contents=contents,
            config=config
        )

        return {
            "text": response.text or "No response received.",
            "model": selected_model,
            "error": False
        }
    except UnicodeEncodeError as ue:
        return {
            "text": "⚠️ **Encoding Notice**: Character encoding issue detected. Please check your API Key in Settings (⚙️).",
            "model": selected_model,
            "error": True
        }
    except Exception as e:
        err_msg = parse_gemini_error(e)
        return {
            "text": err_msg,
            "model": selected_model,
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
    Generator yielding Server-Sent Events (SSE) data chunks for streaming AI responses.
    """
    client, err = get_client(custom_api_key)
    if err:
        error_msg = f"⚠️ **API Key Notice**: {err}\n\n*Click **Settings (⚙️)** in the sidebar to enter and save your Gemini API Key.*"
        yield f"data: {json.dumps({'chunk': error_msg, 'done': True, 'error': True})}\n\n"
        return

    selected_model = model_name if model_name in AVAILABLE_MODELS else DEFAULT_MODEL

    try:
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

        response_stream = client.models.generate_content_stream(
            model=selected_model,
            contents=contents,
            config=config
        )

        for chunk in response_stream:
            if chunk.text:
                yield f"data: {json.dumps({'chunk': chunk.text, 'done': False})}\n\n"

        yield f"data: {json.dumps({'chunk': '', 'done': True, 'model': selected_model})}\n\n"

    except UnicodeEncodeError:
        err_msg = "\n\n⚠️ **Encoding Notice**: Character encoding issue detected. Please check your API Key in Settings (⚙️)."
        yield f"data: {json.dumps({'chunk': err_msg, 'done': True, 'error': True})}\n\n"
    except Exception as e:
        err_msg = f"\n\n{parse_gemini_error(e)}"
        yield f"data: {json.dumps({'chunk': err_msg, 'done': True, 'error': True})}\n\n"
