"""
n8n 워크플로우 변환기
automation_design 아티팩트 → n8n JSON 포맷

n8n 워크플로우 구조:
{
  "name": "...",
  "nodes": [NodeObject, ...],
  "connections": { "NodeName": { "main": [[{node, type, index}]] } },
  "active": false,
  "settings": { "executionOrder": "v1" }
}
"""

from __future__ import annotations
import json
import uuid
from typing import Any

# ── n8n 노드 타입 매핑 ────────────────────────────────────────

# 도구명 → n8n 노드 타입
TOOL_TO_N8N: dict[str, dict] = {
    # 스케줄 트리거
    "scheduler": {
        "type": "n8n-nodes-base.scheduleTrigger",
        "category": "trigger",
        "parameters": {"rule": {"interval": [{"field": "hours", "hoursInterval": 1}]}},
    },
    "webhook": {
        "type": "n8n-nodes-base.webhook",
        "category": "trigger",
        "parameters": {"path": "automation-webhook", "responseMode": "onReceived"},
    },
    # HTTP / API
    "http": {
        "type": "n8n-nodes-base.httpRequest",
        "category": "action",
        "parameters": {"method": "GET", "url": "https://api.example.com/endpoint"},
    },
    "네이버 쇼핑 api": {
        "type": "n8n-nodes-base.httpRequest",
        "category": "action",
        "parameters": {"method": "GET", "url": "https://api.commerce.naver.com/external/v1/pay-order/seller/orders"},
    },
    "카카오 알림톡": {
        "type": "n8n-nodes-base.httpRequest",
        "category": "notify",
        "parameters": {
            "method": "POST",
            "url": "https://kapi.kakao.com/v1/api/talk/message/default/send",
            "sendHeaders": True,
            "headerParameters": {"parameters": [{"name": "Authorization", "value": "KakaoAK YOUR_API_KEY"}]},
        },
    },
    "슬랙": {
        "type": "n8n-nodes-base.slack",
        "category": "notify",
        "parameters": {"resource": "message", "operation": "post", "channel": "#automation"},
    },
    "슬랙 api": {
        "type": "n8n-nodes-base.slack",
        "category": "notify",
        "parameters": {"resource": "message", "operation": "post", "channel": "#automation"},
    },
    "gmail api": {
        "type": "n8n-nodes-base.gmail",
        "category": "notify",
        "parameters": {"resource": "message", "operation": "send", "toList": "owner@example.com"},
    },
    "이메일": {
        "type": "n8n-nodes-base.emailSend",
        "category": "notify",
        "parameters": {"toEmail": "owner@example.com", "subject": "자동화 알림"},
    },
    # 데이터베이스
    "sqlite": {
        "type": "n8n-nodes-base.executionData",
        "category": "data",
        "parameters": {},
    },
    "postgresql": {
        "type": "n8n-nodes-base.postgres",
        "category": "data",
        "parameters": {"operation": "executeQuery", "query": "SELECT * FROM table"},
    },
    "google sheets api": {
        "type": "n8n-nodes-base.googleSheets",
        "category": "data",
        "parameters": {"operation": "append", "spreadsheetId": "YOUR_SHEET_ID"},
    },
    # 로직
    "if": {
        "type": "n8n-nodes-base.if",
        "category": "logic",
        "parameters": {"conditions": {"number": [{"value1": "={{$json.score}}", "operation": "larger", "value2": 75}]}},
    },
    "function": {
        "type": "n8n-nodes-base.function",
        "category": "logic",
        "parameters": {"functionCode": "// 커스텀 로직\nreturn items;"},
    },
    "set": {
        "type": "n8n-nodes-base.set",
        "category": "logic",
        "parameters": {"values": {"string": [{"name": "status", "value": "processed"}]}},
    },
    # AI
    "claude api": {
        "type": "@n8n/n8n-nodes-langchain.lmChatAnthropic",
        "category": "ai",
        "parameters": {"model": "claude-haiku-4-5-20251001"},
    },
    "openai": {
        "type": "@n8n/n8n-nodes-langchain.openAi",
        "category": "ai",
        "parameters": {"resource": "chat", "model": "gpt-4o-mini"},
    },
}

# 패턴 타입 → 기본 트리거
PATTERN_TRIGGERS: dict[str, dict] = {
    "TRIGGER_ACTION": {
        "name": "Webhook Trigger",
        "type": "n8n-nodes-base.webhook",
        "parameters": {"path": "trigger", "responseMode": "onReceived"},
    },
    "LINEAR": {
        "name": "Schedule Trigger",
        "type": "n8n-nodes-base.scheduleTrigger",
        "parameters": {"rule": {"interval": [{"field": "hours", "hoursInterval": 1}]}},
    },
    "PIPELINE": {
        "name": "Schedule Trigger",
        "type": "n8n-nodes-base.scheduleTrigger",
        "parameters": {"rule": {"interval": [{"field": "days", "daysInterval": 1}]}},
    },
    "AGGREGATION": {
        "name": "Schedule Trigger",
        "type": "n8n-nodes-base.scheduleTrigger",
        "parameters": {"rule": {"interval": [{"field": "days", "daysInterval": 1}]}},
    },
    "APPROVAL": {
        "name": "Webhook Trigger",
        "type": "n8n-nodes-base.webhook",
        "parameters": {"path": "approval-request", "responseMode": "lastNode"},
    },
}


