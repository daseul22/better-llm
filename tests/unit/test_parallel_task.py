#!/usr/bin/env python3
"""
ParallelTask 모델 및 JSON 파싱 테스트.

test_json_parsing_only.py, test_parallel_execution.py를 통합한 파일입니다.
"""

import asyncio
import re
from datetime import datetime

import pytest

from src.domain.models.parallel_task import (
    ParallelTask,
    TaskExecutionPlan,
)
from src.domain.services.parallel_executor import ParallelTaskExecutor


def test_parallel_task_creation():
    """ParallelTask 객체가 올바르게 생성되는지 테스트합니다."""
    task = ParallelTask(
        id="task_1",
        description="파일 A 생성",
        target_files=["a.py"],
        estimated_time=100
    )

    assert task.id == "task_1"
    assert task.description == "파일 A 생성"
    assert task.target_files == ["a.py"]
    assert task.estimated_time == 100
    assert task.dependencies == []


def test_task_execution_plan_from_json():
    """TaskExecutionPlan.from_json()이 올바르게 동작하는지 테스트합니다."""
    plan_json = """
    {
        "execution_mode": "parallel",
        "tasks": [
            {
                "id": "task_1",
                "description": "파일 A 생성",
                "target_files": ["a.py"],
                "dependencies": [],
                "estimated_time": 300,
                "priority": 1
            },
            {
                "id": "task_2",
                "description": "파일 B 생성 (A에 의존)",
                "target_files": ["b.py"],
                "dependencies": ["task_1"],
                "estimated_time": 300,
                "priority": 2
            }
        ],
        "integration_notes": "파일 B는 A를 import하므로 나중에 생성해야 합니다."
    }
    """

    plan = TaskExecutionPlan.from_json(plan_json)

    assert len(plan.tasks) == 2
    assert plan.tasks[0].id == "task_1"
    assert plan.tasks[1].id == "task_2"
    assert plan.tasks[1].dependencies == ["task_1"]
    assert plan.integration_notes == "파일 B는 A를 import하므로 나중에 생성해야 합니다."


def test_markdown_code_block_parsing():
    """마크다운 코드 블록이 포함된 JSON을 올바르게 파싱하는지 테스트합니다."""
    plan_json_markdown = """
    Planner가 다음과 같은 병렬 실행 계획을 생성했습니다:

    ```json
    {
        "execution_mode": "parallel",
        "tasks": [
            {
                "id": "task_1",
                "description": "모듈 A 작성",
                "target_files": ["module_a.py"],
                "dependencies": [],
                "estimated_time": 200,
                "priority": 1
            },
            {
                "id": "task_2",
                "description": "모듈 B 작성",
                "target_files": ["module_b.py"],
                "dependencies": [],
                "estimated_time": 200,
                "priority": 1
            }
        ],
        "integration_notes": "두 모듈은 독립적입니다."
    }
    ```

    이제 execute_parallel_tasks를 호출하세요.
    """

    # Markdown 코드 블록 제거
    json_match = re.search(r"```json\s*(.*?)\s*```", plan_json_markdown, re.DOTALL)
    assert json_match, "마크다운 코드 블록 패턴 매칭 실패"

    clean_json = json_match.group(1).strip()
    plan = TaskExecutionPlan.from_json(clean_json)

    assert len(plan.tasks) == 2
    assert plan.tasks[0].id == "task_1"
    assert plan.tasks[1].id == "task_2"


def test_invalid_json_handling():
    """잘못된 JSON이 올바르게 에러를 발생시키는지 테스트합니다."""
    # 필수 필드 누락
    invalid_json = """
    {
        "tasks": [
            {
                "id": "task_1",
                "description": "파일 생성"
            }
        ]
    }
    """

    with pytest.raises(ValueError):
        TaskExecutionPlan.from_json(invalid_json)


def test_dependency_graph():
    """의존성 그래프가 올바르게 생성되는지 테스트합니다."""
    plan_json = """
    {
        "tasks": [
            {
                "id": "task_1",
                "description": "파일 A",
                "target_files": ["a.py"],
                "dependencies": []
            },
            {
                "id": "task_2",
                "description": "파일 B",
                "target_files": ["b.py"],
                "dependencies": ["task_1"]
            },
            {
                "id": "task_3",
                "description": "파일 C",
                "target_files": ["c.py"],
                "dependencies": ["task_1", "task_2"]
            }
        ]
    }
    """

    plan = TaskExecutionPlan.from_json(plan_json)
    graph = plan.build_dependency_graph()

    assert "task_1" in graph
    assert "task_2" in graph
    assert "task_3" in graph
    assert graph["task_2"] == ["task_1"]
    assert set(graph["task_3"]) == {"task_1", "task_2"}


def test_invalid_dependency():
    """존재하지 않는 의존성이 올바르게 에러를 발생시키는지 테스트합니다."""
    invalid_dep_json = """
    {
        "tasks": [
            {
                "id": "task_1",
                "description": "파일 A",
                "target_files": ["a.py"],
                "dependencies": ["task_999"]
            }
        ]
    }
    """

    plan = TaskExecutionPlan.from_json(invalid_dep_json)

    with pytest.raises(ValueError):
        plan.build_dependency_graph()


