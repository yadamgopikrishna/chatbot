import os
import io
import json
import pytest
from app import app
from models import (
    get_user_by_email,
    create_conversation,
    save_message,
    get_conversation_messages,
    save_document,
    get_user_documents
)
from services.pdf_service import extract_pdf_data, chunk_pdf_pages
from services.doc_service import compare_documents
from services.spreadsheet_service import analyze_spreadsheet
from services.vision_service import perform_image_forensics
from services.translation_service import detect_language
from services.rag_service import compute_tf_idf_similarity
from services.ai_service import is_image_generation_query, is_resume_generation_query
from services.resume_service import analyze_resume, generate_professional_resume, create_resume_docx
from PIL import Image
import pandas as pd

def test_database_and_auth():
    print("\n--- Testing Database & Auth ---")
    user = get_user_by_email("gopi1@gmail.com")
    assert user is not None
    assert user["email"] == "gopi1@gmail.com"
    print("User fetched successfully:", user["email"], user["name"])

    # Test conversation creation & message persistence
    conv_id = create_conversation("gopi1@gmail.com", title="Test Multimodal Chat")
    assert conv_id is not None
    print("Created Conversation ID:", conv_id)

    msg_id = save_message(conv_id, "user", "Hello Multimodal AI!")
    assert msg_id is not None

    messages = get_conversation_messages(conv_id)
    assert len(messages) >= 1
    print("Retrieved messages count:", len(messages))


def test_translation_and_language_detection():
    print("\n--- Testing Multilingual Language Detection ---")
    te_text = "ఈ PDF లో ముఖ్యమైన విషయాలు ఏమిటి?"
    hi_text = "इस दस्तावेज़ का सारांश क्या है?"
    en_text = "What does this document contain?"
    es_text = "Por favor explica este documento"

    assert detect_language(te_text) == "te"
    assert detect_language(hi_text) == "hi"
    assert detect_language(en_text) == "en"
    assert detect_language(es_text) == "es"
    print("Language detection passed for Telugu, Hindi, English, Spanish!")


def test_document_comparison():
    print("\n--- Testing Document Comparison Diff Engine ---")
    doc_a = "1. Introduction\nOur quarterly revenue grew by 15% to $4.2M.\n2. Conclusion\nThe project is on track."
    doc_b = "1. Introduction\nOur quarterly revenue grew by 22% to $5.1M.\n2. Conclusion\nThe project is exceeding targets with 5 new clients."

    comp = compare_documents(doc_a, doc_b, "Report_Q1.docx", "Report_Q2.docx")
    print("Comparison similarity:", comp["similarity_score"])
    print("Modified clauses:", len(comp["modified_sections"]))
    assert comp["similarity_score"] > 0
    assert len(comp["modified_sections"]) > 0


def test_spreadsheet_analysis():
    print("\n--- Testing Spreadsheet Analysis & Chart Generator ---")
    df = pd.DataFrame({
        "Month": ["Jan", "Feb", "Mar", "Apr", "May"],
        "Sales": [12000, 18500, 24000, 19500, 31000],
        "Category": ["Electronics", "Furniture", "Electronics", "Clothing", "Electronics"]
    })
    temp_csv = "uploads/test_sales.csv"
    df.to_csv(temp_csv, index=False)

    analysis = analyze_spreadsheet(temp_csv)
    print("Analyzed CSV rows:", analysis["row_count"])
    print("Summary stats columns:", list(analysis["summary_statistics"].keys()))
    print("Suggested charts count:", len(analysis["suggested_charts"]))

    assert analysis["row_count"] == 5
    assert "Sales" in analysis["summary_statistics"]
    assert len(analysis["suggested_charts"]) > 0
    os.remove(temp_csv)


def test_image_forensics():
    print("\n--- Testing Image Forensics Engine ---")
    img = Image.new("RGB", (1024, 1024), color=(73, 109, 137))
    temp_img = "uploads/test_img.png"
    img.save(temp_img)

    forensics = perform_image_forensics(temp_img)
    print("Forensics classification:", forensics["classification"])
    print("AI Probability:", forensics["ai_probability"])
    print("Forensic signals count:", len(forensics["signals"]))

    assert forensics["classification"] in ["Likely Authentic", "Likely AI-Generated", "Likely Manipulated", "Inconclusive"]
    os.remove(temp_img)


