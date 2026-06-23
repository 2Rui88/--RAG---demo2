import json
from pathlib import Path

from app.rag.retriever import LocalKeywordRetriever


def write_chunks(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        {
            "chunk_id": "faq_2025_报名时间_013",
            "type": "faq",
            "content": "问：2025年广东成人高考报名时间是什么时候？\n答：2025年广东成人高考网上注册报名时间为9月9日9时—12日17时。",
            "question": "2025年广东成人高考报名时间是什么时候？",
            "answer": "2025年广东成人高考网上注册报名时间为9月9日9时—12日17时。",
            "aliases": ["广东成考什么时候报名？"],
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
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows), encoding="utf-8")
    return path


def test_retriever_prefers_faq_for_exact_faq_question(tmp_path):
    retriever = LocalKeywordRetriever.from_jsonl(write_chunks(tmp_path / "chunks.jsonl"))

    results = retriever.search("2025年广东成考什么时候报名？", top_k=2)

    assert results[0].chunk_id == "faq_2025_报名时间_013"
    assert results[0].type == "faq"
    assert results[0].score > 0


def test_retriever_finds_policy_chunk_for_policy_question(tmp_path):
    retriever = LocalKeywordRetriever.from_jsonl(write_chunks(tmp_path / "chunks.jsonl"))

    results = retriever.search("专升本报名条件需要什么学历？", top_k=1)

    assert results[0].chunk_id == "013_2025_报名条件_001"
    assert "专科毕业证书" in results[0].content


def test_retriever_returns_empty_for_unrelated_question(tmp_path):
    retriever = LocalKeywordRetriever.from_jsonl(write_chunks(tmp_path / "chunks.jsonl"))

    results = retriever.search("今天股票怎么走？", top_k=3)

    assert results == []


def test_retriever_expands_signup_question_to_prefer_process_over_fee(tmp_path):
    path = tmp_path / "chunks.jsonl"
    rows = [
        {
            "chunk_id": "fee",
            "type": "faq",
            "content": "\u95ee\uff1a\u6210\u4eba\u9ad8\u8003\u62a5\u540d\u8d39\u662f\u591a\u5c11\uff1f\n\u7b54\uff1a\u6210\u4eba\u9ad8\u8003\u8003\u8bd5\u6536\u8d39\u6807\u51c6\u4e3a\u6bcf\u79d137\u5143\u3002",
            "question": "\u6210\u4eba\u9ad8\u8003\u62a5\u540d\u8d39\u662f\u591a\u5c11\uff1f",
            "answer": "\u6210\u4eba\u9ad8\u8003\u8003\u8bd5\u6536\u8d39\u6807\u51c6\u4e3a\u6bcf\u79d137\u5143\u3002",
            "source_title": "\u62a5\u540d\u8d39\u516c\u544a",
            "source_url": "https://example.test/fee",
        },
        {
            "chunk_id": "process",
            "type": "policy_chunk",
            "content": "\u62a5\u540d\u65b9\u5f0f\uff1a\u8003\u751f\u987b\u767b\u5f55\u6210\u4eba\u9ad8\u8003\u62a5\u540d\u7cfb\u7edf\u8fdb\u884c\u7f51\u4e0a\u62a5\u540d\u3002\u5177\u4f53\u62a5\u540d\u6d41\u7a0b\u5305\u62ec\u7f51\u4e0a\u586b\u5199\u4fe1\u606f\u3001\u4e0a\u4f20\u6750\u6599\u548c\u786e\u8ba4\u62a5\u540d\u3002",
            "section": "\u62a5\u540d\u65b9\u5f0f\u548c\u62a5\u540d\u6d41\u7a0b",
            "source_title": "\u62a5\u540d\u6d41\u7a0b\u516c\u544a",
            "source_url": "https://example.test/process",
        },
    ]
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows), encoding="utf-8")
    retriever = LocalKeywordRetriever.from_jsonl(path)

    results = retriever.search("\u600e\u4e48\u62a5\u540d", top_k=2)

    assert results[0].chunk_id == "process"