@pytest.mark.asyncio
async def test_parallel_execution():
    """독립적인 Task들이 병렬로 실행되는지 테스트합니다."""
    async def mock_coder_task(task: ParallelTask) -> str:
        """Mock Coder Agent (간단한 지연 후 결과 반환)"""
        await asyncio.sleep(0.5)
        return f"Task {task.id} completed: {task.description}"

    # Task 생성 (의존성 없음 - 모두 병렬 실행 가능)
    task1 = ParallelTask(
        id="task_1",
        description="파일 A 작성",
        target_files=["src/module_a.py"],
        estimated_time=100
    )
    task2 = ParallelTask(
        id="task_2",
        description="파일 B 작성",
        target_files=["src/module_b.py"],
        estimated_time=100
    )
    task3 = ParallelTask(
        id="task_3",
        description="파일 C 작성",
        target_files=["src/module_c.py"],
        estimated_time=100
    )

    # 실행 계획 생성
    plan = TaskExecutionPlan(
        tasks=[task1, task2, task3],
        integration_notes="3개 파일 독립적으로 생성"
    )

    # 병렬 실행
    executor = ParallelTaskExecutor(mock_coder_task, max_concurrent_tasks=5)

    start_time = datetime.now()
    result = await executor.execute(plan)
    end_time = datetime.now()

    actual_duration = (end_time - start_time).total_seconds()

    # 결과 검증
    assert result.all_succeeded, "모든 Task가 성공해야 함"
    assert len(result.completed_tasks) == 3
    assert len(result.failed_tasks) == 0
    assert result.speedup_factor > 1.5, "병렬 실행으로 1.5배 이상 속도 향상 필요"


@pytest.mark.asyncio
async def test_dependent_execution():
    """의존성이 있는 Task들이 순차적으로 실행되는지 테스트합니다."""
    async def mock_coder_task(task: ParallelTask) -> str:
        """Mock Coder Agent"""
        await asyncio.sleep(0.5)
        return f"Task {task.id} completed"

    # Task 생성 (A → B → C 순차 의존성)
    task_a = ParallelTask(
        id="task_a",
        description="기본 모듈 작성",
        target_files=["src/base.py"],
        estimated_time=100
    )
    task_b = ParallelTask(
        id="task_b",
        description="확장 모듈 작성 (base.py에 의존)",
        target_files=["src/extended.py"],
        dependencies=["task_a"],
        estimated_time=100
    )
    task_c = ParallelTask(
        id="task_c",
        description="통합 모듈 작성 (extended.py에 의존)",
        target_files=["src/integrated.py"],
        dependencies=["task_b"],
        estimated_time=100
    )

    # 실행 계획 생성
    plan = TaskExecutionPlan(
        tasks=[task_a, task_b, task_c],
        integration_notes="순차 의존성 체인"
    )

    # 병렬 실행 (의존성 때문에 순차 실행됨)
    executor = ParallelTaskExecutor(mock_coder_task)
    result = await executor.execute(plan)

    # 결과 검증
    assert result.all_succeeded, "모든 Task가 성공해야 함"
    assert task_a.end_time < task_b.start_time, "task_a가 먼저 완료되어야 함"
    assert task_b.end_time < task_c.start_time, "task_b가 먼저 완료되어야 함"


@pytest.mark.asyncio
async def test_complex_dependency_graph():
    """복잡한 의존성 그래프가 올바르게 처리되는지 테스트합니다."""
    async def mock_coder_task(task: ParallelTask) -> str:
        """Mock Coder Agent"""
        await asyncio.sleep(0.5)
        return f"Task {task.id} completed"

    # 복잡한 의존성 그래프
    # Level 0: task_a, task_b (병렬)
    # Level 1: task_c (task_a, task_b에 의존), task_d (task_a에 의존) (병렬)
    # Level 2: task_e (task_c, task_d에 의존)

    task_a = ParallelTask(
        id="task_a",
        description="모듈 A",
        target_files=["a.py"],
        estimated_time=100
    )
    task_b = ParallelTask(
        id="task_b",
        description="모듈 B",
        target_files=["b.py"],
        estimated_time=100
    )
    task_c = ParallelTask(
        id="task_c",
        description="모듈 C (A, B에 의존)",
        target_files=["c.py"],
        dependencies=["task_a", "task_b"],
        estimated_time=100
    )
    task_d = ParallelTask(
        id="task_d",
        description="모듈 D (A에 의존)",
        target_files=["d.py"],
        dependencies=["task_a"],
        estimated_time=100
    )
    task_e = ParallelTask(
        id="task_e",
        description="모듈 E (C, D에 의존)",
        target_files=["e.py"],
        dependencies=["task_c", "task_d"],
        estimated_time=100
    )

    plan = TaskExecutionPlan(
        tasks=[task_a, task_b, task_c, task_d, task_e],
        integration_notes="복잡한 의존성 그래프"
    )

    # 실행 레벨 확인
    executor = ParallelTaskExecutor(mock_coder_task)
    levels = executor._compute_execution_levels(plan)

    # 레벨 검증
    assert len(levels) == 3, "3개 레벨로 실행되어야 함"
    assert set(levels[0]) == {"task_a", "task_b"}, "레벨 0은 A, B여야 함"
    assert set(levels[1]) == {"task_c", "task_d"}, "레벨 1은 C, D여야 함"
    assert levels[2] == ["task_e"], "레벨 2는 E여야 함"

    # 병렬 실행
    result = await executor.execute(plan)

    # 결과 검증
    assert result.all_succeeded, "모든 Task가 성공해야 함"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
