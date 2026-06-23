from app.llm_client import QwenClient
from app.rag.retriever import SearchResult


class FakeChatCompletions:
    def __init__(self) -> None:
        self.requests = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        return type(
            "Completion",
            (),
            {"choices": [type("Choice", (), {"message": type("Message", (), {"content": "生成后的政策回答"})()})()]},
        )()


class FakeChat:
    def __init__(self) -> None:
        self.completions = FakeChatCompletions()


class FakeOpenAI:
    def __init__(self) -> None:
        self.chat = FakeChat()


def source(chunk_id: str, content: str) -> SearchResult:
    return SearchResult(
        chunk_id=chunk_id,
        type="policy_chunk",
        content=content,
        score=1,
        source_title=f"来源{chunk_id}",
        source_url=f"https://example.test/{chunk_id}",
        year="2025",
    )


def test_qwen_compresses_rag_answer_with_source_constraints():
    fake = FakeOpenAI()
    client = QwenClient()
    client.enabled = True
    client.client = fake

    reply = client.compress_rag_answer(
        "\u62a5\u540d\u6750\u6599\u662f\u4ec0\u4e48\uff1f",
        "\u8fd9\u662f\u4e00\u6bb5\u5f88\u957f\u7684\u56de\u7b54\uff0c\u9700\u8981\u538b\u7f29\u3002",
        [source("1", "\u62a5\u540d\u6750\u6599\u5305\u62ec\u8eab\u4efd\u8bc1\u548c\u5b66\u5386\u8bc1\u660e\u3002")],
        max_chars=200,
    )

    assert reply == "\u751f\u6210\u540e\u7684\u653f\u7b56\u56de\u7b54"
    request = fake.chat.completions.requests[0]
    assert "\u538b\u7f29" in request["messages"][0]["content"]
    assert "\u4e0d\u5f97\u65b0\u589e" in request["messages"][0]["content"]
    assert "200" in request["messages"][1]["content"]


def test_qwen_compression_falls_back_to_trimmed_answer_when_model_fails():
    client = QwenClient()
    client.enabled = False
    long_answer = "\u7532" * 260

    reply = client.compress_rag_answer("\u95ee\u9898", long_answer, [source("1", "\u8d44\u6599")], max_chars=80)

    assert len(reply) <= 83
    assert reply.endswith("...")


def test_qwen_generates_rag_answer_from_top_sources():
    fake = FakeOpenAI()
    client = QwenClient()
    client.enabled = True
    client.client = fake

    reply = client.generate_rag_answer("报名时间是什么？", [source("1", "报名时间为9月9日。")])

    assert reply == "生成后的政策回答"
    request = fake.chat.completions.requests[0]
    assert "只能依据给定资料" in request["messages"][0]["content"]
    assert "报名时间为9月9日" in request["messages"][1]["content"]


def test_qwen_rag_generation_falls_back_when_disabled():
    client = QwenClient()
    client.enabled = False

    reply = client.generate_rag_answer("报名时间是什么？", [source("1", "报名时间为9月9日。")])

    assert "报名时间为9月9日" in reply
