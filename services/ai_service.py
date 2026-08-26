import os
import re
import json
import logging
from config import DEFAULT_MODEL, AVAILABLE_MODELS
from services.gemini_client import generate_chat_response, stream_chat_response
from services.translation_service import detect_language, build_multilingual_system_instruction, get_language_name
from services.rag_service import compute_tf_idf_similarity, build_rag_context_prompt
from services.pdf_service import extract_pdf_data, chunk_pdf_pages
from services.doc_service import extract_document_data
from services.spreadsheet_service import analyze_spreadsheet
from services.vision_service import perform_image_forensics, extract_image_metadata
from services.image_gen_service import generate_image_ai
from services.resume_service import analyze_resume, generate_professional_resume

logger = logging.getLogger(__name__)


def is_resume_generation_query(message):
    """
    Checks if user prompt is asking to build or generate a resume.
    """
    if not message:
        return False, ""
    msg_lower = message.strip().lower()
    patterns = [
        r"^(?:generate|create|build|make|write)\s+(?:an?\s+)?(?:resume|cv|curriculum vitae)\s+(?:for|as)?\s*(.+)$",
        r"^(?:resume|cv)\s+(?:for|of)\s+(.+)$"
    ]
    for p in patterns:
        m = re.match(p, msg_lower, re.IGNORECASE)
        if m:
            extracted = message.strip()[m.start(1):m.end(1)].strip()
            return True, extracted if extracted else message.strip()
    return False, ""


def is_image_generation_query(message):
    """
    Checks if user prompt is asking to generate, draw, or create an image.
    """
    if not message:
        return False, ""
    msg_clean = message.strip()
    msg_lower = msg_clean.lower()

    patterns = [
        r"^(?:generate|create|make|draw|paint|render)\s+(?:an?\s+)?(?:image|picture|photo|illustration|art|drawing)\s+(?:of|showing|about|with)?\s*(.+)$",
        r"^(?:generate|draw|paint|render)\s*:\s*(.+)$",
        r"^(?:image\s+of|photo\s+of|drawing\s+of)\s+(.+)$"
    ]

    for p in patterns:
        m = re.match(p, msg_lower, re.IGNORECASE)
        if m:
            extracted = msg_clean[m.start(1):m.end(1)].strip()
            return True, extracted if extracted else msg_clean

    return False, ""


def route_model(message, attachments=None, requested_model=None):
    """
    Intelligent Model Router.
    Selects the optimal model and task category based on input signals.
    """
    if requested_model and requested_model in AVAILABLE_MODELS:
        return requested_model, "user_selected"

    # Inspect attachments
    has_image = any(a.get("type") == "image" for a in (attachments or []))
    has_doc = any(a.get("type") in ["pdf", "docx", "doc", "txt", "md"] for a in (attachments or []))
    has_sheet = any(a.get("type") in ["xlsx", "xls", "csv"] for a in (attachments or []))

    msg_lower = message.lower()

    # Coding / Math intent
    code_keywords = ["def ", "class ", "function", "sql", "bug", "error", "traceback", "regex", "python", "javascript", "refactor", "algorithm", "math", "calculate", "prove", "theorem"]
    if any(k in msg_lower for k in code_keywords):
        return "gemini-2.5-pro", "coding_math"

    # Multimodal / Vision
    if has_image or "image" in msg_lower or "photo" in msg_lower or "diagram" in msg_lower or "ocr" in msg_lower:
        return "gemini-3.7-flash" if "gemini-3.7-flash" in AVAILABLE_MODELS else "gemini-2.5-flash", "vision"

    # Complex Documents
    if has_doc or "pdf" in msg_lower or "document" in msg_lower:
        return "gemini-2.5-flash", "document"

    # Spreadsheets
    if has_sheet or "excel" in msg_lower or "csv" in msg_lower or "spreadsheet" in msg_lower or "sales" in msg_lower or "revenue" in msg_lower:
        return "gemini-2.5-flash", "spreadsheet"

    return DEFAULT_MODEL, "general"


