"""
Domain 계층 예외 정의.

비즈니스 로직 관련 예외들을 정의합니다.
Use Case에서 Infrastructure 예외를 Domain 예외로 변환하여 사용합니다.

이 모듈은 두 가지 예외 시스템을 제공합니다:
1. Domain 계층 예외 (DomainException 계열): 비즈니스 로직 예외
2. Better-LLM 시스템 예외 (BetterLLMError 계열): 인프라/시스템 예외

Examples:
    >>> from src.domain.exceptions import WorkerExecutionError, ValidationError
    >>> from src.domain.exceptions import BetterLLMError, ErrorCode, handle_error
"""

from typing import Optional

# Better-LLM 시스템 예외 (error_handler에서 import)
from domain.errors.error_handler import (
    BetterLLMError,
    WorkerError,
    ConfigError,
    SessionError,
    APIError,
    StorageError,
    MetricsError,
    LoggingError,
    CacheError,
    handle_error,
    ERROR_CLASS_MAPPING,
)
from domain.errors.error_codes import ErrorCode
from domain.errors.error_messages import (
    get_error_message,
    format_error_message,
    ERROR_MESSAGES,
)


class DomainException(Exception):
    """Domain 계층 기본 예외"""
    pass


class ValidationError(DomainException):
    """입력 검증 실패"""
    pass


class WorkerExecutionError(DomainException):
    """Worker 실행 실패"""

    def __init__(
        self,
        worker_name: str,
        message: str,
        original_error: Optional[Exception] = None
    ):
        """
        Args:
            worker_name: Worker 이름
            message: 에러 메시지
            original_error: 원본 예외 (선택)
        """
        self.worker_name = worker_name
        self.original_error = original_error
        super().__init__(f"[{worker_name}] {message}")


class WorkerNotFoundError(DomainException):
    """Worker를 찾을 수 없음"""

    def __init__(self, worker_name: str):
        """
        Args:
            worker_name: Worker 이름
        """
        self.worker_name = worker_name
        super().__init__(f"Worker '{worker_name}'를 찾을 수 없습니다.")


class WorkerTimeoutError(DomainException):
    """Worker 실행 타임아웃"""

    def __init__(self, worker_name: str, message: Optional[str] = None, timeout: Optional[float] = None):
        """
        Args:
            worker_name: Worker 이름
            message: 에러 메시지 (선택)
            timeout: 타임아웃 시간 (초, 선택)
        """
        self.worker_name = worker_name
        self.timeout = timeout
        if message:
            super().__init__(message)
        elif timeout:
            super().__init__(f"Worker '{worker_name}' 실행 타임아웃 ({timeout}초)")
        else:
            super().__init__(f"Worker '{worker_name}' 실행 타임아웃")


class PreconditionFailedError(DomainException):
    """사전 조건 실패"""

    def __init__(self, condition: str):
        """
        Args:
            condition: 실패한 조건 설명
        """
        self.condition = condition
        super().__init__(f"사전 조건 실패: {condition}")


class CircuitOpenError(DomainException):
    """Circuit이 OPEN 상태일 때 발생하는 예외"""

    def __init__(self, circuit_name: str, message: Optional[str] = None):
        """
        Args:
            circuit_name: Circuit Breaker 이름
            message: 에러 메시지 (선택)
        """
        self.circuit_name = circuit_name
        if message:
            super().__init__(message)
        else:
            super().__init__(
                f"Circuit '{circuit_name}'이(가) OPEN 상태입니다. "
                f"잠시 후 다시 시도하세요."
            )


class RetryableError(DomainException):
    """재시도 가능한 예외의 기본 클래스"""
    pass


# Export all exception classes
__all__ = [
    # Domain 계층 예외
    "DomainException",
    "ValidationError",
    "WorkerExecutionError",
    "WorkerNotFoundError",
    "WorkerTimeoutError",
    "PreconditionFailedError",
    "CircuitOpenError",
    "RetryableError",
    # Better-LLM 시스템 예외
    "BetterLLMError",
    "WorkerError",
    "ConfigError",
    "SessionError",
    "APIError",
    "StorageError",
    "MetricsError",
    "LoggingError",
    "CacheError",
    # 에러 핸들러 및 유틸리티
    "handle_error",
    "ERROR_CLASS_MAPPING",
    "ErrorCode",
    "get_error_message",
    "format_error_message",
    "ERROR_MESSAGES",
]
