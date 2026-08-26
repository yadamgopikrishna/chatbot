import os
import uuid
import logging
from flask import Blueprint, request, jsonify, session, send_file
from werkzeug.utils import secure_filename
from config import UPLOAD_FOLDER, ALL_ALLOWED_EXTENSIONS
from models import (
    save_document,
    get_user_documents,
    get_document_by_id,
    delete_document,
    save_document_chunks,
    get_document_chunks
)
from services.pdf_service import extract_pdf_data, chunk_pdf_pages, search_pdf_content
from services.doc_service import extract_document_data, compare_documents
from services.spreadsheet_service import analyze_spreadsheet

logger = logging.getLogger(__name__)
document_bp = Blueprint("document", __name__)

def get_file_category(ext):
    ext = ext.lower()
    if ext == ".pdf":
        return "pdf"
    elif ext in [".docx", ".doc", ".txt", ".md", ".rtf"]:
        return "docx" if ext in [".docx", ".doc"] else "text"
    elif ext in [".xlsx", ".xls", ".csv"]:
        return "spreadsheet"
    elif ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"]:
        return "image"
    return "unknown"


@document_bp.route("/api/documents/upload", methods=["POST"])
def upload_document():
    """
    Handles single or multi-file uploads, auto-extracts text, chunks, and saves to database.
    """
    user_email = session.get("email", "guest@chatbot.local")
    conv_id = request.form.get("conversation_id")

    if "file" not in request.files and "files" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    uploaded_files = request.files.getlist("file") or request.files.getlist("files")
    processed_docs = []

    for f in uploaded_files:
        if not f or not f.filename:
            continue

        raw_filename = f.filename
        clean_name = secure_filename(raw_filename) or f"file_{uuid.uuid4().hex[:8]}"
        ext = os.path.splitext(clean_name)[1].lower()

        if ext not in ALL_ALLOWED_EXTENSIONS:
            return jsonify({"error": f"File type {ext} is not supported."}), 400

        # Unique file path
        unique_name = f"{uuid.uuid4().hex}_{clean_name}"
        saved_path = os.path.join(UPLOAD_FOLDER, unique_name)
        f.save(saved_path)

        file_size = os.path.getsize(saved_path)
        file_category = get_file_category(ext)
        page_count = 1
        meta = {}
        chunks_to_save = []

        try:
            if file_category == "pdf":
                pdf_data = extract_pdf_data(saved_path)
                page_count = pdf_data["page_count"]
                meta = pdf_data["metadata"]
                meta["word_count"] = pdf_data["total_words"]
                meta["has_scanned_pages"] = pdf_data["has_scanned_pages"]
                chunks_to_save = chunk_pdf_pages(pdf_data["pages"])

            elif file_category in ["docx", "text"]:
                doc_data = extract_document_data(saved_path)
                meta["headings"] = [h["text"] for h in doc_data["headings"][:10]]
                meta["word_count"] = doc_data["word_count"]
                meta["table_count"] = len(doc_data["tables"])
                # Create chunks
                words = doc_data["full_text"].split()
                step = 600
                for i in range(0, len(words), step):
                    chunk_text = " ".join(words[i:i+step])
                    chunks_to_save.append({
                        "page": (i // step) + 1,
                        "text": chunk_text,
                        "metadata": {"doc_name": clean_name}
                    })

            elif file_category == "spreadsheet":
                sheet_data = analyze_spreadsheet(saved_path)
                meta["row_count"] = sheet_data["row_count"]
                meta["column_count"] = sheet_data["column_count"]
                meta["columns"] = sheet_data["columns"]
                meta["sheet_names"] = sheet_data["sheet_names"]

            doc_id = save_document(
                user_email=user_email,
                filename=raw_filename,
                file_type=file_category,
                file_size=file_size,
                file_path=saved_path,
                page_count=page_count,
                conversation_id=conv_id,
                metadata=meta
            )

            if chunks_to_save:
                save_document_chunks(doc_id, chunks_to_save)

            processed_docs.append({
                "doc_id": doc_id,
                "filename": raw_filename,
                "file_type": file_category,
                "file_size": file_size,
                "file_path": saved_path,
                "page_count": page_count,
                "metadata": meta,
                "status": "ready"
            })

        except Exception as e:
            logger.error("Error processing uploaded file %s: %s", raw_filename, e)
            return jsonify({"error": f"Failed to process {raw_filename}: {str(e)}"}), 500

    return jsonify({"success": True, "documents": processed_docs})


@document_bp.route("/api/documents/list", methods=["GET"])
def list_documents():
    user_email = session.get("email", "guest@chatbot.local")
    docs = get_user_documents(user_email)
    return jsonify({"documents": docs})


@document_bp.route("/api/documents/<doc_id>", methods=["GET"])
def get_document(doc_id):
    doc = get_document_by_id(doc_id)
    if not doc:
        return jsonify({"error": "Document not found"}), 404
    return jsonify({"document": doc})


@document_bp.route("/api/documents/<doc_id>/search", methods=["POST"])
def search_doc(doc_id):
    doc = get_document_by_id(doc_id)
    if not doc:
        return jsonify({"error": "Document not found"}), 404

    data = request.get_json() or {}
    query = data.get("query", "").strip()
    if not query:
        return jsonify({"results": []})

    if doc["file_type"] == "pdf":
        pdf_data = extract_pdf_data(doc["file_path"])
        matches = search_pdf_content(pdf_data["pages"], query)
        return jsonify({"results": matches})
    else:
        chunks = get_document_chunks(doc_id)
        matches = [c for c in chunks if query.lower() in c.get("content", "").lower()]
        return jsonify({"results": [{"page_num": m.get("page_number", 1), "snippet": m.get("content", "")[:200]} for m in matches]})


@document_bp.route("/api/documents/compare", methods=["POST"])
def compare_two_documents():
    """
    Compares two documents by ID or uploaded texts and returns structured diff.
    """
    data = request.get_json() or {}
    doc_id_a = data.get("doc_id_a")
    doc_id_b = data.get("doc_id_b")

    if not doc_id_a or not doc_id_b:
        return jsonify({"error": "doc_id_a and doc_id_b are required"}), 400

    doc_a = get_document_by_id(doc_id_a)
    doc_b = get_document_by_id(doc_id_b)

    if not doc_a or not doc_b:
        return jsonify({"error": "One or both documents could not be found"}), 404

    # Extract text from both
    text_a = ""
    text_b = ""

    if doc_a["file_type"] == "pdf":
        text_a = extract_pdf_data(doc_a["file_path"])["full_text"]
    else:
        text_a = extract_document_data(doc_a["file_path"])["full_text"]

    if doc_b["file_type"] == "pdf":
        text_b = extract_pdf_data(doc_b["file_path"])["full_text"]
    else:
        text_b = extract_document_data(doc_b["file_path"])["full_text"]

    comparison = compare_documents(text_a, text_b, doc_a["filename"], doc_b["filename"])
    return jsonify({"comparison": comparison})


@document_bp.route("/api/documents/<doc_id>/delete", methods=["POST", "DELETE"])
def delete_doc(doc_id):
    doc = get_document_by_id(doc_id)
    if not doc:
        return jsonify({"error": "Document not found"}), 404

    # Delete physical file if exists
    if os.path.exists(doc["file_path"]):
        try:
            os.remove(doc["file_path"])
        except Exception:
            pass

    delete_document(doc_id)
    return jsonify({"success": True})