def build_system_prompt(task_category, user_preferred_lang="auto", detected_lang="en", has_docs=False):
    """
    Constructs a comprehensive system instruction covering formatting, citations, code, and language.
    """
    lang_directive = build_multilingual_system_instruction(user_preferred_lang, detected_lang)

    base_prompt = f"""
You are OG, a state-of-the-art Multimodal AI Assistant.
You provide intelligent, accurate, helpful, and beautifully structured responses.

Core Directives:
1. Formatting: Use GitHub Flavored Markdown. Use clear headings, bullet points, bold key terms, tables, and blockquotes where appropriate.
2. Code Blocks: For code, always specify the language (e.g. ```python, ```javascript, ```sql) and write clean, commented, production-quality code.
3. Mathematics: Render mathematical formulas using LaTeX notation (e.g., $E=mc^2$ or $$x = \\frac{{-b \\pm \\sqrt{{b^2 - 4ac}}}}{{2a}}$$).
4. Document Citations: When answering based on uploaded document context, ALWAYS cite your source using the exact format `[Page X]` or `[DocName, Page X]`. Never fabricate citations.
5. Tone: Professional, articulate, friendly, and objective.

{lang_directive}
"""

    if task_category == "vision":
        base_prompt += """
Vision & Image Analysis Directives:
- Provide rich, detailed visual explanations.
- Identify objects, text, layouts, visual relationships, color palettes, and diagram logic.
- If asked about authenticity, explain observations probabilistically (lighting, textures, anatomy, EXIF, artifacts) without making absolute claims.
"""
    elif task_category == "spreadsheet":
        base_prompt += """
Data Analytics Directives:
- Provide clear statistical insights, identify trends, key metrics, and anomalies.
- Format tabular comparisons with markdown tables.
- Suggest key takeaways and actionable business/analytical conclusions.
"""

    return base_prompt.strip()


def extract_citations(text):
    """
    Extracts citations from AI text response (e.g., '[Page 3]', '[Report.pdf, Page 12]').
    """
    citations = []
    matches = re.findall(r'\[(?:Source:\s*)?([^\]]*?Page\s*(\d+)[^\]]*?)\]', text, re.IGNORECASE)
    seen = set()
    for full_match, page_num in matches:
        key = (full_match.strip(), int(page_num))
        if key not in seen:
            seen.add(key)
            citations.append({
                "label": full_match.strip(),
                "page": int(page_num)
            })
    return citations


