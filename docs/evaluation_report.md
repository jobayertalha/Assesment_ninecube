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

### Test run and environment

- **Test set:** `data/evaluation_questions.jsonl`
- **Test cases:** 12
- **Configured retrieval top-k:** 4
- **Runtime errors:** 0
- **Environment:** Python 3.11.13 in GitHub Codespaces; results obtained using the configured embedding model and Groq API.
- **Test run date:** 14 October 2026 (local date; confirm the actual run timestamp if recording a more precise date).

### Automated results

| Metric | Result |
|---|---:|
| Retrieval Hit Rate@4 | 100% |
| Mean source-level Precision@4 | 43.75% |
| Mean reference-fact coverage | 93.75% |
| Automated correct-outcome rate | 100% (12/12) |
| Unanswerable-question handling | 100% (3/3) |
| Ambiguous-question handling | 100% (1/1) |
| Mean end-to-end latency | 1.12 seconds |
| Median end-to-end latency | 0.94 seconds |
| Descriptive P95 latency | 2.70 seconds |
| Runtime errors | 0 |

The automated correct-outcome rate is based on the expected answerability labels and the assistant's abstention metadata. It should not be interpreted as a 100% semantic accuracy score. Retrieval Hit Rate@4 measures whether the expected source files appear in the retrieved results for answerable questions; it does not establish that every retrieved passage is relevant. Reference-fact coverage is based on normalized literal text matching.

### Manual review

Manual review should verify whether each response directly answers the question and whether its material factual claims are supported by the retrieved passages. The final answer-relevance and factual-grounding rates must be calculated from the completed manual-review columns in `results/evaluation_results.csv`.

### Observed limitations

1. **Retrieval precision:** The mean source-level Precision@4 is 43.75%. For example, Q01 and Q08 retrieve three source files although the expected source is `delivery_policy.md`. The expected source is present, but additional retrieved sources reduce precision under the current metric.
2. **Reference-fact coverage:** Q04 has a reference-fact coverage score of 0.50 even though its response correctly gives the seven-calendar-day return window. This illustrates that literal matching may penalize concise answers or differences in how required facts are expressed. The response should be judged against the question and reference answer rather than this metric alone.

The test set did not show a runtime failure or an incorrect automated abstention outcome. The missing wireless-charging and battery-capacity specifications were handled through abstention (Q09 and Q10), and the ambiguous question prompted clarification (Q11). These are successful test cases, not observed failures.

### Improvement experiment

The return-window retrieval issue was addressed with an explicit return-window statement in `warranty_returns.md` and a targeted evidence check in `agent.py`. In the latest run, Q04 returned the seven-calendar-day window instead of abstaining. The latest mean reference-fact coverage is 93.75%, and the mean latency is 1.12 seconds.

These results demonstrate the behavior of the updated implementation. A rigorous before-and-after comparison requires preserved baseline and updated CSV files evaluated under comparable conditions. Without those artifacts, the results should not be presented as a controlled experiment proving that the change improved overall accuracy.

### Limitations

This evaluation uses only 12 questions over a small synthetic business knowledge base. Retrieval and latency measurements are sensitive to the question set, embedding model, relevance threshold, and external API conditions. Literal reference-fact coverage and source-level retrieval precision are proxies rather than complete semantic metrics. Human review is necessary to assess relevance and grounding. A production deployment would require a larger representative test set, access controls, privacy review, monitoring, and robust document/version management.
