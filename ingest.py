"""
ingest.py
Loads PDFs -> extracts text per page -> chunks -> embeds -> stores in ChromaDB.

Design decisions (see README for full rationale):
- Text extraction: pdfplumber, page by page, so every chunk can carry a page number.
- Chunking: a custom recursive character splitter (paragraph -> line -> sentence -> word),
  chunk size 1100 / overlap 150. A size near the top of the allowed 800-1200 range keeps
  the handbook's short numbered clauses attached to their trigger conditions and keeps
  scorecard-style tables from being torn apart mid-row.
- doc_type metadata ("review" or "policy") is attached to every chunk. This is what lets
  rag.py guarantee that both documents are consulted for cross-document questions
  (Stage 6 "retrieve a fixed share from each document" fix from the assignment guide).
- Embeddings: local Ollama embedding model (nomic-embed-text by default), batched one call
  per chunk (Ollama's embed() accepts a single string or list; looping keeps this robust
  across Ollama versions).
- Storage: a single persistent Chroma collection on disk (./chroma_db), so the app survives
  a restart without re-uploading (Stage 5 / Requirement 7).

NOTE ON DEVIATION FROM THE ORIGINAL ASSIGNMENT SPEC:
The assignment's technical-requirements table calls for OpenAI text-embedding-3-small and
GPT-4o specifically. This project instead uses Ollama (local, free) for both embeddings and
generation, per ET AI Academy's official email (13 Aug 2026) explicitly permitting "Ollama"
as an approved alternative for anyone without OpenAI API access. See README for details.
"""

import os
import re
import hashlib
from pathlib import Path
from typing import List, Dict

import pdfplumber
import chromadb
import ollama
from dotenv import load_dotenv

load_dotenv()

CHROMA_DIR = os.getenv("CHROMA_DIR", "chroma_db")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "meridian_supply_chain")
EMBEDDING_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
CHUNK_SIZE = 1100
CHUNK_OVERLAP = 150

_chroma_client = None
_collection = None


def get_chroma_collection():
    """Returns a persistent Chroma collection, creating it on first use."""
    global _chroma_client, _collection
    if _collection is None:
        _chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
        _collection = _chroma_client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def infer_doc_type(filename: str) -> str:
    """Classifies a source file as 'review' or 'policy' from its filename.
    Falls back to 'other' for any additional PDFs the user adds (the assignment's
    optional third-document extension)."""
    name = filename.lower()
    if "review" in name or "performance" in name:
        return "review"
    if "policy" in name or "handbook" in name:
        return "policy"
    return "other"


# ---------------------------------------------------------------------------
# Step 1: Extract text, page by page, keeping filename + page number.
# ---------------------------------------------------------------------------
def load_pdf_pages(filepath: str) -> List[Dict]:
    """Returns a list of {text, filename, page} dicts, one per non-empty page."""
    filename = os.path.basename(filepath)
    pages = []
    with pdfplumber.open(filepath) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            text = text.strip()
            if text:
                pages.append({"text": text, "filename": filename, "page": i})
    return pages


# ---------------------------------------------------------------------------
# Step 2: Recursive character chunking.
# ---------------------------------------------------------------------------
def _split_text(text: str, separators: List[str], chunk_size: int) -> List[str]:
    """Recursively split text using the first separator that produces pieces
    small enough to work with; falls back to hard character slicing."""
    if len(text) <= chunk_size:
        return [text]

    if not separators:
        # Last resort: hard slice.
        return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

    sep, *rest_separators = separators
    parts = text.split(sep) if sep else list(text)

    chunks, current = [], ""
    for part in parts:
        candidate = current + sep + part if current else part
        if len(candidate) <= chunk_size:
            current = candidate
        else:
            if current:
                chunks.append(current)
            if len(part) > chunk_size:
                chunks.extend(_split_text(part, rest_separators, chunk_size))
                current = ""
            else:
                current = part
    if current:
        chunks.append(current)
    return chunks


