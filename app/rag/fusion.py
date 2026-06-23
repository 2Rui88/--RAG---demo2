from __future__ import annotations

from app.rag.retriever import SearchResult


def rrf_fuse(result_lists: list[list[SearchResult]], *, top_k: int = 20, k: int = 60) -> list[SearchResult]:
    fused: dict[str, SearchResult] = {}
    scores: dict[str, float] = {}

    for results in result_lists:
        for rank, result in enumerate(results, start=1):
            scores[result.chunk_id] = scores.get(result.chunk_id, 0.0) + 1.0 / (k + rank)
            if result.chunk_id not in fused:
                fused[result.chunk_id] = result

    for chunk_id, score in scores.items():
        fused[chunk_id].score = round(score, 6)

    return sorted(fused.values(), key=lambda item: item.score, reverse=True)[:top_k]
