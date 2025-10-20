"""
에러 추적 및 집계 모듈

에러 발생을 추적하고 통계를 수집합니다.
"""

import threading
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Any

from .structured_logger import get_logger

logger = get_logger(__name__, component="ErrorTracker")

# 에러 통계 전역 변수
_error_counts: Dict[str, int] = defaultdict(int)
_recent_errors: List[Dict[str, Any]] = []
MAX_RECENT_ERRORS = 100

# 동시성 제어를 위한 Lock
_error_stats_lock = threading.Lock()


def track_error(
    error: Exception,
    context: str,
    **metadata: Any
) -> None:
    """
    에러를 추적하고 로그에 기록합니다.

    Args:
        error: 발생한 예외
        context: 에러 발생 컨텍스트 (예: "worker_execution", "config_loading")
        **metadata: 추가 메타데이터 (worker_name, task_id 등)

    Example:
        >>> try:
        ...     result = await execute_task()
        ... except Exception as e:
        ...     track_error(e, "task_execution", worker_name="planner", task_id="abc123")
    """
    error_type = type(error).__name__

    # Lock으로 보호된 영역
    with _error_stats_lock:
        _error_counts[error_type] += 1

        error_info = {
            "timestamp": datetime.now().isoformat(),
            "error_type": error_type,
            "error_message": str(error),
            "context": context,
            **metadata
        }

        _recent_errors.append(error_info)
        if len(_recent_errors) > MAX_RECENT_ERRORS:
            _recent_errors.pop(0)

    # 로깅은 Lock 밖에서 (성능 개선)
    logger.error(
        "Error tracked",
        error_type=error_type,
        error_message=str(error),
        context=context,
        **metadata,
        exc_info=(type(error), error, error.__traceback__)
    )


def get_error_stats() -> Dict[str, Any]:
    """
    에러 통계를 반환합니다.

    Returns:
        에러 통계 딕셔너리:
        - error_counts: 에러 타입별 발생 횟수
        - recent_errors: 최근 10개 에러 정보
        - total_errors: 총 에러 발생 횟수

    Example:
        >>> stats = get_error_stats()
        >>> print(stats["total_errors"])
        >>> for error in stats["recent_errors"]:
        ...     print(error["error_type"], error["context"])
    """
    # Lock으로 보호된 영역
    with _error_stats_lock:
        return {
            "error_counts": dict(_error_counts),
            "recent_errors": _recent_errors[-10:].copy(),  # 복사본 반환
            "total_errors": sum(_error_counts.values())
        }


def reset_error_stats() -> None:
    """
    에러 통계를 초기화합니다.

    새 세션 시작 시 호출하여 이전 세션의 에러 통계를 초기화합니다.
    """
    global _error_counts, _recent_errors
    _error_counts.clear()
    _recent_errors.clear()
    logger.info("Error statistics reset")


def get_error_summary(limit: int = 5) -> str:
    """
    에러 통계 요약을 문자열로 반환합니다.

    Args:
        limit: 표시할 최대 에러 타입 수

    Returns:
        에러 통계 요약 문자열

    Example:
        >>> print(get_error_summary())
        Total errors: 3
        Top errors:
        - TimeoutError: 2
        - ValueError: 1
    """
    stats = get_error_stats()
    total = stats["total_errors"]

    if total == 0:
        return "No errors recorded"

    summary_lines = [f"Total errors: {total}", "Top errors:"]

    # 에러 타입별 횟수를 내림차순 정렬
    sorted_errors = sorted(
        stats["error_counts"].items(),
        key=lambda x: x[1],
        reverse=True
    )

    for error_type, count in sorted_errors[:limit]:
        summary_lines.append(f"  - {error_type}: {count}")

    return "\n".join(summary_lines)
