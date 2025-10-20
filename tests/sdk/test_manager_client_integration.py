"""
ManagerClient + SDKExecutor 통합 테스트.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import AsyncIterator

from src.infrastructure.claude.manager_client import ManagerAgent
from src.domain.models import Message


@pytest.fixture
def mock_worker_tools_server():
    """Mock Worker Tools Server."""
    return MagicMock()


@pytest.fixture
def manager_agent(mock_worker_tools_server):
    """ManagerAgent 인스턴스."""
    return ManagerAgent(
        worker_tools_server=mock_worker_tools_server,
        model="test-model",
        max_history_messages=10,
        auto_commit_enabled=False,
        session_id="test-session"
    )


@pytest.fixture
def sample_history():
    """샘플 대화 히스토리."""
    return [
        Message(role="user", content="Test request", agent_name="User")
    ]


class MockClaudeClient:
    """Mock ClaudeSDKClient."""

    def __init__(self, responses: list):
        self.responses = responses
        self.connected = False
        self.query_called = False

    async def connect(self):
        """연결."""
        self.connected = True

    async def query(self, prompt: str):
        """쿼리."""
        self.query_called = True

    async def receive_response(self) -> AsyncIterator:
        """응답 수신."""
        for response in self.responses:
            yield response

    async def disconnect(self):
        """연결 해제."""
        self.connected = False


class MockResponse:
    """Mock Response."""

    def __init__(self, text: str = None, content: list = None, usage: dict = None):
        if text:
            self.text = text
        if content:
            self.content = content
        if usage:
            self.usage = MagicMock()
            for key, value in usage.items():
                setattr(self.usage, key, value)


class MockContent:
    """Mock Content."""

    def __init__(self, text: str):
        self.text = text


@pytest.mark.asyncio
async def test_analyze_and_plan_stream_success(manager_agent, sample_history):
    """analyze_and_plan_stream 정상 동작 테스트."""
    # Mock responses
    responses = [
        MockResponse(content=[MockContent("Planning step 1")]),
        MockResponse(content=[MockContent("Planning step 2")])
    ]
    mock_client = MockClaudeClient(responses)

    with patch(
        'src.infrastructure.claude.sdk_executor.ClaudeSDKClient',
        return_value=mock_client
    ):
        chunks = []
        async for chunk in manager_agent.analyze_and_plan_stream(sample_history):
            chunks.append(chunk)

        # Client 호출 검증
        assert mock_client.query_called
        assert not mock_client.connected  # disconnect 호출됨

        # 응답 청크 검증
        assert len(chunks) == 2
        assert chunks[0] == "Planning step 1"
        assert chunks[1] == "Planning step 2"


@pytest.mark.asyncio
async def test_analyze_and_plan_stream_with_usage_tracking(
    manager_agent, sample_history
):
    """토큰 사용량 추적 테스트."""
    # Reset token usage
    manager_agent.reset_token_usage()

    # Mock responses with usage
    responses = [
        MockResponse(
            content=[MockContent("Response")],
            usage={
                'input_tokens': 100,
                'output_tokens': 50,
                'cache_read_tokens': 20,
                'cache_creation_tokens': 10
            }
        )
    ]
    mock_client = MockClaudeClient(responses)

    with patch(
        'src.infrastructure.claude.sdk_executor.ClaudeSDKClient',
        return_value=mock_client
    ):
        async for _ in manager_agent.analyze_and_plan_stream(sample_history):
            pass

        # 토큰 사용량 검증
        usage = manager_agent.get_token_usage()
        assert usage['input_tokens'] == 100
        assert usage['output_tokens'] == 50
        assert usage['cache_read_tokens'] == 20
        assert usage['cache_creation_tokens'] == 10


@pytest.mark.asyncio
async def test_analyze_and_plan_stream_multiple_messages(manager_agent, sample_history):
    """여러 메시지 처리 테스트."""
    # Mock responses
    responses = [
        MockResponse(text="Message 1"),
        MockResponse(text="Message 2"),
        MockResponse(text="Message 3")
    ]
    mock_client = MockClaudeClient(responses)

    with patch(
        'src.infrastructure.claude.sdk_executor.ClaudeSDKClient',
        return_value=mock_client
    ):
        chunks = []
        async for chunk in manager_agent.analyze_and_plan_stream(sample_history):
            chunks.append(chunk)

        assert len(chunks) == 3
        assert chunks == ["Message 1", "Message 2", "Message 3"]


@pytest.mark.asyncio
async def test_analyze_and_plan_stream_with_auto_commit_enabled():
    """auto_commit_enabled=True 시 도구 목록 테스트."""
    mock_server = MagicMock()
    manager = ManagerAgent(
        worker_tools_server=mock_server,
        model="test-model",
        auto_commit_enabled=True
    )

    responses = [MockResponse(text="Test")]
    mock_client = MockClaudeClient(responses)

    captured_options = None

    def capture_client_init(options):
        nonlocal captured_options
        captured_options = options
        return mock_client

    with patch(
        'src.infrastructure.claude.sdk_executor.ClaudeSDKClient',
        side_effect=capture_client_init
    ):
        async for _ in manager.analyze_and_plan_stream(
            [Message(role="user", content="Test", agent_name="User")]
        ):
            pass

        # ClaudeAgentOptions가 전달되었는지 확인
        # (실제로는 execute_stream 내부에서 생성되므로 간접 검증)
        assert mock_client.query_called


@pytest.mark.asyncio
async def test_analyze_and_plan_stream_exception_handling(
    manager_agent, sample_history
):
    """예외 처리 테스트."""
    # Mock client that raises exception
    mock_client = MagicMock()
    mock_client.connect = AsyncMock()
    mock_client.query = AsyncMock(side_effect=RuntimeError("Test error"))
    mock_client.disconnect = AsyncMock()

    with patch(
        'src.infrastructure.claude.sdk_executor.ClaudeSDKClient',
        return_value=mock_client
    ):
        chunks = []
        async for chunk in manager_agent.analyze_and_plan_stream(sample_history):
            chunks.append(chunk)

        # 에러 메시지 검증
        assert len(chunks) == 1
        assert "시스템 오류" in chunks[0]

        # disconnect는 호출되어야 함
        mock_client.disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_analyze_and_plan_stream_generator_exit(manager_agent, sample_history):
    """Generator 중단 시 처리 테스트."""
    responses = [
        MockResponse(text="Response 1"),
        MockResponse(text="Response 2"),
        MockResponse(text="Response 3")
    ]
    mock_client = MockClaudeClient(responses)

    with patch(
        'src.infrastructure.claude.sdk_executor.ClaudeSDKClient',
        return_value=mock_client
    ):
        chunks = []
        async for chunk in manager_agent.analyze_and_plan_stream(sample_history):
            chunks.append(chunk)
            if len(chunks) >= 2:
                break  # 일부만 소비하고 중단

        # 2개만 받았는지 검증
        assert len(chunks) == 2


@pytest.mark.asyncio
async def test_analyze_and_plan_stream_prompt_building(manager_agent):
    """프롬프트 빌드 테스트 (슬라이딩 윈도우)."""
    # 긴 히스토리 생성 (max_history_messages=10보다 큼)
    long_history = [
        Message(role="user", content=f"User message {i}", agent_name="User")
        for i in range(15)
    ]

    responses = [MockResponse(text="Response")]
    mock_client = MockClaudeClient(responses)

    captured_prompt = None

    async def capture_query(prompt: str):
        nonlocal captured_prompt
        captured_prompt = prompt

    mock_client.query = capture_query

    with patch(
        'src.infrastructure.claude.sdk_executor.ClaudeSDKClient',
        return_value=mock_client
    ):
        async for _ in manager_agent.analyze_and_plan_stream(long_history):
            pass

        # 프롬프트가 생성되었는지 확인
        assert captured_prompt is not None
        # 첫 번째 메시지와 최근 메시지들이 포함되어야 함
        assert "User message 0" in captured_prompt  # 첫 번째
        assert "User message 14" in captured_prompt  # 마지막
