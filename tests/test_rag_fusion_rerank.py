from app.rag.fusion import rrf_fuse
from app.rag.rerank import LightweightReranker
from app.rag.retriever import SearchResult


def result(chunk_id: str, content: str, score: float = 1.0, year: str | None = "2025", type_: str = "policy_chunk") -> SearchResult:
    return SearchResult(
        chunk_id=chunk_id,
        type=type_,
        content=content,
        score=score,
        source_title=f"source-{chunk_id}",
        source_url=f"https://example.test/{chunk_id}",
        year=year,
    )


def test_rrf_fuse_deduplicates_and_boosts_items_seen_in_both_lists():
    keyword = [result("a", "报名时间"), result("b", "报名条件")]
    vector = [result("b", "报名条件"), result("c", "准考证打印")]

    fused = rrf_fuse([keyword, vector], top_k=3)

    assert [item.chunk_id for item in fused] == ["b", "a", "c"]
    assert fused[0].score > fused[1].score


def test_lightweight_reranker_promotes_more_relevant_recent_faq():
    reranker = LightweightReranker()
    candidates = [
        result("old", "2024年广东成人高考报名费为每科37元", year="2024"),
        result("faq", "2025年广东成人高考报名时间为9月9日", year="2025", type_="faq"),
        result("weak", "广东成人高考录取工作结束", year="2025"),
    ]

    reranked = reranker.rerank("2025年广东成人高考报名时间是什么时候？", candidates, top_k=2)

    assert [item.chunk_id for item in reranked] == ["faq", "old"]


def test_lightweight_reranker_penalizes_mismatched_year():
    reranker = LightweightReranker()
    candidates = [
        result("old", "\u0032\u0030\u0032\u0034\u5e74\u5e7f\u4e1c\u6210\u4eba\u9ad8\u8003\u5f55\u53d6\u7ed3\u679c\u600e\u4e48\u67e5\u8be2\uff1f\u901a\u8fc7\u5c0f\u7a0b\u5e8f\u67e5\u8be2\u3002", score=10, year="2024", type_="faq"),
        result("new", "\u0032\u0030\u0032\u0035\u5e74\u5e7f\u4e1c\u6210\u4eba\u9ad8\u8003\u5f55\u53d6\u7ed3\u679c\u600e\u4e48\u67e5\u8be2\uff1f\u901a\u8fc7\u5c0f\u7a0b\u5e8f\u67e5\u8be2\u3002", score=9.9, year="2025", type_="faq"),
    ]

    reranked = reranker.rerank("\u0032\u0030\u0032\u0035\u5e74\u5e7f\u4e1c\u6210\u4eba\u9ad8\u8003\u5f55\u53d6\u7ed3\u679c\u600e\u4e48\u67e5\u8be2\uff1f", candidates, top_k=2)

    assert [item.chunk_id for item in reranked] == ["new", "old"]
