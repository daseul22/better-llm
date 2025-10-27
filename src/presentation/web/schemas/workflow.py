"""
워크플로우 관련 스키마 정의

WorkflowNode: 워크플로우 캔버스의 노드 (Worker Agent)
WorkflowEdge: 노드 간 연결 (데이터 흐름)
Workflow: 전체 워크플로우 정의
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class WorkflowNodeData(BaseModel):
    """
    워크플로우 노드의 데이터 (Worker Agent 설정)

    Attributes:
        agent_name: Worker Agent 이름 (planner, coder, reviewer 등)
        task_template: 작업 설명 템플릿 ({{input}} 등의 변수 지원)
        config: 추가 설정 (옵션)
    """
    agent_name: str = Field(..., description="Worker Agent 이름")
    task_template: str = Field(
        ...,
        description="작업 설명 템플릿 ({{input}}, {{node_id}} 등 변수 지원)"
    )
    config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="추가 설정 (옵션)"
    )


class WorkflowNode(BaseModel):
    """
    워크플로우 노드 (React Flow 호환 형식)

    Attributes:
        id: 노드 고유 ID
        type: 노드 타입 (worker, input, output)
        position: 캔버스 상의 위치 {x, y}
        data: 노드 데이터 (agent_name, task_template 등)
    """
    id: str = Field(..., description="노드 고유 ID")
    type: str = Field(default="worker", description="노드 타입")
    position: Dict[str, float] = Field(
        ...,
        description="캔버스 상의 위치",
        example={"x": 100, "y": 100}
    )
    data: WorkflowNodeData = Field(..., description="노드 데이터")


class WorkflowEdge(BaseModel):
    """
    워크플로우 엣지 (노드 간 연결)

    Attributes:
        id: 엣지 고유 ID
        source: 시작 노드 ID
        target: 종료 노드 ID
        sourceHandle: 시작 핸들 ID (옵션)
        targetHandle: 종료 핸들 ID (옵션)
    """
    id: str = Field(..., description="엣지 고유 ID")
    source: str = Field(..., description="시작 노드 ID")
    target: str = Field(..., description="종료 노드 ID")
    sourceHandle: Optional[str] = Field(
        default=None,
        description="시작 핸들 ID"
    )
    targetHandle: Optional[str] = Field(
        default=None,
        description="종료 핸들 ID"
    )


class Workflow(BaseModel):
    """
    워크플로우 정의 (전체)

    Attributes:
        id: 워크플로우 고유 ID
        name: 워크플로우 이름
        description: 워크플로우 설명
        nodes: 노드 목록
        edges: 엣지 목록
        metadata: 추가 메타데이터 (옵션)
    """
    id: Optional[str] = Field(default=None, description="워크플로우 고유 ID")
    name: str = Field(..., description="워크플로우 이름")
    description: Optional[str] = Field(
        default=None,
        description="워크플로우 설명"
    )
    nodes: List[WorkflowNode] = Field(..., description="노드 목록")
    edges: List[WorkflowEdge] = Field(..., description="엣지 목록")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="추가 메타데이터"
    )


class WorkflowExecuteRequest(BaseModel):
    """
    워크플로우 실행 요청

    Attributes:
        workflow: 실행할 워크플로우
        initial_input: 초기 입력 데이터
        session_id: 세션 ID (옵션)
    """
    workflow: Workflow = Field(..., description="실행할 워크플로우")
    initial_input: str = Field(
        ...,
        description="초기 입력 데이터 (첫 번째 노드에 전달)"
    )
    session_id: Optional[str] = Field(
        default=None,
        description="세션 ID (비워두면 자동 생성)"
    )


class WorkflowExecuteResponse(BaseModel):
    """
    워크플로우 실행 응답

    Attributes:
        session_id: 세션 ID
        status: 실행 상태 (running, completed, failed)
        message: 상태 메시지
    """
    session_id: str = Field(..., description="세션 ID")
    status: str = Field(..., description="실행 상태")
    message: str = Field(..., description="상태 메시지")


class WorkflowSaveRequest(BaseModel):
    """
    워크플로우 저장 요청

    Attributes:
        workflow: 저장할 워크플로우
    """
    workflow: Workflow = Field(..., description="저장할 워크플로우")


class WorkflowSaveResponse(BaseModel):
    """
    워크플로우 저장 응답

    Attributes:
        workflow_id: 저장된 워크플로우 ID
        message: 응답 메시지
    """
    workflow_id: str = Field(..., description="저장된 워크플로우 ID")
    message: str = Field(..., description="응답 메시지")


class WorkflowListResponse(BaseModel):
    """
    워크플로우 목록 응답

    Attributes:
        workflows: 워크플로우 목록 (메타데이터만)
    """
    workflows: List[Dict[str, Any]] = Field(
        ...,
        description="워크플로우 목록 (id, name, description)"
    )


class WorkflowNodeExecutionEvent(BaseModel):
    """
    워크플로우 노드 실행 이벤트 (SSE)

    Attributes:
        event_type: 이벤트 타입 (node_start, node_output, node_complete, node_error)
        node_id: 노드 ID
        data: 이벤트 데이터
    """
    event_type: str = Field(
        ...,
        description="이벤트 타입",
        example="node_start"
    )
    node_id: str = Field(..., description="노드 ID")
    data: Dict[str, Any] = Field(..., description="이벤트 데이터")
