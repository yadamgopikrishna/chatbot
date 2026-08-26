import os
from flask import Blueprint, request, jsonify, session
from config import (
    AVAILABLE_MODELS,
    DEFAULT_MODEL,
    SUPPORTED_LANGUAGES,
    get_current_api_key,
    save_api_key_to_env
)
from models import get_user_by_email, update_user_api_key
from db import db_cursor, is_oracle

settings_bp = Blueprint("settings", __name__)


@settings_bp.route("/api/settings", methods=["GET", "POST"])
def settings():
    user_email = session.get("email")

    if request.method == "GET":
        current_key = get_current_api_key() or session.get("gemini_api_key", "")
        has_key = bool(current_key and len(current_key) > 8)
        masked_key = ""
        if has_key:
            masked_key = current_key[:6] + "..." + current_key[-4:]

        return jsonify({
            "models": AVAILABLE_MODELS,
            "default_model": DEFAULT_MODEL,
            "languages": SUPPORTED_LANGUAGES,
            "user_settings": {
                "preferred_lang": session.get("preferred_lang", "auto"),
                "theme": session.get("theme", "dark"),
                "has_api_key": has_key,
                "masked_api_key": masked_key
            }
        })

    elif request.method == "POST":
        data = request.get_json() or {}
        preferred_lang = data.get("preferred_lang")
        theme = data.get("theme")
        api_key = data.get("api_key", "").strip()

        if preferred_lang:
            session["preferred_lang"] = preferred_lang
        if theme:
            session["theme"] = theme
        if api_key:
            clean = api_key.strip().strip('"').strip("'")
            session["gemini_api_key"] = clean
            save_api_key_to_env(clean)
            if user_email:
                try:
                    update_user_api_key(user_email, clean)
                except Exception:
                    pass


        # Update DB if user logged in
        if user_email:
            try:
                with db_cursor(commit=True) as (cursor, conn):
                    if is_oracle():
                        if preferred_lang:
                            cursor.execute("UPDATE users SET preferred_lang = :1 WHERE email = :2", (preferred_lang, user_email))
                        if theme:
                            cursor.execute("UPDATE users SET theme = :1 WHERE email = :2", (theme, user_email))
                    else:
                        if preferred_lang:
                            cursor.execute("UPDATE users SET preferred_lang = ? WHERE email = ?", (preferred_lang, user_email))
                        if theme:
                            cursor.execute("UPDATE users SET theme = ? WHERE email = ?", (theme, user_email))
            except Exception:
                pass

        return jsonify({"success": True, "message": "Settings and API Key updated successfully."})
