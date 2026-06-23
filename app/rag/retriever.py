from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SearchResult:
    chunk_id: str
    type: str
    content: str
    score: float
    source_title: str
    source_url: str
    year: str | None = None
    section: str | None = None
    question: str | None = None
    answer: str | None = None


@dataclass
class IndexedChunk:
    raw: dict[str, object]
    text: str
    tokens: set[str]
    token_counts: Counter[str]
    length: int


class LocalKeywordRetriever:
    def __init__(self, chunks: list[IndexedChunk]) -> None:
        self.chunks = chunks
        self.avg_doc_length = sum(chunk.length for chunk in chunks) / len(chunks) if chunks else 0.0
        self.doc_freqs = _document_frequencies(chunks)

    @classmethod
    def from_jsonl(cls, path: Path) -> "LocalKeywordRetriever":
        chunks: list[IndexedChunk] = []
        if not path.exists():
            return cls([])

        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            raw = json.loads(line)
            text = _search_text(raw)
            token_counts = _token_counts(text)
            chunks.append(
                IndexedChunk(
                    raw=raw,
                    text=text,
                    tokens=set(token_counts),
                    token_counts=token_counts,
                    length=sum(token_counts.values()),
                )
            )
        return cls(chunks)

    def search(self, query: str, top_k: int = 5, min_score: float = 2.0) -> list[SearchResult]:
        query_tokens = _tokens(_expand_query(query))
        if not query_tokens:
            return []

        scored: list[tuple[float, IndexedChunk]] = []
        for chunk in self.chunks:
            score = self._bm25_score(query_tokens, chunk)
            if chunk.raw.get("type") == "faq":
                score *= 1.25
            if str(chunk.raw.get("year") or "") in query:
                score += 1.5
            score += _query_specific_boost(query, chunk.raw)
            if score >= min_score:
                scored.append((score, chunk))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [_to_result(chunk, score) for score, chunk in scored[:top_k]]

    def _bm25_score(self, query_tokens: set[str], chunk: IndexedChunk) -> float:
        if not query_tokens or not self.chunks or self.avg_doc_length <= 0:
            return 0.0

        k1 = 1.5
        b = 0.75
        score = 0.0
        for token in query_tokens:
            term_frequency = chunk.token_counts.get(token, 0)
            if term_frequency <= 0:
                continue
            document_frequency = self.doc_freqs.get(token, 0)
            idf = math.log(1 + (len(self.chunks) - document_frequency + 0.5) / (document_frequency + 0.5))
            denominator = term_frequency + k1 * (1 - b + b * chunk.length / self.avg_doc_length)
            score += idf * (term_frequency * (k1 + 1)) / denominator * _token_weight(token)
        return score


def _search_text(raw: dict[str, object]) -> str:
    parts: list[str] = []
    for key in ("question", "answer", "content", "section", "source_title"):
        value = raw.get(key)
        if isinstance(value, str):
            parts.append(value)
    aliases = raw.get("aliases")
    if isinstance(aliases, list):
        parts.extend(str(alias) for alias in aliases)
    return "\n".join(parts)


def _expand_query(query: str) -> str:
    expanded_terms: list[str] = []
    if "录取" in query and any(keyword in query for keyword in ("时间", "结果", "公布", "查询")):
        expanded_terms.extend(["录取结果公布", "录取结果公布时间", "查询录取结果", "录取期间"])
    if "报名" in query and any(keyword in query for keyword in ("怎么", "如何", "咋", "方式", "流程", "步骤")):
        expanded_terms.extend(["报名方式", "报名流程", "网上报名", "填写信息", "上传材料", "确认报名"])
    return " ".join([query, *expanded_terms])


def _query_specific_boost(query: str, raw: dict[str, object]) -> float:
    if "录取" not in query or not any(keyword in query for keyword in ("时间", "结果", "公布", "查询")):
        return 0.0
    text = _search_text(raw)
    boost = 0.0
    for keyword in ("录取结果公布时间", "查询录取结果", "获取或查询录取结果", "录取期间"):
        if keyword in text:
            boost += 2.0
    return boost


def _tokens(text: str) -> set[str]:
    return set(_token_counts(text))


def _token_counts(text: str) -> Counter[str]:
    normalized = re.sub(r"\s+", "", text.lower())
    chinese = re.findall(r"[\u4e00-\u9fff]{2,}", normalized)
    ascii_words = re.findall(r"[a-z0-9]{2,}", normalized)
    tokens: list[str] = list(ascii_words)

    for word in chinese:
        if len(word) <= 4:
            tokens.append(word)
        for size in (2, 3, 4):
            for index in range(0, max(0, len(word) - size + 1)):
                tokens.append(word[index : index + size])
    return Counter(tokens)


def _document_frequencies(chunks: list[IndexedChunk]) -> dict[str, int]:
    document_frequencies: dict[str, int] = {}
    for chunk in chunks:
        for token in chunk.tokens:
            document_frequencies[token] = document_frequencies.get(token, 0) + 1
    return document_frequencies


def _token_weight(token: str) -> float:
    if len(token) >= 4:
        return 2.0
    if len(token) == 3:
        return 1.2
    return 0.6


def _to_result(chunk: IndexedChunk, score: float) -> SearchResult:
    raw = chunk.raw
    return SearchResult(
        chunk_id=str(raw.get("chunk_id", "")),
        type=str(raw.get("type", "")),
        content=str(raw.get("content", "")),
        score=round(score, 4),
        source_title=str(raw.get("source_title", "")),
        source_url=str(raw.get("source_url", "")),
        year=str(raw["year"]) if raw.get("year") is not None else None,
        section=str(raw["section"]) if raw.get("section") is not None else None,
        question=str(raw["question"]) if raw.get("question") is not None else None,
        answer=str(raw["answer"]) if raw.get("answer") is not None else None,
    )
