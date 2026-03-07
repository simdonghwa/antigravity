"""
SMALL AX AGENT — Anthropic Tool Calling 정의 및 실행기
architect_node에서 사용: 패턴 검색, ROI 계산, 복잡도 추정
"""

from __future__ import annotations
import logging
from typing import Any

logger = logging.getLogger(__name__)

# ── Tool 정의 (Anthropic tools API 스키마) ───────────────────

ARCHITECT_TOOLS: list[dict] = [
    {
        "name": "search_automation_patterns",
        "description": (
            "RAG 지식베이스에서 유사한 자동화 패턴을 검색합니다. "
            "업종과 자동화할 업무를 입력하면 실제 검증된 패턴 사례를 반환합니다."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "business_type": {
                    "type": "string",
                    "description": "업종 (예: 스마트스토어, 카페, 헤어샵, 학원, 식당)",
                },
                "tasks": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "자동화할 반복 업무 목록 (예: ['주문 확인', '재고 업데이트', '리뷰 응답'])",
                },
                "n_results": {
                    "type": "integer",
                    "description": "반환할 패턴 수 (기본 4, 최대 8)",
                    "default": 4,
                },
            },
            "required": ["business_type", "tasks"],
        },
    },
    {
        "name": "calculate_roi",
        "description": (
            "자동화 도입 ROI(투자 수익률)를 계산합니다. "
            "주당 절감 시간, 시간당 인건비, 초기 구축 비용을 입력하면 "
            "월 절감액, 손익분기점(개월), 연 ROI(%)를 반환합니다."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "time_saved_hours_per_week": {
                    "type": "number",
                    "description": "주당 절감 예상 시간 (시간)",
                },
                "hourly_rate_krw": {
                    "type": "number",
                    "description": "시간당 인건비 (원, 기본 최저시급 9,860원)",
                    "default": 9860,
                },
                "setup_cost_krw": {
                    "type": "number",
                    "description": "초기 구축/도입 비용 총합 (원)",
                },
                "monthly_saas_cost_krw": {
                    "type": "number",
                    "description": "월 SaaS/도구 구독 비용 (원, 없으면 0)",
                    "default": 0,
                },
            },
            "required": ["time_saved_hours_per_week", "setup_cost_krw"],
        },
    },
    {
        "name": "estimate_complexity",
        "description": (
            "자동화 설계의 복잡도와 권장 구현 난이도를 추정합니다. "
            "컴포넌트 수와 외부 시스템 연동 수를 기반으로 "
            "난이도(LOW/MEDIUM/HIGH), 예상 구현 시간, 권장 도구를 반환합니다."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "component_count": {
                    "type": "integer",
                    "description": "자동화 컴포넌트(단계) 수",
                },
                "integration_count": {
                    "type": "integer",
                    "description": "연동할 외부 서비스/API 수 (예: 스마트스토어, 카카오, 구글 시트 등)",
                },
                "has_ai_component": {
                    "type": "boolean",
                    "description": "AI/LLM 처리 단계 포함 여부",
                    "default": False,
                },
            },
            "required": ["component_count", "integration_count"],
        },
    },
]


# ── Tool 실행기 ──────────────────────────────────────────────

async def execute_tool(tool_name: str, tool_input: dict[str, Any]) -> str:
    """Tool 이름에 따라 실제 함수 실행 후 결과를 문자열로 반환."""
    try:
        if tool_name == "search_automation_patterns":
            return await _run_search_patterns(**tool_input)
        elif tool_name == "calculate_roi":
            return _run_calculate_roi(**tool_input)
        elif tool_name == "estimate_complexity":
            return _run_estimate_complexity(**tool_input)
        else:
            return f"[Error] 알 수 없는 tool: {tool_name}"
    except Exception as e:
        logger.warning(f"Tool execution failed [{tool_name}]: {e}")
        return f"[Error] {tool_name} 실행 실패: {e}"


async def _run_search_patterns(
    business_type: str, tasks: list[str], n_results: int = 4
) -> str:
    import asyncio
    from rag.knowledge_base import rag_search_patterns_for_business, format_rag_context

    loop = asyncio.get_event_loop()
    patterns = await loop.run_in_executor(
        None, rag_search_patterns_for_business, business_type, tasks, min(n_results, 8)
    )
    if not patterns:
        return "유사 패턴 없음"
    return format_rag_context(patterns, max_chars=2000)


def _run_calculate_roi(
    time_saved_hours_per_week: float,
    setup_cost_krw: float,
    hourly_rate_krw: float = 9860,
    monthly_saas_cost_krw: float = 0,
) -> str:
    import json as _json

    weekly_saving = time_saved_hours_per_week * hourly_rate_krw
    monthly_saving = weekly_saving * 4.33
    net_monthly = monthly_saving - monthly_saas_cost_krw

    if net_monthly <= 0:
        breakeven_months = None
        annual_roi_pct = -100.0
    else:
        breakeven_months = round(setup_cost_krw / net_monthly, 1)
        annual_roi_pct = round((net_monthly * 12 - setup_cost_krw) / max(setup_cost_krw, 1) * 100, 1)

    result = {
        "monthly_labor_saving_krw": round(monthly_saving),
        "monthly_net_saving_krw": round(net_monthly),
        "breakeven_months": breakeven_months,
        "annual_roi_percent": annual_roi_pct,
        "summary": (
            f"월 {round(net_monthly/10000)}만원 절감, "
            f"손익분기 {breakeven_months}개월, "
            f"연 ROI {annual_roi_pct}%"
        ),
    }
    return _json.dumps(result, ensure_ascii=False)


def _run_estimate_complexity(
    component_count: int,
    integration_count: int,
    has_ai_component: bool = False,
) -> str:
    import json as _json

    score = component_count * 2 + integration_count * 3 + (5 if has_ai_component else 0)

    if score <= 10:
        level = "LOW"
        hours = "4~8시간"
        recommended_tool = "n8n (셀프호스팅) 또는 Make Free 플랜"
    elif score <= 22:
        level = "MEDIUM"
        hours = "1~3일"
        recommended_tool = "n8n 또는 Make Core 플랜"
    else:
        level = "HIGH"
        hours = "1주 이상"
        recommended_tool = "n8n + 커스텀 Python 함수 또는 Make Pro"

    result = {
        "complexity": level,
        "complexity_score": score,
        "estimated_build_time": hours,
        "recommended_tool": recommended_tool,
        "notes": (
            f"컴포넌트 {component_count}개, 외부 연동 {integration_count}개"
            + (", AI 처리 포함" if has_ai_component else "")
        ),
    }
    return _json.dumps(result, ensure_ascii=False)
