from app.conversation import ConversationEngine
from app.crm import InMemoryCrm
from app.intent_router import IntentResult


class StubRagService:
    def __init__(self, reply: str | None) -> None:
        self.reply = reply
        self.calls: list[str] = []

    def answer(self, query: str):
        self.calls.append(query)
        if self.reply is None:
            return None
        source = type(
            "Source",
            (),
            {
                "chunk_id": "chunk_1",
                "source_title": "报名公告",
                "score": 0.92,
                "content": "报名时间为9月9日。",
                "source_url": "https://example.test",
            },
        )()
        return type("RagAnswer", (), {"reply": self.reply, "sources": [source]})()


class StubQueryRewriter:
    def __init__(self, rewritten: str) -> None:
        self.rewritten = rewritten
        self.calls: list[tuple[str, list[dict[str, str]]]] = []

    def rewrite(self, query: str, history: list[dict[str, str]] | None = None) -> str:
        self.calls.append((query, list(history or [])))
        return self.rewritten


class StubIntentRouter:
    def __init__(self, intent: str) -> None:
        self.intent = intent
        self.calls: list[tuple[str, list[dict[str, str]]]] = []

    def classify(self, text: str, history: list[dict[str, str]] | None = None) -> IntentResult:
        self.calls.append((text, list(history or [])))
        return IntentResult(intent=self.intent, confidence=0.99, reason="stub")


class StubSlotExtractor:
    def __init__(self, slots: dict[str, str]) -> None:
        self.slots = slots
        self.calls: list[tuple[str, list[dict[str, str]]]] = []

    def extract(self, text: str, history: list[dict[str, str]] | None = None) -> dict[str, str]:
        self.calls.append((text, list(history or [])))
        return dict(self.slots)


class StubSmallTalkResponder:
    def __init__(self, reply: str = "stub small talk reply") -> None:
        self.reply = reply
        self.calls: list[tuple[str, bool]] = []

    def respond(self, text: str, *, off_topic: bool = False) -> str:
        self.calls.append((text, off_topic))
        return self.reply


def test_quick_choices_fill_slots_and_move_to_intent_stage():
    engine = ConversationEngine()
    session = engine.create_session("s1")

    first = engine.handle_message(session, "高中/中专")
    second = engine.handle_message(session, "升大专")
    third = engine.handle_message(session, "考公考编")

    assert first.slots["education"] == "高中/中专"
    assert second.slots["goal"] == "升大专"
    assert third.slots["purpose"] == "考公考编"
    assert third.state == "intent_router"
    assert "费用" in third.quick_replies


def test_greeting_does_not_fill_education_slot():
    engine = ConversationEngine()
    session = engine.create_session("hello")

    response = engine.handle_message(session, "你好")

    assert response.state == "qualification"
    assert "education" not in response.slots
    assert "你好" not in response.reply
    assert "最高学历" in response.reply


def test_greeting_during_intent_stage_does_not_use_rag():
    rag_service = StubRagService("这段 RAG 回答不应该出现")
    engine = ConversationEngine(rag_service=rag_service)
    session = engine.create_session("intent-greeting")
    engine.handle_message(session, "高中/中专")
    engine.handle_message(session, "升大专")
    engine.handle_message(session, "考公考编")

    response = engine.handle_message(session, "你好")

    assert response.state == "intent_router"
    assert response.used_rag is False
    assert response.rag_sources == []
    assert session.qa_turns == 0
    assert rag_service.calls == []
    assert "这段 RAG 回答不应该出现" not in response.reply
    assert "知识库没有找到" not in response.reply
    assert "学历提升" in response.reply


def test_injected_small_talk_responder_is_used_for_small_talk():
    rag_service = StubRagService("这段 RAG 回答不应该出现")
    responder = StubSmallTalkResponder()
    engine = ConversationEngine(rag_service=rag_service, small_talk_responder=responder)
    session = engine.create_session("small-talk-injected")
    engine.handle_message(session, "高中/中专")
    engine.handle_message(session, "升大专")
    engine.handle_message(session, "考公考编")

    response = engine.handle_message(session, "谢谢")

    assert response.reply == "stub small talk reply"
    assert response.used_rag is False
    assert rag_service.calls == []
    assert responder.calls == [("谢谢", False)]


def test_unrelated_question_during_intent_stage_does_not_use_rag():
    rag_service = StubRagService("这段 RAG 回答不应该出现")
    engine = ConversationEngine(rag_service=rag_service)
    session = engine.create_session("intent-unrelated")
    engine.handle_message(session, "高中/中专")
    engine.handle_message(session, "升大专")
    engine.handle_message(session, "考公考编")

    response = engine.handle_message(session, "今天天气怎么样？")

    assert response.state == "intent_router"
    assert response.used_rag is False
    assert rag_service.calls == []
    assert "这个我帮不上" in response.reply


