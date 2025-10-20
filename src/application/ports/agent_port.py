"""
에이전트 포트 (인터페이스)

IAgentClient: 에이전트 실행 클라이언트 인터페이스
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator, List, Optional

from domain.models import Message


class IAgentClient(ABC):
    """
    에이전트 클라이언트 인터페이스

    Infrastructure 계층에서 구현됨 (Claude SDK, Mock 등)
    Application 계층은 이 인터페이스에만 의존함 (의존성 역전)
    """

    @abstractmethod
    async def execute(
        self,
        prompt: str,
        history: List[Message] = None,
        timeout: Optional[float] = None
    ) -> AsyncIterator[str]:
        """
        에이전트 실행 (스트리밍)

        Args:
            prompt: 실행할 프롬프트
            history: 대화 히스토리 (선택)
            timeout: 타임아웃 시간 (초, 선택)

        Yields:
            스트리밍 응답 청크

        Raises:
            WorkerTimeoutError: 타임아웃 발생 시
            Exception: 실행 실패 시
        """
        pass
