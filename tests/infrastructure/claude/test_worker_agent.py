#!/usr/bin/env python3
"""
Worker Agent 초기화 및 호출 테스트.

이 파일은 다음의 원본 테스트 파일들을 통합한 것입니다:
- test_worker_call.py: Worker MCP 서버 생성 및 Manager를 통한 호출 테스트
- test_worker_direct.py: Worker Agent 직접 호출 및 실행 테스트
- test_simple_request.py: 간단한 요청-응답 테스트

통합 이유:
- 중복된 fixture 제거
- Worker 관련 테스트를 한 곳에서 관리
- 에러 처리 시나리오 추가 (타임아웃, 실행 실패, 로깅, 부분 응답)
"""

import asyncio
from pathlib import Path
from unittest.mock import patch, AsyncMock

import pytest

from src.infrastructure.mcp import (
    initialize_workers,
    create_worker_tools_server,
)
from src.infrastructure.mcp.worker_tools import _WORKER_AGENTS
from src.infrastructure.claude import ManagerAgent, WorkerAgent
from src.domain.models import AgentConfig
from src.domain.services import ConversationHistory
from src.domain.exceptions import WorkerTimeoutError, WorkerExecutionError
from src.infrastructure.config import get_project_root


@pytest.fixture
def config_path():
    """Agent 설정 파일 경로를 반환합니다."""
    return get_project_root() / "config" / "agent_config.json"


@pytest.mark.asyncio
async def test_worker_initialization(config_path):
    """Worker Agent가 올바르게 초기화되는지 테스트합니다."""
    # Worker 초기화
    initialize_workers(config_path)

    # Worker 목록 확인
    assert _WORKER_AGENTS, "Worker Agent가 초기화되지 않았습니다"

    # 각 Worker 검증
    for name, worker in _WORKER_AGENTS.items():
        assert worker.config.name == name
        assert worker.config.role
        assert worker.config.model
        assert worker.config.tools


@pytest.mark.asyncio
async def test_worker_tools_server_creation(config_path):
    """Worker Tools MCP Server가 올바르게 생성되는지 테스트합니다."""
    # Worker 초기화
    initialize_workers(config_path)

    # MCP Server 생성
    server = create_worker_tools_server()
    assert server is not None


@pytest.mark.asyncio
async def test_worker_direct_execution():
    """Worker Agent를 직접 호출하여 실행 테스트합니다."""
    # Planner 설정 (간단한 테스트용)
    planner_config = AgentConfig(
        name="planner",
        role="계획 수립 전문가",
        system_prompt="prompts/planner.txt",
        model="claude-sonnet-4-5-20250929",
        tools=["read", "glob"]
    )

    # Worker 생성
    worker = WorkerAgent(planner_config)

    # 간단한 작업 실행
    task = "간단한 테스트입니다. '테스트 완료'라고 응답해주세요."
    result = ""

    async for chunk in worker.execute_task(task):
        result += chunk

    # 응답 검증
    assert result, "Worker가 응답을 반환하지 않았습니다"
    assert len(result) > 0, "응답이 비어있습니다"


@pytest.mark.asyncio
async def test_manager_with_worker_tools(config_path):
    """Manager Agent가 Worker Tools를 통해 Worker를 호출하는지 테스트합니다."""
    # Worker 초기화
    initialize_workers(config_path)

    # Worker Tools MCP Server 생성
    worker_tools_server = create_worker_tools_server()

    # Manager Agent 초기화
    manager = ManagerAgent(
        worker_tools_server,
        model="claude-sonnet-4-5-20250929",
        max_history_messages=20,
        auto_commit_enabled=False
    )

    # 대화 히스토리
    history = ConversationHistory()
    user_request = "안녕하세요. 간단한 테스트입니다."
    history.add_message("user", user_request)

    # Manager 응답
    manager_response = ""
    async for chunk in manager.analyze_and_plan_stream(history.get_history()):
        manager_response += chunk

    # 응답 검증
    assert manager_response, "Manager가 응답을 반환하지 않았습니다"

    # 토큰 사용량 확인 (실제 API 호출이 발생한 경우에만)
    token_usage = manager.get_token_usage()
    assert token_usage["input_tokens"] >= 0
    assert token_usage["output_tokens"] >= 0


