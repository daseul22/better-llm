"""
BaseWorkerUseCase 통합 테스트

Circuit Breaker, Retry Policy의 통합을 검증합니다.
"""

import asyncio
import pytest
from typing import AsyncIterator

from src.application.use_cases.base_worker_use_case import BaseWorkerUseCase
from src.application.resilience.circuit_breaker import CircuitBreaker
from src.application.resilience.retry_policy import ExponentialBackoffRetryPolicy
from src.domain.models import Task, TaskStatus
from src.domain.models.circuit_breaker import CircuitState
from src.domain.exceptions import (
    ValidationError,
    CircuitOpenError,
    WorkerExecutionError,
    WorkerTimeoutError,
    RetryableError,
)


class MockWorkerClient:
    """
    테스트용 Mock Worker Client

    behavior를 설정하여 테스트 시나리오를 구현합니다.
    """

    def __init__(self):
        """MockWorkerClient 초기화"""
        self.behavior = None
        self.call_count = 0

    def set_behavior(self, behavior_func):
        """
        실행 동작 설정

        Args:
            behavior_func: async generator를 반환하는 callable
        """
        self.behavior = behavior_func

    async def execute(
        self,
        prompt: str,
        history=None,
        timeout=None
    ) -> AsyncIterator[str]:
        """Mock execute 메서드"""
        self.call_count += 1

        if self.behavior is None:
            # 기본 동작: 성공
            yield "default response"
            return

        # behavior 실행
        async for chunk in self.behavior():
            yield chunk


class TestBaseWorkerUseCaseValidation:
    """BaseWorkerUseCase 입력 검증 테스트"""

    @pytest.mark.asyncio
    async def test_validate_empty_description(self):
        """빈 작업 설명은 ValidationError를 발생시켜야 합니다."""
        client = MockWorkerClient()
        use_case = BaseWorkerUseCase(
            worker_name="test_worker",
            worker_client=client
        )

        task = Task(description="", agent_name="test_worker")

        with pytest.raises(ValidationError, match="작업 설명이 비어있습니다"):
            async for _ in use_case.execute(task):
                pass

    @pytest.mark.asyncio
    async def test_validate_description_too_long(self):
        """너무 긴 작업 설명은 ValidationError를 발생시켜야 합니다."""
        client = MockWorkerClient()
        use_case = BaseWorkerUseCase(
            worker_name="test_worker",
            worker_client=client,
            max_task_length=100
        )

        task = Task(description="x" * 101, agent_name="test_worker")

        with pytest.raises(ValidationError, match="작업 설명이 너무 깁니다"):
            async for _ in use_case.execute(task):
                pass

    @pytest.mark.asyncio
    async def test_validate_wrong_agent_name(self):
        """잘못된 에이전트 이름은 ValidationError를 발생시켜야 합니다."""
        client = MockWorkerClient()
        use_case = BaseWorkerUseCase(
            worker_name="coder",
            worker_client=client
        )

        task = Task(description="Test task", agent_name="planner")

        with pytest.raises(ValidationError, match="잘못된 에이전트 이름"):
            async for _ in use_case.execute(task):
                pass


