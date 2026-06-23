import json
from pathlib import Path

from app.rag.service import MAX_RAG_ANSWER_CHARS, RagService


def write_service_chunks(path: Path) -> Path:
    rows = [
        {
            "chunk_id": "faq_2025_报名时间_013",
            "type": "faq",
            "content": "问：2025年广东成人高考报名时间是什么时候？\n答：2025年广东成人高考网上注册报名时间为9月9日9时—12日17时。",
            "question": "2025年广东成人高考报名时间是什么时候？",
            "answer": "2025年广东成人高考网上注册报名时间为9月9日9时—12日17时。",
            "year": "2025",
            "source_title": "2025年广东省成人高校招生考试报名公告",
            "source_url": "https://example.test/013",
            "source_doc_id": "013",
        },
        {
            "chunk_id": "013_2025_报名条件_001",
            "type": "policy_chunk",
            "content": "报考专升本的考生必须是已取得经教育部审定核准的国民教育系列专科毕业证书、本科结业证书或以上证书的人员。",
            "year": "2025",
            "source_title": "2025年广东省成人高校招生考试报名公告",
            "source_url": "https://example.test/013",
            "source_doc_id": "013",
            "section": "一、招生对象和报名条件",
        },
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows), encoding="utf-8")
    return path


def test_rag_service_answers_faq_with_source(tmp_path):
    service = RagService.from_jsonl(write_service_chunks(tmp_path / "chunks.jsonl"))

    answer = service.answer("2025年广东成人高考报名时间是什么时候？")

    assert answer is not None
    assert "9月9日9时" in answer.reply
    assert "来源：2025年广东省成人高校招生考试报名公告" in answer.reply
    assert answer.sources[0].source_url == "https://example.test/013"


def test_rag_service_answers_policy_chunk_with_source(tmp_path):
    service = RagService.from_jsonl(write_service_chunks(tmp_path / "chunks.jsonl"))

    answer = service.answer("专升本报名条件需要什么学历？")

    assert answer is not None
    assert "专科毕业证书" in answer.reply
    assert "来源：2025年广东省成人高校招生考试报名公告" in answer.reply


def test_rag_service_returns_none_when_no_source_matches(tmp_path):
    service = RagService.from_jsonl(write_service_chunks(tmp_path / "chunks.jsonl"))

    answer = service.answer("今天股票怎么走？")

    assert answer is None


class FakeVectorIndex:
    def search(self, query_embedding, top_k=5, min_score=0.1):
        return [
            type(
                "VectorMatch",
                (),
                {
                    "chunk_id": "vector_only",
                    "score": 0.88,
                    "chunk": {
                        "chunk_id": "vector_only",
                        "type": "policy_chunk",
                        "content": "语义检索命中的成人高考准考证打印安排。",
                        "source_title": "准考证打印通知",
                        "source_url": "https://example.test/vector",
                        "year": "2025",
                    },
                },
            )()
        ]


class FakeEmbeddingClient:
    def embed_texts(self, texts):
        return [[1.0, 0.0, 0.0] for _ in texts]


def test_rag_service_uses_vector_results_when_keyword_has_no_match(tmp_path):
    service = RagService.from_jsonl(
        write_service_chunks(tmp_path / "chunks.jsonl"),
        vector_index=FakeVectorIndex(),
        embedding_client=FakeEmbeddingClient(),
    )

    answer = service.answer("准考证打印安排")

    assert answer is not None
    assert "准考证打印安排" in answer.reply
    assert answer.sources[0].chunk_id == "vector_only"


class PipelineRetriever:
    def __init__(self):
        self.top_k_calls = []

    def search(self, query, top_k=5):
        self.top_k_calls.append(top_k)
        return [
            _pipeline_result(
                chunk_id=f"keyword_{index}",
                content=f"alpha beta keyword {index}",
                score=100 - index,
                source_title=f"keyword source {index}",
            )
            for index in range(20)
        ][:top_k]


class PipelineVectorIndex:
    def __init__(self):
        self.top_k_calls = []

    def search(self, query_embedding, top_k=5, min_score=0.1):
        self.top_k_calls.append(top_k)
        return [
            type(
                "VectorMatch",
                (),
                {
                    "chunk_id": f"vector_{index}",
                    "score": 1.0 - index / 100,
                    "chunk": {
                        "chunk_id": f"vector_{index}",
                        "type": "policy_chunk",
                        "content": f"alpha beta vector {index}",
                        "source_title": f"vector source {index}",
                        "source_url": f"https://example.test/vector/{index}",
                        "year": "2025",
                    },
                },
            )()
            for index in range(20)
        ][:top_k]


class PipelineGenerator:
    def __init__(self):
        self.calls = []

    def generate_rag_answer(self, query, sources):
        self.calls.append((query, sources))
        return "generated from top sources"


class CompressingGenerator(PipelineGenerator):
    def __init__(self, generated_answer):
        super().__init__()
        self.generated_answer = generated_answer
        self.compress_calls = []

    def generate_rag_answer(self, query, sources):
        self.calls.append((query, sources))
        return self.generated_answer

    def compress_rag_answer(self, query, answer, sources, *, max_chars):
        self.compress_calls.append((query, answer, sources, max_chars))
        return "compressed answer"


