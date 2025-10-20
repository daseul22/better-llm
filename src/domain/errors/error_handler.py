"""에러 핸들러

Better-LLM의 커스텀 예외 클래스 및 에러 처리 유틸리티를 제공합니다.
"""

import traceback
from typing import Optional, Dict, Any
from .error_codes import ErrorCode
from .error_messages import format_error_message


class BetterLLMError(Exception):
    """Better-LLM의 기본 예외 클래스

    모든 Better-LLM 커스텀 예외는 이 클래스를 상속합니다.

    Attributes:
        error_code: 에러 코드
        message: 에러 메시지
        context: 추가 컨텍스트 정보
        original_error: 원본 예외 (있는 경우)

    Examples:
        >>> raise BetterLLMError(
        ...     ErrorCode.WORKER_TIMEOUT,
        ...     worker_name="planner",
        ...     timeout=300
        ... )
    """

    def __init__(
        self,
        error_code: ErrorCode,
        original_error: Optional[Exception] = None,
        **context: Any
    ):
        """에러 초기화

        Args:
            error_code: 에러 코드
            original_error: 원본 예외 (선택)
            **context: 에러 메시지에 포함할 컨텍스트 정보
        """
        self.error_code = error_code
        self.context = context
        self.original_error = original_error

        # 원본 에러가 있으면 context에 추가
        if original_error:
            self.context["error"] = str(original_error)

        # 에러 메시지 생성
        self.message = format_error_message(error_code, **self.context)

        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """에러를 딕셔너리로 변환 (로깅/API 응답용)

        Returns:
            에러 정보를 담은 딕셔너리

        Examples:
            >>> error.to_dict()
            {
                "error_code": "WORKER_TIMEOUT",
                "error_number": 1001,
                "category": "Worker",
                "message": "Worker 'planner'의 실행...",
                "context": {"worker_name": "planner", "timeout": 300}
            }
        """
        return {
            "error_code": self.error_code.name,
            "error_number": self.error_code.value,
            "category": self.error_code.category,
            "message": self.message,
            "context": self.context,
        }

    def __str__(self) -> str:
        """에러를 문자열로 반환"""
        return f"[{self.error_code}] {self.message}"

    def __repr__(self) -> str:
        """에러의 상세 표현 반환"""
        return (
            f"BetterLLMError("
            f"error_code={self.error_code.name}, "
            f"message='{self.message}', "
            f"context={self.context})"
        )


# 카테고리별 예외 클래스
class WorkerError(BetterLLMError):
    """Worker 관련 에러"""
    pass


class ConfigError(BetterLLMError):
    """Config 관련 에러"""
    pass


class SessionError(BetterLLMError):
    """Session 관련 에러"""
    pass


class APIError(BetterLLMError):
    """API 관련 에러"""
    pass


class StorageError(BetterLLMError):
    """Storage 관련 에러"""
    pass


class MetricsError(BetterLLMError):
    """Metrics 관련 에러"""
    pass


class LoggingError(BetterLLMError):
    """Logging 관련 에러"""
    pass


class CacheError(BetterLLMError):
    """Cache 관련 에러"""
    pass


