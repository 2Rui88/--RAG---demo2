# Intent Router Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a dedicated intent router for `faq`, `rag`, `small_talk`, `lead`, and `human_service` while preserving current lead-capture behavior.

**Architecture:** Create a focused `app/intent_router.py` module with typed intent results, deterministic rule fallback, and a confidence threshold. Extend `QwenClient` with JSON intent classification using `qwen3.5-flash`, then inject the router into `ConversationEngine` so free-text routing decisions no longer live only in keyword helper calls.

**Tech Stack:** Python 3.11, pytest, existing OpenAI-compatible Qwen client with `qwen3.5-flash`.

## Global Constraints

- Default lightweight model: `qwen3.5-flash`.
- Do not require API keys for local tests or default development flow.
- Preserve current conversion behavior for price, eligibility, phone, and human-service messages.
- Low-confidence or invalid model output must fall back to deterministic rules.
- Add tests before production implementation.

---

### Task 1: Deterministic Router Types and Rules

**Files:**
- Create: `app/intent_router.py`
- Test: `tests/test_intent_router.py`

**Interfaces:**
- Produces: `IntentResult(intent: IntentName, confidence: float, reason: str = "")`
- Produces: `RuleIntentRouter.classify(text: str, history: list[dict[str, str]] | None = None) -> IntentResult`

- [x] Write failing tests for lead, small talk, human service, unrelated small talk, signup-process RAG, factual registration RAG, and generic education RAG.
- [x] Run tests and verify they fail because `app.intent_router` does not exist.
- [x] Implement minimal dataclass, literal intent names, and rule router.
- [x] Run targeted tests and verify they pass.

### Task 2: Qwen Intent Classification

**Files:**
- Modify: `app/llm_client.py`
- Test: `tests/test_intent_router.py`

**Interfaces:**
- Produces: `QwenClient.classify_intent(text: str, history: list[dict[str, str]] | None = None) -> IntentResult`

- [x] Write failing tests for disabled fallback, valid JSON response, low-confidence fallback, and invalid JSON fallback.
- [x] Run tests and verify expected failures.
- [x] Implement JSON prompt, parse/validate intent and confidence, and fallback to `RuleIntentRouter`.
- [x] Run targeted tests and verify they pass.

### Task 3: ConversationEngine Integration

**Files:**
- Modify: `app/conversation.py`
- Modify: `app/main.py`
- Modify: `.env.example`
- Test: `tests/test_conversation.py`
- Test: `tests/test_api.py`

**Interfaces:**
- Consumes: `intent_router.classify(text, history) -> IntentResult`
- Modifies: `ConversationEngine.__init__(..., intent_router: IntentRouter | None = None)`

- [x] Write failing tests showing `lead`, `small_talk`, `human_service`, and `rag` decisions come from injected router.
- [x] Run tests and verify expected failures.
- [x] Replace direct keyword routing in `handle_message` / `_handle_free_text` with router outcomes.
- [x] Wire `qwen` as default intent router when `INTENT_ROUTER_ENABLED=true`; otherwise use rules.
- [x] Run targeted tests and verify they pass.

### Task 4: Verification

**Files:**
- Modify as needed based on verification failures.

- [x] Run `python -m pytest`.
- [x] Confirm all tests pass.
- [x] Review `git diff` for unintended changes.