# ── 변환 메인 함수 ────────────────────────────────────────────

def design_to_n8n(
    automation_design: dict,
    tool_mapping: dict | None = None,
    workflow_name: str = "AX 자동화 워크플로우",
) -> dict:
    """
    automation_design + tool_mapping → n8n 워크플로우 JSON

    Args:
        automation_design: Architect 에이전트가 생성한 설계 딕셔너리
        tool_mapping: Tool Mapper 에이전트가 생성한 도구 매핑
        workflow_name: 워크플로우 이름

    Returns:
        n8n import 가능한 JSON 딕셔너리
    """
    pattern = automation_design.get("primary_pattern", "LINEAR")
    components = automation_design.get("components", [])
    hitl_nodes = automation_design.get("hitl_nodes", [])

    n8n_nodes: list[dict] = []
    connections: dict[str, dict] = {}

    # 1. 트리거 노드
    trigger_def = PATTERN_TRIGGERS.get(pattern, PATTERN_TRIGGERS["LINEAR"])
    trigger_node = _make_node(
        name=trigger_def["name"],
        node_type=trigger_def["type"],
        parameters=trigger_def["parameters"],
        position=[240, 300],
        is_trigger=True,
    )
    n8n_nodes.append(trigger_node)
    prev_name = trigger_node["name"]

    # 2. 컴포넌트 → 노드 변환
    x_pos = 460
    for i, comp in enumerate(components):
        comp_name = comp.get("name", f"Step {i+1}")
        tools_used = comp.get("tools_used", [])

        # 도구 매핑에서 추가 도구 정보 가져오기
        if tool_mapping:
            mapped = tool_mapping.get("tool_assignments", {}).get(comp_name, {})
            if mapped.get("primary_tool"):
                tools_used = [mapped["primary_tool"]] + tools_used

        # 도구 → n8n 노드 타입 매핑
        n8n_type = _resolve_n8n_type(tools_used, comp.get("operation_type", ""))

        node = _make_node(
            name=comp_name,
            node_type=n8n_type["type"],
            parameters=_merge_parameters(n8n_type.get("parameters", {}), comp),
            position=[x_pos, 300],
            notes=comp.get("description", ""),
        )
        n8n_nodes.append(node)

        # 연결 추가
        _add_connection(connections, prev_name, comp_name)
        prev_name = comp_name
        x_pos += 220

        # HITL 노드가 있으면 Wait 노드 삽입
        if comp_name in hitl_nodes or any(h in comp_name for h in hitl_nodes):
            wait_node = _make_node(
                name=f"{comp_name} - 승인 대기",
                node_type="n8n-nodes-base.wait",
                parameters={"resume": "webhook"},
                position=[x_pos, 300],
                notes="사람 승인 대기 (Human-in-the-Loop)",
            )
            n8n_nodes.append(wait_node)
            _add_connection(connections, prev_name, wait_node["name"])
            prev_name = wait_node["name"]
            x_pos += 220

    # 3. 오류 처리 노드
    error_node = _make_node(
        name="오류 알림",
        node_type="n8n-nodes-base.emailSend",
        parameters={
            "toEmail": "owner@example.com",
            "subject": "⚠️ 자동화 오류 발생",
            "text": "워크플로우 실행 중 오류가 발생했습니다. n8n 대시보드를 확인하세요.",
        },
        position=[x_pos, 500],
        notes="오류 발생 시 자동 알림",
    )
    n8n_nodes.append(error_node)

    # 4. 완료 알림 노드
    complete_node = _make_node(
        name="완료 알림",
        node_type="n8n-nodes-base.slack",
        parameters={
            "resource": "message",
            "operation": "post",
            "channel": "#automation-complete",
            "text": "✅ 자동화 워크플로우 완료",
        },
        position=[x_pos, 300],
    )
    n8n_nodes.append(complete_node)
    _add_connection(connections, prev_name, complete_node["name"])

    return {
        "name": workflow_name,
        "nodes": n8n_nodes,
        "connections": connections,
        "active": False,
        "settings": {
            "executionOrder": "v1",
            "errorWorkflow": "",
            "timezone": "Asia/Seoul",
        },
        "tags": [{"name": "ax-generated"}, {"name": "automation"}],
        "meta": {
            "instanceId": str(uuid.uuid4()),
            "generatedBy": "SMALL AX AGENT",
            "pattern": pattern,
        },
    }


# ── Make(Integromat) 변환 ────────────────────────────────────

