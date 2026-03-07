"""
SMALL AX AGENT — WebSocket 채팅 + 파이프라인 실행
실시간 스트리밍: 에이전트 활동 → 프론트엔드
"""

from __future__ import annotations
import asyncio
import json
import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db import get_db, Session as DBSession, Message as DBMessage, Artifact, PipelineRun, PipelineStage
from api.models import ApprovalRequest, WsUserMessage, ChatRequest, ChatResponse
from graph.state import initial_state, AutomationState
from graph.nodes import (
    interview_node, decompose_node, ax_review_node, architect_node,
    tool_mapper_node, code_gen_node, verifier_node, human_approval_node,
    complete_node, failed_node,
)
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["chat"])

# ── 스테이지 → 노드 매핑 ─────────────────────────────────
STAGE_NODES = {
    "interview":     interview_node,
    "decompose":     decompose_node,
    "ax_review":     ax_review_node,
    "architect":     architect_node,
    "tool_map":      tool_mapper_node,
    "code_gen":      code_gen_node,
    "verify":        verifier_node,
    "human_approve": human_approval_node,
    "complete":      complete_node,
    "failed":        failed_node,
}

def route_next_stage(state: AutomationState) -> str:
    """현재 상태 기반으로 다음 스테이지 결정"""
    stage = state.get("current_stage", "interview")
    if stage == "interview":
        return "decompose" if state.get("interview_complete") else "interview"
    if stage == "decompose":
        return "interview" if state.get("decomposition_quality", 100) < 40 else "ax_review"
    if stage == "verify":
        if state.get("verification_passed"):
            return "human_approve"
        retries = state.get("retry_count", 0)
        if retries >= settings.max_retry_count:
            return "failed"
        return "code_gen" if state.get("verification_score", 0) >= 60 else "architect"
    if stage == "human_approve":
        approved = state.get("human_approved")
        if approved is True:
            return "complete"
        if approved is False:
            return "architect"
        return "human_approve"
    linear = {"ax_review": "architect", "architect": "tool_map", "tool_map": "code_gen", "code_gen": "verify"}
    return linear.get(stage, stage)


# ── WebSocket 연결 관리 ───────────────────────────────────

class ConnectionManager:
    def __init__(self):
        self._connections: dict[str, WebSocket] = {}

    async def connect(self, session_id: str, ws: WebSocket):
        await ws.accept()
        self._connections[session_id] = ws
        logger.info(f"WebSocket connected: {session_id}")

    def disconnect(self, session_id: str):
        self._connections.pop(session_id, None)

    async def send(self, session_id: str, data: dict):
        ws = self._connections.get(session_id)
        if ws:
            try:
                await ws.send_json(data)
            except Exception as e:
                logger.warning(f"WS send failed ({session_id}): {e}")
                self.disconnect(session_id)

    async def broadcast_events(self, session_id: str, events: list[dict]):
        for event in events:
            await self.send(session_id, event)
            await asyncio.sleep(0.05)


manager = ConnectionManager()


# ── 파이프라인 실행 헬퍼 — 노드 직접 호출 방식 ───────────

async def run_pipeline_step(
    session_id: str,
    state: AutomationState,
    db: AsyncSession,
) -> AutomationState:
    """
    현재 스테이지에 맞는 노드를 직접 호출.
    LangGraph 체크포인터 없이 상태를 DB에 직접 저장.
    """
    stage = state.get("current_stage", "interview")
    node_fn = STAGE_NODES.get(stage, interview_node)

    logger.info(f"[Pipeline] Running stage={stage} session={session_id}")
    update = await node_fn(state)

    # 상태 업데이트 (messages, stream_events 는 append-only)
    new_state = {**state}
    for k, v in update.items():
        if k in ("messages", "stream_events"):
            new_state[k] = list(state.get(k, [])) + list(v)
        else:
            new_state[k] = v

    # 스트림 이벤트 → WebSocket 전송
    new_events = update.get("stream_events", [])
    if new_events:
        await manager.broadcast_events(session_id, new_events)

    # 새 메시지 → DB 저장
    for msg in update.get("messages", []):
        db.add(DBMessage(
            id=str(uuid.uuid4()),
            session_id=session_id,
            role=msg.get("role", "agent"),
            agent_name=msg.get("agent_name", ""),
            content=msg.get("content", ""),
        ))

    # 아티팩트 자동 저장
    await save_artifacts_from_output(session_id, stage, update, db)

    # DB 세션 상태 업데이트
    result = await db.execute(select(DBSession).where(DBSession.id == session_id))
    db_session = result.scalar_one_or_none()
    if db_session:
        db_session.pipeline_state = new_state
        db_session.current_stage = new_state.get("current_stage", stage)
        db_session.retry_count = new_state.get("retry_count", 0)

    await db.commit()
    return new_state


