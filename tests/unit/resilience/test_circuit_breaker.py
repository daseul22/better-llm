"""
Circuit Breaker 단위 테스트

Circuit Breaker의 상태 전환 로직을 검증합니다.
"""

import asyncio
import pytest
from datetime import datetime, timedelta

from src.application.resilience.circuit_breaker import CircuitBreaker
from src.domain.models.circuit_breaker import CircuitState
from src.domain.exceptions import CircuitOpenError


class TestCircuitBreakerStateTransitions:
    """Circuit Breaker 상태 전환 테스트"""

    @pytest.mark.asyncio
    async def test_closed_to_open_transition(self):
        """
        CLOSED → OPEN 전환 테스트

        실패 임계값에 도달하면 CLOSED에서 OPEN으로 전환되어야 합니다.
        """
        # Given: failure_threshold=3인 Circuit Breaker
        cb = CircuitBreaker(
            name="test_cb",
            failure_threshold=3,
            timeout_seconds=60
        )

        # When: 3번 연속 실패
        for _ in range(3):
            await cb.record_failure(Exception("Test error"))

        # Then: OPEN 상태로 전환
        assert cb.state.state == CircuitState.OPEN
        assert cb.state.failure_count == 3
        assert cb.state.opened_at is not None

    @pytest.mark.asyncio
    async def test_open_to_half_open_transition(self):
        """
        OPEN → HALF_OPEN 전환 테스트

        타임아웃 시간이 지나면 OPEN에서 HALF_OPEN으로 전환을 시도해야 합니다.
        """
        # Given: timeout_seconds=0.1인 Circuit Breaker (빠른 테스트)
        cb = CircuitBreaker(
            name="test_cb",
            failure_threshold=2,
            timeout_seconds=0.1
        )

        # Circuit을 OPEN 상태로 만듦
        await cb.record_failure(Exception("Error 1"))
        await cb.record_failure(Exception("Error 2"))
        assert cb.state.state == CircuitState.OPEN

        # When: timeout_seconds 대기 후 check_before_call 호출
        await asyncio.sleep(0.15)

        # Then: HALF_OPEN으로 전환 (check_before_call이 성공해야 함)
        await cb.check_before_call()
        assert cb.state.state == CircuitState.HALF_OPEN

        # 정리: in_flight_requests 감소를 위해 success 기록
        await cb.record_success()

    @pytest.mark.asyncio
    async def test_half_open_to_closed_transition(self):
        """
        HALF_OPEN → CLOSED 전환 테스트

        성공 임계값에 도달하면 HALF_OPEN에서 CLOSED로 전환되어야 합니다.
        """
        # Given: success_threshold=2인 Circuit Breaker
        cb = CircuitBreaker(
            name="test_cb",
            failure_threshold=2,
            success_threshold=2,
            timeout_seconds=0.1
        )

        # Circuit을 OPEN → HALF_OPEN으로 전환
        await cb.record_failure(Exception("Error 1"))
        await cb.record_failure(Exception("Error 2"))
        await asyncio.sleep(0.15)
        await cb.check_before_call()  # HALF_OPEN으로 전환

        # When: 2번 연속 성공
        await cb.record_success()

        # HALF_OPEN에서 동시 요청 제한을 위해 다시 check_before_call
        # 하지만 in_flight_requests=0이므로 성공
        await cb.check_before_call()
        await cb.record_success()

        # Then: CLOSED 상태로 전환
        assert cb.state.state == CircuitState.CLOSED
        assert cb.state.success_count == 0
        assert cb.state.failure_count == 0

    @pytest.mark.asyncio
    async def test_half_open_to_open_transition(self):
        """
        HALF_OPEN → OPEN 전환 테스트

        HALF_OPEN 상태에서 실패하면 즉시 OPEN으로 돌아가야 합니다.
        """
        # Given: HALF_OPEN 상태의 Circuit Breaker
        cb = CircuitBreaker(
            name="test_cb",
            failure_threshold=2,
            timeout_seconds=0.1
        )

        # Circuit을 OPEN → HALF_OPEN으로 전환
        await cb.record_failure(Exception("Error 1"))
        await cb.record_failure(Exception("Error 2"))
        await asyncio.sleep(0.15)
        await cb.check_before_call()
        assert cb.state.state == CircuitState.HALF_OPEN

        # When: HALF_OPEN 상태에서 실패
        await cb.record_failure(Exception("Error in half-open"))

        # Then: 즉시 OPEN으로 복귀
        assert cb.state.state == CircuitState.OPEN
        assert cb.state.success_count == 0