class TestBaseWorkerUseCaseCircuitBreakerIntegration:
    """Circuit Breaker 통합 테스트"""

    @pytest.mark.asyncio
    async def test_circuit_breaker_record_success_on_first_chunk(self):
        """첫 청크 수신 시 circuit_breaker.record_success()가 호출되어야 합니다."""
        client = MockWorkerClient()

        async def success_behavior():
            yield "chunk1"
            yield "chunk2"

        client.set_behavior(success_behavior)

        circuit_breaker = CircuitBreaker(
            name="test_cb",
            failure_threshold=3
        )

        # 실패 카운트를 미리 설정
        circuit_breaker._state.failure_count = 2

        use_case = BaseWorkerUseCase(
            worker_name="test_worker",
            worker_client=client,
            circuit_breaker=circuit_breaker
        )

        task = Task(description="Test task", agent_name="test_worker")

        chunks = []
        async for chunk in use_case.execute(task):
            chunks.append(chunk)

        # 첫 청크 수신 후 failure_count 리셋됨
        assert chunks == ["chunk1", "chunk2"]
        assert circuit_breaker.state.failure_count == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_record_failure_on_error(self):
        """실패 시 circuit_breaker.record_failure()가 호출되어야 합니다."""
        client = MockWorkerClient()

        async def failing_behavior():
            raise RuntimeError("Worker failed")
            yield  # unreachable

        client.set_behavior(failing_behavior)

        circuit_breaker = CircuitBreaker(
            name="test_cb",
            failure_threshold=3
        )

        use_case = BaseWorkerUseCase(
            worker_name="test_worker",
            worker_client=client,
            circuit_breaker=circuit_breaker
        )

        task = Task(description="Test task", agent_name="test_worker")

        with pytest.raises(WorkerExecutionError):
            async for _ in use_case.execute(task):
                pass

        # failure_count 증가
        assert circuit_breaker.state.failure_count == 1

    @pytest.mark.asyncio
    async def test_circuit_open_raises_error(self):
        """Circuit이 OPEN 상태일 때 CircuitOpenError를 발생시켜야 합니다."""
        client = MockWorkerClient()

        circuit_breaker = CircuitBreaker(
            name="test_cb",
            failure_threshold=2,
            timeout_seconds=60
        )

        # Circuit을 OPEN으로 만듦
        await circuit_breaker.record_failure(Exception("Error 1"))
        await circuit_breaker.record_failure(Exception("Error 2"))
        assert circuit_breaker.state.state == CircuitState.OPEN

        use_case = BaseWorkerUseCase(
            worker_name="test_worker",
            worker_client=client,
            circuit_breaker=circuit_breaker
        )

        task = Task(description="Test task", agent_name="test_worker")

        with pytest.raises(CircuitOpenError):
            async for _ in use_case.execute(task):
                pass


class TestBaseWorkerUseCaseRetryPolicyIntegration:
    """Retry Policy 통합 테스트"""

    @pytest.mark.asyncio
    async def test_retry_on_retryable_error(self):
        """재시도 가능한 에러 발생 시 재시도해야 합니다."""
        client = MockWorkerClient()

        call_count_container = {"count": 0}

        async def failing_then_success():
            call_count_container["count"] += 1
            if call_count_container["count"] < 2:
                raise WorkerTimeoutError("test_worker", "Timeout")
            yield "success"

        client.set_behavior(failing_then_success)

        retry_policy = ExponentialBackoffRetryPolicy(
            max_attempts=3,
            base_delay=0.01,
            jitter=0
        )

        use_case = BaseWorkerUseCase(
            worker_name="test_worker",
            worker_client=client,
            retry_policy=retry_policy
        )

        task = Task(description="Test task", agent_name="test_worker")

        chunks = []
        async for chunk in use_case.execute(task):
            chunks.append(chunk)

        # 2번 시도 후 성공
        assert chunks == ["success"]
        assert client.call_count == 2

    @pytest.mark.asyncio
    async def test_no_retry_after_first_chunk(self):
        """첫 청크 수신 후 실패 시 재시도하지 않아야 합니다."""
        client = MockWorkerClient()

        async def fail_after_first_chunk():
            yield "chunk1"
            raise RuntimeError("Error after first chunk")

        client.set_behavior(fail_after_first_chunk)

        retry_policy = ExponentialBackoffRetryPolicy(
            max_attempts=3,
            base_delay=0.01
        )

        use_case = BaseWorkerUseCase(
            worker_name="test_worker",
            worker_client=client,
            retry_policy=retry_policy
        )

        task = Task(description="Test task", agent_name="test_worker")

        chunks = []
        with pytest.raises(WorkerExecutionError):
            async for chunk in use_case.execute(task):
                chunks.append(chunk)

        # 첫 청크 수신 후 재시도 안 함
        assert chunks == ["chunk1"]
        assert client.call_count == 1

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """최대 재시도 횟수 초과 시 WorkerExecutionError를 발생시켜야 합니다."""
        client = MockWorkerClient()

        async def always_failing():
            raise RetryableError("Always fails")
            yield  # unreachable

        client.set_behavior(always_failing)

        retry_policy = ExponentialBackoffRetryPolicy(
            max_attempts=3,
            base_delay=0.01,
            jitter=0
        )

        use_case = BaseWorkerUseCase(
            worker_name="test_worker",
            worker_client=client,
            retry_policy=retry_policy
        )

        task = Task(description="Test task", agent_name="test_worker")

        with pytest.raises(WorkerExecutionError):
            async for _ in use_case.execute(task):
                pass

        assert client.call_count == 3


