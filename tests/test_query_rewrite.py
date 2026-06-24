from app.llm_client import QwenClient
from app.rag.query_rewrite import NoopQueryRewriter


def test_noop_query_rewriter_returns_original_query():
    rewriter = NoopQueryRewriter()

    rewritten = rewriter.rewrite("专科升本科", history=[{"role": "user", "content": "成人高考"}])

    assert rewritten == "专科升本科"


def test_qwen_rewrite_query_returns_original_when_client_disabled(monkeypatch):
    monkeypatch.delenv("QWEN_API_KEY", raising=False)
    monkeypatch.setenv("LLM_ENABLED", "false")
    client = QwenClient()

    rewritten = client.rewrite_query("专科升本科")

    assert rewritten == "专科升本科"


def test_qwen_rewrite_query_uses_history_and_model_response(monkeypatch):
    monkeypatch.setenv("QWEN_API_KEY", "fake-key")
    monkeypatch.setenv("LLM_ENABLED", "true")
    monkeypatch.setenv("QWEN_MODEL", "qwen3.5-flash")

    captured = {}

    class FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            message = type("Message", (), {"content": "成人高考报名时间是什么时候？"})()
            choice = type("Choice", (), {"message": message})()
            return type("Completion", (), {"choices": [choice]})()

    class FakeChat:
        completions = FakeCompletions()

    class FakeClient:
        chat = FakeChat()

    client = QwenClient()
    client.client = FakeClient()
    client.enabled = True

    rewritten = client.rewrite_query(
        "报名时间呢？",
        history=[
            {"role": "user", "content": "成人高考和国开有什么区别？"},
            {"role": "assistant", "content": "二者在办学主体和学习形式上不同。"},
        ],
    )

    assert rewritten == "成人高考报名时间是什么时候？"
    assert captured["model"] == "qwen3.5-flash"
    prompt = captured["messages"][1]["content"]
    assert "成人高考和国开有什么区别？" in prompt
    assert "报名时间呢？" in prompt


def test_qwen_rewrite_query_falls_back_on_empty_model_response(monkeypatch):
    monkeypatch.setenv("QWEN_API_KEY", "fake-key")
    monkeypatch.setenv("LLM_ENABLED", "true")

    class FakeCompletions:
        def create(self, **kwargs):
            message = type("Message", (), {"content": "   "})()
            choice = type("Choice", (), {"message": message})()
            return type("Completion", (), {"choices": [choice]})()

    class FakeChat:
        completions = FakeCompletions()

    class FakeClient:
        chat = FakeChat()

    client = QwenClient()
    client.client = FakeClient()
    client.enabled = True

    rewritten = client.rewrite_query("成人高考")

    assert rewritten == "成人高考"
