"""
ParallelExecutor 테스트
"""

import pytest
import asyncio
from datetime import datetime
from src.infrastructure.mcp.parallel_executor import (
    ParallelExecutor,
    ExecutionLevel,
    CircularDependencyError
)
from src.domain.models.parallel_task import (
    ParallelTask,
    TaskExecutionPlan,
    TaskExecutionResult
)
from src.domain.models.task import TaskStatus


class TestParallelExecutorInitialization:
    """ParallelExecutor 초기화 테스트"""

    @pytest.mark.asyncio
    async def test_initialization(self):
        """기본 초기화 테스트"""
        async def dummy_executor(task):
            return "result"

        executor = ParallelExecutor(
            task_executor=dummy_executor,
            max_concurrent_tasks=5
        )

        assert executor.max_concurrent_tasks == 5
        assert executor.continue_on_error is False


class TestPlanParsing:
    """실행 계획 파싱 테스트"""

    def test_parse_plan_valid_json(self):
        """정상 JSON 파싱 테스트"""
        plan_json = """
{
    "tasks": [
        {
            "id": "task_1",
            "description": "Create module A",
            "target_files": ["a.py"]
        }
    ],
    "integration_notes": "Test notes"
}
"""

        async def dummy_executor(task):
            return "result"

        executor = ParallelExecutor(task_executor=dummy_executor)
        plan = executor.parse_plan(plan_json)

        assert len(plan.tasks) == 1
        assert plan.tasks[0].id == "task_1"
        assert plan.integration_notes == "Test notes"

    def test_parse_plan_with_markdown_code_block(self):
        """마크다운 코드 블록 포함 JSON 파싱 테스트"""
        plan_json = """
```json
{
    "tasks": [
        {
            "id": "task_1",
            "description": "Test",
            "target_files": ["test.py"]
        }
    ],
    "integration_notes": ""
}
```
"""

        async def dummy_executor(task):
            return "result"

        executor = ParallelExecutor(task_executor=dummy_executor)
        plan = executor.parse_plan(plan_json)

        assert len(plan.tasks) == 1

    def test_parse_plan_invalid_json(self):
        """잘못된 JSON 파싱 테스트"""
        plan_json = "invalid json"

        async def dummy_executor(task):
            return "result"

        executor = ParallelExecutor(task_executor=dummy_executor)

        with pytest.raises(ValueError):
            executor.parse_plan(plan_json)


class TestDependencyGraph:
    """의존성 그래프 구축 테스트"""

    def test_build_dependency_graph_no_dependencies(self):
        """의존성이 없는 경우 테스트"""
        tasks = [
            ParallelTask(id="task_1", description="A", target_files=["a.py"]),
            ParallelTask(id="task_2", description="B", target_files=["b.py"])
        ]

        async def dummy_executor(task):
            return "result"

        executor = ParallelExecutor(task_executor=dummy_executor)
        graph = executor.build_dependency_graph(tasks)

        assert graph["task_1"] == []
        assert graph["task_2"] == []

    def test_build_dependency_graph_with_dependencies(self):
        """의존성이 있는 경우 테스트"""
        tasks = [
            ParallelTask(id="task_1", description="A", target_files=["a.py"]),
            ParallelTask(
                id="task_2",
                description="B",
                target_files=["b.py"],
                dependencies=["task_1"]
            )
        ]

        async def dummy_executor(task):
            return "result"

        executor = ParallelExecutor(task_executor=dummy_executor)
        graph = executor.build_dependency_graph(tasks)

        assert "task_2" in graph["task_1"]
        assert graph["task_2"] == []

    def test_build_dependency_graph_invalid_dependency(self):
        """존재하지 않는 의존성 테스트"""
        tasks = [
            ParallelTask(
                id="task_1",
                description="A",
                target_files=["a.py"],
                dependencies=["nonexistent"]
            )
        ]

        async def dummy_executor(task):
            return "result"

        executor = ParallelExecutor(task_executor=dummy_executor)

        with pytest.raises(ValueError):
            executor.build_dependency_graph(tasks)


