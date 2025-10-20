"""
Pytest 공통 설정 및 Fixtures

모든 테스트에서 공유되는 fixtures를 정의합니다.
"""

import pytest
import inspect
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from unittest.mock import Mock, AsyncMock, patch

from src.domain.models import Message, AgentConfig, SessionResult, Role
from tests.mocks.claude_api_mock import mock_claude_api


# ============================================================================
# 데이터 모델 Fixtures
# ============================================================================

@pytest.fixture
def sample_message() -> Message:
    """샘플 메시지 객체"""
    return Message(
        role=Role.USER,
        content="Hello, world!",
        timestamp=datetime(2024, 1, 1, 12, 0, 0)
    )


@pytest.fixture
def sample_messages() -> List[Message]:
    """샘플 메시지 리스트"""
    return [
        Message(role=Role.USER, content="사용자 요청", timestamp=datetime(2024, 1, 1, 12, 0, 0)),
        Message(role=Role.MANAGER, content="작업 계획", timestamp=datetime(2024, 1, 1, 12, 1, 0)),
        Message(role=Role.AGENT, content="작업 완료", agent_name="planner", timestamp=datetime(2024, 1, 1, 12, 2, 0)),
    ]


@pytest.fixture
def sample_agent_config() -> AgentConfig:
    """샘플 에이전트 설정"""
    return AgentConfig(
        name="test_agent",
        role="Test Agent",
        system_prompt="You are a test agent.",
        tools=["read", "write"],
        model="claude-sonnet-4"
    )


@pytest.fixture
def sample_agent_configs() -> List[AgentConfig]:
    """여러 에이전트 설정"""
    return [
        AgentConfig(
            name="planner",
            role="Planning Agent",
            system_prompt="You are a planner.",
            tools=["read", "glob", "grep"],
            model="claude-sonnet-4"
        ),
        AgentConfig(
            name="coder",
            role="Coding Agent",
            system_prompt="You are a coder.",
            tools=["read", "write", "edit", "bash"],
            model="claude-sonnet-4"
        ),
        AgentConfig(
            name="tester",
            role="Testing Agent",
            system_prompt="You are a tester.",
            tools=["read", "bash"],
            model="claude-sonnet-4"
        ),
    ]


@pytest.fixture
def sample_session_result() -> SessionResult:
    """샘플 세션 결과"""
    return SessionResult(
        status="completed",
        files_modified=["test.py", "main.py"],
        tests_passed=True,
        error_message=None
    )


# ============================================================================
# Mock SDK Fixtures
# ============================================================================

@pytest.fixture
def mock_claude():
    """Mock Claude API"""
    mock_claude_api.reset()
    return mock_claude_api


@pytest.fixture
def temp_config_dir(tmp_path: Path) -> Path:
    """Temporary config directory"""
    return tmp_path


@pytest.fixture
def mock_env(monkeypatch):
    """Mock environment variables for logging"""
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("LOG_FORMAT", "console")
    monkeypatch.setenv("LOG_DIR", "logs")


@pytest.fixture
def mock_claude_agent_sdk():
    """
    Claude Agent SDK의 query 함수를 mock합니다.

    Returns:
        Mock 객체
    """
    with patch('claude_agent_sdk.query') as mock_query:
        # 기본 응답 설정
        mock_response = Mock()
        mock_response.content = [Mock(text="Mocked response")]

        # AsyncIterator 형태로 반환
        async def async_generator():
            yield mock_response

        mock_query.return_value = async_generator()
        yield mock_query


@pytest.fixture
def mock_sdk_streaming_response():
    """
    Claude Agent SDK의 스트리밍 응답을 mock합니다.

    Returns:
        응답 청크 리스트
    """
    async def create_streaming_response(texts: List[str]):
        """주어진 텍스트 리스트를 스트리밍 응답으로 변환"""
        for text in texts:
            mock_response = Mock()
            mock_response.content = [Mock(text=text)]
            yield mock_response

    return create_streaming_response


# ============================================================================
# 파일 시스템 Fixtures
# ============================================================================

@pytest.fixture
def temp_config_file(tmp_path: Path) -> Path:
    """임시 에이전트 설정 파일 생성"""
    config_content = """[
    {
        "name": "planner",
        "role": "Planning Agent",
        "system_prompt": "You are a planner.",
        "tools": ["read", "glob", "grep"],
        "model": "claude-sonnet-4"
    },
    {
        "name": "coder",
        "role": "Coding Agent",
        "system_prompt": "You are a coder.",
        "tools": ["read", "write", "edit", "bash"],
        "model": "claude-sonnet-4"
    }
]"""
    config_file = tmp_path / "agent_config.json"
    config_file.write_text(config_content)
    return config_file


