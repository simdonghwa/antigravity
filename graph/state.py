"""
SMALL AX AGENT — LangGraph 파이프라인 상태 정의
TypedDict 기반 전체 상태 스키마 + 이벤트 스트림 타입
"""

from __future__ import annotations
from typing import TypedDict, Annotated, Any, Literal
from datetime import datetime
import operator


# ── 파이프라인 스테이지 ────────────────────────────────────
PipelineStageType = Literal[
    "interview", "decompose", "ax_review",
    "architect", "tool_map", "code_gen",
    "verify", "human_approve", "complete", "failed"
]

# ── 메시지 타입 (LangGraph 내부 + WebSocket 스트림) ────────
class AgentMessage(TypedDict):
    role:       str   # user | assistant | agent | system
    agent_name: str   # Interview | Decomposer | ...
    content:    str
    metadata:   dict
    timestamp:  str


# ── 업무 분석 결과 ─────────────────────────────────────────
class ExtractedBusinessInfo(TypedDict):
    business_type:   str
    team_size:       int | None
    pain_points:     list[str]
    current_tools:   list[str]
    repeat_tasks:    list[str]
    time_wasters:    list[dict]   # [{task, daily_hours}]
    priority_task:   str


class WorkflowStep(TypedDict):
    step_id:              str
    step_name:            str
    description:          str
    actor:                str
    sipoc:                dict
    trigger:              str
    trigger_detail:       str
    estimated_time_minutes: int
    frequency_per_week:   int
    aps_score:            int
    aps_reasoning:        str
    dependencies:         list[str]
    exception_cases:      list[str]


class AutomationDesign(TypedDict):
    design_name:          str
    design_version:       str
    primary_pattern:      str
    architecture_overview: str
    components:           list[dict]
    connections:          list[dict]
    hitl_nodes:           list[dict]
    mermaid_diagram:      str
    sla:                  dict


# ── 전체 파이프라인 상태 (LangGraph StateGraph 키) ─────────
class AutomationState(TypedDict):

    # ── 세션 메타 ──────────────────────────────────────────
    session_id:      str
    project_id:      str
    user_id:         str

    # ── 대화 히스토리 (append-only reducer) ───────────────
    messages: Annotated[list[AgentMessage], operator.add]

    # ── 현재 스테이지 ──────────────────────────────────────
    current_stage:   PipelineStageType
    retry_count:     int
    pipeline_feedback: str   # 이전 단계 피드백 (재시도 시 전달)

    # ── 인터뷰 결과 ────────────────────────────────────────
    user_sophistication: str                  # NOVICE | INTERMEDIATE | EXPERT
    interview_complete:  bool
    extracted_info:      ExtractedBusinessInfo | None
    interview_turn_count: int
    history_summary:     str                  # 압축 요약

    # ── 워크플로우 분해 결과 ───────────────────────────────
    workflow_decomposition: dict | None
    decomposition_quality:  int               # 0-100

    # ── AX 리뷰 결과 ──────────────────────────────────────
    ax_review_result:  dict | None
    automation_summary: dict | None

    # ── 자동화 설계 결과 ───────────────────────────────────
    automation_design: AutomationDesign | None
    design_version:    int

    # ── 툴 매핑 결과 ──────────────────────────────────────
    tool_mapping:      dict | None

    # ── 코드 생성 결과 ────────────────────────────────────
    generated_code:    dict | None            # {file_name, code, test_code, ...}
    code_self_critique: dict | None

    # ── 검증 결과 ─────────────────────────────────────────
    verification_result: dict | None
    verification_score:  int
    verification_passed: bool

    # ── Human-in-the-Loop ─────────────────────────────────
    human_approved:    bool | None            # None=대기, True=승인, False=거절
    human_feedback:    str

    # ── 스트림 이벤트 큐 (WebSocket 전송용) ──────────────
    # append-only: 에이전트 활동을 실시간으로 프론트에 전달
    stream_events: Annotated[list[dict], operator.add]

    # ── 비용 추적 ─────────────────────────────────────────
    total_tokens_used: int
    estimated_cost_usd: float


# ── 스트림 이벤트 타입 ────────────────────────────────────
class StreamEvent(TypedDict):
    event_type: Literal[
        "agent_start",      # 에이전트 시작
        "agent_thinking",   # CoT 진행 중
        "agent_output",     # 에이전트 출력
        "agent_complete",   # 에이전트 완료
        "user_input_required",  # 사용자 입력 대기
        "pipeline_advance", # 다음 스테이지 이동
        "pipeline_retry",   # 재시도
        "pipeline_complete", # 전체 완료
        "pipeline_error",   # 오류
    ]
    agent_name:  str
    stage:       str
    content:     Any
    timestamp:   str
    metadata:    dict


def make_event(
    event_type: str,
    agent_name: str,
    stage: str,
    content: Any,
    metadata: dict = None
) -> StreamEvent:
    return StreamEvent(
        event_type=event_type,
        agent_name=agent_name,
        stage=stage,
        content=content,
        timestamp=datetime.utcnow().isoformat(),
        metadata=metadata or {},
    )


def initial_state(session_id: str, project_id: str, user_id: str = "default") -> AutomationState:
    """새 파이프라인 초기 상태 생성"""
    return AutomationState(
        session_id=session_id,
        project_id=project_id,
        user_id=user_id,
        messages=[],
        current_stage="interview",
        retry_count=0,
        pipeline_feedback="",
        user_sophistication="NOVICE",
        interview_complete=False,
        extracted_info=None,
        interview_turn_count=0,
        history_summary="",
        workflow_decomposition=None,
        decomposition_quality=0,
        ax_review_result=None,
        automation_summary=None,
        automation_design=None,
        design_version=1,
        tool_mapping=None,
        generated_code=None,
        code_self_critique=None,
        verification_result=None,
        verification_score=0,
        verification_passed=False,
        human_approved=None,
        human_feedback="",
        stream_events=[],
        total_tokens_used=0,
        estimated_cost_usd=0.0,
    )
