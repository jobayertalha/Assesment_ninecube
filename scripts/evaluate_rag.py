"""Run a repeatable evaluation against the real retrieval + Groq generation pipeline.

Usage: python scripts/evaluate_rag.py
Requires a built FAISS index and GROQ_API_KEY. Manual-review columns are deliberately
left blank; fill them using docs/evaluation_report.md's rubric after inspecting outputs.
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
from rag import Retriever, INDEX_DIR, DEFAULT_TOP_K

DATA = ROOT / "data" / "evaluation_questions.jsonl"
OUT = ROOT / "results" / "evaluation_results.csv"
SUMMARY = ROOT / "results" / "evaluation_summary.json"


def norm(text: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def main():
    cases = [json.loads(line) for line in DATA.read_text(encoding="utf-8").splitlines() if line.strip()]
    retriever = Retriever().load(INDEX_DIR)
    rows, latencies = [], []
    for i, case in enumerate(cases, 1):
        start = time.perf_counter()
        try:
            result = answer_question(case["question"], retriever)
            error = ""
        except Exception as exc:
            result = {"answer": "", "sources": [], "retrieval": [], "abstained": True, "reason": "error"}
            error = f"{type(exc).__name__}: {exc}"
        total = time.perf_counter() - start
        latencies.append(total)
        retrieved_sources = sorted({item["source"] for item in result.get("retrieval", [])})
        expected_sources = case.get("expected_sources", [])
        retrieval_hit = (all(source in retrieved_sources for source in expected_sources)) if case["answerable"] and expected_sources else None
        retrieved_chunks = result.get("retrieval", [])
        precision_at_k = (sum(1 for item in retrieved_chunks if item["source"] in expected_sources) / len(retrieved_chunks)) if case["answerable"] and expected_sources and retrieved_chunks else (0.0 if case["answerable"] and expected_sources else None)
        answer_norm = norm(result.get("answer", ""))
        required_facts = case.get("required_facts", [])
        found_facts = [fact for fact in required_facts if norm(fact) in answer_norm]
        fact_coverage = len(found_facts) / len(required_facts) if required_facts else None
        if case.get("ambiguous", False):
            abstention_success = bool(result.get("abstained"))
        else:
            abstention_success = bool(result.get("abstained")) == (not case["answerable"])
        rows.append({
            "id": case["id"], "category": case["category"], "question": case["question"],
            "expected_answer": case["expected_answer"], "expected_sources": ";".join(expected_sources),
            "retrieved_sources": ";".join(retrieved_sources),
            "retrieval_hit": "" if retrieval_hit is None else int(retrieval_hit),
            "retrieval_precision_at_k": "" if precision_at_k is None else round(precision_at_k, 3),
            "answer": result.get("answer", ""), "abstained": int(bool(result.get("abstained"))),
            "abstention_success": int(abstention_success),
            "reference_fact_coverage": "" if fact_coverage is None else round(fact_coverage, 3),
            "retrieval_seconds": round(result.get("retrieval_seconds", 0.0), 4),
            "generation_seconds": round(result.get("generation_seconds", 0.0), 4),
            "total_seconds": round(total, 4), "error": error,
            "answer_relevance_manual_0_1": "", "grounding_manual_0_1": "", "reviewer_notes": "",
        })
        print(f"[{i:02d}/{len(cases)}] {case['id']} | {total:.2f}s | abstained={result.get('abstained')} | {case['question']}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    answerable_rows = [row for row, case in zip(rows, cases) if case["answerable"]]
    retrieval_values = [int(row["retrieval_hit"]) for row in answerable_rows if row["retrieval_hit"] != ""]
    fact_values = [float(row["reference_fact_coverage"]) for row in rows if row["reference_fact_coverage"] != ""]
    precision_values = [float(row["retrieval_precision_at_k"]) for row in answerable_rows if row["retrieval_precision_at_k"] != ""]
    lat_sorted = sorted(latencies)
    summary = {
        "test_count": len(rows),
        "answerable_count": sum(case["answerable"] for case in cases),
        "retrieval_hit_rate_at_k": round(sum(retrieval_values) / len(retrieval_values), 4) if retrieval_values else None,
        "mean_retrieval_precision_at_k_source_level": round(statistics.mean(precision_values), 4) if precision_values else None,
        "mean_reference_fact_coverage": round(statistics.mean(fact_values), 4) if fact_values else None,
        "correct_abstention_count": sum(int(row["abstention_success"]) for row in rows),
        "correct_abstention_rate": round(sum(int(row["abstention_success"]) for row in rows) / len(rows), 4) if rows else None,
        "mean_latency_seconds": round(statistics.mean(latencies), 4) if latencies else None,
        "median_latency_seconds": round(statistics.median(latencies), 4) if latencies else None,
        "p95_latency_seconds_descriptive_small_sample": round(lat_sorted[min(len(lat_sorted)-1, max(0, int(0.95 * len(lat_sorted))))], 4) if lat_sorted else None,
        "top_k": DEFAULT_TOP_K,
        "note": "Actual values from this run. Reference-fact coverage is a simple automated check, not a complete semantic correctness metric. Review answer relevance and grounding manually in the CSV.",
    }
    SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("\nSummary")
    for key, value in summary.items():
        print(f"{key}: {value}")
    print(f"\nWrote {OUT.relative_to(ROOT)} and {SUMMARY.relative_to(ROOT)}")
    print("Next: fill the two manual-review columns using docs/evaluation_report.md.")


if __name__ == "__main__":
    main()
