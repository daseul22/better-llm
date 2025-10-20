"""
구조화된 로깅 설정 모듈

structlog 라이브러리를 사용하여 JSON 형식 로그 출력,
세션 ID 및 Worker 이름 등 메타데이터를 자동으로 포함합니다.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Any, Optional, Union

import structlog
from structlog.processors import JSONRenderer
from structlog.stdlib import add_log_level

# JSON 직렬화 가능한 타입 정의
JSONSerializable = Union[str, int, float, bool, None, dict, list]


def _get_default_log_dir() -> str:
    """
    기본 로그 디렉토리 경로 반환 (~/.better-llm/{project-name}/logs)

    Returns:
        로그 디렉토리 경로 (문자열)
    """
    try:
        from ..config import get_data_dir
        return str(get_data_dir("logs"))
    except Exception:
        # import 실패 시 폴백
        return "logs"


def configure_structlog(
    log_dir: Optional[str] = None,
    log_level: str = "INFO",
    enable_json: bool = True,
) -> None:
    """
    structlog를 설정합니다.

    Args:
        log_dir: 로그 파일 디렉토리 (None이면 ~/.better-llm/{project-name}/logs 사용)
        log_level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_json: JSON 형식 출력 활성화 여부 (False시 콘솔 형식)

    Example:
        >>> configure_structlog(log_dir=None, log_level="INFO", enable_json=True)
        >>> logger = get_logger(__name__, session_id="abc123")
        >>> logger.info("Task started", worker_name="planner", task_id="task_001")
    """
    if log_dir is None:
        log_dir = _get_default_log_dir()

    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # 프로세서 체인 설정
    processors = [
        structlog.contextvars.merge_contextvars,  # context vars 병합
        structlog.stdlib.add_logger_name,  # 로거 이름 추가
        add_log_level,  # 로그 레벨 추가
        structlog.processors.TimeStamper(fmt="iso"),  # ISO 8601 타임스탬프
        structlog.processors.CallsiteParameterAdder(  # 호출 위치 정보 추가
            [
                structlog.processors.CallsiteParameter.PATHNAME,
                structlog.processors.CallsiteParameter.FUNC_NAME,
                structlog.processors.CallsiteParameter.LINENO,
            ]
        ),
        structlog.stdlib.PositionalArgumentsFormatter(),  # 위치 인자 포맷팅
        structlog.processors.StackInfoRenderer(),  # 스택 정보 렌더링
        structlog.processors.format_exc_info,  # 예외 정보 포맷팅
        structlog.processors.UnicodeDecoder(),  # 유니코드 디코딩
    ]

    if enable_json:
        processors.append(JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # 표준 logging 설정
    # 메인 로그: 10MB (모든 레벨의 로그)
    # 에러 로그: 5MB (ERROR 이상만 필터링되므로 용량 적음)
    # 디버그 로그: 20MB (상세 정보가 많아 용량 증가)
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, log_level.upper()),
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.handlers.RotatingFileHandler(
                log_path / "better-llm.log",
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5,
                encoding="utf-8"
            ),
        ],
    )

    # 에러 로그 전용 핸들러 추가
    error_handler = logging.handlers.RotatingFileHandler(
        log_path / "better-llm-error.log",
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3,
        encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    logging.getLogger().addHandler(error_handler)

    # DEBUG 레벨이 활성화된 경우 디버그 로그 파일 추가
    if log_level.upper() == "DEBUG":
        debug_handler = logging.handlers.RotatingFileHandler(
            log_path / "better-llm-debug.log",
            maxBytes=20 * 1024 * 1024,  # 20MB
            backupCount=3,
            encoding="utf-8"
        )
        debug_handler.setLevel(logging.DEBUG)
        logging.getLogger().addHandler(debug_handler)


def get_logger(name: str, **context: JSONSerializable) -> structlog.stdlib.BoundLogger:
    """
    구조화된 로거를 가져옵니다.

    Args:
        name: 로거 이름 (일반적으로 __name__ 사용)
        **context: 기본 컨텍스트 (JSON 직렬화 가능한 타입만 허용)
                  예: session_id, worker_name, task_id 등

    Returns:
        BoundLogger 인스턴스 (메타데이터가 바인딩된 로거)

    Example:
        >>> logger = get_logger(__name__, session_id="abc123", worker_name="planner")
        >>> logger.info("Processing task", task_description="Analyze requirements")
        # Output (JSON): {"event": "Processing task", "session_id": "abc123",
        #                 "worker_name": "planner", "task_description": "Analyze requirements",
        #                 "timestamp": "2025-01-20T10:30:00Z", "level": "info"}

    Note:
        context 파라미터는 JSON 직렬화 가능한 타입만 허용합니다.
        복잡한 객체를 전달하면 JSON 렌더링 시 오류가 발생할 수 있습니다.
    """
    logger = structlog.get_logger(name)
    if context:
        logger = logger.bind(**context)
    return logger


def log_exception_silently(
    logger: structlog.stdlib.BoundLogger,
    exception: Exception,
    message: str = "Runtime error occurred",
    **extra_context: JSONSerializable
) -> None:
    """
    예외를 조용히 로그에 기록합니다 (프로그램 종료하지 않음).

    Args:
        logger: structlog 로거 인스턴스
        exception: 발생한 예외
        message: 에러 메시지
        **extra_context: 추가 컨텍스트 정보

    Example:
        >>> try:
        ...     risky_operation()
        ... except Exception as e:
        ...     log_exception_silently(logger, e, "Operation failed", operation="risky_op")
    """
    import traceback

    logger.error(
        message,
        error_type=type(exception).__name__,
        error_message=str(exception),
        traceback=traceback.format_exc(),
        **extra_context,
        exc_info=True  # 스택 트레이스 포함
    )
