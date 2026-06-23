from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app.rag.fusion import rrf_fuse
from app.rag.rerank import LightweightReranker
from app.rag.retriever import LocalKeywordRetriever, SearchResult
from app.rag.vector_index import VectorIndex, vector_match_to_search_result


RETRIEVAL_TOP_K = 20
RERANK_TOP_K = 5
GENERATION_TOP_K = 3
MAX_RAG_ANSWER_CHARS = 900
MIN_RAG_SCORE = 0.22
SIGNUP_PROCESS_MIN_SCORE = 0.16
ENTITY_CHECK_TOP_K = 5
ENTITY_GROUPS = {
    "adult_exam": ("成考", "成人高考", "成人高校", "成人高等学校"),
    "open_university": ("国开", "国家开放大学", "开放大学"),
    "self_exam": ("自考", "自学考试"),
}


class RagGenerator(Protocol):
    def generate_rag_answer(self, query: str, sources: list[SearchResult]) -> str:
        ...

    def compress_rag_answer(
        self,
        query: str,
        answer: str,
        sources: list[SearchResult],
        *,
        max_chars: int,
    ) -> str:
        ...


@dataclass
class RagAnswer:
    reply: str
    sources: list[SearchResult]


class RagService:
    def __init__(
        self,
        retriever: LocalKeywordRetriever,
        *,
        vector_index: VectorIndex | None = None,
        embedding_client: object | None = None,
        generator: RagGenerator | None = None,
        reranker: LightweightReranker | None = None,
    ) -> None:
        self.retriever = retriever
        self.vector_index = vector_index
        self.embedding_client = embedding_client
        self.generator = generator
        self.reranker = reranker or LightweightReranker()

    @classmethod
    def from_jsonl(
        cls,
        path: Path,
        *,
        vector_index: VectorIndex | None = None,
        embedding_client: object | None = None,
        generator: RagGenerator | None = None,
    ) -> "RagService":
        return cls(
            LocalKeywordRetriever.from_jsonl(path),
            vector_index=vector_index,
            embedding_client=embedding_client,
            generator=generator,
        )

    def answer(self, query: str) -> RagAnswer | None:
        results = self.search(query, top_k=RERANK_TOP_K)
        if not results or not _passes_confidence_gate(query, results):
            return None

        sources_for_generation = results[:GENERATION_TOP_K]
        body = (
            self.generator.generate_rag_answer(query, sources_for_generation)
            if self.generator
            else _fallback_answer_body(results[0])
        )
        body = self._compress_if_needed(query, body, sources_for_generation)

        reply = (
            f"{body}\n\n"
            f"来源：{results[0].source_title}\n"
            "如果您想结合自己的学历基础判断更适合的报考层次，我可以继续帮您做个简单诊断。"
        )
        return RagAnswer(reply=reply, sources=results)

    def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        keyword_results = self.retriever.search(query, top_k=RETRIEVAL_TOP_K)
        vector_results = self._vector_search(query)
        fused = rrf_fuse([keyword_results, vector_results], top_k=RETRIEVAL_TOP_K)
        return self.reranker.rerank(query, fused, top_k=min(top_k, RERANK_TOP_K))

    def _vector_search(self, query: str) -> list[SearchResult]:
        if not self.vector_index or not self.embedding_client:
            return []
        query_embedding = self.embedding_client.embed_texts([query])[0]
        return [
            vector_match_to_search_result(match)
            for match in self.vector_index.search(query_embedding, top_k=RETRIEVAL_TOP_K)
        ]

    def _compress_if_needed(self, query: str, body: str, sources: list[SearchResult]) -> str:
        if len(body) <= MAX_RAG_ANSWER_CHARS and not _looks_incomplete_answer(body):
            return body
        if self.generator and hasattr(self.generator, "compress_rag_answer"):
            return self.generator.compress_rag_answer(
                query,
                body,
                sources,
                max_chars=MAX_RAG_ANSWER_CHARS,
            )
        return _trim_content(body, MAX_RAG_ANSWER_CHARS)


def _fallback_answer_body(best: SearchResult) -> str:
    if best.type == "faq" and best.answer:
        return best.answer
    return _trim_content(best.content)


def _looks_incomplete_answer(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if stripped.endswith(("：", ":", "；", ";")):
        return True
    return any(stripped.endswith(marker) for marker in ("通知如下", "事项如下", "有关事项通知如下"))


def _passes_confidence_gate(query: str, results: list[SearchResult]) -> bool:
    if not results:
        return False
    if results[0].score < MIN_RAG_SCORE and not _is_supported_signup_process_query(query, results[:ENTITY_CHECK_TOP_K]):
        return False
    return _required_entities_covered(query, results[:ENTITY_CHECK_TOP_K])


def _is_supported_signup_process_query(query: str, results: list[SearchResult]) -> bool:
    if results[0].score < SIGNUP_PROCESS_MIN_SCORE:
        return False
    if "报名" not in query or not any(keyword in query for keyword in ("怎么", "如何", "咋", "方式", "流程", "步骤")):
        return False

    source_text = _joined_result_text(results)
    return any(keyword in source_text for keyword in ("报名方式", "报名流程", "网上报名", "填写信息", "上传材料", "确认报名"))


def _required_entities_covered(query: str, results: list[SearchResult]) -> bool:
    required_groups = [
        aliases
        for aliases in ENTITY_GROUPS.values()
        if any(alias in query for alias in aliases)
    ]
    if not required_groups:
        return True

    source_text = _joined_result_text(results)
    return all(any(alias in source_text for alias in aliases) for aliases in required_groups)


def _joined_result_text(results: list[SearchResult]) -> str:
    return "\n".join(
        " ".join(
            value
            for value in [
                result.question,
                result.answer,
                result.content,
                result.section,
                result.source_title,
            ]
            if value
        )
        for result in results
    )


def _trim_content(content: str, limit: int = 260) -> str:
    text = content.strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip("，。；;") + "..."