def design_to_make(
    automation_design: dict,
    tool_mapping: dict | None = None,
    scenario_name: str = "AX 자동화 시나리오",
) -> dict:
    """
    automation_design → Make(Integromat) 시나리오 JSON

    Make 포맷:
    {
      "name": "...",
      "flow": [ModuleObject, ...],
      "metadata": {...}
    }
    """
    pattern = automation_design.get("primary_pattern", "LINEAR")
    components = automation_design.get("components", [])

    modules: list[dict] = []
    module_id = 1

    # 트리거 모듈
    if pattern in ("TRIGGER_ACTION", "APPROVAL"):
        trigger_module = {
            "id": module_id,
            "module": "gateway:CustomWebHook",
            "version": 1,
            "parameters": {"hook": 1, "maxResults": 1},
            "mapper": {},
            "metadata": {"designer": {"x": 0, "y": 0}, "name": "웹훅 트리거"},
        }
    else:
        trigger_module = {
            "id": module_id,
            "module": "util:SetVariable",
            "version": 1,
            "parameters": {},
            "mapper": {"name": "trigger", "value": "scheduled"},
            "metadata": {"designer": {"x": 0, "y": 0}, "name": "스케줄 시작"},
        }
    modules.append(trigger_module)
    module_id += 1

    # 컴포넌트 모듈들
    x_pos = 300
    for comp in components:
        comp_name = comp.get("name", f"Module {module_id}")
        tools = comp.get("tools_used", [])

        make_module = _comp_to_make_module(module_id, comp_name, tools, x_pos)
        modules.append(make_module)
        module_id += 1
        x_pos += 300

    # 완료 알림
    modules.append({
        "id": module_id,
        "module": "http:ActionSendData",
        "version": 3,
        "parameters": {},
        "mapper": {
            "url": "https://kapi.kakao.com/v1/api/talk/message/default/send",
            "method": "POST",
            "bodyType": "application/json",
            "body": '{"template_id": 1, "template_args": {"status": "completed"}}',
        },
        "metadata": {
            "designer": {"x": x_pos, "y": 0},
            "name": "완료 알림 (카카오톡)",
        },
    })

    return {
        "name": scenario_name,
        "flow": modules,
        "metadata": {
            "instant": pattern in ("TRIGGER_ACTION",),
            "version": 1,
            "scenario": {"roundtrips": 1, "maxErrors": 3, "autoCommit": True},
            "designer": {"orphans": []},
            "zone": "us1.make.com",
            "generatedBy": "SMALL AX AGENT",
        },
    }


# ── 내부 헬퍼 ────────────────────────────────────────────────

def _make_node(
    name: str,
    node_type: str,
    parameters: dict,
    position: list[int],
    is_trigger: bool = False,
    notes: str = "",
) -> dict:
    node: dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "name": name,
        "type": node_type,
        "typeVersion": 1,
        "position": position,
        "parameters": parameters,
    }
    if notes:
        node["notes"] = notes
    if is_trigger:
        node["webhookId"] = str(uuid.uuid4())
    return node


def _resolve_n8n_type(tools: list[str], operation: str) -> dict:
    """도구 리스트 → 가장 적합한 n8n 노드 타입 반환"""
    for tool in tools:
        key = tool.lower().strip()
        if key in TOOL_TO_N8N:
            return TOOL_TO_N8N[key]
        # 부분 매칭
        for k, v in TOOL_TO_N8N.items():
            if k in key or key in k:
                return v

    # 기본값: HTTP Request
    return {
        "type": "n8n-nodes-base.httpRequest",
        "parameters": {"method": "GET", "url": "https://api.example.com"},
    }


def _merge_parameters(base: dict, comp: dict) -> dict:
    """기본 파라미터에 컴포넌트 설명 병합"""
    merged = dict(base)
    if comp.get("description"):
        merged["_notes"] = comp["description"]
    return merged


def _add_connection(connections: dict, from_node: str, to_node: str) -> None:
    """노드 간 연결 추가"""
    if from_node not in connections:
        connections[from_node] = {"main": [[{"node": to_node, "type": "main", "index": 0}]]}
    else:
        connections[from_node]["main"][0].append({"node": to_node, "type": "main", "index": 0})


def _comp_to_make_module(module_id: int, name: str, tools: list[str], x_pos: int) -> dict:
    """컴포넌트 → Make 모듈"""
    # 카카오 알림톡
    if any("카카오" in t for t in tools):
        return {
            "id": module_id,
            "module": "http:ActionSendData",
            "version": 3,
            "parameters": {},
            "mapper": {
                "url": "https://kapi.kakao.com/v1/api/talk/message/default/send",
                "method": "POST",
                "headers": [{"name": "Authorization", "value": "KakaoAK YOUR_API_KEY"}],
            },
            "metadata": {"designer": {"x": x_pos, "y": 0}, "name": name},
        }
    # 구글 시트
    if any("google" in t.lower() or "sheet" in t.lower() for t in tools):
        return {
            "id": module_id,
            "module": "google-sheets:ActionAddRow",
            "version": 2,
            "parameters": {"spreadsheetId": "YOUR_SHEET_ID", "sheetId": 0},
            "mapper": {},
            "metadata": {"designer": {"x": x_pos, "y": 0}, "name": name},
        }
    # 기본: HTTP
    return {
        "id": module_id,
        "module": "http:ActionSendData",
        "version": 3,
        "parameters": {},
        "mapper": {"url": "https://api.example.com", "method": "POST"},
        "metadata": {"designer": {"x": x_pos, "y": 0}, "name": name},
    }