def _pipeline_result(chunk_id, content, score, source_title):
    return type(
        "SearchResult",
        (),
        {
            "chunk_id": chunk_id,
            "type": "policy_chunk",
            "content": content,
            "score": score,
            "source_title": source_title,
            "source_url": f"https://example.test/{chunk_id}",
            "year": "2025",
            "section": None,
            "question": None,
            "answer": None,
        },
    )()


class FixedRetriever:
    def __init__(self, results):
        self.results = results

    def search(self, query, top_k=5):
        return self.results[:top_k]


class PassthroughReranker:
    def rerank(self, query, candidates, *, top_k=5):
        return candidates[:top_k]


class HighConfidenceReranker:
    def rerank(self, query, candidates, *, top_k=5):
        reranked = candidates[:top_k]
        for candidate in reranked:
            candidate.score = 0.9
        return reranked


class SignupProcessReranker:
    def rerank(self, query, candidates, *, top_k=5):
        reranked = candidates[:top_k]
        for candidate in reranked:
            candidate.score = 0.18
        return reranked


def test_rag_service_pipeline_uses_rrf_rerank_and_top3_generation():
    retriever = PipelineRetriever()
    vector_index = PipelineVectorIndex()
    generator = PipelineGenerator()
    service = RagService(
        retriever,
        vector_index=vector_index,
        embedding_client=FakeEmbeddingClient(),
        generator=generator,
        reranker=HighConfidenceReranker(),
    )

    answer = service.answer("alpha beta")

    assert answer is not None
    assert retriever.top_k_calls == [20]
    assert vector_index.top_k_calls == [20]
    assert len(answer.sources) == 5
    assert len(generator.calls[0][1]) == 3
    assert "generated from top sources" in answer.reply


def test_rag_service_compresses_generated_answer_when_it_is_too_long():
    generator = CompressingGenerator("a" * (MAX_RAG_ANSWER_CHARS + 1))
    service = RagService(
        FixedRetriever([
            _pipeline_result("long", "alpha beta policy", 0.9, "long source"),
        ]),
        generator=generator,
        reranker=HighConfidenceReranker(),
    )

    answer = service.answer("alpha beta")

    assert answer is not None
    assert "compressed answer" in answer.reply
    assert "a" * MAX_RAG_ANSWER_CHARS not in answer.reply
    assert len(generator.compress_calls) == 1
    assert generator.compress_calls[0][3] == MAX_RAG_ANSWER_CHARS


def test_rag_service_does_not_compress_short_generated_answer():
    generator = CompressingGenerator("short answer")
    service = RagService(
        FixedRetriever([
            _pipeline_result("short", "alpha beta policy", 0.9, "short source"),
        ]),
        generator=generator,
        reranker=HighConfidenceReranker(),
    )

    answer = service.answer("alpha beta")

    assert answer is not None
    assert "short answer" in answer.reply
    assert generator.compress_calls == []


def test_rag_service_compresses_short_answer_that_looks_truncated():
    generator = CompressingGenerator("notice opening text ends with colon：")
    service = RagService(
        FixedRetriever([
            _pipeline_result("truncated", "alpha beta policy", 0.9, "truncated source"),
        ]),
        generator=generator,
        reranker=HighConfidenceReranker(),
    )

    answer = service.answer("alpha beta")

    assert answer is not None
    assert "compressed answer" in answer.reply
    assert len(generator.compress_calls) == 1


def test_rag_service_rejects_low_confidence_top_result():
    generator = PipelineGenerator()
    service = RagService(
        FixedRetriever([
            _pipeline_result("low", "adult education policy", 0.18, "low source"),
        ]),
        generator=generator,
        reranker=SignupProcessReranker(),
    )

    answer = service.answer("adult education policy")

    assert answer is None
    assert generator.calls == []


def test_rag_service_rejects_when_query_entity_is_missing_from_sources():
    generator = PipelineGenerator()
    service = RagService(
        FixedRetriever([
            _pipeline_result("fee", "成人高考报名费为每科37元。", 0.31, "报名费公告"),
            _pipeline_result("time", "成人高考报名时间为9月。", 0.29, "报名时间公告"),
        ]),
        generator=generator,
        reranker=PassthroughReranker(),
    )

    answer = service.answer("成考和国开区别")

    assert answer is None
    assert generator.calls == []


def test_rag_service_accepts_signup_process_answer_below_general_score_threshold():
    generator = PipelineGenerator()
    service = RagService(
        FixedRetriever([
            _pipeline_result(
                "process",
                "\u62a5\u540d\u65b9\u5f0f\uff1a\u8003\u751f\u987b\u767b\u5f55\u62a5\u540d\u7cfb\u7edf\u8fdb\u884c\u7f51\u4e0a\u62a5\u540d\u3002\u5177\u4f53\u62a5\u540d\u6d41\u7a0b\u5305\u62ec\u7f51\u4e0a\u586b\u5199\u4fe1\u606f\u3001\u4e0a\u4f20\u6750\u6599\u548c\u786e\u8ba4\u62a5\u540d\u3002",
                0.18,
                "\u62a5\u540d\u6d41\u7a0b\u516c\u544a",
            ),
        ]),
        generator=generator,
        reranker=SignupProcessReranker(),
    )

    answer = service.answer("\u600e\u4e48\u62a5\u540d")

    assert answer is not None
    assert generator.calls
