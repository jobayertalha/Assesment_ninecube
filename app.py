"""Streamlit interface for the Business Knowledge Assistant."""
import streamlit as st
from dotenv import load_dotenv
from agent import answer_question
from rag import Retriever, INDEX_DIR

load_dotenv()
st.set_page_config(page_title="Business Knowledge Assistant", page_icon="💬", layout="centered")
st.title("💬 Business Knowledge Assistant")
st.caption("A small RAG proof of concept using synthetic SmartShop BD documents.")
st.info("SmartShop BD is fictional. Product details, prices, and policies are synthetic assessment data.")


@st.cache_resource(show_spinner="Loading the embedding model and knowledge base...")
def load_retriever():
    return Retriever().load(INDEX_DIR)


try:
    retriever = load_retriever()
except Exception as exc:
    st.error(f"The knowledge-base index is not ready: {exc}")
    st.code("python ingest.py\nstreamlit run app.py", language="bash")
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("sources"):
            with st.expander("Sources used"):
                for source in message["sources"]:
                    st.write(f"- `{source['source']}` (similarity {source['score']:.3f})")
        if message.get("retrieval"):
            with st.expander("Retrieved passages (debug view)"):
                for item in message["retrieval"]:
                    st.caption(f"{item['source']} · cosine similarity {item['score']:.3f}")
                    st.write(item["text"])

question = st.chat_input("Ask about products, delivery, warranty, or returns...")
if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        with st.spinner("Finding evidence and preparing an answer..."):
            try:
                result = answer_question(question, retriever)
                st.markdown(result["answer"])
                if result.get("sources"):
                    with st.expander("Sources used"):
                        for source in result["sources"]:
                            st.write(f"- `{source['source']}` (similarity {source['score']:.3f})")
                if result.get("retrieval"):
                    with st.expander("Retrieved passages (debug view)"):
                        for item in result["retrieval"]:
                            st.caption(f"{item['source']} · cosine similarity {item['score']:.3f}")
                            st.write(item["text"])
                st.session_state.messages.append({"role": "assistant", "content": result["answer"], "sources": result.get("sources", []), "retrieval": result.get("retrieval", [])})
            except Exception as exc:
                message = str(exc)
                st.error(message)
                st.session_state.messages.append({"role": "assistant", "content": message})

with st.sidebar:
    st.subheader("Try these questions")
    examples = [
        "What is the delivery fee outside Dhaka?",
        "What is the price and warranty of the Nova A1 Smartphone?",
        "How can I contact customer support?",
        "Does the EchoBuds Lite support wireless charging?",
        "How much does it cost?",
    ]
    for example in examples:
        st.caption(f"• {example}")
    st.divider()
    st.caption("Evaluation: `python scripts/evaluate_rag.py`\n\nTests: `pytest -q`")
