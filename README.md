# Meridian Supply Chain RAG Assistant

A Retrieval-Augmented Generation system that lets a buyer ask plain-English questions
about Meridian Components' Q1 FY 2025-26 Supply Chain Performance Review and its
Procurement Policy Handbook (v4.2), and get an answer grounded in the actual text of
both documents — with page-level citations.

Built for Assignment 2 — Build a RAG System for Supply Chain Documents.

### Note on models used

The assignment's technical-requirements table specifies OpenAI `text-embedding-3-small`
and `GPT-4o`. This submission instead uses **local Ollama models** — `nomic-embed-text`
for embeddings and `llama3.1:8b` for generation — per ET AI Academy's official email
(13 Aug 2026, sent after the doubt-clearing session) explicitly approving Ollama as an
alternative for participants without OpenAI API access. Everything else in the pipeline
(chunking strategy, Chroma storage, retrieval logic, prompt structure, UI, FastAPI bonus)
is unchanged and satisfies the assignment's stated requirements exactly.

---

## 1. Setup and run instructions

### Prerequisites
- Python 3.10+
- [Ollama](https://ollama.com/download) installed and running (no API key or billing needed)

### Steps

```bash
# 0. Install Ollama, then pull the two required models (one-time, needs internet)
ollama pull llama3.1:8b
ollama pull nomic-embed-text

# 1. Clone the repo and enter it
git clone <your-repo-url>
cd supplychain-rag

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy the env template (no key needed, but this sets model names)
cp .env.example .env

# 5. Run the app
streamlit run app.py
```

If your machine is slow with `llama3.1:8b` (4.7GB), pull a lighter model instead —
`ollama pull llama3.2:3b` — and set `OLLAMA_CHAT_MODEL=llama3.2:3b` in `.env`.

Open the URL Streamlit prints (usually http://localhost:8501). In the sidebar, upload
the two PDFs from `data/` (or your own), click **Index documents**, then ask questions.

### Optional: run the FastAPI backend instead

```bash
uvicorn api.main:app --reload
```

Test the three endpoints from the automatic docs page at `http://localhost:8000/docs`.

### Restart / persistence test
Stop the Streamlit app (`Ctrl+C`), start it again with `streamlit run app.py`, and ask a
question **without re-uploading**. The sidebar "Total chunks stored" figure should be
unchanged, and the app should answer immediately — this proves the Chroma collection
persisted to the `chroma_db/` folder on disk.

---

## 2. Chunking decision

| Setting | Value |
|---|---|
| Chunk size | 1100 characters |
| Overlap | 150 characters |
| Splitter | custom recursive character splitter (paragraph → line → sentence → word) |

**Reason:** a size near the top of the allowed 800–1200 range keeps the handbook's short
numbered clauses (Section 6, "Performance failures and consequences") attached to the
condition that triggers them, and keeps the supplier scorecard table from being torn
across chunk boundaries — both called out explicitly as risks in the assignment guide.
150-character overlap ensures a sentence sitting on a chunk boundary survives intact in
at least one chunk.

---

## 3. Cross-document retrieval fix

**Chosen fix: retrieve a fixed share from each document**, applied on every question, not
just as a fallback.

`rag.py` tags every chunk with `doc_type` (`review` or `policy`) at ingestion time. For
every question, it queries Chroma **twice** — once filtered to `doc_type=review`, once to
`doc_type=policy` — each returning `top_k` chunks (default 3, adjustable in the UI), then
merges and sorts the results by similarity. This guarantees that a question like *"Kaveri
Metals recorded 88.1% on-time delivery — which policy clauses does this trigger?"* always
retrieves handbook clauses even though the words "Kaveri Metals" and the percentage only
ever appear in the review. Simply raising a single shared `top_k` was tried first and was
not reliable enough for questions 5–9, because the review's supplier-scorecard language is
semantically closer to itself than to the handbook's more abstract clause language — the
review chunks kept crowding out the handbook chunks.

---

## 4. Prompt used

**System prompt:**
```
You are an internal procurement assistant for Meridian Components Pvt. Ltd.

Answer only from the context provided below. If the context does not contain the answer,
say plainly that the information is not available in the uploaded documents. Do not use
outside knowledge of how procurement "usually" works, even if you are confident about it.

When a question requires combining a figure from the performance review with a rule from
the procurement policy handbook, state all three of the following explicitly:
1. The figure (with its source).
2. The exact policy clause it triggers (quote the clause number).
3. The resulting required action.

Keep answers concise and factual. Do not invent numbers, clause numbers, or names that do
not appear in the context.
```

**User message:** `Context:\n{retrieved chunks with [Source: filename, page N] headers}\n\nQuestion: {question}`

**Model / temperature:** `llama3.1:8b` (via local Ollama), temperature `0.1`.

---

## 5. Screenshots

*(Add screenshots here after running the app locally: the sidebar after indexing showing
"2 files processed, N chunks stored"; a cross-document answer with sources from both
documents visible; the trap question being refused.)*

---

## 6. Test questions and answers

The answers below are **reference answers**, hand-verified against the two source PDFs
(page numbers noted), per the assignment's Stage 1 and Stage 8 instructions. Run these
same ten questions through the app and compare — record any mismatches in Section 7.

| # | Question | Reference answer | Source(s) |
|---|---|---|---|
| 1 | Highest-spend supplier & its on-time delivery | **Shenzhen Rui Electronics**, ₹21.9 crore Q1 spend, **79.5%** on-time delivery | Review, p.1 |
| 2 | Line stoppages, downtime, causes | **7 events, 41 hours total.** 4 events / 22 hrs from microcontroller shortages at Shenzhen Rui (vessel roll-over, 9-day customs hold, partial shipment, allocation shortfall); 2 events / 11 hrs from Trident PCB lot rejections; 1 event / 5 hrs from a transporter strike | Review, p.2 |
| 3 | Approval authority for a ₹1.4 crore PO | **Chief Operating Officer** (band: above ₹1 crore up to ₹5 crore) | Policy, p.1 |
| 4 | Four supplier classification categories & Critical qualifier | **Critical, Strategic, Standard, Tail.** A supplier is Critical if *any one* of: single-source for any part; annual spend above ₹10 crore; or supplies a safety-related component | Policy, p.1 |
| 5 | Kaveri Metals — 88.1% OTD, 1,150 PPM — clauses triggered | Triggers **clause 6.1** (OTD < 90%): written warning within 10 working days + weekly delivery review call until OTD recovers above 90% for a full quarter. Also triggers **clause 6.3** (defects > 500 PPM): supplier bears rework cost at ₹120/affected unit + 100% incoming inspection until 3 consecutive clean lots. (Clause 6.2 does *not* trigger — that needs <85% OTD for two consecutive quarters, and 88.1% is only one quarter above 85%.) | Review p.1 + Policy p.2 |
| 6 | Single-source microcontroller supplier — sourcing policy | **Clause 7.1 (dual sourcing):** every part from a Critical supplier (single-source qualifies as Critical) must have a qualified second source within 12 months of classification. Meridian is already qualifying **Anh Long Semiconductors** (Hai Phong, Vietnam) as the second source, target **30 Sep 2025**, and shifting 30% of volume to air freight in the interim | Policy p.2 + Review p.3 |
| 7 | Safety stock for a 46-day imported microcontroller lead time | Calculated: 46 × 0.25 = **11.5 days**. But the microcontroller supplier is single-source (Critical), so the floor for *"Imported, Critical supplier"* is **30 days**, which is higher — so **30 days** applies | Policy p.3 |
| 8 | Trident Circuit Boards — 640 PPM — cost consequence | Exceeds the 500 PPM threshold → **clause 6.3**: Trident bears rework cost at the standard recovery rate of **₹120 per affected unit**, plus 100% incoming inspection at Trident's cost until three consecutive lots are accepted defect-free | Review p.1 + Policy p.2 |
| 9 | Suppliers below B band on OTD alone; escalation path | Per clause "a supplier delivering below 75% cannot score in Band B" — **none of the six suppliers falls below 75% OTD** (lowest is Shenzhen Rui at 79.5%), so none is excluded from Band B on delivery alone. (A supplier could still land in a lower band once quality/cost/ESG scores are combined, but that's outside the OTD-only test asked here.) Escalation path (Section 10): Level 1 Buyer (24h, slippage ≤3 days) → Level 2 Category Manager (48h, slippage >3 days or rejected lot) → Level 3 Head of Procurement (72h, stoppage risk within 7 days) → Level 4 COO (5 working days, actual stoppage or insolvency signal) | Review p.1 + Policy p.3 |
| 10 | Trap: Head of Procurement's annual salary | **Not available in the uploaded documents** — must be refused, not guessed | — |

---

## 7. Honest note on failures

*(Fill this in after running your own tests: which of the ten questions your app got
wrong, what the retrieved chunks looked like for that question, and your best guess at
the cause — e.g. "Q7 initially returned only the formula chunk and missed the floor
table because they're on different pages; increasing top_k_per_doc from 3 to 4 fixed
it.")*

---

## 8. Project structure

```
supplychain-rag/
├── app.py              # Streamlit interface
├── ingest.py           # load, chunk, embed, store in Chroma
├── rag.py              # retrieve + prompt + call GPT-4o
├── api/main.py          # optional FastAPI backend
├── data/                # the two provided PDFs
├── chroma_db/           # persisted vector store (git-ignored)
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## 9. Design notes / what was deliberately left out

Per the assignment's "keep it simple" rule: no re-ranking, no hybrid keyword+vector
search, no agent framework, no fine-tuning. Retrieval logic is a single well-understood
technique (fixed-share-per-document) chosen and explained above, not stacked with extras.