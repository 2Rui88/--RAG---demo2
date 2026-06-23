from __future__ import annotations

import re

from app.rag.models import RagChunk, RagDocument


SECTION_PATTERN = re.compile(
    r"([一二三四五六七八九十]+、[^\n。；;]{2,40}|（[一二三四五六七八九十]+）[^\n。；;]{2,40}|(?:^|(?<=[。；;]))\d+\.[^\n。；;]{2,40})"
)


def chunk_policy_document(document: RagDocument, target_size: int = 800, max_size: int = 1200) -> list[RagChunk]:
    sections = split_sections(document.text)
    chunks: list[RagChunk] = []

    for section_title, section_text in sections:
        for part_index, content in enumerate(split_by_length(section_text, target_size=target_size, max_size=max_size), start=1):
            chunk_id = _make_chunk_id(document, section_title, part_index)
            chunks.append(
                RagChunk(
                    chunk_id=chunk_id,
                    type="policy_chunk",
                    content=content,
                    year=document.year,
                    source_doc_id=document.doc_id,
                    source_title=document.title,
                    source_url=document.url,
                    section=section_title,
                )
            )

    return chunks


def split_sections(text: str) -> list[tuple[str | None, str]]:
    matches = list(SECTION_PATTERN.finditer(text))
    if not matches:
        return [(None, text.strip())] if text.strip() else []

    sections: list[tuple[str | None, str]] = []
    intro = text[: matches[0].start()].strip()
    if intro:
        sections.append((None, intro))

    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        section_text = text[start:end].strip()
        section_title = match.group(1).strip()
        sections.append((section_title, section_text))

    return sections


def split_by_length(text: str, target_size: int, max_size: int) -> list[str]:
    cleaned = re.sub(r"\s+", "", text)
    if len(cleaned) <= max_size:
        return [cleaned] if cleaned else []

    sentences = re.split(r"(?<=[。；;])", cleaned)
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if not sentence:
            continue
        if current and len(current) + len(sentence) > target_size:
            chunks.append(current)
            current = sentence
        else:
            current += sentence
        while len(current) > max_size:
            chunks.append(current[:max_size])
            current = current[max_size - 100 :]
    if current:
        chunks.append(current)
    return chunks


def _make_chunk_id(document: RagDocument, section: str | None, part_index: int) -> str:
    section_key = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "_", section or "intro").strip("_")[:40]
    year = document.year or "unknown"
    return f"{document.doc_id}_{year}_{section_key}_{part_index:03d}"
