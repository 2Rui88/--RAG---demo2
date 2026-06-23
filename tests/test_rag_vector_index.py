import json
from pathlib import Path

from app.rag.vector_index import VectorIndex


class FakeEmbeddingClient:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(texts)
        return [[float(len(text)), 1.0, 0.0] for text in texts]


def write_vector_chunks(path: Path) -> Path:
    rows = [
        {
            "chunk_id": "a",
            "type": "policy_chunk",
            "content": "广东成人高考报名时间安排",
            "source_title": "报名公告",
            "source_url": "https://example.test/a",
            "year": "2025",
        },
        {
            "chunk_id": "b",
            "type": "policy_chunk",
            "content": "专升本报名条件和学历要求",
            "source_title": "报名条件",
            "source_url": "https://example.test/b",
            "year": "2025",
        },
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows), encoding="utf-8")
    return path


def test_vector_index_builds_and_reuses_cache(tmp_path):
    chunks_path = write_vector_chunks(tmp_path / "chunks.jsonl")
    cache_path = tmp_path / "vector_index.json"
    client = FakeEmbeddingClient()

    first = VectorIndex.load_or_build(chunks_path, cache_path, client, embedding_dimension=3)
    second = VectorIndex.load_or_build(chunks_path, cache_path, client, embedding_dimension=3)

    assert cache_path.exists()
    assert len(first.items) == 2
    assert len(second.items) == 2
    assert len(client.calls) == 1


def test_vector_index_search_returns_cosine_matches(tmp_path):
    chunks_path = write_vector_chunks(tmp_path / "chunks.jsonl")
    cache_path = tmp_path / "vector_index.json"
    client = FakeEmbeddingClient()
    index = VectorIndex.load_or_build(chunks_path, cache_path, client, embedding_dimension=3)

    results = index.search([10.0, 1.0, 0.0], top_k=1)

    assert results[0].chunk_id == "a"
    assert results[0].score > 0
