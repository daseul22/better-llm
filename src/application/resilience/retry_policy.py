"""
Retry Policy 구현

Exponential Backoff를 포함한 재시도 정책을 구현합니다.
"""

import asyncio
import logging
import random
from typing import Any, Callable, TypeVar, Coroutine, Type, Tuple, AsyncIterator

from src.domain.interfaces.retry_policy import IRetryPolicy
from src.domain.exceptions import (
    WorkerTimeoutError,
    RetryableError,
)


logger = logging.getLogger(__name__)

T = TypeVar("T")


class ExponentialBackoffRetryPolicy(IRetryPolicy):
    """
    Exponential Backoff 재시도 정책

    재시도 간격을 지수적으로 증가시켜 부하를 분산합니다.
    Jitter를 추가하여 Thundering Herd 문제를 방지합니다.
    """

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        jitter: float = 0.1,
        retryable_exceptions: Tuple[Type[Exception], ...] = None,
    ):
        """
        Args:
            max_attempts: 최대 시도 횟수 (초기 시도 포함)
            base_delay: 기본 대기 시간 (초)
            max_delay: 최대 대기 시간 (초)
            jitter: Jitter 비율 (0.0 ~ 1.0)
            retryable_exceptions: 재시도 가능한 예외 타입들 (None이면 기본값 사용)
        """
        if max_attempts < 1:
            raise ValueError("max_attempts는 1 이상이어야 합니다.")
        if base_delay <= 0:
            raise ValueError("base_delay는 0보다 커야 합니다.")
        if max_delay < base_delay:
            raise ValueError("max_delay는 base_delay 이상이어야 합니다.")
        if not 0 <= jitter <= 1:
            raise ValueError("jitter는 0.0 ~ 1.0 사이여야 합니다.")

        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter = jitter

        # 재시도 가능한 예외 타입
        if retryable_exceptions is None:
            self.retryable_exceptions = (
                WorkerTimeoutError,
                RetryableError,
                # Claude SDK 예외는 필요 시 추가
            )
        else:
            self.retryable_exceptions = retryable_exceptions

    def is_retryable(self, error: Exception) -> bool:
        """
        주어진 예외가 재시도 가능한지 판단

        Args:
            error: 발생한 예외

        Returns:
            재시도 가능 여부
        """
        return isinstance(error, self.retryable_exceptions)

    def _calculate_delay(self, attempt: int) -> float:
        """
        Exponential backoff 지연 시간 계산

        지연 시간 = min(base_delay * 2^(attempt-1), max_delay) + jitter

        Args:
            attempt: 현재 시도 번호 (1부터 시작)

        Returns:
            지연 시간 (초)
        """
        # Exponential backoff
        delay = self.base_delay * (2 ** (attempt - 1))

        # Max delay 제한
        delay = min(delay, self.max_delay)

        # Jitter 추가 (Thundering Herd 방지)
        jitter_amount = delay * self.jitter * random.random()
        return delay + jitter_amount

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
        last_exception = None

        for attempt in range(1, self.max_attempts + 1):
            try:
                logger.debug(
                    f"[RetryPolicy] 시도 {attempt}/{self.max_attempts}"
                )
                result = await func(*args, **kwargs)

                # 성공 시 결과 반환
                if attempt > 1:
                    logger.info(
                        f"[RetryPolicy] ✅ 재시도 성공 (시도 {attempt}/{self.max_attempts})"
                    )
                return result

            except Exception as e:
                last_exception = e

                # 재시도 불가능한 예외는 즉시 전파
                if not self.is_retryable(e):
                    logger.debug(
                        f"[RetryPolicy] 재시도 불가능한 예외: {type(e).__name__}"
                    )
                    raise

                # 마지막 시도였으면 예외 전파
                if attempt >= self.max_attempts:
                    logger.error(
                        f"[RetryPolicy] ❌ 재시도 횟수 초과 "
                        f"({self.max_attempts}회): {e}"
                    )
                    raise

                # 재시도 대기
                delay = self._calculate_delay(attempt)
                logger.warning(
                    f"[RetryPolicy] 재시도 대기 "
                    f"(시도 {attempt}/{self.max_attempts}, {delay:.2f}초 후): {e}"
                )
                await asyncio.sleep(delay)

        # 이 코드는 도달하지 않아야 함 (안전장치)
        if last_exception:
            raise last_exception
        else:
            raise RuntimeError("예상치 못한 재시도 로직 오류")

    async def execute_streaming(
        self,
        func: Callable[..., AsyncIterator[T]],
        *args: Any,
        **kwargs: Any
    ) -> AsyncIterator[T]:
        """
        스트리밍 함수에 대한 재시도 로직

        첫 번째 청크 수신 실패 시에만 재시도합니다.
        첫 청크 수신 후 발생한 에러는 재시도하지 않습니다.

        Args:
            func: 재시도할 스트리밍 함수
            *args: 함수 인자
            **kwargs: 함수 키워드 인자

        Yields:
            함수 실행 결과 청크

        Raises:
            재시도 불가능한 예외 또는 최대 재시도 횟수 초과 시 마지막 예외
        """
        last_exception = None

        for attempt in range(1, self.max_attempts + 1):
            # 매 재시도마다 초기화 (루프 안으로 이동)
            # 이전 시도에서 첫 청크를 받았더라도, 새로운 시도는 처음부터 시작
            first_chunk_received = False

            try:
                logger.debug(f"[RetryPolicy] 시도 {attempt}/{self.max_attempts}")

                iterator = func(*args, **kwargs)

                async for chunk in iterator:
                    first_chunk_received = True
                    yield chunk

                # 성공적으로 완료
                if attempt > 1:
                    logger.info(f"[RetryPolicy] ✅ 재시도 성공 (시도 {attempt})")
                return

            except Exception as e:
                last_exception = e

                # 첫 청크를 받은 후 실패한 경우 재시도 안 함
                if first_chunk_received:
                    logger.warning(
                        f"[RetryPolicy] 첫 청크 수신 후 실패, 재시도 안 함: {e}"
                    )
                    raise

                # 재시도 불가능한 예외는 즉시 전파
                if not self.is_retryable(e):
                    logger.debug(f"[RetryPolicy] 재시도 불가능한 예외: {type(e).__name__}")
                    raise

                # 마지막 시도였으면 예외 전파
                if attempt >= self.max_attempts:
                    logger.error(
                        f"[RetryPolicy] ❌ 최대 재시도 횟수 초과 ({self.max_attempts}): {e}"
                    )
                    raise

                # 재시도 대기
                delay = self._calculate_delay(attempt)
                logger.warning(
                    f"[RetryPolicy] ⏳ 재시도 대기 (시도 {attempt}/{self.max_attempts}, "
                    f"{delay:.2f}초 후): {e}"
                )
                await asyncio.sleep(delay)

        if last_exception:
            raise last_exception
