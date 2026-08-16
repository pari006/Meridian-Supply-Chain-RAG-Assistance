# Meridian Supply Chain RAG

A Streamlit RAG application for Meridian Components Pvt. Ltd. It indexes the Q1 Supply Chain Performance Review and Procurement Policy Handbook into one persistent ChromaDB collection, then answers questions with document and page-level sources.

## Demo video

[Watch the 3-minute project demonstration](https://drive.google.com/file/d/1UO8qmQvGtOEcbNsZAX0YVrLd0UtOOWC-/view?usp=sharing)

## Features

- Upload and index one or more PDFs.
- Extract text page by page with `pdfplumber`.
- Use recursive character splitting, ChromaDB persistence, and page-level citations.
- Retrieve balanced context from the review and policy documents.
- Refuse unsupported questions instead of guessing.
- Provide FastAPI endpoints for the optional API bonus.

## Tech stack

| Component | Technology |
|---|---|
| Language | Python 3.10+ |
| UI | Streamlit |
| PDF reading | pdfplumber |
| Embeddings | Ollama `nomic-embed-text` |
| Vector database | ChromaDB |
| Answer model | Ollama `llama3.1:8b` |
| API | FastAPI |

> The assignment specifies OpenAI models. This project uses local Ollama models; The alternative was approved by the instructor.

## Setup and run

```powershell
ollama pull llama3.1:8b
ollama pull nomic-embed-text

python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
streamlit run app.py
```

Open the Streamlit address printed in the terminal, normally `http://localhost:8501`.

## Chunking and retrieval design

| Setting | Value |
|---|---:|
| Chunk size | 1100 characters |
| Overlap | 150 characters |
| Default retrieval | 4 chunks total |
| Retrieval split | 2 review + 2 policy chunks |
| Temperature | 0.1 |

The 1100-character chunks keep policy clauses and scorecard information together; 150 characters of overlap preserves boundary context. Chunks are tagged as `review`, `policy`, or `other`, and the application queries both core document types for every question.

## Screenshots

The screenshots document indexing, a single-document answer, cross-document answers, persistence after restart, and the required honest refusal.

### Indexing and persistence

The two supplied PDFs were indexed into one ChromaDB collection: **21 chunks total** (12 handbook chunks and 9 review chunks).

![Successful document indexing: 21 chunks stored](<screenshots/Indexing and chunks.png>)

### Questions and answers

![Q1: highest-spend supplier with sources](<screenshots/Question 1.png>)

### Q6 retrieval retest at `top_k=7`

The higher retrieval setting returned the required dual-sourcing clause and the documented second-source mitigation.

![Q6: question at top_k=7](<screenshots/Question 6 top k 7.png>)

![Q6: answer and sources at top_k=7](<screenshots/Question 6 top k 7 (answer and source).png>)

### Persistence after restart

After refreshing and restarting the application, the persisted ChromaDB collection remained available and the application answered the safety-stock question without re-uploading the documents.

![Q7: safety-stock question after restart](<screenshots/Question 7.png>)

![Q7: safety-stock answer and sources](<screenshots/Question 7 answer.png>)

### Honest refusal for unsupported information

The application correctly refuses the deliberate trap question rather than inventing an answer.

![Q10: deliberate trap-question refusal](<screenshots/Question 10.png>)

## Verified test results

| # | Test | What the application answered | Verdict | Verification |
|---|---|---|---|---|
| 1 | Highest spend and OTD | Shenzhen Rui Electronics, INR 21.9 crore, 79.5% OTD. | Correct | Matches the supplier scorecard exactly. |
| 2 | Stoppages, downtime, and causes | 7 events and 41 hours, but only two of seven causes were listed. | Incomplete | The source table contains all seven causes; retrieval missed most of them. |
| 3 | INR 1.4 crore PO approval | Category Manager, using the INR 5 lakh-INR 25 lakh band. | Incorrect | INR 1.4 crore belongs to the COO band: above INR 1 crore and up to INR 5 crore. |
| 4 | Four categories and Critical qualifier | Categories were correct, but the Critical condition added unsupported wording. | Partially correct | The handbook says "supplies a safety-related component"; it does not say "monthly" or "annually". |
| 5 | Kaveri Metals policy clauses | Clauses 6.1 and 6.3 with both required actions. | Correct | Both clauses and actions match the handbook; clause 6.2 does not apply. |
| 6 | Single-source microcontroller policy | At `top_k=7`, clause 7.1, the Shenzhen Rui single-source risk, and the Anh Long Semiconductors second-source plan targeting 30 Sep 2025. | Correct at `top_k=7` | The default retrieval previously surfaced clause 7.4 instead. |
| 7 | 46-day safety stock | 11.5 days calculated, then the 30-day floor applied. | Correct | 46 x 0.25 = 11.5; the higher Imported/Critical floor applies. |
| 8 | Trident at 640 PPM | Clause 6.3 and INR 120 per affected unit. | Partially correct | The answer omitted mandatory 100% incoming inspection until three clean lots. |
| 9 | Suppliers below Band B and escalation | Shenzhen Rui (79.5%) and Trident (84.6%) were incorrectly called below 75%. | Incorrect | Neither is below 75%; no supplier fails the OTD-only Band B condition, and the escalation path was omitted. |
| 10 | Trap question: Head of Procurement salary | The information is not available in the uploaded documents. | Correct | Correct honest refusal, as required. |

## Honest evaluation note

The system indexes both documents, persists ChromaDB after restart, shows page-level sources, and correctly refuses the trap question. Four tests were fully correct at the tested settings: Q1, Q5, Q7, and Q10. Q4 and Q8 contained the main fact but were incomplete or added unsupported wording. Q2 retrieved the correct stoppage count and downtime but only two of the seven documented causes.

Q3, Q6 at the original setting, and Q9 exposed different weaknesses. For Q3, raising retrieval to `top_k=6` brought the exact approval-authority table into the context, but the local 8B model still selected the wrong monetary band. This is a numeric-comparison reasoning error rather than a retrieval problem. Q9 similarly misapplied the 75% threshold and missed the escalation table.

Q6 was re-tested at `top_k=7`. At the lower setting, retrieval returned clause 7.4, the single-source justification rule. At `top_k=7`, it also returned clause 7.1 and the documented mitigation plan, resulting in a correct answer about dual sourcing and Anh Long Semiconductors. This confirms that Q6 was a retrieval gap rather than a reasoning error. Raising retrieval is therefore useful for clause-heavy cross-document questions, although it does not resolve every numeric-reasoning error.

## FastAPI bonus

Start the API from the project root:

```powershell
uvicorn api.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for Swagger UI, or open `api_requests.http` in VS Code with the **REST Client** extension to run GET and POST requests.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | API status |
| GET | `/stats` | Collection statistics |
| POST | `/ingest` | Index uploaded PDFs |
| POST | `/ask` | Return an answer and sources |

## Project structure

```text
supplychain-rag/
|- app.py
|- ingest.py
|- rag.py
|- api/main.py
|- api_requests.http
|- data/
|- screenshots/
|- requirements.txt
|- .env.example
`- README.md
```

## Repository hygiene

- `.env` and `chroma_db/` are excluded from Git.
- The selected `screenshots/` images are intentionally committed because the public README must display the required evidence.
- No API key is stored in source code.
