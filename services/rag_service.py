import math
import re
import logging
from collections import Counter

logger = logging.getLogger(__name__)

def tokenize(text):
    """Simple alphanumeric tokenizer."""
    return re.findall(r'\w+', text.lower())


def compute_tf_idf_similarity(query, chunks, top_k=5):
    """
    Computes TF-IDF vector cosine similarity between a query and a list of document chunks.
    Each chunk is a dict: {"chunk_id": str, "page_number": int, "content": str, "metadata": dict, "doc_name": str}
    Returns top_k most relevant chunks with similarity score.
    """
    if not chunks:
        return []

    query_tokens = tokenize(query)
    if not query_tokens:
        return chunks[:top_k]

    # Build corpus word document frequencies
    num_docs = len(chunks)
    doc_freq = Counter()
    chunk_token_counts = []

    for chunk in chunks:
        tokens = tokenize(chunk.get("content", ""))
        chunk_token_counts.append(Counter(tokens))
        for token in set(tokens):
            doc_freq[token] += 1

    # IDF for each word
    idf = {}
    for word, freq in doc_freq.items():
        idf[word] = math.log((num_docs + 1) / (freq + 1)) + 1.0

    # Query vector
    query_counts = Counter(query_tokens)
    query_vec = {}
    query_norm_sq = 0.0
    for word, count in query_counts.items():
        weight = count * idf.get(word, 1.0)
        query_vec[word] = weight
        query_norm_sq += weight ** 2
    query_norm = math.sqrt(query_norm_sq) or 1.0

    # Score each chunk
    scored_chunks = []
    for i, chunk in enumerate(chunks):
        counts = chunk_token_counts[i]
        chunk_norm_sq = 0.0
        dot_product = 0.0

        for word, count in counts.items():
            word_idf = idf.get(word, 1.0)
            chunk_weight = (count / (len(counts) + 1)) * word_idf
            chunk_norm_sq += chunk_weight ** 2
            if word in query_vec:
                dot_product += query_vec[word] * chunk_weight

        chunk_norm = math.sqrt(chunk_norm_sq) or 1.0
        similarity = dot_product / (query_norm * chunk_norm)

        scored_chunks.append({
            "chunk": chunk,
            "score": round(similarity, 4),
            "page_number": chunk.get("page_number", 1),
            "content": chunk.get("content", ""),
            "doc_name": chunk.get("doc_name", "Document")
        })

    # Sort descending by score
    scored_chunks.sort(key=lambda x: x["score"], reverse=True)
    return scored_chunks[:top_k]


def build_rag_context_prompt(relevant_chunks, max_words=3000):
    """
    Builds structured RAG context block with page numbers and document names for citation generation.
    """
    if not relevant_chunks:
        return ""

    context_parts = ["=== RETRIEVED DOCUMENT CONTEXT ==="]
    total_words = 0

    for item in relevant_chunks:
        chunk = item.get("chunk", item)
        doc_name = item.get("doc_name") or chunk.get("doc_name") or "Document"
        page_num = item.get("page_number") or chunk.get("page_number") or 1
        content = item.get("content") or chunk.get("content") or ""

        words = content.split()
        if total_words + len(words) > max_words:
            # Add truncated snippet
            remaining = max_words - total_words
            if remaining > 30:
                truncated = " ".join(words[:remaining]) + "..."
                context_parts.append(f"[{doc_name} | Page {page_num}]\n{truncated}\n")
            break

        context_parts.append(f"[{doc_name} | Page {page_num}]\n{content}\n")
        total_words += len(words)

    context_parts.append("=== END OF CONTEXT ===")
    return "\n".join(context_parts)