def test_small_talk_then_business_question_can_return_to_rag():
    rag_service = StubRagService("这是知识库回答。")
    engine = ConversationEngine(rag_service=rag_service)
    session = engine.create_session("small-talk-return")
    engine.handle_message(session, "高中/中专")
    engine.handle_message(session, "升大专")
    engine.handle_message(session, "考公考编")

    small_talk = engine.handle_message(session, "再见")
    business = engine.handle_message(session, "成考和国开有什么区别？")

    assert small_talk.used_rag is False
    assert business.used_rag is True
    assert "这是知识库回答" in business.reply


def test_natural_slot_text_is_accepted_when_it_contains_clear_meaning():
    engine = ConversationEngine()
    session = engine.create_session("natural")

    first = engine.handle_message(session, "我是高中毕业")
    second = engine.handle_message(session, "想升本科")

    assert first.slots["education"] == "高中/中专"
    assert second.slots["goal"] == "专升本"


def test_one_message_can_fill_required_qualification_slots():
    engine = ConversationEngine()
    session = engine.create_session("multi-slot")

    response = engine.handle_message(session, "我是大专，想专升本，主要为了考公")

    assert response.state == "intent_router"
    assert response.slots["education"] == "大专"
    assert response.slots["goal"] == "专升本"
    assert response.slots["purpose"] == "考公考编"
    assert "继续问学历形式" in response.reply


def test_partial_slot_filling_prompts_next_missing_required_slot():
    engine = ConversationEngine()
    session = engine.create_session("partial-slot")

    response = engine.handle_message(session, "我是大专，想专升本")

    assert response.state == "qualification"
    assert response.slots["education"] == "大专"
    assert response.slots["goal"] == "专升本"
    assert "主要准备用在哪方面" in response.reply


def test_optional_slots_are_saved_without_becoming_required_questions():
    engine = ConversationEngine()
    session = engine.create_session("optional-slot")

    response = engine.handle_message(session, "我是大专，想专升本，考公用，在广州，预算一万以内，想尽快")

    assert response.state == "intent_router"
    assert response.slots["city"] == "广州"
    assert response.slots["budget"] == "一万以内"
    assert response.slots["urgency"] == "尽快"


def test_injected_slot_extractor_is_used_during_qualification():
    extractor = StubSlotExtractor({"education": "本科", "goal": "考证/职称", "purpose": "评职称"})
    engine = ConversationEngine(slot_extractor=extractor)
    session = engine.create_session("injected-slot")

    response = engine.handle_message(session, "帮我规划")

    assert response.state == "intent_router"
    assert response.slots["education"] == "本科"
    assert response.slots["goal"] == "考证/职称"
    assert response.slots["purpose"] == "评职称"
    assert extractor.calls == [("帮我规划", [])]


def test_price_or_signup_intent_triggers_lead_hook():
    engine = ConversationEngine()
    session = engine.create_session("s2")

    response = engine.handle_message(session, "我想报名，多少钱？")

    assert response.state == "lead_hook"
    assert response.lead_required is True
    assert "手机号" in response.reply
    assert "免费" in response.reply


def test_signup_process_uses_rag_with_soft_hook_without_entering_lead_hook():
    engine = ConversationEngine(rag_service=StubRagService("\u62a5\u540d\u65b9\u5f0f\u9700\u8981\u5148\u7f51\u4e0a\u6ce8\u518c\uff0c\u518d\u6309\u8981\u6c42\u63d0\u4ea4\u6750\u6599\u3002"))
    session = engine.create_session("answer-before-hook")
    engine.handle_message(session, "\u9ad8\u4e2d/\u4e2d\u4e13")
    engine.handle_message(session, "\u5347\u5927\u4e13")
    engine.handle_message(session, "\u8003\u516c\u8003\u7f16")

    response = engine.handle_message(session, "\u600e\u4e48\u62a5\u540d")

    assert response.state == "intent_router"
    assert response.lead_required is False
    assert response.used_rag is True
    assert "\u62a5\u540d\u65b9\u5f0f\u9700\u8981\u5148\u7f51\u4e0a\u6ce8\u518c" in response.reply
    assert "\u7ee7\u7eed\u5e2e\u60a8\u505a\u4e2a\u7b80\u5355\u8bca\u65ad" in response.reply


