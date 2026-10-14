
"""Run a repeatable evaluation against the real retrieval + Groq generation pipeline.

Usage:
    python scripts/evaluate_rag.py

Requires a built FAISS index and GROQ_API_KEY.
Manual-review columns remain blank until reviewed using
docs/evaluation_report.md.
"""

from __future__ import annotations

import csv
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent import answer_question
from rag import DEFAULT_TOP_K, INDEX_DIR, Retriever

DATA = ROOT / "data" / "evaluation_questions.jsonl"
OUT = ROOT / "results" / "evaluation_results.csv"
SUMMARY = ROOT / "results" / "evaluation_summary.json"


def norm(text: str) -> str:
    """Normalize text for simple, literal reference-fact matching."""
    import re

    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def evaluate_case(case: dict, result: dict, total_seconds: float) -> dict:
    """Calculate per-question metrics without claiming semantic correctness."""
    retrieved = result.get("retrieval", [])
    retrieved_sources = sorted(
        {item["source"] for item in retrieved}
    )
    expected_sources = case.get("expected_sources", [])

    answerable = bool(case["answerable"])
    ambiguous = bool(case.get("ambiguous", False))

    # Retrieval metrics apply only to answerable questions with expected sources.
    if answerable and expected_sources:
        retrieval_hit = int(
            all(source in retrieved_sources for source in expected_sources)
        )
        precision_at_k = (
            sum(
                1 for item in retrieved
                if item["source"] in expected_sources
            ) / len(retrieved)
            if retrieved else 0.0
        )
    else:
        retrieval_hit = None
        precision_at_k = None

    answer = result.get("answer", "")
    answer_norm = norm(answer)
    required_facts = case.get("required_facts", [])
    found_facts = [
        fact for fact in required_facts
        if norm(fact) and norm(fact) in answer_norm
    ]
    fact_coverage = (
        len(found_facts) / len(required_facts)
        if required_facts else None
    )

    abstained = bool(result.get("abstained"))

    # An ambiguous question is handled correctly when the system asks for
    # clarification. Otherwise, answerable questions should be answered and
    # unanswerable questions should be handled without unsupported claims.
    if ambiguous:
        correct_outcome = abstained
    else:
        correct_outcome = abstained == (not answerable)

    return {
        "id": case["id"],
        "category": case["category"],
        "question": case["question"],
        "answerable": int(answerable),
        "ambiguous": int(ambiguous),
        "expected_answer": case.get("expected_answer", ""),
        "expected_sources": ";".join(expected_sources),
        "retrieved_sources": ";".join(retrieved_sources),
        "retrieval_hit": (
            "" if retrieval_hit is None else retrieval_hit
        ),
        "retrieval_precision_at_k": (
            "" if precision_at_k is None
            else round(precision_at_k, 3)
        ),
        "answer": answer,
        "abstained": int(abstained),
        "abstention_reason": result.get("reason", ""),
        "correct_outcome": int(correct_outcome),
        "reference_fact_coverage": (
            "" if fact_coverage is None
            else round(fact_coverage, 3)
        ),
        "retrieval_seconds": round(
            result.get("retrieval_seconds", 0.0), 4
        ),
        "generation_seconds": round(
            result.get("generation_seconds", 0.0), 4
        ),
        "total_seconds": round(total_seconds, 4),
        "error": "",
        "answer_relevance_manual_0_1": "",
        "grounding_manual_0_1": "",
        "reviewer_notes": "",
    }


