"""
병렬 Task 도메인 모델 테스트

ParallelTask, TaskExecutionPlan, TaskExecutionResult 단위 테스트
"""

import pytest
from datetime import datetime, timedelta

from src.domain.models.parallel_task import (
    ParallelTask,
    TaskExecutionPlan,
    TaskExecutionResult,
)
from src.domain.models.task import TaskStatus


class TestParallelTask:
    """ParallelTask 테스트"""

    def test_duration_seconds_with_start_and_end_time(self):
        """실행 시간 계산: start_time과 end_time이 있는 경우"""
        start = datetime.now()
        end = start + timedelta(seconds=10)

        task = ParallelTask(
            id="task_1",
            description="Test task",
            target_files=["file.py"],
            start_time=start,
            end_time=end
        )

        assert task.duration_seconds() == pytest.approx(10.0, abs=0.1)

    def test_duration_seconds_without_start_time(self):
        """실행 시간 계산: start_time이 없는 경우 None 반환"""
        task = ParallelTask(
            id="task_1",
            description="Test task",
            target_files=["file.py"],
            end_time=datetime.now()
        )

        assert task.duration_seconds() is None

    def test_duration_seconds_without_end_time(self):
        """실행 시간 계산: end_time이 없는 경우 None 반환"""
        task = ParallelTask(
            id="task_1",
            description="Test task",
            target_files=["file.py"],
            start_time=datetime.now()
        )

        assert task.duration_seconds() is None

    def test_is_ready_all_dependencies_completed(self):
        """is_ready: 모든 의존성이 완료된 경우 True"""
        task = ParallelTask(
            id="task_3",
            description="Test task",
            target_files=["file.py"],
            dependencies=["task_1", "task_2"]
        )

        completed_task_ids = {"task_1", "task_2"}
        assert task.is_ready(completed_task_ids) is True

    def test_is_ready_some_dependencies_not_completed(self):
        """is_ready: 일부 의존성이 미완료된 경우 False"""
        task = ParallelTask(
            id="task_3",
            description="Test task",
            target_files=["file.py"],
            dependencies=["task_1", "task_2"]
        )

        completed_task_ids = {"task_1"}  # task_2 미완료
        assert task.is_ready(completed_task_ids) is False

    def test_is_ready_no_dependencies(self):
        """is_ready: 의존성이 없는 경우 항상 True"""
        task = ParallelTask(
            id="task_1",
            description="Test task",
            target_files=["file.py"],
            dependencies=[]
        )

        completed_task_ids = set()
        assert task.is_ready(completed_task_ids) is True


class TestTaskExecutionPlan:
    """TaskExecutionPlan 테스트"""

    def test_get_task_existing(self):
        """get_task: 존재하는 Task 반환"""
        task1 = ParallelTask(id="task_1", description="Task 1", target_files=["a.py"])
        task2 = ParallelTask(id="task_2", description="Task 2", target_files=["b.py"])

        plan = TaskExecutionPlan(
            tasks=[task1, task2],
            integration_notes="Test plan"
        )

        assert plan.get_task("task_1") == task1
        assert plan.get_task("task_2") == task2

    def test_get_task_non_existing(self):
        """get_task: 존재하지 않는 Task는 None 반환"""
        task1 = ParallelTask(id="task_1", description="Task 1", target_files=["a.py"])

        plan = TaskExecutionPlan(
            tasks=[task1],
            integration_notes="Test plan"
        )

        assert plan.get_task("task_999") is None

    def test_build_dependency_graph_normal(self):
        """build_dependency_graph: 정상 케이스"""
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
            dependencies=["task_1"]
        )

        plan = TaskExecutionPlan(
            tasks=[task1, task2, task3],
            integration_notes="Test plan"
        )

        graph = plan.build_dependency_graph()

        assert graph == {
            "task_1": ["task_2", "task_3"],  # task_1 완료 후 task_2, task_3 실행 가능
            "task_2": [],
            "task_3": []
        }

    def test_build_dependency_graph_invalid_dependency(self):
        """build_dependency_graph: 존재하지 않는 의존성 지정 시 ValueError (Critical 이슈 수정 검증)"""
        task1 = ParallelTask(id="task_1", description="Task 1", target_files=["a.py"])
        task2 = ParallelTask(
            id="task_2",
            description="Task 2",
            target_files=["b.py"],
            dependencies=["task_999"]  # 존재하지 않는 Task
        )

        plan = TaskExecutionPlan(
            tasks=[task1, task2],
            integration_notes="Test plan"
        )

        with pytest.raises(ValueError) as exc_info:
            plan.build_dependency_graph()

        assert "task_2" in str(exc_info.value)
        assert "task_999" in str(exc_info.value)
        assert "존재하지 않습니다" in str(exc_info.value)

    def test_estimate_total_time(self):
        """estimate_total_time: 순차 실행 시 예상 총 시간 계산"""
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
            estimated_time=200
        )
        task3 = ParallelTask(
            id="task_3",
            description="Task 3",
            target_files=["c.py"],
            estimated_time=150
        )

        plan = TaskExecutionPlan(
            tasks=[task1, task2, task3],
            integration_notes="Test plan"
        )

        assert plan.estimate_total_time() == 450  # 100 + 200 + 150


