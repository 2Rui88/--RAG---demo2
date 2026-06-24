from app.llm_client import QwenClient
from app.slot_filling import RuleSlotExtractor, merge_slots


def test_rule_slot_extractor_extracts_multiple_required_slots():
    extractor = RuleSlotExtractor()

    slots = extractor.extract("我是大专，想专升本，主要为了考公")

    assert slots == {
        "education": "大专",
        "goal": "专升本",
        "purpose": "考公考编",
    }


def test_rule_slot_extractor_extracts_optional_slots():
    extractor = RuleSlotExtractor()

    slots = extractor.extract("我在广州，预算一万以内，想今年尽快报名")

    assert slots == {
        "city": "广州",
        "budget": "一万以内",
        "urgency": "尽快",
    }


def test_rule_slot_extractor_ignores_unknown_values():
    extractor = RuleSlotExtractor()

    slots = extractor.extract("我想学点东西")

    assert slots == {}


def test_merge_slots_preserves_existing_non_empty_values():
    existing = {"education": "大专", "goal": "专升本"}
    extracted = {"education": "本科", "purpose": "评职称", "city": ""}

    merged = merge_slots(existing, extracted)

    assert merged == {"education": "大专", "goal": "专升本", "purpose": "评职称"}


def test_qwen_extract_slots_returns_rule_result_when_disabled(monkeypatch):
    monkeypatch.delenv("QWEN_API_KEY", raising=False)
    monkeypatch.setenv("LLM_ENABLED", "false")
    client = QwenClient()

    slots = client.extract_slots("我是高中，想升大专")

    assert slots == {"education": "高中/中专", "goal": "升大专"}


def test_qwen_extract_slots_parses_valid_json_response(monkeypatch):
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
                {
                    "content": (
                        '{"education":"大专","goal":"专升本","purpose":"考公考编",'
                        '"city":"深圳","budget":"一万以内","urgency":"尽快"}'
                    )
                },
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

    slots = client.extract_slots("我是大专，人在深圳，想专升本考公，预算一万以内，尽快")

    assert slots == {
        "education": "大专",
        "goal": "专升本",
        "purpose": "考公考编",
        "city": "深圳",
        "budget": "一万以内",
        "urgency": "尽快",
    }
    assert captured["model"] == "qwen3.5-flash"
    assert "我是大专" in captured["messages"][1]["content"]


def test_qwen_extract_slots_falls_back_on_invalid_json(monkeypatch):
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

    slots = client.extract_slots("我是本科，想评职称")

    assert slots == {"education": "本科", "purpose": "评职称"}


def test_qwen_extract_slots_ignores_unsupported_values(monkeypatch):
    monkeypatch.setenv("QWEN_API_KEY", "fake-key")
    monkeypatch.setenv("LLM_ENABLED", "true")

    class FakeCompletions:
        def create(self, **kwargs):
            message = type(
                "Message",
                (),
                {"content": '{"education":"博士","goal":"读研","purpose":"宇宙旅行","city":"北京"}'},
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

    slots = client.extract_slots("北京")

    assert slots == {"city": "北京"}
