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
import asyncio

from claude_agent_sdk import tool, create_sdk_mcp_server

from ..claude import WorkerAgent
from src.domain.services import MetricsCollector
from ..config import JsonConfigLoader, get_project_root
from ..logging import get_logger
from ..storage import get_artifact_storage

# Level 1 및 Level 2 모듈 Import
from src.infrastructure.mcp.review_cycle_manager import ReviewCycleManager
from src.infrastructure.mcp.commit_validator import CommitSafetyValidator
from src.infrastructure.mcp.workflow_callback_handler import (
    WorkflowCallbackHandler,
    WorkflowEventType
)
from src.infrastructure.mcp.error_statistics_manager import ErrorStatisticsManager
from src.infrastructure.mcp.parallel_executor import ParallelExecutor
from src.infrastructure.mcp.worker_executor import WorkerExecutor, WorkerExecutionContext
from ..cache.prompt_cache import PromptCache

logger = get_logger(__name__, component="WorkerTools")


# ============================================================================
# 전역 상태 관리 (Singleton Pattern)
# ============================================================================

class WorkerToolsState:
    """
    Worker Tools의 상태를 관리하는 싱글톤 클래스

    전역 변수를 캡슐화하여 상태 관리를 일원화합니다.
    스레드 안전성을 보장하며, 테스트 시 상태 초기화가 용이합니다.

    Attributes:
        worker_agents: Worker Agent 인스턴스 딕셔너리
        worker_executor: WorkerExecutor 인스턴스
        metrics_collector: 메트릭 수집기 (선택적)
        current_session_id: 현재 세션 ID
        worker_output_callback: Worker 출력 스트리밍 콜백
        user_input_callback: 사용자 입력 콜백
        interaction_enabled: Interaction 모드 활성화 여부
        last_tool_results: Tool 실행 결과 리스트

    Example:
        >>> state = WorkerToolsState()
        >>> state.worker_agents["coder"] = WorkerAgent(config)
        >>> state.current_session_id = "session-123"
    """

    _instance: Optional["WorkerToolsState"] = None

    def __new__(cls) -> "WorkerToolsState":
        """싱글톤 인스턴스 생성"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        """상태 초기화"""
        self.worker_agents: Dict[str, WorkerAgent] = {}
        self.worker_executor: Optional[WorkerExecutor] = None
        self.metrics_collector: Optional[MetricsCollector] = None
        self.current_session_id: Optional[str] = None
        self.worker_output_callback: Optional[Callable] = None
        self.user_input_callback: Optional[Callable] = None
        self.interaction_enabled: bool = False
        self.last_tool_results: list[Dict[str, Any]] = []

    @classmethod
    def reset(cls) -> None:
        """
        싱글톤 인스턴스 초기화 (테스트용)

        Note:
            운영 환경에서는 사용하지 마세요.
            테스트 시 상태를 깨끗하게 초기화하는 용도로만 사용합니다.
        """
        if cls._instance is not None:
            cls._instance._initialize()
            logger.warning("WorkerToolsState has been reset (test only)")


# 전역 상태 인스턴스 (호환성 유지를 위한 헬퍼)
_state = WorkerToolsState()

# 하위 호환성을 위한 전역 변수 (Deprecated - 향후 제거 예정)
# 기존 코드가 전역 변수에 직접 접근하는 경우를 위해 유지
_WORKER_AGENTS: Dict[str, WorkerAgent] = _state.worker_agents
_WORKER_EXECUTOR: Optional[WorkerExecutor] = _state.worker_executor
_METRICS_COLLECTOR: Optional[MetricsCollector] = _state.metrics_collector
_CURRENT_SESSION_ID: Optional[str] = _state.current_session_id
_WORKER_OUTPUT_CALLBACK: Optional[Callable] = _state.worker_output_callback
_USER_INPUT_CALLBACK: Optional[Callable] = _state.user_input_callback
_INTERACTION_ENABLED: bool = _state.interaction_enabled
_LAST_TOOL_RESULTS: list[Dict[str, Any]] = _state.last_tool_results


# ============================================================================
# Worker Result Caching
# ============================================================================

# Planner Worker 결과 캐싱 (LRU + TTL)
# - max_size: 100 (최근 100개 요청 캐싱)
# - default_ttl: 3600 (1시간)
# - enabled: system_config.json의 performance.planner_cache_enabled로 제어 (기본: True)
_planner_cache: Optional[PromptCache] = None


# ============================================================================
# 헬퍼 함수
# ============================================================================

async def retry_with_backoff(func: Callable, worker_name: str, max_retries: int = 3) -> Any:
    """
    지수 백오프를 사용하여 함수를 재시도합니다.

    Args:
        func: 실행할 비동기 함수
        worker_name: Worker 이름 (로깅용)
        max_retries: 최대 재시도 횟수 (기본값: 3)

    Returns:
        func의 실행 결과

    Raises:
        Exception: 모든 재시도가 실패한 경우 마지막 예외를 발생

    Example:
        >>> async def my_task():
        ...     return await some_operation()
        >>> result = await retry_with_backoff(my_task, "coder", max_retries=3)
    """
    last_exception = None

    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            last_exception = e
            if attempt < max_retries - 1:
                # 지수 백오프: 2^attempt 초 (1초, 2초, 4초, ...)
                wait_time = 2 ** attempt
                logger.warning(
                    f"[{worker_name}] 실행 실패 (시도 {attempt + 1}/{max_retries}). "
                    f"{wait_time}초 후 재시도... 에러: {e}"
                )
                await asyncio.sleep(wait_time)
            else:
                logger.error(
                    f"[{worker_name}] 모든 재시도 실패 ({max_retries}번 시도)"
                )

    # 모든 재시도 실패 시 마지막 예외 발생
    raise last_exception


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
    "documenter": _get_timeout_from_env("documenter", 300),
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
        _WORKER_TIMEOUTS["documenter"] = _get_timeout_from_env(
            "documenter", timeouts.get("documenter_timeout", 300)
        )

        logger.debug(f"Worker 타임아웃 설정 로드 완료: {_WORKER_TIMEOUTS}")

    except Exception as e:
        logger.warning(f"system_config.json에서 타임아웃 로드 실패: {e}. 기본값 사용.")


def _safe_extract_result_text(result: Dict[str, Any]) -> str:
    """
    Worker 실행 결과에서 텍스트를 안전하게 추출

    IndexError, TypeError, AttributeError를 방지하는 안전한 추출 로직.

    Args:
        result: Worker 실행 결과 딕셔너리

    Returns:
        추출된 텍스트 (실패 시 빈 문자열)
    """
    try:
        content = result.get("content", [])
        if not content or len(content) == 0:
            logger.warning("Worker result content is empty")
            return ""

        first_item = content[0]

        # dict 타입 확인
        if isinstance(first_item, dict):
            return first_item.get("text", "")

        # dict-like object (hasattr 체크)
        if hasattr(first_item, 'get'):
            return first_item.get("text", "")

        # 그 외의 경우 빈 문자열
        logger.warning(f"Unexpected content item type: {type(first_item)}")
        return ""

    except Exception as e:
        logger.error(f"Failed to extract result text: {e}")
        return ""


def _load_interaction_config():
    """
    system_config.json에서 interaction 설정 로드

    환경변수가 설정되어 있으면 우선 사용,
    없으면 system_config.json 값 사용,
    기본값: false
    """
    try:
        # 환경변수 우선
        env_value = os.getenv("ENABLE_INTERACTIVE")
        if env_value is not None:
            _state.interaction_enabled = env_value.lower() in ("true", "1", "yes")
            logger.info(f"✅ Interaction 모드: {_state.interaction_enabled} (환경변수)")
            return

        # system_config.json에서 로드
        from ..config import load_system_config

        config = load_system_config()
        interaction = config.get("interaction", {})
        _state.interaction_enabled = interaction.get("enabled", False)

        logger.info(f"✅ Interaction 모드: {_state.interaction_enabled} (설정 파일)")

    except Exception as e:
        logger.warning(f"interaction 설정 로드 실패: {e}. 기본값(false) 사용.")
        _state.interaction_enabled = False


def _initialize_planner_cache():
    """
    Planner Worker 결과 캐시 초기화

    system_config.json의 performance.planner_cache_enabled로 캐싱 활성화 여부 제어
    (기본값: True)

    설정 예시:
        {
            "performance": {
                "planner_cache_enabled": true,
                "cache_max_size": 100,
                "cache_ttl_seconds": 3600
            }
        }
    """
    global _planner_cache

    try:
        from ..config import load_system_config

        config = load_system_config()
        performance = config.get("performance", {})

        # 캐시 활성화 여부 (기본: True)
        cache_enabled = performance.get("planner_cache_enabled", True)

        # 캐시 설정 (기본값: max_size=100, ttl=3600초)
        max_size = performance.get("cache_max_size", 100)
        ttl_seconds = performance.get("cache_ttl_seconds", 3600)

        # PromptCache 인스턴스 생성
        _planner_cache = PromptCache(
            max_size=max_size,
            default_ttl=ttl_seconds,
            enabled=cache_enabled
        )

        logger.info(
            "✅ Planner cache initialized",
            enabled=cache_enabled,
            max_size=max_size,
            ttl_seconds=ttl_seconds
        )

    except Exception as e:
        logger.warning(
            f"Planner cache 초기화 실패: {e}. 캐싱 비활성화.",
            exc_info=True
        )
        # 폴백: 캐싱 비활성화
        _planner_cache = PromptCache(enabled=False)


# ============================================================================
# 초기화 및 설정 함수
# ============================================================================

def initialize_workers(config_path: Path):
    """
    Worker Agent들을 초기화하고 WorkerExecutor 및 ParallelExecutor를 생성합니다.

    Args:
        config_path: Agent 설정 파일 경로
    """
    global _planner_cache

    # system_config.json에서 타임아웃 설정 로드
    _load_worker_timeouts_from_config()

    # interaction 설정 로드
    _load_interaction_config()

    # Planner 캐시 초기화
    _initialize_planner_cache()

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
        _state.worker_agents[config.name] = worker
        logger.info(
            "Worker agent initialized",
            worker_name=config.name,
            role=config.role,
            model=config.model
        )

    # WorkerExecutor 초기화 (Level 1 매니저들과 함께)
    _state.worker_executor = WorkerExecutor(
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
    _state.metrics_collector = collector
    _state.current_session_id = session_id
    logger.info("Metrics collector configured", session_id=session_id)


def update_session_id(session_id: str) -> None:
    """
    현재 세션 ID 업데이트

    Args:
        session_id: 새 세션 ID
    """
    _state.current_session_id = session_id
    logger.info("Session ID updated", session_id=session_id)


def set_workflow_callback(callback: Optional[Callable]) -> None:
    """
    워크플로우 상태 업데이트 콜백 설정

    Args:
        callback: 워크플로우 상태 업데이트 함수
                  시그니처: callback(worker_name: str, status: str, error: Optional[str])
    """
    if not _state.worker_executor:
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
        _state.worker_executor.callback_handler.register_callback(
            WorkflowEventType.WORKER_RUNNING, wrapped_callback
        )
        _state.worker_executor.callback_handler.register_callback(
            WorkflowEventType.WORKER_COMPLETED, wrapped_callback
        )
        _state.worker_executor.callback_handler.register_callback(
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
    _state.worker_output_callback = callback
    logger.info("✅ Worker 출력 스트리밍 콜백 설정 완료")


def set_user_input_callback(callback: Optional[Callable]) -> None:
    """
    사용자 입력 콜백 설정

    Args:
        callback: 사용자 입력 함수
                  시그니처: callback(question: str, options: List[str] = None) -> str
    """
    _state.user_input_callback = callback
    logger.info("✅ 사용자 입력 콜백 설정 완료")


def get_and_clear_tool_results() -> list[Dict[str, Any]]:
    """
    마지막 Manager 턴에서 실행된 Tool 결과를 조회하고 초기화

    Orchestrator가 Manager 턴 완료 후 호출하여
    Worker Tool 실행 결과를 히스토리에 추가하는 데 사용합니다.

    Returns:
        list[Dict[str, Any]]: Tool 실행 결과 리스트
            각 항목: {
                "tool_name": str,  # Tool 이름 (예: "execute_planner_task")
                "worker_name": str,  # Worker 이름 (예: "planner")
                "result": str  # Worker 실행 결과 텍스트
            }
    """
    results = _state.last_tool_results.copy()
    _state.last_tool_results.clear()

    logger.debug(
        "Tool results retrieved and cleared",
        count=len(results)
    )

    return results


def reset_review_cycle() -> None:
    """
    Review cycle을 초기화합니다.

    새 작업 시작 시 호출하여 이전 작업의 review count가 누적되지 않도록 합니다.
    """
    if _state.worker_executor:
        _state.worker_executor.reset_review_cycle()
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
    if _state.worker_executor:
        return _state.worker_executor.get_error_summary()

    # 폴백: WorkerExecutor가 초기화되지 않은 경우 빈 통계 반환
    logger.warning("WorkerExecutor not initialized, returning empty statistics")
    return {}


def reset_error_statistics():
    """
    에러 통계 초기화
    """
    if _state.worker_executor:
        _state.worker_executor.reset_error_statistics()
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
# Artifact Storage Helper
# ============================================================================

async def _save_and_summarize_output(
    worker_name: str,
    result: Dict[str, Any],
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Worker 출력을 artifact로 저장하고 요약 추출

    요약 실패 시 동일한 Worker에게 요약을 재요청합니다.

    Args:
        worker_name: Worker 이름
        result: Worker 실행 결과 (raw_output 포함)
        session_id: 세션 ID (선택적)

    Returns:
        요약이 적용된 결과
    """
    if not result.get("raw_output"):
        # raw_output이 없으면 그대로 반환
        return result

    artifact_storage = get_artifact_storage()

    # 1. 전체 출력을 artifact로 저장
    full_output = result["raw_output"]
    artifact_id = artifact_storage.save_artifact(
        worker_name=worker_name,
        full_output=full_output,
        session_id=session_id
    )

    # 2. 요약 섹션 추출 시도
    summary = artifact_storage.extract_summary(full_output)

    # 3. 요약 실패 시 Worker에게 재요청
    if summary is None:
        logger.warning(
            f"[{worker_name}] Summary extraction failed, requesting worker to summarize",
            artifact_id=artifact_id
        )

        summary = await _request_summary_from_worker(worker_name, full_output, artifact_id)

        # 재요청 결과도 실패하면 강제로 2000자로 제한 (폴백)
        if summary is None:
            # Manager의 max_output_tokens (8,000)의 25%로 제한
            # 이유: Manager 컨텍스트 윈도우 절약 및 응답 잘림 방지
            MAX_SUMMARY_SIZE = 2000  # 핵심: 컨텍스트 절약
            logger.error(
                f"[{worker_name}] Summary re-request failed, using truncated output (2,000자 제한)",
                artifact_id=artifact_id,
                full_size=len(full_output),
                truncated_size=MAX_SUMMARY_SIZE,
                reason="Manager 컨텍스트 윈도우 절약 및 응답 잘림 방지"
            )

            # 전체 출력 대신 처음 2000자만 사용 + 경고 메시지
            summary = full_output[:MAX_SUMMARY_SIZE]
            if len(full_output) > MAX_SUMMARY_SIZE:
                summary += (
                    f"\n\n⚠️ **요약 추출 실패 (출력 크기 제한)**\n"
                    f"- Worker가 요약 섹션(`## 📋 [{worker_name.upper()} 요약 - Manager 전달용]`)을 출력하지 않았습니다.\n"
                    f"- 전체 출력({len(full_output):,}자)은 artifact `{artifact_id}`에 저장되어 있습니다.\n"
                    f"- 상세 내용이 필요하면 Worker에게 artifact 파일 읽기를 지시하세요.\n"
                    f"- Worker 프롬프트를 확인하고 요약 섹션이 필수임을 명시하세요.\n"
                )

    # 4. Manager에게는 요약 + artifact_id만 전달
    summary_with_ref = f"{summary}\n\n**[전체 로그: artifact `{artifact_id}`]**"
    result_with_summary = {
        "content": [{"type": "text", "text": summary_with_ref}]
    }

    logger.info(
        f"{worker_name.capitalize()} output saved to artifact",
        artifact_id=artifact_id,
        full_size=len(full_output),
        summary_size=len(summary),
        reduction=f"{(1 - len(summary)/len(full_output))*100:.1f}%"
    )

    return result_with_summary


