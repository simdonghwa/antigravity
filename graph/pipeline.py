"""
SMALL AX AGENT — LangGraph 파이프라인 조립
StateGraph + 조건부 엣지 + 루프 구조
"""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from graph.state import AutomationState
from graph.nodes import (
    interview_node, decompose_node, ax_review_node,
    architect_node, tool_mapper_node, code_gen_node,
    verifier_node, human_approval_node,
    complete_node, failed_node,
)
from config import settings


# ── 조건부 엣지 함수 ───────────────────────────────────────

def route_after_interview(state: AutomationState) -> str:
    """인터뷰 완료 여부 → 분기"""
    if state["interview_complete"]:
        return "decompose"
    return "interview"   # 계속 인터뷰


def route_after_verify(state: AutomationState) -> str:
    """검증 결과 → 분기 (핵심 루프)"""
    if state["verification_passed"]:
        return "human_approve"

    retry = state["retry_count"] + 1
    if retry > settings.max_retry_count:
        return "failed"

    # 검증 점수에 따라 재시도 지점 결정
    score = state["verification_score"]
    if score >= 60:
        # 경미한 문제 → 코드만 재생성
        return "code_gen"
    else:
        # 설계 수준 문제 → 아키텍처부터 재시작
        return "architect"


def route_after_human_approve(state: AutomationState) -> str:
    """사람 승인 결과 → 분기"""
    approved = state.get("human_approved")
    if approved is True:
        return "complete"
    elif approved is False:
        # 거절 시 어디서부터 재작업?
        feedback = state.get("human_feedback", "").lower()
        if "설계" in feedback or "구조" in feedback:
            return "architect"
        elif "코드" in feedback:
            return "code_gen"
        else:
            return "architect"  # 기본: 설계부터
    else:
        # None = 아직 대기 중 → 승인 노드에 머뭄
        return "human_approve"


def route_after_decompose(state: AutomationState) -> str:
    """분해 품질이 너무 낮으면 인터뷰로 복귀"""
    if state["decomposition_quality"] < 40:
        return "interview"
    return "ax_review"


# ── 그래프 조립 ───────────────────────────────────────────

def build_pipeline() -> StateGraph:
    """
    전체 멀티 에이전트 파이프라인 빌드.

    흐름:
    interview (loop) → decompose → ax_review → architect
    → tool_map → code_gen → verify (loop) → human_approve → complete

    루프:
    1. Interview Loop: 인터뷰 완료까지 자체 반복
    2. Design-Verify Loop: 검증 실패 시 architect 또는 code_gen 복귀 (최대 3회)
    3. Human Approval Loop: 거절 시 해당 단계로 복귀
    """
    graph = StateGraph(AutomationState)

    # ── 노드 등록 ──────────────────────────────────────────
    graph.add_node("interview",     interview_node)
    graph.add_node("decompose",     decompose_node)
    graph.add_node("ax_review",     ax_review_node)
    graph.add_node("architect",     architect_node)
    graph.add_node("tool_map",      tool_mapper_node)
    graph.add_node("code_gen",      code_gen_node)
    graph.add_node("verify",        verifier_node)
    graph.add_node("human_approve", human_approval_node)
    graph.add_node("complete",      complete_node)
    graph.add_node("failed",        failed_node)

    # ── 시작 노드 ──────────────────────────────────────────
    graph.set_entry_point("interview")

    # ── 엣지 연결 ──────────────────────────────────────────

    # 1. Interview Loop
    graph.add_conditional_edges(
        "interview",
        route_after_interview,
        {"interview": "interview", "decompose": "decompose"},
    )

    # 2. Decompose → 품질 기반 분기
    graph.add_conditional_edges(
        "decompose",
        route_after_decompose,
        {"interview": "interview", "ax_review": "ax_review"},
    )

    # 3. 선형 구간: AX Review → Architect → Tool Map → Code Gen
    graph.add_edge("ax_review", "architect")
    graph.add_edge("architect", "tool_map")
    graph.add_edge("tool_map",  "code_gen")
    graph.add_edge("code_gen",  "verify")

    # 4. Verify Loop (핵심 루프)
    graph.add_conditional_edges(
        "verify",
        route_after_verify,
        {
            "human_approve": "human_approve",
            "architect":     "architect",
            "code_gen":      "code_gen",
            "failed":        "failed",
        },
    )

    # 5. Human Approval Loop
    graph.add_conditional_edges(
        "human_approve",
        route_after_human_approve,
        {
            "complete":      "complete",
            "architect":     "architect",
            "code_gen":      "code_gen",
            "human_approve": "human_approve",
        },
    )

    # 6. 종료 노드
    graph.add_edge("complete", END)
    graph.add_edge("failed",   END)

    return graph


# ── 컴파일된 앱 (싱글톤) ─────────────────────────────────

_pipeline_app = None

def get_pipeline():
    """컴파일된 LangGraph 앱 반환 (싱글톤)"""
    global _pipeline_app
    if _pipeline_app is None:
        graph = build_pipeline()
        # MemorySaver: 인메모리 체크포인트 (프로덕션은 PostgresSaver)
        checkpointer = MemorySaver()
        _pipeline_app = graph.compile(
            checkpointer=checkpointer,
            interrupt_before=["human_approve"],  # 승인 전 자동 중단
        )
    return _pipeline_app
