"""
Worker Agent Adapter

WorkerAgent를 IAgentClient 인터페이스에 맞춰 래핑합니다.
이를 통해 Use Case가 Infrastructure 구현체에 직접 의존하지 않도록 합니다.
"""

import asyncio
import sys
from typing import List, AsyncIterator, Optional

from .worker_client import WorkerAgent
from src.application.ports import IAgentClient
from src.domain.models import Message, AgentConfig
from src.domain.services import ProjectContext
from src.domain.exceptions import WorkerTimeoutError

# Python 3.11+ vs 3.10 호환성
if sys.version_info >= (3, 11):
    from asyncio import timeout as asyncio_timeout
else:
    # Python 3.10 이하는 async_timeout 라이브러리 필요
    try:
        from async_timeout import timeout as asyncio_timeout
    except ImportError:
        raise ImportError(
            "Python 3.10 이하에서는 async_timeout 패키지가 필요합니다. "
            "`pip install async-timeout`으로 설치하세요."
        )


class WorkerAgentAdapter(IAgentClient):
    """
    WorkerAgent를 IAgentClient 인터페이스로 어댑트

    Adapter 패턴을 사용하여 Infrastructure 계층의 WorkerAgent를
    Application 계층의 IAgentClient 인터페이스로 변환합니다.
    """

    def __init__(self, worker_agent: WorkerAgent, default_timeout: float = 300):
        """
        Args:
            worker_agent: 래핑할 WorkerAgent 인스턴스
            default_timeout: 기본 타임아웃 시간 (초, 기본값: 300초 = 5분)
        """
        self._worker_agent = worker_agent
        self.default_timeout = default_timeout

    async def execute(
        self,
        prompt: str,
        history: List[Message] = None,
        timeout: Optional[float] = None
    ) -> AsyncIterator[str]:
        """
        Worker Agent 실행 (스트리밍, 타임아웃 지원)

        Args:
            prompt: 실행할 프롬프트
            history: 대화 히스토리 (현재 미사용)
            timeout: 타임아웃 시간 (초, None이면 default_timeout 사용)

        Yields:
            스트리밍 응답 청크

        Raises:
            WorkerTimeoutError: 타임아웃 발생 시
            Exception: 실행 실패 시
        """
        timeout_value = timeout or self.default_timeout
        worker_name = self._worker_agent.config.name

        try:
            # Python 3.11+의 asyncio.timeout 또는 async_timeout 사용
            async with asyncio_timeout(timeout_value):
                # WorkerAgent의 execute_task 메서드를 호출
                # history는 현재 WorkerAgent가 지원하지 않으므로 무시
                async for chunk in self._worker_agent.execute_task(prompt):
                    yield chunk

        except asyncio.TimeoutError:
            # asyncio.TimeoutError를 Domain 예외로 변환
            raise WorkerTimeoutError(
                worker_name=worker_name,
                message=f"Worker '{worker_name}' 실행 타임아웃 ({timeout_value}초)",
                timeout=timeout_value
            )

    @property
    def config(self) -> AgentConfig:
        """에이전트 설정 반환"""
        return self._worker_agent.config

    def __repr__(self) -> str:
        return f"WorkerAgentAdapter(agent={self._worker_agent})"
