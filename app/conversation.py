from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

from app.crm import InMemoryCrm
from app.rag.service import RagService


State = Literal[
    "welcome",
    "qualification",
    "intent_router",
    "lead_hook",
    "phone_verify",
    "success",
]

LEAD_AFTER_QA_TURNS = 10


@dataclass
class ConversationSession:
    session_id: str
    state: State = "welcome"
    slots: dict[str, str] = field(default_factory=dict)
    qa_turns: int = 0
    pending_soft_lead: bool = False


@dataclass
class ConversationResponse:
    reply: str
    state: State
    slots: dict[str, str]
    quick_replies: list[str]
    lead_required: bool = False
    lead_saved: bool = False
    used_rag: bool = False
    rag_sources: list[dict[str, str | float | None]] = field(default_factory=list)


class ConversationEngine:
    education_choices = {"高中/中专", "大专", "本科", "初中及以下"}
    goal_choices = {"升大专", "专升本", "考证/职称", "还不确定"}
    purpose_choices = {"考公考编", "评职称", "积分落户", "找工作", "个人提升"}
    education_aliases = {
        "高中": "高中/中专",
        "中专": "高中/中专",
        "职高": "高中/中专",
        "技校": "高中/中专",
        "大专": "大专",
        "专科": "大专",
        "本科": "本科",
        "初中": "初中及以下",
        "小学": "初中及以下",
    }
    goal_aliases = {
        "升大专": "升大专",
        "读大专": "升大专",
        "拿大专": "升大专",
        "升本科": "专升本",
        "专升本": "专升本",
        "拿本科": "专升本",
        "考证": "考证/职称",
        "职称": "考证/职称",
        "不确定": "还不确定",
        "不知道": "还不确定",
    }
    purpose_aliases = {
        "考公": "考公考编",
        "考编": "考公考编",
        "公务员": "考公考编",
        "评职称": "评职称",
        "职称": "评职称",
        "落户": "积分落户",
        "积分": "积分落户",
        "找工作": "找工作",
        "求职": "找工作",
        "个人提升": "个人提升",
        "提升自己": "个人提升",
    }

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
        "联系老师",
        "老师联系",
        "让老师联系",
        "老师怎么联系",
        "人工老师",
        "人工客服",
        "加微信",
        "电话联系",
        "我想报",
    )
    factual_registration_keywords = (
        "报名时间",
        "什么时候报名",
        "几号报名",
        "哪天报名",
        "报名截止",
        "截止时间",
    )
    unrelated_keywords = ("天气", "股票", "做饭", "游戏", "电影", "旅游")
    greeting_keywords = ("你好", "您好", "哈喽", "hello", "hi", "在吗", "在不在")
    continue_consulting_keywords = ("先问个问题", "问个问题", "继续问", "继续咨询", "再问一下")
    soft_lead_accept_keywords = ("好", "可以", "同意", "要", "需要", "愿意", "行", "嗯", "对", "帮我算", "核算")
    phone_pattern = re.compile(r"^1[3-9]\d{9}$")

    def __init__(self, crm: InMemoryCrm | None = None, rag_service: RagService | None = None) -> None:
        self.crm = crm
        self.rag_service = rag_service

    def create_session(self, session_id: str) -> ConversationSession:
        return ConversationSession(session_id=session_id)

    def reset_session(self, session: ConversationSession) -> ConversationResponse:
        session.state = "welcome"
        session.slots.clear()
        session.qa_turns = 0
        session.pending_soft_lead = False
        return self.welcome_response(session)

    def welcome_response(self, session: ConversationSession) -> ConversationResponse:
        session.state = "qualification"
        return self._response(
            session,
            "您好，我是学历提升规划助手。先帮您做个简单诊断，方便后面给到更合适的方向。您目前的最高学历是？",
            self._quick_replies_for(session),
        )

    def handle_message(self, session: ConversationSession, message: str) -> ConversationResponse:
        text = message.strip()
        if not text:
            return self._response(session, "您可以直接输入问题，或点击下面的快捷选项。", self._quick_replies_for(session))

        if session.state in {"lead_hook", "phone_verify"} and self._should_handle_phone_step(text):
            return self._handle_phone_step(session, text)
        if session.state in {"lead_hook", "phone_verify"}:
            session.state = "intent_router"
            if self._is_continue_consulting_intent(text):
                return self._continue_consulting_response(session)
            return self._handle_free_text(session, text)

        if session.state == "success" and self._is_continue_consulting_intent(text):
            session.state = "intent_router"
            return self._continue_consulting_response(session)

        if session.pending_soft_lead:
            if self._is_soft_lead_acceptance(text):
                session.pending_soft_lead = False
                session.state = "phone_verify"
                return self._response(
                    session,
                    "可以的。方便留个手机号吗？老师会根据您当前学历、目标层次和用途免费帮您核算更适合的方案。",
                    ["稍后再说"],
                    lead_required=True,
                )
            session.pending_soft_lead = False

        if self._is_direct_lead_intent(text):
            return self._lead_hook(session)

        if session.state in {"welcome", "qualification"}:
            return self._handle_qualification(session, text)

        return self._handle_free_text(session, text)

    def _handle_qualification(self, session: ConversationSession, text: str) -> ConversationResponse:
        session.state = "qualification"
        if "education" not in session.slots:
            education = self._match_choice(text, self.education_choices, self.education_aliases)
            if not education:
                return self._qualification_prompt(
                    session,
                    "您好，我在的。可以先帮您做个简单学历提升诊断，您目前的最高学历是？",
                )
            session.slots["education"] = education
            return self._response(
                session,
                f"了解，您目前是{session.slots['education']}。接下来想提升到哪个阶段？",
                self._quick_replies_for(session),
            )

        if "goal" not in session.slots:
            goal = self._match_choice(text, self.goal_choices, self.goal_aliases)
            if not goal:
                return self._qualification_prompt(session, "我先按步骤帮您梳理。您想提升到哪个阶段？")
            session.slots["goal"] = goal
            return self._response(
                session,
                f"好的，目标先按{session.slots['goal']}记录。您提升学历主要准备用在哪方面？",
                self._quick_replies_for(session),
            )

        if "purpose" not in session.slots:
            purpose = self._match_choice(text, self.purpose_choices, self.purpose_aliases)
            if not purpose:
                return self._qualification_prompt(session, "用途不同，推荐的方式也会不一样。您提升学历主要准备用在哪方面？")
            session.slots["purpose"] = purpose
            session.state = "intent_router"
            return self._response(
                session,
                "信息我先记下了。您可以继续问学历形式、学信网、报考条件等问题；如果想核算费用或报名方案，我也可以帮您约老师免费规划。",
                self._quick_replies_for(session),
            )

        session.state = "intent_router"
        return self._handle_free_text(session, text)

    def _handle_free_text(self, session: ConversationSession, text: str) -> ConversationResponse:
        if self._is_greeting(text):
            return self._response(
                session,
                "您好，我在的。您可以继续问学历提升、报考条件、报名流程、学信网或证书用途相关问题。",
                self._quick_replies_for(session),
            )

        if self._is_unrelated(text):
            return self._response(
                session,
                "这个我帮不上，不过关于学历提升、报考条件、证书用途这些问题，我可以继续帮您梳理。",
                self._quick_replies_for(session),
            )

        session.qa_turns += 1
        if session.qa_turns >= LEAD_AFTER_QA_TURNS:
            return self._answer_then_lead_hook(session, text)

        answer_response = self._answer_user_need(session, text)
        if answer_response:
            return answer_response
        return self._fallback_answer_response(session)

    def _answer_user_need(self, session: ConversationSession, text: str) -> ConversationResponse | None:
        if self.rag_service:
            rag_answer = self.rag_service.answer(text)
            if rag_answer:
                reply = rag_answer.reply
                if self._is_signup_process_intent(text):
                    reply = self._with_signup_soft_hook(reply)
                return self._response(
                    session,
                    reply,
                    self._quick_replies_for(session),
                    used_rag=True,
                    rag_sources=_format_rag_sources(rag_answer.sources),
                )
        return None

    def _fallback_answer_response(self, session: ConversationSession) -> ConversationResponse:
        session.pending_soft_lead = True
        return self._response(
            session,
            "当前知识库没有找到明确依据。一般学历提升会重点看当前学历、目标层次、用途和可投入时间。您要不要先让老师免费帮您核算一下更适合的方案？",
            self._quick_replies_for(session),
        )

    def _answer_then_lead_hook(self, session: ConversationSession, text: str) -> ConversationResponse:
        answer_response = self._answer_user_need(session, text) or self._fallback_answer_response(session)
        return self._lead_hook(
            session,
            prefix=answer_response.reply,
            used_rag=answer_response.used_rag,
            rag_sources=answer_response.rag_sources,
        )

    def _lead_hook(
        self,
        session: ConversationSession,
        *,
        prefix: str | None = None,
        used_rag: bool = False,
        rag_sources: list[dict[str, str | float | None]] | None = None,
    ) -> ConversationResponse:
        session.state = "lead_hook"
        education = session.slots.get("education", "您的")
        purpose = session.slots.get("purpose", "后续使用")
        hook = (
            f"您这个情况需要结合{education}基础和{purpose}用途来核算，像具体费用、是否符合报考条件、最快多久能拿证这些问题，都要看个人情况来判断，不能简单一概而论。"
            "老师可以免费帮您算具体费用和适合路径，方便留个手机号吗？只是初步沟通，不强制报名。"
        )
        reply = f"{prefix}\n\n{hook}" if prefix else hook
        return self._response(
            session,
            reply,
            ["稍后再说", "我先问个问题"],
            lead_required=True,
            used_rag=used_rag,
            rag_sources=rag_sources,
        )

    def _handle_phone_step(self, session: ConversationSession, text: str) -> ConversationResponse:
        if text in {"稍后再说", "不用", "不留", "拒绝"}:
            session.state = "intent_router"
            lead_saved = False
            if self.crm:
                lead = self.crm.create_lead(
                    session_id=session.session_id,
                    slots=session.slots,
                    lead_type="downgraded",
                    refusal_reason="user_refused_phone",
                )
                session.slots["crm_lead_id"] = lead.lead_id
                lead_saved = True
            return self._response(
                session,
                "先不用留手机号也没关系。我先把您的基础情况记录为待跟进线索，您可以继续咨询；如果后面想要免费规划费用、资格和拿证时间，再留手机号也可以。",
                self._quick_replies_for(session),
                lead_saved=lead_saved,
            )

        if not self.phone_pattern.match(text):
            session.state = "phone_verify"
            return self._response(
                session,
                "您暂未输入手机号码或手机号码格式错误，手机号需要是11位大陆手机号，例如 13800138000。您可以重新输入，或先继续咨询。",
                ["稍后再说"],
            )

        session.slots["phone"] = text
        if self.crm:
            lead = self.crm.create_lead(
                session_id=session.session_id,
                slots=session.slots,
                lead_type="full",
                phone=text,
            )
            session.slots["crm_lead_id"] = lead.lead_id
        session.state = "success"
        return self._response(
            session,
            "已收到，老师会根据您当前学历、提升目标和用途做免费规划后联系您。您也可以继续在这里问学历提升相关问题。",
            ["继续咨询"],
            lead_saved=True,
        )

    def _should_handle_phone_step(self, text: str) -> bool:
        if text in {"稍后再说", "不用", "不留", "拒绝"}:
            return True
        return bool(self.phone_pattern.match(text) or re.search(r"\d", text))

    def _is_continue_consulting_intent(self, text: str) -> bool:
        return any(keyword in text for keyword in self.continue_consulting_keywords)

    def _continue_consulting_response(self, session: ConversationSession) -> ConversationResponse:
        return self._response(
            session,
            "可以的，您直接问就行。我会先根据知识库帮您回答；如果后面需要核算费用、资格或报名路径，再留手机号也可以。",
            self._quick_replies_for(session),
        )

    def _quick_replies_for(self, session: ConversationSession) -> list[str]:
        if "education" not in session.slots:
            return ["高中/中专", "大专", "本科", "初中及以下"]
        if "goal" not in session.slots:
            return ["升大专", "专升本", "考证/职称", "还不确定"]
        if "purpose" not in session.slots:
            return ["考公考编", "评职称", "积分落户", "找工作", "个人提升"]
        return ["费用", "我能不能报", "成考和国开区别", "怎么报名"]

    def _match_choice(self, text: str, choices: set[str], aliases: dict[str, str]) -> str | None:
        for choice in choices:
            if choice in text:
                return choice
        for keyword, value in aliases.items():
            if keyword in text:
                return value
        return None

    def _qualification_prompt(self, session: ConversationSession, reply: str) -> ConversationResponse:
        return self._response(session, reply, self._quick_replies_for(session))

    def _is_direct_lead_intent(self, text: str) -> bool:
        if any(keyword in text for keyword in self.factual_registration_keywords):
            return False
        return any(keyword in text for keyword in self.direct_lead_keywords)

    def _is_signup_process_intent(self, text: str) -> bool:
        return "报名" in text and any(keyword in text for keyword in ("怎么", "如何", "咋", "方式", "流程", "步骤"))

    def _with_signup_soft_hook(self, reply: str) -> str:
        hook = "如果您想结合自己的学历基础判断更适合的报考层次，我可以继续帮您做个简单诊断。"
        return reply if hook in reply else f"{reply}\n\n{hook}"

    def _is_unrelated(self, text: str) -> bool:
        return any(keyword in text for keyword in self.unrelated_keywords)

    def _is_greeting(self, text: str) -> bool:
        normalized = text.strip().lower()
        return any(keyword in normalized for keyword in self.greeting_keywords)

    def _is_soft_lead_acceptance(self, text: str) -> bool:
        normalized = text.strip().lower()
        return any(keyword in normalized for keyword in self.soft_lead_accept_keywords)

    def _response(
        self,
        session: ConversationSession,
        reply: str,
        quick_replies: list[str],
        *,
        lead_required: bool = False,
        lead_saved: bool = False,
        used_rag: bool = False,
        rag_sources: list[dict[str, str | float | None]] | None = None,
    ) -> ConversationResponse:
        return ConversationResponse(
            reply=reply,
            state=session.state,
            slots=dict(session.slots),
            quick_replies=quick_replies,
            lead_required=lead_required,
            lead_saved=lead_saved,
            used_rag=used_rag,
            rag_sources=rag_sources or [],
        )


def _format_rag_sources(sources: list[object]) -> list[dict[str, str | float | None]]:
    formatted = []
    for source in sources[:5]:
        content = str(getattr(source, "content", "") or "")
        formatted.append(
            {
                "chunk_id": str(getattr(source, "chunk_id", "") or ""),
                "source_title": str(getattr(source, "source_title", "") or ""),
                "source_url": str(getattr(source, "source_url", "") or ""),
                "score": float(getattr(source, "score", 0.0) or 0.0),
                "content_preview": content[:160],
            }
        )
    return formatted