async def _request_summary_from_worker(
    worker_name: str,
    full_output: str,
    artifact_id: str
) -> Optional[str]:
    """
    Worker에게 출력 요약을 재요청

    Args:
        worker_name: Worker 이름
        full_output: Worker 전체 출력
        artifact_id: Artifact ID

    Returns:
        요약 텍스트 또는 None (재요청 실패)
    """
    try:
        # Worker Agent 가져오기
        worker_agent = _state.worker_agents.get(worker_name)
        if not worker_agent:
            logger.error(f"[{worker_name}] Worker agent not found for summary request")
            return None

        # 요약 요청 프롬프트 생성 (더 명확한 지시사항)
        summary_request = f"""다음은 당신이 방금 생성한 출력입니다.
하지만 "## 📋 [{worker_name.upper()} 요약 - Manager 전달용]" 섹션이 누락되었습니다.

⚠️ **긴급**: 이 요약 섹션이 없으면 시스템 전체가 지연됩니다.

아래 출력을 읽고, Manager에게 전달할 핵심 요약을 **정확히** 다음 형식으로 작성해주세요:

## 📋 [{worker_name.upper()} 요약 - Manager 전달용]
**상태**: (작업 완료/실패)
**핵심 내용**: (3-5줄 요약)
**변경 파일**: (해당 시)
**다음 단계**: (해당 시)

**중요**:
1. 위 헤더를 **정확히** 복사해서 사용하세요
2. 다른 설명, 주석, 부연 설명 **절대 포함 금지**
3. 요약만 작성하고 즉시 종료하세요

---
원본 출력 ({len(full_output)} bytes):
{full_output[:3000]}
{"..." if len(full_output) > 3000 else ""}
"""

        logger.info(
            f"[{worker_name}] Requesting summary from worker",
            artifact_id=artifact_id,
            prompt_length=len(summary_request)
        )

        # Worker에게 요약 요청 (스트리밍)
        summary_result = ""
        async for chunk in worker_agent.execute_task(summary_request):
            summary_result += chunk

        # 요약 결과에서 다시 extract_summary() 시도
        artifact_storage = get_artifact_storage()
        extracted_summary = artifact_storage.extract_summary(summary_result)

        if extracted_summary:
            logger.info(
                f"[{worker_name}] Summary re-request succeeded",
                artifact_id=artifact_id,
                summary_length=len(extracted_summary)
            )
            return extracted_summary
        else:
            logger.warning(
                f"[{worker_name}] Summary re-request failed to extract summary",
                artifact_id=artifact_id,
                response_preview=summary_result[:200]
            )
            return None

    except Exception as e:
        logger.error(
            f"[{worker_name}] Exception during summary re-request: {e}",
            artifact_id=artifact_id,
            exc_info=True
        )
        return None