async def save_artifacts_from_output(
    session_id: str, node_name: str, output: dict, db: AsyncSession
):
    """노드 출력에서 아티팩트 자동 감지 + 저장"""
    artifact_map = {
        "workflow_decomposition": ("workflow", "워크플로우 분해"),
        "automation_design":      ("design",   "자동화 설계"),
        "tool_mapping":           ("tools",    "도구 매핑"),
        "generated_code":         ("code",     "생성 코드"),
        "verification_result":    ("verify",   "검증 결과"),
    }
    for field, (atype, aname) in artifact_map.items():
        if field in output and output[field]:
            existing = await db.execute(
                select(Artifact).where(
                    Artifact.session_id == session_id,
                    Artifact.artifact_type == atype,
                )
            )
            existing_art = existing.scalar_one_or_none()
            if existing_art:
                existing_art.content = output[field]
                existing_art.version = existing_art.version + 1
            else:
                db.add(Artifact(
                    id=str(uuid.uuid4()),
                    project_id="",  # session에서 채워야 함
                    session_id=session_id,
                    artifact_type=atype,
                    name=aname,
                    content=output[field],
                ))


# ── WebSocket 엔드포인트 ──────────────────────────────────

@router.websocket("/ws/{session_id}")
async def websocket_endpoint(session_id: str, ws: WebSocket, db: AsyncSession = Depends(get_db)):
    """
    실시간 양방향 통신:
    - 수신: 사용자 메시지 (WsUserMessage)
    - 송신: 에이전트 활동 스트림 (WsEvent)
    """
    await manager.connect(session_id, ws)

    # 세션 로드
    result = await db.execute(select(DBSession).where(DBSession.id == session_id))
    db_session = result.scalar_one_or_none()
    if not db_session:
        await ws.send_json({"event_type": "pipeline_error", "content": "세션을 찾을 수 없습니다"})
        await ws.close()
        return

    # 현재 상태 복원
    state: AutomationState = db_session.pipeline_state or initial_state(session_id, db_session.project_id)

    # 웰컴 이벤트
    await manager.send(session_id, {
        "event_type": "connected",
        "agent_name": "System",
        "stage": state.get("current_stage", "interview"),
        "content": f"세션 복원 완료 — 현재 단계: {state.get('current_stage', 'interview')}",
        "timestamp": datetime.utcnow().isoformat(),
        "metadata": {},
    })

    try:
        while True:
            # 사용자 메시지 수신
            raw = await ws.receive_text()
            try:
                ws_msg = WsUserMessage.model_validate_json(raw)
            except Exception:
                await manager.send(session_id, {
                    "event_type": "pipeline_error",
                    "content": "잘못된 메시지 형식",
                    "agent_name": "System", "stage": "", "timestamp": datetime.utcnow().isoformat(), "metadata": {},
                })
                continue

            if ws_msg.type == "ping":
                await manager.send(session_id, {"event_type": "pong", "agent_name": "System",
                    "stage": "", "content": "", "timestamp": datetime.utcnow().isoformat(), "metadata": {}})
                continue

            # 사용자 메시지를 상태에 추가
            user_content = ws_msg.selected_option or ws_msg.content
            user_msg = {
                "role": "user", "agent_name": "User",
                "content": user_content, "metadata": {},
                "timestamp": datetime.utcnow().isoformat(),
            }
            state["messages"] = state.get("messages", []) + [user_msg]

            # DB 저장
            db.add(DBMessage(
                id=str(uuid.uuid4()),
                session_id=session_id,
                role="user",
                agent_name="User",
                content=user_content,
            ))

            # 승인 처리
            if ws_msg.type == "approval":
                state["human_approved"] = ws_msg.approved
                state["human_feedback"] = ws_msg.feedback

            # 파이프라인 실행
            await manager.send(session_id, {
                "event_type": "agent_start", "agent_name": "System",
                "stage": state.get("current_stage", ""),
                "content": "처리 중...",
                "timestamp": datetime.utcnow().isoformat(), "metadata": {},
            })

            try:
                state = await run_pipeline_step(session_id, state, db)
            except Exception as e:
                logger.error(f"Pipeline error ({session_id}): {e}", exc_info=True)
                await manager.send(session_id, {
                    "event_type": "pipeline_error", "agent_name": "System",
                    "stage": state.get("current_stage", ""),
                    "content": f"오류 발생: {str(e)}",
                    "timestamp": datetime.utcnow().isoformat(), "metadata": {},
                })

            # 파이프라인 종료 확인
            if state.get("current_stage") in ("complete", "failed"):
                break

    except WebSocketDisconnect:
        logger.info(f"Client disconnected: {session_id}")
    finally:
        manager.disconnect(session_id)


# ── REST 폴백 (WebSocket 불가 환경) ─────────────────────

