import json
import re
from pathlib import Path

import streamlit as st
from agent import answer_question
from rag import Retriever, INDEX_DIR

ROOT = Path(__file__).resolve().parent
SUMMARY_PATH = ROOT / "results" / "evaluation_summary.json"
RESULTS_PATH = ROOT / "results" / "evaluation_results.csv"

# Load the existing FAISS retriever once when the Streamlit app starts.
# This matches the backend signature: answer_question(question, retriever, ...).
@st.cache_resource
def load_retriever():
    retriever = Retriever()
    retriever.load(INDEX_DIR)
    return retriever

try:
    rag_retriever = load_retriever()
    RETRIEVER_ERROR = None
except Exception as exc:
    rag_retriever = None
    RETRIEVER_ERROR = f"{type(exc).__name__}: {exc}"

st.set_page_config(page_title="SmartShop BD Assistant", page_icon="🛍️", layout="wide", initial_sidebar_state="collapsed")

# Keep the entire Streamlit shell in light mode; CSS alone cannot override every
# BaseWeb component (notably the fixed chat input) when the app theme is dark.

BG, SURFACE, ALT = "#F7F2E8", "#FFFCF6", "#EFE6D6"
INK, MUTED, ACCENT, ACCENT_DARK, BORDER = "#332D27", "#786E62", "#B79A72", "#8A704E", "#E3D7C5"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Playfair+Display:wght@600;700&display=swap');
.stApp {{background:{BG};color:{INK};font-family:'DM Sans',sans-serif}}
[data-testid="stHeader"] {{background:{BG};height:0 !important;min-height:0 !important;padding:0 !important;margin:0 !important;display:none!important;}}
[data-testid="stToolbar"], [data-testid="stDecoration"], #MainMenu {{display:none!important;visibility:hidden!important;}}
[data-testid="stAppViewContainer"], [data-testid="stMain"], [data-testid="stMainBlockContainer"] {{background:{BG};}}
.block-container {{max-width:1180px;padding-top: .25rem;padding-bottom:5rem}}
/* Hide Streamlit's floating top chrome; keep the app navbar fully visible. */
div[data-testid="stHorizontalBlock"]:has(.brand) {{
  position: sticky; top: 0; z-index: 9999;
  background: {BG}; padding: .65rem 0 .75rem;
  border-bottom: 1px solid {BORDER}; margin-bottom: .6rem;
}}
div[data-testid="stHorizontalBlock"]:has(.brand) [data-testid="column"] {{
  background: {BG};
}}
/* Force the chat composer and its inner BaseWeb controls to match the beige theme. */
[data-testid="stChatInput"], [data-testid="stChatInput"] > div,
[data-testid="stChatInput"] textarea, [data-baseweb="textarea"],
[data-baseweb="textarea"] > div, [data-testid="stBottom"],
[data-testid="stBottom"] > div {{
  background:{SURFACE}!important; color:{INK}!important; border-color:{BORDER}!important;
}}
[data-testid="stChatInput"] textarea {{-webkit-text-fill-color:{INK}!important; caret-color:{INK}!important;}}
[data-testid="stChatInput"] textarea::placeholder {{color:{MUTED}!important;opacity:1!important;}}
[data-testid="stBottom"] {{background:{BG}!important;}}
[data-testid="stBottom"]::before {{background:linear-gradient(transparent,{BG});}}
h1,h2,h3 {{color:{INK};letter-spacing:-.02em}} h1,h2 {{font-family:'Playfair Display',Georgia,serif}}
p,label,li {{color:{INK}}}
.brand {{font-family:'Playfair Display',Georgia,serif;font-size:1.5rem;font-weight:700;color:{INK};padding-top:.25rem;white-space:nowrap;}}
.brand span {{color:{ACCENT_DARK}}}
.eyebrow,.section-label {{text-transform:uppercase;letter-spacing:.14em;font-size:.73rem;font-weight:700;color:{ACCENT_DARK};margin-bottom:.55rem}}
.muted {{color:{MUTED}}}
.hero {{background:linear-gradient(125deg,{SURFACE},{ALT});border:1px solid {BORDER};border-radius:24px;padding:clamp(1.5rem,4vw,3rem);margin:.8rem 0 1.5rem}}
.hero h1 {{font-size:clamp(2.1rem,4vw,3.5rem);margin:0 0 .8rem;line-height:1.08}}
.hero p {{color:{MUTED};font-size:1.03rem;max-width:680px;line-height:1.7}}
.pill {{display:inline-block;border:1px solid {BORDER};background:{SURFACE};color:{ACCENT_DARK};padding:.35rem .7rem;border-radius:999px;font-size:.78rem;font-weight:600;margin-bottom:1rem}}
.feature-card {{background:{SURFACE};border:1px solid {BORDER};border-radius:18px;padding:1.25rem;min-height:150px}}
.feature-icon {{font-size:1.4rem;margin-bottom:.65rem}} .feature-title {{font-weight:700;margin-bottom:.4rem}} .feature-copy {{color:{MUTED};font-size:.9rem;line-height:1.55}}
div[data-testid="stChatMessage"] {{background:{SURFACE};border:1px solid {BORDER};border-radius:18px;padding:.9rem 1rem;margin-bottom:.8rem}}
div[data-testid="stChatInput"] {{background:{SURFACE};border-color:{BORDER};border-radius:16px}}
.stButton>button {{border-radius:11px;border:1px solid {BORDER};background:{SURFACE};color:{INK};font-weight:600;min-height:2.55rem}}
.stButton>button:hover {{border-color:{ACCENT};color:{INK};background:{ALT}}}
.stButton>button[kind="primary"] {{background:{ACCENT_DARK};border-color:{ACCENT_DARK};color:white}}
.stButton>button[kind="primary"]:hover {{background:{INK};border-color:{INK};color:white}}
[data-testid="stMetric"] {{background:{SURFACE};border:1px solid {BORDER};border-radius:16px;padding:1rem}}
[data-testid="stExpander"] {{background:{SURFACE};border:1px solid {BORDER};border-radius:12px}}
a {{color:{ACCENT_DARK}!important}} footer {{visibility:hidden}}
@media(max-width:700px) {{.block-container{{padding-left:1rem;padding-right:1rem}}.brand{{font-size:1.2rem}}}}


