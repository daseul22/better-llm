"""
src/infrastructure/claude/sdk_executor.py 테스트.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import AsyncIterator

from src.infrastructure.claude.sdk_executor import (
    SDKExecutionConfig,
    SDKResponseHandler,
    ManagerResponseHandler,
    WorkerResponseHandler,
    ManagerSDKExecutor,
    WorkerSDKExecutor
)
# AgentExecutionError는 존재하지 않으므로 import 제거


class TestSDKExecutionConfig:
    """SDKExecutionConfig 테스트."""

    def test_default_config(self):
        """기본 설정 생성 테스트."""
        config = SDKExecutionConfig()

        assert config.model == "claude-sonnet-4-5-20250929"
        assert config.max_tokens == 8000
        assert config.temperature == 0.7
        assert config.timeout == 300
        assert config.cli_path is None
        assert config.permission_mode == "bypassPermissions"

    def test_custom_config(self):
        """커스텀 설정 생성 테스트."""
        config = SDKExecutionConfig(
            model="claude-sonnet-3-5-20241022",
            max_tokens=4000,
            temperature=0.5,
            timeout=600,
            cli_path="/custom/path",
            permission_mode="requireApproval"
        )

        assert config.model == "claude-sonnet-3-5-20241022"
        assert config.max_tokens == 4000
        assert config.temperature == 0.5
        assert config.timeout == 600
        assert config.cli_path == "/custom/path"
        assert config.permission_mode == "requireApproval"


class MockResponse:
    """Mock SDK Response."""

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


class TestSDKResponseHandler:
    """SDKResponseHandler 추상 클래스 테스트."""

    def test_extract_text_from_response_with_content_list(self):
        """content 리스트에서 텍스트 추출 테스트."""
        handler = ManagerResponseHandler()  # 구체 클래스 사용
        response = MockResponse(content=[MockContent("Hello")])

        text = handler.extract_text_from_response(response)

        assert text == "Hello"

    def test_extract_text_from_response_with_text_attr(self):
        """text 속성에서 텍스트 추출 테스트."""
        handler = ManagerResponseHandler()
        response = MockResponse(text="Hello World")

        text = handler.extract_text_from_response(response)

        assert text == "Hello World"

    def test_extract_text_from_response_no_text(self):
        """텍스트가 없는 경우 None 반환 테스트."""
        handler = ManagerResponseHandler()
        response = MagicMock()
        # text, content 속성이 없는 객체

        text = handler.extract_text_from_response(response)

        assert text is None


class TestManagerResponseHandler:
    """ManagerResponseHandler 테스트."""

    @pytest.mark.asyncio
    async def test_process_response_with_text(self):
        """텍스트가 있는 응답 처리 테스트."""
        handler = ManagerResponseHandler()
        response = MockResponse(text="Test response")

        chunks = []
        async for chunk in handler.process_response(response):
            chunks.append(chunk)

        assert len(chunks) == 1
        assert chunks[0] == "Test response"

    @pytest.mark.asyncio
    async def test_process_response_with_usage_callback(self):
        """Usage 콜백 호출 테스트."""
        usage_callback = MagicMock()
        handler = ManagerResponseHandler(usage_callback=usage_callback)
        response = MockResponse(
            text="Test",
            usage={
                'input_tokens': 100,
                'output_tokens': 50,
                'cache_read_tokens': 20,
                'cache_creation_tokens': 10
            }
        )

        async for _ in handler.process_response(response):
            pass

        # 콜백 호출 검증
        usage_callback.assert_called_once()
        call_args = usage_callback.call_args[0][0]
        assert call_args['input_tokens'] == 100
        assert call_args['output_tokens'] == 50
        assert call_args['cache_read_tokens'] == 20
        assert call_args['cache_creation_tokens'] == 10

    @pytest.mark.asyncio
    async def test_process_response_without_usage(self):
        """Usage 정보가 없는 응답 처리 테스트."""
        usage_callback = MagicMock()
        handler = ManagerResponseHandler(usage_callback=usage_callback)
        response = MockResponse(text="Test")

        async for _ in handler.process_response(response):
            pass

        # 콜백이 호출되지 않아야 함
        usage_callback.assert_not_called()


class TestWorkerResponseHandler:
    """WorkerResponseHandler 테스트."""

    @pytest.mark.asyncio
    async def test_process_response_with_text(self):
        """텍스트가 있는 응답 처리 테스트."""
        handler = WorkerResponseHandler()
        response = MockResponse(text="Worker response")

        chunks = []
        async for chunk in handler.process_response(response):
            chunks.append(chunk)

        assert len(chunks) == 1
        assert chunks[0] == "Worker response"

    @pytest.mark.asyncio
    async def test_process_response_fallback_to_str(self):
        """텍스트 추출 실패 시 str() 변환 테스트."""
        handler = WorkerResponseHandler()
        response = MagicMock()
        response.__str__ = lambda self: "Fallback string"
        # text, content 속성이 없는 객체

        chunks = []
        async for chunk in handler.process_response(response):
            chunks.append(chunk)

        assert len(chunks) == 1
        assert "Fallback" in chunks[0] or "Mock" in chunks[0]


class TestManagerSDKExecutor:
    """ManagerSDKExecutor 테스트."""

    @pytest.fixture
    def mock_client_class(self):
        """Mock ClaudeSDKClient 클래스."""
        with patch('src.infrastructure.claude.sdk_executor.ClaudeSDKClient') as mock:
            yield mock

    @pytest.fixture
    def config(self):
        """테스트 설정."""
        return SDKExecutionConfig(
            model="test-model",
            cli_path="/test/cli"
        )

    @pytest.fixture
    def response_handler(self):
        """Mock ResponseHandler."""
        handler = MagicMock(spec=ManagerResponseHandler)

        async def mock_process(response):
            yield "processed text"

        handler.process_response = mock_process
        return handler

    @pytest.mark.asyncio
    async def test_execute_stream_success(
        self, mock_client_class, config, response_handler
    ):
        """정상 스트림 실행 테스트."""
        # Mock client 인스턴스
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        # Mock receive_response
        async def mock_receive():
            yield MockResponse(text="Response 1")
            yield MockResponse(text="Response 2")

        mock_client.receive_response.return_value = mock_receive()

        executor = ManagerSDKExecutor(
            config=config,
            mcp_servers={"test": "server"},
            allowed_tools=["tool1", "tool2"],
            response_handler=response_handler
        )

        chunks = []
        async for chunk in executor.execute_stream("Test prompt"):
            chunks.append(chunk)

        # Client 메서드 호출 검증
        mock_client.connect.assert_awaited_once()
        mock_client.query.assert_awaited_once_with("Test prompt")
        mock_client.disconnect.assert_awaited_once()

        # 응답 청크 검증
        assert len(chunks) == 2
        assert all(chunk == "processed text" for chunk in chunks)

    @pytest.mark.asyncio
    async def test_execute_stream_exception_handling(
        self, mock_client_class, config, response_handler
    ):
        """예외 처리 테스트."""
        # Mock client 인스턴스
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        # query()에서 예외 발생
        mock_client.query.side_effect = RuntimeError("Test error")

        executor = ManagerSDKExecutor(
            config=config,
            mcp_servers={"test": "server"},
            allowed_tools=["tool1"],
            response_handler=response_handler
        )

        chunks = []
        async for chunk in executor.execute_stream("Test prompt"):
            chunks.append(chunk)

        # 에러 메시지 검증
        assert len(chunks) == 1
        assert "시스템 오류" in chunks[0]

        # disconnect는 호출되어야 함
        mock_client.disconnect.assert_awaited_once()


class TestWorkerSDKExecutor:
    """WorkerSDKExecutor 테스트."""

    @pytest.fixture
    def config(self):
        """테스트 설정."""
        return SDKExecutionConfig(
            model="test-model",
            cli_path="/test/cli"
        )

    @pytest.fixture
    def response_handler(self):
        """Mock ResponseHandler."""
        handler = MagicMock(spec=WorkerResponseHandler)

        async def mock_process(response):
            yield "processed text"

        handler.process_response = mock_process
        return handler

    @pytest.mark.asyncio
    async def test_execute_stream_success(self, config, response_handler):
        """정상 스트림 실행 테스트."""
        # Mock query 함수
        async def mock_query(prompt, options):
            yield MockResponse(text="Response 1")
            yield MockResponse(text="Response 2")

        with patch('src.infrastructure.claude.sdk_executor.query', mock_query):
            executor = WorkerSDKExecutor(
                config=config,
                allowed_tools=["tool1", "tool2"],
                response_handler=response_handler,
                worker_name="TestWorker"
            )

            chunks = []
            async for chunk in executor.execute_stream("Test prompt"):
                chunks.append(chunk)

            # 응답 청크 검증
            assert len(chunks) == 2
            assert all(chunk == "processed text" for chunk in chunks)

    @pytest.mark.asyncio
    async def test_execute_stream_exception_handling(self, config, response_handler):
        """예외 처리 테스트."""
        # Mock query 함수 (예외 발생)
        async def mock_query(prompt, options):
            raise RuntimeError("Test error")
            yield  # unreachable but needed for generator

        with patch('src.infrastructure.claude.sdk_executor.query', mock_query):
            executor = WorkerSDKExecutor(
                config=config,
                allowed_tools=["tool1"],
                response_handler=response_handler,
                worker_name="TestWorker"
            )

            chunks = []
            async for chunk in executor.execute_stream("Test prompt"):
                chunks.append(chunk)

            # 에러 메시지 검증
            assert len(chunks) == 1
            assert "시스템 오류" in chunks[0]
            assert "TestWorker" in chunks[0]
