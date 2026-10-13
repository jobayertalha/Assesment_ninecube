# Business Knowledge Assistant — RAG Proof of Concept

A small, source-aware question-answering application for a fictional Bangladeshi retailer, SmartShop BD. It retrieves relevant passages from a local Markdown knowledge base and uses an LLM to draft answers grounded in those passages. If retrieval is insufficient, it abstains rather than guessing.

> **Assessment data notice:** SmartShop BD, products, prices, phone number, email address and policies in this repository are synthetic examples created for the NineCube Digital technical assessment. They do not describe a real business.

## What is implemented

- Markdown document ingestion and overlapping text chunking.
- Sentence Transformers embeddings (`all-MiniLM-L6-v2` by default).
- FAISS inner-product search over normalized vectors (cosine similarity).
- Source metadata preserved per chunk and shown in the UI.
- Groq API answer generation with evidence-only instructions and source filenames.
- Basic ambiguity handling and retrieval-threshold fallback.
- Streamlit interface with answers, sources and expandable retrieved passages.
- Repeatable evaluation runner, CSV outputs and offline unit tests.

## Architecture

```text
Markdown knowledge base
        ↓
Load + chunk + source metadata
        ↓
Sentence Transformers embeddings (normalized)
        ↓
FAISS IndexFlatIP (cosine similarity)
        ↓
Top-k retrieval + relevance threshold
        ↓
Groq LLM (evidence-only prompt)
        ↓
Answer with source filenames OR safe abstention
```

The evaluation script calls the same retrieval and generation functions as the application. It reports retrieval hit rate, source-level Precision@k, simple reference-fact coverage, correct-abstention checks, and measured latency. Answer relevance and factual grounding are deliberately included as manual-review fields because automated string checks alone cannot reliably judge semantic correctness.

## Technology choices

| Technology | Why it is used |
|---|---|
| Python | Application and evaluation logic |
| Streamlit | Minimal chat interface; no separate frontend/API server needed |
| Sentence Transformers | Local semantic embeddings |
| FAISS | Lightweight vector similarity search for a small static knowledge base |
| Groq API | LLM answer generation without training a model |
| pytest | Basic deterministic unit tests |

LangChain, FastAPI, PostgreSQL, Docker, a hosted vector database and agent orchestration are intentionally omitted: they are not needed for this small proof of concept.

## Run in GitHub Codespaces

1. Upload/push this project folder to your GitHub repository and open it in Codespaces. The `.devcontainer` configuration uses Python 3.11 and installs `requirements.txt`.
2. In the terminal, create your local environment file:

   ```bash
   cp .env.example .env
   ```

3. Edit `.env` and set `GROQ_API_KEY` to a valid key. Never commit `.env` or expose the key in screenshots.
4. Build the local index:

   ```bash
   python ingest.py
   ```

   The first run downloads the embedding model and may take a few minutes. The index is generated under `faiss_index/` and is excluded from Git.
5. Run the app:

   ```bash
   streamlit run app.py --server.address 0.0.0.0
   ```

   Open forwarded port 8501 in Codespaces.

## Run tests and evaluation

Run deterministic unit tests (no Groq API key or embedding download required):

```bash
pytest -q
```

Run the end-to-end evaluation (requires the FAISS index and a valid `GROQ_API_KEY`):

```bash
python scripts/evaluate_rag.py
```

The script writes:

- `results/evaluation_results.csv` — per-question retrieval sources, generated answers, reference-fact coverage, abstention checks and timings; manual-review columns are blank until reviewed.
- `results/evaluation_summary.json` — aggregate actual measurements from that run.

Review the outputs and fill `answer_relevance_manual_0_1`, `grounding_manual_0_1`, and reviewer notes in the CSV according to `docs/evaluation_report.md`. Preserve the baseline CSV before changing settings, then rerun the same test set to measure an improvement. Do not report results that were not measured.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `GROQ_API_KEY` | None | Required for generated answers |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Groq chat model name; confirm availability in your account |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Embedding model; rebuild the index if changed |
| `MIN_RELEVANCE_SCORE` | `0.38` | Initial cosine-similarity threshold; validate against test data |
| `TOP_K` | `4` | Maximum number of chunks retrieved per question |

The threshold is a starting configuration, not a proven universal value. Use the evaluation set to inspect false accepts and false abstentions before changing it. If the embedding model changes, rebuild the FAISS index with `python ingest.py`.

## Project structure

```text
.
├── app.py
├── agent.py
├── rag.py
├── ingest.py
├── requirements.txt
├── runtime.txt
├── .env.example
├── .devcontainer/devcontainer.json
├── data/
│   ├── knowledge_base/       # Synthetic Markdown business documents
│   └── evaluation_questions.jsonl
├── scripts/evaluate_rag.py
├── tests/test_rag.py
├── results/                  # Generated evaluation output; not committed by default
└── docs/
    ├── evaluation_report.md
    ├── demo_script.md
    └── technical_presentation_outline.md
```

## Evaluation design

The fixed test set includes factual questions, questions needing multiple facts, an ambiguous question and unanswerable questions. The evaluation report explains metrics, manual-review rubric, failure-case design and before/after experiment. See `docs/evaluation_report.md`.

## Limitations and security

- The knowledge base is small and synthetic; results do not establish production reliability.
- The cosine threshold needs calibration against representative queries.
- String-based reference-fact coverage may undercount paraphrases and does not detect every hallucination. Manual source-grounding review is required.
- Generation latency depends on API/network conditions and model availability.
- This proof of concept has no authentication, role-based access, audit log or production data-retention controls. Do not load confidential customer records. For a real deployment, use approved data handling, access control, secret management, logging safeguards and a representative security/privacy review.
- The API provider receives the question and retrieved context needed to generate the answer; do not send confidential information without authorization.

## Credits and external resources

The application pattern is adapted from the author's own CareerVector repository, replacing CV/job matching with business-document question answering. The sample business data is synthetic. Core libraries are documented at [Streamlit](https://docs.streamlit.io/), [Sentence Transformers](https://www.sbert.net/), [FAISS](https://github.com/facebookresearch/faiss), and [Groq API documentation](https://console.groq.com/docs). No third-party dataset or external code snippets are bundled.
