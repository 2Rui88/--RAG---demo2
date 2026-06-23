# RAG Chunking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first RAG preprocessing layer that parses Guangdong Adult College Entrance Exam `.txt` files and emits standardized JSONL chunks.

**Architecture:** A small `app.rag` package owns parsing, section chunking, FAQ extraction, and JSONL writing. A CLI module builds `documents.jsonl`, `policy_chunks.jsonl`, `faq_chunks.jsonl`, and merged `chunks.jsonl` from a source folder.

**Tech Stack:** Python 3.11 standard library, pytest.

## Global Constraints

- Source files are local `.txt` files from Guangdong Education Examinations Authority adult exam pages.
- Chunking output must preserve source title, URL, year, and document id.
- Policy documents are split by section markers first, then by length.
- FAQ chunks are generated only from high-confidence policy patterns.
- This plan does not implement retrieval, embeddings, rerank, or answer generation.

---

### Task 1: Parse Raw Txt Documents

**Files:**
- Create: `app/rag/models.py`
- Create: `app/rag/loader.py`
- Test: `tests/test_rag_chunking.py`

**Interfaces:**
- Produces: `parse_txt_document(path: Path) -> RagDocument`

- [x] Write failing tests for title, URL, year, doc id, and cleaned text extraction.
- [x] Implement parser.
- [x] Run parser tests.

### Task 2: Split Policy Sections

**Files:**
- Create: `app/rag/chunker.py`
- Test: `tests/test_rag_chunking.py`

**Interfaces:**
- Produces: `chunk_policy_document(document: RagDocument, target_size: int = 800, max_size: int = 1200) -> list[RagChunk]`

- [x] Write failing tests for section-aware chunk metadata.
- [x] Implement section and length splitting.
- [x] Run chunking tests.

### Task 3: Generate High-Confidence FAQ Chunks

**Files:**
- Create: `app/rag/faq.py`
- Test: `tests/test_rag_chunking.py`

**Interfaces:**
- Produces: `generate_faq_chunks(document: RagDocument) -> list[RagChunk]`

- [x] Write failing tests for报名时间 and报名费 extraction.
- [x] Implement conservative regex extraction.
- [x] Run FAQ tests.

### Task 4: Build JSONL Artifacts

**Files:**
- Create: `app/rag/jsonl.py`
- Create: `app/rag/build_chunks.py`
- Test: `tests/test_rag_chunking.py`

**Interfaces:**
- Produces: `build_rag_chunks(source_dir: Path, output_dir: Path) -> BuildSummary`
- CLI: `python -m app.rag.build_chunks --source <folder> --output data/rag`

- [x] Write failing test for output files and merged chunks.
- [x] Implement JSONL writer and CLI.
- [x] Run all tests.