class TestBaseWorkerUseCaseCircuitBreakerAndRetryIntegration:
    """Circuit Breaker + Retry Policy 통합 테스트"""

    @pytest.mark.asyncio
    async def test_circuit_breaker_and_retry_together(self):
        """Circuit Breaker와 Retry Policy가 함께 작동해야 합니다."""
        client = MockWorkerClient()

        call_count_container = {"count": 0}

        async def failing_then_success():
            call_count_container["count"] += 1
            if call_count_container["count"] < 2:
                raise WorkerTimeoutError("test_worker", "Timeout")
            yield "success"

        client.set_behavior(failing_then_success)

        circuit_breaker = CircuitBreaker(
            name="test_cb",
            failure_threshold=3
        )

        retry_policy = ExponentialBackoffRetryPolicy(
            max_attempts=3,
            base_delay=0.01,
            jitter=0
        )

        use_case = BaseWorkerUseCase(
            worker_name="test_worker",
            worker_client=client,
            circuit_breaker=circuit_breaker,
            retry_policy=retry_policy
        )

        task = Task(description="Test task", agent_name="test_worker")

        chunks = []
        async for chunk in use_case.execute(task):
            chunks.append(chunk)

        # Retry 성공 후 Circuit Breaker 상태도 정상
        assert chunks == ["success"]
        assert client.call_count == 2
        assert circuit_breaker.state.state == CircuitState.CLOSED
        assert circuit_breaker.state.failure_count == 0

    @pytest.mark.asyncio
    async def test_circuit_opens_after_multiple_failures(self):
        """여러 번의 재시도 실패 후 Circuit이 OPEN되어야 합니다."""
        client = MockWorkerClient()

        async def always_failing():
            raise RetryableError("Always fails")
            yield  # unreachable

        client.set_behavior(always_failing)

        circuit_breaker = CircuitBreaker(
            name="test_cb",
            failure_threshold=2  # 2번 실패 후 OPEN
        )

        retry_policy = ExponentialBackoffRetryPolicy(
            max_attempts=3,
            base_delay=0.01,
            jitter=0
        )

        use_case = BaseWorkerUseCase(
            worker_name="test_worker",
            worker_client=client,
            circuit_breaker=circuit_breaker,
            retry_policy=retry_policy
        )

        # 첫 번째 작업 실패 (3번 재시도)
        task1 = Task(description="Task 1", agent_name="test_worker")
        with pytest.raises(WorkerExecutionError):
            async for _ in use_case.execute(task1):
                pass

        # 첫 번째 작업 후 failure_count = 1
        assert circuit_breaker.state.failure_count == 1

        # 두 번째 작업 실패 (3번 재시도)
        task2 = Task(description="Task 2", agent_name="test_worker")
        with pytest.raises(WorkerExecutionError):
            async for _ in use_case.execute(task2):
                pass

        # Circuit OPEN
        assert circuit_breaker.state.state == CircuitState.OPEN


class TestBaseWorkerUseCaseExecuteWithResult:
    """execute_with_result() 메서드 테스트"""

    @pytest.mark.asyncio
    async def test_execute_with_result_success(self):
        """성공 시 TaskResult를 반환하고 상태를 COMPLETED로 변경해야 합니다."""
        client = MockWorkerClient()

        async def success_behavior():
            yield "chunk1"
            yield "chunk2"

        client.set_behavior(success_behavior)

        use_case = BaseWorkerUseCase(
            worker_name="test_worker",
            worker_client=client
        )

        task = Task(description="Test task", agent_name="test_worker")

        result = await use_case.execute_with_result(task)

        # TaskResult 반환 및 상태 업데이트
        assert result.status == TaskStatus.COMPLETED
        assert result.output == "chunk1chunk2"
        assert result.error is None
        assert task.status == TaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_execute_with_result_failure(self):
        """실패 시 TaskResult를 반환하고 상태를 FAILED로 변경해야 합니다."""
        client = MockWorkerClient()

        async def failing_behavior():
            raise RuntimeError("Worker error")
            yield  # unreachable

        client.set_behavior(failing_behavior)

        use_case = BaseWorkerUseCase(
            worker_name="test_worker",
            worker_client=client
        )

        task = Task(description="Test task", agent_name="test_worker")

        result = await use_case.execute_with_result(task)

        # 실패 결과 반환 (예외 재발생 안 함)
        assert result.status == TaskStatus.FAILED
        assert result.output == ""
        assert result.error is not None
        assert "Worker error" in result.error
        assert task.status == TaskStatus.FAILED
