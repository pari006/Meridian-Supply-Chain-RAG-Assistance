# Screenshot evidence index

This folder contains the evidence used by the root README and the additional captures used to verify application behaviour. The descriptions below were checked against the screenshot contents.

| File | What it shows | Result |
|---|---|---|
| `Indexing and chunks.png` | Center-screen completion modal after the two PDFs are indexed. | 21 total chunks stored. |
| `Question 1.png` | Q1 asks for the highest-spend supplier and its on-time delivery percentage. | Correct: Shenzhen Rui Electronics, INR 21.9 crore, 79.5% OTD. |
| `Question 2 part 1.png` | Q2 question with the beginning of the line-stoppage answer. | Shows 7 events and 41 hours. |
| `Question 2 part 2.png` | Remaining Q2 answer and cited sources. | Lists only two causes, then says the remaining five are unavailable; incomplete. |
| `Question 3.png` | Q3 at the normal retrieval setting. | Incorrectly chooses Category Manager for an INR 1.4 crore PO. |
| `Question 3 top k 6 (1).png` | Q3 with retrieval expanded to 6 chunks per document. | The correct approval table is present in context. |
| `Question 3 top k 6 (2).png` | Q3 answer and sources at `top_k=6`. | Still selects the wrong INR 25 lakh-INR 1 crore band; numeric reasoning error. |
| `Question 4 part 1.png` | Q4 asks for supplier categories; answer lists Critical, Strategic, Standard, and Tail. | Categories are correct. |
| `Question 4 part 2.png` | Remaining Q4 Critical-supplier definition and sources. | Adds unsupported monthly/annually wording; partially correct. |
| `Question 5.png` | Q5 asks which policy clauses Kaveri Metals triggers. | Correctly identifies clauses 6.1 and 6.3 and their actions. |
| `Question 6.png` | Q6 at the lower retrieval setting. | Retrieves the single-source justification route rather than the dual-sourcing rule; incorrect. |
| `Question 6 top k 7.png` | Q6 with the retrieval slider set to 7 chunks per document. | Shows the single-source microcontroller question and successful higher-retrieval test. |
| `Question 6 top k 7 (answer and source).png` | Q6 answer and sources at `top_k=7`. | Correctly describes dual sourcing and the Anh Long Semiconductors mitigation plan. |
| `Question 7.png` | Q7 after an application restart, with the safety-stock question entered. | Demonstrates persisted index availability without re-uploading. |
| `Question 7 answer.png` | Q7 safety-stock answer and sources. | Correctly calculates 11.5 days and applies the 30-day Imported/Critical floor. |
| `Question 8.png` | Q8 asks for the consequence of Trident's 640 PPM defect rate. | Gets clause 6.3 and INR 120 recovery, but omits full incoming inspection. |
| `Question 9 part 1.png` | Q9 asks about suppliers below the Band B OTD threshold and escalation. | Shows the question and the start of an incorrect answer. |
| `Question 9 part 2.png` | Remaining Q9 answer and sources. | Incorrectly treats 79.5% and 84.6% as below 75% and omits the escalation path. |
| `Question 10.png` | Deliberate trap question about the Head of Procurement's annual salary. | Correct honest refusal: information is not available in the uploaded documents. |

## Images shown in the root README

The root README uses the indexing, Q1, Q6 at `top_k=7`, Q7 persistence, and Q10 refusal images because together they demonstrate the core assignment requirements with minimal repetition.

Keep this folder tracked in Git. The public README must be able to display its screenshot evidence on GitHub.
