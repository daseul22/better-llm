"""
Worker Agent Tools - Worker Agent들을 Custom Tool로 래핑

각 Worker Agent를 Claude Agent SDK의 Custom Tool로 만들어,
Manager Agent가 필요할 때 호출할 수 있도록 합니다.

Phase 2-1 Level 3: WorkerExecutor 및 Level 1 모듈과 통합하여 중복 코드 제거
"""

from typing import Any, Dict, Callable, Optional
from pathlib import Path
import logging
import os

from claude_agent_sdk import tool, create_sdk_mcp_server

from ..claude import WorkerAgent
from domain.services import MetricsCollector
from ..config import JsonConfigLoader, get_project_root
from ..logging import get_logger

# Level 1 및 Level 2 모듈 Import
from infrastructure.mcp.review_cycle_manager import ReviewCycleManager
from infrastructure.mcp.commit_validator import CommitSafetyValidator
from infrastructure.mcp.workflow_callback_handler import (
    WorkflowCallbackHandler,
    WorkflowEventType
)
from infrastructure.mcp.error_statistics_manager import ErrorStatisticsManager
from infrastructure.mcp.parallel_executor import ParallelExecutor
from infrastructure.mcp.worker_executor import WorkerExecutor, WorkerExecutionContext

logger = get_logger(__name__, component="WorkerTools")


# ============================================================================
# 전역 변수 (Global State Management)
# ============================================================================

# Worker Agent 인스턴스들
_WORKER_AGENTS: Dict[str, WorkerAgent] = {}

# WorkerExecutor 인스턴스 (싱글톤 패턴)
_WORKER_EXECUTOR: Optional[WorkerExecutor] = None

# 메트릭 수집기 (선택적)
_METRICS_COLLECTOR: Optional[MetricsCollector] = None
_CURRENT_SESSION_ID: Optional[str] = None

# Worker 출력 스트리밍 콜백 (TUI에서 설정)
_WORKER_OUTPUT_CALLBACK: Optional[Callable] = None


# ============================================================================
# Worker별 타임아웃 설정
# ============================================================================

def _get_timeout_from_env(worker_name: str, default: int) -> int:
    """
    환경변수에서 타임아웃 값 가져오기 (안전한 int 변환)

    Args:
        worker_name: Worker 이름 (예: "planner", "coder")
        default: 기본값

    Returns:
        타임아웃 값 (초)
    """
    env_var = f"WORKER_TIMEOUT_{worker_name.upper()}"
    value = os.getenv(env_var)

    if value is None:
        return default

    try:
        return int(value)
    except ValueError:
        logger.warning(
            f"환경변수 {env_var}의 값 '{value}'을(를) 정수로 변환할 수 없습니다. "
            f"기본값 {default}초를 사용합니다."
        )
        return default


# Worker별 타임아웃 설정 (초 단위, 환경변수 > system_config.json > 기본값 순)
_WORKER_TIMEOUTS = {
    "planner": _get_timeout_from_env("planner", 300),
    "coder": _get_timeout_from_env("coder", 600),
    "reviewer": _get_timeout_from_env("reviewer", 300),
    "tester": _get_timeout_from_env("tester", 600),
    "committer": _get_timeout_from_env("committer", 180),
    "ideator": _get_timeout_from_env("ideator", 300),
    "product_manager": _get_timeout_from_env("product_manager", 300),
}


