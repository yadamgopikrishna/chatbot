import os
import uuid
import base64
import logging
from PIL import Image
import io
from config import UPLOAD_FOLDER, get_current_api_key
from services.gemini_client import get_client, clean_key

logger = logging.getLogger(__name__)


def generate_image_ai(prompt, aspect_ratio="1:1", custom_api_key=None):
    """
    Generates an image using Google GenAI Image models (Imagen 3.0 / Gemini).
    Saves the output to the uploads folder and returns image URL & metadata.
    """
    if not prompt or not prompt.strip():
        return {"success": False, "error": "Prompt cannot be empty"}

    client, err = get_client(custom_api_key)
    if err:
        return {"success": False, "error": err}

    # Ensure valid aspect ratio
    valid_ratios = {"1:1", "3:4", "4:3", "9:16", "16:9"}
    selected_ratio = aspect_ratio if aspect_ratio in valid_ratios else "1:1"

    img_filename = f"gen_{uuid.uuid4().hex[:10]}.png"
    save_path = os.path.join(UPLOAD_FOLDER, img_filename)

    # 1. Try Imagen 3.0 via Google GenAI SDK
    try:
        from google.genai import types

        config = types.GenerateImagesConfig(
            number_of_images=1,
            aspect_ratio=selected_ratio,
            output_mime_type="image/png"
        )

        response = client.models.generate_images(
            model="imagen-3.0-generate-002",
            prompt=prompt,
            config=config
        )

        if response.generated_images:
            generated = response.generated_images[0]
            img_bytes = generated.image.image_bytes
            with open(save_path, "wb") as f:
                f.write(img_bytes)

            return {
                "success": True,
                "image_url": f"/uploads/{img_filename}",
                "image_path": save_path,
                "filename": img_filename,
                "prompt": prompt,
                "model": "imagen-3.0-generate-002",
                "aspect_ratio": selected_ratio
            }
    except Exception as e:
        logger.info("Imagen 3 generation notice: %s. Trying fallback model...", e)

    # 2. Try gemini-2.5-flash / gemini-3-pro-image-preview fallback
    try:
        from google.genai import types
        config = types.GenerateImagesConfig(
            number_of_images=1,
            aspect_ratio=selected_ratio,
            output_mime_type="image/png"
        )
        response = client.models.generate_images(
            model="imagen-3.0-fast-generate-001",
            prompt=prompt,
            config=config
        )
        if response.generated_images:
            generated = response.generated_images[0]
            with open(save_path, "wb") as f:
                f.write(generated.image.image_bytes)

            return {
                "success": True,
                "image_url": f"/uploads/{img_filename}",
                "image_path": save_path,
                "filename": img_filename,
                "prompt": prompt,
                "model": "imagen-3.0-fast-generate-001",
                "aspect_ratio": selected_ratio
            }
    except Exception as e2:
        logger.warning("Fast Imagen generation notice: %s", e2)

    # 3. Create high-detail artistic SVG/Canvas visual art as resilient fallback
    try:
        from services.gemini_client import generate_chat_response
        svg_prompt = f"""
Create a visually stunning, detailed SVG artwork illustration representing: "{prompt}".
Return ONLY valid raw SVG code starting with `<svg viewBox="0 0 800 800" ...>` and ending with `</svg>`.
Do not include any explanation or markdown formatting outside the SVG.
"""
        res = generate_chat_response(
            messages=[{"role": "user", "content": svg_prompt}],
            custom_api_key=custom_api_key
        )
        svg_text = res.get("text", "")
        if "<svg" in svg_text and "</svg>" in svg_text:
            svg_content = svg_text[svg_text.find("<svg"):svg_text.find("</svg>") + 6]
            svg_filename = f"gen_{uuid.uuid4().hex[:10]}.svg"
            svg_path = os.path.join(UPLOAD_FOLDER, svg_filename)
            with open(svg_path, "w", encoding="utf-8") as f:
                f.write(svg_content)

            return {
                "success": True,
                "image_url": f"/uploads/{svg_filename}",
                "image_path": svg_path,
                "filename": svg_filename,
                "prompt": prompt,
                "model": "gemini-vector-art",
                "aspect_ratio": selected_ratio
            }
    except Exception as e3:
        logger.error("Visual fallback error: %s", e3)

    return {
        "success": False,
        "error": "Failed to generate image. Please ensure your Gemini API key has access to Imagen models in Google AI Studio."
    }
