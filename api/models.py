"""
SMALL AX AGENT — Pydantic API 모델
Request / Response 스키마
"""

from __future__ import annotations
from typing import Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field


# ── 공통 ─────────────────────────────────────────────────

class BaseResponse(BaseModel):
    success: bool = True
    message: str = ""


# ── 프로젝트 ─────────────────────────────────────────────

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = ""


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: str
    status: str
    business_type: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── 세션 ─────────────────────────────────────────────────

class SessionCreate(BaseModel):
    project_id: str


class SessionResponse(BaseModel):
    id: str
    project_id: str
    current_stage: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── 채팅 메시지 ───────────────────────────────────────────

class ChatRequest(BaseModel):
    session_id: str
    message: str = Field(..., min_length=1, max_length=4000)
    selected_option: str | None = None   # 버튼 선택 시


class ChatResponse(BaseModel):
    session_id: str
    stage: str
    agent_name: str
    content: str
    question_type: str | None = None
    options: list[str] = []
    completion_pct: int = 0
    metadata: dict = {}


# ── 파이프라인 제어 ───────────────────────────────────────

class ApprovalRequest(BaseModel):
    session_id: str
    approved: bool
    feedback: str = ""


class RetryRequest(BaseModel):
    session_id: str
    stage: str    # 어느 단계부터 재시작
    feedback: str = ""


# ── 아티팩트 ─────────────────────────────────────────────

class ArtifactResponse(BaseModel):
    id: str
    artifact_type: str
    name: str
    content: dict
    version: int
    approved: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── WebSocket 이벤트 ──────────────────────────────────────

class WsEvent(BaseModel):
    """WebSocket으로 전송되는 스트림 이벤트"""
    event_type: str
    agent_name: str
    stage: str
    content: Any
    timestamp: str
    metadata: dict = {}


class WsUserMessage(BaseModel):
    """WebSocket으로 수신되는 사용자 메시지"""
    type: Literal["chat", "approval", "retry", "ping"]
    session_id: str
    content: str = ""
    approved: bool | None = None
    feedback: str = ""
    selected_option: str | None = None


# ── 파이프라인 상태 조회 ──────────────────────────────────

class PipelineStatusResponse(BaseModel):
    session_id: str
    current_stage: str
    retry_count: int
    total_tokens_used: int
    estimated_cost_usd: float
    verification_score: int | None
    human_approved: bool | None
    artifacts: list[str]   # artifact types available
