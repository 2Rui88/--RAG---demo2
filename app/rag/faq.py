from __future__ import annotations

import re

from app.rag.models import RagChunk, RagDocument


REGISTRATION_TIME_PATTERN = re.compile(
    r"考生网上注册报名[:：]?(?P<register>[^；。]+)[；;，,].*?考生网上缴费确认[:：]?(?P<payment>[^；。]+)"
)
FEE_PATTERN = re.compile(r"(?:考试收费标准|报名费|考试费)[^。；;]*?(每科\s*\d+元)")


def generate_faq_chunks(document: RagDocument) -> list[RagChunk]:
    chunks: list[RagChunk] = []
    chunks.extend(_registration_time_faq(document))
    chunks.extend(_fee_faq(document))
    return chunks


def _registration_time_faq(document: RagDocument) -> list[RagChunk]:
    match = REGISTRATION_TIME_PATTERN.search(document.text)
    if not match or not document.year:
        return []

    answer = (
        f"{document.year}年广东成人高考网上注册报名时间为{match.group('register')}，"
        f"网上缴费确认时间为{match.group('payment')}。"
    )
    return [
        RagChunk(
            chunk_id=f"faq_{document.year}_报名时间_{document.doc_id}",
            type="faq",
            question=f"{document.year}年广东成人高考报名时间是什么时候？",
            answer=answer,
            content=f"问：{document.year}年广东成人高考报名时间是什么时候？\n答：{answer}",
            aliases=["广东成考什么时候报名？", "成人高考几号开始报名？", "成考报名截止时间是什么时候？"],
            year=document.year,
            source_doc_id=document.doc_id,
            source_title=document.title,
            source_url=document.url,
            section="报名时间",
        )
    ]


def _fee_faq(document: RagDocument) -> list[RagChunk]:
    match = FEE_PATTERN.search(document.text)
    if not match or not document.year:
        return []

    answer = f"根据{document.year}年相关通知，广东成人高考考试收费标准为{match.group(1)}。"
    return [
        RagChunk(
            chunk_id=f"faq_{document.year}_报名费_{document.doc_id}",
            type="faq",
            question=f"{document.year}年广东成人高考报名费是多少？",
            answer=answer,
            content=f"问：{document.year}年广东成人高考报名费是多少？\n答：{answer}",
            aliases=["广东成考报名费用是多少？", "成人高考考试费怎么收？", "成考每科多少钱？"],
            year=document.year,
            source_doc_id=document.doc_id,
            source_title=document.title,
            source_url=document.url,
            section="报名费用",
        )
    ]