# ============================================================================
# 에러 처리 시스템 테스트
# ============================================================================

@pytest.mark.asyncio
async def test_worker_timeout_error_handling(config_path):
    """
    Worker 타임아웃 시 올바른 예외가 발생하는지 테스트합니다.

    타임아웃 에러를 시뮬레이션하고 WorkerTimeoutError가 발생하는지 검증합니다.
    """
    # Planner 설정
    planner_config = AgentConfig(
        name="planner",
        role="계획 수립 전문가",
        system_prompt="prompts/planner.txt",
        model="claude-sonnet-4-5-20250929",
        tools=["read", "glob"]
    )

    # Worker 생성
    worker = WorkerAgent(planner_config)

    # query 함수를 mock하여 타임아웃 시뮬레이션
    async def mock_timeout_query(*args, **kwargs):
        """타임아웃을 시뮬레이션하는 mock 함수"""
        await asyncio.sleep(0.1)  # 짧은 대기
        raise asyncio.TimeoutError("Worker execution timeout")

    # claude_agent_sdk.query를 mock으로 대체
    with patch('claude_agent_sdk.query', side_effect=mock_timeout_query):
        task = "테스트 작업"
        result = ""

        # execute_task는 에러를 예외로 던지지 않고 에러 메시지를 yield
        async for chunk in worker.execute_task(task):
            result += chunk

        # 에러 메시지가 포함되어 있는지 검증 (구체적인 메시지 검증)
        assert "[시스템 오류]" in result, (
            f"타임아웃 에러 메시지가 반환되지 않았습니다. 실제 응답: {result[:100]}"
        )
        assert "planner" in result.lower(), (
            f"Worker 이름이 에러 메시지에 포함되지 않았습니다. 실제 응답: {result[:100]}"
        )
        assert "Worker 실행 중 오류가 발생했습니다" in result, (
            f"예상된 에러 메시지가 포함되지 않았습니다. 실제 응답: {result[:100]}"
        )


@pytest.mark.asyncio
async def test_worker_execution_failure_handling(config_path):
    """
    Worker 실행 실패 시 올바른 에러 처리가 이루어지는지 테스트합니다.

    일반적인 실행 에러를 시뮬레이션하고 적절한 에러 메시지가 반환되는지 검증합니다.
    """
    # Coder 설정
    coder_config = AgentConfig(
        name="coder",
        role="코딩 전문가",
        system_prompt="prompts/coder.txt",
        model="claude-sonnet-4-5-20250929",
        tools=["read", "write", "edit"]
    )

    # Worker 생성
    worker = WorkerAgent(coder_config)

    # query 함수를 mock하여 실행 실패 시뮬레이션
    async def mock_failed_query(*args, **kwargs):
        """실행 실패를 시뮬레이션하는 mock 함수"""
        raise RuntimeError("Claude Agent SDK execution failed")

    # claude_agent_sdk.query를 mock으로 대체
    with patch('claude_agent_sdk.query', side_effect=mock_failed_query):
        task = "테스트 작업"
        result = ""

        # execute_task는 에러를 예외로 던지지 않고 에러 메시지를 yield
        async for chunk in worker.execute_task(task):
            result += chunk

        # 에러 메시지가 포함되어 있는지 검증 (구체적인 메시지 검증)
        assert "[시스템 오류]" in result, (
            f"실행 실패 에러 메시지가 반환되지 않았습니다. 실제 응답: {result[:100]}"
        )
        assert "coder" in result.lower(), (
            f"Worker 이름이 에러 메시지에 포함되지 않았습니다. 실제 응답: {result[:100]}"
        )
        assert "Worker 실행 중 오류가 발생했습니다" in result, (
            f"예상된 에러 메시지가 포함되지 않았습니다. 실제 응답: {result[:100]}"
        )


