from app.conversation import ConversationEngine
from app.crm import InMemoryCrm


def test_valid_phone_creates_full_crm_lead():
    crm = InMemoryCrm()
    engine = ConversationEngine(crm=crm)
    session = engine.create_session("crm-full")
    engine.handle_message(session, "高中/中专")
    engine.handle_message(session, "升大专")
    engine.handle_message(session, "考公考编")
    engine.handle_message(session, "多少钱")

    response = engine.handle_message(session, "13800138000")

    assert response.state == "success"
    assert response.lead_saved is True
    assert response.slots["crm_lead_id"] == "lead_1"
    assert crm.leads[0].phone == "13800138000"
    assert crm.leads[0].lead_type == "full"
    assert crm.leads[0].slots["education"] == "高中/中专"
    assert "phone" not in crm.leads[0].slots
    assert crm.leads[0].source == "chat_demo"


def test_refusing_phone_creates_downgraded_crm_lead_and_retention_reply():
    crm = InMemoryCrm()
    engine = ConversationEngine(crm=crm)
    session = engine.create_session("crm-soft")
    engine.handle_message(session, "高中/中专")
    engine.handle_message(session, "升大专")
    engine.handle_message(session, "考公考编")
    engine.handle_message(session, "多少钱")

    response = engine.handle_message(session, "稍后再说")

    assert response.state == "intent_router"
    assert response.lead_saved is True
    assert response.slots["crm_lead_id"] == "lead_1"
    assert crm.leads[0].phone is None
    assert crm.leads[0].lead_type == "downgraded"
    assert crm.leads[0].refusal_reason == "user_refused_phone"
    assert "先不用留手机号" in response.reply
    assert "免费规划" in response.reply
