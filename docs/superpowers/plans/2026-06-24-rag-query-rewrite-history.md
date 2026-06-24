# RAG Query Rewrite History Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add lightweight Qwen-backed query rewriting and recent conversation history so RAG retrieval understands synonyms and short follow-up questions.

**Architecture:** Introduce a small query rewriting interface used by `ConversationEngine` before calling `RagService`. Store recent user/assistant turns on `ConversationSession`, cap history to 10 turns, and keep deterministic fallbacks when LLM calls or rewrite config are disabled.

**Tech Stack:** Python 3.11, FastAPI, pytest, existing OpenAI-compatible Qwen client with `qwen3.5-flash`.

## Global Constraints

- Default lightweight model: `qwen3.5-flash`.
- Do not require API keys for local tests or default development flow.
- Preserve existing lead-capture and CRM behavior.
- Add tests before production implementation.
- Keep query rewrite optional and recoverable if the model call fails.

---

### Task 1: Query Rewriter Interface

**Files:**
- Create: `app/rag/query_rewrite.py`
- Modify: `app/llm_client.py`
- Test: `tests/test_query_rewrite.py`

**Interfaces:**
- Produces: `QueryRewriter.rewrite(query: str, history: list[dict[str, str]] | None = None) -> str`
- Produces: `NoopQueryRewriter.rewrite(...) -> str`
- Produces: `QwenClient.rewrite_query(query: str, history: list[dict[str, str]] | None = None) -> str`

- [x] Write failing tests for no-op rewrite, Qwen disabled fallback, Qwen enabled prompt construction, and empty model output fallback.
- [x] Run tests and verify they fail because the module/method does not exist.
- [x] Implement minimal rewriter protocol/no-op class and Qwen rewrite method using existing client.
- [x] Run the targeted tests and verify they pass.

### Task 2: Conversation History

**Files:**
- Modify: `app/conversation.py`
- Test: `tests/test_conversation.py`

**Interfaces:**
- Produces: `ConversationSession.history: list[dict[str, str]]`
- Produces: `ConversationEngine._record_turn(session, user_message, assistant_reply) -> None`
- Produces: `ConversationEngine._recent_history(session) -> list[dict[str, str]]`

- [x] Write failing tests for recording turns, capping history to 20 messages / 10 turns, and reset clearing history.
- [x] Run tests and verify they fail because history is not implemented.
- [x] Implement minimal history storage and reset behavior.
- [x] Run targeted conversation tests and verify they pass.

### Task 3: Rewrite Integration Before RAG

**Files:**
- Modify: `app/conversation.py`
- Modify: `app/main.py`
- Test: `tests/test_conversation.py`
- Test: `tests/test_api.py`

**Interfaces:**
- Consumes: `QueryRewriter.rewrite(query, history) -> str`
- Modifies: `ConversationEngine.__init__(..., query_rewriter: QueryRewriter | None = None)`

- [x] Write failing tests showing RAG receives the rewritten query and follow-up questions receive prior history.
- [x] Run tests and verify expected failures.
- [x] Inject rewriter into `ConversationEngine` and call it only before RAG answers.
- [x] Wire `QwenClient` as the default query rewriter in `app/main.py`.
- [x] Run targeted tests and verify they pass.

### Task 4: Verification

**Files:**
- Modify as needed based on verification failures.

- [x] Run `python -m pytest`.
- [x] Confirm all tests pass.
- [x] Review `git diff` for unintended changes.
