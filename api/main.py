"""
api/main.py — Bonus FastAPI backend.

Run with: uvicorn api.main:app --reload
Then check http://localhost:8000/docs
"""

import os
import sys
import tempfile
from typing import Optional, List

from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel

# Allow running as `uvicorn api.main:app` from the project root.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ingest
import rag

app = FastAPI(
    title="Meridian Supply Chain RAG API",
    description="Ingest supply-chain PDFs and ask grounded questions over them.",
    version="1.0.0",
)


@app.get("/")
def root():
    """Small landing response for visitors opening the API base URL."""
    return {
        "message": "Meridian Supply Chain RAG API is running.",
        "docs": "/docs",
        "endpoints": ["POST /ingest", "POST /ask", "GET /stats"],
    }


class AskRequest(BaseModel):
    question: str
    top_k: Optional[int] = 3


class SourceOut(BaseModel):
    file: str
    page: int


class AskResponse(BaseModel):
    answer: str
    sources: List[SourceOut]


class IngestResponse(BaseModel):
    files: int
    chunks: int


@app.post("/ingest", response_model=IngestResponse)
async def ingest_endpoint(files: List[UploadFile] = File(...)):
    with tempfile.TemporaryDirectory() as tmpdir:
        filepaths = []
        for f in files:
            path = os.path.join(tmpdir, f.filename)
            content = await f.read()
            with open(path, "wb") as out:
                out.write(content)
            filepaths.append(path)
        report = ingest.ingest_files(filepaths)
    return {"files": report["files"], "chunks": report["chunks"]}


@app.post("/ask", response_model=AskResponse)
def ask_endpoint(req: AskRequest):
    result = rag.answer_question(req.question, top_k_per_doc=req.top_k or 3)
    sources = [{"file": s["file"], "page": s["page"]} for s in result["sources"]]
    return {"answer": result["answer"], "sources": sources}


@app.get("/stats")
def stats_endpoint():
    return ingest.collection_stats()