def process_user_query(
    message,
    conversation_history=None,
    attachments=None,
    model_name=None,
    user_preferred_lang="auto",
    custom_api_key=None,
    stream=False
):
    """
    Central pipeline for handling a multimodal chat request.
    """
    # 0. Check for Image Generation intent
    is_img_gen, img_prompt = is_image_generation_query(message)
    if is_img_gen and not attachments:
        gen_res = generate_image_ai(img_prompt or message, custom_api_key=custom_api_key)
        if gen_res.get("success"):
            img_url = gen_res.get("image_url")
            img_md = f"### 🎨 Generated Artwork\n\n**Prompt:** *\"{img_prompt or message}\"*\n\n![{img_prompt}]({img_url})\n\n<a href=\"{img_url}\" download=\"{gen_res.get('filename')}\" class=\"msg-btn\" style=\"display: inline-flex; margin-top: 10px;\">⬇️ Download Image</a>"
        else:
            img_md = f"⚠️ Could not generate image: {gen_res.get('error', 'Unknown error')}"

        if stream:
            def _img_stream_gen():
                yield {"token": img_md, "full_text": img_md, "done": True, "citations": []}
            return _img_stream_gen(), "imagen-3.0-generate-002", None, None
        else:
            return {
                "response": img_md,
                "model": "imagen-3.0-generate-002",
                "citations": [],
                "chart_data": None,
                "forensics": None,
                "detected_language": "en",
                "error": not gen_res.get("success")
            }

    # 0.1 Check for Resume Generation intent
    is_res_gen, res_prompt = is_resume_generation_query(message)
    if is_res_gen and not attachments:
        res_obj = generate_professional_resume(
            {"target_role": res_prompt or "Software Engineer", "skills": "System Architecture, Python, Cloud, Full-Stack", "name": "Candidate"},
            custom_api_key=custom_api_key
        )
        docx_url = res_obj.get("docx_url", "")
        resume_md = f"### 📝 Generated ATS-Optimized Resume\n\n**Role Target:** *{res_prompt}*\n\n<a href=\"{docx_url}\" download class=\"msg-btn btn-compare\" style=\"display: inline-flex; margin: 10px 0 16px;\">⬇️ Download Word Resume (.docx)</a>\n\n---\n\n{res_obj.get('markdown', '')}"

        if stream:
            def _res_stream_gen():
                yield {"token": resume_md, "full_text": resume_md, "done": True, "citations": []}
            return _res_stream_gen(), "gemini-2.5-flash", None, None
        else:
            return {
                "response": resume_md,
                "model": "gemini-2.5-flash",
                "citations": [],
                "chart_data": None,
                "forensics": None,
                "detected_language": "en",
                "error": False
            }

    detected_lang = detect_language(message)
    selected_model, task_cat = route_model(message, attachments, model_name)
    system_instruction = build_system_prompt(task_cat, user_preferred_lang, detected_lang, bool(attachments))

    # Process attachments for context & images
    image_paths = []
    rag_chunks = []
    sheet_context = ""
    chart_data = None
    forensics_data = None

    if attachments:
        for att in attachments:
            file_path = att.get("file_path", "")
            file_type = att.get("type", "")
            if not os.path.exists(file_path):
                continue

            if file_type == "image":
                image_paths.append(file_path)
                if any(w in message.lower() for w in ["real", "fake", "ai generated", "manipulated", "authentic", "forensic", "detect"]):
                    forensics_data = perform_image_forensics(file_path)

            elif file_type == "pdf":
                pdf_data = extract_pdf_data(file_path)
                chunks = chunk_pdf_pages(pdf_data["pages"])
                for c in chunks:
                    c["doc_name"] = os.path.basename(file_path)
                rag_chunks.extend(chunks)

            elif file_type in ["docx", "doc", "txt", "md", "rtf"]:
                doc_data = extract_document_data(file_path)
                words = doc_data["full_text"].split()
                step = 600
                for i in range(0, len(words), step):
                    chunk_text = " ".join(words[i:i+step])
                    rag_chunks.append({
                        "page": (i // step) + 1,
                        "text": chunk_text,
                        "doc_name": os.path.basename(file_path),
                        "content": chunk_text
                    })

            elif file_type in ["xlsx", "xls", "csv"]:
                sheet_info = analyze_spreadsheet(file_path)
                sheet_context += f"\n--- Spreadsheet Analysis ({sheet_info['filename']}) ---\n"
                sheet_context += f"Rows: {sheet_info['row_count']}, Columns: {sheet_info['column_count']}\n"
                sheet_context += f"Columns: {', '.join(sheet_info['columns'])}\n"
                sheet_context += f"Missing Values: {sheet_info['missing_values']}\n"
                sheet_context += f"Summary Statistics: {json.dumps(sheet_info['summary_statistics'])}\n"
                sheet_context += f"Categorical Summary: {json.dumps(sheet_info['categorical_summary'])}\n"
                if sheet_info.get("suggested_charts"):
                    chart_data = sheet_info["suggested_charts"][0]

    # Perform RAG retrieval if document chunks exist
    context_text = ""
    if rag_chunks:
        relevant = compute_tf_idf_similarity(message, rag_chunks, top_k=6)
        context_text = build_rag_context_prompt(relevant)

    # Build messages array for Gemini
    gemini_messages = []
    
    # Add history
    if conversation_history:
        for prev in conversation_history[-8:]:
            gemini_messages.append({
                "sender": prev.get("sender", "user"),
                "content": prev.get("content", "")
            })

    # Prepare current prompt with context
    current_prompt_parts = []
    if sheet_context:
        current_prompt_parts.append(sheet_context)
    if context_text:
        current_prompt_parts.append(context_text)
    if forensics_data:
        current_prompt_parts.append(f"Image Forensic Indicators: AI Probability: {forensics_data['ai_probability']}%, Classification: {forensics_data['classification']}, Signals: {json.dumps(forensics_data['signals'])}")
    
    current_prompt_parts.append(message)
    full_current_prompt = "\n\n".join(current_prompt_parts)

    gemini_messages.append({"sender": "user", "content": full_current_prompt})

    if stream:
        return stream_chat_response(
            messages=gemini_messages,
            system_instruction=system_instruction,
            model_name=selected_model,
            images=image_paths,
            custom_api_key=custom_api_key
        ), selected_model, chart_data, forensics_data
    else:
        resp = generate_chat_response(
            messages=gemini_messages,
            system_instruction=system_instruction,
            model_name=selected_model,
            images=image_paths,
            custom_api_key=custom_api_key
        )
        citations = extract_citations(resp["text"])
        return {
            "response": resp["text"],
            "model": selected_model,
            "citations": citations,
            "chart_data": chart_data,
            "forensics": forensics_data,
            "detected_language": detected_lang,
            "error": resp.get("error", False)
        }


def get_ai_response(message):
    """
    Legacy compatibility wrapper for existing code.
    """
    res = process_user_query(message, stream=False)
    return res["response"]