def test_conversion_intents_directly_enter_lead_hook_without_rag_lookup():
    rag_service = StubRagService("\u8fd9\u6bb5 RAG \u56de\u7b54\u4e0d\u5e94\u8be5\u51fa\u73b0")
    engine = ConversationEngine(rag_service=rag_service)
    session = engine.create_session("direct-lead-hook")
    engine.handle_message(session, "\u9ad8\u4e2d/\u4e2d\u4e13")
    engine.handle_message(session, "\u5347\u5927\u4e13")
    engine.handle_message(session, "\u8003\u516c\u8003\u7f16")

    for message in ["\u6211\u80fd\u4e0d\u80fd\u62a5", "\u591a\u5c11\u94b1", "\u6700\u5feb\u591a\u4e45\u62ff\u8bc1"]:
        session.state = "intent_router"
        response = engine.handle_message(session, message)

        assert response.state == "lead_hook"
        assert response.lead_required is True
        assert response.used_rag is False
        assert response.rag_sources == []
        assert "\u8fd9\u6bb5 RAG \u56de\u7b54\u4e0d\u5e94\u8be5\u51fa\u73b0" not in response.reply

    assert rag_service.calls == []


def test_injected_intent_router_can_route_message_to_lead_hook():
    rag_service = StubRagService("这段 RAG 回答不应该出现")
    intent_router = StubIntentRouter("lead")
    engine = ConversationEngine(rag_service=rag_service, intent_router=intent_router)
    session = engine.create_session("router-lead")
    engine.handle_message(session, "高中/中专")
    engine.handle_message(session, "升大专")
    engine.handle_message(session, "考公考编")

    response = engine.handle_message(session, "帮我看看")

    assert response.state == "lead_hook"
    assert response.lead_required is True
    assert response.used_rag is False
    assert rag_service.calls == []
    assert intent_router.calls[-1][0] == "帮我看看"


def test_injected_intent_router_can_route_message_to_small_talk():
    rag_service = StubRagService("这段 RAG 回答不应该出现")
    intent_router = StubIntentRouter("small_talk")
    engine = ConversationEngine(rag_service=rag_service, intent_router=intent_router)
    session = engine.create_session("router-small-talk")
    engine.handle_message(session, "高中/中专")
    engine.handle_message(session, "升大专")
    engine.handle_message(session, "考公考编")

    response = engine.handle_message(session, "随便聊聊")

    assert response.state == "intent_router"
    assert response.used_rag is False
    assert rag_service.calls == []
    assert "学历提升" in response.reply


def test_injected_intent_router_can_route_message_to_human_service_lead_hook():
    rag_service = StubRagService("这段 RAG 回答不应该出现")
    intent_router = StubIntentRouter("human_service")
    engine = ConversationEngine(rag_service=rag_service, intent_router=intent_router)
    session = engine.create_session("router-human")
    engine.handle_message(session, "高中/中专")
    engine.handle_message(session, "升大专")
    engine.handle_message(session, "考公考编")

    response = engine.handle_message(session, "我想咨询")

    assert response.state == "lead_hook"
    assert response.lead_required is True
    assert rag_service.calls == []


def test_injected_intent_router_can_route_message_to_rag():
    rag_service = StubRagService("这是知识库回答。")
    intent_router = StubIntentRouter("rag")
    engine = ConversationEngine(rag_service=rag_service, intent_router=intent_router)
    session = engine.create_session("router-rag")
    engine.handle_message(session, "高中/中专")
    engine.handle_message(session, "升大专")
    engine.handle_message(session, "考公考编")

    response = engine.handle_message(session, "你好")

    assert response.used_rag is True
    assert "这是知识库回答" in response.reply
    assert rag_service.calls == ["你好"]


def test_lead_hook_after_ten_qa_turns_answers_tenth_question_first():
    engine = ConversationEngine(rag_service=StubRagService("\u8fd9\u662f\u77e5\u8bc6\u5e93\u91cc\u7684\u7b54\u7591\u5185\u5bb9\u3002"))
    session = engine.create_session("ten-turns")
    engine.handle_message(session, "\u9ad8\u4e2d/\u4e2d\u4e13")
    engine.handle_message(session, "\u5347\u5927\u4e13")
    engine.handle_message(session, "\u8003\u516c\u8003\u7f16")

    for index in range(9):
        response = engine.handle_message(session, f"\u653f\u7b56\u95ee\u9898{index}")
        assert response.state == "intent_router"
        assert response.lead_required is False

    response = engine.handle_message(session, "\u7b2c\u5341\u4e2a\u653f\u7b56\u95ee\u9898")

    assert response.state == "lead_hook"
    assert response.lead_required is True
    assert response.used_rag is True
    assert "\u8fd9\u662f\u77e5\u8bc6\u5e93\u91cc\u7684\u7b54\u7591\u5185\u5bb9" in response.reply
    assert "\u624b\u673a\u53f7" in response.reply


