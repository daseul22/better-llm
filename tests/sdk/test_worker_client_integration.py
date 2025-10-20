"""
WorkerClient + SDKExecutor 통합 테스트.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import AsyncIterator

from src.infrastructure.claude.worker_client import WorkerAgent
from src.domain.models import AgentConfig
from src.domain.services import ProjectContext


@pytest.fixture
def agent_config():
    """AgentConfig 인스턴스."""
    return AgentConfig(
        name="TestWorker",
        role="Test role",
        model="test-model",
        system_prompt="Test system prompt",
        tools=["read", "write", "bash"]
    )


@pytest.fixture
def worker_agent(agent_config):
    """WorkerAgent 인스턴스."""
    # project_context를 None으로 설정하여 _load_project_context 우회
    return WorkerAgent(config=agent_config, project_context=None)


class MockResponse:
    """Mock Response."""

    def __init__(self, text: str = None, content: list = None):
        if text:
            self.text = text
        if content:
            self.content = content


class MockContent:
    """Mock Content."""

    def __init__(self, text: str):
        self.text = text


@pytest.mark.asyncio
async def test_execute_task_success(worker_agent):
    """execute_task 정상 동작 테스트."""
    # Mock query 함수
    async def mock_query(prompt, options):
        yield MockResponse(text="Task result line 1")
        yield MockResponse(text="Task result line 2")

    with patch('src.infrastructure.claude.sdk_executor.query', mock_query):
        chunks = []
        async for chunk in worker_agent.execute_task("Test task"):
            chunks.append(chunk)

        # 응답 청크 검증
        assert len(chunks) == 2
        assert chunks[0] == "Task result line 1"
        assert chunks[1] == "Task result line 2"


@pytest.mark.asyncio
async def test_execute_task_with_content_list(worker_agent):
    """content 리스트 응답 처리 테스트."""
    # Mock query 함수
    async def mock_query(prompt, options):
        yield MockResponse(content=[MockContent("Content from list")])

    with patch('src.infrastructure.claude.sdk_executor.query', mock_query):
        chunks = []
        async for chunk in worker_agent.execute_task("Test task"):
            chunks.append(chunk)

        # 응답 검증
        assert len(chunks) == 1
        assert chunks[0] == "Content from list"


@pytest.mark.asyncio
async def test_execute_task_with_debug_info(worker_agent):
    """디버그 정보 출력 테스트."""
    # Mock query 함수
    async def mock_query(prompt, options):
        yield MockResponse(text="Task result")

    # 환경변수 설정
    with patch.dict('os.environ', {'WORKER_DEBUG_INFO': 'true'}):
        with patch('src.infrastructure.claude.sdk_executor.query', mock_query):
            chunks = []
            async for chunk in worker_agent.execute_task("Test task"):
                chunks.append(chunk)

            # 디버그 정보 + 응답이 있어야 함
            assert len(chunks) >= 1
            # 첫 번째 청크는 디버그 정보일 수 있음
            assert any("Task result" in chunk for chunk in chunks)


@pytest.mark.asyncio
async def test_execute_task_exception_handling(worker_agent):
    """예외 처리 테스트."""
    # Mock query 함수 (예외 발생)
    async def mock_query(prompt, options):
        raise RuntimeError("Test error")
        yield  # unreachable but needed for generator

    with patch('src.infrastructure.claude.sdk_executor.query', mock_query):
        chunks = []
        async for chunk in worker_agent.execute_task("Test task"):
            chunks.append(chunk)

        # 에러 메시지 검증
        assert len(chunks) == 1
        assert "시스템 오류" in chunks[0]
        assert "TestWorker" in chunks[0]


@pytest.mark.asyncio
async def test_execute_task_with_project_context():
    """프로젝트 컨텍스트가 포함된 실행 테스트."""
    # AgentConfig 생성
    config = AgentConfig(
        name="ContextWorker",
        role="Test",
        model="test-model",
        system_prompt="Base prompt",
        tools=["read"]
    )

    # ProjectContext 생성
    project_context = ProjectContext(
        project_name="TestProject",
        description="Test description",
        language="python",
        framework="pytest",
        architecture="Clean Architecture",
        key_files={}
    )

    worker = WorkerAgent(config=config, project_context=project_context)

    # 시스템 프롬프트에 프로젝트 컨텍스트가 포함되었는지 확인
    assert "TestProject" in worker.system_prompt
    assert "Test description" in worker.system_prompt

    # Mock query 함수
    async def mock_query(prompt, options):
        # 프롬프트에 프로젝트 컨텍스트가 포함되었는지 확인
        assert "TestProject" in prompt
        yield MockResponse(text="Done")

    with patch('src.infrastructure.claude.sdk_executor.query', mock_query):
        async for _ in worker.execute_task("Test task"):
            pass


@pytest.mark.asyncio
async def test_execute_task_prompt_composition(worker_agent):
    """프롬프트 조합 테스트."""
    task_description = "Specific task instruction"

    captured_prompt = None

    async def mock_query(prompt, options):
        nonlocal captured_prompt
        captured_prompt = prompt
        yield MockResponse(text="Done")

    with patch('src.infrastructure.claude.sdk_executor.query', mock_query):
        async for _ in worker_agent.execute_task(task_description):
            pass

        # 프롬프트가 시스템 프롬프트 + 작업 설명으로 구성되었는지 확인
        assert captured_prompt is not None
        assert "Test system prompt" in captured_prompt
        assert task_description in captured_prompt
