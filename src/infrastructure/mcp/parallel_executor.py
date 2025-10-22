"""
Parallel Executor - 병렬 작업 실행 및 의존성 관리

Task 실행 계획을 분석하여 의존성 그래프를 구축하고,
의존성 순서에 따라 Task들을 병렬로 실행합니다.
"""

from dataclasses import dataclass
from typing import List, Dict, Set, Optional, Callable, Any
from collections import defaultdict, deque
import asyncio
from datetime import datetime

from src.domain.models.parallel_task import (
    TaskExecutionPlan,
    ParallelTask,
    TaskExecutionResult
)
from src.domain.models.task import TaskStatus
from src.infrastructure.logging import get_logger

logger = get_logger(__name__, component="ParallelExecutor")


@dataclass
class ExecutionLevel:
    """실행 레벨 (의존성 순서)"""
    level: int
    tasks: List[ParallelTask]


class CircularDependencyError(Exception):
    """순환 의존성 에러"""
    pass


class ParallelExecutor:
    """
    병렬 Task 실행기

    Task 실행 계획을 분석하여 의존성 그래프를 구축하고,
    Topological Sort를 통해 Level별로 병렬 실행합니다.

    Attributes:
        task_executor: 단일 Task 실행 함수
        max_concurrent_tasks: 동시 실행 최대 개수
        continue_on_error: 에러 발생 시 계속 진행 여부

    Example:
        >>> async def execute_task(task: ParallelTask) -> str:
        ...     # Task 실행 로직
        ...     return "result"
        >>> executor = ParallelExecutor(
        ...     task_executor=execute_task,
        ...     max_concurrent_tasks=5
        ... )
        >>> result = await executor.execute(plan)
    """

    def __init__(
        self,
        task_executor: Callable[[ParallelTask], Any],
        max_concurrent_tasks: int = 5,
        continue_on_error: bool = False
    ):
        """
        ParallelExecutor 초기화

        Args:
            task_executor: 단일 Task 실행 함수
                          시그니처: async def executor(task: ParallelTask) -> str
            max_concurrent_tasks: 동시 실행 최대 개수
            continue_on_error: 에러 발생 시 계속 진행 여부
        """
        self.task_executor = task_executor
        self.max_concurrent_tasks = max_concurrent_tasks
        self.continue_on_error = continue_on_error

    def parse_plan(self, plan_json: str) -> TaskExecutionPlan:
        """
        JSON 문자열을 TaskExecutionPlan으로 파싱

        Args:
            plan_json: Planner가 생성한 JSON 문자열

        Returns:
            TaskExecutionPlan 인스턴스

        Raises:
            ValueError: JSON 파싱 실패 또는 필수 필드 누락
        """
        import re

        # JSON 추출 (```json ... ``` 마크다운 코드 블록 제거)
        json_match = re.search(r'```json\s*(.*?)\s*```', plan_json, re.DOTALL)
        if json_match:
            plan_json = json_match.group(1).strip()

        return TaskExecutionPlan.from_json(plan_json)

    def build_dependency_graph(self, tasks: List[ParallelTask]) -> Dict[str, List[str]]:
        """
        의존성 그래프 구축

        Args:
            tasks: Task 리스트

        Returns:
            {task_id: [dependent_task_ids]}
            예: {"task_1": ["task_2", "task_3"]}
                task_1 완료 후 task_2, task_3 실행 가능

        Raises:
            ValueError: 존재하지 않는 Task ID를 의존성으로 지정한 경우
        """
        graph: Dict[str, List[str]] = {task.id: [] for task in tasks}
        task_ids = set(graph.keys())

        for task in tasks:
            for dep_id in task.dependencies:
                if dep_id not in task_ids:
                    raise ValueError(
                        f"Task '{task.id}'의 의존성 '{dep_id}'가 존재하지 않습니다."
                    )
                graph[dep_id].append(task.id)

        return graph

    def detect_circular_dependency(
        self,
        tasks: List[ParallelTask]
    ) -> Optional[List[str]]:
        """
        순환 의존성 감지 (DFS 기반)

        Args:
            tasks: Task 리스트

        Returns:
            순환 경로 (예: ["task_1", "task_2", "task_1"])
            순환이 없으면 None
        """
        # 의존성 그래프 구축 (역방향)
        task_map = {task.id: task for task in tasks}
        visited = set()
        rec_stack = set()
        path = []

        def dfs(task_id: str) -> Optional[List[str]]:
            visited.add(task_id)
            rec_stack.add(task_id)
            path.append(task_id)

            task = task_map.get(task_id)
            if not task:
                return None

            for dep_id in task.dependencies:
                if dep_id not in visited:
                    cycle = dfs(dep_id)
                    if cycle:
                        return cycle
                elif dep_id in rec_stack:
                    # 순환 발견
                    cycle_start = path.index(dep_id)
                    return path[cycle_start:] + [dep_id]

            path.pop()
            rec_stack.remove(task_id)
            return None

        for task in tasks:
            if task.id not in visited:
                cycle = dfs(task.id)
                if cycle:
                    return cycle

        return None

    def topological_sort(self, tasks: List[ParallelTask]) -> List[ExecutionLevel]:
        """
        Topological Sort로 실행 레벨 생성

        Args:
            tasks: Task 리스트

        Returns:
            Level별 Task 그룹 리스트

        Raises:
            CircularDependencyError: 순환 의존성이 있는 경우
        """
        # 순환 의존성 검사
        cycle = self.detect_circular_dependency(tasks)
        if cycle:
            raise CircularDependencyError(
                f"순환 의존성이 감지되었습니다: {' -> '.join(cycle)}"
            )

        # Task ID -> Task 매핑
        task_map = {task.id: task for task in tasks}

        # 진입 차수 계산
        in_degree = {task.id: len(task.dependencies) for task in tasks}

        # Level별 Task 그룹
        levels: List[ExecutionLevel] = []
        current_level = 0

        # 진입 차수가 0인 Task들로 시작
        queue = deque([task for task in tasks if in_degree[task.id] == 0])

        while queue:
            level_tasks = list(queue)
            queue.clear()

            levels.append(ExecutionLevel(
                level=current_level,
                tasks=level_tasks
            ))

            # 현재 레벨 Task들의 dependent Task 진입 차수 감소
            for task in level_tasks:
                for other_task in tasks:
                    if task.id in other_task.dependencies:
                        in_degree[other_task.id] -= 1
                        if in_degree[other_task.id] == 0:
                            queue.append(other_task)

            current_level += 1

        # 모든 Task가 처리되었는지 확인
        processed_count = sum(len(level.tasks) for level in levels)
        if processed_count != len(tasks):
            raise CircularDependencyError(
                f"일부 Task가 처리되지 않았습니다. "
                f"순환 의존성을 확인하세요. "
                f"(처리됨: {processed_count}/{len(tasks)})"
            )

        logger.info(
            f"Topological sort completed: {len(levels)} levels",
            total_tasks=len(tasks)
        )

        return levels

    async def execute_level(
        self,
        level: int,
        tasks: List[ParallelTask],
        completed_task_ids: Set[str]
    ) -> tuple[List[ParallelTask], List[ParallelTask]]:
        """
        단일 레벨의 Task들을 병렬 실행

        Args:
            level: 실행 레벨 번호
            tasks: 실행할 Task 리스트
            completed_task_ids: 완료된 Task ID 집합

        Returns:
            (완료된 Task 리스트, 실패한 Task 리스트)
        """
        logger.info(
            f"Executing level {level}: {len(tasks)} tasks",
            task_ids=[task.id for task in tasks]
        )

        # Semaphore로 동시 실행 개수 제한
        semaphore = asyncio.Semaphore(self.max_concurrent_tasks)

        async def execute_single_task(task: ParallelTask) -> ParallelTask:
            """단일 Task 실행 (Semaphore 적용)"""
            async with semaphore:
                task.status = TaskStatus.IN_PROGRESS
                task.start_time = datetime.now()

                try:
                    logger.info(f"Starting task: {task.id}")
                    result = await self.task_executor(task)
                    task.result = result
                    task.status = TaskStatus.COMPLETED
                    logger.info(f"Completed task: {task.id}")

                except Exception as e:
                    task.error = str(e)
                    task.status = TaskStatus.FAILED
                    logger.error(f"Failed task: {task.id} - {e}")

                finally:
                    task.end_time = datetime.now()

                return task

        # 모든 Task 병렬 실행
        results = await asyncio.gather(
            *[execute_single_task(task) for task in tasks],
            return_exceptions=True
        )

        completed = []
        failed = []

        for task, result in zip(tasks, results):
            if isinstance(result, Exception):
                # Exception 발생한 경우 - task를 FAILED로 마킹하고 failed 리스트에 추가
                logger.error(f"Task {task.id} execution raised exception: {result}")
                task.status = TaskStatus.FAILED
                task.error = str(result)
                failed.append(task)
                continue

            if result.status == TaskStatus.COMPLETED:
                completed.append(result)
                completed_task_ids.add(result.id)
            else:
                failed.append(result)

        logger.info(
            f"Level {level} completed: {len(completed)} succeeded, {len(failed)} failed"
        )

        return completed, failed

    async def execute(self, plan: TaskExecutionPlan) -> TaskExecutionResult:
        """
        Task 실행 계획을 병렬 실행

        Args:
            plan: Task 실행 계획

        Returns:
            TaskExecutionResult: 실행 결과

        Raises:
            CircularDependencyError: 순환 의존성이 있는 경우
        """
        start_time = datetime.now()

        logger.info(
            f"Starting parallel execution: {len(plan.tasks)} tasks",
            task_ids=[task.id for task in plan.tasks]
        )

        # Topological Sort로 실행 레벨 생성
        try:
            levels = self.topological_sort(plan.tasks)
        except CircularDependencyError as e:
            logger.error(f"Circular dependency detected: {e}")
            raise

        completed_task_ids: Set[str] = set()
        all_completed: List[ParallelTask] = []
        all_failed: List[ParallelTask] = []

        # Level별로 순차 실행 (각 Level 내에서는 병렬)
        for exec_level in levels:
            completed, failed = await self.execute_level(
                exec_level.level,
                exec_level.tasks,
                completed_task_ids
            )

            all_completed.extend(completed)
            all_failed.extend(failed)

            # 에러 발생 시 중단 (continue_on_error=False인 경우)
            if failed and not self.continue_on_error:
                logger.warning(
                    f"Stopping execution due to failures in level {exec_level.level}"
                )
                # 남은 Task들을 FAILED로 마킹
                for remaining_level in levels[exec_level.level + 1:]:
                    for task in remaining_level.tasks:
                        task.status = TaskStatus.FAILED
                        task.error = "Skipped due to previous failures"
                        all_failed.append(task)
                break

        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds()

        # 순차 실행 시 예상 시간
        estimated_sequential_time = plan.estimate_total_time()

        # 속도 향상 배율
        speedup_factor = (
            estimated_sequential_time / total_duration
            if total_duration > 0 else 1.0
        )

        result = TaskExecutionResult(
            plan=plan,
            completed_tasks=all_completed,
            failed_tasks=all_failed,
            total_duration=total_duration,
            speedup_factor=speedup_factor
        )

        logger.info(
            f"Parallel execution finished",
            total_duration=total_duration,
            completed=len(all_completed),
            failed=len(all_failed),
            speedup_factor=speedup_factor
        )

        return result

    def rollback(self, completed_tasks: List[ParallelTask]) -> None:
        """
        완료된 Task 롤백 (파일 복원 등)

        Args:
            completed_tasks: 롤백할 Task 리스트

        Note:
            현재는 placeholder로 구현되어 있습니다.
            향후 실제 롤백 메커니즘이 필요한 경우 다음 방식으로 구현 가능합니다:

            1. **Git 기반 롤백**
               - 각 Task 시작 전 Git 커밋 또는 stash 생성
               - 롤백 시 해당 커밋으로 reset
               - 예: `git reset --hard <commit_hash>`

            2. **파일 스냅샷 롤백**
               - Task 시작 전 target_files의 백업 생성
               - 롤백 시 백업에서 복원
               - 예: `shutil.copy(backup_file, original_file)`

            3. **데이터베이스 트랜잭션 롤백**
               - 각 Task를 트랜잭션으로 관리
               - 롤백 시 ROLLBACK 실행

            현재는 Worker Agent가 Git 기반으로 동작하므로,
            필요 시 git stash 또는 branch 기반 롤백을 권장합니다.
        """
        logger.info(f"Rolling back {len(completed_tasks)} tasks")

        for task in completed_tasks:
            logger.info(f"Rollback task: {task.id} (not implemented)")

        logger.warning("Rollback completed (placeholder - no actual rollback performed)")
