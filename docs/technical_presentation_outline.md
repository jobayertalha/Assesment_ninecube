# Technical Presentation — 6-slide outline

The deliverable presentation is `technical_presentation.pptx`. This outline is the source content.

1. **Problem & Objective** — Repetitive business questions; intended users are customers and support staff; goal is grounded document-based Q&A.
2. **Solution Architecture** — Markdown documents → chunking → Sentence Transformers embeddings → normalized FAISS cosine retrieval → relevance/ambiguity check → Groq LLM → answer with source names or abstention.
3. **Implementation & Stack** — Python, Streamlit, Sentence Transformers, FAISS, Groq API, dotenv, pytest; why each is sufficient; no separate backend/database/container stack.
4. **Evaluation Method** — Fixed 12-question test set; expected sources and facts; retrieval hit rate, reference-fact coverage, manual answer relevance and grounding, abstention, latency.
5. **Results, Failure Cases & Improvement** — Populate only with actual run results; show one successful case and two actual observed failures/limitations; baseline vs improved comparison.
6. **Limitations & Next Steps** — Synthetic narrow dataset, threshold calibration, manual grounding review, API/network latency; next: larger evaluation set, privacy/access controls, monitoring and document updates.

Slide 5 must be updated after actual evaluation. Do not leave generic placeholders in the submitted deck.
