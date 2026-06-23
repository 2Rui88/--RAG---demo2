# RAG RRF Rerank Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade RAG from simple hybrid merge to BM25-like top 20 + vector top 20, RRF fusion, lightweight rerank top 5, and qwen answer generation from top 3 chunks.

**Architecture:** Keep the existing local keyword retriever and vector index. Add a fusion module for RRF, a lightweight reranker module, and a generation method on `QwenClient`. `RagService.search()` becomes a staged pipeline, and `RagService.answer()` uses top reranked sources.

**Tech Stack:** Python 3.11 standard library, existing OpenAI-compatible qwen client, pytest.

## Global Constraints

- Do not answer price, personal eligibility, signup path, or fastest-graduation questions through RAG; conversation state machine still routes those to lead capture.
- Retrieval pipeline must request keyword top 20 and vector top 20 before fusion.
- RRF fusion must deduplicate by `chunk_id`.
- Rerank is lightweight local scoring for now, no extra model dependency.
- Qwen generation must only use retrieved chunks and fall back to controlled extractive answer on failure.

---

### Task 1: RRF Fusion

- [x] Add failing tests for reciprocal-rank fusion and duplicate chunk merging.
- [x] Implement `app/rag/fusion.py`.

### Task 2: Lightweight Reranker

- [x] Add failing tests for top 5 reranking.
- [x] Implement `app/rag/rerank.py`.

### Task 3: Qwen RAG Generation

- [x] Add failing tests for prompt construction and fallback.
- [x] Implement `QwenClient.generate_rag_answer()`.

### Task 4: Service Pipeline

- [x] Add tests proving keyword/vector top 20, RRF, rerank top 5, qwen top 3.
- [x] Update `RagService`.
- [x] Run all tests and verify service.