# ============================================================================
# Worker Tool Factory Pattern (중복 코드 제거)
# ============================================================================

class WorkerToolFactory:
    """
    Worker Tool 실행의 공통 로직을 중앙화하는 팩토리 클래스

    Template Method Pattern을 사용하여 각 Worker Tool의 중복 코드를 제거합니다.

    책임:
        - Worker 설정 관리 (캐싱, 재시도, 타임아웃)
        - WorkerExecutionContext 생성
        - Worker 실행 및 결과 처리
        - Artifact 저장 및 요약 추출
        - Tool 결과 기록

    Example:
        >>> result = await WorkerToolFactory.execute_worker_task(
        ...     worker_name="planner",
        ...     task_description="작업 설명",
        ...     use_cache=True,
        ...     use_retry=True
        ... )
    """

    # Worker별 설정 (캐싱 활성화 여부, 재시도 정책)
    TOOL_CONFIG = {
        "planner": {"use_cache": True, "use_retry": True},
        "coder": {"use_cache": False, "use_retry": False},
        "reviewer": {"use_cache": False, "use_retry": False},
        "tester": {"use_cache": False, "use_retry": False},
        "committer": {"use_cache": False, "use_retry": False},
        "ideator": {"use_cache": False, "use_retry": True},
        "product_manager": {"use_cache": False, "use_retry": True},
        "documenter": {"use_cache": False, "use_retry": False},
    }

    @staticmethod
    async def execute_worker_task(
        worker_name: str,
        task_description: str,
        use_cache: bool = False,
        use_retry: bool = False
    ) -> Dict[str, Any]:
        """
        Worker Task 실행의 공통 로직 통합 (Template Method)

        단일 책임: 모든 Worker Tool의 공통 실행 프로세스를 중앙화

        프로세스:
            1. 캐시 확인 (Planner만)
            2. WorkerExecutionContext 생성
            3. Worker 실행
            4. Artifact 저장 및 요약 추출
            5. 캐시 저장 (Planner만)
            6. 결과 기록

        Args:
            worker_name: Worker 이름 (예: "planner", "coder")
            task_description: 작업 설명
            use_cache: 캐싱 사용 여부 (Planner만 지원)
            use_retry: 재시도 사용 여부

        Returns:
            Worker 실행 결과 (요약 포함)

        Example:
            >>> result = await WorkerToolFactory.execute_worker_task(
            ...     worker_name="planner",
            ...     task_description="새 기능 계획 수립",
            ...     use_cache=True,
            ...     use_retry=True
            ... )
        """
        # Step 1: 캐시 확인 (Planner만)
        if use_cache and worker_name == "planner":
            cache = _get_planner_cache()
            if cache:
                cached = cache.get(prompt=task_description)
                if cached:
                    logger.info(
                        f"[{worker_name}] Cache HIT - returning cached result",
                        task_preview=task_description[:100]
                    )
                    # 캐시 히트 시에도 last_tool_results에 추가 (Orchestrator 인식용)
                    _record_tool_result(worker_name, cached)
                    return cached

            logger.debug(
                f"[{worker_name}] Cache MISS - executing worker",
                task_preview=task_description[:100]
            )

        # Step 2: WorkerExecutionContext 생성
        context = _create_execution_context(worker_name, task_description, use_retry)

        # Step 3: Worker 실행 (재시도 로직은 WorkerExecutor에서 처리)
        result = await _state.worker_executor.execute(context)

        # Step 4: Artifact 저장 및 요약 추출
        result = await _save_and_summarize_output(worker_name, result, _state.current_session_id)

        # Step 5: 캐시 저장 (Planner만)
        if use_cache and worker_name == "planner":
            _cache_result(worker_name, task_description, result)

        # Step 6: 결과 기록
        _record_tool_result(worker_name, result)

        return result


