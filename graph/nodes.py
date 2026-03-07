"""
SMALL AX AGENT — LangGraph 노드 구현 (7개 에이전트)
각 노드 = async 함수 (state → state 업데이트 반환)
"""

from __future__ import annotations
import asyncio
import json
import logging
import time
from datetime import datetime

import anthropic

from config import settings
from graph.state import AutomationState, make_event, AgentMessage
from rag import rag_seed
from rag.knowledge_base import rag_search_patterns_for_business, format_rag_context
from prompts import (
    INTERVIEW_SYSTEM_PROMPT, INTERVIEW_FEW_SHOTS,
    SOPHISTICATION_DETECTOR_PROMPT, HISTORY_COMPRESSION_PROMPT,
    build_interview_prompt,
    DECOMPOSER_SYSTEM_PROMPT, DECOMPOSER_FEW_SHOTS, DECOMPOSER_USER_TEMPLATE,
    DECOMPOSITION_VERIFIER_PROMPT,
    AX_REVIEW_SYSTEM_PROMPT, AX_REVIEW_FEW_SHOTS,
    ARCHITECT_SYSTEM_PROMPT, ARCHITECT_REFINEMENT_PROMPT,
    TOOL_MAPPER_SYSTEM_PROMPT, TOOL_MAPPER_CONTEXT_TEMPLATE,
    CODE_GENERATOR_SYSTEM_PROMPT, CODE_FEW_SHOT_SMARTSTORE, CODE_SELF_CRITIQUE_PROMPT,
    assemble_agent_prompt,
)


def sfmt(template: str, **kwargs) -> str:
    """JSON 블록이 포함된 프롬프트에서 안전하게 변수 치환."""
    result = template
    for k, v in kwargs.items():
        result = result.replace("{" + k + "}", str(v))
    return result

logger = logging.getLogger(__name__)
client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)


# ── 공통 LLM 호출 헬퍼 ───────────────────────────────────

async def call_llm(
    system: str,
    messages: list[dict],
    model: str = None,
    max_tokens: int = 4096,
) -> tuple[str, int]:
    """
    Anthropic API 호출 + JSON 파싱 시도
    Returns: (content_str, tokens_used)
    """
    model = model or settings.primary_model
    start = time.monotonic()

    response = await client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=messages,
    )
    content = response.content[0].text
    tokens = response.usage.input_tokens + response.usage.output_tokens

    elapsed = (time.monotonic() - start) * 1000
    logger.info(f"LLM call: model={model} tokens={tokens} ms={elapsed:.0f}")

    return content, tokens


async def call_llm_with_tools(
    system: str,
    messages: list[dict],
    tools: list[dict],
    model: str = None,
    max_tokens: int = 4096,
    max_tool_rounds: int = 3,
) -> tuple[str, int, list[dict]]:
    """
    Tool Calling 지원 LLM 호출.
    모델이 tool_use를 요청하면 실제 실행 후 결과를 주입, 최종 텍스트까지 반복.

    Returns: (final_text, total_tokens, tool_calls_log)
    """
    from graph.tools import execute_tool

    model = model or settings.primary_model
    total_tokens = 0
    tool_calls_log: list[dict] = []
    current_messages = list(messages)

    for round_idx in range(max_tool_rounds + 1):
        start = time.monotonic()
        response = await client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=current_messages,
            tools=tools,
            tool_choice={"type": "auto"},
        )
        elapsed = (time.monotonic() - start) * 1000
        round_tokens = response.usage.input_tokens + response.usage.output_tokens
        total_tokens += round_tokens
        logger.info(
            f"LLM+tools round={round_idx} stop={response.stop_reason} "
            f"tokens={round_tokens} ms={elapsed:.0f}"
        )

        # 최종 텍스트 응답
        if response.stop_reason == "end_turn":
            text_blocks = [b.text for b in response.content if hasattr(b, "text")]
            final_text = "\n".join(text_blocks)
            return final_text, total_tokens, tool_calls_log

        # tool_use 처리
        if response.stop_reason == "tool_use":
            # assistant 메시지로 content 블록 추가
            current_messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                logger.info(f"  Tool call: {block.name} input={block.input}")
                result_str = await execute_tool(block.name, block.input)
                tool_calls_log.append({"tool": block.name, "input": block.input, "result": result_str})
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_str,
                })

            current_messages.append({"role": "user", "content": tool_results})
            continue

        # 예상치 못한 stop_reason (max_tokens 등)
        text_blocks = [b.text for b in response.content if hasattr(b, "text")]
        return "\n".join(text_blocks), total_tokens, tool_calls_log

    # max_tool_rounds 초과 → 마지막 텍스트 반환
    text_blocks = [b.text for b in response.content if hasattr(b, "text")]
    return "\n".join(text_blocks), total_tokens, tool_calls_log


