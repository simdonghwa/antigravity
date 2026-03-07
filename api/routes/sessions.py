"""
SMALL AX AGENT — 세션/프로젝트 REST API
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from db import get_db, Project, Session as DBSession, Artifact, ProjectStatus
from api.models import (
    ProjectCreate, ProjectResponse, SessionCreate, SessionResponse,
    ArtifactResponse, PipelineStatusResponse,
)
from graph.state import initial_state

router = APIRouter(prefix="/api", tags=["sessions"])


# ── 프로젝트 ─────────────────────────────────────────────

@router.post("/projects", response_model=ProjectResponse)
async def create_project(body: ProjectCreate, db: AsyncSession = Depends(get_db)):
    project = Project(
        id=str(uuid.uuid4()),
        name=body.name,
        description=body.description,
    )
    db.add(project)
    await db.flush()
    await db.refresh(project)
    return project


@router.get("/projects", response_model=list[ProjectResponse])
async def list_projects(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Project).where(Project.status != ProjectStatus.ARCHIVED).order_by(Project.created_at.desc())
    )
    return result.scalars().all()


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "프로젝트를 찾을 수 없습니다")
    return project


# ── 세션 ─────────────────────────────────────────────────

@router.get("/sessions", response_model=list[SessionResponse])
async def list_sessions(
    limit: int = Query(default=20, le=100),
    db: AsyncSession = Depends(get_db),
):
    """최근 세션 목록 (limit개, 최신순)"""
    result = await db.execute(
        select(DBSession).order_by(DBSession.created_at.desc()).limit(limit)
    )
    return result.scalars().all()


@router.post("/sessions", response_model=SessionResponse)
async def create_session(body: SessionCreate, db: AsyncSession = Depends(get_db)):
    # 프로젝트 존재 확인
    result = await db.execute(select(Project).where(Project.id == body.project_id))
    if not result.scalar_one_or_none():
        raise HTTPException(404, "프로젝트를 찾을 수 없습니다")

    session_id = str(uuid.uuid4())
    state = initial_state(session_id=session_id, project_id=body.project_id)

    session = DBSession(
        id=session_id,
        project_id=body.project_id,
        current_stage="interview",
        pipeline_state=dict(state),
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)
    return session


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DBSession).where(DBSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(404, "세션을 찾을 수 없습니다")
    return session


@router.get("/sessions/{session_id}/status", response_model=PipelineStatusResponse)
async def get_pipeline_status(session_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DBSession).where(DBSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(404, "세션을 찾을 수 없습니다")

    state = session.pipeline_state or {}

    # 아티팩트 목록
    arts = await db.execute(
        select(Artifact.artifact_type).where(Artifact.session_id == session_id)
    )
    artifact_types = [r[0] for r in arts.fetchall()]

    return PipelineStatusResponse(
        session_id=session_id,
        current_stage=session.current_stage,
        retry_count=state.get("retry_count", 0),
        total_tokens_used=state.get("total_tokens_used", 0),
        estimated_cost_usd=state.get("estimated_cost_usd", 0.0),
        verification_score=state.get("verification_score"),
        human_approved=state.get("human_approved"),
        artifacts=artifact_types,
    )


@router.get("/sessions/{session_id}/artifacts", response_model=list[ArtifactResponse])
async def get_artifacts(session_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Artifact).where(Artifact.session_id == session_id)
        .order_by(Artifact.created_at)
    )
    return result.scalars().all()
