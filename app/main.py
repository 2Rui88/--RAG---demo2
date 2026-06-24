from __future__ import annotations

from pathlib import Path
import os

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.conversation import ConversationEngine, ConversationResponse, ConversationSession
from app.crm import CrmLead, InMemoryCrm
from app.llm_client import QwenClient
from app.rag.embedding import DEFAULT_EMBEDDING_DIMENSION
from app.rag.index_manager import RagIndexManager
from app.rag.service import RagService


BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
RAG_CHUNKS_PATH = BASE_DIR / "data" / "rag" / "chunks.jsonl"
RAG_VECTOR_CACHE_PATH = BASE_DIR / "data" / "rag" / "vector_index.json"
RAG_EMBEDDING_ENABLED = os.getenv("RAG_EMBEDDING_ENABLED", "false").lower() == "true"
RAG_QUERY_REWRITE_ENABLED = os.getenv("RAG_QUERY_REWRITE_ENABLED", "true").lower() == "true"
INTENT_ROUTER_ENABLED = os.getenv("INTENT_ROUTER_ENABLED", "true").lower() == "true"
SLOT_FILLING_ENABLED = os.getenv("SLOT_FILLING_ENABLED", "true").lower() == "true"

app = FastAPI(title="RAG Lead Capture Demo", version="0.1.0")
crm = InMemoryCrm()
qwen = QwenClient()
rag_manager = (
    RagIndexManager(
        chunks_path=RAG_CHUNKS_PATH,
        vector_cache_path=RAG_VECTOR_CACHE_PATH,
        generator=qwen,
        embedding_dimension=DEFAULT_EMBEDDING_DIMENSION,
    )
    if RAG_CHUNKS_PATH.exists() and RAG_EMBEDDING_ENABLED
    else None
)
if rag_manager and RAG_VECTOR_CACHE_PATH.exists():
    rag_service = rag_manager.load()
else:
    rag_service = RagService.from_jsonl(RAG_CHUNKS_PATH, generator=qwen) if RAG_CHUNKS_PATH.exists() else None
engine = ConversationEngine(
    crm=crm,
    rag_service=rag_service,
    query_rewriter=qwen if RAG_QUERY_REWRITE_ENABLED else None,
    intent_router=qwen if INTENT_ROUTER_ENABLED else None,
    slot_extractor=qwen if SLOT_FILLING_ENABLED else None,
)
sessions: dict[str, ConversationSession] = {}


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=80)
    message: str = Field(min_length=1, max_length=1000)


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    state: str
    slots: dict[str, str]
    quick_replies: list[str]
    lead_required: bool
    lead_saved: bool
    used_rag: bool
    rag_sources: list[dict[str, str | float | None]]


class CrmLeadResponse(BaseModel):
    lead_id: str
    session_id: str
    lead_type: str
    source: str
    slots: dict[str, str]
    phone: str | None
    refusal_reason: str | None
    created_at: str


class CrmLeadsResponse(BaseModel):
    leads: list[CrmLeadResponse]


class RagStatusResponse(BaseModel):
    enabled: bool
    embedding_enabled: bool
    chunks_path: str
    vector_cache_path: str
    vector_cache_exists: bool


class RagRebuildResponse(BaseModel):
    status: str
    message: str
    chunk_count: int | None = None
    embedding_dimension: int | None = None


def get_session(session_id: str) -> ConversationSession:
    if session_id not in sessions:
        sessions[session_id] = engine.create_session(session_id)
    return sessions[session_id]


def to_chat_response(session_id: str, response: ConversationResponse) -> ChatResponse:
    return ChatResponse(
        session_id=session_id,
        reply=response.reply,
        state=response.state,
        slots=response.slots,
        quick_replies=response.quick_replies,
        lead_required=response.lead_required,
        lead_saved=response.lead_saved,
        used_rag=response.used_rag,
        rag_sources=response.rag_sources,
    )


def to_crm_lead_response(lead: CrmLead) -> CrmLeadResponse:
    return CrmLeadResponse(
        lead_id=lead.lead_id,
        session_id=lead.session_id,
        lead_type=lead.lead_type,
        source=lead.source,
        slots=lead.slots,
        phone=lead.phone,
        refusal_reason=lead.refusal_reason,
        created_at=lead.created_at,
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    session = get_session(request.session_id)
    response = engine.handle_message(session, request.message)
    return to_chat_response(request.session_id, response)


@app.post("/api/sessions/{session_id}/reset", response_model=ChatResponse)
def reset_session(session_id: str) -> ChatResponse:
    session = get_session(session_id)
    response = engine.reset_session(session)
    return to_chat_response(session_id, response)


@app.get("/api/crm/leads", response_model=CrmLeadsResponse)
def list_crm_leads() -> CrmLeadsResponse:
    return CrmLeadsResponse(leads=[to_crm_lead_response(lead) for lead in crm.leads])


@app.get("/api/rag/status", response_model=RagStatusResponse)
def rag_status() -> RagStatusResponse:
    return RagStatusResponse(
        enabled=rag_service is not None,
        embedding_enabled=RAG_EMBEDDING_ENABLED,
        chunks_path=str(RAG_CHUNKS_PATH),
        vector_cache_path=str(RAG_VECTOR_CACHE_PATH),
        vector_cache_exists=RAG_VECTOR_CACHE_PATH.exists(),
    )


@app.post("/api/rag/rebuild", response_model=RagRebuildResponse)
def rebuild_rag_index() -> RagRebuildResponse:
    global rag_service
    if not RAG_EMBEDDING_ENABLED or rag_manager is None:
        return RagRebuildResponse(
            status="disabled",
            message="向量索引重建未启用。请设置 RAG_EMBEDDING_ENABLED=true 后重启服务。",
        )

    summary = rag_manager.rebuild()
    rag_service = rag_manager.service
    engine.rag_service = rag_service
    return RagRebuildResponse(
        status="ok",
        message="向量索引已重建并写入缓存。",
        chunk_count=int(summary["chunk_count"]),
        embedding_dimension=int(summary["embedding_dimension"]),
    )


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")