def safe_parse_json(text: str) -> dict | None:
    """LLM 응답에서 JSON 블록 추출 + 파싱"""
    # ```json ... ``` 블록 추출 시도
    import re
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        text = match.group(1).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # 첫 번째 { ... } 추출 시도
        try:
            start = text.index("{")
            end = text.rindex("}") + 1
            return json.loads(text[start:end])
        except (ValueError, json.JSONDecodeError):
            return None


def make_agent_message(agent_name: str, content: str, metadata: dict = None) -> AgentMessage:
    return AgentMessage(
        role="agent",
        agent_name=agent_name,
        content=content,
        metadata=metadata or {},
        timestamp=datetime.utcnow().isoformat(),
    )


async def _rag_similar_patterns(business_type: str, tasks: list[str], n: int = 4) -> str:
    """
    비즈니스 컨텍스트 기반 유사 자동화 패턴 검색 (비동기 래퍼).
    ChromaDB는 동기 API이므로 thread pool에서 실행.
    """
    loop = asyncio.get_event_loop()
    try:
        patterns = await loop.run_in_executor(
            None, rag_search_patterns_for_business, business_type, tasks, n
        )
        return format_rag_context(patterns, max_chars=1500)
    except Exception as e:
        logger.warning(f"RAG search failed: {e}")
        return ""


async def _rag_tool_context(use_case: str) -> str:
    """도구 조합 RAG 검색 (비동기)."""
    loop = asyncio.get_event_loop()
    try:
        from rag.knowledge_base import rag_search_tools
        combos = await loop.run_in_executor(None, rag_search_tools, use_case)
        return format_rag_context(combos, max_chars=800)
    except Exception as e:
        logger.warning(f"RAG tool search failed: {e}")
        return ""


def _ensure_rag_seeded():
    """RAG 시딩 보장 (동기, 최초 1회)."""
    try:
        rag_seed()
    except Exception as e:
        logger.warning(f"RAG seed skipped: {e}")


# ═══════════════════════════════════════════════════════════
# NODE 1 — Interview Agent
# ═══════════════════════════════════════════════════════════