@pytest.fixture
def temp_prompt_file(tmp_path: Path) -> Path:
    """임시 시스템 프롬프트 파일 생성"""
    prompt_content = "This is a test system prompt."
    prompt_file = tmp_path / "system_prompt.txt"
    prompt_file.write_text(prompt_content)
    return prompt_file


# ============================================================================
# 에이전트 Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_manager_agent():
    """
    ManagerAgent를 mock합니다.

    Returns:
        Mock ManagerAgent
    """
    # Mock ManagerAgent without importing (to avoid import errors)
    mock_manager = Mock()
    mock_manager.model = "claude-sonnet-4-5-20250929"

    # analyze_and_plan 메서드를 async mock으로 설정
    mock_manager.analyze_and_plan = AsyncMock(
        return_value="**작업 분석:**\n테스트 작업\n\n**다음 단계:**\n@planner 계획 수립"
    )

    return mock_manager


@pytest.fixture
def mock_worker_agent(sample_agent_config):
    """
    WorkerAgent를 mock합니다.

    Args:
        sample_agent_config: 에이전트 설정 fixture

    Returns:
        Mock WorkerAgent
    """
    # Mock WorkerAgent without importing (to avoid import errors)
    mock_worker = Mock()
    mock_worker.config = sample_agent_config
    mock_worker.system_prompt = sample_agent_config.system_prompt

    # execute_task 메서드를 async generator로 설정
    async def mock_execute_task(task_description: str):
        yield "Task started\n"
        yield "Processing...\n"
        yield "Task completed\n"

    mock_worker.execute_task = mock_execute_task

    return mock_worker


# ============================================================================
# 환경 설정 Fixtures
# ============================================================================

@pytest.fixture
def mock_env_vars(monkeypatch):
    """
    환경 변수를 mock합니다.

    Args:
        monkeypatch: pytest의 monkeypatch fixture
    """
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "test_token_12345")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test_api_key_67890")


@pytest.fixture(autouse=True)
def reset_logging():
    """
    각 테스트 전후로 로깅 설정을 리셋합니다.
    """
    import logging

    # 테스트 전: 로깅 레벨을 WARNING으로 설정 (테스트 출력 최소화)
    logging.basicConfig(level=logging.WARNING)

    yield

    # 테스트 후: 로거 정리
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)


# ============================================================================
# 유틸리티 Fixtures
# ============================================================================

@pytest.fixture
def captured_output():
    """
    표준 출력을 캡처하는 컨텍스트 매니저를 제공합니다.

    Usage:
        with captured_output() as output:
            print("test")
        assert "test" in output.getvalue()
    """
    from io import StringIO
    from contextlib import redirect_stdout

    def _capture():
        from contextlib import contextmanager

        @contextmanager
        def capture():
            output = StringIO()
            with redirect_stdout(output):
                yield output

        return capture()

    return _capture


@pytest.fixture
def freeze_time():
    """
    시간을 고정합니다 (테스트 재현성 향상).

    Usage:
        with freeze_time("2024-01-01 12:00:00"):
            # 시간이 고정된 상태에서 테스트
    """
    from unittest.mock import patch
    from datetime import datetime

    def _freeze(frozen_time: str):
        from contextlib import contextmanager

        @contextmanager
        def freeze():
            frozen_dt = datetime.fromisoformat(frozen_time)
            with patch('datetime.datetime') as mock_datetime:
                mock_datetime.now.return_value = frozen_dt
                mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
                yield mock_datetime

        return freeze()

    return _freeze


# ============================================================================
# Pytest 설정
# ============================================================================

def pytest_configure(config):
    """pytest 초기 설정"""
    config.addinivalue_line(
        "markers", "unit: 단위 테스트 (독립적인 기능 테스트)"
    )
    config.addinivalue_line(
        "markers", "integration: 통합 테스트 (여러 컴포넌트 통합)"
    )
    config.addinivalue_line(
        "markers", "slow: 실행 시간이 긴 테스트"
    )
    config.addinivalue_line(
        "markers", "requires_api: API 호출이 필요한 테스트"
    )


def pytest_collection_modifyitems(config, items):
    """테스트 수집 후 자동으로 마커 추가"""
    for item in items:
        # unit 디렉토리의 테스트에 @pytest.mark.unit 자동 추가
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)

        # integration 디렉토리의 테스트에 @pytest.mark.integration 자동 추가
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)

        # async 함수에 @pytest.mark.asyncio 자동 추가
        if inspect.iscoroutinefunction(item.function):
            item.add_marker(pytest.mark.asyncio)
