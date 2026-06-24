from __future__ import annotations

import os

from dotenv import load_dotenv
from openai import OpenAI

from app.rag.retriever import SearchResult


load_dotenv()


SYSTEM_PROMPT = """你是学历提升咨询智能客服，围绕学历提升、资质诊断、报考条件、证书用途和留资规划回答。
必须遵守：
1. 可以正常寒暄，但不要长时间闲聊，不回答与学历提升无关的问题。
2. 价格、个人能不能报、最快多久毕业、具体报名方式，不要答透；引导用户留下手机号，由老师免费规划。
3. 语气亲切、简洁，每次回答尽量把用户带回当前咨询主线。
4. 不编造资料外的政策、院校、价格或时间。"""

RAG_SYSTEM_PROMPT = """你是学历提升政策问答助手。只能依据给定资料回答，不得编造资料外的政策、时间、院校、价格或承诺。
如果资料不足以回答，要明确说明暂未在资料中找到依据。
涉及价格、个人是否能报、报名方案、最快毕业/拿证等转化型问题，不要答透，建议用户留下手机号由老师免费规划。
回答要简洁、自然，避免重复粘贴原文，不要输出资料编号清单。"""


RAG_COMPRESSION_SYSTEM_PROMPT = """你是学历提升政策问答的答案压缩器。请把已有回答压缩成适合客服对话展示的简洁版本。必须遵守：
1. 只压缩和整理已有回答，不得新增资料外事实、政策、时间、费用、院校或承诺。
2. 必须保留关键硬信息，例如时间、条件、材料、步骤、限制和来源依据。
3. 如果原回答已经说明资料不足，不要改写成确定答案。
4. 语气自然，优先用短段落或要点，避免长篇粘贴。"""


QUERY_REWRITE_SYSTEM_PROMPT = """你是学历提升领域查询改写助手。
请将用户问题改写为更适合知识库检索的标准问题。
要求：
1. 保留原始语义，不新增事实、时间、院校、价格或承诺。
2. 展开简称并补充常见领域术语，例如成人高考、成考、专升本、国家开放大学。
3. 如果用户问题依赖上文，可以结合最近对话补全省略对象。
4. 只输出一句改写后的问题，不要解释。"""


class QwenClient:
    def __init__(self) -> None:
        self.api_key = os.getenv("QWEN_API_KEY", "")
        self.base_url = os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        self.model = os.getenv("QWEN_MODEL", "qwen3.5-flash")
        self.enabled = bool(self.api_key) and os.getenv("LLM_ENABLED", "true").lower() == "true"
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=8.0, max_retries=0) if self.enabled else None

    def polish_reply(self, user_message: str, controlled_reply: str) -> str:
        if not self.enabled or not self.client:
            return controlled_reply

        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            "请把下面这段受控回复润色成自然客服口吻，不要增加事实、价格、院校、承诺或新的业务规则。\n"
                            f"用户输入：{user_message}\n"
                            f"受控回复：{controlled_reply}"
                        ),
                    },
                ],
                temperature=0.4,
                max_tokens=300,
            )
        except Exception:
            return controlled_reply

        content = completion.choices[0].message.content
        return content.strip() if content else controlled_reply

    def generate_rag_answer(self, query: str, sources: list[SearchResult]) -> str:
        fallback = _extractive_rag_fallback(sources)
        if not self.enabled or not self.client:
            return fallback

        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": RAG_SYSTEM_PROMPT},
                    {"role": "user", "content": _rag_user_prompt(query, sources)},
                ],
                temperature=0.2,
                max_tokens=500,
            )
        except Exception:
            return fallback

        content = completion.choices[0].message.content
        return content.strip() if content else fallback

    def compress_rag_answer(self, query: str, answer: str, sources: list[SearchResult], *, max_chars: int) -> str:
        fallback = _trim_text(answer, max_chars)
        if not self.enabled or not self.client:
            return fallback

        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": RAG_COMPRESSION_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": _rag_compression_prompt(query, answer, sources, max_chars),
                    },
                ],
                temperature=0.1,
                max_tokens=420,
            )
        except Exception:
            return fallback

        content = completion.choices[0].message.content
        return content.strip() if content else fallback

    def rewrite_query(self, query: str, history: list[dict[str, str]] | None = None) -> str:
        fallback = query
        if not self.enabled or not self.client:
            return fallback

        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": QUERY_REWRITE_SYSTEM_PROMPT},
                    {"role": "user", "content": _query_rewrite_prompt(query, history or [])},
                ],
                temperature=0.1,
                max_tokens=120,
            )
        except Exception:
            return fallback

        content = completion.choices[0].message.content
        rewritten = content.strip() if content else ""
        return rewritten or fallback

    def rewrite(self, query: str, history: list[dict[str, str]] | None = None) -> str:
        return self.rewrite_query(query, history)


def _rag_user_prompt(query: str, sources: list[SearchResult]) -> str:
    source_blocks = []
    for index, source in enumerate(sources, start=1):
        text = source.answer if source.type == "faq" and source.answer else source.content
        source_blocks.append(
            "\n".join(
                [
                    f"[资料{index}]",
                    f"标题：{source.source_title}",
                    f"年份：{source.year or '未知'}",
                    f"小节：{source.section or source.question or '未标注'}",
                    f"内容：{text.strip()}",
                ]
            )
        )
    return f"用户问题：{query}\n\n给定资料：\n" + "\n\n".join(source_blocks)


def _rag_compression_prompt(query: str, answer: str, sources: list[SearchResult], max_chars: int) -> str:
    source_titles = "；".join(source.source_title for source in sources if source.source_title)
    return (
        f"用户问题：{query}\n"
        f"目标长度：不超过{max_chars}个中文字符。\n"
        f"来源标题：{source_titles or '未标注'}\n\n"
        f"待压缩回答：\n{answer}"
    )


def _query_rewrite_prompt(query: str, history: list[dict[str, str]]) -> str:
    history_lines = []
    for item in history[-20:]:
        role = item.get("role", "")
        content = item.get("content", "")
        if role and content:
            history_lines.append(f"{role}: {content}")
    history_text = "\n".join(history_lines) if history_lines else "无"
    return f"最近对话：\n{history_text}\n\n用户问题：\n{query}"


def _extractive_rag_fallback(sources: list[SearchResult]) -> str:
    if not sources:
        return "暂未在知识库中找到足够依据回答这个问题。"
    best = sources[0]
    text = best.answer if best.type == "faq" and best.answer else best.content
    return _trim_text(text)


def _trim_text(text: str, limit: int = 320) -> str:
    cleaned = text.strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit].rstrip("，。；;") + "..."