def _load_worker_timeouts_from_config():
    """
    system_config.json에서 Worker 타임아웃 로드

    환경변수가 설정되어 있으면 우선 사용,
    없으면 system_config.json 값 사용,
    둘 다 없으면 기본값 사용
    """
    global _WORKER_TIMEOUTS

    try:
        from ..config import load_system_config

        config = load_system_config()
        timeouts = config.get("timeouts", {})

        # 환경변수 > system_config.json > 기본값 순으로 우선순위
        _WORKER_TIMEOUTS["planner"] = _get_timeout_from_env(
            "planner", timeouts.get("planner_timeout", 300)
        )
        _WORKER_TIMEOUTS["coder"] = _get_timeout_from_env(
            "coder", timeouts.get("coder_timeout", 600)
        )
        _WORKER_TIMEOUTS["reviewer"] = _get_timeout_from_env(
            "reviewer", timeouts.get("reviewer_timeout", 300)
        )
        _WORKER_TIMEOUTS["tester"] = _get_timeout_from_env(
            "tester", timeouts.get("tester_timeout", 600)
        )
        _WORKER_TIMEOUTS["committer"] = _get_timeout_from_env(
            "committer", timeouts.get("committer_timeout", 180)
        )
        _WORKER_TIMEOUTS["ideator"] = _get_timeout_from_env(
            "ideator", timeouts.get("ideator_timeout", 300)
        )
        _WORKER_TIMEOUTS["product_manager"] = _get_timeout_from_env(
            "product_manager", timeouts.get("product_manager_timeout", 300)
        )

        logger.debug(f"Worker 타임아웃 설정 로드 완료: {_WORKER_TIMEOUTS}")

    except Exception as e:
        logger.warning(f"system_config.json에서 타임아웃 로드 실패: {e}. 기본값 사용.")


# ============================================================================
# 초기화 및 설정 함수
# ============================================================================

def initialize_workers(config_path: Path):
    """
    Worker Agent들을 초기화하고 WorkerExecutor 및 ParallelExecutor를 생성합니다.

    Args:
        config_path: Agent 설정 파일 경로
    """
    global _WORKER_AGENTS, _WORKER_EXECUTOR, _PARALLEL_EXECUTOR

    # system_config.json에서 타임아웃 설정 로드
    _load_worker_timeouts_from_config()

    # system_config.json에서 max_review_iterations 로드
    max_cycles = 3
    try:
        from ..config import load_system_config
        config = load_system_config()
        max_cycles = config.get("workflow_limits", {}).get(
            "max_review_iterations", 3
        )
        logger.info(f"✅ Review cycle 최대 횟수: {max_cycles}회")
    except Exception as e:
        logger.warning(f"max_review_iterations 로드 실패: {e}. 기본값 3 사용.")
        max_cycles = 3

    # Worker Agent 초기화
    loader = JsonConfigLoader(get_project_root())
    worker_configs = loader.load_agent_configs()

    for config in worker_configs:
        worker = WorkerAgent(config)
        _WORKER_AGENTS[config.name] = worker
        logger.info(
            "Worker agent initialized",
            worker_name=config.name,
            role=config.role,
            model=config.model
        )

    # WorkerExecutor 초기화 (Level 1 매니저들과 함께)
    _WORKER_EXECUTOR = WorkerExecutor(
        review_manager=ReviewCycleManager(max_cycles=max_cycles),
        commit_validator=CommitSafetyValidator(),
        callback_handler=WorkflowCallbackHandler(),
        error_manager=ErrorStatisticsManager()
    )
    logger.info("✅ WorkerExecutor initialized with Level 1 managers")

    # ParallelExecutor는 execute_parallel_tasks에서 동적으로 생성
    # (task_executor 콜백 함수 필요)
    logger.info("✅ Worker initialization completed")


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
    logger.info("Metrics collector configured", session_id=session_id)


def update_session_id(session_id: str) -> None:
    """
    현재 세션 ID 업데이트

    Args:
        session_id: 새 세션 ID
    """
    global _CURRENT_SESSION_ID
    _CURRENT_SESSION_ID = session_id
    logger.info("Session ID updated", session_id=session_id)


