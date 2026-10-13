"""Source-aware RAG retrieval for the Business Knowledge Assistant.

Markdown files -> chunks -> Sentence Transformers embeddings -> normalized FAISS inner-product search.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from dotenv import load_dotenv

load_dotenv()
ROOT = Path(__file__).resolve().parent
KB_DIR = ROOT / "data" / "knowledge_base"
INDEX_DIR = ROOT / "faiss_index"
DEFAULT_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
DEFAULT_TOP_K = int(os.getenv("TOP_K", "4"))
DEFAULT_MIN_SCORE = float(os.getenv("MIN_RELEVANCE_SCORE", "0.38"))


@dataclass
class Chunk:
    text: str
    source: str
    chunk_id: str

    def to_dict(self):
        return asdict(self)


def load_documents(directory: Path = KB_DIR) -> list[tuple[str, str]]:
    """Read Markdown knowledge-base files in deterministic filename order."""
    if not directory.exists():
        raise FileNotFoundError(f"Knowledge-base directory not found: {directory}")
    documents = []
    for path in sorted(directory.glob("*.md")):
        text = path.read_text(encoding="utf-8").strip()
        if text:
            documents.append((path.name, text))
    if not documents:
        raise ValueError(f"No non-empty .md documents found in {directory}")
    return documents


def chunk_text(text: str, chunk_size: int = 900, overlap: int = 140) -> list[str]:
    """Split text into bounded character chunks, preferring paragraph boundaries."""
    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("Require chunk_size > overlap >= 0")
    text = re.sub(r"\n{3,}", "\n\n", text.strip())
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]
    chunks, start = [], 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            boundary = max(text.rfind("\n\n", start, end), text.rfind("\n", start, end), text.rfind(". ", start, end))
            if boundary > start + int(chunk_size * 0.55):
                end = boundary + (2 if text[boundary:boundary + 2] == ". " else 1)
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks


def build_chunks(documents: Iterable[tuple[str, str]], chunk_size: int = 900, overlap: int = 140) -> list[Chunk]:
    chunks = []
    for source, text in documents:
        for i, piece in enumerate(chunk_text(text, chunk_size, overlap)):
            chunks.append(Chunk(text=piece, source=source, chunk_id=f"{source}::chunk-{i + 1}"))
    if not chunks:
        raise ValueError("No text chunks were created from the knowledge base")
    return chunks


class Retriever:
    def __init__(self, model_name: str = DEFAULT_MODEL):
        # Heavy ML dependencies are loaded only when an index is built or loaded.
        from sentence_transformers import SentenceTransformer
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        self.index = None
        self.chunks: list[Chunk] = []

    def build(self, chunks: list[Chunk]):
        import faiss
        import numpy as np
        vectors = self.model.encode(
            [chunk.text for chunk in chunks], convert_to_numpy=True,
            normalize_embeddings=True, show_progress_bar=False
        )
        vectors = np.asarray(vectors, dtype="float32")
        index = faiss.IndexFlatIP(vectors.shape[1])
        index.add(vectors)
        self.index, self.chunks = index, chunks
        return self

    def save(self, directory: Path = INDEX_DIR):
        import faiss
        if self.index is None or not self.chunks:
            raise RuntimeError("Build the index before saving")
        directory.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(directory / "index.faiss"))
        (directory / "chunks.json").write_text(
            json.dumps([chunk.to_dict() for chunk in self.chunks], ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (directory / "metadata.json").write_text(
            json.dumps({"model_name": self.model_name, "chunk_count": len(self.chunks)}, indent=2), encoding="utf-8"
        )

    def load(self, directory: Path = INDEX_DIR):
        import faiss
        index_path, chunks_path, meta_path = directory / "index.faiss", directory / "chunks.json", directory / "metadata.json"
        if not (index_path.exists() and chunks_path.exists() and meta_path.exists()):
            raise FileNotFoundError("FAISS index is missing. Run `python ingest.py` first.")
        metadata = json.loads(meta_path.read_text(encoding="utf-8"))
        if metadata.get("model_name") != self.model_name:
            raise ValueError("Embedding model differs from the model used to build the index. Re-run `python ingest.py`.")
        self.index = faiss.read_index(str(index_path))
        self.chunks = [Chunk(**item) for item in json.loads(chunks_path.read_text(encoding="utf-8"))]
        if self.index.ntotal != len(self.chunks):
            raise ValueError("FAISS index and chunk metadata counts do not match. Rebuild the index.")
        return self

    def retrieve(self, question: str, top_k: int = DEFAULT_TOP_K) -> list[dict]:
        import numpy as np
        if not question or not question.strip():
            raise ValueError("Question cannot be empty")
        if self.index is None:
            raise RuntimeError("Retriever is not built or loaded")
        query = self.model.encode([question.strip()], convert_to_numpy=True, normalize_embeddings=True)
        query = np.asarray(query, dtype="float32")
        k = min(max(1, int(top_k)), len(self.chunks))
        scores, indices = self.index.search(query, k)
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            chunk = self.chunks[int(idx)]
            results.append({"text": chunk.text, "source": chunk.source, "chunk_id": chunk.chunk_id, "score": float(score)})
        return results


def is_ambiguous_question(question: str) -> bool:
    """Catch common underspecified price/cost questions before retrieval."""
    q = re.sub(r"[^a-z0-9\s]", " ", question.lower())
    q = re.sub(r"\s+", " ", q).strip()
    patterns = [
        r"^(how much( does it cost)?|what is the price|how much is it)( please)?$",
        r"^(how much does (this|that|it) cost)( please)?$",
        r"^(what does it cost)( please)?$",
    ]
    return any(re.fullmatch(pattern, q) for pattern in patterns)


def context_is_sufficient(results: list[dict], min_score: float = DEFAULT_MIN_SCORE) -> bool:
    return bool(results) and float(results[0]["score"]) >= min_score


def format_context(results: list[dict]) -> str:
    return "\n\n".join(
        f"[Source: {item['source']} | similarity: {item['score']:.3f}]\n{item['text']}"
        for item in results
    )
