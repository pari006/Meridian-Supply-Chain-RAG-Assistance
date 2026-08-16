"""High-contrast Streamlit interface for the Meridian Supply Chain RAG."""

import html
import os
import tempfile
import threading
import time

import streamlit as st
from dotenv import load_dotenv

import ingest
import rag

load_dotenv()
st.set_page_config(page_title="Meridian Supply Chain RAG", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Playfair+Display:wght@600;700&family=Source+Sans+3:wght@400;600;700&display=swap');
:root{--ink:#142631;--muted:#465b66;--paper:#f5f1e9;--card:#fffdf9;--line:#c9c0b4;--teal:#156b78;--teal-dark:#0e4f59;--red:#ba302c;--green:#155f46}html,body,[class*="css"]{font-family:'Source Sans 3',sans-serif!important;color:var(--ink)!important}header[data-testid="stHeader"], [data-testid="stAppViewContainer"]{background:var(--paper)!important}#MainMenu,footer,[data-testid="stToolbar"]{visibility:hidden}.block-container{max-width:1840px;padding:30px 58px 45px}.project-name{font-family:'Playfair Display',serif;color:var(--ink)!important;font-size:3.25rem;font-weight:700;text-align:center;margin:5px 0 42px;letter-spacing:-.045em}
[class*="st-key-left-panel"],[class*="st-key-right-panel"]{background:var(--card)!important;border:1px solid var(--line);border-radius:20px;min-height:680px;padding:30px!important;box-shadow:0 12px 34px rgba(20,38,49,.08)}.section-kicker{font:500 .78rem 'DM Mono',monospace!important;color:var(--teal)!important;letter-spacing:.14em;text-transform:uppercase;margin-bottom:12px}.section-title{font-family:'Playfair Display',serif!important;color:var(--ink)!important;font-size:2rem!important;margin:0 0 28px!important}.stMarkdown p,.stMarkdown span,label,[data-testid="stFileUploader"] span,[data-testid="stFileUploader"] small,[data-testid="stFileUploader"] button{color:var(--ink)!important;opacity:1!important}
[data-testid="stFileUploaderDropzone"]{background:#f8f5ef!important;border:1.5px dashed #7b9095!important;border-radius:12px!important}[data-testid="stFileUploader"] *,[data-testid="stFileUploaderFileName"],[data-testid="stFileUploaderFileName"] *{color:var(--ink)!important;opacity:1!important}[data-testid="stFileUploaderDropzone"] button{background:var(--ink)!important;color:#fff!important;border-color:var(--ink)!important}[data-testid="stTextArea"] textarea{min-height:88px!important;height:88px!important;background:#fffefa!important;color:var(--ink)!important;border:2px solid #819198!important;border-radius:12px!important;padding:13px 16px!important;font-size:1.05rem!important;line-height:1.45!important}[data-testid="stTextArea"] textarea::placeholder{color:#5e727b!important;opacity:1!important}[data-testid="stExpander"]{background:#f7f4ee!important;border:1px solid var(--line)!important;border-radius:10px!important}[data-testid="stExpander"] *{color:var(--ink)!important;opacity:1!important}
div[data-testid="stButton"] button,div[data-testid="stFormSubmitButton"] button{min-height:50px;border-radius:10px!important;background:var(--teal)!important;border-color:var(--teal)!important;color:#fff!important;font-weight:700!important;font-size:1rem!important}div[data-testid="stButton"] button:disabled,div[data-testid="stFormSubmitButton"] button:disabled{background:#9eafb2!important;border-color:#9eafb2!important;color:#fff!important;opacity:1!important}.st-key-question-form{margin-top:-18px}.activity{text-align:center;padding:28px 0 8px;color:var(--teal)!important;font:500 1.15rem 'DM Mono',monospace}.activity .dots{display:inline-block;width:2.5rem;text-align:left}.web-motion{height:80px;position:relative;overflow:hidden;margin:12px 0 4px}.web-motion:before,.web-motion:after{content:'';position:absolute;top:40px;width:46%;height:2px;background:var(--teal);animation:sweep 1s ease-in-out infinite}.web-motion:before{left:0}.web-motion:after{right:0}@keyframes sweep{50%{transform:translateX(14px);opacity:.3}}
.answer-card{margin-top:14px;padding:18px 22px;border:1px solid var(--line);border-radius:15px;background:#fffefa;box-shadow:0 7px 20px rgba(20,38,49,.06);animation:rise .45s ease-out}.answer-label,.sources-label{font:500 .74rem 'DM Mono',monospace;color:var(--teal)!important;letter-spacing:.12em;text-transform:uppercase}.answer-text{color:var(--ink)!important;white-space:pre-wrap;font-size:1rem;line-height:1.45;margin:8px 0 14px}.sources-label{border-top:1px solid var(--line);padding-top:11px}.source{display:inline-block;background:#e7f0ee;border:1px solid #9fc2ba;color:#174b42!important;border-radius:99px;padding:4px 9px;margin:6px 5px 0 0}@keyframes rise{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:none}}
.completion-modal{position:fixed;inset:0;z-index:9999;background:rgba(20,38,49,.42);display:flex;align-items:center;justify-content:center;pointer-events:none;animation:fade .25s ease-out}.completion-card{position:relative;overflow:hidden;width:min(480px,85vw);padding:48px 35px;border-radius:22px;background:#fffdf9;border:2px solid #77aa99;text-align:center;color:var(--ink)!important;box-shadow:0 24px 70px rgba(0,0,0,.28);animation:burst .55s cubic-bezier(.18,1.3,.45,1)}.completion-card:before,.completion-card:after{content:'';position:absolute;width:180px;height:180px;border:2px dotted #c38a34;border-radius:50%;opacity:.7}.completion-card:before{top:-95px;left:-90px}.completion-card:after{bottom:-105px;right:-100px}.completion-card h2{font-family:'Playfair Display',serif;color:var(--green)!important;font-size:2rem;margin:0 0 12px}.completion-number{font:700 3.7rem 'DM Mono',monospace;color:var(--teal)!important}.completion-copy{color:var(--muted)!important;font-size:1.1rem}@keyframes burst{from{opacity:0;transform:scale(.55)}to{opacity:1;transform:scale(1)}}@keyframes fade{from{opacity:0}to{opacity:1}}.stored-count{margin-top:18px;border-left:4px solid var(--green);background:#eaf4ef;color:#124a37!important;padding:12px 14px;border-radius:5px 10px 10px 5px;font-weight:700;animation:rise .5s ease-out}
@media(max-width:900px){.block-container{padding:20px 16px}.project-name{font-size:2.25rem;margin-bottom:25px}[class*="st-key-left-panel"],[class*="st-key-right-panel"]{min-height:auto;padding:22px!important}}
</style>""", unsafe_allow_html=True)


def run_with_activity(slot, label, work):
    """Runs work immediately while showing a simple, non-time-based activity state."""
    holder = {}
    started = time.perf_counter()

    def runner():
        try:
            holder["value"] = work()
        except Exception as error:
            holder["error"] = error

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
    while thread.is_alive():
        dots = "." * (int((time.perf_counter() - started) * 2) % 3 + 1)
        slot.markdown(f'<div class="web-motion"></div><div class="activity">{label}<span class="dots">{dots}</span></div>', unsafe_allow_html=True)
        time.sleep(.35)
    elapsed = time.perf_counter() - started
    if "error" in holder:
        raise holder["error"]
    return holder["value"], elapsed


def index_uploaded(files):
    with tempfile.TemporaryDirectory() as tmpdir:
        paths = []
        for file in files:
            path = os.path.join(tmpdir, file.name)
            with open(path, "wb") as destination:
                destination.write(file.getbuffer())
            paths.append(path)
        return ingest.ingest_files(paths)


st.session_state.setdefault("history", [])
st.session_state.setdefault("last_index_report", None)
try:
    indexed = ingest.collection_stats()["total_chunks"] > 0
except Exception:
    indexed = False

st.markdown('<div class="project-name">Meridian Supply Chain RAG</div>', unsafe_allow_html=True)
left, right = st.columns([.92, 1.48], gap="large")

with left:
    with st.container(key="left-panel"):
        st.markdown('<div class="section-kicker">Document workspace</div><h2 class="section-title">Browse and index</h2>', unsafe_allow_html=True)
        files = st.file_uploader("Choose PDF documents", type=["pdf"], accept_multiple_files=True, label_visibility="collapsed")
        index_clicked = st.button("Index documents", type="primary", disabled=not files, use_container_width=True)
        index_status, stored_position = st.empty(), st.empty()
        if index_clicked:
            try:
                report, elapsed = run_with_activity(index_status, "Indexing documents", lambda: index_uploaded(files))
                st.session_state.last_index_report = report
                indexed = True
                index_status.empty()
                modal = st.empty()
                modal.markdown(f'<div class="completion-modal"><div class="completion-card"><h2>Index complete</h2><div class="completion-number">{report["chunks"]}</div><div class="completion-copy">chunks stored in {elapsed:.1f} seconds</div></div></div>', unsafe_allow_html=True)
                time.sleep(2.2)
                modal.empty()
            except Exception as error:
                index_status.empty()
                st.error(f"Indexing could not finish: {error}")
        report = st.session_state.last_index_report
        if report:
            stored_position.markdown(f'<div class="stored-count">{report["chunks"]} chunks stored</div>', unsafe_allow_html=True)

with right:
    with st.container(key="right-panel"):
        st.markdown('<div class="section-kicker">Question workspace</div><h2 class="section-title">Ask the documents</h2>', unsafe_allow_html=True)
        if not indexed:
            st.info("Upload and index at least one PDF to begin.")
        with st.container(key="question-form"):
            with st.form("ask_form"):
                question = st.text_area("Question", placeholder="Ask a question about the documents you indexed...", height=88, label_visibility="collapsed")
                with st.expander("Tune retrieval"):
                    top_k = st.slider("Chunks retrieved from each document", 2, 8, 2)
                ask_clicked = st.form_submit_button("Ask question", type="primary", disabled=not indexed, use_container_width=True)
        answer_status = st.empty()
        if ask_clicked:
            if not question.strip():
                st.warning("Write a question before asking.")
            else:
                try:
                    result, _ = run_with_activity(answer_status, "Finding your answer", lambda: rag.answer_question(question.strip(), top_k_per_doc=top_k))
                    st.session_state.history.insert(0, result)
                    answer_status.empty()
                except Exception as error:
                    answer_status.empty()
                    st.error(f"The question could not be answered: {error}")
        for item in st.session_state.history:
            source_html = "".join(f'<span class="source">{html.escape(str(source["file"]))} · page {html.escape(str(source["page"]))}</span>' for source in item.get("sources", [])) or '<span class="source">No supporting passage found</span>'
            st.markdown(f'<div class="answer-card"><div class="answer-label">Answer</div><div class="answer-text">{html.escape(item["answer"])}</div><div class="sources-label">Sources</div>{source_html}</div>', unsafe_allow_html=True)