def _create_execution_context(
    worker_name: str,
    task_description: str,
    use_retry: bool
) -> WorkerExecutionContext:
    """
    WorkerExecutionContext 생성 (공통 로직)

    Args:
        worker_name: Worker 이름
        task_description: 작업 설명
        use_retry: 재시도 사용 여부

    Returns:
        WorkerExecutionContext 인스턴스
    """
    return WorkerExecutionContext(
        worker_name=worker_name,
        task_description=task_description,
        use_retry=use_retry,
        timeout=_WORKER_TIMEOUTS.get(worker_name, 300),
        session_id=_state.current_session_id,
        metrics_collector=_state.metrics_collector,
        worker_agent=_state.worker_agents.get(worker_name),
        worker_output_callback=_state.worker_output_callback
    )


def _record_tool_result(worker_name: str, result: Dict[str, Any]) -> None:
    """
    Tool 결과를 last_tool_results에 기록 (공통 로직)

    Args:
        worker_name: Worker 이름
        result: Worker 실행 결과
    """
    result_text = _safe_extract_result_text(result)
    if result_text:
        _state.last_tool_results.append({
            "tool_name": f"execute_{worker_name}_task",
            "worker_name": worker_name,
            "result": result_text
        })


def _get_planner_cache() -> Optional[PromptCache]:
    """
    Planner 캐시 인스턴스 반환 (헬퍼)

    Returns:
        PromptCache 인스턴스 또는 None
    """
    global _planner_cache
    if _planner_cache and _planner_cache.enabled:
        return _planner_cache
    return None


