import os
import sys
from pathlib import Path

# Ensure UTF-8 console output and Oracle client UTF-8 encoding
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

os.environ["NLS_LANG"] = "AMERICAN_AMERICA.AL32UTF8"
os.environ["PYTHONIOENCODING"] = "utf-8"

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

# Load .env file if present
load_dotenv(dotenv_path=ENV_PATH)

def reload_env():
    """Reloads environment variables from .env."""
    load_dotenv(dotenv_path=ENV_PATH, override=True)

def save_api_key_to_env(api_key):
    """Persists API key to .env file."""
    api_key = str(api_key).strip().strip('"').strip("'")
    lines = []
    found = False
    
    if ENV_PATH.exists():
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
    new_lines = []
    for line in lines:
        if line.strip().startswith("GEMINI_API_KEY=") or line.strip().startswith("GOOGLE_API_KEY="):
            new_lines.append(f"GEMINI_API_KEY={api_key}\n")
            found = True
        else:
            new_lines.append(line)
            
    if not found:
        new_lines.append(f"\nGEMINI_API_KEY={api_key}\n")
        
    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
        
    os.environ["GEMINI_API_KEY"] = api_key
    os.environ["GOOGLE_API_KEY"] = api_key
    reload_env()

# Oracle Instant Client auto-discovery
DEFAULT_CLIENT_PATHS = [
    str(BASE_DIR / "instantclient_19_31"),
    r"C:\Users\gopik\OneDrive\Desktop\chatbot\instantclient_19_31",
    r"C:\oracle\instantclient_19_31",
]

ORACLE_CLIENT_DIR = os.getenv("ORACLE_CLIENT_DIR")
if not ORACLE_CLIENT_DIR:
    for path in DEFAULT_CLIENT_PATHS:
        if os.path.exists(path):
            ORACLE_CLIENT_DIR = path
            break

# Database settings
DB_TYPE = os.getenv("DB_TYPE", "oracle")  # "oracle" with automatic sqlite fallback
ORACLE_USER = os.getenv("ORACLE_USER", "yadam")
ORACLE_PASSWORD = os.getenv("ORACLE_PASSWORD", "gopi")
ORACLE_DSN = os.getenv("ORACLE_DSN", "localhost:1521/XE")
SQLITE_DB_PATH = str(BASE_DIR / "database" / "chatbot.db")

# Flask Security & Session
SECRET_KEY = os.getenv("SECRET_KEY", "multimodal-ai-assistant-secret-key-2026-secure")

# AI & Gemini API Settings
def get_current_api_key():
    return (
        os.getenv("GEMINI_API_KEY", "").strip()
        or os.getenv("GOOGLE_API_KEY", "").strip()
    )

GEMINI_API_KEY = get_current_api_key()

AVAILABLE_MODELS = {
    "gemini-2.5-flash": {
        "name": "Gemini 2.5 Flash",
        "badge": "Balanced & Fast",
        "description": "Recommended for general chat, vision, quick document queries, and everyday tasks.",
        "category": "balanced",
        "is_default": True
    },
    "gemini-3.7-flash": {
        "name": "Gemini 3.7 Flash",
        "badge": "Latest Agentic",
        "description": "State-of-the-art fast reasoning model for multimodal and agentic tasks.",
        "category": "advanced",
        "is_default": False
    },
    "gemini-2.5-pro": {
        "name": "Gemini 2.5 Pro",
        "badge": "Deep Reasoning",
        "description": "Best for complex document analysis, multi-step math, research, and deep code refactoring.",
        "category": "reasoning",
        "is_default": False
    },
    "gemini-3.5-flash-lite": {
        "name": "Gemini 3.5 Flash Lite",
        "badge": "Ultra Fast",
        "description": "Ultra-fast low-latency responses for quick translations and short questions.",
        "category": "fast",
        "is_default": False
    }
}

DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gemini-2.5-flash")

# Upload and Storage configurations
UPLOAD_FOLDER = str(BASE_DIR / "uploads")
ALLOWED_DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt", ".rtf", ".md"}
ALLOWED_SPREADSHEET_EXTENSIONS = {".xlsx", ".xls", ".csv"}
ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}
ALL_ALLOWED_EXTENSIONS = (
    ALLOWED_DOCUMENT_EXTENSIONS
    | ALLOWED_SPREADSHEET_EXTENSIONS
    | ALLOWED_IMAGE_EXTENSIONS
)

MAX_CONTENT_LENGTH = 30 * 1024 * 1024  # 30 MB maximum upload size

# Multilingual configurations
SUPPORTED_LANGUAGES = {
    "auto": "Auto-Detect (ఆటోమేటిక్)",
    "en": "English",
    "te": "Telugu (తెలుగు)",
    "hi": "Hindi (हिन्दी)",
    "ta": "Tamil (தமிழ்)",
    "kn": "Kannada (ಕನ್ನಡ)",
    "ml": "Malayalam (മലയാളം)",
    "bn": "Bengali (বাংলা)",
    "mr": "Marathi (मराठी)",
    "gu": "Gujarati (ગુજરાતી)",
    "ur": "Urdu (اردو)",
    "pa": "Punjabi (ਪੰਜਾਬੀ)",
    "es": "Spanish (Español)",
    "fr": "French (Français)",
    "de": "German (Deutsch)",
    "pt": "Portuguese (Português)",
    "ar": "Arabic (العربية)",
    "zh": "Chinese (中文)",
    "ja": "Japanese (日本語)",
    "ko": "Korean (한국어)"
}

# Ensure upload and database folders exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(str(BASE_DIR / "database"), exist_ok=True)
