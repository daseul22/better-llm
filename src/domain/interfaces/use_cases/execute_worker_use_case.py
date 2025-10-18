"""
Worker 실행 Use Case 인터페이스

각 Worker(Planner, Coder, Reviewer, Tester)를 실행하는 Use Case의 공통 인터페이스입니다.
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator

from ...models import Task, TaskResult


class IExecuteWorkerUseCase(ABC):
    """
    Worker 실행 Use Case 인터페이스

    각 Worker별 Use Case가 구현해야 하는 공통 인터페이스입니다.
    비즈니스 로직 오케스트레이션을 담당합니다:
    - Input Validation
    - 사전 조건 체크
    - Worker 실행
    - 결과 후처리
    - 에러 변환 (Infrastructure → Domain)
    """

    @abstractmethod
    async def execute(self, task: Task) -> AsyncIterator[str]:
        """
        Worker 작업 실행 (스트리밍)

        Args:
            task: 실행할 작업

        Yields:
            스트리밍 응답 청크

        Raises:
            ValidationError: 입력 검증 실패
            PreconditionFailedError: 사전 조건 실패
            WorkerNotFoundError: Worker를 찾을 수 없음
            WorkerExecutionError: Worker 실행 실패
            WorkerTimeoutError: Worker 실행 타임아웃
        """
        pass

    @abstractmethod
    async def execute_with_result(self, task: Task) -> TaskResult:
        """
        Worker 작업 실행 및 결과 반환 (버퍼링)

        Args:
            task: 실행할 작업

        Returns:
            작업 실행 결과

        Raises:
            ValidationError: 입력 검증 실패
            PreconditionFailedError: 사전 조건 실패
            WorkerNotFoundError: Worker를 찾을 수 없음
            WorkerExecutionError: Worker 실행 실패
            WorkerTimeoutError: Worker 실행 타임아웃
        """
        pass
