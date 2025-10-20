"""
병렬 Task 실행 엔진 테스트

ParallelTaskExecutor 단위 테스트
"""

import pytest
import asyncio
from datetime import datetime
from typing import Dict

from src.domain.models.parallel_task import (
    ParallelTask,
    TaskExecutionPlan,
    TaskExecutionResult,
)
from src.domain.models.task import TaskStatus
from src.domain.services.parallel_executor import ParallelTaskExecutor


class TestParallelTaskExecutor:
    """ParallelTaskExecutor 테스트"""

    @pytest.fixture
    def mock_task_executor(self):
        """Mock task executor 생성"""
        async def executor(task: ParallelTask) -> str:
            """정상적으로 완료되는 Mock Executor"""
            await asyncio.sleep(0.1)  # 짧은 지연
            return f"Result of {task.id}"

        return executor

    @pytest.fixture
    def failing_task_executor(self):
        """실패하는 Mock task executor 생성"""
        failed_task_ids = {"task_2"}  # task_2만 실패하도록 설정

        async def executor(task: ParallelTask) -> str:
            """task_2만 실패하는 Mock Executor"""
            await asyncio.sleep(0.1)
            if task.id in failed_task_ids:
                raise Exception(f"Task {task.id} failed intentionally")
            return f"Result of {task.id}"

        return executor

    def test_compute_execution_levels_no_dependencies(self, mock_task_executor):
        """_compute_execution_levels: 의존성 없는 Task들 (레벨 0)"""
        task1 = ParallelTask(id="task_1", description="Task 1", target_files=["a.py"])
        task2 = ParallelTask(id="task_2", description="Task 2", target_files=["b.py"])
        task3 = ParallelTask(id="task_3", description="Task 3", target_files=["c.py"])

        plan = TaskExecutionPlan(tasks=[task1, task2, task3], integration_notes="Test")
        executor = ParallelTaskExecutor(mock_task_executor)

        levels = executor._compute_execution_levels(plan)

        assert len(levels) == 1  # 모든 Task가 레벨 0
        assert set(levels[0]) == {"task_1", "task_2", "task_3"}

    def test_compute_execution_levels_simple_chain(self, mock_task_executor):
        """_compute_execution_levels: 단순 의존성 체인 (A → B → C)"""
        task1 = ParallelTask(id="task_1", description="Task 1", target_files=["a.py"])
        task2 = ParallelTask(
            id="task_2",
            description="Task 2",
            target_files=["b.py"],
            dependencies=["task_1"]
        )
        task3 = ParallelTask(
            id="task_3",
            description="Task 3",
            target_files=["c.py"],
            dependencies=["task_2"]
        )

        plan = TaskExecutionPlan(tasks=[task1, task2, task3], integration_notes="Test")
        executor = ParallelTaskExecutor(mock_task_executor)

        levels = executor._compute_execution_levels(plan)

        assert len(levels) == 3
        assert levels[0] == ["task_1"]
        assert levels[1] == ["task_2"]
        assert levels[2] == ["task_3"]

    def test_compute_execution_levels_complex_graph(self, mock_task_executor):
        """_compute_execution_levels: 복잡한 의존성 그래프 (A, B → C, D → E)"""
        task_a = ParallelTask(id="task_a", description="Task A", target_files=["a.py"])
        task_b = ParallelTask(id="task_b", description="Task B", target_files=["b.py"])
        task_c = ParallelTask(
            id="task_c",
            description="Task C",
            target_files=["c.py"],
            dependencies=["task_a", "task_b"]
        )
        task_d = ParallelTask(
            id="task_d",
            description="Task D",
            target_files=["d.py"],
            dependencies=["task_a"]
        )
        task_e = ParallelTask(
            id="task_e",
            description="Task E",
            target_files=["e.py"],
            dependencies=["task_c", "task_d"]
        )

        plan = TaskExecutionPlan(
            tasks=[task_a, task_b, task_c, task_d, task_e],
            integration_notes="Test"
        )
        executor = ParallelTaskExecutor(mock_task_executor)

        levels = executor._compute_execution_levels(plan)

        assert len(levels) == 3
        assert set(levels[0]) == {"task_a", "task_b"}  # 레벨 0
        assert set(levels[1]) == {"task_c", "task_d"}  # 레벨 1
        assert levels[2] == ["task_e"]  # 레벨 2

    def test_compute_execution_levels_circular_dependency(self, mock_task_executor):
        """_compute_execution_levels: 순환 의존성 감지 시 ValueError (Critical 이슈 수정 검증)"""
        # 순환 의존성: task_1 → task_2 → task_3 → task_1
        task1 = ParallelTask(
            id="task_1",
            description="Task 1",
            target_files=["a.py"],
            dependencies=["task_3"]  # task_3에 의존
        )
        task2 = ParallelTask(
            id="task_2",
            description="Task 2",
            target_files=["b.py"],
            dependencies=["task_1"]
        )
        task3 = ParallelTask(
            id="task_3",
            description="Task 3",
            target_files=["c.py"],
            dependencies=["task_2"]
        )

        plan = TaskExecutionPlan(tasks=[task1, task2, task3], integration_notes="Test")
        executor = ParallelTaskExecutor(mock_task_executor)

        with pytest.raises(ValueError) as exc_info:
            executor._compute_execution_levels(plan)

        assert "순환 의존성" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_independent_tasks(self, mock_task_executor):
        """execute: 독립적인 Task 2개 병렬 실행"""
        task1 = ParallelTask(
            id="task_1",
            description="Task 1",
            target_files=["a.py"],
            estimated_time=100
        )
        task2 = ParallelTask(
            id="task_2",
            description="Task 2",
            target_files=["b.py"],
            estimated_time=100
        )

        plan = TaskExecutionPlan(tasks=[task1, task2], integration_notes="Test")
        executor = ParallelTaskExecutor(mock_task_executor)

        result = await executor.execute(plan)

        # 검증
        assert len(result.completed_tasks) == 2
        assert len(result.failed_tasks) == 0
        assert result.all_succeeded is True
        assert result.success_rate == 1.0

        # Task 상태 확인
        assert task1.status == TaskStatus.COMPLETED
        assert task2.status == TaskStatus.COMPLETED
        assert task1.result == "Result of task_1"
        assert task2.result == "Result of task_2"

    @pytest.mark.asyncio
    async def test_execute_dependent_tasks(self, mock_task_executor):
        """execute: 의존성 있는 Task 순차 실행"""
        task1 = ParallelTask(
            id="task_1",
            description="Task 1",
            target_files=["a.py"],
            estimated_time=100
        )
        task2 = ParallelTask(
            id="task_2",
            description="Task 2",
            target_files=["b.py"],
            dependencies=["task_1"],
            estimated_time=100
        )

        plan = TaskExecutionPlan(tasks=[task1, task2], integration_notes="Test")
        executor = ParallelTaskExecutor(mock_task_executor)

        result = await executor.execute(plan)

        # 검증
        assert len(result.completed_tasks) == 2
        assert len(result.failed_tasks) == 0
        assert result.all_succeeded is True
        assert result.success_rate == 1.0

        # Task 실행 순서 확인 (task1이 먼저 완료되어야 함)
        assert task1.end_time < task2.start_time

    @pytest.mark.asyncio
    async def test_execute_with_failure_cancels_dependent_tasks(
        self, failing_task_executor
    ):
        """execute: 실패한 Task의 하위 Task 자동 취소 (Major 이슈 수정 검증)"""
        task1 = ParallelTask(
            id="task_1",
            description="Task 1",
            target_files=["a.py"],
            estimated_time=100
        )
        task2 = ParallelTask(
            id="task_2",
            description="Task 2 (will fail)",
            target_files=["b.py"],
            estimated_time=100
        )
        task3 = ParallelTask(
            id="task_3",
            description="Task 3 (depends on task_2)",
            target_files=["c.py"],
            dependencies=["task_2"],
            estimated_time=100
        )
        task4 = ParallelTask(
            id="task_4",
            description="Task 4 (depends on task_3)",
            target_files=["d.py"],
            dependencies=["task_3"],
            estimated_time=100
        )

        plan = TaskExecutionPlan(
            tasks=[task1, task2, task3, task4],
            integration_notes="Test"
        )
        executor = ParallelTaskExecutor(failing_task_executor)

        result = await executor.execute(plan)

        # 검증
        assert len(result.completed_tasks) == 1  # task_1만 성공
        assert len(result.failed_tasks) == 1  # task_2 실패
        assert result.all_succeeded is False

        # Task 상태 확인
        assert task1.status == TaskStatus.COMPLETED
        assert task2.status == TaskStatus.FAILED
        assert task3.status == TaskStatus.CANCELLED  # task_2 실패로 취소
        assert task4.status == TaskStatus.CANCELLED  # task_3 취소로 취소

        # 에러 메시지 확인
        assert "failed intentionally" in task2.error
        assert "task_2" in task3.error
        assert "실패로 인한 취소" in task3.error

    @pytest.mark.asyncio
    async def test_execute_speedup_factor(self, mock_task_executor):
        """execute: speedup_factor 계산 정확성"""
        task1 = ParallelTask(
            id="task_1",
            description="Task 1",
            target_files=["a.py"],
            estimated_time=100
        )
        task2 = ParallelTask(
            id="task_2",
            description="Task 2",
            target_files=["b.py"],
            estimated_time=100
        )

        plan = TaskExecutionPlan(tasks=[task1, task2], integration_notes="Test")
        executor = ParallelTaskExecutor(mock_task_executor)

        result = await executor.execute(plan)

        # 병렬 실행이므로 speedup_factor > 1.0 (이론적으로 ~2.0)
        assert result.speedup_factor > 1.0

    def test_cancel_dependent_tasks(self, mock_task_executor):
        """_cancel_dependent_tasks: BFS 탐색 및 취소 정확성"""
        task1 = ParallelTask(id="task_1", description="Task 1", target_files=["a.py"])
        task2 = ParallelTask(
            id="task_2",
            description="Task 2",
            target_files=["b.py"],
            dependencies=["task_1"]
        )
        task3 = ParallelTask(
            id="task_3",
            description="Task 3",
            target_files=["c.py"],
            dependencies=["task_2"]
        )
        task4 = ParallelTask(
            id="task_4",
            description="Task 4",
            target_files=["d.py"],
            dependencies=["task_3"]
        )

        plan = TaskExecutionPlan(
            tasks=[task1, task2, task3, task4],
            integration_notes="Test"
        )
        executor = ParallelTaskExecutor(mock_task_executor)

        # task_1 실패로 인한 취소 시뮬레이션
        task1.status = TaskStatus.FAILED
        remaining_levels = [["task_2"], ["task_3"], ["task_4"]]

        executor._cancel_dependent_tasks(task1.id, plan, remaining_levels)

        # 검증
        assert task2.status == TaskStatus.CANCELLED
        assert task3.status == TaskStatus.CANCELLED
        assert task4.status == TaskStatus.CANCELLED

        # 에러 메시지 확인
        assert "task_1" in task2.error
        assert "실패로 인한 취소" in task2.error

    def test_cancel_dependent_tasks_partial_cancellation(self, mock_task_executor):
        """_cancel_dependent_tasks: 일부 Task만 취소"""
        # 복잡한 그래프: task_1, task_2 → task_3 → task_4
        #                          task_2 → task_5 (독립적)
        task1 = ParallelTask(id="task_1", description="Task 1", target_files=["a.py"])
        task2 = ParallelTask(id="task_2", description="Task 2", target_files=["b.py"])
        task3 = ParallelTask(
            id="task_3",
            description="Task 3",
            target_files=["c.py"],
            dependencies=["task_1", "task_2"]
        )
        task4 = ParallelTask(
            id="task_4",
            description="Task 4",
            target_files=["d.py"],
            dependencies=["task_3"]
        )
        task5 = ParallelTask(
            id="task_5",
            description="Task 5",
            target_files=["e.py"],
            dependencies=["task_2"]
        )

        plan = TaskExecutionPlan(
            tasks=[task1, task2, task3, task4, task5],
            integration_notes="Test"
        )
        executor = ParallelTaskExecutor(mock_task_executor)

        # task_1 실패로 인한 취소 시뮬레이션
        task1.status = TaskStatus.FAILED
        task2.status = TaskStatus.COMPLETED  # task_2는 정상 완료
        remaining_levels = [["task_3", "task_5"], ["task_4"]]

        executor._cancel_dependent_tasks(task1.id, plan, remaining_levels)

        # 검증: task_1에 의존하는 task_3, task_4만 취소
        assert task3.status == TaskStatus.CANCELLED
        assert task4.status == TaskStatus.CANCELLED
        assert task5.status == TaskStatus.PENDING  # task_5는 task_2에만 의존하므로 취소되지 않음
