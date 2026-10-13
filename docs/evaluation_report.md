# Task 3 — Evaluation & Testing Report

## Status and reproducibility

This report describes the evaluation method for the Business Knowledge Assistant. **Do not report results until `python ingest.py` and `python scripts/evaluate_rag.py` have been run in the target environment.** The script writes actual measured outputs to `results/evaluation_results.csv` and aggregate measurements to `results/evaluation_summary.json`. The repository intentionally contains no fabricated performance values.

## Test design

The fixed test set is `data/evaluation_questions.jsonl`. It contains answerable factual questions, multi-fact questions, unknown-information questions, an ambiguous question, and an unrelated question. Expected answers and expected source files are defined before running the model. Sample facts are synthetic and are supported by the Markdown files under `data/knowledge_base/`.

## Metrics

- **Retrieval Hit Rate@k:** fraction of answerable questions for which all expected source files appear among the top-k retrieved chunks. The current configured k is printed in the generated summary.
- **Source-level Precision@k:** fraction of retrieved chunks whose source file is one of the expected source files, averaged over answerable questions. This is a practical source-level proxy, not human passage-level relevance labeling.
- **Reference-fact coverage:** fraction of required answer facts that appear as normalized text in the generated answer. This is a lightweight automatic check, not a complete semantic correctness metric; paraphrases may be undercounted.
- **Answer relevance (manual):** score 1 if the response directly addresses the question; otherwise 0. Use the `answer_relevance_manual_0_1` CSV column.
- **Factual grounding (manual):** score 1 if all material factual claims are supported by the retrieved source passages; otherwise 0. Use the `grounding_manual_0_1` CSV column and add a note for unsupported claims.
- **Correct abstention:** whether the assistant abstains for unknown or ambiguous questions. Inspect the CSV; the summary's automated rate is a first-pass check, not a replacement for manual review.
- **Latency:** elapsed end-to-end seconds per question, with retrieval and generation components recorded where available. Mean and median are reported. P95 on a small test set is descriptive only.

## Manual review rubric

Review each generated answer alongside its expected answer and retrieved passages. Fill both manual-review columns in the CSV. Do not score an answer as grounded merely because it cites a source; verify that the cited passage supports the claim. A safe abstention for a genuinely unknown question counts as successful behavior, not a failed factual answer.

## Failure cases to test and document

1. **Missing product specification:** ask whether EchoBuds Lite supports wireless charging. That specification is deliberately absent. Failure occurs if the application invents an answer rather than abstaining.
2. **Retrieval confusion:** ask a question containing terms shared by multiple product/policy passages. Failure occurs if the top-k results omit the expected source or the generated answer mixes facts from different products.

Record what actually happened in the CSV/reviewer notes. If these scenarios do not fail in a run, report them as tests that passed or as potential limitations—not as observed failures.

## Improvement experiment

Baseline: run the fixed set using the initial chunk size, top-k and relevance threshold. Inspect misses and unsupported answers. Make one targeted change at a time (for example, adjust chunk boundaries or the relevance threshold based on inspected examples), rerun the same questions, and compare the generated summary and CSV. Preserve both baseline and improved CSV files under distinct names before rerunning if you want a clean before/after comparison. Only claim an improvement when the measured results support it; discuss trade-offs such as increased abstention or latency.

## Results

Populate this section after running the evaluation:

- Test run date / environment: [fill in]
- Retrieval Hit Rate@k: [from evaluation_summary.json]
- Mean reference-fact coverage: [from evaluation_summary.json]
- Correct abstention rate: [from evaluation_summary.json, then verify manually]
- Mean / median latency: [from evaluation_summary.json]
- Answer relevance rate from manual review: [calculate from CSV]
- Factual grounding rate from manual review: [calculate from CSV]
- Two actual failures or limitations: [cite question IDs and observed outputs]
- Improvement and before/after evidence: [document measured comparison]

## Limitations

This is a small synthetic-data proof of concept, not a production benchmark. The dataset is narrow; cosine-similarity thresholds depend on the embedding model and data; the simple reference-fact coverage check can miss paraphrases and may not detect every hallucination; latency depends on network/API conditions; and human review is needed for semantic relevance and factual grounding. Production deployment would require a larger representative evaluation set, access controls, privacy review, monitoring, and more robust document/version management.
