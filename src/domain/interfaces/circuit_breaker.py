"""
Circuit Breaker 인터페이스

Circuit Breaker 패턴의 인터페이스를 정의합니다.
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, TypeVar, Coroutine

from ..models.circuit_breaker import CircuitBreakerState


T = TypeVar("T")


class ICircuitBreaker(ABC):
    """
    Circuit Breaker 인터페이스

    Circuit Breaker 패턴을 구현하는 클래스가 따라야 할 인터페이스입니다.
    """

    @property
    @abstractmethod
    def state(self) -> CircuitBreakerState:
        """
        현재 Circuit Breaker 상태 조회

        Returns:
            현재 Circuit Breaker 상태
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    async def check_before_call(self) -> None:
        """
        호출 전 Circuit 상태 체크

        Circuit 상태를 확인하고, OPEN 상태이면 CircuitOpenError를 발생시킵니다.
        HALF_OPEN 상태이면 동시 실행 제한을 확인합니다.

        Raises:
            CircuitOpenError: Circuit이 OPEN 상태이거나 HALF_OPEN에서 복구 시도 중
        """
        pass

    @abstractmethod
    async def record_success(self) -> None:
        """
        작업 성공 기록

        Circuit Breaker에 성공을 기록합니다.
        스트리밍 방식에서 check_before_call()을 사용한 경우 반드시 호출해야 합니다.
        """
        pass

    @abstractmethod
    async def record_failure(self, error: Exception) -> None:
        """
        작업 실패 기록

        Circuit Breaker에 실패를 기록합니다.
        스트리밍 방식에서 check_before_call()을 사용한 경우 반드시 호출해야 합니다.

        Args:
            error: 발생한 예외
        """
        pass

    @abstractmethod
    async def reset(self) -> None:
        """
        Circuit Breaker를 초기 상태로 리셋

        주로 테스트나 수동 복구 시 사용됩니다.
        """
        pass