def set_workflow_callback(callback: Optional[Callable]) -> None:
    """
    워크플로우 상태 업데이트 콜백 설정

    Args:
        callback: 워크플로우 상태 업데이트 함수
                  시그니처: callback(worker_name: str, status: str, error: Optional[str])
    """
    global _WORKER_EXECUTOR

    if not _WORKER_EXECUTOR:
        logger.warning("WorkerExecutor not initialized, callback not set")
        return

    if callback:
        # 기존 콜백을 WorkflowCallbackHandler 형식으로 래핑
        def wrapped_callback(context: Dict[str, Any]) -> None:
            callback(
                context.get("worker_name"),
                context.get("status"),
                context.get("error")
            )

        # 각 이벤트에 콜백 등록
        _WORKER_EXECUTOR.callback_handler.register_callback(
            WorkflowEventType.WORKER_RUNNING, wrapped_callback
        )
        _WORKER_EXECUTOR.callback_handler.register_callback(
            WorkflowEventType.WORKER_COMPLETED, wrapped_callback
        )
        _WORKER_EXECUTOR.callback_handler.register_callback(
            WorkflowEventType.WORKER_FAILED, wrapped_callback
        )

    logger.info("✅ 워크플로우 콜백 설정 완료")


def set_worker_output_callback(callback: Optional[Callable]) -> None:
    """
    Worker 출력 스트리밍 콜백 설정

    Args:
        callback: Worker 출력 스트리밍 함수
                  시그니처: callback(worker_name: str, chunk: str)
    """
    global _WORKER_OUTPUT_CALLBACK
    _WORKER_OUTPUT_CALLBACK = callback
    logger.info("✅ Worker 출력 스트리밍 콜백 설정 완료")


def reset_review_cycle() -> None:
    """
    Review cycle을 초기화합니다.

    새 작업 시작 시 호출하여 이전 작업의 review count가 누적되지 않도록 합니다.
    """
    global _WORKER_EXECUTOR

    if _WORKER_EXECUTOR:
        _WORKER_EXECUTOR.reset_review_cycle()
        logger.info("🔄 Review cycle has been reset")
    else:
        logger.warning("WorkerExecutor not initialized, cannot reset review cycle")


# ============================================================================
# 에러 통계 조회 (ErrorStatisticsManager 위임)
# ============================================================================

def get_error_statistics() -> Dict[str, Any]:
    """
    에러 통계 조회

    Returns:
        각 Worker의 시도/실패 통계 및 에러율
    """
    global _WORKER_EXECUTOR

    if _WORKER_EXECUTOR:
        return _WORKER_EXECUTOR.get_error_summary()

    # 폴백: WorkerExecutor가 초기화되지 않은 경우 빈 통계 반환
    logger.warning("WorkerExecutor not initialized, returning empty statistics")
    return {}


def reset_error_statistics():
    """
    에러 통계 초기화
    """
    global _WORKER_EXECUTOR

    if _WORKER_EXECUTOR:
        _WORKER_EXECUTOR.reset_error_statistics()
        logger.info("✅ 에러 통계 초기화 완료")
    else:
        logger.warning("WorkerExecutor not initialized, cannot reset statistics")


def log_error_summary():
    """
    에러 통계 요약 로그 출력
    """
    stats = get_error_statistics()
    if not stats:
        logger.info("📊 에러 통계가 없습니다.")
        return

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


# ============================================================================
# MCP Tool 함수들 (7개 Worker Tools)
# ============================================================================

