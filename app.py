"""
app.py — Streamlit interface for the Supply Chain RAG assistant.

Run with: streamlit run app.py

Layout note: this intentionally does not use st.sidebar. Everything lives in
a single custom "console" built from st.container(key=...) panels, styled
via the CSS block below, so the whole page reads as one product rather than
a default Streamlit form. See .streamlit/config.toml for the base theme that
keeps native widgets (file uploader, buttons) readable regardless of the
visitor's browser dark-mode setting.
"""

import os
import tempfile

import streamlit as st
from dotenv import load_dotenv

import ingest
import rag

load_dotenv()

st.set_page_config(page_title="Meridian Supply Chain Assistant", page_icon="✨", layout="wide")

# ---------------------------------------------------------------------------
# Theme + layout
# ---------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,700&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
    --linen: #F6EFE7;
    --ivory: #FFFCF9;
    --glass: rgba(255, 252, 249, 0.72);
    --espresso: #3A2E28;
    --taupe: #8C7A6E;
    --rose: #C08776;
    --rose-dark: #A8695A;
    --gold: #E4BE85;
    --gold-glow: rgba(228, 190, 133, 0.55);
    --lavender: #B5A2C4;
    --line: #E7DACB;
}

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* Hide default Streamlit chrome so this reads as a product, not a dev tool */
header[data-testid="stHeader"] { background: transparent; }
[data-testid="stToolbar"], #MainMenu, footer { visibility: hidden; height: 0; }

[data-testid="stAppViewContainer"] {
    background: linear-gradient(180deg, var(--linen) 0%, #F1E7DC 100%);
}
.block-container { padding-top: 1.5rem; max-width: 1100px; }

p, span, label, .stMarkdown, li { color: var(--espresso); }
[data-testid="stCaptionContainer"] { color: var(--taupe) !important; }
hr { border-color: var(--line) !important; }

/* ============ HERO ============ */
[class*="st-key-hero"] {
    position: relative;
    overflow: hidden;
    border-radius: 28px;
    padding: 3rem 2.5rem 2.5rem 2.5rem;
    margin-bottom: 1.75rem;
    background: linear-gradient(150deg, #FBF5EE 0%, #F3E7DA 100%);
    border: 1px solid var(--line);
}
.aurora-blob {
    position: absolute;
    border-radius: 50%;
    filter: blur(50px);
    opacity: 0.5;
    z-index: 0;
    animation: drift 14s ease-in-out infinite;
}
.aurora-1 { width: 320px; height: 320px; background: radial-gradient(circle, var(--rose) 0%, transparent 70%); top: -140px; left: -60px; animation-delay: 0s; }
.aurora-2 { width: 280px; height: 280px; background: radial-gradient(circle, var(--gold) 0%, transparent 70%); top: -100px; right: 5%; animation-delay: 3s; }
.aurora-3 { width: 240px; height: 240px; background: radial-gradient(circle, var(--lavender) 0%, transparent 70%); bottom: -140px; left: 30%; animation-delay: 6s; }
@keyframes drift {
    0%, 100% { transform: translate(0, 0) scale(1); }
    50% { transform: translate(20px, -25px) scale(1.08); }
}
@media (prefers-reduced-motion: reduce) { .aurora-blob { animation: none; } }

.sparkle { position: absolute; color: var(--gold); z-index: 0; animation: twinkle 2.6s ease-in-out infinite; }
@keyframes twinkle { 0%, 100% { opacity: 0.2; } 50% { opacity: 0.9; } }

.hero-content { position: relative; z-index: 1; }
.hero-eyebrow {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--rose-dark);
    margin-bottom: 0.6rem;
}
.hero-title {
    font-family: 'Fraunces', serif;
    font-weight: 600;
    font-size: 2.8rem;
    line-height: 1.1;
    color: var(--espresso);
    margin: 0 0 0.7rem 0;
}
.hero-title .shine {
    background: linear-gradient(120deg, var(--gold) 0%, var(--rose) 50%, var(--gold) 100%);
    background-size: 200% auto;
    -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
    animation: shimmer 4s linear infinite;
}
@keyframes shimmer { 0% { background-position: 0% center; } 100% { background-position: 200% center; } }
@media (prefers-reduced-motion: reduce) { .hero-title .shine { animation: none; -webkit-text-fill-color: var(--gold); } }
.hero-subtitle { font-size: 1.02rem; color: var(--taupe); max-width: 620px; }

/* ============ GLASS PANELS ============ */
[class*="st-key-panel-upload"], [class*="st-key-panel-ask"] {
    background: var(--glass);
    backdrop-filter: blur(10px);
    border: 1px solid var(--line);
    border-radius: 22px;
    padding: 1.6rem 1.7rem;
    box-shadow: 0 4px 24px rgba(58, 46, 40, 0.06);
}
.panel-eyebrow {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--rose-dark);
    margin-bottom: 0.15rem;
}
.panel-title {
    font-family: 'Fraunces', serif;
    font-weight: 600;
    font-size: 1.3rem;
    color: var(--espresso);
    margin-bottom: 1rem;
}

