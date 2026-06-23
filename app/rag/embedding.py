from __future__ import annotations

import os
import urllib.error
import urllib.request
import json
from typing import Callable

from dotenv import load_dotenv


load_dotenv()


DEFAULT_EMBEDDING_MODEL = "tongyi-embedding-vision-flash-2026-03-06"
DEFAULT_EMBEDDING_DIMENSION = 768
DEFAULT_EMBEDDING_MAX_CHARS = 3000
DEFAULT_EMBEDDING_ENDPOINT = "https://dashscope.aliyuncs.com/api/v1/services/embeddings/multimodal-embedding/multimodal-embedding"


EmbeddingTransport = Callable[[str, dict[str, object], str], dict[str, object]]


class TongyiEmbeddingClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str = DEFAULT_EMBEDDING_MODEL,
        embedding_dimension: int = DEFAULT_EMBEDDING_DIMENSION,
        embedding_max_chars: int = DEFAULT_EMBEDDING_MAX_CHARS,
        endpoint: str = DEFAULT_EMBEDDING_ENDPOINT,
        batch_size: int = 16,
        transport: EmbeddingTransport | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("QWEN_API_KEY", "")
        self.base_url = base_url or os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        self.model = model
        self.embedding_dimension = embedding_dimension
        self.embedding_max_chars = embedding_max_chars
        self.endpoint = endpoint
        self.batch_size = batch_size
        self.transport = transport or _post_json

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        clipped = [text[: self.embedding_max_chars] for text in texts]
        if not clipped:
            return []

        embeddings: list[list[float]] = []
        for start in range(0, len(clipped), self.batch_size):
            batch = clipped[start : start + self.batch_size]
            payload: dict[str, object] = {
                "model": self.model,
                "input": {"contents": [{"text": text} for text in batch]},
                "parameters": {"dimension": self.embedding_dimension},
            }
            response = self.transport(self.endpoint, payload, self.api_key)
            batch_embeddings = _extract_embeddings(response)
            embeddings.extend(batch_embeddings)
        return embeddings


def _post_json(url: str, payload: dict[str, object], api_key: str) -> dict[str, object]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"DashScope embedding request failed: {error.code} {detail}") from error


def _extract_embeddings(response: dict[str, object]) -> list[list[float]]:
    output = response.get("output")
    if not isinstance(output, dict):
        raise RuntimeError("DashScope embedding response missing output")
    raw_embeddings = output.get("embeddings")
    if not isinstance(raw_embeddings, list):
        raise RuntimeError("DashScope embedding response missing embeddings")

    sorted_embeddings = sorted(raw_embeddings, key=lambda item: int(item.get("index", 0)))
    return [list(item["embedding"]) for item in sorted_embeddings if isinstance(item, dict) and "embedding" in item]