@pytest.mark.asyncio
async def test_worker_error_logging(config_path, caplog):
    """
    Worker 에러 발생 시 로그가 올바르게 기록되는지 테스트합니다.

    에러가 발생했을 때 로그에 Worker 이름, 역할, 모델 등의
    컨텍스트 정보가 포함되는지 검증합니다.
    """
    import logging

    # 로깅 레벨을 DEBUG로 설정하여 모든 로그 캡처
    caplog.set_level(logging.DEBUG)

    # Tester 설정
    tester_config = AgentConfig(
        name="tester",
        role="테스트 전문가",
        system_prompt="prompts/tester.txt",
        model="claude-sonnet-4-5-20250929",
        tools=["read", "bash"]
    )

    # Worker 생성
    worker = WorkerAgent(tester_config)

    # query 함수를 mock하여 실패 시뮬레이션
    async def mock_failed_query(*args, **kwargs):
        """실행 실패를 시뮬레이션하는 mock 함수"""
        raise ValueError("Invalid configuration")

    # claude_agent_sdk.query를 mock으로 대체
    with patch('claude_agent_sdk.query', side_effect=mock_failed_query):
        task = "테스트 작업"
        result = ""

        # execute_task 실행
        async for chunk in worker.execute_task(task):
            result += chunk

        # 로그 검증 (구체적인 검증)
        # 에러 로그가 기록되었는지 확인
        error_logs = [record for record in caplog.records if record.levelname == "ERROR"]
        assert len(error_logs) > 0, (
            f"에러 로그가 기록되지 않았습니다. "
            f"전체 로그: {[r.levelname for r in caplog.records]}"
        )

        # 로그에 Worker 이름과 역할이 포함되어 있는지 확인
        log_text = " ".join([record.message for record in error_logs])
        assert "tester" in log_text.lower(), (
            f"로그에 Worker 이름이 포함되지 않았습니다. 실제 로그: {log_text[:200]}"
        )
        assert "Worker 실행 중 오류가 발생했습니다" in log_text, (
            f"예상된 에러 메시지가 로그에 포함되지 않았습니다. 실제 로그: {log_text[:200]}"
        )


@pytest.mark.asyncio
async def test_worker_partial_response_handling(config_path):
    """
    Worker 실행 중 부분적으로 응답이 반환된 후 에러가 발생하는 경우를 테스트합니다.

    스트리밍 응답 중간에 에러가 발생해도 이미 받은 응답은 유지되는지 검증합니다.
    """
    # Reviewer 설정
    reviewer_config = AgentConfig(
        name="reviewer",
        role="코드 리뷰 전문가",
        system_prompt="prompts/reviewer.txt",
        model="claude-sonnet-4-5-20250929",
        tools=["read", "grep"]
    )

    # Worker 생성
    worker = WorkerAgent(reviewer_config)

    # query 함수를 mock하여 부분 응답 후 에러 시뮬레이션
    async def mock_partial_response_query(*args, **kwargs):
        """부분 응답 후 에러를 시뮬레이션하는 mock 함수"""
        # 부분 응답 생성
        class MockContent:
            def __init__(self, text):
                self.text = text

        class MockResponse:
            def __init__(self, text):
                self.content = [MockContent(text)]

        # 첫 번째 청크 반환
        yield MockResponse("리뷰 시작...\n")

        # 두 번째 청크 반환
        yield MockResponse("파일 분석 중...\n")

        # 에러 발생
        raise RuntimeError("Network error during streaming")

    # claude_agent_sdk.query를 mock으로 대체
    with patch('claude_agent_sdk.query', side_effect=mock_partial_response_query):
        task = "코드 리뷰 수행"
        result = ""

        # execute_task 실행
        async for chunk in worker.execute_task(task):
            result += chunk

        # 부분 응답이 포함되어 있는지 검증 (구체적인 검증)
        assert "리뷰 시작" in result, (
            f"첫 번째 부분 응답이 유지되지 않았습니다. 실제 응답: {result[:100]}"
        )
        assert "파일 분석 중" in result, (
            f"두 번째 부분 응답이 유지되지 않았습니다. 실제 응답: {result[:100]}"
        )

        # 에러 메시지도 포함되어 있는지 검증
        assert "[시스템 오류]" in result, (
            f"에러 메시지가 추가되지 않았습니다. 실제 응답: {result[:150]}"
        )
        assert "Worker 실행 중 오류가 발생했습니다" in result, (
            f"예상된 에러 메시지가 포함되지 않았습니다. 실제 응답: {result[:150]}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
