# RAG Lead Chat Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a runnable front-end and FastAPI chat demo for an education lead-capture assistant.

**Architecture:** FastAPI serves both the JSON API and static chat UI. Conversation control lives in a deterministic state machine; qwen3.5-flash only polishes controlled replies. RAG is intentionally stubbed until the knowledge base is ready.

**Tech Stack:** Python 3.11, FastAPI, Pydantic, OpenAI-compatible qwen client, static HTML/CSS/JS, pytest.

## Global Constraints

- Conversation follows the md requirement: state machine, slots, three-way intent routing, and lead hook.
- RAG is not implemented yet; factual questions must not invent policies, prices, schools, or timelines.
- Price, eligibility, signup, payment, and fastest-graduation questions must trigger lead capture.
- API key is read from `.env`; `.env` is ignored by git.

---

### Task 1: Conversation State Machine

**Files:**
- Create: `app/conversation.py`
- Test: `tests/test_conversation.py`

**Interfaces:**
- Produces: `ConversationEngine.create_session(session_id)`, `handle_message(session, message)`, `reset_session(session)`.

- [x] Write failing tests for slot filling, lead hook trigger, and phone validation.
- [x] Run `python -m pytest tests/test_conversation.py -q` and verify failure before implementation.
- [x] Implement deterministic state machine and response payload dataclasses.
- [x] Re-run the conversation tests and verify pass.

### Task 2: FastAPI API

**Files:**
- Create: `app/main.py`
- Test: `tests/test_api.py`

**Interfaces:**
- Produces: `GET /health`, `POST /api/chat`, `POST /api/sessions/{session_id}/reset`.

- [x] Write failing tests for health, chat payload, and session reset.
- [x] Run `python -m pytest tests/test_api.py -q` and verify failure before implementation.
- [x] Implement API request/response models and in-memory sessions.
- [x] Re-run API tests and verify pass.

### Task 3: Qwen Client And Static UI

**Files:**
- Create: `app/llm_client.py`
- Create: `static/index.html`
- Create: `static/styles.css`
- Create: `static/app.js`
- Create: `.env.example`, `.gitignore`, `requirements.txt`

**Interfaces:**
- Produces: `QwenClient.polish_reply(user_message, controlled_reply)` and a browser chat UI at `/`.

- [x] Add OpenAI-compatible qwen client with guarded `.env` configuration.
- [x] Build a static chat workbench with messages, quick replies, state display, and slot display.
- [x] Serve static assets from FastAPI.
- [ ] Run full tests.
- [ ] Start local server and verify the page loads.
