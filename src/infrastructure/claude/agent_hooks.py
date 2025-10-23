"""
Agent SDK Hooks - Worker Tool 호출 전후 검증 및 모니터링

Claude Agent SDK의 Hooks 기능을 활용하여:
1. PreToolUse: Worker Tool 호출 전 입력 검증
2. PostToolUse: Worker Tool 실행 후 모니터링
"""

from typing import Any, Dict, Optional
import time

from src.infrastructure.logging import get_logger

logger = get_logger(__name__)


# ============================================================================
# PreToolUse Hook - 입력 검증
# ============================================================================

async def validate_worker_input(
    input_data: Dict[str, Any],
    tool_use_id: str,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Worker Tool 호출 전 입력 검증.

    과도하게 긴 task_description이나 금지된 패턴을 차단합니다.

    Args:
        input_data: {"tool_name": str, "tool_input": dict}
        tool_use_id: Tool 사용 ID
        context: 컨텍스트 (선택)

    Returns:
        Hook 응답 (deny 시 permissionDecision 포함)
    """
    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    # Worker Tool만 검증 (다른 Tool은 패스)
    if not tool_name.startswith("mcp__workers__"):
        return {}

    task_description = tool_input.get("task_description", "")

    # 1. 과도하게 긴 입력 차단 (20,000자 이상)
    if len(task_description) > 20000:
        logger.warning(
            "Worker Tool 입력이 너무 깁니다",
            tool_name=tool_name,
            input_length=len(task_description),
            max_length=20000
        )
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    f"task_description이 너무 깁니다 "
                    f"({len(task_description):,}자, 최대 20,000자). "
                    "입력을 요약하거나 분할하세요."
                )
            }
        }

    # 2. 금지된 패턴 검사 (예: 시스템 명령어 삽입 시도)
    forbidden_patterns = [
        "rm -rf /",
        "sudo rm",
        "; rm ",
        "&& rm ",
    ]

    for pattern in forbidden_patterns:
        if pattern.lower() in task_description.lower():
            logger.warning(
                "Worker Tool 입력에 금지된 패턴 발견",
                tool_name=tool_name,
                pattern=pattern
            )
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": (
                        f"task_description에 금지된 패턴이 포함되어 있습니다: {pattern}"
                    )
                }
            }

    # 검증 통과
    logger.debug(
        "Worker Tool 입력 검증 통과",
        tool_name=tool_name,
        input_length=len(task_description)
    )
    return {}


# ============================================================================
# PostToolUse Hook - 실행 모니터링
# ============================================================================

# Worker Tool 실행 시간 추적 (tool_use_id -> start_time)
_worker_execution_times: Dict[str, float] = {}
_MAX_EXECUTION_TIMES = 1000  # 최대 추적 개수
_STALE_THRESHOLD = 3600  # 1시간 (초 단위)


def _cleanup_stale_execution_times() -> None:
    """
    오래된 실행 시간 항목 정리 (메모리 누수 방지).

    - 1시간 이상 된 항목 삭제
    - 최대 개수 초과 시 오래된 항목부터 삭제
    """
    current_time = time.time()

    # 1. 1시간 이상 된 항목 정리
    to_delete = [
        tool_id for tool_id, start_time in _worker_execution_times.items()
        if current_time - start_time > _STALE_THRESHOLD
    ]

    for tool_id in to_delete:
        del _worker_execution_times[tool_id]

    if to_delete:
        logger.debug(
            "Cleaned up stale execution times",
            deleted_count=len(to_delete),
            remaining_count=len(_worker_execution_times)
        )

    # 2. 최대 개수 초과 시 오래된 항목부터 삭제
    if len(_worker_execution_times) > _MAX_EXECUTION_TIMES:
        sorted_items = sorted(_worker_execution_times.items(), key=lambda x: x[1])
        to_keep = dict(sorted_items[-_MAX_EXECUTION_TIMES:])
        removed_count = len(_worker_execution_times) - len(to_keep)
        _worker_execution_times.clear()
        _worker_execution_times.update(to_keep)

        logger.warning(
            "Execution times exceeded max limit",
            max_limit=_MAX_EXECUTION_TIMES,
            removed_count=removed_count
        )


async def monitor_worker_execution(
    input_data: Dict[str, Any],
    tool_use_id: str,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Worker Tool 실행 후 모니터링.

    실행 시간을 로깅하고 통계를 수집합니다.

    Args:
        input_data: {"tool_name": str, "tool_input": dict, "tool_output": dict}
        tool_use_id: Tool 사용 ID
        context: 컨텍스트 (선택)

    Returns:
        Hook 응답 (항상 빈 딕셔너리)
    """
    tool_name = input_data.get("tool_name", "")
    tool_output = input_data.get("tool_output", {})

    # Worker Tool만 모니터링
    if not tool_name.startswith("mcp__workers__"):
        return {}

    # 주기적으로 오래된 항목 정리 (10번에 1번 실행)
    import random
    if random.randint(1, 10) == 1:
        _cleanup_stale_execution_times()

    # 실행 시간 계산 (PreToolUse에서 시작 시간 기록 필요)
    start_time = _worker_execution_times.pop(tool_use_id, None)
    if start_time:
        execution_time = time.time() - start_time
        logger.info(
            "Worker Tool 실행 완료",
            tool_name=tool_name,
            execution_time_seconds=f"{execution_time:.2f}",
            success=tool_output.get("success", True)
        )
    else:
        logger.debug(
            "Worker Tool 실행 완료 (실행 시간 미측정)",
            tool_name=tool_name
        )

    return {}


async def record_worker_start_time(
    input_data: Dict[str, Any],
    tool_use_id: str,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Worker Tool 실행 시작 시간 기록 (PostToolUse에서 실행 시간 계산용).

    Args:
        input_data: {"tool_name": str, "tool_input": dict}
        tool_use_id: Tool 사용 ID
        context: 컨텍스트 (선택)

    Returns:
        Hook 응답 (항상 빈 딕셔너리)
    """
    tool_name = input_data.get("tool_name", "")

    # Worker Tool만 기록
    if not tool_name.startswith("mcp__workers__"):
        return {}

    _worker_execution_times[tool_use_id] = time.time()
    return {}


# ============================================================================
# Hook 설정 헬퍼 함수
# ============================================================================

def create_worker_hooks(enable_validation: bool = True, enable_monitoring: bool = True) -> Dict[str, list]:
    """
    Worker Tool용 Hooks 설정 생성.

    Args:
        enable_validation: PreToolUse Hook 활성화 (입력 검증)
        enable_monitoring: PostToolUse Hook 활성화 (실행 모니터링)

    Returns:
        ClaudeAgentOptions의 hooks 파라미터
    """
    from claude_agent_sdk import HookMatcher

    hooks = {}

    # PreToolUse: 입력 검증 + 시작 시간 기록
    # 주의: record_worker_start_time은 monitoring과 함께 활성화해야 메모리 누수 방지
    pre_hooks = []
    if enable_validation:
        pre_hooks.append(validate_worker_input)
    if enable_monitoring:
        pre_hooks.append(record_worker_start_time)

    if pre_hooks:
        hooks["PreToolUse"] = [
            HookMatcher(
                matcher="mcp__workers__*",  # 모든 Worker Tool
                hooks=pre_hooks
            )
        ]

    # PostToolUse: 실행 모니터링 (시작 시간 pop)
    if enable_monitoring:
        hooks["PostToolUse"] = [
            HookMatcher(
                matcher="mcp__workers__*",  # 모든 Worker Tool
                hooks=[monitor_worker_execution]
            )
        ]

    return hooks