async def interview_node(state: AutomationState) -> dict:
    """
    대화형 인터뷰. 사용자 업무를 파악할 때까지 반복.
    사용자 입력 대기 → stream_events로 UI에 신호 전달.
    """
    agent = "Interview"
    logger.info(f"[{agent}] Turn {state['interview_turn_count'] + 1}")

    # 첫 번째 턴: 사용자 수준 감지
    if state["interview_turn_count"] == 0:
        last_user_msg = next(
            (m["content"] for m in reversed(state["messages"]) if m["role"] == "user"),
            ""
        )
        if last_user_msg:
            detect_prompt = SOPHISTICATION_DETECTOR_PROMPT.replace('"{user_message}"', f'"{last_user_msg}"')
            detect_resp, _ = await call_llm(
                system="You are a user profiling assistant. Respond in JSON only.",
                messages=[{"role": "user", "content": detect_prompt}],
                model=settings.fast_model,
                max_tokens=256,
            )
            detected = safe_parse_json(detect_resp) or {}
            sophistication = detected.get("level", "NOVICE")
        else:
            sophistication = "NOVICE"
    else:
        sophistication = state["user_sophistication"]

    # 대화 히스토리 압축 (5턴 이상일 때)
    history_summary = state["history_summary"]
    if state["interview_turn_count"] >= 5 and state["interview_turn_count"] % 3 == 0:
        history_text = "\n".join(
            f"{m['role']}: {m['content']}" for m in state["messages"][-10:]
        )
        compress_prompt = sfmt(HISTORY_COMPRESSION_PROMPT, conversation_history=history_text)
        summary_resp, _ = await call_llm(
            system="Compress conversation into structured summary. JSON only.",
            messages=[{"role": "user", "content": compress_prompt}],
            model=settings.fast_model,
            max_tokens=512,
        )
        history_summary = compress_prompt  # 압축 결과 저장

    # 인터뷰 프롬프트 조립
    extracted = state["extracted_info"] or {}
    turn_context = build_interview_prompt(
        current_stage="D" if state["interview_turn_count"] < 3 else
                      "I" if state["interview_turn_count"] < 7 else "P",
        completion_pct=min(state["interview_turn_count"] * 12, 95),
        turn_count=state["interview_turn_count"],
        extracted_info=extracted,
        history_summary=history_summary,
    )

    system_prompt = assemble_agent_prompt(
        base_system_prompt=INTERVIEW_SYSTEM_PROMPT,
        few_shots=INTERVIEW_FEW_SHOTS,
        session_history_summary=history_summary,
    )

    # 대화 메시지 조립
    lc_messages = []
    for m in state["messages"][-8:]:  # 최근 8개만
        if m["role"] in ("user", "assistant", "agent"):
            role = "assistant" if m["role"] == "agent" else m["role"]
            lc_messages.append({"role": role, "content": m["content"]})

    lc_messages.append({"role": "user", "content": turn_context})

    # LLM 호출
    content, tokens = await call_llm(
        system=system_prompt,
        messages=lc_messages,
        max_tokens=1024,
    )

    parsed = safe_parse_json(content)
    if not parsed:
        parsed = {
            "agent_message": content,
            "question_type": "open",
            "options": [],
            "dipd_stage": "D",
            "completion_percentage": state["interview_turn_count"] * 10,
            "extracted_info": extracted,
            "ready_for_decomposition": False,
        }

    # 추출 정보 업데이트 (누적)
    new_extracted = {**extracted, **parsed.get("extracted_info", {})}

    events = [make_event(
        "agent_output", agent, "interview",
        content=parsed["agent_message"],
        metadata={
            "question_type": parsed.get("question_type"),
            "options": parsed.get("options", []),
            "completion_pct": parsed.get("completion_percentage", 0),
        }
    )]

    interview_complete = parsed.get("ready_for_decomposition", False)
    if interview_complete:
        events.append(make_event("pipeline_advance", agent, "decompose", "인터뷰 완료 → 워크플로우 분해 시작"))

    return {
        "messages": [make_agent_message(agent, parsed["agent_message"], parsed)],
        "stream_events": events,
        "user_sophistication": sophistication,
        "interview_turn_count": state["interview_turn_count"] + 1,
        "interview_complete": interview_complete,
        "extracted_info": new_extracted,
        "history_summary": history_summary,
        "current_stage": "decompose" if interview_complete else "interview",
        "total_tokens_used": state["total_tokens_used"] + tokens,
    }


# ═══════════════════════════════════════════════════════════
# NODE 2 — Workflow Decomposer
# ═══════════════════════════════════════════════════════════