class TestCircuitBreakerPublicAPI:
    """Circuit Breaker Public API 테스트"""

    @pytest.mark.asyncio
    async def test_check_before_call_when_open(self):
        """
        OPEN 상태에서 check_before_call()은 CircuitOpenError를 발생시켜야 합니다.
        """
        # Given: OPEN 상태의 Circuit Breaker
        cb = CircuitBreaker(
            name="test_cb",
            failure_threshold=2,
            timeout_seconds=60  # 긴 타임아웃
        )

        await cb.record_failure(Exception("Error 1"))
        await cb.record_failure(Exception("Error 2"))
        assert cb.state.state == CircuitState.OPEN

        # When/Then: check_before_call()이 CircuitOpenError 발생
        with pytest.raises(CircuitOpenError) as exc_info:
            await cb.check_before_call()

        assert "test_cb" in str(exc_info.value)
        assert "OPEN" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_record_success_in_closed_state(self):
        """
        CLOSED 상태에서 record_success()는 failure_count를 리셋해야 합니다.
        """
        # Given: 일부 실패가 있는 CLOSED 상태
        cb = CircuitBreaker(
            name="test_cb",
            failure_threshold=5
        )

        await cb.record_failure(Exception("Error 1"))
        await cb.record_failure(Exception("Error 2"))
        assert cb.state.failure_count == 2

        # When: 성공 기록
        await cb.record_success()

        # Then: failure_count 리셋
        assert cb.state.failure_count == 0
        assert cb.state.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_record_failure_increments_count(self):
        """
        record_failure()는 실패 카운트를 증가시켜야 합니다.
        """
        # Given: CLOSED 상태의 Circuit Breaker
        cb = CircuitBreaker(
            name="test_cb",
            failure_threshold=5
        )

        # When: 실패 3번 기록
        await cb.record_failure(Exception("Error 1"))
        await cb.record_failure(Exception("Error 2"))
        await cb.record_failure(Exception("Error 3"))

        # Then: failure_count = 3
        assert cb.state.failure_count == 3
        assert cb.state.state == CircuitState.CLOSED  # 아직 threshold 미도달


