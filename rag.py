"""
rag.py
Retrieval + prompt construction + local Ollama answering.

Cross-document fix chosen (see README, Stage 6 of the guide):
"Retrieve a fixed share from each document." Every question retrieves top_k chunks
from the review AND top_k chunks from the policy handbook separately (using the
doc_type metadata written during ingestion), then merges and sorts by similarity.
This guarantees that a question like "Kaveri Metals had 88.1% on-time delivery and
1,150 PPM - which clauses does this trigger?" always pulls in handbook clauses even
though the numbers themselves only appear in the review. Raising top_k alone was not
reliable enough for the assignment's specific cross-document questions, so the fixed
per-document share is used unconditionally rather than as a fallback.

Uses a local Ollama model instead of GPT-4o (see note in ingest.py on why).
"""

import os
from typing import List, Dict

import ollama
from dotenv import load_dotenv

from ingest import get_chroma_collection, EMBEDDING_MODEL

load_dotenv()

CHAT_MODEL = os.getenv("OLLAMA_CHAT_MODEL", "llama3.1:8b")
TEMPERATURE = 0.1
DEFAULT_TOP_K_PER_DOC = 3

SYSTEM_PROMPT = """You are an internal procurement assistant for Meridian Components Pvt. Ltd.

Answer only from the context provided below. If the context does not contain the answer,
say plainly that the information is not available in the uploaded documents. Do not use
outside knowledge of how procurement "usually" works, even if you are confident about it.

When a question requires combining a figure from the performance review with a rule from
the procurement policy handbook, state all three of the following explicitly:
1. The figure (with its source).
2. The exact policy clause it triggers (quote the clause number).
3. The resulting required action.

Keep answers concise and factual. Do not invent numbers, clause numbers, or names that do
not appear in the context."""


def embed_query(query: str) -> List[float]:
    resp = ollama.embed(model=EMBEDDING_MODEL, input=query)
    return resp["embeddings"][0]


def _query_by_doc_type(collection, query_vector, doc_type: str, top_k: int):
    try:
        return collection.query(
            query_embeddings=[query_vector],
            n_results=top_k,
            where={"doc_type": doc_type},
        )
    except Exception:
        return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}


def retrieve(question: str, top_k_per_doc: int = DEFAULT_TOP_K_PER_DOC) -> List[Dict]:
    """Retrieves top_k_per_doc chunks from each known document type and merges them,
    sorted by similarity distance (lower = closer)."""
    collection = get_chroma_collection()
    query_vector = embed_query(question)

    results = []
    for doc_type in ("review", "policy", "other"):
        res = _query_by_doc_type(collection, query_vector, doc_type, top_k_per_doc)
        ids = res.get("ids", [[]])[0]
        docs = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        dists = res.get("distances", [[]])[0]
        for i in range(len(ids)):
            results.append({
                "id": ids[i],
                "text": docs[i],
                "filename": metas[i]["filename"],
                "page": metas[i]["page"],
                "doc_type": metas[i]["doc_type"],
                "distance": dists[i],
            })

    results.sort(key=lambda r: r["distance"])
    return results


def build_context(chunks: List[Dict]) -> str:
    blocks = []
    for c in chunks:
        blocks.append(
            f"[Source: {c['filename']}, page {c['page']}]\n{c['text']}"
        )
    return "\n\n---\n\n".join(blocks)


def answer_question(question: str, top_k_per_doc: int = DEFAULT_TOP_K_PER_DOC) -> Dict:
    """Full retrieve -> prompt -> answer pipeline. Returns
    {"answer": str, "sources": [{"file":..., "page":..., "doc_type":...}, ...]}"""
    chunks = retrieve(question, top_k_per_doc=top_k_per_doc)

    if not chunks:
        return {
            "answer": "The information is not available in the uploaded documents "
                      "(no documents are indexed yet).",
            "sources": [],
        }

    context = build_context(chunks)

    completion = ollama.chat(
        model=CHAT_MODEL,
        options={"temperature": TEMPERATURE},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"},
        ],
    )
    answer_text = completion["message"]["content"]

    seen = set()
    sources = []
    for c in chunks:
        key = (c["filename"], c["page"])
        if key not in seen:
            seen.add(key)
            sources.append({
                "file": c["filename"],
                "page": c["page"],
                "doc_type": c["doc_type"],
            })

    return {"answer": answer_text, "sources": sources}