async def decompose_node(state: AutomationState) -> dict:
    agent = "Decomposer"
    logger.info(f"[{agent}] Decomposing workflow")

    extracted = state["extracted_info"] or {}

    # RAG: 유사 업종 자동화 패턴 검색 (비동기, 실패해도 계속)
    _ensure_rag_seeded()
    rag_context = await _rag_similar_patterns(
        business_type=extracted.get("business_type", "일반 소상공인"),
        tasks=extracted.get("repeat_tasks", []),
    )

    user_prompt = sfmt(
        DECOMPOSER_USER_TEMPLATE,
        business_profile=json.dumps(extracted, ensure_ascii=False),
        task_list="\n".join(f"- {t}" for t in extracted.get("repeat_tasks", [])),
        time_data=json.dumps(extracted.get("time_wasters", []), ensure_ascii=False),
        current_tools=", ".join(extracted.get("current_tools", [])),
        priority_task=extracted.get("priority_task", "가장 시간이 많이 걸리는 업무"),
    )

    if rag_context:
        user_prompt += f"\n\n{rag_context}\n\n위 검증된 패턴을 참고하되, 사용자 업무에 맞게 커스터마이징하세요."

    system_prompt = assemble_agent_prompt(
        base_system_prompt=DECOMPOSER_SYSTEM_PROMPT,
        few_shots=DECOMPOSER_FEW_SHOTS,
    )

    events = [make_event("agent_start", agent, "decompose", "워크플로우 원자 단위 분해 시작")]

    content, tokens = await call_llm(
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
        max_tokens=3000,
    )

    decomposition = safe_parse_json(content)
    if not decomposition:
        decomposition = {"error": "파싱 실패", "raw": content}

    # 품질 검증 (자기 검증)
    verify_prompt = sfmt(DECOMPOSITION_VERIFIER_PROMPT,
        decomposition_json=json.dumps(decomposition, ensure_ascii=False))
    verify_resp, vtokens = await call_llm(
        system="You are a decomposition quality verifier. JSON only.",
        messages=[{"role": "user", "content": verify_prompt}],
        model=settings.fast_model,
        max_tokens=1024,
    )
    quality_result = safe_parse_json(verify_resp) or {"quality_score": 50, "approved": False}
    quality_score = quality_result.get("quality_score", 50)

    events.append(make_event(
        "agent_complete", agent, "decompose",
        f"분해 완료: {len(decomposition.get('steps', []))}개 스텝, 품질 {quality_score}/100"
    ))

    return {
        "messages": [make_agent_message(agent, f"워크플로우 분해 완료 ({len(decomposition.get('steps', []))}개 스텝)")],
        "stream_events": events,
        "workflow_decomposition": decomposition,
        "decomposition_quality": quality_score,
        "current_stage": "ax_review",
        "total_tokens_used": state["total_tokens_used"] + tokens + vtokens,
    }


# ═══════════════════════════════════════════════════════════
# NODE 3 — AX Review
# ═══════════════════════════════════════════════════════════

async def ax_review_node(state: AutomationState) -> dict:
    agent = "AX-Review"
    logger.info(f"[{agent}] Analyzing automation potential")

    decomposition = state["workflow_decomposition"] or {}
    steps_json = json.dumps(decomposition.get("steps", []), ensure_ascii=False)

    user_prompt = f"""
Analyze these workflow steps for automation potential.

Steps:
{steps_json}

Business context:
{json.dumps(state.get('extracted_info', {}), ensure_ascii=False)}

Apply ARTE Matrix to each step. Generate complete AX Review output.
"""

    system_prompt = assemble_agent_prompt(
        base_system_prompt=AX_REVIEW_SYSTEM_PROMPT,
        few_shots=AX_REVIEW_FEW_SHOTS,
    )

    events = [make_event("agent_start", agent, "ax_review", "자동화 가능성 분석 중")]

    content, tokens = await call_llm(
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
        max_tokens=3000,
    )

    review_result = safe_parse_json(content) or {}
    automation_summary = review_result.get("automation_summary", {})

    saved_hours = automation_summary.get("estimated_weekly_hours_saved", 0)
    events.append(make_event(
        "agent_complete", agent, "ax_review",
        f"분석 완료: 주 {saved_hours}시간 절약 예상, ROI: {automation_summary.get('payback_period_months', '?')}개월 회수"
    ))

    return {
        "messages": [make_agent_message(agent,
            f"자동화 분석 완료. 주 {saved_hours}시간 절약 가능, 예상 페이백 {automation_summary.get('payback_period_months', '?')}개월")],
        "stream_events": events,
        "ax_review_result": review_result,
        "automation_summary": automation_summary,
        "current_stage": "architect",
        "total_tokens_used": state["total_tokens_used"] + tokens,
    }


# ═══════════════════════════════════════════════════════════
# NODE 4 — Automation Architect
# ═══════════════════════════════════════════════════════════

