# 🌟 OG AI — Production Multimodal AI Assistant

[![OG AI CI Pipeline](https://github.com/yadamgopikrishna/chatbot/actions/workflows/ci.yml/badge.svg)](https://github.com/yadamgopikrishna/chatbot/actions/workflows/ci.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Google GenAI SDK](https://img.shields.io/badge/Google%20GenAI-v2.0-8a2be2.svg)](https://ai.google.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**OG AI** is a production-grade, multimodal AI assistant designed for seamless text, document intelligence, spreadsheet analytics, image forensics, AI artwork generation, and multilingual interactions.

---

## ✨ Features & Capabilities

- ⚡ **Next-Gen AI Models**: Powered by the modern `google-genai` SDK with real-time SSE streaming across `gemini-2.5-flash`, `gemini-3.7-flash`, and `gemini-2.5-pro`.
- 🎨 **AI Image Generation**: Built-in **Imagen 3.0** (`imagen-3.0-generate-002`) studio modal and automatic prompt detection (`"draw a futuristic city"`).
- 📄 **Document Intelligence (RAG)**: Multi-page PDF and Word (`.docx`) understanding with page-level citations (`[Page 3]`).
- ⚖️ **Document Semantic Comparison**: Side-by-side section diffs, clause comparisons, and similarity scoring.
- 📊 **Spreadsheet Analytics**: Natural language queries on CSV/Excel files with interactive **Chart.js** visualizations.
- 🔍 **Image Forensics & Authenticity**: Multilingual OCR, metadata inspection, and AI manipulation probability detection.
- 🌐 **Multilingual Engine**: Native support for **Telugu (తెలుగు)**, **Hindi (हिन्दी)**, **Tamil (தமிழ்)**, **Spanish**, **French**, **German**, and **English**.
- 🎙️ **Voice Integration**: Hands-free voice input and speech synthesis via Web Speech API.
- 🌓 **Adaptive Dual Theme**: Razor-sharp, high-contrast **Dark Mode** and crisp **Light Mode** with Google Fonts (*Poppins & Inter*).
- 🗄️ **Flexible Database Architecture**: Native **Oracle Database 11g/19c/23c** (Thick Mode) with zero-configuration **SQLite** fallback.

---

## 🚀 Live Deployment Options

### Option 1: Deploy on Render (Recommended & Free)

1. Fork or push this repository to your GitHub account (`https://github.com/yadamgopikrishna/chatbot`).
2. Log in to [Render.com](https://render.com/) and click **New +** → **Web Service**.
3. Connect your GitHub repository `yadamgopikrishna/chatbot`.
4. Render will automatically detect `render.yaml` and configure:
   - **Environment**: `Python`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app --workers 2 --threads 4 --timeout 120 --bind 0.0.0.0:$PORT`
5. In the **Environment Variables** tab, add:
   - `GEMINI_API_KEY` = *Your Google AI Studio Key*
   - `DB_TYPE` = `sqlite`
6. Click **Deploy Web Service**!

---

### Option 2: Deploy with Docker

```bash
# 1. Clone repository
git clone https://github.com/yadamgopikrishna/chatbot.git
cd chatbot

# 2. Configure environment
cp .env.example .env
# Edit .env with your GEMINI_API_KEY

# 3. Build & run with Docker Compose
docker compose up -d --build
```

Access the app at: **`http://localhost:5000`**

---

### Option 3: Deploy on Railway / Heroku

1. Connect your GitHub repository.
2. The included `Procfile` will automatically execute `gunicorn`.
3. Add `GEMINI_API_KEY` and `DB_TYPE=sqlite` in service variables.

---

### Option 4: Local Development

```bash
# 1. Clone the repository
git clone https://github.com/yadamgopikrishna/chatbot.git
cd chatbot

# 2. Create virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env

# 5. Run the application
python app.py
```

Open **`http://127.0.0.1:5000`** in your browser.

---

## 🛠️ Environment Configuration (`.env`)

```ini
# Google Gemini AI API Key (https://aistudio.google.com/)
GEMINI_API_KEY=your_gemini_api_key_here

# Database Selection: 'sqlite' or 'oracle'
DB_TYPE=sqlite

# Oracle Database Configuration (optional if using SQLite)
ORACLE_USER=yadam
ORACLE_PASSWORD=gopi
ORACLE_DSN=localhost:1521/XE
ORACLE_CLIENT_DIR=g:\chatbot\instantclient_19_31

# Flask Session Key
SECRET_KEY=production-secret-key
```

---

## 🧪 Automated Testing

Run the full multimodal test suite:

```bash
python test_multimodal_app.py
```

Run end-to-end integration tests:

```bash
python test_multimodal_e2e.py
```

---

## 📁 Project Architecture

```
chatbot/
├── .github/workflows/ci.yml     # Automated CI/CD pipeline
├── routes/                      # Modular Flask blueprint controllers
│   ├── auth_routes.py           # User registration & session auth
│   ├── chat_routes.py           # SSE Streaming & multi-turn chat
│   ├── document_routes.py       # PDF/Word parser & semantic comparison
│   ├── image_routes.py          # Vision, OCR, forensics & Image Gen
│   ├── spreadsheet_routes.py    # Excel/CSV stats & Chart.js engine
│   └── settings_routes.py       # API key & preference management
├── services/                    # Core business logic & AI pipelines
│   ├── ai_service.py            # Central intent router & RAG engine
│   ├── gemini_client.py         # Google GenAI SDK wrapper
│   ├── image_gen_service.py     # Imagen 3.0 image generation
│   ├── pdf_service.py           # PyPDF text extractor & chunker
│   ├── doc_service.py           # Word parser & diff engine
│   ├── spreadsheet_service.py   # Pandas summary & analytics
│   ├── vision_service.py        # Forensics & image metadata
│   ├── ocr_service.py           # Multilingual OCR prompt engine
│   ├── rag_service.py           # TF-IDF semantic vector search
│   └── translation_service.py   # Multi-language detector & adapter
├── static/
│   ├── css/                     # Clean design system & themes
│   └── js/                      # Interactive client modules
├── templates/                   # Semantic HTML5 templates
├── app.py                       # Application entry point
├── config.py                    # Environment & configuration loader
├── db.py                        # Database connection factory
├── models.py                    # Database schema & migrations
├── Dockerfile                   # Production container definition
├── render.yaml                  # 1-click cloud deployment manifest
└── Procfile                     # WSGI server process definition
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