def recursive_character_split(text: str, chunk_size: int = CHUNK_SIZE,
                               overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Splits on paragraph breaks first, then lines, then sentences, then words,
    matching LangChain's RecursiveCharacterTextSplitter behaviour. Adds overlap
    between consecutive chunks so a sentence sitting on a boundary survives intact
    somewhere (see Stage 3 of the assignment guide)."""
    separators = ["\n\n", "\n", ". ", " "]
    raw_chunks = _split_text(text, separators, chunk_size)

    # Merge tiny trailing fragments into the previous chunk.
    merged = []
    for c in raw_chunks:
        if merged and len(c) < 200:
            merged[-1] = merged[-1] + " " + c
        else:
            merged.append(c)

    if overlap <= 0 or len(merged) <= 1:
        return merged

    overlapped = []
    for i, c in enumerate(merged):
        if i == 0:
            overlapped.append(c)
        else:
            prefix = merged[i - 1][-overlap:]
            overlapped.append(prefix + " " + c)
    return overlapped


def chunk_pages(pages: List[Dict]) -> List[Dict]:
    """Chunks every page's text, keeping filename/page/doc_type metadata on each chunk."""
    chunks = []
    for page in pages:
        doc_type = infer_doc_type(page["filename"])
        pieces = recursive_character_split(page["text"])
        for piece in pieces:
            piece = piece.strip()
            if not piece:
                continue
            chunk_id = hashlib.sha256(
                f"{page['filename']}::{page['page']}::{piece[:80]}".encode()
            ).hexdigest()[:24]
            chunks.append({
                "id": chunk_id,
                "text": piece,
                "filename": page["filename"],
                "page": page["page"],
                "doc_type": doc_type,
            })
    return chunks


# ---------------------------------------------------------------------------
# Step 3: Embed via local Ollama model.
# ---------------------------------------------------------------------------
def embed_texts(texts: List[str]) -> List[List[float]]:
    """Embeds a list of strings using the local Ollama embedding model.
    Called one at a time for compatibility across Ollama versions (some older
    versions don't accept a batched `input` list on /api/embed)."""
    vectors = []
    for text in texts:
        resp = ollama.embed(model=EMBEDDING_MODEL, input=text)
        # response.embeddings is a list containing one vector per input string
        vectors.append(resp["embeddings"][0])
    return vectors


# ---------------------------------------------------------------------------
# Step 4: Store in Chroma (upsert, so re-running ingest never duplicates chunks).
# ---------------------------------------------------------------------------
def store_chunks(chunks: List[Dict]) -> None:
    if not chunks:
        return
    collection = get_chroma_collection()
    vectors = embed_texts([c["text"] for c in chunks])
    collection.upsert(
        ids=[c["id"] for c in chunks],
        embeddings=vectors,
        documents=[c["text"] for c in chunks],
        metadatas=[
            {"filename": c["filename"], "page": c["page"], "doc_type": c["doc_type"]}
            for c in chunks
        ],
    )


def ingest_files(filepaths: List[str]) -> Dict:
    """Full pipeline for a list of PDF filepaths. Returns a report dict:
    {"files": n, "chunks": n, "by_document": {filename: chunk_count}}"""
    all_chunks = []
    for fp in filepaths:
        pages = load_pdf_pages(fp)
        chunks = chunk_pages(pages)
        all_chunks.extend(chunks)

    store_chunks(all_chunks)

    by_document: Dict[str, int] = {}
    for c in all_chunks:
        by_document[c["filename"]] = by_document.get(c["filename"], 0) + 1

    return {
        "files": len(filepaths),
        "chunks": len(all_chunks),
        "by_document": by_document,
    }


def collection_stats() -> Dict:
    collection = get_chroma_collection()
    count = collection.count()
    return {
        "collection_name": COLLECTION_NAME,
        "total_chunks": count,
        "embedding_model": EMBEDDING_MODEL,
        "llm_model": os.getenv("OLLAMA_CHAT_MODEL", "llama3.1:8b"),
        "persist_directory": CHROMA_DIR,
    }


def ollama_is_reachable() -> bool:
    """Checks whether the local Ollama server is up and has the required models pulled."""
    try:
        models = {m["model"] for m in ollama.list().get("models", [])}
        chat_model = os.getenv("OLLAMA_CHAT_MODEL", "llama3.1:8b")
        missing = []
        # Ollama model names in `list` include a tag (e.g. "llama3.1:8b"); allow a
        # loose match so "llama3.1" in .env still matches "llama3.1:8b" on disk.
        def _have(name):
            return any(m == name or m.startswith(name + ":") or m.startswith(name)
                       for m in models)
        if not _have(chat_model):
            missing.append(chat_model)
        if not _have(EMBEDDING_MODEL):
            missing.append(EMBEDDING_MODEL)
        if missing:
            raise RuntimeError(f"Missing Ollama model(s): {', '.join(missing)}. "
                                f"Run `ollama pull {missing[0]}`.")
        return True
    except Exception as e:
        raise RuntimeError(
            f"Cannot reach Ollama ({e}). Make sure Ollama is installed and running "
            f"(it usually starts automatically; otherwise run `ollama serve`)."
        )


if __name__ == "__main__":
    data_dir = Path("data")
    pdfs = [str(p) for p in data_dir.glob("*.pdf")]
    print(f"Ingesting {len(pdfs)} PDF(s) from {data_dir}...")
    report = ingest_files(pdfs)
    print(report)