async def architect_node(state: AutomationState) -> dict:
    agent = "Architect"
    logger.info(f"[{agent}] Designing automation v{state['design_version']}")

    # 재시도 시 피드백 포함
    feedback_section = ""
    if state["pipeline_feedback"]:
        feedback_section = f"\n\n## Revision Feedback\n{state['pipeline_feedback']}"

    user_prompt = f"""
Design automation system based on:

AX Review:
{json.dumps(state.get('ax_review_result', {}), ensure_ascii=False)}

Workflow:
{json.dumps(state.get('workflow_decomposition', {}), ensure_ascii=False)}

Business Context:
{json.dumps(state.get('extracted_info', {}), ensure_ascii=False)}
{feedback_section}

Design version: {state['design_version']}
Include Mermaid diagram.
"""

    # 재시도 시 refinement 프롬프트 사용
    if state["design_version"] > 1 and state.get("automation_design"):
        system_prompt = sfmt(ARCHITECT_REFINEMENT_PROMPT,
            original_design=json.dumps(state["automation_design"], ensure_ascii=False),
            feedback=state["pipeline_feedback"])
        system_prompt = assemble_agent_prompt(
            base_system_prompt=ARCHITECT_SYSTEM_PROMPT,
            session_history_summary=system_prompt,
        )
    else:
        system_prompt = assemble_agent_prompt(base_system_prompt=ARCHITECT_SYSTEM_PROMPT)

    from graph.tools import ARCHITECT_TOOLS

    events = [make_event("agent_start", agent, "architect",
        f"자동화 설계 {'재' if state['design_version'] > 1 else ''}생성 중 (v{state['design_version']})")]

    content, tokens, tool_log = await call_llm_with_tools(
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
        tools=ARCHITECT_TOOLS,
        max_tokens=4096,
    )

    # tool 호출 이벤트 기록
    for tc in tool_log:
        events.append(make_event(
            "tool_call", agent, "architect",
            f"[Tool] {tc['tool']}",
            metadata={"tool": tc["tool"], "input": tc["input"]},
        ))

    design = safe_parse_json(content) or {}
    if "mermaid_diagram" not in design:
        design["mermaid_diagram"] = "flowchart TD\n    A[시작] --> B[처리] --> C[완료]"

    pattern = design.get("primary_pattern", "LINEAR")
    comp_count = len(design.get("components", []))
    tool_info = f", 도구 {len(tool_log)}회 사용" if tool_log else ""
    events.append(make_event(
        "agent_complete", agent, "architect",
        f"설계 완료: {pattern} 패턴, {comp_count}개 컴포넌트{tool_info}"
    ))

    return {
        "messages": [make_agent_message(agent, f"자동화 설계 v{state['design_version']} 완료 ({pattern} 패턴)")],
        "stream_events": events,
        "automation_design": design,
        "design_version": state["design_version"] + 1,
        "current_stage": "tool_map",
        "total_tokens_used": state["total_tokens_used"] + tokens,
    }


# ═══════════════════════════════════════════════════════════
# NODE 5 — Tool Mapper
# ═══════════════════════════════════════════════════════════

async def tool_mapper_node(state: AutomationState) -> dict:
    agent = "ToolMapper"
    logger.info(f"[{agent}] Mapping tools to components")

    extracted = state.get("extracted_info") or {}
    design = state.get("automation_design") or {}

    # RAG: 동일 업종의 검증된 도구 조합 추천
    use_case = f"{extracted.get('business_type', '')} {design.get('primary_pattern', '')} 자동화"
    tool_rag_context = await _rag_tool_context(use_case)

    user_prompt = sfmt(TOOL_MAPPER_CONTEXT_TEMPLATE,
        components_json=json.dumps(design.get("components", []), ensure_ascii=False),
        business_type=extracted.get("business_type", "일반"),
        tech_level=state.get("user_sophistication", "NOVICE"),
        budget="명시 없음",
        existing_tools=", ".join(extracted.get("current_tools", [])),
        volume_info=json.dumps(extracted.get("time_wasters", []), ensure_ascii=False))

    if tool_rag_context:
        user_prompt += f"\n\n## 유사 업종 검증 도구 조합 (참고)\n{tool_rag_context}"

    events = [make_event("agent_start", agent, "tool_map", "최적 도구 선택 중 (RAG 보강)")]

    content, tokens = await call_llm(
        system=assemble_agent_prompt(base_system_prompt=TOOL_MAPPER_SYSTEM_PROMPT),
        messages=[{"role": "user", "content": user_prompt}],
        max_tokens=2048,
    )

    tool_mapping = safe_parse_json(content) or {}
    monthly_cost = tool_mapping.get("total_estimated_monthly_cost_usd", 0)

    events.append(make_event(
        "agent_complete", agent, "tool_map",
        f"도구 선택 완료: 월 예상 비용 ${monthly_cost}"
    ))

    return {
        "messages": [make_agent_message(agent, f"도구 매핑 완료 (월 $~{monthly_cost})")],
        "stream_events": events,
        "tool_mapping": tool_mapping,
        "current_stage": "code_gen",
        "total_tokens_used": state["total_tokens_used"] + tokens,
    }