def test_question_during_lead_hook_is_answered_instead_of_treated_as_invalid_phone():
    engine = ConversationEngine(rag_service=StubRagService("\u53ef\u4ee5\u7ee7\u7eed\u95ee\uff0c\u6211\u5148\u5e2e\u60a8\u89e3\u7b54\u8fd9\u4e2a\u95ee\u9898\u3002"))
    session = engine.create_session("lead-hook-question")
    engine.handle_message(session, "\u9ad8\u4e2d/\u4e2d\u4e13")
    engine.handle_message(session, "\u5347\u5927\u4e13")
    engine.handle_message(session, "\u8003\u516c\u8003\u7f16")
    engine.handle_message(session, "\u600e\u4e48\u62a5\u540d")

    response = engine.handle_message(session, "\u62a5\u540d\u9700\u8981\u4ec0\u4e48\u6750\u6599")

    assert response.state == "intent_router"
    assert response.lead_required is False
    assert response.used_rag is True
    assert "\u53ef\u4ee5\u7ee7\u7eed\u95ee" in response.reply
    assert "11\u4f4d\u5927\u9646\u624b\u673a\u53f7" not in response.reply


def test_continue_consulting_intent_during_lead_hook_invites_next_question():
    engine = ConversationEngine()
    session = engine.create_session("lead-hook-continue")
    engine.handle_message(session, "\u6211\u60f3\u62a5\u540d\uff0c\u591a\u5c11\u94b1\uff1f")

    response = engine.handle_message(session, "\u6211\u5148\u95ee\u4e2a\u95ee\u9898")

    assert response.state == "intent_router"
    assert response.lead_required is False
    assert "\u60a8\u76f4\u63a5\u95ee" in response.reply
    assert "\u77e5\u8bc6\u5e93\u6ca1\u6709\u627e\u5230" not in response.reply
    assert "11\u4f4d\u5927\u9646\u624b\u673a\u53f7" not in response.reply


def test_refusal_during_lead_hook_still_creates_downgraded_lead():
    crm = InMemoryCrm()
    engine = ConversationEngine(crm=crm)
    session = engine.create_session("lead-hook-refusal")
    engine.handle_message(session, "\u6211\u60f3\u62a5\u540d\uff0c\u591a\u5c11\u94b1\uff1f")

    response = engine.handle_message(session, "\u7a0d\u540e\u518d\u8bf4")

    assert response.state == "intent_router"
    assert response.lead_saved is True
    assert "crm_lead_id" in response.slots
    assert crm.leads[-1].lead_type == "downgraded"


def test_phone_validation_rejects_invalid_and_accepts_valid_number():
    engine = ConversationEngine()
    session = engine.create_session("s3")
    engine.handle_message(session, "多少钱")

    invalid = engine.handle_message(session, "12345")
    valid = engine.handle_message(session, "13800138000")

    assert invalid.state == "phone_verify"
    assert "11位" in invalid.reply
    assert valid.state == "success"
    assert valid.slots["phone"] == "13800138000"
    assert valid.lead_saved is True


def test_continue_consulting_after_success_invites_next_question_without_rag_fallback():
    engine = ConversationEngine(rag_service=StubRagService(None))
    session = engine.create_session("success-continue")
    engine.handle_message(session, "多少钱")
    engine.handle_message(session, "13800138000")

    response = engine.handle_message(session, "继续咨询")

    assert response.state == "intent_router"
    assert response.lead_required is False
    assert response.used_rag is False
    assert "您直接问" in response.reply
    assert "知识库没有找到" not in response.reply


def test_free_text_uses_rag_answer_when_available():
    engine = ConversationEngine(rag_service=StubRagService("2025年广东成人高考报名时间为9月9日。"))
    session = engine.create_session("rag")
    engine.handle_message(session, "高中/中专")
    engine.handle_message(session, "升大专")
    engine.handle_message(session, "考公考编")

    response = engine.handle_message(session, "2025年广东成考什么时候报名？")

    assert response.state == "intent_router"
    assert "9月9日" in response.reply
    assert response.lead_required is False
    assert response.used_rag is True
    assert response.rag_sources[0]["chunk_id"] == "chunk_1"


