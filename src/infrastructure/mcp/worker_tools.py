"""
Worker Agent Tools - Worker Agent들을 Custom Tool로 래핑

각 Worker Agent를 Claude Agent SDK의 Custom Tool로 만들어,
Manager Agent가 필요할 때 호출할 수 있도록 합니다.
"""

from typing import Any, Dict, Callable, Optional
from pathlib import Path
import logging
import asyncio
from functools import wraps
from datetime import datetime

from claude_agent_sdk import tool, create_sdk_mcp_server
from claude_agent_sdk.types import ClaudeAgentOptions

from ..claude import WorkerAgent
from ...domain.models import AgentConfig
from ...domain.services import MetricsCollector
from ..config import JsonConfigLoader, get_project_root

logger = logging.getLogger(__name__)


# 에러 통계
_ERROR_STATS = {
    "planner": {"attempts": 0, "failures": 0},
    "coder": {"attempts": 0, "failures": 0},
    "reviewer": {"attempts": 0, "failures": 0},
    "tester": {"attempts": 0, "failures": 0}
}


async def retry_with_backoff(
    func: Callable,
    worker_name: str,
    max_retries: int = 3,
    base_delay: float = 1.0
) -> Dict[str, Any]:
    """
    재시도 로직이 포함된 래퍼

    Args:
        func: 실행할 비동기 함수
        worker_name: Worker 이름 (로깅용)
        max_retries: 최대 재시도 횟수
        base_delay: 기본 대기 시간 (초)

    Returns:
        함수 실행 결과
    """
    _ERROR_STATS[worker_name]["attempts"] += 1

    for attempt in range(max_retries):
        try:
            result = await func()
            return result

        except Exception as e:
            _ERROR_STATS[worker_name]["failures"] += 1

            if attempt < max_retries - 1:
                # Exponential backoff
                wait_time = base_delay * (2 ** attempt)
                logger.warning(
                    f"⚠️  [{worker_name}] 시도 {attempt + 1}/{max_retries} 실패: {e}. "
                    f"{wait_time}초 후 재시도..."
                )
                await asyncio.sleep(wait_time)
            else:
                # 최종 실패 - 예외를 다시 던져서 호출자가 처리하도록 함
                logger.error(
                    f"❌ [{worker_name}] {max_retries}회 시도 후 최종 실패: {e}"
                )
                raise

    # 여기 도달하면 안 됨
    raise RuntimeError("Unexpected error in retry_with_backoff")


# 전역 변수로 Worker Agent 인스턴스들을 저장
_WORKER_AGENTS: Dict[str, WorkerAgent] = {}

# 메트릭 수집기 (선택적)
_METRICS_COLLECTOR: Optional[MetricsCollector] = None
_CURRENT_SESSION_ID: Optional[str] = None

# 워크플로우 콜백 (TUI에서 설정)
_WORKFLOW_CALLBACK: Optional[Callable] = None


def initialize_workers(config_path: Path):
    """
    Worker Agent들을 초기화합니다.

    Args:
        config_path: Agent 설정 파일 경로
    """
    global _WORKER_AGENTS

    loader = JsonConfigLoader(get_project_root())
    worker_configs = loader.load_agent_configs()

    for config in worker_configs:
        worker = WorkerAgent(config)
        _WORKER_AGENTS[config.name] = worker
        logger.info(f"✅ Worker Agent 초기화: {config.name} ({config.role})")


def set_metrics_collector(collector: MetricsCollector, session_id: str) -> None:
    """
    메트릭 컬렉터 설정 (TUI/CLI에서 호출)

    Args:
        collector: 메트릭 수집기
        session_id: 현재 세션 ID
    """
    global _METRICS_COLLECTOR, _CURRENT_SESSION_ID
    _METRICS_COLLECTOR = collector
    _CURRENT_SESSION_ID = session_id
    logger.info(f"✅ 메트릭 컬렉터 설정 완료 (Session: {session_id})")


def update_session_id(session_id: str) -> None:
    """
    현재 세션 ID 업데이트

    Args:
        session_id: 새 세션 ID
    """
    global _CURRENT_SESSION_ID
    _CURRENT_SESSION_ID = session_id
    logger.info(f"✅ 세션 ID 업데이트: {session_id}")


def set_workflow_callback(callback: Optional[Callable]) -> None:
    """
    워크플로우 상태 업데이트 콜백 설정

    Args:
        callback: 워크플로우 상태 업데이트 함수
                  시그니처: callback(worker_name: str, status: str, error: Optional[str])
    """
    global _WORKFLOW_CALLBACK
    _WORKFLOW_CALLBACK = callback
    logger.info("✅ 워크플로우 콜백 설정 완료")


