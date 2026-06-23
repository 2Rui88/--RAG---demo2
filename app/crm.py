from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal


LeadType = Literal["full", "downgraded"]


@dataclass
class CrmLead:
    lead_id: str
    session_id: str
    lead_type: LeadType
    source: str
    slots: dict[str, str]
    phone: str | None = None
    refusal_reason: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class InMemoryCrm:
    def __init__(self) -> None:
        self.leads: list[CrmLead] = []

    def create_lead(
        self,
        *,
        session_id: str,
        slots: dict[str, str],
        lead_type: LeadType,
        phone: str | None = None,
        refusal_reason: str | None = None,
        source: str = "chat_demo",
    ) -> CrmLead:
        lead = CrmLead(
            lead_id=f"lead_{len(self.leads) + 1}",
            session_id=session_id,
            lead_type=lead_type,
            source=source,
            slots={key: value for key, value in slots.items() if key not in {"phone", "crm_lead_id"}},
            phone=phone,
            refusal_reason=refusal_reason,
        )
        self.leads.append(lead)
        return lead
