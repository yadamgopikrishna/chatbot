import os
import uuid
import logging
from flask import Blueprint, request, jsonify, session
from werkzeug.utils import secure_filename
from config import UPLOAD_FOLDER, get_current_api_key
from services.resume_service import (
    extract_text_from_resume_file,
    analyze_resume,
    generate_professional_resume
)

logger = logging.getLogger(__name__)
resume_bp = Blueprint("resume", __name__)


@resume_bp.route("/api/resume/analyze", methods=["POST"])
def analyze_resume_endpoint():
    """
    Analyzes an uploaded resume file or pasted text for ATS compatibility and role match.
    """
    json_data = request.get_json(silent=True) or {} if request.is_json else {}
    
    custom_api_key = (
        request.form.get("api_key")
        or json_data.get("api_key")
        or session.get("gemini_api_key")
        or get_current_api_key()
        or ""
    )
    custom_api_key = str(custom_api_key).strip() if custom_api_key else ""

    resume_text = ""
    target_role = ""
    job_description = ""

    if "resume_file" in request.files:
        uploaded_file = request.files["resume_file"]
        if uploaded_file.filename != "":
            clean_name = secure_filename(uploaded_file.filename) or f"resume_{uuid.uuid4().hex[:8]}.pdf"
            save_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4().hex[:8]}_{clean_name}")
            uploaded_file.save(save_path)
            resume_text = extract_text_from_resume_file(save_path)
            target_role = request.form.get("target_role", "").strip()
            job_description = request.form.get("job_description", "").strip()
    elif request.is_json:
        resume_text = json_data.get("resume_text", "").strip()
        target_role = json_data.get("target_role", "").strip()
        job_description = json_data.get("job_description", "").strip()
    else:
        resume_text = request.form.get("resume_text", "").strip()
        target_role = request.form.get("target_role", "").strip()
        job_description = request.form.get("job_description", "").strip()

    if not resume_text:
        return jsonify({"success": False, "error": "Please provide a resume file or paste resume text."}), 400

    analysis_result = analyze_resume(
        resume_text=resume_text,
        job_description=job_description,
        target_role=target_role,
        custom_api_key=custom_api_key
    )

    return jsonify(analysis_result)


@resume_bp.route("/api/resume/generate", methods=["POST"])
def generate_resume_endpoint():
    """
    Generates a structured, ATS-compliant resume and creates a downloadable Word .docx file.
    """
    json_data = request.get_json(silent=True) or {}
    custom_api_key = (
        json_data.get("api_key")
        or session.get("gemini_api_key")
        or get_current_api_key()
        or ""
    )
    custom_api_key = str(custom_api_key).strip() if custom_api_key else ""

    if not json_data.get("target_role") and not json_data.get("skills"):
        return jsonify({"success": False, "error": "Please provide at least a target role and some skills."}), 400

    result = generate_professional_resume(
        candidate_info=json_data,
        custom_api_key=custom_api_key
    )

    return jsonify(result)