class TestCircularDependencyDetection:
    """순환 의존성 감지 테스트"""

    def test_detect_circular_dependency_simple(self):
        """단순 순환 의존성 감지 테스트"""
        # task_1 -> task_2 -> task_1 (순환)
        tasks = [
            ParallelTask(
                id="task_1",
                description="A",
                target_files=["a.py"],
                dependencies=["task_2"]
            ),
            ParallelTask(
                id="task_2",
                description="B",
                target_files=["b.py"],
                dependencies=["task_1"]
            )
        ]

        async def dummy_executor(task):
            return "result"

        executor = ParallelExecutor(task_executor=dummy_executor)
        cycle = executor.detect_circular_dependency(tasks)

        assert cycle is not None
        assert "task_1" in cycle or "task_2" in cycle

    def test_detect_circular_dependency_none(self):
        """순환 의존성이 없는 경우 테스트"""
        tasks = [
            ParallelTask(id="task_1", description="A", target_files=["a.py"]),
            ParallelTask(
                id="task_2",
                description="B",
                target_files=["b.py"],
                dependencies=["task_1"]
            )
        ]

        async def dummy_executor(task):
            return "result"

        executor = ParallelExecutor(task_executor=dummy_executor)
        cycle = executor.detect_circular_dependency(tasks)

        assert cycle is None

    def test_detect_circular_dependency_complex(self):
        """복잡한 순환 의존성 감지 테스트"""
        # task_1 -> task_2 -> task_3 -> task_1 (순환)
        tasks = [
            ParallelTask(
                id="task_1",
                description="A",
                target_files=["a.py"],
                dependencies=["task_3"]
            ),
            ParallelTask(
                id="task_2",
                description="B",
                target_files=["b.py"],
                dependencies=["task_1"]
            ),
            ParallelTask(
                id="task_3",
                description="C",
                target_files=["c.py"],
                dependencies=["task_2"]
            )
        ]

        async def dummy_executor(task):
            return "result"

        executor = ParallelExecutor(task_executor=dummy_executor)
        cycle = executor.detect_circular_dependency(tasks)

        assert cycle is not None


class TestTopologicalSort:
    """Topological Sort 테스트"""

    def test_topological_sort_no_dependencies(self):
        """의존성이 없는 경우 테스트"""
        tasks = [
            ParallelTask(id="task_1", description="A", target_files=["a.py"]),
            ParallelTask(id="task_2", description="B", target_files=["b.py"])
        ]

        async def dummy_executor(task):
            return "result"

        executor = ParallelExecutor(task_executor=dummy_executor)
        levels = executor.topological_sort(tasks)

        # 모든 Task가 Level 0에 있어야 함
        assert len(levels) == 1
        assert len(levels[0].tasks) == 2

    def test_topological_sort_with_dependencies(self):
        """의존성이 있는 경우 테스트"""
        tasks = [
            ParallelTask(id="task_1", description="A", target_files=["a.py"]),
            ParallelTask(
                id="task_2",
                description="B",
                target_files=["b.py"],
                dependencies=["task_1"]
            ),
            ParallelTask(
                id="task_3",
                description="C",
                target_files=["c.py"],
                dependencies=["task_1"]
            )
        ]

        async def dummy_executor(task):
            return "result"

        executor = ParallelExecutor(task_executor=dummy_executor)
        levels = executor.topological_sort(tasks)

        # Level 0: task_1
        # Level 1: task_2, task_3
        assert len(levels) == 2
        assert levels[0].tasks[0].id == "task_1"
        assert len(levels[1].tasks) == 2

    def test_topological_sort_circular_dependency_raises(self):
        """순환 의존성이 있는 경우 예외 발생 테스트"""
        tasks = [
            ParallelTask(
                id="task_1",
                description="A",
                target_files=["a.py"],
                dependencies=["task_2"]
            ),
            ParallelTask(
                id="task_2",
                description="B",
                target_files=["b.py"],
                dependencies=["task_1"]
            )
        ]

        async def dummy_executor(task):
            return "result"

        executor = ParallelExecutor(task_executor=dummy_executor)

        with pytest.raises(CircularDependencyError):
            executor.topological_sort(tasks)


