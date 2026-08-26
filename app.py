import sys
import os

# Ensure UTF-8 console output and error handling on Windows
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import logging
from flask import Flask, render_template, session, redirect, send_from_directory, jsonify
from config import SECRET_KEY, UPLOAD_FOLDER, MAX_CONTENT_LENGTH
from models import init_db

# Configure logging with safe stream handler
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

from flask_cors import CORS

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = False

# Enable CORS for local & ngrok tunnels
CORS(app, supports_credentials=True, resources={r"/*": {"origins": "*"}})

@app.after_request
def add_ngrok_headers(response):
    response.headers["ngrok-skip-browser-warning"] = "true"
    return response

# Initialize database tables
try:
    init_db()
    logger.info("Database successfully initialized.")
except Exception as e:
    logger.warning("Database init notice: %s", e)


# Import & Register Blueprints
from routes.auth_routes import auth_bp
from routes.chat_routes import chat_bp
from routes.document_routes import document_bp
from routes.image_routes import image_bp
from routes.spreadsheet_routes import spreadsheet_bp
from routes.settings_routes import settings_bp
from routes.resume_routes import resume_bp

app.register_blueprint(auth_bp)
app.register_blueprint(chat_bp)
app.register_blueprint(document_bp)
app.register_blueprint(image_bp)
app.register_blueprint(spreadsheet_bp)
app.register_blueprint(settings_bp)
app.register_blueprint(resume_bp)


@app.route("/dashboard")
def dashboard():
    """Main dashboard page."""
    if "email" not in session:
        return redirect("/")
    return render_template(
        "dashboard.html",
        name=session.get("name", "User"),
        email=session.get("email", ""),
        preferred_lang=session.get("preferred_lang", "auto"),
        theme=session.get("theme", "dark")
    )


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    """Secure static file server for uploaded documents and images."""
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


# Error Handlers
@app.errorhandler(404)
def not_found_error(e):
    return jsonify({"error": "Resource not found"}), 404


@app.errorhandler(413)
def file_too_large(e):
    return jsonify({"error": "File size exceeds the 30MB maximum limit."}), 413


@app.errorhandler(500)
def internal_error(e):
    logger.error("Internal Server Error: %s", e)
    return jsonify({"error": "An internal server error occurred."}), 500


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)