class TestCircuitBreakerEdgeCases:
    """Circuit Breaker 엣지 케이스 테스트"""

    @pytest.mark.asyncio
    async def test_half_open_concurrent_request_limit(self):
        """
        HALF_OPEN 상태에서 동시 요청은 1개만 허용되어야 합니다.
        """
        # Given: HALF_OPEN 상태의 Circuit Breaker
        cb = CircuitBreaker(
            name="test_cb",
            failure_threshold=2,
            timeout_seconds=0.1
        )

        # OPEN으로 전환
        await cb.record_failure(Exception("Error 1"))
        await cb.record_failure(Exception("Error 2"))

        # HALF_OPEN으로 전환
        await asyncio.sleep(0.15)
        await cb.check_before_call()
        assert cb.state.state == CircuitState.HALF_OPEN
        assert cb.state.in_flight_requests == 1

        # When/Then: 두 번째 요청은 차단되어야 함
        with pytest.raises(CircuitOpenError) as exc_info:
            await cb.check_before_call()

        assert "복구 시도 중" in str(exc_info.value)

        # 정리
        await cb.record_success()

    @pytest.mark.asyncio
    async def test_reset_clears_all_state(self):
        """
        reset()은 모든 상태를 초기화해야 합니다.
        """
        # Given: OPEN 상태의 Circuit Breaker
        cb = CircuitBreaker(
            name="test_cb",
            failure_threshold=2
        )

        await cb.record_failure(Exception("Error 1"))
        await cb.record_failure(Exception("Error 2"))
        assert cb.state.state == CircuitState.OPEN

        # When: reset 호출
        await cb.reset()

        # Then: 모든 상태 초기화
        assert cb.state.state == CircuitState.CLOSED
        assert cb.state.failure_count == 0
        assert cb.state.success_count == 0
        assert cb.state.in_flight_requests == 0
        assert cb.state.opened_at is None

    @pytest.mark.asyncio
    async def test_call_method_success(self):
        """
        call() 메서드로 성공적인 함수 실행을 테스트합니다.
        """
        # Given: CLOSED 상태의 Circuit Breaker
        cb = CircuitBreaker(name="test_cb")

        async def successful_func(value: int) -> int:
            return value * 2

        # When: call()로 함수 실행
        result = await cb.call(successful_func, 5)

        # Then: 결과 반환 및 상태 유지
        assert result == 10
        assert cb.state.state == CircuitState.CLOSED
        assert cb.state.failure_count == 0

    @pytest.mark.asyncio
    async def test_call_method_failure(self):
        """
        call() 메서드로 실패하는 함수 실행을 테스트합니다.
        """
        # Given: CLOSED 상태의 Circuit Breaker
        cb = CircuitBreaker(
            name="test_cb",
            failure_threshold=2
        )

        async def failing_func():
            raise ValueError("Test error")

        # When: call()로 실패하는 함수를 2번 실행
        with pytest.raises(ValueError):
            await cb.call(failing_func)

        with pytest.raises(ValueError):
            await cb.call(failing_func)

        # Then: OPEN 상태로 전환
        assert cb.state.state == CircuitState.OPEN
        assert cb.state.failure_count == 2

    @pytest.mark.asyncio
    async def test_call_method_when_circuit_open(self):
        """
        Circuit이 OPEN 상태일 때 call()은 CircuitOpenError를 발생시켜야 합니다.
        """
        # Given: OPEN 상태의 Circuit Breaker
        cb = CircuitBreaker(
            name="test_cb",
            failure_threshold=1,
            timeout_seconds=60
        )

        async def some_func():
            return "result"

        # Circuit을 OPEN으로 만듦
        await cb.record_failure(Exception("Error"))
        assert cb.state.state == CircuitState.OPEN

        # When/Then: call()이 CircuitOpenError 발생
        with pytest.raises(CircuitOpenError):
            await cb.call(some_func)


class TestCircuitBreakerTimestamps:
    """Circuit Breaker 타임스탬프 관련 테스트"""

    @pytest.mark.asyncio
    async def test_opened_at_timestamp_set_on_open(self):
        """
        OPEN 상태로 전환 시 opened_at 타임스탬프가 설정되어야 합니다.
        """
        # Given: Circuit Breaker
        cb = CircuitBreaker(
            name="test_cb",
            failure_threshold=1
        )

        before = datetime.now()

        # When: OPEN으로 전환
        await cb.record_failure(Exception("Error"))

        after = datetime.now()

        # Then: opened_at이 설정됨
        assert cb.state.opened_at is not None
        assert before <= cb.state.opened_at <= after

    @pytest.mark.asyncio
    async def test_last_failure_time_updated(self):
        """
        실패 시 last_failure_time이 업데이트되어야 합니다.
        """
        # Given: Circuit Breaker
        cb = CircuitBreaker(name="test_cb")

        # When: 실패 기록
        before = datetime.now()
        await cb.record_failure(Exception("Error"))
        after = datetime.now()

        # Then: last_failure_time 업데이트
        assert cb.state.last_failure_time is not None
        assert before <= cb.state.last_failure_time <= after
