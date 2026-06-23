from app.rag.embedding import TongyiEmbeddingClient


class FakeTransport:
    def __init__(self) -> None:
        self.requests = []

    def __call__(self, url, payload, api_key):
        self.requests.append({"url": url, "payload": payload, "api_key": api_key})
        return {
            "output": {
                "embeddings": [
                    {"index": 0, "embedding": [1.0, 0.0, 0.0]},
                    {"index": 1, "embedding": [0.0, 1.0, 0.0]},
                ]
            }
        }


def test_tongyi_embedding_client_uses_configured_model_and_truncates_text():
    fake_transport = FakeTransport()
    client = TongyiEmbeddingClient(
        api_key="key",
        transport=fake_transport,
        embedding_dimension=3,
        embedding_max_chars=5,
    )

    embeddings = client.embed_texts(["123456789", "abc"])

    assert embeddings == [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]
    request = fake_transport.requests[0]["payload"]
    assert request["model"] == "tongyi-embedding-vision-flash-2026-03-06"
    assert request["input"]["contents"] == [{"text": "12345"}, {"text": "abc"}]
    assert request["parameters"]["dimension"] == 3
