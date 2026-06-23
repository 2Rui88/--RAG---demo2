from __future__ import annotations

import re
from pathlib import Path

from app.rag.models import RagDocument


YEAR_PATTERN = re.compile(r"(20\d{2})")
URL_PATTERN = re.compile(r"https?://[A-Za-z0-9./_%?=&:#-]+")


def parse_txt_document(path: Path) -> RagDocument:
    lines = [line.strip() for line in path.read_text(encoding="utf-8-sig").splitlines()]
    non_empty = [line for line in lines if line]
    if not non_empty:
        raise ValueError(f"Empty document: {path}")

    title = non_empty[0]
    url = ""
    body_start_index = 1
    body_prefix = ""
    for index, line in enumerate(non_empty[1:], start=1):
        match = URL_PATTERN.search(line)
        if match:
            url = match.group(0)
            body_prefix = line[match.end() :].strip()
            body_start_index = index + 1
            break

    body_lines = [body_prefix] if body_prefix else []
    body_lines.extend(URL_PATTERN.sub("", line).strip() for line in non_empty[body_start_index:])
    text = "\n".join(line for line in body_lines if line).strip()
    year_match = YEAR_PATTERN.search(title) or YEAR_PATTERN.search(path.name)

    return RagDocument(
        doc_id=_extract_doc_id(path),
        title=title,
        url=url,
        year=year_match.group(1) if year_match else None,
        source="广东省教育考试院",
        text=text,
    )


def load_txt_documents(source_dir: Path) -> list[RagDocument]:
    return [parse_txt_document(path) for path in sorted(source_dir.glob("*.txt"))]


def _extract_doc_id(path: Path) -> str:
    match = re.match(r"(\d+)_", path.name)
    return match.group(1) if match else path.stem
