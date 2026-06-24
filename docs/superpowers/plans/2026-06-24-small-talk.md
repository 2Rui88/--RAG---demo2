# Small Talk Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a dedicated Small Talk module for greetings, thanks, goodbye, and unrelated chatter without disrupting RAG or lead capture.

**Architecture:** Create `app/small_talk.py` with deterministic template responses and a protocol. Inject it into `ConversationEngine` so `small_talk` intent responses are handled outside the state machine’s routing logic. Keep model-based small talk out of scope for stability; Qwen can still classify the intent.

**Tech Stack:** Python 3.11, pytest.

## Global Constraints

- Do not call RAG for small talk.
- Do not trigger lead capture for small talk.
- Preserve current behavior for unrelated off-domain questions.
- Small talk replies should guide users back to学历提升咨询.
- Add tests before production implementation.

---

### Task 1: Small Talk Responder

**Files:**
- Create: `app/small_talk.py`
- Test: `tests/test_small_talk.py`

**Interfaces:**
- Produces: `SmallTalkResponder.respond(text: str, *, off_topic: bool = False) -> str`
- Produces: `TemplateSmallTalkResponder.respond(...) -> str`

- [x] Write failing tests for greeting, presence check, thanks, goodbye, and off-topic fallback.
- [x] Run tests and verify they fail because `app.small_talk` does not exist.
- [x] Implement deterministic template responder.
- [x] Run targeted tests and verify they pass.

### Task 2: ConversationEngine Integration

**Files:**
- Modify: `app/conversation.py`
- Test: `tests/test_conversation.py`
- Test: `tests/test_api.py`

**Interfaces:**
- Consumes: `small_talk_responder.respond(text, off_topic=False) -> str`
- Modifies: `ConversationEngine.__init__(..., small_talk_responder: SmallTalkResponder | None = None)`

- [x] Write failing tests showing injected responder is used, small talk does not call RAG, and a later business question can still use RAG.
- [x] Run tests and verify expected failures.
- [x] Inject responder and replace inline small-talk replies.
- [x] Run targeted tests and verify they pass.

### Task 3: Verification

**Files:**
- Modify as needed based on verification failures.

- [x] Run `python -m pytest`.
- [x] Confirm all tests pass.
- [x] Review `git diff` for unintended changes.
