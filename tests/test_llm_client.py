from app.llm_client import QwenClient


class BrokenCompletions:
    def create(self, **kwargs):
        raise RuntimeError("network unavailable")


class BrokenChat:
    completions = BrokenCompletions()


class BrokenClient:
    chat = BrokenChat()


def test_qwen_client_falls_back_to_controlled_reply_when_model_fails():
    client = QwenClient()
    client.enabled = True
    client.client = BrokenClient()

    reply = client.polish_reply("多少钱", "这个要根据您的情况核算。")

    assert reply == "这个要根据您的情况核算。"
