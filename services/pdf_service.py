import os
import re
import logging
from pypdf import PdfReader

logger = logging.getLogger(__name__)

def extract_pdf_data(file_path):
    """
    Extracts text, metadata, page breakdown, and scan-status from a PDF file.
    Returns structured dict:
    {
        "filename": str,
        "page_count": int,
        "metadata": dict,
        "pages": [{"page_num": int, "text": str, "word_count": int, "is_scanned": bool}],
        "full_text": str,
        "total_words": int,
        "has_scanned_pages": bool
    }
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    reader = PdfReader(file_path)
    page_count = len(reader.pages)
    
    # Extract metadata safely
    raw_meta = reader.metadata or {}
    meta = {
        "title": str(raw_meta.get("/Title", "") or ""),
        "author": str(raw_meta.get("/Author", "") or ""),
        "subject": str(raw_meta.get("/Subject", "") or ""),
        "creator": str(raw_meta.get("/Creator", "") or ""),
        "producer": str(raw_meta.get("/Producer", "") or ""),
        "pages": page_count
    }

    pages_data = []
    full_text_parts = []
    total_words = 0
    scanned_count = 0

    for idx, page in enumerate(reader.pages):
        page_num = idx + 1
        try:
            page_text = page.extract_text() or ""
        except Exception as e:
            logger.warning("Error extracting text from page %d: %s", page_num, e)
            page_text = ""

        # Clean text
        clean_text = re.sub(r'\s+', ' ', page_text).strip()
        word_count = len(clean_text.split()) if clean_text else 0
        total_words += word_count

        # Detect if page is likely scanned/image-only
        is_scanned = (word_count < 10)
        if is_scanned:
            scanned_count += 1

        pages_data.append({
            "page_num": page_num,
            "text": clean_text,
            "word_count": word_count,
            "is_scanned": is_scanned
        })
        
        if clean_text:
            full_text_parts.append(f"--- Page {page_num} ---\n{clean_text}")

    full_text = "\n\n".join(full_text_parts)

    return {
        "filename": os.path.basename(file_path),
        "page_count": page_count,
        "metadata": meta,
        "pages": pages_data,
        "full_text": full_text,
        "total_words": total_words,
        "has_scanned_pages": (scanned_count > 0)
    }


def chunk_pdf_pages(pages_data, chunk_size=800, overlap=100):
    """
    Chunks PDF text by pages while maintaining page attribution for citations.
    """
    chunks = []
    for p in pages_data:
        text = p["text"]
        page_num = p["page_num"]
        if not text:
            continue

        words = text.split()
        if len(words) <= chunk_size:
            chunks.append({
                "page": page_num,
                "text": text,
                "metadata": {"page": page_num, "word_count": len(words)}
            })
        else:
            # Sliding window over words
            start = 0
            while start < len(words):
                end = min(start + chunk_size, len(words))
                chunk_words = words[start:end]
                chunk_text = " ".join(chunk_words)
                chunks.append({
                    "page": page_num,
                    "text": chunk_text,
                    "metadata": {"page": page_num, "start_word": start, "end_word": end}
                })
                if end >= len(words):
                    break
                start += (chunk_size - overlap)

    return chunks


def search_pdf_content(pages_data, query):
    """
    Searches inside PDF pages for matching terms or phrases.
    """
    query_lower = query.lower()
    terms = query_lower.split()
    results = []

    for p in pages_data:
        text = p["text"]
        text_lower = text.lower()
        if query_lower in text_lower or any(t in text_lower for t in terms):
            # Extract snippet around match
            snippet = _extract_snippet(text, terms)
            results.append({
                "page_num": p["page_num"],
                "snippet": snippet,
                "word_count": p["word_count"]
            })

    return results


def _extract_snippet(text, terms, max_chars=200):
    """Helper to extract relevant text snippet."""
    text_lower = text.lower()
    best_pos = -1
    for t in terms:
        pos = text_lower.find(t)
        if pos != -1:
            best_pos = pos
            break
    if best_pos == -1:
        return text[:max_chars] + "..." if len(text) > max_chars else text
    
    start = max(0, best_pos - 80)
    end = min(len(text), best_pos + 120)
    snippet = text[start:end].strip()
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."
    return snippet
