"""Offline unit tests for deterministic behavior; no API key or model download needed."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rag import chunk_text, build_chunks, context_is_sufficient, is_ambiguous_question, format_context


def test_chunk_text_returns_short_text_unchanged():
    assert chunk_text("small text") == ["small text"]


def test_chunk_text_splits_long_text_and_overlaps():
    text = ("alpha beta gamma delta " * 30).strip()
    chunks = chunk_text(text, chunk_size=100, overlap=20)
    assert len(chunks) > 1
    assert all(len(c) <= 100 for c in chunks)


def test_chunk_text_rejects_invalid_parameters():
    try:
        chunk_text("text", chunk_size=10, overlap=10)
    except ValueError:
        return
    assert False, "Expected invalid chunk parameters to raise ValueError"


def test_build_chunks_preserves_source_metadata():
    chunks = build_chunks([("policy.md", "Delivery costs BDT 120.")])
    assert chunks[0].source == "policy.md"
    assert chunks[0].chunk_id.startswith("policy.md::")


def test_ambiguous_cost_question_is_detected():
    assert is_ambiguous_question("How much does it cost?")


def test_specific_cost_question_is_not_ambiguous():
    assert not is_ambiguous_question("How much does the Nova A1 Smartphone cost?")


def test_context_threshold_requires_a_relevant_top_result():
    assert context_is_sufficient([{"score": 0.7}], 0.38)
    assert not context_is_sufficient([{"score": 0.2}], 0.38)
    assert not context_is_sufficient([], 0.38)


def test_format_context_includes_source_and_evidence():
    formatted = format_context([{"source":"delivery_policy.md", "score":0.8, "text":"Outside Dhaka costs BDT 120."}])
    assert "delivery_policy.md" in formatted
    assert "BDT 120" in formatted
