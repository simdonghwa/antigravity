"""
SMALL AX AGENT — 워크플로우 Export API
n8n / Make 포맷으로 자동화 설계를 내보내기
"""

import json
import uuid
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db import get_db, Session as DBSession, Artifact
from export.n8n_converter import design_to_n8n, design_to_make

router = APIRouter(prefix="/api/export", tags=["export"])


async def _get_artifacts(session_id: str, db: AsyncSession) -> dict[str, dict]:
    """세션 아티팩트 딕셔너리 반환"""
    result = await db.execute(
        select(Artifact).where(Artifact.session_id == session_id)
    )
    arts = result.scalars().all()
    return {a.artifact_type: a.content for a in arts}


@router.get("/{session_id}/n8n")
async def export_n8n(session_id: str, db: AsyncSession = Depends(get_db)):
    """
    automation_design → n8n JSON 워크플로우로 변환 후 다운로드.
    n8n 대시보드에서 직접 import 가능한 파일.
    """
    result = await db.execute(select(DBSession).where(DBSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(404, "세션을 찾을 수 없습니다")

    artifacts = await _get_artifacts(session_id, db)
    design = artifacts.get("design")
    tools  = artifacts.get("tools")

    if not design:
        raise HTTPException(422, "자동화 설계 아티팩트가 없습니다. 파이프라인을 먼저 완료하세요.")

    state = session.pipeline_state or {}
    workflow_name = f"AX_{state.get('extracted_info', {}).get('business_type', 'automation')}_{session_id[:8]}"

    n8n_workflow = design_to_n8n(
        automation_design=design,
        tool_mapping=tools,
        workflow_name=workflow_name,
    )

    filename = f"n8n_workflow_{session_id[:8]}.json"
    return Response(
        content=json.dumps(n8n_workflow, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{session_id}/make")
async def export_make(session_id: str, db: AsyncSession = Depends(get_db)):
    """
    automation_design → Make(Integromat) 시나리오 JSON으로 변환.
    Make > Scenarios > Import 에서 사용 가능.
    """
    result = await db.execute(select(DBSession).where(DBSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(404, "세션을 찾을 수 없습니다")

    artifacts = await _get_artifacts(session_id, db)
    design = artifacts.get("design")
    tools  = artifacts.get("tools")

    if not design:
        raise HTTPException(422, "자동화 설계 아티팩트가 없습니다.")

    state = session.pipeline_state or {}
    scenario_name = f"AX_{state.get('extracted_info', {}).get('business_type', 'scenario')}_{session_id[:8]}"

    make_scenario = design_to_make(
        automation_design=design,
        tool_mapping=tools,
        scenario_name=scenario_name,
    )

    filename = f"make_scenario_{session_id[:8]}.json"
    return Response(
        content=json.dumps(make_scenario, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{session_id}/python")
async def export_python(session_id: str, db: AsyncSession = Depends(get_db)):
    """
    생성된 Python 코드 아티팩트를 .py 파일로 다운로드.
    """
    artifacts = await _get_artifacts(session_id, db)
    code_art = artifacts.get("code")

    if not code_art:
        raise HTTPException(422, "코드 아티팩트가 없습니다.")

    code_content = code_art.get("code", "# No code generated")
    filename = code_art.get("file_name", "automation.py")

    return Response(
        content=code_content,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{session_id}/summary")
async def export_summary(session_id: str, db: AsyncSession = Depends(get_db)):
    """
    전체 파이프라인 결과 요약 JSON 반환.
    (design + tools + code + verify 통합)
    """
    result = await db.execute(select(DBSession).where(DBSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(404, "세션을 찾을 수 없습니다")

    artifacts = await _get_artifacts(session_id, db)
    state = session.pipeline_state or {}

    return {
        "session_id": session_id,
        "status": session.current_stage,
        "business_type": state.get("extracted_info", {}).get("business_type", ""),
        "design_summary": {
            "pattern": (artifacts.get("design") or {}).get("primary_pattern", "N/A"),
            "components": len((artifacts.get("design") or {}).get("components", [])),
            "mermaid_diagram": (artifacts.get("design") or {}).get("mermaid_diagram", ""),
        },
        "tools_summary": {
            "monthly_cost_usd": (artifacts.get("tools") or {}).get("total_estimated_monthly_cost_usd", 0),
            "tool_count": len((artifacts.get("tools") or {}).get("tool_assignments", {})),
        },
        "code_summary": {
            "file_name": (artifacts.get("code") or {}).get("file_name", ""),
            "lines": len(str((artifacts.get("code") or {}).get("code", "")).splitlines()),
        },
        "verification": {
            "score": state.get("verification_score"),
            "verdict": (artifacts.get("verify") or {}).get("verdict", ""),
        },
        "downloads": {
            "n8n":    f"/api/export/{session_id}/n8n",
            "make":   f"/api/export/{session_id}/make",
            "python": f"/api/export/{session_id}/python",
        },
        "weekly_hours_saved": state.get("automation_summary", {}).get("estimated_weekly_hours_saved", 0),
        "total_tokens_used": state.get("total_tokens_used", 0),
    }
