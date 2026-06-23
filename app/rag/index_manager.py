from __future__ import annotations

from pathlib import Path

from app.rag.embedding import DEFAULT_EMBEDDING_DIMENSION, TongyiEmbeddingClient
from app.rag.service import RagGenerator, RagService
from app.rag.vector_index import EmbeddingClient, VectorIndex


class RagIndexManager:
    def __init__(
        self,
        *,
        chunks_path: Path,
        vector_cache_path: Path,
        embedding_client: EmbeddingClient | None = None,
        generator: RagGenerator | None = None,
        embedding_dimension: int = DEFAULT_EMBEDDING_DIMENSION,
    ) -> None:
        self.chunks_path = chunks_path
        self.vector_cache_path = vector_cache_path
        self.embedding_client = embedding_client or TongyiEmbeddingClient(embedding_dimension=embedding_dimension)
        self.generator = generator
        self.embedding_dimension = embedding_dimension
        self.service: RagService | None = None

    def load(self) -> RagService:
        vector_index = VectorIndex.load_or_build(
            self.chunks_path,
            self.vector_cache_path,
            self.embedding_client,
            embedding_dimension=self.embedding_dimension,
        )
        self.service = RagService.from_jsonl(
            self.chunks_path,
            vector_index=vector_index,
            embedding_client=self.embedding_client,
            generator=self.generator,
        )
        return self.service

    def rebuild(self) -> dict[str, int | str]:
        vector_index = VectorIndex.load_or_build(
            self.chunks_path,
            self.vector_cache_path,
            self.embedding_client,
            embedding_dimension=self.embedding_dimension,
            force_rebuild=True,
        )
        self.service = RagService.from_jsonl(
            self.chunks_path,
            vector_index=vector_index,
            embedding_client=self.embedding_client,
            generator=self.generator,
        )
        return {
            "status": "ok",
            "chunk_count": len(vector_index.items),
            "embedding_dimension": self.embedding_dimension,
        }