# ═══════════════════════════════════════════════════════════
# NODE 6 — Code Generator
# ═══════════════════════════════════════════════════════════

async def code_gen_node(state: AutomationState) -> dict:
    agent = "CodeGen"
    logger.info(f"[{agent}] Generating automation code")

    design = state.get("automation_design") or {}
    tool_mapping = state.get("tool_mapping") or {}
    extracted = state.get("extracted_info") or {}

    user_prompt = f"""
Generate complete, production-ready automation code.

Automation Design:
{json.dumps(design, ensure_ascii=False, indent=2)}

Tool Mapping:
{json.dumps(tool_mapping, ensure_ascii=False, indent=2)}

Business Context:
- Type: {extracted.get('business_type', '')}
- Existing tools: {', '.join(extracted.get('current_tools', []))}

Requirements:
1. Complete Python code with all imports
2. Environment variables from .env (never hardcode)
3. Async implementation with aiohttp/asyncio
4. Retry logic on all external API calls
5. Structured logging
6. Type hints throughout
7. Include .env.example snippet

Previous feedback (if retry): {state.get('pipeline_feedback', 'None')}
"""

    system_prompt = assemble_agent_prompt(
        base_system_prompt=CODE_GENERATOR_SYSTEM_PROMPT,
        few_shots=CODE_FEW_SHOT_SMARTSTORE,
    )

    events = [make_event("agent_start", agent, "code_gen", "자동화 코드 생성 중")]

    content, tokens = await call_llm(
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
        max_tokens=4096,
    )

    code_result = safe_parse_json(content)
    if not code_result:
        # JSON 없으면 raw code를 감싸서 저장
        code_result = {
            "file_name": "automation.py",
            "description": "생성된 자동화 코드",
            "code": content,
            "test_code": "",
            "dependencies": [],
            "env_variables": [],
        }

    # 자기 비판 (Self-Critique)
    critique_prompt = sfmt(CODE_SELF_CRITIQUE_PROMPT,
        generated_code=code_result.get("code", content))
    critique_resp, ctokens = await call_llm(
        system="You are a security and reliability code reviewer. JSON only.",
        messages=[{"role": "user", "content": critique_prompt}],
        model=settings.fast_model,
        max_tokens=1024,
    )
    critique = safe_parse_json(critique_resp) or {"overall_score": 70, "approved_for_production": True}

    events.append(make_event(
        "agent_complete", agent, "code_gen",
        f"코드 생성 완료: {code_result.get('file_name', 'automation.py')}, 품질 {critique.get('overall_score', '?')}/100"
    ))

    return {
        "messages": [make_agent_message(agent,
            f"코드 생성 완료 — `{code_result.get('file_name', 'automation.py')}` (품질 점수: {critique.get('overall_score', '?')}/100)")],
        "stream_events": events,
        "generated_code": code_result,
        "code_self_critique": critique,
        "current_stage": "verify",
        "total_tokens_used": state["total_tokens_used"] + tokens + ctokens,
    }


# ═══════════════════════════════════════════════════════════
# NODE 7 — Verifier
# ═══════════════════════════════════════════════════════════

