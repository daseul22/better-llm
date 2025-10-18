"""
WorkerAgent 단위 테스트

WorkerAgent의 기능을 독립적으로 테스트합니다.
Claude Agent SDK와 파일 시스템은 mock으로 대체합니다.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, mock_open
from pathlib import Path

from src.worker_agent import WorkerAgent
from src.models import AgentConfig


class TestWorkerAgent:
    """WorkerAgent 클래스 테스트"""

    def test_worker_agent_initialization(self, sample_agent_config):
        """워커 에이전트 초기화 테스트"""
        worker = WorkerAgent(sample_agent_config)

        assert worker.config == sample_agent_config
        assert worker.system_prompt is not None

    def test_worker_agent_with_inline_prompt(self):
        """인라인 시스템 프롬프트로 초기화 테스트"""
        config = AgentConfig(
            name="test_agent",
            role="Test Agent",
            system_prompt="This is an inline prompt.",
            tools=["read"],
            model="claude-sonnet-4"
        )

        worker = WorkerAgent(config)

        assert worker.system_prompt == "This is an inline prompt."

    def test_repr(self, sample_agent_config):
        """__repr__ 테스트"""
        worker = WorkerAgent(sample_agent_config)
        repr_str = repr(worker)

        assert "WorkerAgent" in repr_str
        assert "test_agent" in repr_str
        assert "Test Agent" in repr_str


class TestLoadSystemPrompt:
    """_load_system_prompt 메서드 테스트"""

    def test_load_prompt_from_inline_text(self):
        """인라인 텍스트에서 프롬프트 로드 테스트"""
        config = AgentConfig(
            name="test_agent",
            role="Test Agent",
            system_prompt="Inline prompt text",
            tools=["read"],
            model="claude-sonnet-4"
        )

        worker = WorkerAgent(config)

        assert worker.system_prompt == "Inline prompt text"

    def test_load_prompt_from_file(self, temp_prompt_file):
        """파일에서 프롬프트 로드 테스트"""
        config = AgentConfig(
            name="test_agent",
            role="Test Agent",
            system_prompt=str(temp_prompt_file),
            tools=["read"],
            model="claude-sonnet-4"
        )

        worker = WorkerAgent(config)

        assert worker.system_prompt == "This is a test system prompt."

    def test_load_prompt_from_relative_path(self, temp_prompt_file, monkeypatch):
        """상대 경로에서 프롬프트 로드 테스트"""
        # 현재 작업 디렉토리를 temp_prompt_file의 부모로 설정
        monkeypatch.chdir(temp_prompt_file.parent)

        config = AgentConfig(
            name="test_agent",
            role="Test Agent",
            system_prompt=temp_prompt_file.name,  # 파일명만
            tools=["read"],
            model="claude-sonnet-4"
        )

        worker = WorkerAgent(config)

        assert worker.system_prompt == "This is a test system prompt."

    def test_load_prompt_file_not_found(self):
        """존재하지 않는 파일에서 프롬프트 로드 시 기본값 사용 테스트"""
        config = AgentConfig(
            name="test_agent",
            role="Test Agent",
            system_prompt="nonexistent_file.txt",
            tools=["read"],
            model="claude-sonnet-4"
        )

        worker = WorkerAgent(config)

        # 파일을 찾지 못하면 원본 문자열을 그대로 사용
        assert worker.system_prompt == "nonexistent_file.txt"

    def test_load_prompt_with_path_separator(self, tmp_path):
        """경로 구분자가 있으면 파일로 인식하는지 테스트"""
        prompt_file = tmp_path / "prompts" / "test.txt"
        prompt_file.parent.mkdir(parents=True, exist_ok=True)
        prompt_file.write_text("Loaded from subdirectory")

        config = AgentConfig(
            name="test_agent",
            role="Test Agent",
            system_prompt=str(prompt_file),
            tools=["read"],
            model="claude-sonnet-4"
        )

        worker = WorkerAgent(config)

        assert worker.system_prompt == "Loaded from subdirectory"

    def test_load_prompt_with_txt_extension(self, temp_prompt_file):
        """.txt 확장자가 있으면 파일로 인식하는지 테스트"""
        config = AgentConfig(
            name="test_agent",
            role="Test Agent",
            system_prompt=str(temp_prompt_file),
            tools=["read"],
            model="claude-sonnet-4"
        )

        worker = WorkerAgent(config)

        assert worker.system_prompt == "This is a test system prompt."

    def test_load_prompt_error_handling(self):
        """프롬프트 로드 중 에러 발생 시 기본값 사용 테스트"""
        config = AgentConfig(
            name="test_agent",
            role="Test Agent",
            system_prompt="/root/no_permission.txt",  # 권한 없는 경로
            tools=["read"],
            model="claude-sonnet-4"
        )

        # 에러 발생해도 예외를 발생시키지 않고 기본값 사용
        worker = WorkerAgent(config)

        assert worker.system_prompt == "/root/no_permission.txt"


class TestExecuteTask:
    """execute_task 메서드 테스트"""

    @pytest.mark.asyncio
    async def test_execute_task_success(self, sample_agent_config, mock_claude_agent_sdk):
        """작업 실행 성공 테스트"""
        worker = WorkerAgent(sample_agent_config)

        # 응답 수집
        responses = []
        async for chunk in worker.execute_task("Read the file"):
            responses.append(chunk)

        # 응답이 있는지 확인
        assert len(responses) > 0

        # SDK가 호출되었는지 확인
        mock_claude_agent_sdk.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_task_sdk_options(self, sample_agent_config, mock_claude_agent_sdk):
        """SDK 옵션이 올바르게 전달되는지 테스트"""
        worker = WorkerAgent(sample_agent_config)

        async for _ in worker.execute_task("Test task"):
            pass

        # call_args로 전달된 인자 확인
        call_args = mock_claude_agent_sdk.call_args

        assert call_args is not None
        assert "options" in call_args.kwargs
        options = call_args.kwargs["options"]

        # AgentConfig의 설정이 올바르게 전달되었는지 확인
        assert options.model == sample_agent_config.model
        assert options.allowed_tools == sample_agent_config.tools
        assert options.permission_mode == "bypassPermissions"

    @pytest.mark.asyncio
    async def test_execute_task_combines_prompt_and_task(self, sample_agent_config, mock_claude_agent_sdk):
        """시스템 프롬프트와 작업 설명이 결합되는지 테스트"""
        worker = WorkerAgent(sample_agent_config)
        task_description = "Read file.py and analyze it"

        async for _ in worker.execute_task(task_description):
            pass

        # 프롬프트 확인
        call_args = mock_claude_agent_sdk.call_args
        prompt = call_args.kwargs["prompt"]

        # 시스템 프롬프트와 작업 설명이 모두 포함되어 있는지 확인
        assert sample_agent_config.system_prompt in prompt
        assert task_description in prompt

    @pytest.mark.asyncio
    async def test_execute_task_streaming(self, sample_agent_config):
        """스트리밍 응답을 올바르게 처리하는지 테스트"""
        worker = WorkerAgent(sample_agent_config)

        # 여러 청크로 나뉜 스트리밍 응답 mock
        async def mock_streaming():
            responses = [
                Mock(content=[Mock(text="Chunk 1\n")]),
                Mock(content=[Mock(text="Chunk 2\n")]),
                Mock(content=[Mock(text="Chunk 3\n")])
            ]
            for resp in responses:
                yield resp

        with patch('claude_agent_sdk.query', return_value=mock_streaming()):
            chunks = []
            async for chunk in worker.execute_task("Test task"):
                chunks.append(chunk)

            # 모든 청크가 개별적으로 전달되었는지 확인
            assert len(chunks) == 3
            assert chunks[0] == "Chunk 1\n"
            assert chunks[1] == "Chunk 2\n"
            assert chunks[2] == "Chunk 3\n"

    @pytest.mark.asyncio
    async def test_execute_task_error_handling(self, sample_agent_config):
        """SDK 호출 실패 시 예외 처리 테스트"""
        worker = WorkerAgent(sample_agent_config)

        # SDK 호출 시 에러 발생
        with patch('claude_agent_sdk.query', side_effect=Exception("SDK Error")):
            with pytest.raises(Exception) as exc_info:
                async for _ in worker.execute_task("Test task"):
                    pass

            assert "SDK Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_task_response_formats(self, sample_agent_config):
        """다양한 응답 형식을 처리하는지 테스트"""
        worker = WorkerAgent(sample_agent_config)

        # 1. content 속성이 있는 경우
        async def mock_with_content():
            yield Mock(content=[Mock(text="Response with content")])

        with patch('claude_agent_sdk.query', return_value=mock_with_content()):
            chunks = []
            async for chunk in worker.execute_task("Test"):
                chunks.append(chunk)
            assert chunks[0] == "Response with content"

        # 2. text 속성이 직접 있는 경우
        async def mock_with_text():
            yield Mock(text="Direct text", spec=['text'])

        with patch('claude_agent_sdk.query', return_value=mock_with_text()):
            chunks = []
            async for chunk in worker.execute_task("Test"):
                chunks.append(chunk)
            assert chunks[0] == "Direct text"

        # 3. 그 외의 경우 (문자열 변환)
        async def mock_other():
            yield "String response"

        with patch('claude_agent_sdk.query', return_value=mock_other()):
            chunks = []
            async for chunk in worker.execute_task("Test"):
                chunks.append(chunk)
            assert chunks[0] == "String response"

    @pytest.mark.asyncio
    async def test_execute_task_with_different_tools(self, mock_claude_agent_sdk):
        """다양한 도구 설정으로 작업 실행 테스트"""
        # Read만 가능한 에이전트
        config_read_only = AgentConfig(
            name="reader",
            role="Reader Agent",
            system_prompt="Read files only",
            tools=["read"],
            model="claude-sonnet-4"
        )

        worker_read_only = WorkerAgent(config_read_only)
        async for _ in worker_read_only.execute_task("Read file.py"):
            pass

        call_args = mock_claude_agent_sdk.call_args
        assert call_args.kwargs["options"].allowed_tools == ["read"]

        # 모든 도구 사용 가능한 에이전트
        config_full = AgentConfig(
            name="coder",
            role="Coder Agent",
            system_prompt="Write code",
            tools=["read", "write", "edit", "bash"],
            model="claude-sonnet-4"
        )

        worker_full = WorkerAgent(config_full)
        async for _ in worker_full.execute_task("Write code"):
            pass

        call_args = mock_claude_agent_sdk.call_args
        assert call_args.kwargs["options"].allowed_tools == ["read", "write", "edit", "bash"]

    @pytest.mark.asyncio
    async def test_execute_task_empty_tools(self, mock_claude_agent_sdk):
        """도구가 없는 에이전트 테스트"""
        config = AgentConfig(
            name="observer",
            role="Observer",
            system_prompt="Just observe",
            tools=[],
            model="claude-sonnet-4"
        )

        worker = WorkerAgent(config)
        async for _ in worker.execute_task("Observe"):
            pass

        call_args = mock_claude_agent_sdk.call_args
        assert call_args.kwargs["options"].allowed_tools == []


class TestWorkerAgentIntegration:
    """WorkerAgent의 통합 동작 테스트"""

    @pytest.mark.asyncio
    async def test_multiple_task_execution(self, sample_agent_config, mock_claude_agent_sdk):
        """여러 작업을 순차적으로 실행하는 테스트"""
        worker = WorkerAgent(sample_agent_config)

        # 첫 번째 작업
        async for _ in worker.execute_task("First task"):
            pass

        # 두 번째 작업
        async for _ in worker.execute_task("Second task"):
            pass

        # SDK가 두 번 호출되었는지 확인
        assert mock_claude_agent_sdk.call_count == 2

    @pytest.mark.asyncio
    async def test_worker_with_file_prompt_and_task(self, temp_prompt_file, mock_claude_agent_sdk):
        """파일에서 로드한 프롬프트로 작업 실행 테스트"""
        config = AgentConfig(
            name="test_agent",
            role="Test Agent",
            system_prompt=str(temp_prompt_file),
            tools=["read"],
            model="claude-sonnet-4"
        )

        worker = WorkerAgent(config)

        async for _ in worker.execute_task("Execute with file prompt"):
            pass

        # 프롬프트에 파일 내용이 포함되었는지 확인
        call_args = mock_claude_agent_sdk.call_args
        prompt = call_args.kwargs["prompt"]

        assert "This is a test system prompt." in prompt
        assert "Execute with file prompt" in prompt