class TestExecuteLevel:
    """Level별 실행 테스트"""

    @pytest.mark.asyncio
    async def test_execute_level_single_task(self):
        """단일 Task 실행 테스트"""
        task = ParallelTask(id="task_1", description="Test", target_files=["test.py"])

        async def dummy_executor(t):
            await asyncio.sleep(0.01)
            return "result"

        executor = ParallelExecutor(task_executor=dummy_executor)
        completed, failed = await executor.execute_level(0, [task], set())

        assert len(completed) == 1
        assert len(failed) == 0
        assert task.status == TaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_execute_level_multiple_tasks(self):
        """여러 Task 병렬 실행 테스트"""
        tasks = [
            ParallelTask(id="task_1", description="A", target_files=["a.py"]),
            ParallelTask(id="task_2", description="B", target_files=["b.py"])
        ]

        async def dummy_executor(t):
            await asyncio.sleep(0.01)
            return f"result_{t.id}"

        executor = ParallelExecutor(task_executor=dummy_executor)
        completed, failed = await executor.execute_level(0, tasks, set())

        assert len(completed) == 2
        assert len(failed) == 0

    @pytest.mark.asyncio
    async def test_execute_level_with_failure(self):
        """Task 실패 처리 테스트"""
        task = ParallelTask(id="task_1", description="Test", target_files=["test.py"])

        async def failing_executor(t):
            raise ValueError("Test error")

        executor = ParallelExecutor(task_executor=failing_executor)
        completed, failed = await executor.execute_level(0, [task], set())

        assert len(completed) == 0
        assert len(failed) == 1
        assert task.status == TaskStatus.FAILED
        assert "Test error" in task.error

    @pytest.mark.asyncio
    async def test_execute_level_concurrency_limit(self):
        """동시 실행 개수 제한 테스트"""
        tasks = [
            ParallelTask(id=f"task_{i}", description=f"Task {i}", target_files=["test.py"])
            for i in range(10)
        ]

        execution_count = 0
        max_concurrent = 0
        current_concurrent = 0

        async def counting_executor(t):
            nonlocal execution_count, max_concurrent, current_concurrent
            current_concurrent += 1
            max_concurrent = max(max_concurrent, current_concurrent)
            await asyncio.sleep(0.01)
            current_concurrent -= 1
            execution_count += 1
            return "result"

        executor = ParallelExecutor(
            task_executor=counting_executor,
            max_concurrent_tasks=3
        )
        await executor.execute_level(0, tasks, set())

        assert execution_count == 10
        # 최대 3개까지만 동시 실행
        assert max_concurrent <= 3


