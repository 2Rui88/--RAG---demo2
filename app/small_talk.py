from __future__ import annotations

from typing import Protocol


class SmallTalkResponder(Protocol):
    def respond(self, text: str, *, off_topic: bool = False) -> str:
        ...


class TemplateSmallTalkResponder:
    def respond(self, text: str, *, off_topic: bool = False) -> str:
        normalized = text.strip().lower()
        if off_topic:
            return "这个我帮不上，不过关于学历提升、报考条件、证书用途这些问题，我可以继续帮您梳理。"
        if any(keyword in normalized for keyword in ("谢谢", "感谢", "辛苦")):
            return "不客气，您可以继续问学历提升、报考条件、报名流程、学信网或证书用途相关问题。"
        if any(keyword in normalized for keyword in ("再见", "拜拜", "下次")):
            return "好的，后面有学历提升相关问题随时来问，我会继续帮您梳理。"
        if any(keyword in normalized for keyword in ("在吗", "在不在")):
            return "我在的。您可以继续问学历提升、报考条件、报名流程、学信网或证书用途相关问题。"
        return "您好，我在的。您可以继续问学历提升、报考条件、报名流程、学信网或证书用途相关问题。"
