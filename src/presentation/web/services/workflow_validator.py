"""
워크플로우 검증기

워크플로우 실행 전 검증을 수행합니다:
- 순환 참조 검사 (DFS)
- 고아 노드 검사
- 템플릿 변수 유효성 검사
- Worker별 필수 도구 검사
"""

from typing import List, Dict, Set, Optional, Any
from dataclasses import dataclass
import re
from pathlib import Path
import json

from ..schemas.workflow import (
    Workflow,
    WorkflowNode,
    WorkflowEdge,
    WorkerNodeData,
    ManagerNodeData,
    InputNodeData,
)


@dataclass
class ValidationError:
    """
    워크플로우 검증 에러

    Attributes:
        severity: 심각도 ('error', 'warning', 'info')
        node_id: 에러가 발생한 노드 ID
        message: 에러 메시지
        suggestion: 해결 방법 제안
    """
    severity: str  # 'error', 'warning', 'info'
    node_id: str
    message: str
    suggestion: str


class WorkflowValidator:
    """
    워크플로우 검증기

    워크플로우 실행 전 다양한 검증을 수행하여 잠재적인 문제를 사전에 감지합니다.
    """

    # Worker별 사용 가능한 도구 (agent_config.json 기반)
    WORKER_TOOLS: Dict[str, List[str]] = {
        # 범용 워커
        "planner": ["read", "glob", "grep"],
        "coder": ["read", "write", "edit", "glob", "grep"],
        "reviewer": ["read", "glob", "grep"],
        "tester": ["read", "bash", "glob", "grep"],
        "committer": ["bash", "read", "glob", "grep"],
        "ideator": ["read", "glob"],
        "product_manager": ["read", "glob", "grep"],
        "documenter": ["read", "write", "edit", "glob", "grep"],
        # 특화 워커
        "style_reviewer": ["read", "glob", "grep"],
        "security_reviewer": ["read", "glob", "grep"],
        "summarizer": ["read", "glob"],
        "architecture_reviewer": ["read", "glob", "grep"],
        "bug_fixer": ["read", "write", "edit", "bash", "glob", "grep"],
        "log_analyzer": ["read", "bash", "glob", "grep"],
    }

    # 템플릿 변수 패턴 ({{input}}, {{node_123}} 등)
    TEMPLATE_VAR_PATTERN = re.compile(r'\{\{(\w+)\}\}')

    def __init__(self, config_loader=None):
        """
        워크플로우 검증기 초기화

        Args:
            config_loader: 설정 로더 (옵션, Worker 도구 목록 동적 로드용)
        """
        self.config_loader = config_loader

        # config_loader가 제공되면 동적으로 Worker 도구 목록 로드
        if config_loader:
            self._load_worker_tools_from_config()

    def _load_worker_tools_from_config(self):
        """agent_config.json에서 Worker별 도구 목록 동적 로드"""
        try:
            config = self.config_loader.load_agent_config()
            for agent in config.get("agents", []):
                agent_name = agent.get("name")
                tools = agent.get("tools", [])
                if agent_name and tools:
                    self.WORKER_TOOLS[agent_name] = tools
        except Exception:
            # 로드 실패 시 기본값 사용
            pass

    def validate(self, workflow: Workflow) -> List[ValidationError]:
        """
        워크플로우 검증 (전체)

        Args:
            workflow: 검증할 워크플로우

        Returns:
            검증 에러 목록 (비어있으면 검증 통과)
        """
        errors: List[ValidationError] = []

        # 1. 순환 참조 검사
        errors.extend(self._check_cycles(workflow))

        # 2. 고아 노드 검사
        errors.extend(self._check_orphan_nodes(workflow))

        # 3. 템플릿 변수 검증
        errors.extend(self._validate_template_variables(workflow))

        # 4. Worker별 필수 도구 권한 검사
        errors.extend(self._check_worker_tools(workflow))

        # 5. Input 노드 존재 여부 검사
        errors.extend(self._check_input_node(workflow))

        # 6. Manager 노드 검증
        errors.extend(self._check_manager_nodes(workflow))

        return errors

    def _check_cycles(self, workflow: Workflow) -> List[ValidationError]:
        """
        순환 참조 검사 (DFS)

        Args:
            workflow: 검증할 워크플로우

        Returns:
            순환 참조 에러 목록
        """
        errors: List[ValidationError] = []

        # 그래프 구성 (인접 리스트)
        graph: Dict[str, List[str]] = {node.id: [] for node in workflow.nodes}
        for edge in workflow.edges:
            if edge.source in graph:
                graph[edge.source].append(edge.target)

        # DFS로 순환 참조 검사
        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def dfs(node_id: str, path: List[str]) -> Optional[List[str]]:
            """
            DFS로 순환 참조 탐지

            Returns:
                순환 경로 (순환이 있으면), 없으면 None
            """
            visited.add(node_id)
            rec_stack.add(node_id)
            path.append(node_id)

            for neighbor in graph.get(node_id, []):
                if neighbor not in visited:
                    cycle_path = dfs(neighbor, path.copy())
                    if cycle_path:
                        return cycle_path
                elif neighbor in rec_stack:
                    # 순환 발견
                    cycle_start_idx = path.index(neighbor)
                    return path[cycle_start_idx:] + [neighbor]

            rec_stack.remove(node_id)
            return None

        # 모든 노드에서 DFS 시작
        for node_id in graph:
            if node_id not in visited:
                cycle_path = dfs(node_id, [])
                if cycle_path:
                    errors.append(ValidationError(
                        severity="error",
                        node_id=cycle_path[0],
                        message=f"순환 참조가 감지되었습니다: {' → '.join(cycle_path)}",
                        suggestion="노드 간 연결을 확인하여 순환 참조를 제거하세요."
                    ))
                    break  # 하나만 보고 (여러 개일 수 있지만 가독성 위해)

        return errors

    def _check_orphan_nodes(self, workflow: Workflow) -> List[ValidationError]:
        """
        고아 노드 검사 (연결되지 않은 노드)

        Args:
            workflow: 검증할 워크플로우

        Returns:
            고아 노드 에러 목록
        """
        errors: List[ValidationError] = []

        # 연결된 노드 ID 집합
        connected_nodes: Set[str] = set()
        for edge in workflow.edges:
            connected_nodes.add(edge.source)
            connected_nodes.add(edge.target)

        # 고아 노드 찾기 (Input 노드는 제외)
        for node in workflow.nodes:
            if node.id not in connected_nodes and node.type != "input":
                errors.append(ValidationError(
                    severity="warning",
                    node_id=node.id,
                    message=f"노드 '{node.id}'가 다른 노드와 연결되지 않았습니다.",
                    suggestion="이 노드를 다른 노드와 연결하거나 삭제하세요."
                ))

        return errors

    def _validate_template_variables(self, workflow: Workflow) -> List[ValidationError]:
        """
        템플릿 변수 유효성 검사

        {{input}}, {{node_123}} 등의 템플릿 변수가 유효한지 검사합니다.

        Args:
            workflow: 검증할 워크플로우

        Returns:
            템플릿 변수 에러 목록
        """
        errors: List[ValidationError] = []

        # 노드 ID 집합
        node_ids = {node.id for node in workflow.nodes}

        # 각 노드의 템플릿 검증
        for node in workflow.nodes:
            template = None

            # 노드 타입별 템플릿 추출
            if node.type == "worker" and isinstance(node.data, (WorkerNodeData, dict)):
                if isinstance(node.data, WorkerNodeData):
                    template = node.data.task_template
                elif isinstance(node.data, dict):
                    template = node.data.get("task_template", "")
            elif node.type == "manager" and isinstance(node.data, (ManagerNodeData, dict)):
                if isinstance(node.data, ManagerNodeData):
                    template = node.data.task_description
                elif isinstance(node.data, dict):
                    template = node.data.get("task_description", "")

            if not template:
                continue

            # 템플릿 변수 추출 ({{...}})
            variables = self.TEMPLATE_VAR_PATTERN.findall(template)

            for var in variables:
                # 'input'은 항상 유효
                if var == "input":
                    continue

                # 노드 ID 참조 검증 (예: {{node_123}})
                if var.startswith("node_"):
                    referenced_node_id = var  # 전체 변수 이름이 노드 ID
                elif var in node_ids:
                    # 노드 ID 직접 참조
                    referenced_node_id = var
                else:
                    # 유효하지 않은 변수
                    example_node = list(node_ids)[0] if node_ids else 'node_1'
                    errors.append(ValidationError(
                        severity="error",
                        node_id=node.id,
                        message=f"유효하지 않은 템플릿 변수입니다: {{{{{var}}}}}",
                        suggestion=f"변수 이름을 확인하세요. 사용 가능한 변수: {{{{input}}}}, 또는 노드 ID (예: {{{example_node}}})"
                    ))
                    continue

                # 참조하는 노드가 존재하는지 확인
                if referenced_node_id not in node_ids:
                    errors.append(ValidationError(
                        severity="error",
                        node_id=node.id,
                        message=f"존재하지 않는 노드를 참조합니다: {{{{{var}}}}}",
                        suggestion=f"노드 ID '{referenced_node_id}'가 존재하지 않습니다. 올바른 노드 ID를 사용하세요."
                    ))

        return errors

    def _check_worker_tools(self, workflow: Workflow) -> List[ValidationError]:
        """
        Worker별 필수 도구 권한 검사

        Worker 노드에서 사용하는 도구가 해당 Worker의 허용 도구 목록에 있는지 검사합니다.

        Args:
            workflow: 검증할 워크플로우

        Returns:
            도구 권한 에러 목록
        """
        errors: List[ValidationError] = []

        for node in workflow.nodes:
            if node.type != "worker":
                continue

            # Worker 노드 데이터 추출
            agent_name = None
            allowed_tools = None

            if isinstance(node.data, WorkerNodeData):
                agent_name = node.data.agent_name
                allowed_tools = node.data.allowed_tools
            elif isinstance(node.data, dict):
                agent_name = node.data.get("agent_name")
                allowed_tools = node.data.get("allowed_tools")

            if not agent_name:
                continue

            # Worker 기본 도구 목록 가져오기
            default_tools = self.WORKER_TOOLS.get(agent_name, [])

            # 커스텀 워커인 경우 (WORKER_TOOLS에 없음) 검증 스킵
            if not default_tools:
                continue

            # allowed_tools가 지정된 경우, 기본 도구 목록과 비교
            if allowed_tools:
                invalid_tools = [tool for tool in allowed_tools if tool not in default_tools]
                if invalid_tools:
                    errors.append(ValidationError(
                        severity="error",
                        node_id=node.id,
                        message=f"Worker '{agent_name}'이(가) 사용할 수 없는 도구가 지정되었습니다: {', '.join(invalid_tools)}",
                        suggestion=f"'{agent_name}'의 허용 도구: {', '.join(default_tools)}"
                    ))

        return errors

    def _check_input_node(self, workflow: Workflow) -> List[ValidationError]:
        """
        Input 노드 존재 여부 검사

        워크플로우는 최소 1개의 Input 노드가 필요합니다.

        Args:
            workflow: 검증할 워크플로우

        Returns:
            Input 노드 에러 목록
        """
        errors: List[ValidationError] = []

        input_nodes = [node for node in workflow.nodes if node.type == "input"]

        if len(input_nodes) == 0:
            errors.append(ValidationError(
                severity="error",
                node_id="",
                message="워크플로우에 Input 노드가 없습니다.",
                suggestion="워크플로우 시작점으로 Input 노드를 추가하세요."
            ))
        elif len(input_nodes) > 1:
            errors.append(ValidationError(
                severity="warning",
                node_id=input_nodes[1].id,
                message="워크플로우에 여러 개의 Input 노드가 있습니다.",
                suggestion="일반적으로 Input 노드는 1개만 필요합니다. 불필요한 노드를 제거하세요."
            ))

        return errors

    def _check_manager_nodes(self, workflow: Workflow) -> List[ValidationError]:
        """
        Manager 노드 검증

        Manager 노드는 최소 1개의 워커가 등록되어 있어야 합니다.

        Args:
            workflow: 검증할 워크플로우

        Returns:
            Manager 노드 에러 목록
        """
        errors: List[ValidationError] = []

        for node in workflow.nodes:
            if node.type != "manager":
                continue

            # Manager 노드 데이터 추출
            available_workers = None

            if isinstance(node.data, ManagerNodeData):
                available_workers = node.data.available_workers
            elif isinstance(node.data, dict):
                available_workers = node.data.get("available_workers", [])

            # 워커 등록 여부 검사
            if not available_workers or len(available_workers) == 0:
                errors.append(ValidationError(
                    severity="error",
                    node_id=node.id,
                    message="Manager 노드에 등록된 워커가 없습니다.",
                    suggestion="Manager 노드는 최소 1개의 워커가 필요합니다. 노드 설정에서 워커를 선택하세요."
                ))
            # 커스텀 워커 지원을 위해 알려지지 않은 워커 검증 제거

        return errors