class TestExecute:
    """전체 실행 테스트"""

    @pytest.mark.asyncio
    async def test_execute_simple_plan(self):
        """단순 실행 계획 테스트"""
        tasks = [
            ParallelTask(id="task_1", description="A", target_files=["a.py"])
        ]
        plan = TaskExecutionPlan(tasks=tasks, integration_notes="Test")

        async def dummy_executor(t):
            await asyncio.sleep(0.01)
            return "result"

        executor = ParallelExecutor(task_executor=dummy_executor)
        result = await executor.execute(plan)

        assert result.all_succeeded is True
        assert len(result.completed_tasks) == 1
        assert len(result.failed_tasks) == 0

    @pytest.mark.asyncio
    async def test_execute_with_dependencies(self):
        """의존성이 있는 실행 계획 테스트"""
        tasks = [
            ParallelTask(id="task_1", description="A", target_files=["a.py"]),
            ParallelTask(
                id="task_2",
                description="B",
                target_files=["b.py"],
                dependencies=["task_1"]
            )
        ]
        plan = TaskExecutionPlan(tasks=tasks, integration_notes="Test")

        async def dummy_executor(t):
            await asyncio.sleep(0.01)
            return f"result_{t.id}"

        executor = ParallelExecutor(task_executor=dummy_executor)
        result = await executor.execute(plan)

        assert result.all_succeeded is True
        assert len(result.completed_tasks) == 2

    @pytest.mark.asyncio
    async def test_execute_with_failure_stop_on_error(self):
        """실패 시 중단 테스트 (continue_on_error=False)"""
        tasks = [
            ParallelTask(id="task_1", description="A", target_files=["a.py"]),
            ParallelTask(
                id="task_2",
                description="B",
                target_files=["b.py"],
                dependencies=["task_1"]
            )
        ]
        plan = TaskExecutionPlan(tasks=tasks, integration_notes="Test")

        async def failing_executor(t):
            if t.id == "task_1":
                raise ValueError("Test error")
            return "result"

        executor = ParallelExecutor(
            task_executor=failing_executor,
            continue_on_error=False
        )
        result = await executor.execute(plan)

        assert result.all_succeeded is False
        assert len(result.failed_tasks) == 2  # task_1 실패, task_2 스킵

    @pytest.mark.asyncio
    async def test_execute_with_failure_continue_on_error(self):
        """실패해도 계속 진행 테스트 (continue_on_error=True)"""
        tasks = [
            ParallelTask(id="task_1", description="A", target_files=["a.py"]),
            ParallelTask(id="task_2", description="B", target_files=["b.py"])
        ]
        plan = TaskExecutionPlan(tasks=tasks, integration_notes="Test")

        async def partially_failing_executor(t):
            if t.id == "task_1":
                raise ValueError("Test error")
            return "result"

        executor = ParallelExecutor(
            task_executor=partially_failing_executor,
            continue_on_error=True
        )
        result = await executor.execute(plan)

        assert len(result.completed_tasks) == 1
        assert len(result.failed_tasks) == 1

    @pytest.mark.asyncio
    async def test_execute_speedup_calculation(self):
        """속도 향상 계산 테스트"""
        tasks = [
            ParallelTask(
                id="task_1",
                description="A",
                target_files=["a.py"],
                estimated_time=100
            ),
            ParallelTask(
                id="task_2",
                description="B",
                target_files=["b.py"],
                estimated_time=100
            )
        ]
        plan = TaskExecutionPlan(tasks=tasks, integration_notes="Test")

        async def dummy_executor(t):
            await asyncio.sleep(0.01)
            return "result"

        executor = ParallelExecutor(task_executor=dummy_executor)
        result = await executor.execute(plan)

        # 순차 실행 시간: 200초, 실제 실행 시간: ~0.01초
        # speedup_factor > 1 이어야 함
        assert result.speedup_factor > 1

    @pytest.mark.asyncio
    async def test_execute_circular_dependency_raises(self):
        """순환 의존성 감지 테스트"""
        tasks = [
            ParallelTask(
                id="task_1",
                description="A",
                target_files=["a.py"],
                dependencies=["task_2"]
            ),
            ParallelTask(
                id="task_2",
                description="B",
                target_files=["b.py"],
                dependencies=["task_1"]
            )
        ]
        plan = TaskExecutionPlan(tasks=tasks, integration_notes="Test")

        async def dummy_executor(t):
            return "result"

        executor = ParallelExecutor(task_executor=dummy_executor)

        with pytest.raises(CircularDependencyError):
            await executor.execute(plan)


class TestRollback:
    """롤백 테스트"""

    def test_rollback(self):
        """롤백 메서드 호출 테스트"""
        tasks = [
            ParallelTask(id="task_1", description="A", target_files=["a.py"])
        ]

        async def dummy_executor(t):
            return "result"

        executor = ParallelExecutor(task_executor=dummy_executor)

        # 롤백 호출 - 에러 없이 실행되어야 함
        executor.rollback(tasks)