def test_image_generation_intent():
    print("\n--- Testing AI Image Generation Intent Detection ---")
    is_gen, prompt = is_image_generation_query("Generate an image of a cybernetic tiger in a neon rainforest")
    assert is_gen is True
    assert "tiger" in prompt
    print("Image generation intent detected correctly:", prompt)


def test_resume_analysis_and_generation():
    print("\n--- Testing Resume Analysis & Word Doc Generation ---")
    sample_resume = """
    John Doe
    john@example.com | +1 555 123 4567 | San Francisco, CA
    
    Professional Summary:
    Full-Stack Developer with 4 years of experience building Python and React applications.
    
    Skills:
    Python, Flask, JavaScript, React, SQL, Git, Docker
    
    Experience:
    Software Engineer at Tech Innovations (2021 - Present)
    - Developed backend APIs using Flask and PostgreSQL.
    - Improved page load speeds by 30%.
    """

    # 1. Test Analysis
    res_analysis = analyze_resume(sample_resume, target_role="Senior Full-Stack Engineer")
    assert res_analysis.get("success") is True
    assert "ats_score" in res_analysis
    assert "matched_skills" in res_analysis
    assert "bullet_improvements" in res_analysis
    print("ATS Score calculated:", res_analysis.get("ats_score"))
    print("Matched skills count:", len(res_analysis.get("matched_skills", [])))

    # 2. Test Generation
    gen_result = generate_professional_resume({
        "name": "Jane Smith",
        "target_role": "Senior Cloud Architect",
        "skills": "AWS, Kubernetes, Terraform, Python, Docker, Microservices",
        "experience": "Lead Architect at CloudSys (2020-Present)",
        "email": "jane@example.com"
    })
    assert gen_result.get("success") is True
    assert "docx_url" in gen_result
    assert os.path.exists(os.path.join("uploads", gen_result["filename"]))
    print("Generated Word Resume file:", gen_result["filename"])

    # 3. Test Intent detection
    is_res, role = is_resume_generation_query("Generate a resume for a Senior Cloud Architect")
    assert is_res is True
    assert "Cloud" in role


def test_rag_semantic_search():
    print("\n--- Testing RAG TF-IDF Semantic Retrieval ---")
    chunks = [
        {"content": "Groundwater contamination in region A is due to chemical runoff.", "page_number": 1, "doc_name": "Hydro.pdf"},
        {"content": "Solar cell efficiency reached 24.5 percent in laboratory trials.", "page_number": 2, "doc_name": "Energy.pdf"},
        {"content": "Deep learning models require balanced training sets.", "page_number": 3, "doc_name": "AI.pdf"}
    ]
    query = "groundwater chemical contamination"
    results = compute_tf_idf_similarity(query, chunks, top_k=1)
    print("Top retrieved chunk:", results[0]["content"])
    assert "groundwater" in results[0]["content"].lower()


def test_flask_endpoints():
    print("\n--- Testing Flask Endpoints ---")
    client = app.test_client()

    # Test login page
    resp = client.get("/")
    assert resp.status_code == 200
    print("GET / returned 200 OK")

    # Test settings API
    resp = client.get("/api/settings")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert "models" in data
    assert "languages" in data
    print("GET /api/settings returned models and languages correctly")

    # Test Resume analyze endpoint
    resp = client.post("/api/resume/analyze", json={
        "resume_text": "Alex Dev - Python, React, Docker. Software Engineer with 3 years experience.",
        "target_role": "Backend Engineer"
    })
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data.get("success") is True
    print("POST /api/resume/analyze returned 200 OK")

    # Test legacy chat API
    resp = client.post("/chat", json={"message": "Hello AI"})
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert "response" in data
    print("POST /chat legacy response received successfully")


if __name__ == "__main__":
    test_database_and_auth()
    test_translation_and_language_detection()
    test_document_comparison()
    test_spreadsheet_analysis()
    test_image_forensics()
    test_image_generation_intent()
    test_resume_analysis_and_generation()
    test_rag_semantic_search()
    test_flask_endpoints()
    print("\n=======================================================")
    print("ALL MULTIMODAL AI TESTS PASSED SUCCESSFULLY!")
    print("=======================================================")