@router.post("/chat", response_model=ChatResponse)
async def chat_rest(body: ChatRequest, db: AsyncSession = Depends(get_db)):
    """WebSocket 대신 REST polling 방식 채팅 (폴백)"""
    result = await db.execute(select(DBSession).where(DBSession.id == body.session_id))
    db_session = result.scalar_one_or_none()
    if not db_session:
        raise HTTPException(404, "세션을 찾을 수 없습니다")

    state: AutomationState = db_session.pipeline_state or initial_state(
        body.session_id, db_session.project_id
    )

    user_content = body.selected_option or body.message
    state["messages"] = state.get("messages", []) + [{
        "role": "user", "agent_name": "User",
        "content": user_content, "metadata": {},
        "timestamp": datetime.utcnow().isoformat(),
    }]

    state = await run_pipeline_step(body.session_id, state, db)

    # 마지막 에이전트 메시지 추출
    last_agent_msg = next(
        (m for m in reversed(state.get("messages", [])) if m.get("role") == "agent"),
        {"content": "", "agent_name": "System", "metadata": {}}
    )

    meta = last_agent_msg.get("metadata", {})
    return ChatResponse(
        session_id=body.session_id,
        stage=state.get("current_stage", ""),
        agent_name=last_agent_msg.get("agent_name", ""),
        content=last_agent_msg.get("content", ""),
        question_type=meta.get("question_type"),
        options=meta.get("options", []),
        completion_pct=meta.get("completion_pct", 0),
        metadata=meta,
    )


# ── 승인 REST ────────────────────────────────────────────

@router.post("/approve")
async def approve_pipeline(body: ApprovalRequest, db: AsyncSession = Depends(get_db)):
    """Human approval REST endpoint"""
    result = await db.execute(select(DBSession).where(DBSession.id == body.session_id))
    db_session = result.scalar_one_or_none()
    if not db_session:
        raise HTTPException(404, "세션을 찾을 수 없습니다")

    state = db_session.pipeline_state or {}
    state["human_approved"] = body.approved
    state["human_feedback"] = body.feedback
    db_session.pipeline_state = state
    await db.commit()

    # WebSocket으로도 알림
    await manager.send(body.session_id, {
        "event_type": "agent_output",
        "agent_name": "HumanGate",
        "stage": "human_approve",
        "content": f"{'승인' if body.approved else '거절'} 처리됨",
        "timestamp": datetime.utcnow().isoformat(),
        "metadata": {"approved": body.approved},
    })

    return {"success": True, "approved": body.approved}


# ── 이메일 원클릭 승인 (GET) ──────────────────────────────────

@router.get("/approve/{session_id}")
async def email_approve_pipeline(
    session_id: str,
    token: str,
    action: str,
    db: AsyncSession = Depends(get_db),
):
    """
    이메일 원클릭 승인/거절 엔드포인트.
    token: HMAC 서명 토큰 (generate_approval_token으로 생성)
    action: 'approve' | 'reject'
    """
    from fastapi.responses import HTMLResponse
    from notification.email import verify_approval_token

    # 토큰 검증
    verified_action = verify_approval_token(token, session_id)
    if verified_action is None or verified_action != action:
        return HTMLResponse(
            "<h2>❌ 유효하지 않은 링크입니다.</h2><p>링크가 만료되었거나 잘못된 요청입니다.</p>",
            status_code=400,
        )

    result = await db.execute(select(DBSession).where(DBSession.id == session_id))
    db_session = result.scalar_one_or_none()
    if not db_session:
        return HTMLResponse("<h2>❌ 세션을 찾을 수 없습니다.</h2>", status_code=404)

    approved = (action == "approve")
    state = db_session.pipeline_state or {}
    state["human_approved"] = approved
    db_session.pipeline_state = state
    await db.commit()

    # WebSocket으로 알림
    await manager.send(session_id, {
        "event_type": "agent_output",
        "agent_name": "HumanGate",
        "stage": "human_approve",
        "content": f"이메일 {'승인' if approved else '거절'} 처리됨",
        "timestamp": datetime.utcnow().isoformat(),
        "metadata": {"approved": approved},
    })

    label = "승인" if approved else "거절"
    color = "#22c55e" if approved else "#ef4444"
    return HTMLResponse(f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8">
<style>body{{font-family:sans-serif;display:flex;justify-content:center;
align-items:center;height:100vh;background:#f8fafc;color:#1e293b;}}
.box{{text-align:center;padding:40px;background:#fff;border-radius:16px;
box-shadow:0 4px 24px rgba(0,0,0,.08);}}</style></head>
<body><div class="box">
<div style="font-size:3rem;">{'✅' if approved else '❌'}</div>
<h2 style="color:{color}">자동화 설계가 {label}되었습니다.</h2>
<p>창을 닫으셔도 됩니다.</p>
</div></body></html>""")
