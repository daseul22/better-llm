"""
워크플로우 실행 엔진

워크플로우의 노드를 순차적으로 실행하고, 노드 간 데이터 전달을 관리합니다.
"""

import asyncio
import time
from datetime import datetime
from typing import Dict, Any, AsyncIterator, Set, List
from collections import deque
from dataclasses import replace

from src.domain.models import AgentConfig, Message
from src.infrastructure.config import JsonConfigLoader, get_project_root
from src.infrastructure.claude.worker_client import WorkerAgent
from src.infrastructure.claude.manager_client import ManagerAgent
from src.infrastructure.logging import get_logger
from src.presentation.web.schemas.workflow import (
    Workflow,
    WorkflowNode,
    WorkflowEdge,
    WorkflowNodeExecutionEvent,
    WorkerNodeData,
    ManagerNodeData,
    TokenUsage,
)

logger = get_logger(__name__)


class WorkflowExecutor:
    """
    워크플로우 실행 엔진

    워크플로우의 노드를 위상 정렬하여 순차적으로 실행하고,
    각 노드의 출력을 다음 노드의 입력으로 전달합니다.

    Attributes:
        config_loader: Agent 설정 로더
        agent_configs: Agent 설정 목록 (캐시)
    """

    def __init__(self, config_loader: JsonConfigLoader):
        """
        WorkflowExecutor 초기화

        Args:
            config_loader: Agent 설정 로더
        """
        self.config_loader = config_loader
        self.agent_configs = config_loader.load_agent_configs()
        self.agent_config_map = {
            config.name: config for config in self.agent_configs
        }

    def _get_agent_config(self, agent_name: str) -> AgentConfig:
        """
        Agent 설정 조회

        Args:
            agent_name: Agent 이름

        Returns:
            AgentConfig: Agent 설정

        Raises:
            ValueError: Agent를 찾을 수 없는 경우
        """
        config = self.agent_config_map.get(agent_name)
        if not config:
            raise ValueError(f"Agent '{agent_name}'를 찾을 수 없습니다")
        return config

    def _topological_sort(
        self, nodes: List[WorkflowNode], edges: List[WorkflowEdge]
    ) -> List[WorkflowNode]:
        """
        워크플로우 노드 위상 정렬 (Topological Sort)

        Args:
            nodes: 노드 목록
            edges: 엣지 목록

        Returns:
            List[WorkflowNode]: 실행 순서대로 정렬된 노드 목록

        Raises:
            ValueError: 순환 참조가 있는 경우
        """
        # 노드 ID → 노드 매핑
        node_map = {node.id: node for node in nodes}

        # 인접 리스트 (노드 ID → 자식 노드 ID 목록)
        adjacency: Dict[str, List[str]] = {node.id: [] for node in nodes}
        in_degree: Dict[str, int] = {node.id: 0 for node in nodes}

        for edge in edges:
            adjacency[edge.source].append(edge.target)
            in_degree[edge.target] += 1

        # 진입 차수가 0인 노드로 시작
        queue = deque([node_id for node_id, deg in in_degree.items() if deg == 0])
        sorted_nodes = []

        while queue:
            node_id = queue.popleft()
            sorted_nodes.append(node_map[node_id])

            # 자식 노드의 진입 차수 감소
            for child_id in adjacency[node_id]:
                in_degree[child_id] -= 1
                if in_degree[child_id] == 0:
                    queue.append(child_id)

        # 순환 참조 검사
        if len(sorted_nodes) != len(nodes):
            raise ValueError("워크플로우에 순환 참조가 있습니다")

        return sorted_nodes

    def _get_parent_nodes(
        self, node_id: str, edges: List[WorkflowEdge]
    ) -> List[str]:
        """
        노드의 부모 노드 ID 목록 조회

        Args:
            node_id: 노드 ID
            edges: 엣지 목록

        Returns:
            List[str]: 부모 노드 ID 목록
        """
        return [edge.source for edge in edges if edge.target == node_id]

    def _render_task_template(
        self,
        template: str,
        node_id: str,
        node_outputs: Dict[str, str],
        initial_input: str,
    ) -> str:
        """
        작업 설명 템플릿 렌더링

        변수:
        - {{input}}: 초기 입력 (첫 번째 노드)
        - {{node_<id>}}: 특정 노드의 출력
        - {{parent}}: 부모 노드의 출력 (부모가 1개인 경우)

        Args:
            template: 템플릿 문자열
            node_id: 현재 노드 ID
            node_outputs: 노드 ID → 출력 매핑
            initial_input: 초기 입력

        Returns:
            str: 렌더링된 작업 설명
        """
        result = template

        # {{input}} 치환
        result = result.replace("{{input}}", initial_input)

        # {{node_<id>}} 치환
        for nid, output in node_outputs.items():
            result = result.replace(f"{{{{node_{nid}}}}}", output)

        # {{parent}} 치환 (부모가 1개인 경우만 지원)
        if "{{parent}}" in result:
            parent_nodes = [
                nid for nid in node_outputs.keys()
                if nid in result  # 임시: 더 정교한 로직 필요
            ]
            if len(parent_nodes) == 1:
                result = result.replace("{{parent}}", node_outputs[parent_nodes[0]])

        return result

    async def _execute_manager_node(
        self,
        node: WorkflowNode,
        node_outputs: Dict[str, str],
        initial_input: str,
        session_id: str,
    ) -> AsyncIterator[WorkflowNodeExecutionEvent]:
        """
        Manager 노드 실행 (병렬 워커 호출)

        Manager 노드는 등록된 워커들을 병렬로 실행하여 결과를 통합합니다.

        Args:
            node: Manager 노드
            node_outputs: 이전 노드 출력들
            initial_input: 초기 입력
            session_id: 세션 ID

        Yields:
            WorkflowNodeExecutionEvent: 노드 실행 이벤트
        """
        node_id = node.id
        node_data: ManagerNodeData = node.data  # type: ignore
        task_description = node_data.task_description
        available_workers = node_data.available_workers

        logger.info(
            f"[{session_id}] Manager 노드 실행: {node_id} "
            f"(워커: {available_workers})"
        )

        # 노드 시작 시간 기록
        start_time = time.time()

        # 노드 시작 이벤트
        start_event = WorkflowNodeExecutionEvent(
            event_type="node_start",
            node_id=node_id,
            data={
                "node_type": "manager",
                "available_workers": available_workers
            },
            timestamp=datetime.now().isoformat(),
        )
        yield start_event

        try:
            # 등록된 워커들 병렬 실행
            worker_tasks = []
            for worker_name in available_workers:
                # Worker 설정 조회
                try:
                    worker_config = self._get_agent_config(worker_name)
                except ValueError as e:
                    logger.warning(
                        f"[{session_id}] 워커 '{worker_name}' 설정을 찾을 수 없습니다: {e}"
                    )
                    continue

                # Worker Agent 생성
                worker = WorkerAgent(config=worker_config)
                worker_tasks.append((worker_name, worker.execute_task(task_description)))

            # 병렬 실행 및 결과 수집
            worker_results: Dict[str, str] = {}

            for worker_name, worker_stream in worker_tasks:
                # 워커 시작 로그
                yield WorkflowNodeExecutionEvent(
                    event_type="node_output",
                    node_id=node_id,
                    data={"chunk": f"\n\n--- {worker_name.upper()} 실행 시작 ---\n\n"},
                )

                chunks = []
                async for chunk in worker_stream:
                    chunks.append(chunk)
                    # 스트리밍 출력
                    yield WorkflowNodeExecutionEvent(
                        event_type="node_output",
                        node_id=node_id,
                        data={"chunk": chunk},
                    )

                worker_output = "".join(chunks)
                worker_results[worker_name] = worker_output

                # 워커 완료 로그
                yield WorkflowNodeExecutionEvent(
                    event_type="node_output",
                    node_id=node_id,
                    data={"chunk": f"\n\n--- {worker_name.upper()} 완료 ---\n\n"},
                )

                logger.info(
                    f"[{session_id}] Manager 노드의 워커 완료: {worker_name} "
                    f"(출력 길이: {len(worker_output)})"
                )

            # 통합 결과 생성
            integrated_output = "\n\n".join(
                f"## {worker_name.upper()} 결과\n\n{output}"
                for worker_name, output in worker_results.items()
            )

            # 실행 시간 계산
            elapsed_time = time.time() - start_time

            # 노드 완료 이벤트 (output 포함)
            complete_event = WorkflowNodeExecutionEvent(
                event_type="node_complete",
                node_id=node_id,
                data={
                    "node_type": "manager",
                    "workers_executed": list(worker_results.keys()),
                    "output_length": len(integrated_output),
                    "output": integrated_output,  # 통합 결과 포함
                },
                timestamp=datetime.now().isoformat(),
                elapsed_time=elapsed_time,
            )
            yield complete_event

            logger.info(
                f"[{session_id}] Manager 노드 완료: {node_id} "
                f"(출력 길이: {len(integrated_output)})"
            )

        except Exception as e:
            error_msg = f"Manager 노드 실행 실패: {str(e)}"
            logger.error(f"[{session_id}] {node_id}: {error_msg}", exc_info=True)

            # 실행 시간 계산 (에러 발생까지의 시간)
            elapsed_time = time.time() - start_time

            # 노드 에러 이벤트
            error_event = WorkflowNodeExecutionEvent(
                event_type="node_error",
                node_id=node_id,
                data={"error": error_msg},
                timestamp=datetime.now().isoformat(),
                elapsed_time=elapsed_time,
            )
            yield error_event

            raise

    async def execute_workflow(
        self,
        workflow: Workflow,
        initial_input: str,
        session_id: str,
    ) -> AsyncIterator[WorkflowNodeExecutionEvent]:
        """
        워크플로우 실행 (스트리밍)

        Args:
            workflow: 실행할 워크플로우
            initial_input: 초기 입력 데이터
            session_id: 세션 ID

        Yields:
            WorkflowNodeExecutionEvent: 노드 실행 이벤트

        Raises:
            ValueError: 워크플로우 설정 오류
            Exception: 노드 실행 실패
        """
        logger.info(
            f"[{session_id}] 워크플로우 실행 시작: {workflow.name} "
            f"(노드: {len(workflow.nodes)}, 엣지: {len(workflow.edges)})"
        )

        # 위상 정렬
        try:
            sorted_nodes = self._topological_sort(workflow.nodes, workflow.edges)
        except ValueError as e:
            logger.error(f"[{session_id}] 워크플로우 정렬 실패: {e}")
            raise

        logger.info(
            f"[{session_id}] 실행 순서: "
            f"{[node.id for node in sorted_nodes]}"
        )

        # 노드 출력 저장 (노드 ID → 출력)
        node_outputs: Dict[str, str] = {}

        # 각 노드 순차 실행
        for node in sorted_nodes:
            node_id = node.id

            # Input 노드 처리 (프론트엔드 전용 노드 - 스킵)
            if node.type == "input":
                # Input 노드의 initial_input을 노드 출력으로 저장
                # (다음 노드가 {{node_<id>}} 형태로 참조 가능)
                input_value = node.data.get("initial_input", initial_input)
                node_outputs[node_id] = input_value

                # 시작 이벤트
                yield WorkflowNodeExecutionEvent(
                    event_type="node_start",
                    node_id=node_id,
                    data={"agent_name": "Input"},
                    timestamp=datetime.now().isoformat(),
                )

                # 완료 이벤트 (Input 노드는 즉시 완료되므로 elapsed_time은 0에 가까움)
                yield WorkflowNodeExecutionEvent(
                    event_type="node_complete",
                    node_id=node_id,
                    data={
                        "node_type": "input",
                        "agent_name": "Input",
                        "output_length": len(input_value),
                        "output": input_value,
                    },
                    timestamp=datetime.now().isoformat(),
                    elapsed_time=0.0,
                )

                logger.info(
                    f"[{session_id}] Input 노드 완료: {node_id} "
                    f"(출력 길이: {len(input_value)})"
                )
                continue  # 다음 노드로

            # Manager 노드 vs Worker 노드 구분
            elif node.type == "manager":
                # Manager 노드 실행
                async for event in self._execute_manager_node(
                    node, node_outputs, initial_input, session_id
                ):
                    if event.event_type == "node_complete":
                        # 통합 결과 저장
                        node_outputs[node_id] = event.data.get("output", "")
                    yield event

            else:
                # Worker 노드 실행 (기존 로직)
                node_data: WorkerNodeData = node.data  # type: ignore
                agent_name = node_data.agent_name
                task_template = node_data.task_template

                # 노드 시작 시간 기록
                start_time = time.time()

                # 노드 시작 이벤트
                start_event = WorkflowNodeExecutionEvent(
                    event_type="node_start",
                    node_id=node_id,
                    data={"agent_name": agent_name},
                    timestamp=datetime.now().isoformat(),
                )
                logger.info(f"[{session_id}] 🟢 이벤트 생성: node_start (node: {node_id}, agent: {agent_name})")
                yield start_event

                try:
                    # Agent 설정 조회
                    agent_config = self._get_agent_config(agent_name)

                    # allowed_tools 오버라이드 (노드에서 지정한 경우)
                    if node_data.allowed_tools is not None:
                        agent_config = replace(agent_config, allowed_tools=node_data.allowed_tools)
                        logger.info(
                            f"[{session_id}] 노드 {node_id}: allowed_tools 오버라이드 "
                            f"({len(node_data.allowed_tools)}개 도구)"
                        )

                    # 작업 설명 렌더링
                    parent_nodes = self._get_parent_nodes(node_id, workflow.edges)
                    parent_outputs = {
                        pid: node_outputs[pid] for pid in parent_nodes
                        if pid in node_outputs
                    }

                    task_description = self._render_task_template(
                        template=task_template,
                        node_id=node_id,
                        node_outputs=parent_outputs,
                        initial_input=initial_input,
                    )

                    logger.info(
                        f"[{session_id}] 노드 실행: {node_id} ({agent_name}) "
                        f"- 작업 길이: {len(task_description)}"
                    )

                    # Worker Agent 실행
                    worker = WorkerAgent(config=agent_config)
                    node_output_chunks = []

                    # 토큰 사용량 수집을 위한 변수
                    node_token_usage: Optional[TokenUsage] = None

                    def usage_callback(usage_info: Dict[str, Any]):
                        """토큰 사용량 콜백"""
                        nonlocal node_token_usage
                        node_token_usage = TokenUsage(
                            input_tokens=usage_info.get("input_tokens", 0),
                            output_tokens=usage_info.get("output_tokens", 0),
                            total_tokens=usage_info.get("total_tokens", 0),
                        )
                        logger.debug(
                            f"[{session_id}] 💰 토큰 사용량: {node_token_usage.total_tokens} "
                            f"(입력: {node_token_usage.input_tokens}, 출력: {node_token_usage.output_tokens})"
                        )

                    async for chunk in worker.execute_task(task_description, usage_callback=usage_callback):
                        node_output_chunks.append(chunk)

                        # 노드 출력 이벤트 (스트리밍)
                        output_event = WorkflowNodeExecutionEvent(
                            event_type="node_output",
                            node_id=node_id,
                            data={"chunk": chunk},
                        )
                        logger.debug(f"[{session_id}] 📝 이벤트 생성: node_output (node: {node_id}, chunk: {len(chunk)}자)")
                        yield output_event

                    # 노드 출력 저장
                    node_output = "".join(node_output_chunks)
                    node_outputs[node_id] = node_output

                    # 실행 시간 계산
                    elapsed_time = time.time() - start_time

                    # 노드 완료 이벤트
                    complete_event = WorkflowNodeExecutionEvent(
                        event_type="node_complete",
                        node_id=node_id,
                        data={
                            "agent_name": agent_name,
                            "output_length": len(node_output),
                        },
                        timestamp=datetime.now().isoformat(),
                        elapsed_time=elapsed_time,
                        token_usage=node_token_usage,
                    )
                    logger.info(f"[{session_id}] ✅ 이벤트 생성: node_complete (node: {node_id}, agent: {agent_name})")
                    yield complete_event

                    logger.info(
                        f"[{session_id}] 노드 완료: {node_id} ({agent_name}) "
                        f"- 출력 길이: {len(node_output)}"
                    )

                except Exception as e:
                    error_msg = f"노드 실행 실패: {str(e)}"
                    logger.error(f"[{session_id}] {node_id}: {error_msg}", exc_info=True)

                    # 실행 시간 계산 (에러 발생까지의 시간)
                    elapsed_time = time.time() - start_time

                    # 노드 에러 이벤트
                    error_event = WorkflowNodeExecutionEvent(
                        event_type="node_error",
                        node_id=node_id,
                        data={"error": error_msg},
                        timestamp=datetime.now().isoformat(),
                        elapsed_time=elapsed_time,
                    )
                    logger.error(f"[{session_id}] 🔴 이벤트 생성: node_error (node: {node_id})")
                    yield error_event

                    # 워크플로우 중단
                    raise

        logger.info(f"[{session_id}] 워크플로우 실행 완료: {workflow.name}")

        # 워크플로우 완료 이벤트
        workflow_complete_event = WorkflowNodeExecutionEvent(
            event_type="workflow_complete",
            node_id="",
            data={"message": "워크플로우 실행 완료"},
            timestamp=datetime.now().isoformat(),
        )
        logger.info(f"[{session_id}] 🎉 이벤트 생성: workflow_complete")
        yield workflow_complete_event