/* Stat chips */
.mrd-stats-row { display: flex; gap: 0.6rem; margin-top: 1rem; flex-wrap: wrap; }
.mrd-stat-chip {
    background: var(--ivory);
    border: 1px solid var(--line);
    border-radius: 14px;
    padding: 0.6rem 0.9rem;
    flex: 1;
    min-width: 100px;
}
.mrd-stat-chip .val { font-family: 'Fraunces', serif; font-size: 1.35rem; color: var(--rose-dark); line-height: 1; }
.mrd-stat-chip .lbl { font-size: 0.72rem; color: var(--taupe); margin-top: 0.2rem; }

/* Buttons */
div[data-testid="stButton"] button, div[data-testid="stFormSubmitButton"] button {
    border-radius: 12px !important;
    font-weight: 600;
    transition: box-shadow 0.35s ease, transform 0.15s ease;
}
div[data-testid="stButton"] button[kind="primary"], div[data-testid="stFormSubmitButton"] button[kind="primary"] {
    background: linear-gradient(135deg, var(--rose) 0%, var(--rose-dark) 100%) !important;
    border: none !important;
    color: var(--ivory) !important;
}
div[data-testid="stButton"] button[kind="primary"]:hover, div[data-testid="stFormSubmitButton"] button[kind="primary"]:hover {
    box-shadow: 0 0 18px 2px var(--gold-glow);
    transform: translateY(-1px);
}
div[data-testid="stButton"] button[kind="secondary"] {
    background: var(--ivory) !important;
    border: 1px solid var(--line) !important;
    color: var(--espresso) !important;
}

/* File uploader */
[data-testid="stFileUploaderDropzone"] {
    background: var(--linen) !important;
    border: 1.5px dashed var(--rose) !important;
    border-radius: 16px !important;
}

/* Text input (search-bar style) */
[data-testid="stTextInput"] input {
    background: var(--ivory) !important;
    border: 1.5px solid var(--line) !important;
    border-radius: 999px !important;
    color: var(--espresso) !important;
    padding: 0.7rem 1.2rem !important;
    font-size: 1rem !important;
}
[data-testid="stTextInput"] input:focus {
    border-color: var(--rose) !important;
    box-shadow: 0 0 0 3px var(--gold-glow) !important;
}
[data-testid="stTextInput"] label { display: none; }

/* Slider */
[data-testid="stSlider"] [role="slider"] { background-color: var(--rose) !important; }
[data-testid="stSlider"] > div > div > div > div { background: var(--rose) !important; }

/* Expander (advanced settings) */
[data-testid="stExpander"] {
    background: var(--ivory);
    border: 1px solid var(--line) !important;
    border-radius: 14px !important;
}

/* Alerts */
[data-testid="stAlertContainer"] { border-radius: 12px !important; border: 1px solid var(--line) !important; }