def test_retriever_expands_admission_time_query_to_prefer_result_section(tmp_path):
    path = tmp_path / "chunks.jsonl"
    rows = [
        {
            "chunk_id": "intro",
            "type": "policy_chunk",
            "content": "\u6211\u77012024\u5e74\u5168\u56fd\u6210\u4eba\u9ad8\u6821\u62db\u751f\u7edf\u4e00\u8003\u8bd5\u8bc4\u5377\u5de5\u4f5c\u5df2\u5168\u90e8\u5b8c\u6210\uff0c\u6210\u4eba\u9ad8\u8003\u5f55\u53d6\u5c06\u4e8e12\u6708\u4e2d\u4e0a\u65ec\u8fdb\u884c\u3002\u73b0\u5c06\u8003\u751f\u8003\u8bd5\u6210\u7ee9\u548c\u5f55\u53d6\u7ed3\u679c\u516c\u5e03\u7684\u6709\u5173\u4e8b\u9879\u901a\u77e5\u5982\u4e0b\uff1a",
            "source_title": "\u5173\u4e8e\u516c\u5e03\u5e7f\u4e1c\u77012024\u5e74\u6210\u4eba\u9ad8\u8003\u8003\u751f\u6210\u7ee9\u548c\u5f55\u53d6\u7ed3\u679c\u67e5\u8be2\u65b9\u5f0f\u7684\u901a\u77e5",
            "source_url": "https://example.test/intro",
            "year": "2024",
        },
        {
            "chunk_id": "result",
            "type": "policy_chunk",
            "content": "\u6210\u4eba\u9ad8\u8003\u5f55\u53d6\u671f\u95f4\uff0c\u901a\u8fc7\u7701\u6559\u80b2\u8003\u8bd5\u9662\u5b98\u5fae\u5c0f\u7a0b\u5e8f\u548c\u767e\u5ea6\u667a\u80fd\u5c0f\u7a0b\u5e8f\u53ef\u4ee5\u83b7\u53d6\u6216\u67e5\u8be2\u5f55\u53d6\u7ed3\u679c\u3002\u5f55\u53d6\u7ed3\u679c\u516c\u5e03\u65f6\u95f4\u8bf7\u7559\u610f\u5e7f\u4e1c\u7701\u6559\u80b2\u8003\u8bd5\u9662\u5b98\u65b9\u5fae\u4fe1\u3001\u5e7f\u4e1c\u7701\u6559\u80b2\u8003\u8bd5\u9662\u7f51\u7ad9\u3001\u5e7f\u4e1c\u6559\u80b2\u8003\u8bd5\u670d\u52a1\u7f51\u76f8\u5173\u516c\u544a\u8baf\u606f\u3002",
            "section": "\u6210\u7ee9\u548c\u5f55\u53d6\u7ed3\u679c\u516c\u5e03",
            "source_title": "\u5173\u4e8e\u516c\u5e03\u5e7f\u4e1c\u77012024\u5e74\u6210\u4eba\u9ad8\u8003\u8003\u751f\u6210\u7ee9\u548c\u5f55\u53d6\u7ed3\u679c\u67e5\u8be2\u65b9\u5f0f\u7684\u901a\u77e5",
            "source_url": "https://example.test/result",
            "year": "2024",
        },
    ]
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows), encoding="utf-8")
    retriever = LocalKeywordRetriever.from_jsonl(path)

    results = retriever.search("2024\u5e74\u6210\u4eba\u9ad8\u8003\u5f55\u53d6\u65f6\u95f4\u662f", top_k=2)

    assert results[0].chunk_id == "result"


def test_retriever_penalizes_mismatched_year_when_query_has_year(tmp_path):
    path = tmp_path / "chunks.jsonl"
    rows = [
        {
            "chunk_id": "fee_2024",
            "type": "faq",
            "content": "\u95ee\uff1a2024\u5e74\u5e7f\u4e1c\u6210\u4eba\u9ad8\u8003\u62a5\u540d\u8d39\u662f\u591a\u5c11\uff1f\n\u7b54\uff1a2024\u5e74\u6bcf\u79d137\u5143\u3002",
            "question": "2024\u5e74\u5e7f\u4e1c\u6210\u4eba\u9ad8\u8003\u62a5\u540d\u8d39\u662f\u591a\u5c11\uff1f",
            "answer": "2024\u5e74\u6bcf\u79d137\u5143\u3002",
            "year": "2024",
            "source_title": "2024\u62a5\u540d\u8d39\u516c\u544a",
            "source_url": "https://example.test/2024",
        },
        {
            "chunk_id": "fee_2025",
            "type": "faq",
            "content": "\u95ee\uff1a2025\u5e74\u5e7f\u4e1c\u6210\u4eba\u9ad8\u8003\u62a5\u540d\u8d39\u662f\u591a\u5c11\uff1f\n\u7b54\uff1a2025\u5e74\u6bcf\u79d137\u5143\u3002",
            "question": "2025\u5e74\u5e7f\u4e1c\u6210\u4eba\u9ad8\u8003\u62a5\u540d\u8d39\u662f\u591a\u5c11\uff1f",
            "answer": "2025\u5e74\u6bcf\u79d137\u5143\u3002",
            "year": "2025",
            "source_title": "2025\u62a5\u540d\u8d39\u516c\u544a",
            "source_url": "https://example.test/2025",
        },
    ]
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows), encoding="utf-8")
    retriever = LocalKeywordRetriever.from_jsonl(path)

    results = retriever.search("2025\u5e74\u6210\u4eba\u9ad8\u8003\u62a5\u540d\u8d39\u662f\u591a\u5c11", top_k=2)

    assert results[0].chunk_id == "fee_2025"
