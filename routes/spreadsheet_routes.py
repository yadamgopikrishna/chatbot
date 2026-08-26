import os
import uuid
import json
import logging
from flask import Blueprint, request, jsonify, session
from werkzeug.utils import secure_filename
from config import UPLOAD_FOLDER, get_current_api_key
from services.spreadsheet_service import analyze_spreadsheet, query_spreadsheet_data
from services.gemini_client import generate_chat_response

logger = logging.getLogger(__name__)
spreadsheet_bp = Blueprint("spreadsheet", __name__)


@spreadsheet_bp.route("/api/spreadsheet/analyze", methods=["POST"])
def analyze_sheet():
    """
    Parses and analyzes an Excel or CSV spreadsheet.
    """
    if "file" not in request.files:
        return jsonify({"error": "No spreadsheet file provided"}), 400

    file = request.files["file"]
    sheet_name = request.form.get("sheet_name")

    clean_name = secure_filename(file.filename) or f"data_{uuid.uuid4().hex[:8]}.csv"
    save_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4().hex}_{clean_name}")
    file.save(save_path)

    analysis = analyze_spreadsheet(save_path, sheet_name=sheet_name)
    analysis["file_path"] = save_path

    return jsonify({"analysis": analysis})


@spreadsheet_bp.route("/api/spreadsheet/query", methods=["POST"])
def query_sheet():
    """
    Answers natural language queries regarding the spreadsheet and outputs insights + charts.
    """
    data = request.get_json() or {}
    file_path = data.get("file_path")
    query = data.get("query", "").strip()
    custom_api_key = (data.get("api_key") or session.get("gemini_api_key") or get_current_api_key() or "").strip()

    if not file_path or not os.path.exists(file_path):
        return jsonify({"error": "Valid file_path is required"}), 400

    sheet_data = analyze_spreadsheet(file_path)

    prompt = f"""
Dataset Summary for {sheet_data['filename']}:
- Dimensions: {sheet_data['row_count']} rows, {sheet_data['column_count']} columns
- Columns: {', '.join(sheet_data['columns'])}
- Missing Values: {json.dumps(sheet_data['missing_values'])}
- Numerical Stats: {json.dumps(sheet_data['summary_statistics'])}
- Categorical Distribution: {json.dumps(sheet_data['categorical_summary'])}
- Sample Records: {json.dumps(sheet_data['sample_data'][:5])}

User Question: "{query}"

Answer the question accurately based on this data. Highlight key metrics, trends, and specific calculations.
"""

    ai_resp = generate_chat_response(
        messages=[{"role": "user", "content": prompt}],
        system_instruction="You are a Senior Data Analyst and Business Intelligence specialist. Provide precise data-driven answers.",
        model_name="gemini-2.5-flash",
        custom_api_key=custom_api_key
    )

    return jsonify({
        "answer": ai_resp["text"],
        "suggested_charts": sheet_data.get("suggested_charts", [])
    })