def test_free_text_rewrites_query_before_rag_lookup():
    rag_service = StubRagService("2025年广东成人高考报名时间为9月9日。")
    rewriter = StubQueryRewriter("2025年广东成人高考报名时间是什么时候？")
    engine = ConversationEngine(rag_service=rag_service, query_rewriter=rewriter)
    session = engine.create_session("rewrite-rag")
    engine.handle_message(session, "高中/中专")
    engine.handle_message(session, "升大专")
    engine.handle_message(session, "考公考编")

    response = engine.handle_message(session, "2025年广东成考什么时候报名？")

    assert response.used_rag is True
    assert rewriter.calls[0] == ("2025年广东成考什么时候报名？", [])
    assert rag_service.calls == ["2025年广东成人高考报名时间是什么时候？"]


def test_follow_up_rewrite_receives_recent_history():
    rag_service = StubRagService("这是知识库回答。")
    rewriter = StubQueryRewriter("成人高考报名时间是什么时候？")
    engine = ConversationEngine(rag_service=rag_service, query_rewriter=rewriter)
    session = engine.create_session("rewrite-history")
    engine.handle_message(session, "高中/中专")
    engine.handle_message(session, "升大专")
    engine.handle_message(session, "考公考编")
    first_response = engine.handle_message(session, "成人高考和国开有什么区别？")

    engine.handle_message(session, "报名时间呢？")

    assert rewriter.calls[1][0] == "报名时间呢？"
    assert rewriter.calls[1][1] == [
        {"role": "user", "content": "成人高考和国开有什么区别？"},
        {"role": "assistant", "content": first_response.reply},
    ]
    assert rag_service.calls[-1] == "成人高考报名时间是什么时候？"


def test_conversation_records_user_and_assistant_history_for_free_text_turns():
    engine = ConversationEngine(rag_service=StubRagService("2025年广东成人高考报名时间为9月9日。"))
    session = engine.create_session("history-record")
    engine.handle_message(session, "高中/中专")
    engine.handle_message(session, "升大专")
    engine.handle_message(session, "考公考编")

    response = engine.handle_message(session, "2025年广东成考什么时候报名？")

    assert session.history[-2:] == [
        {"role": "user", "content": "2025年广东成考什么时候报名？"},
        {"role": "assistant", "content": response.reply},
    ]


def test_conversation_history_keeps_recent_ten_turns():
    engine = ConversationEngine(rag_service=StubRagService("这是知识库回答。"))
    session = engine.create_session("history-cap")
    engine.handle_message(session, "高中/中专")
    engine.handle_message(session, "升大专")
    engine.handle_message(session, "考公考编")

    for index in range(12):
        engine.handle_message(session, f"政策问题{index}")
        session.state = "intent_router"

    assert len(session.history) == 20
    assert session.history[0] == {"role": "user", "content": "政策问题2"}
    assert session.history[-2]["content"] == "政策问题11"


def test_reset_session_clears_conversation_history():
    engine = ConversationEngine(rag_service=StubRagService("这是知识库回答。"))
    session = engine.create_session("history-reset")
    engine.handle_message(session, "高中/中专")
    engine.handle_message(session, "升大专")
    engine.handle_message(session, "考公考编")
    engine.handle_message(session, "怎么报名")

    engine.reset_session(session)

    assert session.history == []


def test_accepting_soft_lead_after_rag_fallback_enters_phone_verification_without_rag():
    rag_service = StubRagService(None)
    engine = ConversationEngine(rag_service=rag_service)
    session = engine.create_session("soft-lead-accept")
    engine.handle_message(session, "高中/中专")
    engine.handle_message(session, "升大专")
    engine.handle_message(session, "考公考编")

    fallback = engine.handle_message(session, "这个政策怎么判断")
    calls_after_fallback = list(rag_service.calls)
    response = engine.handle_message(session, "好")

    assert "知识库没有找到" in fallback.reply
    assert response.state == "phone_verify"
    assert response.lead_required is True
    assert response.used_rag is False
    assert response.rag_sources == []
    assert "手机号" in response.reply
    assert rag_service.calls == calls_after_fallback


def test_free_text_falls_back_when_rag_has_no_answer():
    engine = ConversationEngine(rag_service=StubRagService(None))
    session = engine.create_session("rag-miss")
    engine.handle_message(session, "高中/中专")
    engine.handle_message(session, "升大专")
    engine.handle_message(session, "考公考编")

    response = engine.handle_message(session, "这个政策在哪里看？")

    assert "知识库暂时还没接入" in response.reply or "没有找到" in response.reply