# 에러 코드별 예외 클래스 매핑
ERROR_CLASS_MAPPING: Dict[ErrorCode, type] = {
    # Worker 에러
    ErrorCode.WORKER_TIMEOUT: WorkerError,
    ErrorCode.WORKER_EXECUTION_FAILED: WorkerError,
    ErrorCode.WORKER_NOT_FOUND: WorkerError,
    ErrorCode.WORKER_INITIALIZATION_FAILED: WorkerError,
    ErrorCode.WORKER_TOOL_NOT_AVAILABLE: WorkerError,
    ErrorCode.WORKER_RETRY_EXCEEDED: WorkerError,
    ErrorCode.WORKER_INVALID_INPUT: WorkerError,
    ErrorCode.WORKER_OUTPUT_PARSING_FAILED: WorkerError,
    # Config 에러
    ErrorCode.CONFIG_LOAD_FAILED: ConfigError,
    ErrorCode.CONFIG_INVALID: ConfigError,
    ErrorCode.CONFIG_MISSING_REQUIRED_FIELD: ConfigError,
    ErrorCode.CONFIG_VALIDATION_FAILED: ConfigError,
    ErrorCode.CONFIG_FILE_NOT_FOUND: ConfigError,
    ErrorCode.PROMPT_FILE_NOT_FOUND: ConfigError,
    ErrorCode.PROMPT_LOAD_FAILED: ConfigError,
    # Session 에러
    ErrorCode.SESSION_NOT_FOUND: SessionError,
    ErrorCode.SESSION_SAVE_FAILED: SessionError,
    ErrorCode.SESSION_LOAD_FAILED: SessionError,
    ErrorCode.SESSION_INVALID_STATE: SessionError,
    ErrorCode.SESSION_EXCEEDED_MAX_TURNS: SessionError,
    ErrorCode.SESSION_COMPRESSION_FAILED: SessionError,
    ErrorCode.SESSION_DECOMPRESSION_FAILED: SessionError,
    # API 에러
    ErrorCode.API_KEY_MISSING: APIError,
    ErrorCode.API_KEY_INVALID: APIError,
    ErrorCode.API_RATE_LIMIT_EXCEEDED: APIError,
    ErrorCode.API_REQUEST_FAILED: APIError,
    ErrorCode.API_RESPONSE_INVALID: APIError,
    ErrorCode.API_TIMEOUT: APIError,
    ErrorCode.API_NETWORK_ERROR: APIError,
    ErrorCode.API_SERVER_ERROR: APIError,
    # Storage 에러
    ErrorCode.STORAGE_WRITE_FAILED: StorageError,
    ErrorCode.STORAGE_READ_FAILED: StorageError,
    ErrorCode.STORAGE_DELETE_FAILED: StorageError,
    ErrorCode.STORAGE_PERMISSION_DENIED: StorageError,
    ErrorCode.STORAGE_DISK_FULL: StorageError,
    ErrorCode.STORAGE_INVALID_PATH: StorageError,
    # Metrics 에러
    ErrorCode.METRICS_COLLECTION_FAILED: MetricsError,
    ErrorCode.METRICS_QUEUE_FULL: MetricsError,
    ErrorCode.METRICS_FLUSH_FAILED: MetricsError,
    ErrorCode.METRICS_INVALID_VALUE: MetricsError,
    # Logging 에러
    ErrorCode.LOGGING_SETUP_FAILED: LoggingError,
    ErrorCode.LOGGING_FILE_WRITE_FAILED: LoggingError,
    ErrorCode.LOGGING_ROTATION_FAILED: LoggingError,
    # Cache 에러
    ErrorCode.CACHE_SET_FAILED: CacheError,
    ErrorCode.CACHE_GET_FAILED: CacheError,
    ErrorCode.CACHE_INVALIDATION_FAILED: CacheError,
    ErrorCode.CACHE_SERIALIZATION_FAILED: CacheError,
}


def handle_error(
    error_code: ErrorCode,
    original_error: Optional[Exception] = None,
    log: bool = True,
    **context: Any
) -> BetterLLMError:
    """에러를 처리하고 적절한 예외를 반환

    Args:
        error_code: 에러 코드
        original_error: 원본 예외 (선택)
        log: 로깅 여부 (기본: True)
        **context: 에러 컨텍스트 정보

    Returns:
        적절한 BetterLLMError 서브클래스 인스턴스

    Examples:
        >>> try:
        ...     worker.run(task)
        ... except TimeoutError as e:
        ...     raise handle_error(
        ...         ErrorCode.WORKER_TIMEOUT,
        ...         original_error=e,
        ...         worker_name="planner",
        ...         timeout=300
        ...     )
    """
    # 에러 코드에 맞는 예외 클래스 선택
    error_class = ERROR_CLASS_MAPPING.get(error_code, BetterLLMError)

    # 예외 인스턴스 생성
    exception = error_class(
        error_code=error_code,
        original_error=original_error,
        **context
    )

    # 로깅 (순환 import 방지를 위해 여기서 import)
    if log:
        try:
            from src.infrastructure.logging import get_logger
            logger = get_logger(__name__)

            # 에러 레벨에 따라 다르게 로깅
            if error_code.value >= 9000:
                logger.critical(
                    exception.message,
                    error_code=error_code.name,
                    **context,
                    exc_info=original_error
                )
            elif error_code.value >= 4000:
                logger.error(
                    exception.message,
                    error_code=error_code.name,
                    **context,
                    exc_info=original_error
                )
            else:
                logger.warning(
                    exception.message,
                    error_code=error_code.name,
                    **context
                )
        except ImportError:
            # 로깅 모듈이 없으면 무시
            pass

    return exception