/* ============ CONVERSATION FEED ============ */
.mrd-turn { margin: 1.6rem 0; }
.mrd-q-row { display: flex; justify-content: flex-end; margin-bottom: 0.6rem; }
.mrd-q-bubble {
    background: linear-gradient(135deg, var(--rose) 0%, var(--rose-dark) 100%);
    color: var(--ivory);
    padding: 0.7rem 1.1rem;
    border-radius: 18px 18px 4px 18px;
    max-width: 75%;
    font-weight: 500;
    box-shadow: 0 2px 10px rgba(168, 105, 90, 0.25);
}
.mrd-a-row { display: flex; align-items: flex-start; gap: 0.7rem; }
.mrd-avatar {
    flex-shrink: 0;
    width: 34px; height: 34px;
    border-radius: 50%;
    background: linear-gradient(135deg, var(--gold) 0%, var(--rose) 100%);
    display: flex; align-items: center; justify-content: center;
    font-size: 1rem;
    box-shadow: 0 0 10px var(--gold-glow);
}
.mrd-a-card {
    background: var(--ivory);
    border: 1px solid var(--line);
    border-radius: 4px 18px 18px 18px;
    padding: 1rem 1.3rem;
    box-shadow: 0 2px 14px rgba(58, 46, 40, 0.05);
    max-width: 85%;
}
.mrd-answer { color: var(--espresso); line-height: 1.6; margin-bottom: 0.8rem; }
.mrd-sources-label { font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--taupe); margin-bottom: 0.45rem; }
.mrd-pill-row { display: flex; flex-wrap: wrap; gap: 0.45rem; }
.mrd-pill {
    display: inline-flex; align-items: center; gap: 0.35rem;
    background: var(--linen); border: 1px solid var(--line);
    border-radius: 999px; padding: 0.3rem 0.75rem; font-size: 0.82rem; color: var(--espresso);
}
.mrd-pill .pages {
    font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: var(--rose-dark);
    background: rgba(192, 135, 118, 0.12); padding: 0.05rem 0.4rem; border-radius: 6px;
}
.mrd-empty { font-style: italic; color: var(--taupe); font-size: 0.88rem; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Hero
# ---------------------------------------------------------------------------
with st.container(key="hero"):
    st.markdown("""
    <div class="aurora-blob aurora-1"></div>
    <div class="aurora-blob aurora-2"></div>
    <div class="aurora-blob aurora-3"></div>
    <span class="sparkle" style="top:20px; left:45%; font-size:1.1rem;">✦</span>
    <span class="sparkle" style="top:60px; right:12%; font-size:0.9rem; animation-delay:1s;">✧</span>
    <span class="sparkle" style="bottom:20px; left:8%; font-size:1rem; animation-delay:1.8s;">✦</span>
    <div class="hero-content">
        <div class="hero-eyebrow">Meridian Components Pvt. Ltd. · Internal tool</div>
        <div class="hero-title">Ask your <span class="shine">supply chain</span> anything</div>
        <div class="hero-subtitle">
            Grounded answers from the Q1 Performance Review and the Procurement Policy Handbook —
            with page-level sources, and an honest "not in the documents" when it doesn't know.
        </div>
    </div>
    """, unsafe_allow_html=True)

try:
    ingest.ollama_is_reachable()
except RuntimeError as e:
    st.error(str(e))
    st.info(
        "Quick fix: install Ollama from https://ollama.com/download, then run "
        "`ollama pull llama3.1:8b` and `ollama pull nomic-embed-text` in a terminal."
    )
    st.stop()

try:
    stats = ingest.collection_stats()
    indexed = stats["total_chunks"] > 0
except Exception:
    stats = None
    indexed = False

# ---------------------------------------------------------------------------
# Console: two glass panels side by side
# ---------------------------------------------------------------------------
col_upload, col_ask = st.columns([1, 1.3], gap="medium")

with col_upload:
    with st.container(key="panel-upload", border=True):
        st.markdown('<div class="panel-eyebrow">Step 01</div>', unsafe_allow_html=True)
        st.markdown('<div class="panel-title">Feed the assistant</div>', unsafe_allow_html=True)

        uploaded_files = st.file_uploader(
            "Upload one or more PDF files", type=["pdf"], accept_multiple_files=True,
            label_visibility="collapsed",
        )

        if st.button("✨ Index documents", type="primary", disabled=not uploaded_files, use_container_width=True):
            with st.spinner("Reading, chunking, embedding, and storing..."):
                with tempfile.TemporaryDirectory() as tmpdir:
                    filepaths = []
                    for f in uploaded_files:
                        path = os.path.join(tmpdir, f.name)
                        with open(path, "wb") as out:
                            out.write(f.getbuffer())
                        filepaths.append(path)
                    report = ingest.ingest_files(filepaths)
            st.success(f"{report['files']} files processed, {report['chunks']} chunks stored.")
            stats = ingest.collection_stats()
            indexed = stats["total_chunks"] > 0

        if stats:
            st.markdown(f"""
            <div class="mrd-stats-row">
                <div class="mrd-stat-chip"><div class="val">{stats['total_chunks']}</div><div class="lbl">Chunks stored</div></div>
                <div class="mrd-stat-chip"><div class="val" style="font-size:0.95rem;">{stats['embedding_model']}</div><div class="lbl">Embedding model</div></div>
                <div class="mrd-stat-chip"><div class="val" style="font-size:0.95rem;">{stats['llm_model']}</div><div class="lbl">LLM model</div></div>
            </div>
            """, unsafe_allow_html=True)

with col_ask:
    with st.container(key="panel-ask", border=True):
        st.markdown('<div class="panel-eyebrow">Step 02</div>', unsafe_allow_html=True)
        st.markdown('<div class="panel-title">Ask anything</div>', unsafe_allow_html=True)

        if not indexed:
            st.info("Index a document on the left before asking a question.")

        with st.form("ask_form"):
            question = st.text_input(
                "Your question", label_visibility="collapsed",
                placeholder="e.g. What is the approval authority for a purchase order worth ₹1.4 crore?",
            )
            with st.expander("Tune retrieval ✨"):
                top_k = st.slider("Chunks retrieved per document (top_k)", 2, 8, 3)
            submitted = st.form_submit_button("Ask", disabled=not indexed, type="primary", use_container_width=True)

# ---------------------------------------------------------------------------
# Conversation feed
# ---------------------------------------------------------------------------
if "history" not in st.session_state:
    st.session_state.history = []

if submitted and question:
    with st.spinner("Retrieving relevant chunks and asking the model..."):
        result = rag.answer_question(question, top_k_per_doc=top_k)
    st.session_state.history.insert(0, {"question": question, **result})

for entry in st.session_state.history:
    sources_html = ""
    if entry["sources"]:
        by_doc = {}
        for s in entry["sources"]:
            by_doc.setdefault(s["file"], []).append(s["page"])
        pills = []
        for fname, pages in by_doc.items():
            pages_str = ", ".join(str(p) for p in sorted(set(pages)))
            pills.append(f'<span class="mrd-pill">📄 {fname} <span class="pages">p.{pages_str}</span></span>')
        sources_html = f'<div class="mrd-sources-label">Sources</div><div class="mrd-pill-row">{"".join(pills)}</div>'
    else:
        sources_html = '<div class="mrd-empty">No sources — information not found in the uploaded documents.</div>'

    st.markdown(f"""
    <div class="mrd-turn">
        <div class="mrd-q-row"><div class="mrd-q-bubble">{entry['question']}</div></div>
        <div class="mrd-a-row">
            <div class="mrd-avatar">✨</div>
            <div class="mrd-a-card">
                <div class="mrd-answer">{entry['answer']}</div>
                {sources_html}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)