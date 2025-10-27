"""
워크플로우 관련 스키마 정의

WorkflowNode: 워크플로우 캔버스의 노드 (Worker Agent)
WorkflowEdge: 노드 간 연결 (데이터 흐름)
Workflow: 전체 워크플로우 정의
"""

from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field


class WorkerNodeData(BaseModel):
    """
    Worker 노드의 데이터 (개별 Worker Agent)

    Attributes:
        agent_name: Worker Agent 이름 (planner, coder, reviewer 등)
        task_template: 작업 설명 템플릿 ({{input}} 등의 변수 지원)
        allowed_tools: 사용 가능한 도구 목록 (옵션, 미지정 시 기본 설정 사용)
        config: 추가 설정 (옵션)
    """
    agent_name: str = Field(..., description="Worker Agent 이름")
    task_template: str = Field(
        ...,
        description="작업 설명 템플릿 ({{input}}, {{node_id}} 등 변수 지원)"
    )
    allowed_tools: Optional[List[str]] = Field(
        default=None,
        description="사용 가능한 도구 목록 (옵션, 미지정 시 agent_config.json의 기본값 사용)"
    )
    config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="추가 설정 (옵션)"
    )


class ManagerNodeData(BaseModel):
    """
    Manager 노드의 데이터 (오케스트레이터)

    Manager 노드는 등록된 Worker들을 조율하여 작업을 수행합니다.
    - TUI의 Manager Agent와 동일하게 동작
    - 등록된 워커만 호출 가능
    - 병렬 워커 호출 지원

    Attributes:
        task_description: 초기 작업 설명 (Manager에게 전달)
        available_workers: 사용 가능한 워커 이름 목록 (등록된 워커만 호출 가능)
        config: 추가 설정 (옵션)
    """
    task_description: str = Field(
        ...,
        description="Manager에게 전달할 초기 작업 설명"
    )
    available_workers: List[str] = Field(
        ...,
        description="사용 가능한 워커 이름 목록 (예: ['planner', 'coder', 'reviewer'])"
    )
    config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="추가 설정 (옵션)"
    )


class InputNodeData(BaseModel):
    """
    Input 노드의 데이터 (워크플로우 시작점)

    Input 노드는 워크플로우의 시작점으로, 초기 입력을 저장하고
    연결된 노드로 전달합니다.

    Attributes:
        initial_input: 초기 입력 텍스트
    """
    initial_input: str = Field(
        ...,
        description="워크플로우 초기 입력 텍스트"
    )


# Union 타입으로 Worker/Manager/Input 구분
WorkflowNodeData = Union[WorkerNodeData, ManagerNodeData, InputNodeData]


class WorkflowNode(BaseModel):
    """
    워크플로우 노드 (React Flow 호환 형식)

    Attributes:
        id: 노드 고유 ID
        type: 노드 타입 (worker, manager, input)
        position: 캔버스 상의 위치 {x, y}
        data: 노드 데이터 (WorkerNodeData, ManagerNodeData, InputNodeData)
    """
    id: str = Field(..., description="노드 고유 ID")
    type: str = Field(default="worker", description="노드 타입 (worker, manager, input)")
    position: Dict[str, float] = Field(
        ...,
        description="캔버스 상의 위치",
        example={"x": 100, "y": 100}
    )
    data: Union[WorkerNodeData, ManagerNodeData, InputNodeData, Dict[str, Any]] = Field(
        ...,
        description="노드 데이터 (타입에 따라 다름)"
    )


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


# ==================== 프로젝트 설정 스키마 ====================


class ProjectConfig(BaseModel):
    """
    프로젝트 워크플로우 설정

    프로젝트 디렉토리의 .better-llm/workflow-config.json에 저장됩니다.

    Attributes:
        project_path: 프로젝트 디렉토리 절대 경로
        workflow: 워크플로우 정의
        metadata: 메타데이터 (마지막 수정 시간 등)
    """
    project_path: str = Field(..., description="프로젝트 디렉토리 절대 경로")
    workflow: Workflow = Field(..., description="워크플로우 정의")
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="메타데이터 (last_modified, version 등)"
    )


class ProjectSelectRequest(BaseModel):
    """
    프로젝트 선택 요청

    Attributes:
        project_path: 프로젝트 디렉토리 절대 경로
    """
    project_path: str = Field(
        ...,
        description="프로젝트 디렉토리 절대 경로",
        example="/Users/username/my-project"
    )


class ProjectSelectResponse(BaseModel):
    """
    프로젝트 선택 응답

    Attributes:
        project_path: 선택된 프로젝트 경로
        message: 응답 메시지
        has_existing_config: 기존 설정 존재 여부
    """
    project_path: str = Field(..., description="선택된 프로젝트 경로")
    message: str = Field(..., description="응답 메시지")
    has_existing_config: bool = Field(
        ...,
        description="기존 설정 존재 여부 (자동 로드 가능)"
    )


class ProjectWorkflowSaveRequest(BaseModel):
    """
    프로젝트에 워크플로우 저장 요청

    Attributes:
        project_path: 프로젝트 디렉토리 경로 (옵션, 미제공 시 현재 프로젝트 사용)
        workflow: 저장할 워크플로우
    """
    project_path: Optional[str] = Field(
        default=None,
        description="프로젝트 디렉토리 경로 (미제공 시 현재 프로젝트)"
    )
    workflow: Workflow = Field(..., description="저장할 워크플로우")


class ProjectWorkflowLoadResponse(BaseModel):
    """
    프로젝트에서 워크플로우 로드 응답

    Attributes:
        project_path: 프로젝트 경로
        workflow: 로드된 워크플로우
        last_modified: 마지막 수정 시간
    """
    project_path: str = Field(..., description="프로젝트 경로")
    workflow: Workflow = Field(..., description="로드된 워크플로우")
    last_modified: Optional[str] = Field(
        default=None,
        description="마지막 수정 시간 (ISO 8601)"
    )
