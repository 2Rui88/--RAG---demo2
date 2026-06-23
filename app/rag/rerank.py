from __future__ import annotations

from app.rag.retriever import SearchResult, _tokens


class LightweightReranker:
    def rerank(self, query: str, candidates: list[SearchResult], *, top_k: int = 5) -> list[SearchResult]:
        query_tokens = _tokens(query)
        reranked: list[SearchResult] = []
        for candidate in candidates:
            text = " ".join(
                value
                for value in [candidate.question, candidate.answer, candidate.content, candidate.section, candidate.source_title]
                if value
            )
            candidate_tokens = _tokens(text)
            overlap = query_tokens & candidate_tokens
            overlap_score = len(overlap) / max(len(query_tokens), 1)
            year_score = 0.2 if candidate.year and candidate.year in query else 0.0
            faq_score = 0.15 if candidate.type == "faq" else 0.0
            candidate.score = round(candidate.score + overlap_score + year_score + faq_score, 6)
            reranked.append(candidate)

        return sorted(reranked, key=lambda item: item.score, reverse=True)[:top_k]
