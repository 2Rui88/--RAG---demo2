import json
from pathlib import Path

from app.rag.index_manager import RagIndexManager


class FakeEmbeddingClient:
    def __init__(self) -> None:
        self.calls = 0

    def embed_texts(self, texts):
        self.calls += 1
        return [[1.0, 0.0, 0.0] for _ in texts]


def write_chunks(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "chunk_id": "c1",
                "type": "policy_chunk",
                "content": "成人高考报名时间",
                "source_title": "报名公告",
                "source_url": "https://example.test",
                "year": "2025",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return path


def test_index_manager_builds_cache_and_loads_service(tmp_path):
    chunks_path = write_chunks(tmp_path / "chunks.jsonl")
    cache_path = tmp_path / "vector_index.json"
    client = FakeEmbeddingClient()
    manager = RagIndexManager(chunks_path=chunks_path, vector_cache_path=cache_path, embedding_client=client, embedding_dimension=3)

    service = manager.load()

    assert cache_path.exists()
    assert client.calls == 1
    assert service.answer("报名时间") is not None


def test_index_manager_rebuild_forces_embedding_refresh(tmp_path):
    chunks_path = write_chunks(tmp_path / "chunks.jsonl")
    cache_path = tmp_path / "vector_index.json"
    client = FakeEmbeddingClient()
    manager = RagIndexManager(chunks_path=chunks_path, vector_cache_path=cache_path, embedding_client=client, embedding_dimension=3)
    manager.load()

    summary = manager.rebuild()

    assert summary["chunk_count"] == 1
    assert summary["embedding_dimension"] == 3
    assert client.calls == 2
