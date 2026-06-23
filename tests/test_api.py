import os

os.environ["RAG_EMBEDDING_ENABLED"] = "false"

from fastapi.testclient import TestClient

from app.main import app, crm, engine, qwen


client = TestClient(app)
qwen.enabled = False


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_endpoint_returns_conversation_payload():
    response = client.post("/api/chat", json={"session_id": "api-1", "message": "高中/中专"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["session_id"] == "api-1"
    assert payload["state"] == "qualification"
    assert payload["slots"]["education"] == "高中/中专"
    assert "quick_replies" in payload


def test_reset_endpoint_clears_session_slots():
    client.post("/api/chat", json={"session_id": "api-2", "message": "高中/中专"})

    response = client.post("/api/sessions/api-2/reset")

    assert response.status_code == 200
    payload = response.json()
    assert payload["session_id"] == "api-2"
    assert payload["slots"] == {}
    assert payload["state"] == "qualification"


def test_chat_successful_phone_writes_crm_lead_visible_from_api():
    crm.leads.clear()
    session_id = "api-crm-full"
    client.post("/api/chat", json={"session_id": session_id, "message": "高中/中专"})
    client.post("/api/chat", json={"session_id": session_id, "message": "升大专"})
    client.post("/api/chat", json={"session_id": session_id, "message": "考公考编"})
    client.post("/api/chat", json={"session_id": session_id, "message": "多少钱"})

    chat_response = client.post("/api/chat", json={"session_id": session_id, "message": "13800138000"})
    leads_response = client.get("/api/crm/leads")

    assert chat_response.status_code == 200
    assert chat_response.json()["slots"]["crm_lead_id"] == "lead_1"
    assert leads_response.status_code == 200
    leads = leads_response.json()["leads"]
    assert leads[0]["lead_type"] == "full"
    assert leads[0]["phone"] == "13800138000"


def test_phone_refusal_writes_downgraded_crm_lead_visible_from_api():
    crm.leads.clear()
    session_id = "api-crm-soft"
    client.post("/api/chat", json={"session_id": session_id, "message": "高中/中专"})
    client.post("/api/chat", json={"session_id": session_id, "message": "升大专"})
    client.post("/api/chat", json={"session_id": session_id, "message": "考公考编"})
    client.post("/api/chat", json={"session_id": session_id, "message": "多少钱"})

    chat_response = client.post("/api/chat", json={"session_id": session_id, "message": "稍后再说"})
    leads_response = client.get("/api/crm/leads")

    assert chat_response.status_code == 200
    assert "先不用留手机号" in chat_response.json()["reply"]
    leads = leads_response.json()["leads"]
    assert leads[0]["lead_type"] == "downgraded"
    assert leads[0]["phone"] is None
    assert leads[0]["refusal_reason"] == "user_refused_phone"


def test_chat_policy_question_uses_rag_when_available():
    session_id = "api-rag"
    client.post("/api/chat", json={"session_id": session_id, "message": "高中/中专"})
    client.post("/api/chat", json={"session_id": session_id, "message": "升大专"})
    client.post("/api/chat", json={"session_id": session_id, "message": "考公考编"})

    response = client.post("/api/chat", json={"session_id": session_id, "message": "2025年广东成人高考报名时间是什么时候？"})

    assert response.status_code == 200
    payload = response.json()
    assert "来源：" in payload["reply"]
    assert payload["lead_required"] is False


def test_rag_status_endpoint_reports_index_state():
    response = client.get("/api/rag/status")

    assert response.status_code == 200
    payload = response.json()
    assert "enabled" in payload
    assert "chunks_path" in payload


def test_rag_rebuild_endpoint_returns_summary():
    response = client.post("/api/rag/rebuild")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"ok", "disabled"}
    assert "message" in payload


class ApiRagService:
    def answer(self, query):
        source = type(
            "Source",
            (),
            {
                "chunk_id": "api_chunk",
                "source_title": "API测试来源",
                "score": 0.88,
                "content": "API测试命中片段",
                "source_url": "https://example.test/api",
            },
        )()
        return type("RagAnswer", (), {"reply": "RAG原始回答", "sources": [source]})()


class CountingQwen:
    def __init__(self):
        self.calls = 0

    def polish_reply(self, user_message, controlled_reply):
        self.calls += 1
        return "被二次润色"


def test_chat_rag_answer_returns_sources_and_skips_second_polish():
    original_rag_service = engine.rag_service
    original_enabled = qwen.enabled
    original_client = qwen.client
    original_polish = qwen.polish_reply
    counter = CountingQwen()
    engine.rag_service = ApiRagService()
    qwen.enabled = True
    qwen.client = object()
    qwen.polish_reply = counter.polish_reply

    try:
        session_id = "api-rag-debug"
        client.post("/api/chat", json={"session_id": session_id, "message": "高中/中专"})
        client.post("/api/chat", json={"session_id": session_id, "message": "升大专"})
        client.post("/api/chat", json={"session_id": session_id, "message": "考公考编"})
        calls_before_rag = counter.calls
        response = client.post("/api/chat", json={"session_id": session_id, "message": "报名时间"})
    finally:
        engine.rag_service = original_rag_service
        qwen.enabled = original_enabled
        qwen.client = original_client
        qwen.polish_reply = original_polish

    payload = response.json()
    assert payload["reply"] == "RAG原始回答"
    assert payload["used_rag"] is True
    assert payload["rag_sources"][0]["chunk_id"] == "api_chunk"
    assert counter.calls == calls_before_rag


def test_chat_controlled_state_machine_reply_skips_polish():
    original_polish = qwen.polish_reply
    counter = CountingQwen()
    qwen.polish_reply = counter.polish_reply

    try:
        response = client.post("/api/chat", json={"session_id": "api-no-polish", "message": "高中/中专"})
    finally:
        qwen.polish_reply = original_polish

    payload = response.json()
    assert response.status_code == 200
    assert payload["used_rag"] is False
    assert payload["reply"] != "被二次润色"
    assert counter.calls == 0
