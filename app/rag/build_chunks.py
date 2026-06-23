from __future__ import annotations

import argparse
from pathlib import Path

from app.rag.chunker import chunk_policy_document
from app.rag.faq import generate_faq_chunks
from app.rag.jsonl import write_jsonl
from app.rag.loader import load_txt_documents
from app.rag.models import BuildSummary, RagChunk


def build_rag_chunks(source_dir: Path, output_dir: Path) -> BuildSummary:
    documents = load_txt_documents(source_dir)
    policy_chunks: list[RagChunk] = []
    faq_chunks: list[RagChunk] = []

    for document in documents:
        policy_chunks.extend(chunk_policy_document(document))
        faq_chunks.extend(generate_faq_chunks(document))

    faq_chunks = deduplicate_faq_chunks(faq_chunks)
    merged_chunks = [*faq_chunks, *policy_chunks]

    write_jsonl(output_dir / "documents.jsonl", documents)
    write_jsonl(output_dir / "policy_chunks.jsonl", policy_chunks)
    write_jsonl(output_dir / "faq_chunks.jsonl", faq_chunks)
    write_jsonl(output_dir / "chunks.jsonl", merged_chunks)

    return BuildSummary(
        document_count=len(documents),
        policy_chunk_count=len(policy_chunks),
        faq_chunk_count=len(faq_chunks),
        merged_chunk_count=len(merged_chunks),
    )


def deduplicate_faq_chunks(chunks: list[RagChunk]) -> list[RagChunk]:
    seen: set[tuple[str | None, str | None]] = set()
    unique: list[RagChunk] = []
    for chunk in chunks:
        key = (chunk.year, chunk.question)
        if key in seen:
            continue
        seen.add(key)
        unique.append(chunk)
    return unique


def main() -> None:
    parser = argparse.ArgumentParser(description="Build RAG JSONL chunks from txt documents.")
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", default=Path("data/rag"), type=Path)
    args = parser.parse_args()

    summary = build_rag_chunks(args.source, args.output)
    print(
        f"documents={summary.document_count} "
        f"policy_chunks={summary.policy_chunk_count} "
        f"faq_chunks={summary.faq_chunk_count} "
        f"chunks={summary.merged_chunk_count}"
    )


if __name__ == "__main__":
    main()
