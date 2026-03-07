"""
SMALL AX AGENT — DB 모델 (SQLAlchemy 2.0 async)
멀티세션 영속성 + 파이프라인 상태 저장
"""

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Column, String, Text, Integer, Float, Boolean,
    DateTime, JSON, ForeignKey, Enum
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class PipelineStage(str, PyEnum):
    INTERVIEW     = "interview"
    DECOMPOSE     = "decompose"
    AX_REVIEW     = "ax_review"
    ARCHITECT     = "architect"
    TOOL_MAP      = "tool_map"
    CODE_GEN      = "code_gen"
    VERIFY        = "verify"
    HUMAN_APPROVE = "human_approve"
    COMPLETE      = "complete"
    FAILED        = "failed"


class ProjectStatus(str, PyEnum):
    ACTIVE    = "active"
    PAUSED    = "paused"
    COMPLETE  = "complete"
    ARCHIVED  = "archived"


# ── Project (최상위 컨테이너) ─────────────────────────────
class Project(Base):
    __tablename__ = "projects"

    id            = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name          = Column(String(200), nullable=False)
    description   = Column(Text, default="")
    status        = Column(Enum(ProjectStatus), default=ProjectStatus.ACTIVE)
    business_type = Column(String(100), default="")
    created_at    = Column(DateTime, default=datetime.utcnow)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    sessions      = relationship("Session", back_populates="project", cascade="all, delete-orphan")
    artifacts     = relationship("Artifact", back_populates="project", cascade="all, delete-orphan")


# ── Session (대화 세션) ───────────────────────────────────
class Session(Base):
    __tablename__ = "sessions"

    id              = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id      = Column(String, ForeignKey("projects.id"), nullable=False)
    current_stage   = Column(Enum(PipelineStage), default=PipelineStage.INTERVIEW)
    pipeline_state  = Column(JSON, default=dict)   # AutomationState 전체 직렬화
    retry_count     = Column(Integer, default=0)
    total_tokens    = Column(Integer, default=0)
    is_active       = Column(Boolean, default=True)
    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project         = relationship("Project", back_populates="sessions")
    messages        = relationship("Message", back_populates="session", cascade="all, delete-orphan")


# ── Message (대화 메시지) ─────────────────────────────────
class Message(Base):
    __tablename__ = "messages"

    id          = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id  = Column(String, ForeignKey("sessions.id"), nullable=False)
    role        = Column(String(20), nullable=False)     # user | assistant | agent
    agent_name  = Column(String(50), default="")         # Interview | Decomposer | ...
    content     = Column(Text, nullable=False)
    msg_metadata = Column("metadata", JSON, default=dict)  # options, stage, completion_pct 등
    tokens_used = Column(Integer, default=0)
    created_at  = Column(DateTime, default=datetime.utcnow)

    session     = relationship("Session", back_populates="messages")


# ── Artifact (생성물 저장) ────────────────────────────────
class Artifact(Base):
    __tablename__ = "artifacts"

    id           = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id   = Column(String, ForeignKey("projects.id"), nullable=False)
    session_id   = Column(String, nullable=True)
    artifact_type = Column(String(50), nullable=False)  # workflow | design | code | test
    name         = Column(String(200), nullable=False)
    content      = Column(JSON, nullable=False)          # 구조화된 결과물
    version      = Column(Integer, default=1)
    approved     = Column(Boolean, default=False)
    created_at   = Column(DateTime, default=datetime.utcnow)

    project      = relationship("Project", back_populates="artifacts")


# ── PipelineRun (실행 기록 + 반성 학습용) ────────────────
class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id              = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id      = Column(String, ForeignKey("sessions.id"), nullable=False)
    stage           = Column(Enum(PipelineStage), nullable=False)
    agent_name      = Column(String(50), nullable=False)
    input_summary   = Column(Text, default="")
    output_summary  = Column(Text, default="")
    quality_score   = Column(Float, default=0.0)
    retry_count     = Column(Integer, default=0)
    tokens_used     = Column(Integer, default=0)
    duration_ms     = Column(Integer, default=0)
    error_message   = Column(Text, default="")
    created_at      = Column(DateTime, default=datetime.utcnow)