def _cache_result(worker_name: str, task_description: str, result: Dict[str, Any]) -> None:
    """
    Worker 실행 결과를 캐시에 저장 (Planner만)

    Args:
        worker_name: Worker 이름
        task_description: 작업 설명 (캐시 키)
        result: Worker 실행 결과
    """
    cache = _get_planner_cache()
    if cache:
        cache.set(prompt=task_description, value=result)
        logger.info(
            f"[{worker_name}] Result cached",
            task_preview=task_description[:100],
            cache_size=len(cache)
        )


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
    """Planner Agent 실행 (재시도 로직 및 캐싱 포함)"""
    return await WorkerToolFactory.execute_worker_task(
        worker_name="planner",
        task_description=args["task_description"],
        **WorkerToolFactory.TOOL_CONFIG["planner"]
    )


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
    """Coder Agent 실행"""
    return await WorkerToolFactory.execute_worker_task(
        worker_name="coder",
        task_description=args["task_description"],
        **WorkerToolFactory.TOOL_CONFIG["coder"]
    )


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
    """Tester Agent 실행"""
    return await WorkerToolFactory.execute_worker_task(
        worker_name="tester",
        task_description=args["task_description"],
        **WorkerToolFactory.TOOL_CONFIG["tester"]
    )


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
    """Reviewer Agent 실행 (Review cycle 자동 관리)"""
    return await WorkerToolFactory.execute_worker_task(
        worker_name="reviewer",
        task_description=args["task_description"],
        **WorkerToolFactory.TOOL_CONFIG["reviewer"]
    )


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
    """Committer Agent 실행 (보안 검증 포함)"""
    return await WorkerToolFactory.execute_worker_task(
        worker_name="committer",
        task_description=args["task_description"],
        **WorkerToolFactory.TOOL_CONFIG["committer"]
    )


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
    """Ideator Agent 실행 (재시도 로직 포함)"""
    return await WorkerToolFactory.execute_worker_task(
        worker_name="ideator",
        task_description=args["task_description"],
        **WorkerToolFactory.TOOL_CONFIG["ideator"]
    )


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
    """Product Manager Agent 실행 (재시도 로직 포함)"""
    return await WorkerToolFactory.execute_worker_task(
        worker_name="product_manager",
        task_description=args["task_description"],
        **WorkerToolFactory.TOOL_CONFIG["product_manager"]
    )


