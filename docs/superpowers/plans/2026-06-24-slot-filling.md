# Slot Filling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add slot filling so one user message can populate multiple lead-profile fields while preserving the current guided qualification flow.

**Architecture:** Create a focused `app/slot_filling.py` module with a deterministic rule extractor and merge helper. Extend `QwenClient` with JSON slot extraction using `qwen3.5-flash`, then inject the extractor into `ConversationEngine` so qualification messages can update several slots at once.

**Tech Stack:** Python 3.11, pytest, existing OpenAI-compatible Qwen client with `qwen3.5-flash`.

## Global Constraints

- Default lightweight model: `qwen3.5-flash`.
- Do not require API keys for local tests or default development flow.
- Preserve current required qualification flow: education, goal, purpose.
- Support optional extracted slots: city, budget, urgency.
- Low-confidence, invalid, or unavailable model output must fall back to deterministic rules.
- Add tests before production implementation.

---

### Task 1: Rule Slot Extractor

**Files:**
- Create: `app/slot_filling.py`
- Test: `tests/test_slot_filling.py`

**Interfaces:**
- Produces: `SlotExtractor.extract(text: str, history: list[dict[str, str]] | None = None) -> dict[str, str]`
- Produces: `RuleSlotExtractor.extract(...) -> dict[str, str]`
- Produces: `merge_slots(existing: dict[str, str], extracted: dict[str, str]) -> dict[str, str]`

- [x] Write failing tests for extracting multiple slots from one sentence, optional city/budget/urgency, ignoring unknown values, and preserving existing non-empty slots during merge.
- [x] Run tests and verify they fail because `app.slot_filling` does not exist.
- [x] Implement deterministic extraction and merge.
- [x] Run targeted tests and verify they pass.

### Task 2: Qwen Slot Extraction

**Files:**
- Modify: `app/llm_client.py`
- Test: `tests/test_slot_filling.py`

**Interfaces:**
- Produces: `QwenClient.extract_slots(text: str, history: list[dict[str, str]] | None = None) -> dict[str, str]`
- Produces: `QwenClient.extract(...) -> dict[str, str]`

- [x] Write failing tests for disabled fallback, valid JSON response, invalid JSON fallback, and unsupported values being ignored.
- [x] Run tests and verify expected failures.
- [x] Implement JSON prompt, parse/validate slots, and fallback to `RuleSlotExtractor`.
- [x] Run targeted tests and verify they pass.

### Task 3: ConversationEngine Integration

**Files:**
- Modify: `app/conversation.py`
- Modify: `app/main.py`
- Modify: `.env.example`
- Test: `tests/test_conversation.py`
- Test: `tests/test_api.py`

**Interfaces:**
- Consumes: `slot_extractor.extract(text, history) -> dict[str, str]`
- Modifies: `ConversationEngine.__init__(..., slot_extractor: SlotExtractor | None = None)`

- [x] Write failing tests showing one sentence can fill education, goal, and purpose; optional city/budget/urgency are stored; partial input still prompts the next missing required slot.
- [x] Run tests and verify expected failures.
- [x] Update qualification handling to merge extracted slots before prompting.
- [x] Wire `qwen` as default slot extractor when `SLOT_FILLING_ENABLED=true`; otherwise use rules.
- [x] Run targeted tests and verify they pass.

### Task 4: Verification

**Files:**
- Modify as needed based on verification failures.

- [x] Run `python -m pytest`.
- [x] Confirm all tests pass.
- [x] Review `git diff` for unintended changes.
