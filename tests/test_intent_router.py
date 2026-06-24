from app.intent_router import IntentResult, RuleIntentRouter
from app.llm_client import QwenClient


def test_rule_router_classifies_conversion_messages_as_lead():
    router = RuleIntentRouter()

    result = router.classify("我想报名，多少钱？")

    assert result.intent == "lead"
    assert result.confidence >= 0.9


def test_rule_router_keeps_factual_registration_time_as_rag():
    router = RuleIntentRouter()

    result = router.classify("2025年广东成考什么时候报名？")

    assert result.intent == "rag"


def test_rule_router_classifies_signup_process_as_rag():
    router = RuleIntentRouter()

    result = router.classify("成人高考怎么报名？")

    assert result.intent == "rag"


def test_rule_router_classifies_greeting_as_small_talk():
    router = RuleIntentRouter()

    result = router.classify("你好，在吗")

    assert result.intent == "small_talk"


def test_rule_router_classifies_unrelated_chat_as_small_talk():
    router = RuleIntentRouter()

    result = router.classify("今天天气怎么样？")

    assert result.intent == "small_talk"


def test_rule_router_classifies_human_service_request():
    router = RuleIntentRouter()

    result = router.classify("我要找人工客服")

    assert result.intent == "human_service"


def test_rule_router_defaults_education_policy_questions_to_rag():
    router = RuleIntentRouter()

    result = router.classify("成考和国开有什么区别？")

    assert result.intent == "rag"


def test_qwen_intent_classifier_returns_rule_result_when_disabled(monkeypatch):
    monkeypatch.delenv("QWEN_API_KEY", raising=False)
    monkeypatch.setenv("LLM_ENABLED", "false")
    client = QwenClient()

    result = client.classify_intent("多少钱？")

    assert result.intent == "lead"


def test_qwen_intent_classifier_parses_valid_json_response(monkeypatch):
    monkeypatch.setenv("QWEN_API_KEY", "fake-key")
    monkeypatch.setenv("LLM_ENABLED", "true")
    monkeypatch.setenv("QWEN_MODEL", "qwen3.5-flash")

    captured = {}

    class FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            message = type(
                "Message",
                (),
                {"content": '{"intent":"small_talk","confidence":0.96,"reason":"用户在寒暄"}'},
            )()
            choice = type("Choice", (), {"message": message})()
            return type("Completion", (), {"choices": [choice]})()

    class FakeChat:
        completions = FakeCompletions()

    class FakeClient:
        chat = FakeChat()

    client = QwenClient()
    client.client = FakeClient()
    client.enabled = True

    result = client.classify_intent("谢谢")

    assert result == IntentResult(intent="small_talk", confidence=0.96, reason="用户在寒暄")
    assert captured["model"] == "qwen3.5-flash"
    assert "谢谢" in captured["messages"][1]["content"]


def test_qwen_intent_classifier_falls_back_when_confidence_is_low(monkeypatch):
    monkeypatch.setenv("QWEN_API_KEY", "fake-key")
    monkeypatch.setenv("LLM_ENABLED", "true")

    class FakeCompletions:
        def create(self, **kwargs):
            message = type("Message", (), {"content": '{"intent":"rag","confidence":0.4}'})()
            choice = type("Choice", (), {"message": message})()
            return type("Completion", (), {"choices": [choice]})()

    class FakeChat:
        completions = FakeCompletions()

    class FakeClient:
        chat = FakeChat()

    client = QwenClient()
    client.client = FakeClient()
    client.enabled = True

    result = client.classify_intent("多少钱？")

    assert result.intent == "lead"


def test_qwen_intent_classifier_falls_back_on_invalid_json(monkeypatch):
    monkeypatch.setenv("QWEN_API_KEY", "fake-key")
    monkeypatch.setenv("LLM_ENABLED", "true")

    class FakeCompletions:
        def create(self, **kwargs):
            message = type("Message", (), {"content": "不是 JSON"})()
            choice = type("Choice", (), {"message": message})()
            return type("Completion", (), {"choices": [choice]})()

    class FakeChat:
        completions = FakeCompletions()

    class FakeClient:
        chat = FakeChat()

    client = QwenClient()
    client.client = FakeClient()
    client.enabled = True

    result = client.classify_intent("我要找人工客服")

    assert result.intent == "human_service"
