"""
에이전트 인터페이스

BaseAgent: 모든 에이전트가 구현해야 하는 인터페이스 (ABC)
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator

from ..models import AgentConfig, Task, TaskResult


class BaseAgent(ABC):
    """
    에이전트 인터페이스

    모든 에이전트(Manager, Worker)가 구현해야 하는 추상 베이스 클래스
    """

    @property
    @abstractmethod
    def config(self) -> AgentConfig:
        """에이전트 설정 반환"""
        pass

    @abstractmethod
    async def execute_task(self, task: Task) -> AsyncIterator[str]:
        """
        작업 실행 (스트리밍)

        Args:
            task: 작업 요청

        Yields:
            스트리밍 응답 청크

        Raises:
            Exception: 작업 실행 실패 시
        """
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.config.name})"