@tool(
    "execute_documenter_task",
    "Documenter Agent에게 작업을 할당합니다. 문서 생성 및 업데이트를 담당합니다.",
    {
        "task_description": {
            "type": "string",
            "description": "작업 설명"
        }
    }
)
async def execute_documenter_task(args: Dict[str, Any]) -> Dict[str, Any]:
    """Documenter Agent 실행"""
    return await WorkerToolFactory.execute_worker_task(
        worker_name="documenter",
        task_description=args["task_description"],
        **WorkerToolFactory.TOOL_CONFIG["documenter"]
    )


# ============================================================================
# Human-in-the-Loop Tool
# ============================================================================

@tool(
    "ask_user",
    "사용자에게 질문하고 응답을 받습니다. 여러 선택지 중 하나를 선택하거나 자유 텍스트 입력을 요청할 수 있습니다. interaction.enabled가 true일 때만 사용 가능합니다.",
    {
        "question": {
            "type": "string",
            "description": "사용자에게 보여줄 질문"
        },
        "options": {
            "type": "array",
            "description": "선택지 목록 (선택적). 예: ['A안: 기존 시스템 확장', 'B안: 새로운 모듈 분리']",
            "items": {"type": "string"}
        }
    }
)
async def ask_user(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    사용자에게 질문하고 응답을 받는 Tool

    Args:
        args: {
            "question": "질문 내용",
            "options": ["선택지1", "선택지2", ...] (선택적)
        }

    Returns:
        {"content": [{"type": "text", "text": "사용자 응답"}]}
    """
    # Interaction 모드가 비활성화된 경우
    if not _state.interaction_enabled:
        logger.warning("[ask_user] Interaction 모드가 비활성화되어 있습니다.")
        return {
            "content": [{
                "type": "text",
                "text": "⚠️ Interaction 모드가 비활성화되어 있어 사용자 입력을 받을 수 없습니다.\n"
                       "system_config.json의 interaction.enabled를 true로 설정하거나 "
                       "ENABLE_INTERACTIVE=true 환경변수를 설정해주세요."
            }]
        }

    # 사용자 입력 콜백이 설정되지 않은 경우
    if not _state.user_input_callback:
        logger.error("[ask_user] 사용자 입력 콜백이 설정되지 않았습니다.")
        return {
            "content": [{
                "type": "text",
                "text": "❌ 사용자 입력 콜백이 설정되지 않았습니다.\n"
                       "CLI/TUI에서 set_user_input_callback()을 호출해주세요."
            }]
        }

    question = args.get("question", "")
    options = args.get("options")

    logger.info(f"[ask_user] 사용자에게 질문: {question}")
    if options:
        logger.info(f"[ask_user] 선택지: {options}")

    try:
        # 사용자 입력 받기 (동기 함수를 비동기로 래핑)
        import asyncio
        loop = asyncio.get_event_loop()
        user_response = await loop.run_in_executor(
            None,
            _state.user_input_callback,
            question,
            options
        )

        logger.info(f"[ask_user] 사용자 응답: {user_response}")

        return {
            "content": [{
                "type": "text",
                "text": f"✅ 사용자 응답: {user_response}"
            }]
        }

    except Exception as e:
        logger.error(f"[ask_user] 사용자 입력 받기 실패: {e}", exc_info=True)
        return {
            "content": [{
                "type": "text",
                "text": f"❌ 사용자 입력 받기 실패: {e}"
            }]
        }


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
            coder_agent = _state.worker_agents.get("coder")
            if not coder_agent:
                raise RuntimeError("Coder Agent를 찾을 수 없습니다")

            # Worker ID 동적 생성 (병렬 실행용 - 각 Task별로 고유한 Worker ID 생성)
            worker_id = f"coder_{task.id}"

            # Coder에게 전달할 작업 설명
            # Task description에 target_files 정보 추가
            task_description = task.description
            if task.target_files:
                task_description += f"\n\n**Target Files**: {', '.join(task.target_files)}"

            # Task 시작 메시지 전송 (TUI에서 볼 수 있도록)
            if _state.worker_output_callback:
                _state.worker_output_callback(
                    worker_id,
                    f"🚀 [Parallel Task {task.id}] 시작\n"
                    f"📝 설명: {task.description[:100]}...\n"
                    f"📁 파일: {', '.join(task.target_files)}\n\n"
                )

            result = ""
            async for chunk in coder_agent.execute_task(task_description):
                result += chunk
                # Worker 출력 콜백 호출 (TUI 스트리밍) - Task별 Worker ID 사용
                if _state.worker_output_callback:
                    _state.worker_output_callback(worker_id, chunk)

            # Task 완료 메시지 전송
            if _state.worker_output_callback:
                duration = task.duration_seconds() if task.end_time else 0
                _state.worker_output_callback(
                    worker_id,
                    f"\n\n✅ [Parallel Task {task.id}] 완료 (소요 시간: {duration:.1f}초)\n"
                )

            return result

        # 설정 로드
        config_loader = JsonConfigLoader(get_project_root())
        system_config = config_loader.load_system_config()
        parallel_config = system_config.get("parallel_execution", {})

        # ParallelExecutor 인스턴스 생성 (설정 기반)
        executor = ParallelExecutor(
            task_executor=coder_task_executor,
            max_concurrent_tasks=parallel_config.get("max_concurrent_tasks", 5),
            continue_on_error=parallel_config.get("continue_on_error", False)
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

        # Tool 결과 저장
        _state.last_tool_results.append({
            "tool_name": "execute_parallel_tasks",
            "worker_name": "parallel_executor",
            "result": result_text
        })

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
            execute_documenter_task,
            ask_user,
            execute_parallel_tasks
        ]
    )

    logger.info("✅ Worker Tools MCP Server 생성 완료")

    return server