@tool(
    "execute_planner_task",
    "Planner Agent에게 작업을 할당합니다. 요구사항 분석 및 계획 수립을 담당합니다.",
    {
        "task_description": {
            "type": "string",
            "description": "작업 설명"
        }
    }
)
async def execute_planner_task(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Planner Agent 실행 (재시도 로직 포함)

    Args:
        args: {"task_description": "작업 설명"}

    Returns:
        Agent 실행 결과
    """
    context = WorkerExecutionContext(
        worker_name="planner",
        task_description=args["task_description"],
        use_retry=True,
        timeout=_WORKER_TIMEOUTS["planner"],
        session_id=_CURRENT_SESSION_ID,
        metrics_collector=_METRICS_COLLECTOR,
        worker_agent=_WORKER_AGENTS.get("planner"),
        worker_output_callback=_WORKER_OUTPUT_CALLBACK
    )
    return await _WORKER_EXECUTOR.execute(context)


@tool(
    "execute_coder_task",
    "Coder Agent에게 작업을 할당합니다. 코드 작성, 수정, 리팩토링을 담당합니다.",
    {
        "task_description": {
            "type": "string",
            "description": "작업 설명"
        }
    }
)
async def execute_coder_task(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Coder Agent 실행

    Args:
        args: {"task_description": "작업 설명"}

    Returns:
        Agent 실행 결과
    """
    context = WorkerExecutionContext(
        worker_name="coder",
        task_description=args["task_description"],
        use_retry=False,
        timeout=_WORKER_TIMEOUTS["coder"],
        session_id=_CURRENT_SESSION_ID,
        metrics_collector=_METRICS_COLLECTOR,
        worker_agent=_WORKER_AGENTS.get("coder"),
        worker_output_callback=_WORKER_OUTPUT_CALLBACK
    )
    return await _WORKER_EXECUTOR.execute(context)


@tool(
    "execute_tester_task",
    "Tester Agent에게 작업을 할당합니다. 테스트 작성 및 실행을 담당합니다.",
    {
        "task_description": {
            "type": "string",
            "description": "작업 설명"
        }
    }
)
async def execute_tester_task(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tester Agent 실행

    Args:
        args: {"task_description": "작업 설명"}

    Returns:
        Agent 실행 결과
    """
    context = WorkerExecutionContext(
        worker_name="tester",
        task_description=args["task_description"],
        use_retry=False,
        timeout=_WORKER_TIMEOUTS["tester"],
        session_id=_CURRENT_SESSION_ID,
        metrics_collector=_METRICS_COLLECTOR,
        worker_agent=_WORKER_AGENTS.get("tester"),
        worker_output_callback=_WORKER_OUTPUT_CALLBACK
    )
    return await _WORKER_EXECUTOR.execute(context)


@tool(
    "execute_reviewer_task",
    "Reviewer Agent에게 작업을 할당합니다. 코드 리뷰 및 품질 검증을 담당합니다.",
    {
        "task_description": {
            "type": "string",
            "description": "리뷰 요청 내용"
        }
    }
)
async def execute_reviewer_task(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Reviewer Agent에게 작업을 할당합니다. 코드 리뷰 및 품질 검증을 담당합니다.

    Review cycle은 무한 루프 방지를 위해 최대 횟수가 제한됩니다.
    (기본값: 3회, system_config.json의 'workflow_limits.max_review_iterations'로 조정 가능)

    Args:
        args: {"task_description": "리뷰 요청 내용"}

    Returns:
        Dict[str, Any]: Agent 실행 결과
            - content: [{"type": "text", "text": "리뷰 결과"}]

    Raises:
        Exception: Review cycle이 최대치를 초과한 경우

    Note:
        - Review cycle은 Reviewer → Coder → Reviewer 패턴을 감지하여 증가합니다.
        - 최대 횟수 초과 시 자동으로 실행이 중단되며, 수동 검토가 필요합니다.
        - 새 작업 시작 시(Planner 또는 Coder 호출) Review cycle이 자동 초기화됩니다.
    """
    context = WorkerExecutionContext(
        worker_name="reviewer",
        task_description=args["task_description"],
        use_retry=False,
        timeout=_WORKER_TIMEOUTS["reviewer"],
        session_id=_CURRENT_SESSION_ID,
        metrics_collector=_METRICS_COLLECTOR,
        worker_agent=_WORKER_AGENTS.get("reviewer"),
        worker_output_callback=_WORKER_OUTPUT_CALLBACK
    )
    return await _WORKER_EXECUTOR.execute(context)


@tool(
    "execute_committer_task",
    "Committer Agent에게 작업을 할당합니다. Git 커밋 생성을 담당합니다.",
    {
        "task_description": {
            "type": "string",
            "description": "작업 설명"
        }
    }
)
async def execute_committer_task(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Committer Agent 실행 (보안 검증 포함)

    Args:
        args: {"task_description": "작업 설명"}

    Returns:
        Agent 실행 결과
    """
    # 보안 검증 수행
    is_safe, error_msg = await _WORKER_EXECUTOR.commit_validator.validate()
    if not is_safe:
        logger.warning(f"[Committer Tool] 커밋 거부 (민감 정보 감지): {error_msg}")
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"❌ 커밋 거부 (보안 검증 실패):\n\n{error_msg}"
                }
            ]
        }

    logger.info("[Committer Tool] 보안 검증 통과 - Committer Agent 실행")

    context = WorkerExecutionContext(
        worker_name="committer",
        task_description=args["task_description"],
        use_retry=False,
        timeout=_WORKER_TIMEOUTS["committer"],
        session_id=_CURRENT_SESSION_ID,
        metrics_collector=_METRICS_COLLECTOR,
        worker_agent=_WORKER_AGENTS.get("committer"),
        worker_output_callback=_WORKER_OUTPUT_CALLBACK
    )
    return await _WORKER_EXECUTOR.execute(context)


@tool(
    "execute_ideator_task",
    "Ideator Agent에게 작업을 할당합니다. 창의적 아이디어 생성 및 브레인스토밍을 담당합니다.",
    {
        "task_description": {
            "type": "string",
            "description": "작업 설명"
        }
    }
)
async def execute_ideator_task(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ideator Agent 실행 (재시도 로직 포함)

    Args:
        args: {"task_description": "작업 설명"}

    Returns:
        Agent 실행 결과
    """
    context = WorkerExecutionContext(
        worker_name="ideator",
        task_description=args["task_description"],
        use_retry=True,
        timeout=_WORKER_TIMEOUTS["ideator"],
        session_id=_CURRENT_SESSION_ID,
        metrics_collector=_METRICS_COLLECTOR,
        worker_agent=_WORKER_AGENTS.get("ideator"),
        worker_output_callback=_WORKER_OUTPUT_CALLBACK
    )
    return await _WORKER_EXECUTOR.execute(context)


@tool(
    "execute_product_manager_task",
    "Product Manager Agent에게 작업을 할당합니다. 제품 기획 및 요구사항 정의를 담당합니다.",
    {
        "task_description": {
            "type": "string",
            "description": "작업 설명"
        }
    }
)
async def execute_product_manager_task(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Product Manager Agent 실행 (재시도 로직 포함)

    Args:
        args: {"task_description": "작업 설명"}

    Returns:
        Agent 실행 결과
    """
    context = WorkerExecutionContext(
        worker_name="product_manager",
        task_description=args["task_description"],
        use_retry=True,
        timeout=_WORKER_TIMEOUTS["product_manager"],
        session_id=_CURRENT_SESSION_ID,
        metrics_collector=_METRICS_COLLECTOR,
        worker_agent=_WORKER_AGENTS.get("product_manager"),
        worker_output_callback=_WORKER_OUTPUT_CALLBACK
    )
    return await _WORKER_EXECUTOR.execute(context)


# ============================================================================
# 병렬 실행 Tool (ParallelExecutor 통합)
# ============================================================================

@tool(
    "execute_parallel_tasks",
    "병렬 작업 실행을 수행합니다. Planner가 생성한 병렬 실행 계획 JSON을 받아서 Task들을 병렬로 실행합니다.",
    {
        "plan_json": {
            "type": "string",
            "description": "Planner가 생성한 병렬 실행 계획 JSON 문자열"
        }
    }
)
async def execute_parallel_tasks(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    병렬 작업 실행 Tool

    Planner가 생성한 병렬 실행 계획 JSON을 받아서
    ParallelExecutor를 사용하여 Task들을 병렬 실행합니다.

    Args:
        args: {
            "plan_json": "Planner가 생성한 병렬 실행 계획 JSON 문자열"
        }

    Returns:
        {
            "content": [{"type": "text", "text": "실행 결과"}],
            "success": True/False,
            "metadata": {
                "completed_tasks": int,
                "failed_tasks": int,
                "total_duration": float,
                "speedup_factor": float
            }
        }
    """
    from src.domain.models.parallel_task import ParallelTask

    try:
        # ParallelExecutor 동적 생성
        # Coder Worker를 task_executor로 래핑
        async def coder_task_executor(task: ParallelTask) -> str:
            """단일 Task 실행 (Coder Worker 호출)"""
            coder_agent = _WORKER_AGENTS.get("coder")
            if not coder_agent:
                raise RuntimeError("Coder Agent를 찾을 수 없습니다")

            # Coder에게 전달할 작업 설명
            # Task description에 target_files 정보 추가
            task_description = task.description
            if task.target_files:
                task_description += f"\n\n**Target Files**: {', '.join(task.target_files)}"

            result = ""
            async for chunk in coder_agent.execute_task(task_description):
                result += chunk
                # Worker 출력 콜백 호출 (TUI 스트리밍)
                if _WORKER_OUTPUT_CALLBACK:
                    _WORKER_OUTPUT_CALLBACK("coder", chunk)

            return result

        # ParallelExecutor 인스턴스 생성
        executor = ParallelExecutor(
            task_executor=coder_task_executor,
            max_concurrent_tasks=4
        )

        # JSON 파싱 및 실행
        plan = executor.parse_plan(args["plan_json"])

        logger.info(
            f"[parallel_executor] {len(plan.tasks)}개 Task 병렬 실행 시작",
            task_ids=[task.id for task in plan.tasks]
        )

        # 병렬 실행
        execution_result = await executor.execute(plan)

        # 결과 포맷팅
        result_lines = []
        result_lines.append(f"🚀 병렬 실행 완료\n")
        result_lines.append(f"📊 실행 결과:")
        result_lines.append(f"   - 성공: {len(execution_result.completed_tasks)}개")
        result_lines.append(f"   - 실패: {len(execution_result.failed_tasks)}개")
        result_lines.append(f"   - 실행 시간: {execution_result.total_duration:.1f}초")
        result_lines.append(f"   - 속도 향상: {execution_result.speedup_factor:.2f}x")
        result_lines.append(f"   - 성공률: {execution_result.success_rate * 100:.0f}%\n")

        # 완료된 Task 상세
        if execution_result.completed_tasks:
            result_lines.append("✅ 완료된 Task:")
            for task in execution_result.completed_tasks:
                result_lines.append(f"   - [{task.id}] {task.description}")
                result_lines.append(f"     파일: {', '.join(task.target_files)}")
                if task.duration_seconds():
                    result_lines.append(f"     실행 시간: {task.duration_seconds():.1f}초")
                result_lines.append("")

        # 실패한 Task 상세
        if execution_result.failed_tasks:
            result_lines.append("❌ 실패한 Task:")
            for task in execution_result.failed_tasks:
                result_lines.append(f"   - [{task.id}] {task.description}")
                result_lines.append(f"     에러: {task.error}")
                result_lines.append("")

        # 통합 주의사항
        if plan.integration_notes:
            result_lines.append(f"📝 통합 시 주의사항:")
            result_lines.append(f"   {plan.integration_notes}\n")

        result_text = "\n".join(result_lines)

        logger.info(
            f"[parallel_executor] 병렬 실행 완료",
            completed=len(execution_result.completed_tasks),
            failed=len(execution_result.failed_tasks),
            duration=execution_result.total_duration
        )

        return {
            "content": [{"type": "text", "text": result_text}],
            "success": execution_result.all_succeeded,
            "metadata": {
                "completed_tasks": len(execution_result.completed_tasks),
                "failed_tasks": len(execution_result.failed_tasks),
                "total_duration": execution_result.total_duration,
                "speedup_factor": execution_result.speedup_factor,
                "success_rate": execution_result.success_rate
            }
        }

    except Exception as e:
        logger.error(f"[parallel_executor] 병렬 실행 실패: {e}", exc_info=True)
        return {
            "content": [{"type": "text", "text": f"❌ 병렬 실행 실패: {e}"}],
            "success": False,
            "error": str(e)
        }


# ============================================================================
# MCP 서버 생성
# ============================================================================

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
            execute_tester_task,
            execute_committer_task,
            execute_ideator_task,
            execute_product_manager_task,
            execute_parallel_tasks
        ]
    )

    logger.info("✅ Worker Tools MCP Server 생성 완료 (병렬 실행 포함)")

    return server
