import json
import logging
from flask import Blueprint, request, jsonify, session, Response, stream_with_context
from config import get_current_api_key
from models import (
    get_user_by_email,
    get_user_conversations,
    create_conversation,
    update_conversation,
    delete_conversation,
    get_conversation_messages,
    save_message
)
from services.ai_service import process_user_query, get_ai_response

logger = logging.getLogger(__name__)
chat_bp = Blueprint("chat", __name__)


@chat_bp.route("/chat", methods=["POST"])
def legacy_chat():
    """
    Backward-compatible legacy chat endpoint for existing scripts or direct API calls.
    """
    data = request.get_json() or {}
    message = data.get("message", "")
    if not message:
        return jsonify({"response": "Please provide a valid message."})

    user_email = session.get("email")
    user_record = get_user_by_email(user_email) if user_email else None
    conv_id = data.get("conversation_id")
    custom_api_key = (
        data.get("api_key")
        or session.get("gemini_api_key")
        or (user_record.get("api_key") if user_record else "")
        or get_current_api_key()
        or ""
    ).strip()

    # If in session and no conversation, create or use one
    if user_email and not conv_id:
        conv_id = create_conversation(user_email, title=message[:40] + ("..." if len(message) > 40 else ""))

    result = process_user_query(
        message=message,
        attachments=data.get("attachments"),
        model_name=data.get("model"),
        user_preferred_lang=session.get("preferred_lang", "auto"),
        custom_api_key=custom_api_key,
        stream=False
    )

    if user_email and conv_id:
        save_message(conv_id, "user", message, attachments=data.get("attachments"))
        save_message(
            conv_id,
            "ai",
            result["response"],
            citations=result.get("citations"),
            chart_data=result.get("chart_data"),
            forensics=result.get("forensics")
        )

    return jsonify({
        "response": result["response"],
        "conversation_id": conv_id,
        "model": result["model"],
        "citations": result.get("citations", []),
        "chart_data": result.get("chart_data"),
        "forensics": result.get("forensics")
    })


@chat_bp.route("/api/chat/stream", methods=["POST"])
def stream_chat():
    """
    Server-Sent Events (SSE) streaming chat endpoint with real-time tokens, citations, and metadata.
    """
    data = request.get_json() or {}
    message = data.get("message", "").strip()
    conv_id = data.get("conversation_id")
    attachments = data.get("attachments", [])
    model_name = data.get("model")

    user_email = session.get("email", "guest@chatbot.local")
    user_record = get_user_by_email(user_email) if user_email and user_email != "guest@chatbot.local" else None
    
    custom_api_key = (
        data.get("api_key")
        or session.get("gemini_api_key")
        or (user_record.get("api_key") if user_record else "")
        or get_current_api_key()
        or ""
    ).strip()


    if not message and not attachments:
        return jsonify({"error": "Message or attachment is required"}), 400

    # If no conversation ID, create a new conversation thread
    if not conv_id:
        title_text = message[:40] if message else (attachments[0].get("name", "New Chat") if attachments else "New Chat")
        conv_id = create_conversation(user_email, title=title_text, model=model_name or "gemini-2.5-flash")

    # Fetch prior conversation history
    history = get_conversation_messages(conv_id) if conv_id else []

    # Save user message to database
    save_message(conv_id, "user", message or "Attached file(s) for analysis", attachments=attachments)

    generator, selected_model, chart_data, forensics_data = process_user_query(
        message=message or "Please analyze and summarize the attached file(s).",
        conversation_history=history,
        attachments=attachments,
        model_name=model_name,
        user_preferred_lang=session.get("preferred_lang", "auto"),
        custom_api_key=custom_api_key,
        stream=True
    )

    def sse_wrapper():
        full_ai_response = []
        # Send initial event with conversation ID and metadata
        init_payload = {
            "conversation_id": conv_id,
            "model": selected_model,
            "chart_data": chart_data,
            "forensics": forensics_data
        }
        yield f"data: {json.dumps({'type': 'init', 'data': init_payload})}\n\n"

        for sse_event in generator:
            if sse_event.startswith("data: "):
                try:
                    payload = json.loads(sse_event[6:].strip())
                    chunk_text = payload.get("chunk", "")
                    if chunk_text:
                        full_ai_response.append(chunk_text)
                except Exception:
                    pass
            yield sse_event

        # Save AI message to DB upon completion
        complete_text = "".join(full_ai_response)
        if complete_text and conv_id:
            try:
                save_message(
                    conv_id,
                    "ai",
                    complete_text,
                    chart_data=chart_data,
                    forensics=forensics_data
                )
            except Exception as e:
                logger.warning("Could not save message: %s", e)

    response = Response(stream_with_context(sse_wrapper()), mimetype="text/event-stream")
    response.headers["Content-Type"] = "text/event-stream; charset=utf-8"
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    return response


@chat_bp.route("/api/conversations", methods=["GET", "POST"])
def conversations():
    user_email = session.get("email")
    if not user_email:
        return jsonify({"error": "Unauthorized"}), 401

    if request.method == "GET":
        convs = get_user_conversations(user_email)
        return jsonify({"conversations": convs})

    elif request.method == "POST":
        data = request.get_json() or {}
        title = data.get("title", "New Conversation")
        model = data.get("model", "gemini-2.5-flash")
        conv_id = create_conversation(user_email, title=title, model=model)
        return jsonify({"conversation_id": conv_id, "title": title, "model": model})


@chat_bp.route("/api/conversations/<conv_id>", methods=["GET", "PUT", "DELETE"])
def single_conversation(conv_id):
    user_email = session.get("email")
    if not user_email:
        return jsonify({"error": "Unauthorized"}), 401

    if request.method == "GET":
        messages = get_conversation_messages(conv_id)
        return jsonify({"conversation_id": conv_id, "messages": messages})

    elif request.method == "PUT":
        data = request.get_json() or {}
        title = data.get("title")
        is_pinned = data.get("is_pinned")
        model = data.get("model")
        update_conversation(conv_id, title=title, is_pinned=is_pinned, model=model)
        return jsonify({"success": True})

    elif request.method == "DELETE":
        delete_conversation(conv_id)
        return jsonify({"success": True})


@chat_bp.route("/api/conversations/<conv_id>/messages", methods=["GET"])
def conversation_messages(conv_id):
    user_email = session.get("email")
    if not user_email:
        return jsonify({"error": "Unauthorized"}), 401

    messages = get_conversation_messages(conv_id)
    return jsonify({"messages": messages})
