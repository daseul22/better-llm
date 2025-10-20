#!/usr/bin/env python3
"""
병렬 실행 통합 테스트.

test_parallel_integration.py, test_debug_info.py를 통합한 파일입니다.
"""

import asyncio
import json
import os
from pathlib import Path

import pytest

from src.infrastructure.mcp import initialize_workers
from src.infrastructure.mcp.worker_tools import execute_parallel_tasks, _WORKER_AGENTS
from src.infrastructure.config import get_project_root


@pytest.fixture
def config_path():
    """Agent 설정 파일 경로를 반환합니다."""
    return get_project_root() / "config" / "agent_config.json"


@pytest.mark.asyncio
async def test_debug_info_display(config_path):
    """
    WORKER_DEBUG_INFO 환경변수가 활성화되면
    각 Worker 실행 시 시스템 프롬프트와 컨텍스트를 표시하는지 테스트합니다.
    """
    # 디버그 정보 활성화 확인
    debug_enabled = os.getenv("WORKER_DEBUG_INFO", "false").lower() in (
        "true", "1", "yes"
    )

    if not debug_enabled:
        pytest.skip("WORKER_DEBUG_INFO가 비활성화되어 있습니다")

    # Worker 초기화
    initialize_workers(config_path)
    assert len(_WORKER_AGENTS) > 0, "Worker가 초기화되지 않았습니다"

    # Planner Worker 테스트
    planner = _WORKER_AGENTS.get("planner")
    assert planner is not None, "Planner Agent를 찾을 수 없습니다"

    # Worker 정보 확인
    assert planner.system_prompt, "시스템 프롬프트가 비어있습니다"
    assert planner.config.tools, "도구 목록이 비어있습니다"


@pytest.mark.asyncio
async def test_parallel_tasks_tool_execution(config_path):
    """execute_parallel_tasks Tool이 제대로 작동하는지 테스트합니다."""
    # Worker 초기화
    initialize_workers(config_path)

    # 병렬 실행 계획 JSON 생성 (Mock)
    plan_json = {
        "execution_mode": "parallel",
        "tasks": [
            {
                "id": "task_1",
                "description": "src/test_module_a.py 파일 생성:\n\ndef hello_a():\n    return 'Hello from A'",
                "target_files": ["src/test_module_a.py"],
                "dependencies": [],
                "estimated_time": 100,
                "priority": 1
            },
            {
                "id": "task_2",
                "description": "src/test_module_b.py 파일 생성:\n\ndef hello_b():\n    return 'Hello from B'",
                "target_files": ["src/test_module_b.py"],
                "dependencies": [],
                "estimated_time": 100,
                "priority": 1
            },
            {
                "id": "task_3",
                "description": "src/test_module_c.py 파일 생성 (A, B에 의존):\n\nfrom test_module_a import hello_a\nfrom test_module_b import hello_b\n\ndef hello_c():\n    return f'{hello_a()} and {hello_b()}'",
                "target_files": ["src/test_module_c.py"],
                "dependencies": ["task_1", "task_2"],
                "estimated_time": 100,
                "priority": 2
            }
        ],
        "integration_notes": "test_module_c는 test_module_a와 test_module_b를 import하므로 먼저 생성되어야 합니다."
    }

    plan_json_str = json.dumps(plan_json, ensure_ascii=False, indent=2)

    # execute_parallel_tasks 호출
    result = await execute_parallel_tasks({
        "plan_json": plan_json_str
    })

    # 결과 검증
    assert result.get("success"), f"병렬 실행 실패: {result.get('error')}"

    # 메타데이터 검증
    if "metadata" in result:
        metadata = result["metadata"]
        assert metadata.get("completed_tasks", 0) > 0, "완료된 Task가 없습니다"
        assert metadata.get("success_rate", 0) > 0, "성공률이 0입니다"


@pytest.mark.asyncio
async def test_json_parsing_in_integration(config_path):
    """통합 테스트 시나리오에서 JSON 파싱이 올바르게 동작하는지 테스트합니다."""
    from src.domain.models.parallel_task import TaskExecutionPlan

    # 정상 JSON 테스트
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
                "description": "파일 B 생성",
                "target_files": ["b.py"],
                "dependencies": ["task_1"],
                "estimated_time": 300,
                "priority": 2
            }
        ],
        "integration_notes": "통합 테스트"
    }
    """

    plan = TaskExecutionPlan.from_json(plan_json)

    assert len(plan.tasks) == 2
    assert plan.tasks[0].id == "task_1"
    assert plan.tasks[1].id == "task_2"
    assert plan.tasks[1].dependencies == ["task_1"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