/* compact top spacing */
[data-testid="stAppViewBlockContainer"] {{ padding-top: 0rem !important; }}
[data-testid="stHeader"] {{ height: 0rem !important; min-height: 0rem !important; padding: 0 !important; margin: 0 !important; }}

/* compact layout below navbar */
[data-testid="stVerticalBlock"] > [data-testid="stElementContainer"] {{ margin-bottom: .15rem; }}
[data-testid="stMainBlockContainer"] {{ padding-top: 0rem !important; }}

/* Collapse Streamlit divider whitespace — this is what caused the large gap */
hr, [data-testid="stDivider"], [data-testid="stDivider"] > div {{
  margin: 0 !important;
  padding: 0 !important;
}}
hr {{
  border: none !important;
  border-top: 1px solid {BORDER} !important;
}}

</style>
""", unsafe_allow_html=True)

if "page" not in st.session_state: st.session_state.page = "Home"
if "chat_messages" not in st.session_state: st.session_state.chat_messages = []
PAGES = ["Home", "AI Assistant", "Evaluation", "Contact"]

def navigate(page):
    st.session_state.page = page
    st.rerun()

def clean_answer(text):
    """Remove model-emitted source tokens; source filenames are shown separately."""
    text = str(text or "")
    # Common formats: [Source: file.md], 【Source: file.md】, 【file.md】, [file.md]
    patterns = [
        r"【\s*(?:source\s*:\s*)?[^】\n]*\.md\s*】",
        r"\[\s*(?:source\s*:\s*)?[^\]\n]*\.md\s*\]",
        r"\(\s*(?:source\s*:\s*)?[^)\n]*\.md\s*\)",
    ]
    for pattern in patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    text = re.sub(r"[ \t]+([.,!?;:])", r"\1", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n[ \t]+\n", "\n\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def show_sources(sources):
    names = []
    for source in sources or []:
        name = source.get("source") if isinstance(source, dict) else str(source)
        if name and name not in names: names.append(name)
    if names:
        with st.expander(f"📚 Sources used · {len(names)}"):
            for name in names: st.markdown(f"- `{name}`")

# Top navigation
nav_brand, nav_pages, nav_note = st.columns([2, 4.5, 1.3], vertical_alignment="center")
with nav_brand:
    st.markdown('<div class="brand">SmartShop <span>BD</span></div>', unsafe_allow_html=True)
with nav_pages:
    cols = st.columns(4, gap="small")
    for col, page in zip(cols, PAGES):
        with col:
            if st.button(page, key=f"nav_{page}", use_container_width=True,
                         type="primary" if st.session_state.page == page else "secondary"):
                navigate(page)
with nav_note:
    st.markdown(f'<div style="text-align:right;color:{MUTED};font-size:.8rem">CUSTOMER CARE<br><b style="color:{INK}">Here to help</b></div>', unsafe_allow_html=True)
st.divider()

page = st.session_state.page
if page == "Home":
    st.markdown("""<div class="hero"><div class="square"><h1>Reference answers.<br>Made easy.</h1><p>Meet the SmartShop BD Assistant. Ask about products, delivery, warranties, and returns—with answers grounded in our available information.</p></div>""", unsafe_allow_html=True)
    cols = st.columns(3, gap="medium")
    cards = [
        ("🛍️", "Product information", "Check listed prices, product details, and warranty periods."),
        ("📦", "Delivery & returns", "Find delivery fees, estimated delivery times, and return conditions."),
        ("💡", "Helpful by design", "When a detail is missing, the assistant tells you instead of guessing."),
    ]
    for col, (icon, title, desc) in zip(cols, cards):
        with col:
            st.markdown(f'<div class="feature-card"><div class="feature-icon">{icon}</div><div class="feature-title">{title}</div><div class="feature-copy">{desc}</div></div>', unsafe_allow_html=True)
    st.write("")
    st.markdown('<div class="section-label">TRY ASKING</div>', unsafe_allow_html=True)
    prompts = ["What is the delivery fee outside Dhaka?", "What is the price and warranty of the Nova A1 Smartphone?", "How can I contact customer support?", "Does the EchoBuds Lite support wireless charging?"]
    pcols = st.columns(2)
    for i, prompt in enumerate(prompts):
        with pcols[i % 2]:
            if st.button("↗  " + prompt, key=f"home_prompt_{i}", use_container_width=True):
                st.session_state.pending_question = prompt
                navigate("AI Assistant")
    st.write("")
    if st.button("Chat with the assistant →", type="primary"):
        navigate("AI Assistant")

elif page == "AI Assistant":
    left, right = st.columns([4, 1], vertical_alignment="center")
    with left:
        st.markdown('<div class="eyebrow">SMARTSHOP BD · SUPPORT</div>', unsafe_allow_html=True)
        st.title("How can we help?")
        st.markdown(f'<p style="color:{MUTED}">Ask about products, delivery, warranty, or returns.</p>', unsafe_allow_html=True)
    with right:
        clear_col1, clear_col2 = st.columns(2, gap="small")
        with clear_col1:
            if st.button("＋ New chat", use_container_width=True):
                st.session_state.chat_messages = []
                st.session_state.pop("pending_question", None)
                st.rerun()
        with clear_col2:
            if st.button("Clear history", use_container_width=True):
                st.session_state.chat_messages = []
                st.session_state.pop("pending_question", None)
                st.rerun()
    if not st.session_state.chat_messages:
        st.markdown(f'<div class="hero" style="padding:1.4rem 1.6rem"><div class="pill">● Assistant online</div><h2 style="font-size:1.8rem">Welcome to SmartShop BD</h2><p style="margin-bottom:0">I can help with the information in our product and policy documents. If something is not listed, I will let you know.</p></div>', unsafe_allow_html=True)
    st.markdown('<div class="section-label">POPULAR QUESTIONS</div>', unsafe_allow_html=True)
    qs = ["What is the delivery fee outside Dhaka?", "What is the price of the Nova A1 Smartphone?", "How can I contact customer support?", "What is the return window?"]
    qcols = st.columns(2)
    for i, q in enumerate(qs):
        with qcols[i % 2]:
            if st.button(q, key=f"chat_suggestion_{i}", use_container_width=True):
                st.session_state.pending_question = q
                st.rerun()
    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"], avatar="🛍️" if message["role"] == "assistant" else "👤"):
            st.markdown(message["content"])
            show_sources(message.get("sources", []))
            if message.get("abstained"): st.caption("I couldn't verify that detail from the available information.")
    typed = st.chat_input("Ask about products, delivery, warranty, or returns…")
    question = typed or st.session_state.pop("pending_question", None)
    if question:
        st.session_state.chat_messages.append({"role": "user", "content": question})
        with st.chat_message("user", avatar="👤"): st.markdown(question)
        with st.chat_message("assistant", avatar="🛍️"):
            with st.spinner("Checking the available information…"):
                try:
                    if rag_retriever is None:
                        raise RuntimeError(f"Retriever could not load: {RETRIEVER_ERROR}")
                    result = answer_question(question, rag_retriever)
                    answer = clean_answer(result.get("answer", "I couldn't prepare an answer right now."))
                    sources = result.get("sources", [])
                    abstained = bool(result.get("abstained", False))
                    st.markdown(answer)
                    show_sources(sources)
                    if abstained: st.caption("I couldn't verify that detail from the available information.")
                    st.session_state.chat_messages.append({"role":"assistant","content":answer,"sources":sources,"abstained":abstained})
                except Exception as exc:
                    # Show a safe diagnostic so a failed API/config call can be fixed,
                    # without printing environment variables or API keys.
                    detail = f"{type(exc).__name__}: {str(exc)[:350]}"
                    st.error("The assistant couldn't complete this request. Check the terminal for the full traceback.")
                    st.caption(f"Diagnostic: {detail}")
                    st.session_state.chat_messages.append({
                        "role": "assistant",
                        "content": "I couldn't complete that request just now. Please try again in a moment.",
                        "sources": [],
                        "abstained": True,
                    })

elif page == "Evaluation":
    st.markdown('<div class="eyebrow">QUALITY & TESTING</div>', unsafe_allow_html=True)
    eval_title, eval_actions = st.columns([3, 1], vertical_alignment="center")
    with eval_title:
        st.title("Evaluation overview")
    with eval_actions:
        if st.button("🗑️ Clear evaluation history", key="clear_evaluation_history", use_container_width=True):
            failed_deletions = []
            for saved_file in (RESULTS_PATH, SUMMARY_PATH):
                try:
                    if saved_file.exists():
                        saved_file.unlink()
                except OSError:
                    failed_deletions.append(saved_file.name)
            if failed_deletions:
                st.error("Could not delete: " + ", ".join(failed_deletions))
            else:
                st.session_state["evaluation_history_cleared"] = True
                st.rerun()
    st.markdown(f'<p style="color:{MUTED}">Latest saved evaluation results for the sample knowledge assistant.</p>', unsafe_allow_html=True)
    try:
        summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        summary = {}
    if not summary:
        st.info("No evaluation results to display yet.")
    else:
        metrics = [
            ("Test questions", str(summary.get("test_count", "—"))),
            ("Retrieval Hit Rate@k", f'{summary["retrieval_hit_rate_at_k"]:.0%}' if isinstance(summary.get("retrieval_hit_rate_at_k"), (float,int)) else "—"),
            ("Reference-fact coverage", f'{summary["mean_reference_fact_coverage"]:.1%}' if isinstance(summary.get("mean_reference_fact_coverage"), (float,int)) else "—"),
            ("Mean response time", f'{summary["mean_latency_seconds"]:.2f} s' if isinstance(summary.get("mean_latency_seconds"), (float,int)) else "—"),
        ]
        cols = st.columns(4)
        for col, (label, value) in zip(cols, metrics): col.metric(label, value)
        st.write("")
        a, b = st.columns(2)
        with a:
            st.markdown("#### Answer handling")
            col1, col2 = st.columns(2)
            col1.metric("Automated outcome rate", f'{summary.get("overall_correct_outcome_rate", 0):.0%}')
            col2.metric("Unanswerable handling", f'{summary.get("unanswerable_handling_rate", 0):.0%}')
            st.caption("Automated outcome is a label/abstention check, not semantic accuracy.")
        with b:
            st.markdown("#### Runtime")
            col1, col2 = st.columns(2)
            col1.metric("Median response", f'{summary.get("median_latency_seconds", 0):.2f} s')
            col2.metric("Runtime errors", str(summary.get("error_count", "—")))
            st.caption("Latency varies with model initialization, network conditions, and the external LLM API.")
        if RESULTS_PATH.exists():
            with st.expander("View individual test cases"):
                try:
                    import pandas as pd
                    df = pd.read_csv(RESULTS_PATH)
                    visible = [c for c in ["id","question","abstained","abstention_reason","total_seconds"] if c in df.columns]
                    st.dataframe(df[visible], use_container_width=True, hide_index=True)
                except Exception:
                    st.caption("The saved CSV could not be displayed.")

elif page == "Contact":
    st.markdown('<div class="eyebrow">CONTACT</div>', unsafe_allow_html=True)
    st.title("Let's connect.")
    st.markdown(f'<p style="color:{MUTED}">For SmartShop BD support, use the sample customer-care details. For project or developer enquiries, contact the creator below.</p>', unsafe_allow_html=True)
    a, b = st.columns(2, gap="large")
    with a:
        with st.container(border=True):
            st.subheader("SmartShop BD support")
            st.markdown("**Email**")
            st.markdown("[support@smartshop.example](mailto:support@smartshop.example)")
            st.markdown("**Phone**")
            st.markdown("[09610000000](tel:09610000000)")
            st.markdown("**Support hours**")
            st.write("Saturday–Thursday, 9:00 AM–6:00 PM Bangladesh time")
            st.caption("Sample customer-support details for the fictional knowledge base.")
    with b:
        with st.container(border=True):
            st.subheader("Project creator")
            st.markdown("**Talha Jobayer Zihan**")
            st.write("Researcher & AI/ML Engineer")
            st.markdown("**Email**")
            st.markdown("[jobayertalha2020@gmail.com](mailto:jobayertalha2020@gmail.com)")
            st.markdown("**Phone**")
            st.markdown("[+880 1721 577792](tel:+8801721577792)")
            st.markdown("**LinkedIn**")
            st.markdown("[linkedin.com/in/talha-jobayer](https://www.linkedin.com/in/talha-jobayer-696a74237/)")
            st.markdown("**GitHub**")
            st.markdown("[github.com/jobayertalha](https://github.com/jobayertalha)")
            st.markdown("**Portfolio**")
            st.markdown("[Personal Portfolio](https://v0-personal-portfolio-site-tau.vercel.app/)")
    st.info("This is a demonstration using a fictional SmartShop BD knowledge base.")
    st.markdown("### About this assistant")
    st.write("A retrieval-augmented question-answering prototype that answers from the available knowledge base and abstains when it cannot verify a detail.")

st.divider()
f1, f2 = st.columns([3, 2])
with f1: st.caption("© SmartShop BD · AI Customer Assistant")
with f2: st.markdown(f'<div style="text-align:right;color:{MUTED};font-size:.78rem">Warm, helpful, grounded in available information</div>', unsafe_allow_html=True)