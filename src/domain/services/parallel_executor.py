"""
병렬 Task 실행 엔진

ParallelTaskExecutor: 의존성 그래프 기반 병렬 실행
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Set, Optional, Callable, Awaitable
from collections import deque

from ..models.parallel_task import (
    ParallelTask,
    TaskExecutionPlan,
    TaskExecutionResult,
)
from ..models.task import TaskStatus
from ...infrastructure.logging import get_logger

logger = get_logger(__name__, component="ParallelExecutor")


class ParallelTaskExecutor:
    """
    병렬 Task 실행 엔진

    의존성 그래프를 기반으로 Task들을 레벨별로 병렬 실행합니다.

    Algorithm:
        1. 의존성 그래프에서 실행 레벨 계산 (Topological Sort)
        2. 각 레벨의 Task들을 asyncio.gather()로 병렬 실행
        3. 한 레벨 완료 후 다음 레벨 진행
        4. 에러 발생 시 의존하는 하위 Task 자동 취소

    Example:
        ```python
        executor = ParallelTaskExecutor(task_executor_func)
        result = await executor.execute(plan)

        print(f"Success rate: {result.success_rate * 100}%")
        print(f"Speedup: {result.speedup_factor}x")
        ```
    """

    def __init__(
        self,
        task_executor: Callable[[ParallelTask], Awaitable[str]],
        max_concurrent_tasks: int = 5
    ):
        """
        초기화

        Args:
            task_executor (Callable[[ParallelTask], Awaitable[str]]):
                Task 실행 함수 (예: Coder Agent 호출)
            max_concurrent_tasks (int): 동시 실행 최대 Task 수
        """
        self.task_executor = task_executor
        self.max_concurrent_tasks = max_concurrent_tasks

    async def execute(self, plan: TaskExecutionPlan) -> TaskExecutionResult:
        """
        실행 계획을 기반으로 Task들을 병렬 실행

        Args:
            plan: Planner Agent가 생성한 실행 계획

        Returns:
            실행 결과 (완료/실패 Task, 실행 시간 등)
        """
        logger.info(f"병렬 실행 시작: {len(plan.tasks)}개 Task")

        start_time = datetime.now()
        completed_tasks: List[ParallelTask] = []
        failed_tasks: List[ParallelTask] = []

        # 1. 실행 레벨 계산
        levels = self._compute_execution_levels(plan)
        logger.info(f"실행 레벨 수: {len(levels)}")

        # 2. 레벨별 순차 실행 (각 레벨 내에서는 병렬)
        completed_task_ids: Set[str] = set()

        for level_idx, level_task_ids in enumerate(levels):
            logger.info(
                f"Level {level_idx + 1}/{len(levels)} 실행 시작: "
                f"{len(level_task_ids)}개 Task"
            )

            # 해당 레벨의 Task들 가져오기
            level_tasks = [plan.get_task(tid) for tid in level_task_ids]
            level_tasks = [t for t in level_tasks if t is not None]

            # 병렬 실행
            results = await self._execute_task_batch(level_tasks)

            # 결과 분류
            for task, success in results.items():
                if success:
                    completed_tasks.append(task)
                    completed_task_ids.add(task.id)
                else:
                    failed_tasks.append(task)
                    # 실패한 Task에 의존하는 하위 Task들을 취소
                    remaining = levels[level_idx + 1:]
                    self._cancel_dependent_tasks(task.id, plan, remaining)

            success_count = sum(1 for r in results.values() if r)
            fail_count = sum(1 for r in results.values() if not r)
            logger.info(
                f"Level {level_idx + 1} 완료: "
                f"성공 {success_count}개, 실패 {fail_count}개"
            )

        # 3. 결과 생성
        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds()

        # 실제 실행 시간 기반 계산
        actual_sequential_time = sum(
            task.duration_seconds() or task.estimated_time
            for task in completed_tasks + failed_tasks
        )
        speedup_factor = (
            actual_sequential_time / total_duration
            if total_duration > 0
            else 1.0
        )

        result = TaskExecutionResult(
            plan=plan,
            completed_tasks=completed_tasks,
            failed_tasks=failed_tasks,
            total_duration=total_duration,
            speedup_factor=speedup_factor,
        )

        logger.info(
            f"병렬 실행 완료: "
            f"성공 {len(completed_tasks)}개, 실패 {len(failed_tasks)}개, "
            f"실행 시간 {total_duration:.1f}초, "
            f"속도 향상 {speedup_factor:.2f}x"
        )

        return result

    def _compute_execution_levels(
        self,
        plan: TaskExecutionPlan
    ) -> List[List[str]]:
        """
        의존성 그래프에서 실행 레벨 계산 (Topological Sort)

        레벨 0: 의존성이 없는 Task들
        레벨 1: 레벨 0이 완료되어야 실행 가능한 Task들
        레벨 2: 레벨 1이 완료되어야 실행 가능한 Task들
        ...

        Args:
            plan: 실행 계획

        Returns:
            레벨별 Task ID 리스트
            예: [["task_1", "task_3"], ["task_2"], ["task_4"]]
        """
        # 각 Task의 진입 차수 (indegree) 계산
        indegree: Dict[str, int] = {
            task.id: len(task.dependencies) for task in plan.tasks
        }

        # 역방향 그래프 (task_id → 이 Task에 의존하는 Task들)
        reverse_graph = plan.build_dependency_graph()

        # BFS로 레벨별 Task 계산
        levels: List[List[str]] = []
        queue: deque[str] = deque()

        # 레벨 0: 의존성이 없는 Task들
        for task_id, degree in indegree.items():
            if degree == 0:
                queue.append(task_id)

        while queue:
            # 현재 레벨의 모든 Task
            current_level = list(queue)
            queue.clear()
            levels.append(current_level)

            # 다음 레벨 Task 찾기
            for task_id in current_level:
                # 이 Task에 의존하는 Task들의 indegree 감소
                for dependent_id in reverse_graph.get(task_id, []):
                    indegree[dependent_id] -= 1
                    if indegree[dependent_id] == 0:
                        queue.append(dependent_id)

        # 순환 의존성 체크
        if sum(len(level) for level in levels) != len(plan.tasks):
            missing_tasks = len(plan.tasks) - sum(len(level) for level in levels)
            logger.error(
                f"순환 의존성 감지! {missing_tasks}개 Task가 실행되지 않습니다."
            )
            raise ValueError(
                f"순환 의존성이 감지되었습니다. "
                f"{missing_tasks}개 Task가 의존성 그래프에서 제외되었습니다."
            )

        return levels

    async def _execute_task_batch(
        self,
        tasks: List[ParallelTask]
    ) -> Dict[ParallelTask, bool]:
        """
        한 레벨의 Task들을 병렬 실행

        Args:
            tasks: 실행할 Task 리스트

        Returns:
            {task: success} 딕셔너리
        """
        # Task를 max_concurrent_tasks 단위로 나누어 실행
        results: Dict[ParallelTask, bool] = {}

        for i in range(0, len(tasks), self.max_concurrent_tasks):
            batch = tasks[i:i + self.max_concurrent_tasks]

            # 병렬 실행 (asyncio.gather with return_exceptions=True)
            coros = [self._execute_single_task(task) for task in batch]
            batch_results = await asyncio.gather(*coros, return_exceptions=True)

            # 결과 매핑
            for task, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    task.status = TaskStatus.FAILED
                    task.error = str(result)
                    results[task] = False
                    logger.error(f"Task {task.id} 실패: {result}")
                else:
                    task.status = TaskStatus.COMPLETED
                    task.result = result
                    results[task] = True
                    logger.info(f"Task {task.id} 완료")

        return results

    async def _execute_single_task(self, task: ParallelTask) -> str:
        """
        단일 Task 실행

        Args:
            task: 실행할 Task

        Returns:
            Task 실행 결과 (Coder Agent 출력)

        Raises:
            Exception: Task 실행 실패 시
        """
        task.status = TaskStatus.IN_PROGRESS
        task.start_time = datetime.now()

        logger.debug(f"Task {task.id} 실행 시작: {task.description}")

        try:
            # task_executor 호출 (예: Coder Agent)
            result = await self.task_executor(task)

            task.end_time = datetime.now()
            logger.debug(
                f"Task {task.id} 완료 (소요 시간: {task.duration_seconds():.1f}초)"
            )

            return result

        except Exception as e:
            task.end_time = datetime.now()
            task.status = TaskStatus.FAILED
            task.error = str(e)
            logger.error(f"Task {task.id} 실패: {e}", exc_info=True)
            raise

    def _cancel_dependent_tasks(
        self,
        failed_task_id: str,
        plan: TaskExecutionPlan,
        remaining_levels: List[List[str]]
    ) -> None:
        """
        실패한 Task에 의존하는 모든 하위 Task 취소

        Args:
            failed_task_id (str): 실패한 Task ID
            plan (TaskExecutionPlan): 실행 계획
            remaining_levels (List[List[str]]): 남은 실행 레벨들
        """
        reverse_graph = plan.build_dependency_graph()

        # BFS로 의존하는 모든 Task 찾기
        queue = deque([failed_task_id])
        cancelled_ids = set()

        while queue:
            current_id = queue.popleft()
            for dependent_id in reverse_graph.get(current_id, []):
                if dependent_id not in cancelled_ids:
                    task = plan.get_task(dependent_id)
                    if task and task.status != TaskStatus.COMPLETED:
                        task.status = TaskStatus.CANCELLED
                        task.error = (
                            f"의존성 Task '{failed_task_id}' 실패로 인한 취소"
                        )
                        cancelled_ids.add(dependent_id)
                        queue.append(dependent_id)
                        logger.info(
                            f"Task {dependent_id} 취소 (의존성 실패)"
                        )
