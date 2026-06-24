from __future__ import annotations

import re
from typing import Protocol


SUPPORTED_SLOT_KEYS = ("education", "goal", "purpose", "city", "budget", "urgency")
REQUIRED_SLOT_KEYS = ("education", "goal", "purpose")

EDUCATION_ALIASES = {
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
GOAL_ALIASES = {
    "升大专": "升大专",
    "读大专": "升大专",
    "拿大专": "升大专",
    "升本科": "专升本",
    "专升本": "专升本",
    "拿本科": "专升本",
    "考证": "考证/职称",
    "不确定": "还不确定",
    "不知道": "还不确定",
}
PURPOSE_ALIASES = {
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
KNOWN_CITIES = (
    "广州",
    "深圳",
    "佛山",
    "东莞",
    "珠海",
    "中山",
    "惠州",
    "北京",
    "上海",
)


class SlotExtractor(Protocol):
    def extract(self, text: str, history: list[dict[str, str]] | None = None) -> dict[str, str]:
        ...


class RuleSlotExtractor:
    def extract(self, text: str, history: list[dict[str, str]] | None = None) -> dict[str, str]:
        slots: dict[str, str] = {}
        _set_first_match(slots, "education", text, EDUCATION_ALIASES)
        _set_first_match(slots, "goal", text, GOAL_ALIASES)
        _set_first_match(slots, "purpose", text, PURPOSE_ALIASES)

        city = _extract_city(text)
        if city:
            slots["city"] = city
        budget = _extract_budget(text)
        if budget:
            slots["budget"] = budget
        urgency = _extract_urgency(text)
        if urgency:
            slots["urgency"] = urgency
        return slots


def merge_slots(existing: dict[str, str], extracted: dict[str, str]) -> dict[str, str]:
    merged = dict(existing)
    for key, value in extracted.items():
        if key in SUPPORTED_SLOT_KEYS and value and not merged.get(key):
            merged[key] = value
    return merged


def normalize_extracted_slots(raw: dict[str, object]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key in SUPPORTED_SLOT_KEYS:
        value = raw.get(key)
        if not isinstance(value, str) or not value.strip():
            continue
        text = value.strip()
        if key == "education" and text not in set(EDUCATION_ALIASES.values()):
            continue
        if key == "goal" and text not in set(GOAL_ALIASES.values()):
            continue
        if key == "purpose" and text not in set(PURPOSE_ALIASES.values()):
            continue
        normalized[key] = text
    return normalized


def _set_first_match(slots: dict[str, str], key: str, text: str, aliases: dict[str, str]) -> None:
    for keyword, value in aliases.items():
        if keyword in text:
            slots[key] = value
            return


def _extract_city(text: str) -> str | None:
    for city in KNOWN_CITIES:
        if city in text:
            return city
    match = re.search(r"(?:我在|人在|城市|地区|坐标)([\u4e00-\u9fff]{2,4})", text)
    return match.group(1) if match else None


def _extract_budget(text: str) -> str | None:
    match = re.search(r"预算(?:是|大概|大约)?([一二三四五六七八九十\d万千以内以下左右\-~到]+)", text)
    if match:
        return match.group(1)
    match = re.search(r"([一二三四五六七八九十\d]+万以内)", text)
    return match.group(1) if match else None


def _extract_urgency(text: str) -> str | None:
    if any(keyword in text for keyword in ("尽快", "越快越好", "急", "马上", "近期")):
        return "尽快"
    if any(keyword in text for keyword in ("今年", "本年")):
        return "今年"
    return None
