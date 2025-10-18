"""
Base Worker Use Case 구현

각 Worker Use Case의 공통 로직을 포함하는 베이스 클래스입니다.
Circuit Breaker, Retry Policy, Timeout 관리를 통합합니다.
"""

import logging
from typing import AsyncIterator, Optional, Callable, Any, Coroutine

from ...domain.interfaces.use_cases import IExecuteWorkerUseCase
from ...domain.interfaces.circuit_breaker import ICircuitBreaker
from ...domain.interfaces.retry_policy import IRetryPolicy
from ...domain.models import Task, TaskResult, TaskStatus
from ...domain.exceptions import (
    ValidationError,
    WorkerExecutionError,
    WorkerNotFoundError,
    PreconditionFailedError,
    CircuitOpenError
)
from ..ports import IAgentClient


logger = logging.getLogger(__name__)


class BaseWorkerUseCase(IExecuteWorkerUseCase):
    """
    Worker Use Case 베이스 클래스

    공통 비즈니스 로직을 구현합니다:
    - Input Validation
    - Circuit Breaker 적용
    - Retry Policy 적용
    - Timeout 관리
    - Worker 실행
    - 에러 변환 (Infrastructure → Domain)
    - 결과 후처리

    각 Worker Use Case는 이 클래스를 상속하여 사전/사후 조건을 추가할 수 있습니다.
    """

    def __init__(
        self,
        worker_name: str,
        worker_client: IAgentClient,
        max_task_length: int = 10000,
        circuit_breaker: Optional[ICircuitBreaker] = None,
        retry_policy: Optional[IRetryPolicy] = None,
        timeout: Optional[float] = None,
    ):
        """
        Args:
            worker_name: Worker 이름 (예: "planner", "coder")
            worker_client: Worker 클라이언트 (Infrastructure 계층)
            max_task_length: 작업 설명 최대 길이
            circuit_breaker: Circuit Breaker (선택)
            retry_policy: Retry Policy (선택)
            timeout: 타임아웃 시간 (초, 선택)
        """
        self.worker_name = worker_name
        self.worker_client = worker_client
        self.max_task_length = max_task_length
        self.circuit_breaker = circuit_breaker
        self.retry_policy = retry_policy
        self.timeout = timeout

    def _validate_task(self, task: Task) -> None:
        """
        작업 입력 검증

        Args:
            task: 검증할 작업

        Raises:
            ValidationError: 검증 실패
        """
        if not task.description:
            raise ValidationError("작업 설명이 비어있습니다.")

        if len(task.description) > self.max_task_length:
            raise ValidationError(
                f"작업 설명이 너무 깁니다. "
                f"(최대 {self.max_task_length}자, 현재 {len(task.description)}자)"
            )

        if not task.agent_name:
            raise ValidationError("에이전트 이름이 비어있습니다.")

        if task.agent_name != self.worker_name:
            raise ValidationError(
                f"잘못된 에이전트 이름입니다. "
                f"(기대: {self.worker_name}, 실제: {task.agent_name})"
            )

    def _check_preconditions(self, task: Task) -> None:
        """
        사전 조건 체크 (서브클래스에서 오버라이드 가능)

        Args:
            task: 체크할 작업

        Raises:
            PreconditionFailedError: 사전 조건 실패
        """
        # 기본 구현은 아무것도 하지 않음
        # 서브클래스에서 필요 시 오버라이드
        pass

    def _process_result(self, task: Task, output: str) -> TaskResult:
        """
        결과 후처리 (서브클래스에서 오버라이드 가능)

        Args:
            task: 원본 작업
            output: Worker 실행 결과

        Returns:
            후처리된 TaskResult
        """
        # 기본 구현: 그대로 반환
        return TaskResult(
            task=task,
            status=TaskStatus.COMPLETED,
            output=output
        )

    async def _execute_worker_with_timeout(self, task: Task) -> AsyncIterator[str]:
        """
        Timeout을 적용하여 Worker 실행

        Args:
            task: 실행할 작업

        Yields:
            작업 실행 결과 청크
        """
        async for chunk in self.worker_client.execute(
            task.description,
            history=None,  # Task 모델에 history가 없으므로 None
            timeout=self.timeout
        ):
            yield chunk

    async def execute(self, task: Task) -> AsyncIterator[str]:
        """
        Worker 작업을 실행하고 결과를 스트리밍합니다.

        Circuit Breaker, Retry Policy, Timeout이 적용됩니다.

        주의: 이 메서드는 task의 상태를 변경하지 않습니다.
              상태 관리가 필요한 경우 execute_with_result()를 사용하세요.

        Args:
            task: 실행할 작업

        Yields:
            작업 실행 결과 (스트리밍)

        Raises:
            ValidationError: 작업 검증 실패
            PreconditionFailedError: 사전 조건 미충족
            CircuitOpenError: Circuit Breaker가 OPEN 상태
            WorkerExecutionError: Worker 실행 중 오류 발생
        """
        try:
            # 검증
            self._validate_task(task)
            self._check_preconditions(task)

            logger.info(f"[{self.worker_name}] 🚀 작업 시작: {task.description[:50]}...")

            # Circuit Breaker 상태 체크 (실행 전)
            if self.circuit_breaker:
                await self.circuit_breaker.check_before_call()

            # Retry Policy 적용 여부 결정
            first_chunk_received = False

            if self.retry_policy:
                # Retry Policy 적용하여 실행
                async def _worker_operation():
                    async for chunk in self._execute_worker_with_timeout(task):
                        yield chunk

                async for chunk in self.retry_policy.execute_streaming(_worker_operation):
                    # 첫 청크 수신 = 성공으로 간주
                    if not first_chunk_received:
                        first_chunk_received = True
                        if self.circuit_breaker:
                            await self.circuit_breaker.record_success()
                    yield chunk
            else:
                # Retry Policy 없이 직접 실행
                async for chunk in self._execute_worker_with_timeout(task):
                    # 첫 청크 수신 = 성공으로 간주
                    if not first_chunk_received:
                        first_chunk_received = True
                        if self.circuit_breaker:
                            await self.circuit_breaker.record_success()
                    yield chunk

            logger.info(f"[{self.worker_name}] ✅ 작업 완료")

        except (ValidationError, PreconditionFailedError, CircuitOpenError):
            # 검증 에러와 Circuit Open 에러는 그대로 전파
            raise
        except Exception as e:
            # Circuit Breaker 실패 기록
            if self.circuit_breaker:
                await self.circuit_breaker.record_failure(e)

            logger.error(
                f"[{self.worker_name}] ❌ 작업 실행 실패: {e}",
                exc_info=True
            )
            raise WorkerExecutionError(
                worker_name=self.worker_name,
                message=str(e),
                original_error=e
            )

    async def execute_with_result(self, task: Task) -> TaskResult:
        """
        Worker 작업을 실행하고 결과를 TaskResult로 반환합니다.

        이 메서드는 task의 status를 자동으로 관리합니다.

        Args:
            task: 실행할 작업

        Returns:
            작업 실행 결과
        """
        # 상태: IN_PROGRESS
        task.status = TaskStatus.IN_PROGRESS

        try:
            # 출력 버퍼링
            output = ""
            async for chunk in self.execute(task):  # execute는 상태 변경 안 함
                output += chunk

            # 상태: COMPLETED
            task.status = TaskStatus.COMPLETED

            # 결과 처리 및 반환
            return self._process_result(task, output)

        except (ValidationError, PreconditionFailedError, CircuitOpenError, WorkerExecutionError) as e:
            # 상태: FAILED
            task.status = TaskStatus.FAILED

            # 실패 결과 반환 (예외 재발생 안 함)
            return TaskResult(
                task=task,
                output="",
                status=TaskStatus.FAILED,
                error=str(e)
            )
