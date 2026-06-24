from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol


IntentName = Literal["faq", "rag", "small_talk", "lead", "human_service"]
MIN_MODEL_INTENT_CONFIDENCE = 0.7


@dataclass(frozen=True)
class IntentResult:
    intent: IntentName
    confidence: float
    reason: str = ""


class IntentRouter(Protocol):
    def classify(self, text: str, history: list[dict[str, str]] | None = None) -> IntentResult:
        ...


class RuleIntentRouter:
    direct_lead_keywords = (
        "多少钱",
        "价格",
        "费用",
        "报价",
        "能不能报",
        "可以报",
        "资格",
        "怎么交费",
        "缴费",
        "交钱",
        "多久毕业",
        "最快",
        "拿证",
        "加微信",
        "电话联系",
        "我想报",
    )
    human_service_keywords = (
        "联系老师",
        "老师联系",
        "让老师联系",
        "老师怎么联系",
        "人工老师",
        "人工客服",
        "人工",
        "客服",
    )
    factual_registration_keywords = (
        "报名时间",
        "什么时候报名",
        "几号报名",
        "哪天报名",
        "报名截止",
        "截止时间",
    )
    greeting_keywords = ("你好", "您好", "哈喽", "hello", "hi", "在吗", "在不在", "谢谢", "辛苦了", "再见")
    unrelated_keywords = ("天气", "股票", "做饭", "游戏", "电影", "旅游")

    def classify(self, text: str, history: list[dict[str, str]] | None = None) -> IntentResult:
        normalized = text.strip().lower()
        if any(keyword in normalized for keyword in self.human_service_keywords):
            return IntentResult("human_service", 0.95, "用户请求人工服务")
        if self._is_direct_lead_intent(normalized):
            return IntentResult("lead", 0.95, "用户咨询费用、资格或报名转化问题")
        if any(keyword in normalized for keyword in self.greeting_keywords):
            return IntentResult("small_talk", 0.95, "用户寒暄")
        if any(keyword in normalized for keyword in self.unrelated_keywords):
            return IntentResult("small_talk", 0.9, "用户咨询非学历提升话题")
        return IntentResult("rag", 0.8, "默认进入知识库问答")

    def _is_direct_lead_intent(self, text: str) -> bool:
        if any(keyword in text for keyword in self.factual_registration_keywords):
            return False
        return any(keyword in text for keyword in self.direct_lead_keywords)