async def _execute_worker_task(
    worker_name: str,
    task_description: str,
    use_retry: bool = False
) -> Dict[str, Any]:
    """
    Worker Agent 실행 공통 로직

    Args:
        worker_name: Worker 이름 (예: "planner", "coder")
        task_description: 작업 설명
        use_retry: 재시도 로직 사용 여부

    Returns:
        Agent 실행 결과
    """
    logger.debug(f"[{worker_name.capitalize()} Tool] 작업 실행: {task_description[:50]}...")

    worker = _WORKER_AGENTS.get(worker_name)
    if not worker:
        return {
            "content": [
                {"type": "text", "text": f"❌ {worker_name.capitalize()} Agent를 찾을 수 없습니다."}
            ]
        }

    # 메트릭 수집 시작
    start_time = datetime.now()
    success = False
    error_message = None

    # 워크플로우 콜백: RUNNING 상태
    if _WORKFLOW_CALLBACK:
        try:
            _WORKFLOW_CALLBACK(worker_name, "running", None)
        except Exception as e:
            logger.warning(f"워크플로우 콜백 실행 실패 (running): {e}")

    async def execute():
        result = ""
        async for chunk in worker.execute_task(task_description):
            result += chunk
        return {"content": [{"type": "text", "text": result}]}

    try:
        if use_retry:
            result = await retry_with_backoff(execute, worker_name)
        else:
            _ERROR_STATS[worker_name]["attempts"] += 1
            result = await execute()

        success = True

        # 워크플로우 콜백: COMPLETED 상태
        if _WORKFLOW_CALLBACK:
            try:
                _WORKFLOW_CALLBACK(worker_name, "completed", None)
            except Exception as e:
                logger.warning(f"워크플로우 콜백 실행 실패 (completed): {e}")

        return result

    except Exception as e:
        _ERROR_STATS[worker_name]["failures"] += 1
        error_message = str(e)
        logger.error(f"[{worker_name.capitalize()} Tool] 실행 실패: {e}")

        # 워크플로우 콜백: FAILED 상태
        if _WORKFLOW_CALLBACK:
            try:
                _WORKFLOW_CALLBACK(worker_name, "failed", str(e))
            except Exception as callback_error:
                logger.warning(f"워크플로우 콜백 실행 실패 (failed): {callback_error}")

        return {
            "content": [
                {"type": "text", "text": f"❌ {worker_name.capitalize()} 실행 실패: {e}"}
            ]
        }

    finally:
        # 메트릭 기록 (컬렉터가 설정되어 있으면)
        if _METRICS_COLLECTOR and _CURRENT_SESSION_ID:
            end_time = datetime.now()
            try:
                _METRICS_COLLECTOR.record_worker_execution(
                    session_id=_CURRENT_SESSION_ID,
                    worker_name=worker_name,
                    task_description=task_description[:100],  # 너무 길면 잘라냄
                    start_time=start_time,
                    end_time=end_time,
                    success=success,
                    tokens_used=None,  # 추후 Claude SDK에서 토큰 정보 가져오면 추가
                    error_message=error_message,
                )
            except Exception as metrics_error:
                # 메트릭 기록 실패는 로그만 남기고 무시
                logger.warning(f"메트릭 기록 실패: {metrics_error}")


@tool(
    "execute_planner_task",
    "Planner Agent에게 작업을 할당합니다. 요구사항 분석 및 계획 수립을 담당합니다.",
    {"task_description": str}
)
async def execute_planner_task(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Planner Agent 실행 (재시도 로직 포함)

    Args:
        args: {"task_description": "작업 설명"}

    Returns:
        Agent 실행 결과
    """
    return await _execute_worker_task("planner", args["task_description"], use_retry=True)


@tool(
    "execute_coder_task",
    "Coder Agent에게 작업을 할당합니다. 코드 작성, 수정, 리팩토링을 담당합니다.",
    {"task_description": str}
)
async def execute_coder_task(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Coder Agent 실행

    Args:
        args: {"task_description": "작업 설명"}

    Returns:
        Agent 실행 결과
    """
    return await _execute_worker_task("coder", args["task_description"], use_retry=False)


@tool(
    "execute_tester_task",
    "Tester Agent에게 작업을 할당합니다. 테스트 작성 및 실행을 담당합니다.",
    {"task_description": str}
)
async def execute_tester_task(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tester Agent 실행

    Args:
        args: {"task_description": "작업 설명"}

    Returns:
        Agent 실행 결과
    """
    return await _execute_worker_task("tester", args["task_description"], use_retry=False)


@tool(
    "execute_reviewer_task",
    "Reviewer Agent에게 작업을 할당합니다. 코드 리뷰 및 품질 검증을 담당합니다.",
    {"task_description": str}
)
async def execute_reviewer_task(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Reviewer Agent 실행

    Args:
        args: {"task_description": "작업 설명"}

    Returns:
        Agent 실행 결과
    """
    return await _execute_worker_task("reviewer", args["task_description"], use_retry=False)


def get_error_statistics() -> Dict[str, Any]:
    """
    에러 통계 조회

    Returns:
        각 Worker의 시도/실패 통계 및 에러율
    """
    stats = {}
    for worker_name, data in _ERROR_STATS.items():
        attempts = data["attempts"]
        failures = data["failures"]
        error_rate = (failures / attempts * 100) if attempts > 0 else 0.0

        stats[worker_name] = {
            "attempts": attempts,
            "failures": failures,
            "successes": attempts - failures,
            "error_rate": round(error_rate, 2)
        }

    return stats


def reset_error_statistics():
    """
    에러 통계 초기화
    """
    global _ERROR_STATS
    for worker_name in _ERROR_STATS:
        _ERROR_STATS[worker_name]["attempts"] = 0
        _ERROR_STATS[worker_name]["failures"] = 0
    logger.info("✅ 에러 통계 초기화 완료")


def log_error_summary():
    """
    에러 통계 요약 로그 출력
    """
    stats = get_error_statistics()
    logger.info("=" * 60)
    logger.info("📊 Worker Tools 에러 통계")
    logger.info("=" * 60)

    for worker_name, data in stats.items():
        logger.info(
            f"[{worker_name.upper()}] "
            f"시도: {data['attempts']}, "
            f"성공: {data['successes']}, "
            f"실패: {data['failures']}, "
            f"에러율: {data['error_rate']}%"
        )

    logger.info("=" * 60)


def create_worker_tools_server():
    """
    Worker Tool들을 포함하는 MCP 서버 생성

    Returns:
        MCP 서버 인스턴스
    """
    server = create_sdk_mcp_server(
        name="workers",
        version="1.0.0",
        tools=[
            execute_planner_task,
            execute_coder_task,
            execute_reviewer_task,
            execute_tester_task
        ]
    )

    logger.info("✅ Worker Tools MCP Server 생성 완료")

    return server
