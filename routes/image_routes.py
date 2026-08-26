import os
import uuid
import logging
from flask import Blueprint, request, jsonify, session
from werkzeug.utils import secure_filename
from config import UPLOAD_FOLDER, ALLOWED_IMAGE_EXTENSIONS, get_current_api_key
from services.vision_service import extract_image_metadata, perform_image_forensics
from services.ocr_service import prepare_ocr_prompt
from services.gemini_client import generate_chat_response
from services.image_gen_service import generate_image_ai

logger = logging.getLogger(__name__)
image_bp = Blueprint("image", __name__)


@image_bp.route("/api/images/generate", methods=["POST"])
def generate_image_endpoint():
    """
    Generates an image from natural language prompt using Imagen 3.0 / Gemini models.
    """
    data = request.get_json() or {}
    prompt = data.get("prompt", "").strip()
    aspect_ratio = data.get("aspect_ratio", "1:1")
    custom_api_key = (
        data.get("api_key")
        or session.get("gemini_api_key")
        or get_current_api_key()
        or ""
    ).strip()

    if not prompt:
        return jsonify({"success": False, "error": "Please provide an image prompt."}), 400

    result = generate_image_ai(
        prompt=prompt,
        aspect_ratio=aspect_ratio,
        custom_api_key=custom_api_key
    )

    if result.get("success"):
        return jsonify(result)
    else:
        return jsonify({"success": False, "error": result.get("error", "Image generation failed")}), 400


@image_bp.route("/api/images/analyze", methods=["POST"])
def analyze_image():
    """
    Analyzes an uploaded image with Gemini Vision.
    """
    if "image" not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    img_file = request.files["image"]
    prompt = request.form.get("prompt", "Describe this image in detail and explain key elements, text, and objects.")
    model = request.form.get("model", "gemini-2.5-flash")
    custom_api_key = (request.form.get("api_key") or session.get("gemini_api_key") or get_current_api_key() or "").strip()

    clean_name = secure_filename(img_file.filename) or f"img_{uuid.uuid4().hex[:8]}.png"
    save_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4().hex}_{clean_name}")
    img_file.save(save_path)

    metadata = extract_image_metadata(save_path)

    ai_resp = generate_chat_response(
        messages=[{"role": "user", "content": prompt}],
        system_instruction="You are an expert Computer Vision and Image Analysis AI. Provide rich, detailed visual breakdowns.",
        model_name=model,
        images=[save_path],
        custom_api_key=custom_api_key
    )

    return jsonify({
        "analysis": ai_resp["text"],
        "metadata": metadata,
        "image_path": save_path
    })


@image_bp.route("/api/images/detect", methods=["POST"])
def detect_authenticity():
    """
    Performs AI generation and digital manipulation detection with forensic evidence report.
    """
    if "image" not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    img_file = request.files["image"]
    custom_api_key = (request.form.get("api_key") or session.get("gemini_api_key") or get_current_api_key() or "").strip()
    clean_name = secure_filename(img_file.filename) or f"img_{uuid.uuid4().hex[:8]}.png"
    save_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4().hex}_{clean_name}")
    img_file.save(save_path)

    forensics = perform_image_forensics(save_path)

    prompt = """
Analyze this image for signs of AI generation (e.g. Midjourney, DALL-E, Stable Diffusion) or digital manipulation.
Examine lighting consistency, shadows, reflections, eye reflections, hand anatomy, background coherence, text rendering, and edge artifacts.
Provide a probabilistic evaluation and summarize forensic observations clearly.
"""
    ai_resp = generate_chat_response(
        messages=[{"role": "user", "content": prompt}],
        system_instruction="You are a digital media forensics and authenticity analysis specialist. Explain visual evidence probabilistically.",
        model_name="gemini-2.5-flash",
        images=[save_path],
        custom_api_key=custom_api_key
    )

    forensics["visual_explanation"] = ai_resp["text"]

    return jsonify({
        "forensics": forensics,
        "image_path": save_path
    })


@image_bp.route("/api/images/ocr", methods=["POST"])
def ocr_extract():
    """
    Extracts text from image using high-precision multilingual OCR engine.
    """
    if "image" not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    img_file = request.files["image"]
    language = request.form.get("language", "auto")
    target_type = request.form.get("type", "general")
    custom_api_key = (request.form.get("api_key") or session.get("gemini_api_key") or get_current_api_key() or "").strip()

    clean_name = secure_filename(img_file.filename) or f"img_{uuid.uuid4().hex[:8]}.png"
    save_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4().hex}_{clean_name}")
    img_file.save(save_path)

    ocr_prompt = prepare_ocr_prompt(language=language, target_type=target_type)

    ai_resp = generate_chat_response(
        messages=[{"role": "user", "content": ocr_prompt}],
        system_instruction="You are a professional Multilingual OCR Engine.",
        model_name="gemini-2.5-flash",
        images=[save_path],
        custom_api_key=custom_api_key
    )

    return jsonify({
        "extracted_text": ai_resp["text"],
        "language": language,
        "type": target_type
    })
