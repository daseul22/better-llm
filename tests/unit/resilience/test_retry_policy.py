"""
Retry Policy 단위 테스트

Exponential Backoff 재시도 정책을 검증합니다.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, call

from src.application.resilience.retry_policy import ExponentialBackoffRetryPolicy
from src.domain.exceptions import WorkerTimeoutError, RetryableError


class TestRetryPolicyBasicBehavior:
    """Retry Policy 기본 동작 테스트"""

    @pytest.mark.asyncio
    async def test_successful_execution_on_first_try(self):
        """
        첫 시도에서 성공하면 재시도하지 않아야 합니다.
        """
        # Given: Retry Policy와 성공하는 함수
        policy = ExponentialBackoffRetryPolicy(max_attempts=3)

        async def successful_func():
            return "success"

        # When: 함수 실행
        result = await policy.execute(successful_func)

        # Then: 첫 시도에서 성공
        assert result == "success"

    @pytest.mark.asyncio
    async def test_retry_on_retryable_error(self):
        """
        재시도 가능한 예외 발생 시 재시도해야 합니다.
        """
        # Given: Retry Policy와 처음에는 실패하고 나중에 성공하는 함수
        policy = ExponentialBackoffRetryPolicy(
            max_attempts=3,
            base_delay=0.01,  # 빠른 테스트
            jitter=0
        )

        call_count = 0

        async def failing_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise WorkerTimeoutError("test_worker", "Timeout")
            return "success"

        # When: 함수 실행
        result = await policy.execute(failing_then_success)

        # Then: 3번 시도 후 성공
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_no_retry_on_non_retryable_error(self):
        """
        재시도 불가능한 예외는 즉시 전파되어야 합니다.
        """
        # Given: Retry Policy와 재시도 불가능한 예외를 발생시키는 함수
        policy = ExponentialBackoffRetryPolicy(max_attempts=3)

        call_count = 0

        async def non_retryable_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("Non-retryable error")

        # When/Then: 첫 시도에서 예외 전파
        with pytest.raises(ValueError):
            await policy.execute(non_retryable_error)

        assert call_count == 1  # 재시도하지 않음

    @pytest.mark.asyncio
    async def test_max_attempts_exceeded(self):
        """
        최대 재시도 횟수를 초과하면 마지막 예외를 전파해야 합니다.
        """
        # Given: max_attempts=3인 Retry Policy
        policy = ExponentialBackoffRetryPolicy(
            max_attempts=3,
            base_delay=0.01,
            jitter=0
        )

        call_count = 0

        async def always_failing():
            nonlocal call_count
            call_count += 1
            raise RetryableError("Always fails")

        # When/Then: 3번 시도 후 예외 전파
        with pytest.raises(RetryableError):
            await policy.execute(always_failing)

        assert call_count == 3


class TestRetryPolicyExponentialBackoff:
    """Exponential Backoff 로직 테스트"""

    @pytest.mark.asyncio
    async def test_delay_increases_exponentially(self):
        """
        재시도 간격이 지수적으로 증가해야 합니다.
        """
        # Given: base_delay=0.1, jitter=0인 Retry Policy
        policy = ExponentialBackoffRetryPolicy(
            max_attempts=4,
            base_delay=0.1,
            max_delay=10.0,
            jitter=0  # Jitter 제거로 정확한 시간 측정
        )

        # When: 지연 시간 계산
        delay1 = policy._calculate_delay(1)  # 0.1 * 2^0 = 0.1
        delay2 = policy._calculate_delay(2)  # 0.1 * 2^1 = 0.2
        delay3 = policy._calculate_delay(3)  # 0.1 * 2^2 = 0.4

        # Then: Exponential backoff 확인
        assert delay1 == 0.1
        assert delay2 == 0.2
        assert delay3 == 0.4

    @pytest.mark.asyncio
    async def test_delay_capped_at_max_delay(self):
        """
        재시도 간격은 max_delay를 초과하지 않아야 합니다.
        """
        # Given: max_delay=1.0인 Retry Policy
        policy = ExponentialBackoffRetryPolicy(
            max_attempts=10,
            base_delay=0.5,
            max_delay=1.0,
            jitter=0
        )

        # When: 큰 attempt 번호로 지연 시간 계산
        delay = policy._calculate_delay(10)  # 0.5 * 2^9 = 256 (하지만 max 1.0)

        # Then: max_delay로 제한됨
        assert delay == 1.0

    @pytest.mark.asyncio
    async def test_jitter_adds_randomness(self):
        """
        Jitter가 지연 시간에 무작위성을 추가해야 합니다.
        """
        # Given: jitter=0.5인 Retry Policy
        policy = ExponentialBackoffRetryPolicy(
            max_attempts=3,
            base_delay=1.0,
            max_delay=10.0,
            jitter=0.5
        )

        # When: 같은 attempt로 여러 번 지연 시간 계산
        delays = [policy._calculate_delay(1) for _ in range(10)]

        # Then: 모든 값이 base_delay 이상, base_delay * (1 + jitter) 이하
        for delay in delays:
            assert 1.0 <= delay <= 1.5  # 1.0 + (1.0 * 0.5)

        # 최소 2개의 다른 값이 있어야 함 (무작위성 확인)
        assert len(set(delays)) >= 2


class TestRetryPolicyStreamingBehavior:
    """스트리밍 함수에 대한 Retry Policy 테스트"""

    @pytest.mark.asyncio
    async def test_streaming_success_on_first_try(self):
        """
        스트리밍 함수가 첫 시도에서 성공하면 재시도하지 않아야 합니다.
        """
        # Given: Retry Policy와 스트리밍 함수
        policy = ExponentialBackoffRetryPolicy(max_attempts=3)

        async def streaming_func():
            yield "chunk1"
            yield "chunk2"
            yield "chunk3"

        # When: 스트리밍 실행
        chunks = []
        async for chunk in policy.execute_streaming(streaming_func):
            chunks.append(chunk)

        # Then: 모든 청크 수신
        assert chunks == ["chunk1", "chunk2", "chunk3"]

    @pytest.mark.asyncio
    async def test_streaming_retry_before_first_chunk(self):
        """
        첫 청크 수신 전 실패 시 재시도해야 합니다.
        """
        # Given: 처음에는 실패하고 나중에 성공하는 스트리밍 함수
        policy = ExponentialBackoffRetryPolicy(
            max_attempts=3,
            base_delay=0.01,
            jitter=0
        )

        attempt_count = 0

        async def failing_then_success_streaming():
            nonlocal attempt_count
            attempt_count += 1

            if attempt_count < 2:
                # 첫 청크 전에 실패
                raise WorkerTimeoutError("test_worker", "Timeout")

            # 두 번째 시도에서 성공
            yield "chunk1"
            yield "chunk2"

        # When: 스트리밍 실행
        chunks = []
        async for chunk in policy.execute_streaming(failing_then_success_streaming):
            chunks.append(chunk)

        # Then: 2번 시도 후 성공
        assert chunks == ["chunk1", "chunk2"]
        assert attempt_count == 2

    @pytest.mark.asyncio
    async def test_streaming_no_retry_after_first_chunk(self):
        """
        첫 청크 수신 후 실패 시 재시도하지 않아야 합니다.
        """
        # Given: 첫 청크 후 실패하는 스트리밍 함수
        policy = ExponentialBackoffRetryPolicy(
            max_attempts=3,
            base_delay=0.01
        )

        attempt_count = 0

        async def fail_after_first_chunk():
            nonlocal attempt_count
            attempt_count += 1
            yield "chunk1"
            raise RuntimeError("Error after first chunk")

        # When/Then: 첫 청크 수신 후 예외 즉시 전파
        chunks = []
        with pytest.raises(RuntimeError) as exc_info:
            async for chunk in policy.execute_streaming(fail_after_first_chunk):
                chunks.append(chunk)

        assert chunks == ["chunk1"]
        assert attempt_count == 1  # 재시도하지 않음
        assert "Error after first chunk" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_streaming_first_chunk_received_flag_reset(self):
        """
        매 재시도마다 first_chunk_received 플래그가 초기화되어야 합니다.
        """
        # Given: 여러 번 재시도하는 스트리밍 함수
        policy = ExponentialBackoffRetryPolicy(
            max_attempts=3,
            base_delay=0.01,
            jitter=0
        )

        attempt_count = 0

        async def multiple_retries_before_success():
            nonlocal attempt_count
            attempt_count += 1

            if attempt_count < 3:
                # 처음 2번은 첫 청크 전에 실패
                raise WorkerTimeoutError("test_worker", "Timeout")

            # 3번째 시도에서 성공
            yield "success_chunk"

        # When: 스트리밍 실행
        chunks = []
        async for chunk in policy.execute_streaming(multiple_retries_before_success):
            chunks.append(chunk)

        # Then: 3번 시도 후 성공 (first_chunk_received가 매번 False로 초기화됨)
        assert chunks == ["success_chunk"]
        assert attempt_count == 3


class TestRetryPolicyConfiguration:
    """Retry Policy 설정 검증 테스트"""

    def test_invalid_max_attempts(self):
        """
        max_attempts가 1 미만이면 ValueError를 발생시켜야 합니다.
        """
        with pytest.raises(ValueError, match="max_attempts는 1 이상"):
            ExponentialBackoffRetryPolicy(max_attempts=0)

    def test_invalid_base_delay(self):
        """
        base_delay가 0 이하면 ValueError를 발생시켜야 합니다.
        """
        with pytest.raises(ValueError, match="base_delay는 0보다 커야"):
            ExponentialBackoffRetryPolicy(base_delay=0)

        with pytest.raises(ValueError, match="base_delay는 0보다 커야"):
            ExponentialBackoffRetryPolicy(base_delay=-1)

    def test_invalid_max_delay(self):
        """
        max_delay가 base_delay보다 작으면 ValueError를 발생시켜야 합니다.
        """
        with pytest.raises(ValueError, match="max_delay는 base_delay 이상"):
            ExponentialBackoffRetryPolicy(base_delay=10, max_delay=5)

    def test_invalid_jitter(self):
        """
        jitter가 0~1 범위를 벗어나면 ValueError를 발생시켜야 합니다.
        """
        with pytest.raises(ValueError, match="jitter는 0.0 ~ 1.0"):
            ExponentialBackoffRetryPolicy(jitter=-0.1)

        with pytest.raises(ValueError, match="jitter는 0.0 ~ 1.0"):
            ExponentialBackoffRetryPolicy(jitter=1.5)

    def test_custom_retryable_exceptions(self):
        """
        커스텀 재시도 가능한 예외를 설정할 수 있어야 합니다.
        """
        # Given: ValueError만 재시도 가능하도록 설정
        policy = ExponentialBackoffRetryPolicy(
            max_attempts=3,
            retryable_exceptions=(ValueError,)
        )

        # When/Then: ValueError는 재시도 가능
        assert policy.is_retryable(ValueError("test"))

        # WorkerTimeoutError는 재시도 불가능 (기본값에서 제외됨)
        assert not policy.is_retryable(WorkerTimeoutError("test_worker", "timeout"))


class TestRetryPolicyEdgeCases:
    """Retry Policy 엣지 케이스 테스트"""

    @pytest.mark.asyncio
    async def test_single_attempt_policy(self):
        """
        max_attempts=1인 경우 재시도하지 않아야 합니다.
        """
        # Given: max_attempts=1인 Retry Policy
        policy = ExponentialBackoffRetryPolicy(max_attempts=1)

        call_count = 0

        async def failing_func():
            nonlocal call_count
            call_count += 1
            raise RetryableError("Fail")

        # When/Then: 첫 시도에서 실패하면 즉시 예외 전파
        with pytest.raises(RetryableError):
            await policy.execute(failing_func)

        assert call_count == 1

    @pytest.mark.asyncio
    async def test_streaming_empty_generator(self):
        """
        빈 스트림을 반환하는 함수도 정상 처리되어야 합니다.
        """
        # Given: 빈 스트림을 반환하는 함수
        policy = ExponentialBackoffRetryPolicy(max_attempts=3)

        async def empty_streaming():
            # 아무것도 yield하지 않음
            return
            yield  # unreachable

        # When: 스트리밍 실행
        chunks = []
        async for chunk in policy.execute_streaming(empty_streaming):
            chunks.append(chunk)

        # Then: 빈 리스트
        assert chunks == []

    @pytest.mark.asyncio
    async def test_is_retryable_with_default_exceptions(self):
        """
        기본 재시도 가능한 예외를 올바르게 판단해야 합니다.
        """
        # Given: 기본 설정의 Retry Policy
        policy = ExponentialBackoffRetryPolicy()

        # When/Then: WorkerTimeoutError는 재시도 가능
        assert policy.is_retryable(WorkerTimeoutError("test", "timeout"))

        # RetryableError는 재시도 가능
        assert policy.is_retryable(RetryableError("retryable"))

        # ValueError는 재시도 불가능
        assert not policy.is_retryable(ValueError("not retryable"))

        # RuntimeError는 재시도 불가능
        assert not policy.is_retryable(RuntimeError("not retryable"))
