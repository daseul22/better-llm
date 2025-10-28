"""
워크플로우 실행 엔진

워크플로우의 노드를 순차적으로 실행하고, 노드 간 데이터 전달을 관리합니다.
"""

import asyncio
import time
from datetime import datetime
from typing import Dict, Any, AsyncIterator, Set, List, Optional, Tuple
from collections import deque
from dataclasses import replace
from pathlib import Path

from src.domain.models import AgentConfig, Message
from src.infrastructure.config import JsonConfigLoader, get_project_root
from src.infrastructure.claude.worker_client import WorkerAgent
from src.infrastructure.claude.manager_client import ManagerAgent
from src.infrastructure.storage.custom_worker_repository import CustomWorkerRepository
from src.infrastructure.logging import get_logger, add_session_file_handlers, remove_session_file_handlers
from src.presentation.web.schemas.workflow import (
    Workflow,
    WorkflowNode,
    WorkflowEdge,
    WorkflowNodeExecutionEvent,
    WorkerNodeData,
    ManagerNodeData,
    InputNodeData,
    ConditionNodeData,
    LoopNodeData,
    MergeNodeData,
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

    def __init__(self, config_loader: JsonConfigLoader, project_path: Optional[str] = None):
        """
        WorkflowExecutor 초기화

        Args:
            config_loader: Agent 설정 로더
            project_path: 프로젝트 경로 (커스텀 워커 로드용, 옵션)
        """
        self.config_loader = config_loader
        self.project_path = project_path
        self.agent_configs = config_loader.load_agent_configs()

        # 커스텀 워커 로드 (프로젝트 경로가 주어진 경우)
        if project_path:
            try:
                custom_repo = CustomWorkerRepository(Path(project_path))
                custom_workers = custom_repo.load_custom_workers()
                self.agent_configs.extend(custom_workers)
                logger.info(f"커스텀 워커 로드 완료: {len(custom_workers)}개")
            except Exception as e:
                logger.warning(f"커스텀 워커 로드 실패: {e}")

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

        # 유효하지 않은 엣지 필터링 (존재하지 않는 노드를 참조하는 엣지 제거)
        valid_edges = []
        for edge in edges:
            if edge.source not in node_map:
                logger.warning(
                    f"엣지 {edge.id}: source 노드 '{edge.source}'가 존재하지 않습니다. 엣지를 무시합니다."
                )
                continue
            if edge.target not in node_map:
                logger.warning(
                    f"엣지 {edge.id}: target 노드 '{edge.target}'가 존재하지 않습니다. 엣지를 무시합니다."
                )
                continue
            valid_edges.append(edge)

        # Input 노드 찾기 (시작점)
        input_nodes = [node for node in nodes if node.type == "input"]
        if not input_nodes:
            raise ValueError("워크플로우에 Input 노드가 없습니다. Input 노드에서 시작해야 합니다.")

        # 여러 Input 노드가 있는 경우 모두 시작점으로 사용
        input_node_ids = [node.id for node in input_nodes]

        # 인접 리스트 (노드 ID → 자식 노드 ID 목록)
        adjacency: Dict[str, List[str]] = {node.id: [] for node in nodes}
        in_degree: Dict[str, int] = {node.id: 0 for node in nodes}

        for edge in valid_edges:
            adjacency[edge.source].append(edge.target)
            in_degree[edge.target] += 1

        # Input 노드에서 도달 가능한 노드만 필터링 (BFS)
        reachable_nodes = set(input_node_ids)
        bfs_queue = deque(input_node_ids)

        while bfs_queue:
            current_id = bfs_queue.popleft()
            for child_id in adjacency[current_id]:
                if child_id not in reachable_nodes:
                    reachable_nodes.add(child_id)
                    bfs_queue.append(child_id)

        # 도달 불가능한 노드 경고
        unreachable_nodes = [node.id for node in nodes if node.id not in reachable_nodes]
        if unreachable_nodes:
            logger.warning(
                f"Input 노드에서 도달할 수 없는 노드가 있습니다: {unreachable_nodes}. "
                "이 노드들은 실행되지 않습니다."
            )

        # 도달 가능한 노드만으로 위상 정렬 수행
        # Input 노드만 시작점으로 설정
        queue = deque(input_node_ids)
        sorted_nodes = []
        visited = set()

        while queue:
            node_id = queue.popleft()

            if node_id in visited:
                continue

            # 도달 불가능한 노드는 건너뜀
            if node_id not in reachable_nodes:
                continue

            # 모든 부모 노드가 처리되었는지 확인
            parents_ready = True
            for edge in valid_edges:
                if edge.target == node_id and edge.source in reachable_nodes:
                    if edge.source not in visited:
                        parents_ready = False
                        break

            if not parents_ready:
                # 부모 노드가 아직 처리되지 않았으면 큐 뒤로
                queue.append(node_id)
                continue

            visited.add(node_id)
            sorted_nodes.append(node_map[node_id])

            # 자식 노드를 큐에 추가
            for child_id in adjacency[node_id]:
                if child_id not in visited and child_id in reachable_nodes:
                    queue.append(child_id)

        # 순환 참조 검사 (도달 가능한 노드 기준)
        if len(sorted_nodes) != len(reachable_nodes):
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

    def _get_child_nodes(
        self, node_id: str, edges: List[WorkflowEdge]
    ) -> List[str]:
        """
        노드의 자식 노드 ID 목록 조회

        Args:
            node_id: 노드 ID
            edges: 엣지 목록

        Returns:
            List[str]: 자식 노드 ID 목록
        """
        return [edge.target for edge in edges if edge.source == node_id]

    def _check_parallel_execution(self, node: WorkflowNode) -> bool:
        """
        노드의 parallel_execution 플래그 확인

        Args:
            node: 워크플로우 노드

        Returns:
            bool: 병렬 실행 여부
        """
        if isinstance(node.data, dict):
            return node.data.get("parallel_execution", False)
        else:
            return getattr(node.data, "parallel_execution", False)

    def _compute_execution_groups(
        self, nodes: List[WorkflowNode], edges: List[WorkflowEdge]
    ) -> List[List[WorkflowNode]]:
        """
        병렬 실행 그룹 계산

        parallel_execution=True인 노드의 자식 노드들을 병렬 그룹으로 묶습니다.

        Args:
            nodes: 위상 정렬된 노드 목록
            edges: 엣지 목록

        Returns:
            List[List[WorkflowNode]]: 실행 그룹 목록 (각 그룹은 병렬 실행)
        """
        node_map = {node.id: node for node in nodes}
        processed = set()
        execution_groups = []

        for node in nodes:
            if node.id in processed:
                continue

            # parallel_execution 플래그 확인
            if self._check_parallel_execution(node):
                # 자식 노드들을 병렬 그룹으로 묶음
                child_ids = self._get_child_nodes(node.id, edges)
                parallel_group = []

                for child_id in child_ids:
                    if child_id in node_map and child_id not in processed:
                        parallel_group.append(node_map[child_id])
                        processed.add(child_id)

                # 현재 노드는 단독 실행
                execution_groups.append([node])
                processed.add(node.id)

                # 자식 노드들은 병렬 실행
                if parallel_group:
                    execution_groups.append(parallel_group)
            else:
                # 단독 실행
                execution_groups.append([node])
                processed.add(node.id)

        return execution_groups

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
            parent_node_ids = list(node_outputs.keys())
            if len(parent_node_ids) == 1:
                # 부모가 1개인 경우, 해당 노드의 출력 사용
                result = result.replace("{{parent}}", node_outputs[parent_node_ids[0]])
            elif len(parent_node_ids) == 0:
                # 부모가 없으면 빈 문자열로 치환
                result = result.replace("{{parent}}", "")
            else:
                # 부모가 여러 개인 경우, 경고 로그 및 첫 번째 부모 출력 사용
                logger.warning(
                    f"노드에 부모가 {len(parent_node_ids)}개 있습니다. "
                    f"{{{{parent}}}} 변수는 부모가 1개인 경우만 지원합니다. "
                    f"첫 번째 부모의 출력을 사용합니다: {parent_node_ids[0]}"
                )
                result = result.replace("{{parent}}", node_outputs[parent_node_ids[0]])

        return result

    def _evaluate_condition(
        self,
        condition_type: str,
        condition_value: str,
        input_text: str
    ) -> bool:
        """
        조건 평가

        Args:
            condition_type: 조건 타입 ('contains', 'regex', 'length', 'custom')
            condition_value: 조건 값
            input_text: 평가할 텍스트

        Returns:
            bool: 조건이 True인지 여부
        """
        import re

        if condition_type == "contains":
            # 텍스트 포함 검사
            return condition_value in input_text

        elif condition_type == "regex":
            # 정규표현식 매칭
            try:
                pattern = re.compile(condition_value)
                return bool(pattern.search(input_text))
            except re.error as e:
                logger.error(f"정규표현식 오류: {e}")
                return False

        elif condition_type == "length":
            # 길이 비교 (예: ">100", "<=500", "==0")
            try:
                text_length = len(input_text)
                # condition_value를 파싱하여 비교
                if condition_value.startswith(">="):
                    threshold = int(condition_value[2:].strip())
                    return text_length >= threshold
                elif condition_value.startswith("<="):
                    threshold = int(condition_value[2:].strip())
                    return text_length <= threshold
                elif condition_value.startswith(">"):
                    threshold = int(condition_value[1:].strip())
                    return text_length > threshold
                elif condition_value.startswith("<"):
                    threshold = int(condition_value[1:].strip())
                    return text_length < threshold
                elif condition_value.startswith("=="):
                    threshold = int(condition_value[2:].strip())
                    return text_length == threshold
                else:
                    # 숫자만 있는 경우 == 로 간주
                    threshold = int(condition_value.strip())
                    return text_length == threshold
            except (ValueError, IndexError) as e:
                logger.error(f"길이 조건 파싱 오류: {e}")
                return False

        elif condition_type == "custom":
            # 커스텀 Python 표현식 평가
            try:
                # 안전한 평가를 위해 제한된 네임스페이스 사용
                namespace = {
                    "output": input_text,
                    "len": len,
                    "str": str,
                    "int": int,
                    "float": float,
                }
                result = eval(condition_value, {"__builtins__": {}}, namespace)
                return bool(result)
            except Exception as e:
                logger.error(f"커스텀 조건 평가 오류: {e}")
                return False

        else:
            logger.warning(f"알 수 없는 조건 타입: {condition_type}")
            return False

    async def _execute_condition_node(
        self,
        node: WorkflowNode,
        node_outputs: Dict[str, str],
        edges: List[WorkflowEdge],
        session_id: str,
    ) -> tuple[str, str]:
        """
        조건 분기 노드 실행

        Args:
            node: 조건 노드
            node_outputs: 이전 노드 출력들
            edges: 엣지 목록 (분기 경로 확인용)
            session_id: 세션 ID

        Returns:
            tuple[str, str]: (다음 실행할 노드 ID, 조건 평가 결과 텍스트)

        Raises:
            ValueError: 부모 노드가 없거나 분기 경로가 없는 경우
        """
        node_id = node.id
        node_data: ConditionNodeData = node.data  # type: ignore

        logger.info(
            f"[{session_id}] 조건 노드 실행: {node_id} "
            f"(타입: {node_data.condition_type}, 값: {node_data.condition_value})"
        )

        # 부모 노드 출력 가져오기
        parent_nodes = self._get_parent_nodes(node_id, edges)
        if not parent_nodes:
            raise ValueError(f"조건 노드 {node_id}에 부모 노드가 없습니다")

        # 첫 번째 부모 노드의 출력 사용
        parent_id = parent_nodes[0]
        parent_output = node_outputs.get(parent_id, "")

        # 조건 평가
        condition_result = self._evaluate_condition(
            node_data.condition_type,
            node_data.condition_value,
            parent_output
        )

        logger.info(
            f"[{session_id}] 조건 평가 결과: {condition_result} "
            f"(입력 길이: {len(parent_output)})"
        )

        # 분기 경로 결정 (엣지의 sourceHandle을 사용)
        # sourceHandle이 "true"인 엣지 → True 경로
        # sourceHandle이 "false"인 엣지 → False 경로
        next_node_id = None
        for edge in edges:
            if edge.source == node_id:
                if condition_result and edge.sourceHandle == "true":
                    next_node_id = edge.target
                    break
                elif not condition_result and edge.sourceHandle == "false":
                    next_node_id = edge.target
                    break

        if next_node_id is None:
            branch_type = "true" if condition_result else "false"
            raise ValueError(
                f"조건 노드 {node_id}의 {branch_type} 분기 경로가 없습니다. "
                f"sourceHandle이 '{branch_type}'인 엣지를 추가해주세요."
            )

        # 조건 결과를 텍스트로 변환
        result_text = f"조건 평가 결과: {condition_result}\n분기: {next_node_id}"

        return next_node_id, result_text

    async def _execute_loop_node(
        self,
        node: WorkflowNode,
        node_outputs: Dict[str, str],
        edges: List[WorkflowEdge],
        nodes: List[WorkflowNode],
        initial_input: str,
        session_id: str,
        project_path: Optional[str] = None,
    ) -> AsyncIterator[WorkflowNodeExecutionEvent]:
        """
        반복 노드 실행

        Args:
            node: 반복 노드
            node_outputs: 이전 노드 출력들
            edges: 엣지 목록
            nodes: 노드 목록
            initial_input: 초기 입력
            session_id: 세션 ID
            project_path: 프로젝트 디렉토리 경로 (CLAUDE.md 로드용)

        Yields:
            WorkflowNodeExecutionEvent: 노드 실행 이벤트
        """
        node_id = node.id
        node_data: LoopNodeData = node.data  # type: ignore

        logger.info(
            f"[{session_id}] 반복 노드 시작: {node_id} "
            f"(최대 반복: {node_data.max_iterations}, 조건: {node_data.loop_condition})"
        )

        # 노드 시작 시간 기록
        start_time = time.time()

        # 노드 시작 이벤트
        yield WorkflowNodeExecutionEvent(
            event_type="node_start",
            node_id=node_id,
            data={
                "node_type": "loop",
                "max_iterations": node_data.max_iterations,
            },
            timestamp=datetime.now().isoformat(),
        )

        try:
            # 루프 본문 노드 찾기 (loop 노드의 자식 노드들)
            loop_body_node_ids = [
                edge.target for edge in edges if edge.source == node_id
            ]

            if not loop_body_node_ids:
                raise ValueError(f"반복 노드 {node_id}에 자식 노드가 없습니다")

            iteration = 0
            loop_output_history = []

            while iteration < node_data.max_iterations:
                iteration += 1

                yield WorkflowNodeExecutionEvent(
                    event_type="node_output",
                    node_id=node_id,
                    data={"chunk": f"\n\n--- 반복 {iteration}회차 시작 ---\n\n"},
                )

                logger.info(f"[{session_id}] 반복 노드 {node_id}: {iteration}회차 실행")

                # 루프 본문 노드 실행 (첫 번째 자식 노드만)
                # TODO: 여러 노드를 순서대로 실행하려면 위상 정렬 필요
                body_node_id = loop_body_node_ids[0]
                body_node = next((n for n in nodes if n.id == body_node_id), None)

                if body_node is None:
                    raise ValueError(f"루프 본문 노드 {body_node_id}를 찾을 수 없습니다")

                # 루프 본문이 Worker 노드인 경우만 지원 (현재 구현)
                if body_node.type != "worker":
                    raise ValueError(
                        f"반복 노드는 현재 Worker 노드만 지원합니다 (노드: {body_node_id}, 타입: {body_node.type})"
                    )

                # Worker 노드 실행 (간소화된 버전)
                body_node_data: WorkerNodeData = body_node.data  # type: ignore
                agent_name = body_node_data.agent_name
                task_template = body_node_data.task_template

                # 작업 설명 렌더링 (이전 반복 결과 포함)
                task_description = self._render_task_template(
                    template=task_template,
                    node_id=body_node_id,
                    node_outputs=node_outputs,
                    initial_input=initial_input,
                )

                # Worker Agent 실행
                agent_config = self._get_agent_config(agent_name)
                worker = WorkerAgent(config=agent_config, project_dir=project_path)
                body_output_chunks = []

                async for chunk in worker.execute_task(task_description):
                    body_output_chunks.append(chunk)
                    yield WorkflowNodeExecutionEvent(
                        event_type="node_output",
                        node_id=node_id,
                        data={"chunk": chunk},
                    )

                body_output = "".join(body_output_chunks)
                loop_output_history.append(body_output)

                # 루프 본문 출력을 node_outputs에 저장 (다음 반복에서 사용)
                node_outputs[body_node_id] = body_output

                yield WorkflowNodeExecutionEvent(
                    event_type="node_output",
                    node_id=node_id,
                    data={"chunk": f"\n\n--- 반복 {iteration}회차 완료 ---\n\n"},
                )

                # 조건 평가 (종료 조건 확인)
                condition_met = self._evaluate_condition(
                    node_data.loop_condition_type,
                    node_data.loop_condition,
                    body_output
                )

                logger.info(
                    f"[{session_id}] 반복 노드 {node_id}: 조건 평가 결과 = {condition_met}"
                )

                if condition_met:
                    logger.info(
                        f"[{session_id}] 반복 노드 {node_id}: 조건 만족, 루프 종료"
                    )
                    break

            # 실행 시간 계산
            elapsed_time = time.time() - start_time

            # 통합 출력 (모든 반복 결과 결합)
            integrated_output = "\n\n---\n\n".join(loop_output_history)

            # 노드 완료 이벤트
            yield WorkflowNodeExecutionEvent(
                event_type="node_complete",
                node_id=node_id,
                data={
                    "node_type": "loop",
                    "iterations": iteration,
                    "output": integrated_output,
                },
                timestamp=datetime.now().isoformat(),
                elapsed_time=elapsed_time,
            )

            logger.info(
                f"[{session_id}] 반복 노드 완료: {node_id} ({iteration}회 반복)"
            )

        except Exception as e:
            error_msg = f"반복 노드 실행 실패: {str(e)}"
            logger.error(f"[{session_id}] {node_id}: {error_msg}", exc_info=True)

            elapsed_time = time.time() - start_time

            yield WorkflowNodeExecutionEvent(
                event_type="node_error",
                node_id=node_id,
                data={"error": error_msg},
                timestamp=datetime.now().isoformat(),
                elapsed_time=elapsed_time,
            )

            raise

    async def _execute_merge_node(
        self,
        node: WorkflowNode,
        node_outputs: Dict[str, str],
        edges: List[WorkflowEdge],
        session_id: str,
    ) -> str:
        """
        병합 노드 실행

        Args:
            node: 병합 노드
            node_outputs: 이전 노드 출력들
            edges: 엣지 목록
            session_id: 세션 ID

        Returns:
            str: 병합된 출력
        """
        node_id = node.id
        node_data: MergeNodeData = node.data  # type: ignore

        logger.info(
            f"[{session_id}] 병합 노드 실행: {node_id} "
            f"(전략: {node_data.merge_strategy})"
        )

        # 부모 노드 출력들 수집
        parent_nodes = self._get_parent_nodes(node_id, edges)
        if not parent_nodes:
            raise ValueError(f"병합 노드 {node_id}에 부모 노드가 없습니다")

        parent_outputs = []
        for pid in parent_nodes:
            if pid not in node_outputs:
                logger.warning(
                    f"[{session_id}] 병합 노드 {node_id}: "
                    f"부모 노드 '{pid}'의 출력이 없습니다. 빈 문자열을 사용합니다."
                )
            parent_outputs.append(node_outputs.get(pid, ""))

        # 병합 전략에 따라 출력 생성
        if node_data.merge_strategy == "concatenate":
            # 모든 출력을 구분자로 결합
            merged_output = node_data.separator.join(parent_outputs)

        elif node_data.merge_strategy == "first":
            # 첫 번째 출력만 사용
            merged_output = parent_outputs[0] if parent_outputs else ""

        elif node_data.merge_strategy == "last":
            # 마지막 출력만 사용
            merged_output = parent_outputs[-1] if parent_outputs else ""

        elif node_data.merge_strategy == "custom":
            # 커스텀 템플릿 사용
            if node_data.custom_template:
                merged_output = node_data.custom_template
                for i, output in enumerate(parent_outputs):
                    merged_output = merged_output.replace(f"{{{{branch_{i+1}}}}}", output)
            else:
                # 템플릿이 없으면 concatenate로 폴백
                merged_output = node_data.separator.join(parent_outputs)

        else:
            logger.warning(
                f"알 수 없는 병합 전략: {node_data.merge_strategy}, "
                "concatenate로 폴백합니다"
            )
            merged_output = node_data.separator.join(parent_outputs)

        logger.info(
            f"[{session_id}] 병합 노드 완료: {node_id} "
            f"(입력: {len(parent_outputs)}개, 출력 길이: {len(merged_output)})"
        )

        return merged_output

    async def _execute_manager_node(
        self,
        node: WorkflowNode,
        node_outputs: Dict[str, str],
        initial_input: str,
        session_id: str,
        project_path: Optional[str] = None,
    ) -> AsyncIterator[WorkflowNodeExecutionEvent]:
        """
        Manager 노드 실행 (병렬 워커 호출)

        Manager 노드는 등록된 워커들을 병렬로 실행하여 결과를 통합합니다.

        Args:
            node: Manager 노드
            node_outputs: 이전 노드 출력들
            initial_input: 초기 입력
            session_id: 세션 ID
            project_path: 프로젝트 디렉토리 경로 (CLAUDE.md 로드용)

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
                "available_workers": available_workers,
                "input": task_description,  # 노드 입력 추가 (디버깅용)
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
                worker = WorkerAgent(config=worker_config, project_dir=project_path)
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

    async def _execute_single_node(
        self,
        node: WorkflowNode,
        node_outputs: Dict[str, str],
        initial_input: str,
        session_id: str,
        edges: List[WorkflowEdge],
        all_nodes: List[WorkflowNode],
        project_path: Optional[str] = None,
    ) -> AsyncIterator[WorkflowNodeExecutionEvent]:
        """
        단일 노드 실행 (모든 노드 타입 지원)

        Args:
            node: 실행할 노드
            node_outputs: 이전 노드 출력들
            initial_input: 초기 입력
            session_id: 세션 ID
            edges: 엣지 목록
            all_nodes: 모든 노드 목록
            project_path: 프로젝트 디렉토리 경로

        Yields:
            WorkflowNodeExecutionEvent: 노드 실행 이벤트
        """
        node_id = node.id

        # Input 노드 처리
        if node.type == "input":
            if isinstance(node.data, InputNodeData):
                input_value = node.data.initial_input
            elif isinstance(node.data, dict):
                input_value = node.data.get("initial_input", initial_input)
            else:
                input_value = initial_input
            node_outputs[node_id] = input_value

            yield WorkflowNodeExecutionEvent(
                event_type="node_start",
                node_id=node_id,
                data={
                    "agent_name": "Input",
                    "input": input_value,  # 노드 입력 추가 (디버깅용)
                },
                timestamp=datetime.now().isoformat(),
            )

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
            return

        # Manager 노드
        elif node.type == "manager":
            async for event in self._execute_manager_node(
                node, node_outputs, initial_input, session_id, project_path
            ):
                if event.event_type == "node_complete":
                    node_outputs[node_id] = event.data.get("output", "")
                yield event

        # Condition 노드
        elif node.type == "condition":
            start_time = time.time()

            yield WorkflowNodeExecutionEvent(
                event_type="node_start",
                node_id=node_id,
                data={"node_type": "condition"},
                timestamp=datetime.now().isoformat(),
            )

            try:
                next_node_id, result_text = await self._execute_condition_node(
                    node, node_outputs, edges, session_id
                )

                node_outputs[node_id] = result_text
                elapsed_time = time.time() - start_time

                yield WorkflowNodeExecutionEvent(
                    event_type="node_complete",
                    node_id=node_id,
                    data={
                        "node_type": "condition",
                        "next_node": next_node_id,
                        "output": result_text,
                    },
                    timestamp=datetime.now().isoformat(),
                    elapsed_time=elapsed_time,
                )

                logger.info(
                    f"[{session_id}] 조건 노드 완료: {node_id} → {next_node_id}"
                )

            except Exception as e:
                error_msg = f"조건 노드 실행 실패: {str(e)}"
                logger.error(f"[{session_id}] {node_id}: {error_msg}", exc_info=True)

                elapsed_time = time.time() - start_time

                yield WorkflowNodeExecutionEvent(
                    event_type="node_error",
                    node_id=node_id,
                    data={"error": error_msg},
                    timestamp=datetime.now().isoformat(),
                    elapsed_time=elapsed_time,
                )

                raise

        # Loop 노드
        elif node.type == "loop":
            async for event in self._execute_loop_node(
                node, node_outputs, edges, all_nodes,
                initial_input, session_id, project_path
            ):
                if event.event_type == "node_complete":
                    node_outputs[node_id] = event.data.get("output", "")
                yield event

        # Merge 노드
        elif node.type == "merge":
            start_time = time.time()

            yield WorkflowNodeExecutionEvent(
                event_type="node_start",
                node_id=node_id,
                data={"node_type": "merge"},
                timestamp=datetime.now().isoformat(),
            )

            try:
                merged_output = await self._execute_merge_node(
                    node, node_outputs, edges, session_id
                )

                node_outputs[node_id] = merged_output
                elapsed_time = time.time() - start_time

                yield WorkflowNodeExecutionEvent(
                    event_type="node_complete",
                    node_id=node_id,
                    data={
                        "node_type": "merge",
                        "output_length": len(merged_output),
                        "output": merged_output,
                    },
                    timestamp=datetime.now().isoformat(),
                    elapsed_time=elapsed_time,
                )

                logger.info(
                    f"[{session_id}] 병합 노드 완료: {node_id} "
                    f"(출력 길이: {len(merged_output)})"
                )

            except Exception as e:
                error_msg = f"병합 노드 실행 실패: {str(e)}"
                logger.error(f"[{session_id}] {node_id}: {error_msg}", exc_info=True)

                elapsed_time = time.time() - start_time

                yield WorkflowNodeExecutionEvent(
                    event_type="node_error",
                    node_id=node_id,
                    data={"error": error_msg},
                    timestamp=datetime.now().isoformat(),
                    elapsed_time=elapsed_time,
                )

                raise

        # Worker 노드
        else:
            if isinstance(node.data, dict):
                agent_name = node.data.get("agent_name")
                task_template = node.data.get("task_template")
                allowed_tools_override = node.data.get("allowed_tools")
                thinking_override = node.data.get("thinking")

                if not agent_name:
                    raise ValueError(f"노드 {node_id}: agent_name이 지정되지 않았습니다")
                if not task_template:
                    raise ValueError(f"노드 {node_id}: task_template이 지정되지 않았습니다")
            else:
                node_data: WorkerNodeData = node.data  # type: ignore
                agent_name = node_data.agent_name
                task_template = node_data.task_template
                allowed_tools_override = node_data.allowed_tools
                thinking_override = node_data.thinking

            start_time = time.time()

            # 먼저 task_description 생성 (입력 저장용)
            agent_config = self._get_agent_config(agent_name)

            if allowed_tools_override is not None:
                agent_config = replace(agent_config, allowed_tools=allowed_tools_override)
                logger.info(
                    f"[{session_id}] 노드 {node_id}: allowed_tools 오버라이드 "
                    f"({len(allowed_tools_override)}개 도구)"
                )

            if thinking_override is not None:
                agent_config = replace(agent_config, thinking=thinking_override)
                logger.info(
                    f"[{session_id}] 노드 {node_id}: thinking 모드 오버라이드 "
                    f"(thinking={thinking_override})"
                )

            parent_nodes = self._get_parent_nodes(node_id, edges)
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

            # node_start 이벤트에 입력 포함
            start_event = WorkflowNodeExecutionEvent(
                event_type="node_start",
                node_id=node_id,
                data={
                    "agent_name": agent_name,
                    "input": task_description,  # 노드 입력 추가 (디버깅용)
                },
                timestamp=datetime.now().isoformat(),
            )
            logger.info(f"[{session_id}] 🟢 이벤트 생성: node_start (node: {node_id}, agent: {agent_name})")
            yield start_event

            try:

                logger.info(
                    f"[{session_id}] 노드 실행: {node_id} ({agent_name}) "
                    f"- 작업 길이: {len(task_description)}"
                )

                worker = WorkerAgent(config=agent_config, project_dir=project_path)
                node_output_chunks = []
                node_token_usage: Optional[TokenUsage] = None

                def usage_callback(usage_info: Dict[str, Any]):
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

                    output_event = WorkflowNodeExecutionEvent(
                        event_type="node_output",
                        node_id=node_id,
                        data={"chunk": chunk},
                    )
                    logger.debug(f"[{session_id}] 📝 이벤트 생성: node_output (node: {node_id}, chunk: {len(chunk)}자)")
                    yield output_event

                node_output = "".join(node_output_chunks)
                node_outputs[node_id] = node_output
                elapsed_time = time.time() - start_time

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

                elapsed_time = time.time() - start_time

                error_event = WorkflowNodeExecutionEvent(
                    event_type="node_error",
                    node_id=node_id,
                    data={"error": error_msg},
                    timestamp=datetime.now().isoformat(),
                    elapsed_time=elapsed_time,
                )
                logger.error(f"[{session_id}] 🔴 이벤트 생성: node_error (node: {node_id})")
                yield error_event

                raise

    async def _execute_node_and_queue_events(
        self,
        node: WorkflowNode,
        node_outputs: Dict[str, str],
        initial_input: str,
        session_id: str,
        edges: List[WorkflowEdge],
        all_nodes: List[WorkflowNode],
        event_queue: asyncio.Queue,
        project_path: Optional[str] = None,
    ) -> None:
        """
        단일 노드를 실행하고 모든 이벤트를 큐에 전송

        Args:
            node: 실행할 노드
            node_outputs: 노드 출력 딕셔너리 (공유)
            initial_input: 초기 입력
            session_id: 세션 ID
            edges: 엣지 목록
            all_nodes: 모든 노드 목록
            event_queue: 이벤트를 전송할 큐
            project_path: 프로젝트 경로
        """
        try:
            async for event in self._execute_single_node(
                node, node_outputs, initial_input, session_id,
                edges, all_nodes, project_path
            ):
                await event_queue.put(event)
        except Exception as e:
            # 에러 발생 시 에러를 큐에 전달
            logger.error(
                f"[{session_id}] 노드 {node.id} 실행 중 에러: {str(e)}",
                exc_info=True
            )
            await event_queue.put(e)  # 예외를 큐에 넣음

    async def execute_workflow(
        self,
        workflow: Workflow,
        initial_input: str,
        session_id: str,
        project_path: Optional[str] = None,
    ) -> AsyncIterator[WorkflowNodeExecutionEvent]:
        """
        워크플로우 실행 (스트리밍, 병렬 실행 지원)

        Args:
            workflow: 실행할 워크플로우
            initial_input: 초기 입력 데이터
            session_id: 세션 ID
            project_path: 프로젝트 디렉토리 경로 (세션별 로그 저장용)

        Yields:
            WorkflowNodeExecutionEvent: 노드 실행 이벤트

        Raises:
            ValueError: 워크플로우 설정 오류
            Exception: 노드 실행 실패
        """
        # 세션별 파일 핸들러 추가
        add_session_file_handlers(session_id, project_path)

        # 실행 중인 병렬 태스크 추적 (취소 시 정리용)
        running_tasks: List[asyncio.Task] = []

        try:
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

            # 실행 그룹 계산 (병렬 실행 그룹 포함)
            execution_groups = self._compute_execution_groups(sorted_nodes, workflow.edges)

            logger.info(
                f"[{session_id}] 실행 그룹: {len(execution_groups)}개 "
                f"(병렬 그룹: {sum(1 for g in execution_groups if len(g) > 1)}개)"
            )

            # 노드 출력 저장 (노드 ID → 출력)
            node_outputs: Dict[str, str] = {}

            # 실행 그룹별로 처리 (병렬 실행 지원)
            for group_idx, group in enumerate(execution_groups):
                group_node_ids = [node.id for node in group]

                if len(group) == 1:
                    # 단독 실행
                    node = group[0]
                    logger.info(
                        f"[{session_id}] 그룹 {group_idx + 1}/{len(execution_groups)}: "
                        f"노드 {node.id} 단독 실행"
                    )

                    async for event in self._execute_single_node(
                        node, node_outputs, initial_input, session_id,
                        workflow.edges, workflow.nodes, project_path
                    ):
                        yield event

                else:
                    # 병렬 실행 (실시간 이벤트 스트리밍)
                    logger.info(
                        f"[{session_id}] 그룹 {group_idx + 1}/{len(execution_groups)}: "
                        f"{len(group)}개 노드 병렬 실행 ({group_node_ids})"
                    )

                    # 이벤트 큐 생성
                    event_queue: asyncio.Queue = asyncio.Queue()

                    # 병렬 실행 태스크 생성
                    tasks = [
                        asyncio.create_task(
                            self._execute_node_and_queue_events(
                                node, node_outputs, initial_input, session_id,
                                workflow.edges, workflow.nodes, event_queue, project_path
                            )
                        )
                        for node in group
                    ]

                    # 실행 중인 태스크 추적에 추가
                    running_tasks.extend(tasks)

                    # 완료된 노드 수 추적
                    completed_nodes = 0
                    total_nodes = len(group)

                    # 실시간으로 이벤트를 스트리밍
                    while completed_nodes < total_nodes:
                        # 큐에서 이벤트 가져오기 (타임아웃 1초)
                        try:
                            event_or_exception = await asyncio.wait_for(
                                event_queue.get(), timeout=1.0
                            )

                            # 예외인 경우
                            if isinstance(event_or_exception, Exception):
                                error_msg = f"병렬 실행 중 노드 실패: {str(event_or_exception)}"
                                logger.error(f"[{session_id}] {error_msg}", exc_info=event_or_exception)

                                # 에러 이벤트 생성
                                yield WorkflowNodeExecutionEvent(
                                    event_type="node_error",
                                    node_id="unknown",
                                    data={"error": error_msg},
                                    timestamp=datetime.now().isoformat(),
                                )

                                # 모든 태스크 취소
                                for task in tasks:
                                    task.cancel()

                                raise event_or_exception

                            # 정상 이벤트인 경우
                            event = event_or_exception
                            yield event

                            # 노드 완료/에러 이벤트 카운팅
                            if event.event_type in ["node_complete", "node_error"]:
                                completed_nodes += 1
                                logger.info(
                                    f"[{session_id}] 병렬 노드 완료: {event.node_id} "
                                    f"({completed_nodes}/{total_nodes})"
                                )

                        except asyncio.TimeoutError:
                            # 타임아웃 시 태스크 상태 확인
                            done_tasks = [t for t in tasks if t.done()]
                            if done_tasks:
                                # 완료된 태스크가 있으면 다시 시도
                                continue
                            else:
                                # 모든 태스크가 아직 실행 중
                                continue

                    # 모든 태스크 완료 대기 (정리 작업)
                    await asyncio.gather(*tasks, return_exceptions=True)

                    logger.info(
                        f"[{session_id}] 병렬 그룹 완료: {group_node_ids}"
                    )

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

        except asyncio.CancelledError:
            # 워크플로우 취소 요청 시
            logger.warning(
                f"[{session_id}] 워크플로우 취소 요청 받음. "
                f"실행 중인 태스크 {len(running_tasks)}개 정리 중..."
            )

            # 모든 실행 중인 병렬 태스크 취소
            for task in running_tasks:
                if not task.done():
                    task.cancel()

            # 취소된 태스크 대기 (정리)
            if running_tasks:
                await asyncio.gather(*running_tasks, return_exceptions=True)

            logger.info(f"[{session_id}] 모든 태스크 정리 완료")

            # 취소 이벤트 생성
            cancel_event = WorkflowNodeExecutionEvent(
                event_type="workflow_cancelled",
                node_id="",
                data={"message": "워크플로우가 취소되었습니다"},
                timestamp=datetime.now().isoformat(),
            )
            yield cancel_event

            # CancelledError 재발생 (상위 호출자에게 전파)
            raise

        finally:
            # 세션별 파일 핸들러 제거 (메모리 누수 방지)
            remove_session_file_handlers(session_id)
