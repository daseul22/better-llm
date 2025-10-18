"""
Circuit Breaker 구현

Circuit Breaker 패턴을 구현하여 장애 격리 및 자동 복구를 제공합니다.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Callable, TypeVar, Coroutine

from ...domain.interfaces.circuit_breaker import ICircuitBreaker
from ...domain.models.circuit_breaker import CircuitState, CircuitBreakerState
from ...domain.exceptions import CircuitOpenError


logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitBreaker(ICircuitBreaker):
    """
    Circuit Breaker 구현

    상태:
        - CLOSED: 정상 동작, 모든 요청 허용
        - OPEN: 장애 발생, 모든 요청 차단
        - HALF_OPEN: 복구 시도 중, 제한된 요청 허용

    상태 전이:
        CLOSED -> OPEN: failure_count >= failure_threshold
        OPEN -> HALF_OPEN: timeout_seconds 경과
        HALF_OPEN -> CLOSED: success_count >= success_threshold
        HALF_OPEN -> OPEN: 실패 발생
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout_seconds: float = 60,
    ):
        """
        Args:
            name: Circuit Breaker 이름 (로깅용)
            failure_threshold: OPEN으로 전환하기 위한 연속 실패 횟수
            success_threshold: HALF_OPEN에서 CLOSED로 전환하기 위한 성공 횟수
            timeout_seconds: OPEN 상태 유지 시간 (초)
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout_seconds = timeout_seconds
        self._state = CircuitBreakerState(state=CircuitState.CLOSED)
        self._lock = asyncio.Lock()  # Thread-safety for async

    @property
    def state(self) -> CircuitBreakerState:
        """현재 Circuit Breaker 상태 조회"""
        return self._state

    def _should_open(self) -> bool:
        """
        Circuit을 OPEN 상태로 전환해야 하는지 판단

        Returns:
            OPEN 전환 필요 여부
        """
        return (
            self._state.state == CircuitState.CLOSED
            and self._state.failure_count >= self.failure_threshold
        )

    def _should_attempt_reset(self) -> bool:
        """
        Circuit을 HALF_OPEN으로 전환 시도해야 하는지 판단

        Returns:
            HALF_OPEN 전환 시도 필요 여부
        """
        if self._state.state != CircuitState.OPEN:
            return False

        if self._state.opened_at is None:
            return True

        elapsed = datetime.now() - self._state.opened_at
        return elapsed >= timedelta(seconds=self.timeout_seconds)

    async def _on_success(self) -> None:
        """
        함수 실행 성공 시 호출

        상태 업데이트:
            - CLOSED: failure_count 리셋
            - HALF_OPEN: success_count 증가, threshold 도달 시 CLOSED로 전환
        """
        async with self._lock:
            # in_flight_requests 감소
            self._state.in_flight_requests = max(0, self._state.in_flight_requests - 1)

            if self._state.state == CircuitState.CLOSED:
                # CLOSED: 실패 카운트만 리셋
                self._state.failure_count = 0

            elif self._state.state == CircuitState.HALF_OPEN:
                # HALF_OPEN: 성공 카운트 증가
                self._state.success_count += 1
                logger.info(
                    f"[CircuitBreaker:{self.name}] HALF_OPEN 성공 "
                    f"({self._state.success_count}/{self.success_threshold})"
                )

                # Threshold 도달 시 CLOSED로 전환
                if self._state.success_count >= self.success_threshold:
                    logger.info(
                        f"[CircuitBreaker:{self.name}] "
                        f"HALF_OPEN -> CLOSED (복구 완료)"
                    )
                    self._state.state = CircuitState.CLOSED
                    self._state.reset()

    async def _on_failure(self, error: Exception) -> None:
        """
        함수 실행 실패 시 호출

        상태 업데이트:
            - CLOSED: failure_count 증가, threshold 도달 시 OPEN으로 전환
            - HALF_OPEN: 즉시 OPEN으로 전환

        Args:
            error: 발생한 예외
        """
        async with self._lock:
            # in_flight_requests 감소
            self._state.in_flight_requests = max(0, self._state.in_flight_requests - 1)

            self._state.last_failure_time = datetime.now()

            if self._state.state == CircuitState.CLOSED:
                # CLOSED: 실패 카운트 증가
                self._state.failure_count += 1
                logger.warning(
                    f"[CircuitBreaker:{self.name}] 실패 감지 "
                    f"({self._state.failure_count}/{self.failure_threshold}): {error}"
                )

                # Threshold 도달 시 OPEN으로 전환
                if self._should_open():
                    self._state.state = CircuitState.OPEN
                    self._state.opened_at = datetime.now()
                    logger.error(
                        f"[CircuitBreaker:{self.name}] "
                        f"CLOSED -> OPEN (장애 감지, {self.timeout_seconds}초간 차단)"
                    )

            elif self._state.state == CircuitState.HALF_OPEN:
                # HALF_OPEN: 즉시 OPEN으로 복귀
                logger.error(
                    f"[CircuitBreaker:{self.name}] "
                    f"HALF_OPEN -> OPEN (복구 실패): {error}"
                )
                self._state.state = CircuitState.OPEN
                self._state.opened_at = datetime.now()
                self._state.success_count = 0

    async def _check_before_call(self) -> None:
        """
        호출 전 Circuit 상태 체크 (내부 구현)

        Raises:
            CircuitOpenError: Circuit이 OPEN 상태이거나 HALF_OPEN에서 복구 시도 중
        """
        async with self._lock:
            if self._state.state == CircuitState.OPEN:
                if not self._should_attempt_reset():
                    raise CircuitOpenError(
                        circuit_name=self.name,
                        message=f"Circuit '{self.name}'이(가) OPEN 상태입니다. "
                        f"{self.timeout_seconds}초 후 재시도하세요."
                    )
                # HALF_OPEN으로 전환
                logger.info(
                    f"[CircuitBreaker:{self.name}] "
                    f"OPEN -> HALF_OPEN (복구 시도)"
                )
                self._state.state = CircuitState.HALF_OPEN
                self._state.success_count = 0

            # HALF_OPEN 상태에서 동시 실행 제한
            if self._state.state == CircuitState.HALF_OPEN:
                if self._state.in_flight_requests >= 1:
                    raise CircuitOpenError(
                        circuit_name=self.name,
                        message=f"Circuit '{self.name}'이(가) HALF_OPEN 상태이며, "
                                f"복구 시도 중입니다. 잠시 후 다시 시도하세요."
                    )

            self._state.in_flight_requests += 1

    async def check_before_call(self) -> None:
        """
        호출 전 Circuit 상태 체크 (Public API)

        Circuit 상태를 확인하고, OPEN 상태이면 CircuitOpenError를 발생시킵니다.
        HALF_OPEN 상태이면 동시 실행 제한을 확인합니다.

        Raises:
            CircuitOpenError: Circuit이 OPEN 상태이거나 HALF_OPEN에서 복구 시도 중
        """
        await self._check_before_call()

    async def record_success(self) -> None:
        """
        작업 성공 기록 (Public API)

        Circuit Breaker에 성공을 기록합니다.
        스트리밍 방식에서 check_before_call()을 사용한 경우 반드시 호출해야 합니다.
        """
        await self._on_success()

    async def record_failure(self, error: Exception) -> None:
        """
        작업 실패 기록 (Public API)

        Circuit Breaker에 실패를 기록합니다.
        스트리밍 방식에서 check_before_call()을 사용한 경우 반드시 호출해야 합니다.

        Args:
            error: 발생한 예외
        """
        await self._on_failure(error)

    async def call(
        self,
        func: Callable[..., Coroutine[Any, Any, T]],
        *args: Any,
        **kwargs: Any
    ) -> T:
        """
        Circuit Breaker를 통해 함수 실행

        Args:
            func: 실행할 async 함수
            *args: 함수 인자
            **kwargs: 함수 키워드 인자

        Returns:
            함수 실행 결과

        Raises:
            CircuitOpenError: Circuit이 OPEN 상태일 때
            Exception: func 실행 중 발생한 예외
        """
        # _check_before_call() 재사용하여 코드 중복 제거
        await self._check_before_call()

        # 함수 실행 (Lock 외부)
        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except Exception as e:
            await self._on_failure(e)
            raise

    async def reset(self) -> None:
        """
        Circuit Breaker를 초기 상태로 리셋

        주로 테스트나 수동 복구 시 사용됩니다.
        """
        async with self._lock:
            logger.info(f"[CircuitBreaker:{self.name}] 수동 리셋")
            self._state.state = CircuitState.CLOSED
            self._state.reset()
