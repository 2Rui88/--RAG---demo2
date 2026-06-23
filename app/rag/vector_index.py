from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app.rag.retriever import SearchResult


class EmbeddingClient(Protocol):
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        ...


@dataclass
class VectorItem:
    chunk: dict[str, object]
    embedding: list[float]


@dataclass
class VectorMatch:
    chunk_id: str
    score: float
    chunk: dict[str, object]


class VectorIndex:
    def __init__(self, items: list[VectorItem], embedding_dimension: int) -> None:
        self.items = items
        self.embedding_dimension = embedding_dimension

    @classmethod
    def load_or_build(
        cls,
        chunks_path: Path,
        cache_path: Path,
        embedding_client: EmbeddingClient,
        *,
        embedding_dimension: int,
        force_rebuild: bool = False,
    ) -> "VectorIndex":
        if cache_path.exists() and not force_rebuild:
            return cls._load_cache(cache_path)

        chunks = _read_chunks(chunks_path)
        texts = [_embedding_text(chunk) for chunk in chunks]
        embeddings = embedding_client.embed_texts(texts) if texts else []
        items = [
            VectorItem(chunk=chunk, embedding=_fit_dimension(embedding, embedding_dimension))
            for chunk, embedding in zip(chunks, embeddings)
        ]
        index = cls(items, embedding_dimension)
        index.save(cache_path)
        return index

    @classmethod
    def _load_cache(cls, cache_path: Path) -> "VectorIndex":
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
        return cls(
            items=[VectorItem(chunk=item["chunk"], embedding=item["embedding"]) for item in payload["items"]],
            embedding_dimension=int(payload["embedding_dimension"]),
        )

    def save(self, cache_path: Path) -> None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "embedding_dimension": self.embedding_dimension,
            "items": [{"chunk": item.chunk, "embedding": item.embedding} for item in self.items],
        }
        cache_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def search(self, query_embedding: list[float], top_k: int = 5, min_score: float = 0.1) -> list[VectorMatch]:
        query = _fit_dimension(query_embedding, self.embedding_dimension)
        scored: list[VectorMatch] = []
        for item in self.items:
            score = _cosine_similarity(query, item.embedding)
            if score >= min_score:
                scored.append(VectorMatch(chunk_id=str(item.chunk.get("chunk_id", "")), score=score, chunk=item.chunk))
        scored.sort(key=lambda match: match.score, reverse=True)
        return scored[:top_k]


def vector_match_to_search_result(match: VectorMatch) -> SearchResult:
    raw = match.chunk
    return SearchResult(
        chunk_id=str(raw.get("chunk_id", "")),
        type=str(raw.get("type", "")),
        content=str(raw.get("content", "")),
        score=round(match.score, 4),
        source_title=str(raw.get("source_title", "")),
        source_url=str(raw.get("source_url", "")),
        year=str(raw["year"]) if raw.get("year") is not None else None,
        section=str(raw["section"]) if raw.get("section") is not None else None,
        question=str(raw["question"]) if raw.get("question") is not None else None,
        answer=str(raw["answer"]) if raw.get("answer") is not None else None,
    )


def _read_chunks(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _embedding_text(chunk: dict[str, object]) -> str:
    parts = []
    for key in ("question", "answer", "content", "section", "source_title"):
        value = chunk.get(key)
        if isinstance(value, str):
            parts.append(value)
    return "\n".join(parts)


def _fit_dimension(vector: list[float], dimension: int) -> list[float]:
    fitted = [float(value) for value in vector[:dimension]]
    if len(fitted) < dimension:
        fitted.extend([0.0] * (dimension - len(fitted)))
    return fitted


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)