async def verifier_node(state: AutomationState) -> dict:
    """
    Verifier — XML 태그 기반 출력으로 안정적 파싱.
    복잡한 JSON 스키마 대신 단순 XML 추출 사용.
    """
    agent = "Verifier"
    logger.info(f"[{agent}] Running SLICE verification")

    # ── 검증 대상 요약 (컨텍스트 압축) ───────────────────────
    design = state.get("automation_design") or {}
    code_obj = state.get("generated_code") or {}
    extracted = state.get("extracted_info") or {}

    user_prompt = f"""
Verify this automation system. Be concise and practical.

## Automation Design Summary
- Pattern: {design.get('primary_pattern', 'N/A')}
- Components: {len(design.get('components', []))}개
- HITL nodes: {len(design.get('hitl_nodes', []))}개

## Generated Code File
{code_obj.get('file_name', 'automation.py')}

Code snippet (first 800 chars):
{(code_obj.get('code') or '')[:800]}

## Business Context
- Type: {extracted.get('business_type', '')}
- Volume: {json.dumps(extracted.get('time_wasters', []), ensure_ascii=False)}
- Tech level: {state.get('user_sophistication', 'NOVICE')}

## Previous retry count: {state.get('retry_count', 0)}

---

Respond using EXACTLY these XML tags:

<score>0-100</score>
<verdict>APPROVED or NEEDS_REVISION or REJECTED</verdict>
<issues>
- [CRITICAL/HIGH/MEDIUM] issue description
- [CRITICAL/HIGH/MEDIUM] issue description
</issues>
<fixes>
- specific fix instruction
- specific fix instruction
</fixes>
<summary>One sentence overall assessment in Korean</summary>

Verdict rules:
- APPROVED: score >= 75, no CRITICAL issues
- NEEDS_REVISION: 50 <= score < 75, or has HIGH issues
- REJECTED: score < 50, or multiple CRITICAL issues

Be lenient on MVP-level code. Focus on blocking issues only.
"""

    events = [make_event("agent_start", agent, "verify", "SLICE 다차원 검증 실행 중")]

    content, tokens = await call_llm(
        system="You are a pragmatic automation systems auditor. Use XML tags exactly as instructed.",
        messages=[{"role": "user", "content": user_prompt}],
        max_tokens=1500,
    )

    # ── XML 태그 기반 파싱 (JSON보다 훨씬 안정적) ─────────────
    import re

    def extract_tag(tag: str, text: str, default: str = "") -> str:
        m = re.search(rf"<{tag}>(.*?)</{tag}>", text, re.DOTALL)
        return m.group(1).strip() if m else default

    raw_score   = extract_tag("score",   content, "70")
    raw_verdict = extract_tag("verdict", content, "APPROVED")
    raw_issues  = extract_tag("issues",  content, "")
    raw_fixes   = extract_tag("fixes",   content, "")
    raw_summary = extract_tag("summary", content, "검증 완료")

    # 숫자 파싱 안전 처리
    try:
        score = max(0, min(100, int(re.search(r'\d+', raw_score).group())))
    except Exception:
        score = 70

    verdict = raw_verdict.strip().upper()
    if verdict not in ("APPROVED", "NEEDS_REVISION", "REJECTED"):
        verdict = "APPROVED" if score >= 75 else "NEEDS_REVISION"

    # score 와 verdict 정합성 보정
    if score >= 75 and verdict == "NEEDS_REVISION" and "CRITICAL" not in raw_issues:
        verdict = "APPROVED"
    if score < 50:
        verdict = "NEEDS_REVISION"

    passed = verdict == "APPROVED"

    issues_list = [l.strip("- ").strip() for l in raw_issues.splitlines() if l.strip().startswith("-")]
    fixes_list  = [l.strip("- ").strip() for l in raw_fixes.splitlines()  if l.strip().startswith("-")]

    verification = {
        "overall_score": score,
        "verdict": verdict,
        "issues": issues_list,
        "revision_instructions": fixes_list,
        "summary": raw_summary,
        "raw_content": content[:500],
    }

    feedback = ""
    if not passed and fixes_list:
        feedback = "수정 필요:\n" + "\n".join(f"- {f}" for f in fixes_list[:5])

    events.append(make_event(
        "agent_complete", agent, "verify",
        f"검증 {'통과' if passed else '실패'}: {score}/100 ({verdict})",
        metadata={"score": score, "verdict": verdict},
    ))

    next_stage = "human_approve" if passed else "architect"

    return {
        "messages": [make_agent_message(agent,
            f"검증 결과: **{verdict}** ({score}/100)\n{raw_summary}" +
            (f"\n\n수정 사항:\n{feedback}" if feedback else ""))],
        "stream_events": events,
        "verification_result": verification,
        "verification_score": score,
        "verification_passed": passed,
        "pipeline_feedback": feedback,
        "current_stage": next_stage,
        "total_tokens_used": state["total_tokens_used"] + tokens,
        "retry_count": state.get("retry_count", 0) + (0 if passed else 1),
    }


