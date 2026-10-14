# SmartShop BD — Business Knowledge Assistant

A source-aware Retrieval-Augmented Generation (RAG) proof of concept for a fictional Bangladeshi retailer. The app retrieves relevant passages from a small Markdown knowledge base and uses an LLM to draft answers grounded in that evidence. When the available information is insufficient, it is designed to say so rather than guess.

**Live demo:** [Open SmartShop BD](https://cahappnct7c5qsgfxt34uj3.streamlit.app/)  
**Source code:** [GitHub repository](https://github.com/jobayertalha/Assesment_ninecube)

> **Assessment data notice:** SmartShop BD, its products, prices, contact details, and policies are synthetic examples created for the NineCube Digital technical assessment. They do not describe a real business.

## Features

- Loads and chunks Markdown knowledge-base documents with overlapping text chunks.
- Generates local embeddings using Sentence Transformers (`all-MiniLM-L6-v2` by default).
- Uses FAISS inner-product search over normalized vectors for cosine-similarity retrieval.
- Preserves source metadata so answers can show the source filenames and retrieved passages.
- Uses the Groq API for evidence-grounded answer generation.
- Includes a retrieval-threshold fallback and basic ambiguity/abstention handling.
- Provides a Streamlit interface with Home, AI Assistant, Evaluation, and Contact pages.
- Includes a repeatable evaluation runner, CSV/JSON outputs, and offline unit tests.

## How it works

```text
Markdown knowledge base
        ↓
Load documents, chunk text, preserve source metadata
        ↓
Sentence Transformers embeddings (normalized vectors)
        ↓
FAISS IndexFlatIP (cosine-similarity search)
        ↓
Top-k retrieval + relevance threshold
        ↓
Groq LLM with an evidence-only prompt
        ↓
Answer with source filenames OR safe abstention
```

The evaluation runner uses the same retrieval and generation functions as the application. It measures retrieval hit rate, source-level Precision@k, reference-fact coverage, automated abstention checks, and response latency. Answer relevance and factual grounding are included as **manual-review** fields because simple automated checks cannot reliably determine semantic correctness.

## Technology stack

| Technology | Purpose |
|---|---|
| Python | Application, retrieval, ingestion, and evaluation logic |
| Streamlit | Web interface without a separate frontend or API server |
| Sentence Transformers | Local semantic embeddings |
| FAISS | Vector similarity search over the indexed knowledge base |
| Groq API | LLM answer generation |
| pytest | Basic automated tests |

LangChain, FastAPI, PostgreSQL, Docker, a hosted vector database, and agent orchestration are intentionally omitted. They are not necessary for this small proof of concept.

## Run locally or in GitHub Codespaces

### 1. Get the repository

```bash
git clone https://github.com/jobayertalha/Assesment_ninecube.git
cd Assesment_ninecube
```

Alternatively, open the repository in GitHub Codespaces. The `.devcontainer` configuration specifies Python 3.11 and installs the dependencies from `requirements.txt`.

### 2. Configure the API key

```bash
cp .env.example .env
```

Edit `.env` and set a valid `GROQ_API_KEY`. Never commit `.env`, paste the key into source code, or expose it in screenshots.

### 3. Build the knowledge-base index

```bash
python ingest.py
```

The first run downloads the embedding model and may take a few minutes. The generated index is stored in `faiss_index/`, which is excluded from Git.

### 4. Start the app

```bash
streamlit run app.py
```

In Codespaces, open the forwarded port shown for Streamlit (usually port `8501`). If running in a container where external port forwarding requires binding to all interfaces, use:

```bash
streamlit run app.py --server.address 0.0.0.0
```

## Run tests and evaluation

### Unit tests

```bash
pytest -q
```

The unit tests are intended to run without a Groq API key or an embedding-model download.

### End-to-end evaluation

Build the index first and configure `GROQ_API_KEY`, then run:

```bash
python scripts/evaluate_rag.py
```

The script generates:

- `results/evaluation_results.csv` — per-question results, retrieved sources, generated answers, reference-fact coverage, abstention checks, and timing information. Manual-review columns remain blank until reviewed.
- `results/evaluation_summary.json` — aggregate measurements from that evaluation run.

Review each generated answer against the expected answer and retrieved passages. Complete `answer_relevance_manual_0_1`, `grounding_manual_0_1`, and reviewer notes in the CSV as described in `docs/evaluation_report.md`.

**Metric interpretation:** Retrieval hit rate measures whether expected source files were retrieved; reference-fact coverage is a simple text-based proxy; and an automated outcome/abstention rate is not semantic accuracy. Do not report manual review as complete until it has actually been performed. Preserve baseline results before changing settings if conducting a before/after experiment.

## Configuration

| Environment variable | Default | Purpose |
|---|---|---|
| `GROQ_API_KEY` | None | Required for generated answers |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Groq chat model; verify that it is available to your account |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Embedding model; rebuild the index if changed |
| `MIN_RELEVANCE_SCORE` | `0.38` | Initial cosine-similarity threshold; validate using the test set |
| `TOP_K` | `4` | Maximum number of chunks retrieved per question |

The relevance threshold is a starting configuration, not a universally valid value. Inspect false accepts and false abstentions before tuning it. If the embedding model changes, rebuild the index with `python ingest.py`.

## Deploy on Streamlit Community Cloud

1. Push the repository to GitHub.
2. Open [Streamlit Community Cloud](https://share.streamlit.io/) and sign in with GitHub.
3. Create an app using repository `jobayertalha/Assesment_ninecube`, branch `main`, and main file `app.py`.
4. In the app settings, add the API key under **Secrets**:

   ```toml
   GROQ_API_KEY = "your_actual_api_key"
   ```

5. Deploy and test the Home, AI Assistant, Evaluation, and Contact pages.

**Deployment note:** `faiss_index/` is excluded from Git. The app's deployment must ensure the index is generated or otherwise available before the retriever is used. If deployment logs report a missing index, check the app's index-initialization logic and logs. Never commit API keys or other secrets.

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
├── .devcontainer/
│   └── devcontainer.json
├── data/
│   ├── knowledge_base/           # Synthetic Markdown business documents
│   └── evaluation_questions.jsonl
├── scripts/
│   └── evaluate_rag.py
├── tests/
│   └── test_rag.py
├── results/                      # Generated evaluation outputs
└── docs/
    ├── evaluation_report.md
    ├── demo_script.md
    └── technical_presentation_outline.md
```

Generated evaluation outputs may be excluded from Git depending on the repository's ignore rules. Include the final reviewed results in the submission if required.

## Limitations and security

- **Small synthetic corpus:** Results do not establish production performance on a large or real business knowledge base.
- **Threshold sensitivity:** The retrieval threshold needs calibration against representative queries.
- **Approximate automated metrics:** Text-based reference-fact coverage can undercount paraphrases and does not detect every unsupported claim. Manual grounding review is necessary.
- **External dependency:** Answer quality and latency depend on API availability, network conditions, and model behavior.
- **No production access controls:** This proof of concept does not provide authentication, role-based access, audit logging, or production data-retention controls. Do not load confidential customer records.
- **Data sent to the provider:** The LLM provider receives the question and retrieved context required to generate an answer. Do not send confidential information without authorization.
- **Production hardening:** A real deployment should use approved data handling, access control, secret management, logging safeguards, monitoring, and a security/privacy review.

## Credits and external resources

The application pattern is adapted from the author's own CareerVector repository, with the use case changed from CV/job matching to business-document question answering. The SmartShop BD sample business data is synthetic. No third-party dataset is bundled.

- [Streamlit documentation](https://docs.streamlit.io/)
- [Sentence Transformers documentation](https://www.sbert.net/)
- [FAISS repository](https://github.com/facebookresearch/faiss)
- [Groq API documentation](https://console.groq.com/docs)

## Assessment deliverables

The project repository is intended to support the NineCube Digital assessment deliverables:

1. Working prototype and setup documentation.
2. Technical presentation covering the problem, architecture, implementation, evaluation, limitations, and next steps.
3. Short screen recording or live walkthrough.
4. Test questions, outputs, and evaluation findings.

See `docs/evaluation_report.md` for the evaluation method, results, manual-review rubric, and remaining checks.
