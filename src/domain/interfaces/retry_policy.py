"""
Retry Policy 인터페이스

재시도 정책의 인터페이스를 정의합니다.
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, TypeVar, Coroutine, AsyncIterator


T = TypeVar("T")


class IRetryPolicy(ABC):
    """
    Retry Policy 인터페이스

    재시도 메커니즘을 구현하는 클래스가 따라야 할 인터페이스입니다.
    """

    @abstractmethod
    async def execute(
        self,
        func: Callable[..., Coroutine[Any, Any, T]],
        *args: Any,
        **kwargs: Any
    ) -> T:
        """
        재시도 로직으로 함수 실행

        Args:
            func: 실행할 async 함수
            *args: 함수 인자
            **kwargs: 함수 키워드 인자

        Returns:
            함수 실행 결과

        Raises:
            Exception: 재시도 횟수 초과 또는 재시도 불가능한 예외 발생 시
        """
        pass

    @abstractmethod
    async def execute_streaming(
        self,
        func: Callable[..., AsyncIterator[T]],
        *args: Any,
        **kwargs: Any
    ) -> AsyncIterator[T]:
        """
        스트리밍 함수에 재시도 로직을 적용합니다.

        첫 번째 청크 수신 실패 시에만 재시도합니다.

        Args:
            func: 재시도할 스트리밍 함수
            *args: 함수 인자
            **kwargs: 함수 키워드 인자

        Yields:
            함수 실행 결과 청크

        Raises:
            재시도 불가능한 예외 또는 최대 재시도 횟수 초과 시 마지막 예외
        """
        pass

    @abstractmethod
    def is_retryable(self, error: Exception) -> bool:
        """
        주어진 예외가 재시도 가능한지 판단

        Args:
            error: 발생한 예외

        Returns:
            재시도 가능 여부
        """
        pass
