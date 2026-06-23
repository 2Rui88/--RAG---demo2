from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass
class RagDocument:
    doc_id: str
    title: str
    url: str
    year: str | None
    source: str
    text: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass
class RagChunk:
    chunk_id: str
    type: str
    content: str
    year: str | None
    source_doc_id: str
    source_title: str
    source_url: str
    section: str | None = None
    question: str | None = None
    answer: str | None = None
    aliases: list[str] | None = None

    def to_dict(self) -> dict[str, object]:
        return {key: value for key, value in asdict(self).items() if value is not None}


@dataclass
class BuildSummary:
    document_count: int
    policy_chunk_count: int
    faq_chunk_count: int
    merged_chunk_count: int