class TestTaskExecutionResult:
    """TaskExecutionResult 테스트"""

    def test_success_rate_all_succeeded(self):
        """success_rate: 모든 Task 성공 시 1.0"""
        task1 = ParallelTask(id="task_1", description="Task 1", target_files=["a.py"])
        task2 = ParallelTask(id="task_2", description="Task 2", target_files=["b.py"])

        plan = TaskExecutionPlan(tasks=[task1, task2], integration_notes="Test")
        result = TaskExecutionResult(
            plan=plan,
            completed_tasks=[task1, task2],
            failed_tasks=[],
            total_duration=10.0,
            speedup_factor=1.5
        )

        assert result.success_rate == 1.0

    def test_success_rate_partial_success(self):
        """success_rate: 일부 Task 실패 시 성공률 계산"""
        task1 = ParallelTask(id="task_1", description="Task 1", target_files=["a.py"])
        task2 = ParallelTask(id="task_2", description="Task 2", target_files=["b.py"])
        task3 = ParallelTask(id="task_3", description="Task 3", target_files=["c.py"])

        plan = TaskExecutionPlan(tasks=[task1, task2, task3], integration_notes="Test")
        result = TaskExecutionResult(
            plan=plan,
            completed_tasks=[task1, task2],  # 2개 성공
            failed_tasks=[task3],  # 1개 실패
            total_duration=10.0,
            speedup_factor=1.5
        )

        assert result.success_rate == pytest.approx(2.0 / 3.0, abs=0.01)

    def test_success_rate_all_failed(self):
        """success_rate: 모든 Task 실패 시 0.0"""
        task1 = ParallelTask(id="task_1", description="Task 1", target_files=["a.py"])
        task2 = ParallelTask(id="task_2", description="Task 2", target_files=["b.py"])

        plan = TaskExecutionPlan(tasks=[task1, task2], integration_notes="Test")
        result = TaskExecutionResult(
            plan=plan,
            completed_tasks=[],
            failed_tasks=[task1, task2],
            total_duration=10.0,
            speedup_factor=1.0
        )

        assert result.success_rate == 0.0

    def test_success_rate_no_tasks(self):
        """success_rate: Task가 없는 경우 0.0"""
        plan = TaskExecutionPlan(tasks=[], integration_notes="Test")
        result = TaskExecutionResult(
            plan=plan,
            completed_tasks=[],
            failed_tasks=[],
            total_duration=0.0,
            speedup_factor=1.0
        )

        assert result.success_rate == 0.0

    def test_all_succeeded_true(self):
        """all_succeeded: 실패한 Task가 없으면 True"""
        task1 = ParallelTask(id="task_1", description="Task 1", target_files=["a.py"])
        task2 = ParallelTask(id="task_2", description="Task 2", target_files=["b.py"])

        plan = TaskExecutionPlan(tasks=[task1, task2], integration_notes="Test")
        result = TaskExecutionResult(
            plan=plan,
            completed_tasks=[task1, task2],
            failed_tasks=[],
            total_duration=10.0,
            speedup_factor=1.5
        )

        assert result.all_succeeded is True

    def test_all_succeeded_false(self):
        """all_succeeded: 실패한 Task가 있으면 False"""
        task1 = ParallelTask(id="task_1", description="Task 1", target_files=["a.py"])
        task2 = ParallelTask(id="task_2", description="Task 2", target_files=["b.py"])

        plan = TaskExecutionPlan(tasks=[task1, task2], integration_notes="Test")
        result = TaskExecutionResult(
            plan=plan,
            completed_tasks=[task1],
            failed_tasks=[task2],
            total_duration=10.0,
            speedup_factor=1.0
        )

        assert result.all_succeeded is False