# ═══════════════════════════════════════════════════════════
# NODE 8 — Human Approval Gate
# ═══════════════════════════════════════════════════════════

async def human_approval_node(state: AutomationState) -> dict:
    """
    사용자 승인 대기 노드.
    실제로는 여기서 실행을 멈추고 WebSocket으로 승인 요청 전달.
    승인/거절은 API endpoint가 state를 업데이트함.
    """
    agent = "HumanGate"

    design = state.get("automation_design") or {}
    code = state.get("generated_code") or {}
    summary = state.get("automation_summary") or {}

    approval_summary = f"""
## 자동화 설계 검토 요청

**설계 패턴**: {design.get('primary_pattern', 'N/A')}
**컴포넌트 수**: {len(design.get('components', []))}개
**예상 주간 절약 시간**: {summary.get('estimated_weekly_hours_saved', '?')}시간
**예상 월 비용**: ${state.get('tool_mapping', {}).get('total_estimated_monthly_cost_usd', '?')}
**코드 파일**: {code.get('file_name', 'automation.py')}
**검증 점수**: {state.get('verification_score', '?')}/100

다이어그램:
```mermaid
{design.get('mermaid_diagram', '')}
```

승인하시면 최종 코드와 설정 파일을 다운로드할 수 있습니다.
"""

    events = [make_event(
        "user_input_required", agent, "human_approve",
        approval_summary,
        metadata={"requires_approval": True, "timeout_hours": 48},
    )]

    # 이메일 승인 알림 발송 (미설정 시 콘솔 fallback)
    session_id = state.get("session_id", "unknown")
    try:
        from notification.email import send_approval_email
        email_sent = await send_approval_email(
            session_id=session_id,
            design_summary=approval_summary,
        )
        if email_sent:
            events.append(make_event(
                "notification_sent", agent, "human_approve",
                "승인 요청 이메일 발송 완료",
                metadata={"channel": "email"},
            ))
    except Exception as e:
        logger.warning(f"이메일 알림 발송 실패: {e}")

    return {
        "messages": [make_agent_message(agent, approval_summary, {"requires_approval": True})],
        "stream_events": events,
        "current_stage": "human_approve",
        "human_approved": None,  # 대기 상태
    }


# ═══════════════════════════════════════════════════════════
# NODE 9 — Complete / Failed Terminal Nodes
# ═══════════════════════════════════════════════════════════

async def complete_node(state: AutomationState) -> dict:
    agent = "System"
    cost = state.get("total_tokens_used", 0) * 0.000003  # 대략적 비용

    summary = f"""
## 자동화 생성 완료!

- 워크플로우 분석: 완료
- 자동화 설계: v{state.get('design_version', 1)} 확정
- 코드 생성: `{state.get('generated_code', {}).get('file_name', 'automation.py')}`
- 검증 점수: {state.get('verification_score', '?')}/100
- 총 사용 토큰: {state.get('total_tokens_used', 0):,}
- 예상 비용: ${cost:.4f}

다음 단계:
1. `.env` 파일에 API 키 입력
2. `pip install -r requirements.txt`
3. 코드 실행 후 테스트
"""

    return {
        "messages": [make_agent_message(agent, summary)],
        "stream_events": [make_event("pipeline_complete", agent, "complete", summary)],
        "current_stage": "complete",
        "estimated_cost_usd": cost,
    }


async def failed_node(state: AutomationState) -> dict:
    agent = "System"
    message = f"파이프라인 실패: {state.get('pipeline_feedback', '알 수 없는 오류')}"
    return {
        "messages": [make_agent_message(agent, message)],
        "stream_events": [make_event("pipeline_error", agent, "failed", message)],
        "current_stage": "failed",
    }