def main() -> None:
    if not DATA.exists():
        raise FileNotFoundError(
            f"Evaluation dataset not found: {DATA}"
        )

    cases = [
        json.loads(line)
        for line in DATA.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    if not cases:
        raise ValueError(
            f"No evaluation questions found in {DATA}"
        )

    retriever = Retriever().load(INDEX_DIR)
    rows = []
    latencies = []

    for i, case in enumerate(cases, 1):
        start = time.perf_counter()

        try:
            result = answer_question(
                case["question"],
                retriever,
            )
            error = ""
        except Exception as exc:
            result = {
                "answer": "",
                "sources": [],
                "retrieval": [],
                "abstained": True,
                "reason": "error",
                "retrieval_seconds": 0.0,
                "generation_seconds": 0.0,
            }
            error = f"{type(exc).__name__}: {exc}"

        total = time.perf_counter() - start
        latencies.append(total)

        row = evaluate_case(case, result, total)
        row["error"] = error
        rows.append(row)

        print(
            f"[{i:02d}/{len(cases)}] {case['id']} | "
            f"{total:.2f}s | "
            f"abstained={result.get('abstained')} | "
            f"correct_outcome={row['correct_outcome']} | "
            f"{case['question']}"
        )

    OUT.parent.mkdir(parents=True, exist_ok=True)

    with OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(rows[0].keys()),
        )
        writer.writeheader()
        writer.writerows(rows)

    answerable_rows = [
        row for row in rows if row["answerable"] == 1
    ]
    unanswerable_rows = [
        row for row in rows
        if row["answerable"] == 0 and row["ambiguous"] == 0
    ]
    ambiguous_rows = [
        row for row in rows if row["ambiguous"] == 1
    ]

    retrieval_values = [
        int(row["retrieval_hit"])
        for row in answerable_rows
        if row["retrieval_hit"] != ""
    ]
    precision_values = [
        float(row["retrieval_precision_at_k"])
        for row in answerable_rows
        if row["retrieval_precision_at_k"] != ""
    ]
    fact_values = [
        float(row["reference_fact_coverage"])
        for row in rows
        if row["reference_fact_coverage"] != ""
    ]

    correct_outcomes = sum(
        int(row["correct_outcome"]) for row in rows
    )
    correct_unanswerable = sum(
        int(row["correct_outcome"]) for row in unanswerable_rows
    )
    correct_ambiguous = sum(
        int(row["correct_outcome"]) for row in ambiguous_rows
    )

    lat_sorted = sorted(latencies)
    # Nearest-rank percentile. With only 12 cases, this is descriptive,
    # not a reliable production latency estimate.
    p95_index = max(
        0,
        min(len(lat_sorted) - 1, int(0.95 * len(lat_sorted) + 0.999999) - 1),
    )

    summary = {
        "test_count": len(rows),
        "answerable_count": len(answerable_rows),
        "unanswerable_count": len(unanswerable_rows),
        "ambiguous_count": len(ambiguous_rows),
        "retrieval_hit_rate_at_k": (
            round(statistics.mean(retrieval_values), 4)
            if retrieval_values else None
        ),
        "mean_retrieval_precision_at_k_source_level": (
            round(statistics.mean(precision_values), 4)
            if precision_values else None
        ),
        "mean_reference_fact_coverage": (
            round(statistics.mean(fact_values), 4)
            if fact_values else None
        ),
        "correct_outcome_count": correct_outcomes,
        "overall_correct_outcome_rate": round(
            correct_outcomes / len(rows), 4
        ),
        "correct_unanswerable_handling_count": correct_unanswerable,
        "unanswerable_handling_rate": (
            round(
                correct_unanswerable / len(unanswerable_rows), 4
            )
            if unanswerable_rows else None
        ),
        "correct_ambiguous_handling_count": correct_ambiguous,
        "ambiguous_handling_rate": (
            round(correct_ambiguous / len(ambiguous_rows), 4)
            if ambiguous_rows else None
        ),
        "mean_latency_seconds": round(
            statistics.mean(latencies), 4
        ),
        "median_latency_seconds": round(
            statistics.median(latencies), 4
        ),
        "p95_latency_seconds_descriptive_small_sample": round(
            lat_sorted[p95_index], 4
        ),
        "top_k": DEFAULT_TOP_K,
        "note": (
            "Reference-fact coverage is literal normalized text matching, "
            "not semantic correctness. Source-level retrieval precision "
            "does not measure ranking quality within a source. Correct "
            "outcome is based on the answerable/ambiguous labels and "
            "abstention metadata; manually review answer relevance and "
            "grounding in the CSV. Errors are treated as incorrect outcomes."
        ),
        "error_count": sum(bool(row["error"]) for row in rows),
    }

    SUMMARY.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    print("\nSummary")
    for key, value in summary.items():
        print(f"{key}: {value}")

    print(f"\nWrote {OUT.relative_to(ROOT)}")
    print(f"Wrote {SUMMARY.relative_to(ROOT)}")
    print(
        "Next: inspect the answers and fill the manual-review columns "
        "using docs/evaluation_report.md."
    )


if __name__ == "__main__":
    main()
