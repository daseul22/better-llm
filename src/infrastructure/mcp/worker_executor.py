"""
Worker Executor - Worker 실행을 담당하는 통합 Executor

Level 1의 4개 매니저를 조합하여 복잡한 Worker 실행 로직을 단순화합니다.
- ReviewCycleManager: Review cycle 추적
- CommitSafetyValidator: Commit 안전성 검증
- WorkflowCallbackHandler: 워크플로우 콜백 관리
- ErrorStatisticsManager: 에러 통계 수집
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Callable, Optional
from datetime import datetime
import asyncio
import logging

from infrastructure.mcp.review_cycle_manager import ReviewCycleManager
from infrastructure.mcp.commit_validator import CommitSafetyValidator
from infrastructure.mcp.workflow_callback_handler import (
    WorkflowCallbackHandler,
    WorkflowEventType
)
from infrastructure.mcp.error_statistics_manager import ErrorStatisticsManager
from infrastructure.logging import get_logger, log_exception_silently

logger = get_logger(__name__, component="WorkerExecutor")


@dataclass
class WorkerExecutionContext:
    """
    Worker 실행 컨텍스트

    Worker 실행에 필요한 모든 매개변수를 담는 데이터 클래스입니다.

    Attributes:
        worker_name: Worker 이름 (예: "planner", "coder", "reviewer")
        task_description: 작업 설명
        use_retry: 재시도 로직 사용 여부
        timeout: 타임아웃 (초)
        session_id: 현재 세션 ID (메트릭 수집용)
        metrics_collector: 메트릭 수집기 (선택적)
        worker_agent: Worker Agent 인스턴스
        worker_output_callback: Worker 출력 스트리밍 콜백 (선택적)
        metadata: 추가 메타데이터

    Example:
        >>> context = WorkerExecutionContext(
        ...     worker_name="coder",
        ...     task_description="Implement feature X",
        ...     timeout=600,
        ...     worker_agent=coder_agent
        ... )
        >>> executor = WorkerExecutor()
        >>> result = await executor.execute(context)
    """
    worker_name: str
    task_description: str
    use_retry: bool = False
    timeout: int = 300
    session_id: Optional[str] = None
    metrics_collector: Optional[Any] = None
    worker_agent: Optional[Any] = None
    worker_output_callback: Optional[Callable[[str, str], None]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """
        컨텍스트를 딕셔너리로 변환 (직렬화 가능)

        Returns:
            직렬화 가능한 딕셔너리
        """
        return {
            "worker_name": self.worker_name,
            "task_description": self.task_description[:100],  # 너무 길면 잘라냄
            "use_retry": self.use_retry,
            "timeout": self.timeout,
            "session_id": self.session_id,
            "metadata": self.metadata
        }


class WorkerExecutor:
    """
    Worker 실행을 관리하는 통합 Executor

    Level 1의 4개 매니저를 조합하여 복잡한 실행 로직을 단순화합니다.
    기존 `_execute_worker_task()` 함수 (208줄, 5중 try-except)를
    구조화된 클래스로 리팩토링하여 복잡도를 낮춥니다.

    Attributes:
        review_manager: Review cycle 추적 관리자
        commit_validator: Commit 안전성 검증기
        callback_handler: 워크플로우 콜백 핸들러
        error_manager: 에러 통계 관리자

    Example:
        >>> executor = WorkerExecutor()
        >>> context = WorkerExecutionContext(
        ...     worker_name="coder",
        ...     task_description="Refactor module X",
        ...     worker_agent=coder_agent,
        ...     timeout=600
        ... )
        >>> result = await executor.execute(context)
        >>> print(result["content"][0]["text"])
    """

    def __init__(
        self,
        review_manager: Optional[ReviewCycleManager] = None,
        commit_validator: Optional[CommitSafetyValidator] = None,
        callback_handler: Optional[WorkflowCallbackHandler] = None,
        error_manager: Optional[ErrorStatisticsManager] = None
    ):
        """
        WorkerExecutor 초기화

        Args:
            review_manager: Review cycle 추적 관리자 (기본값: 새 인스턴스 생성)
            commit_validator: Commit 안전성 검증기 (기본값: 새 인스턴스 생성)
            callback_handler: 워크플로우 콜백 핸들러 (기본값: 새 인스턴스 생성)
            error_manager: 에러 통계 관리자 (기본값: 새 인스턴스 생성)
        """
        self.review_manager = review_manager or ReviewCycleManager()
        self.commit_validator = commit_validator or CommitSafetyValidator()
        self.callback_handler = callback_handler or WorkflowCallbackHandler()
        self.error_manager = error_manager or ErrorStatisticsManager()

        logger.info("WorkerExecutor initialized")

    async def execute(self, context: WorkerExecutionContext) -> Dict[str, Any]:
        """
        Worker를 실행합니다

        Args:
            context: 실행 컨텍스트

        Returns:
            실행 결과 딕셔너리:
                - content: [{"type": "text", "text": "실행 결과"}]
                - (에러 시) status: "error", error: "에러 메시지"

        Raises:
            ValueError: Worker Agent가 설정되지 않은 경우

        Example:
            >>> context = WorkerExecutionContext(
            ...     worker_name="reviewer",
            ...     task_description="Review module X",
            ...     worker_agent=reviewer_agent
            ... )
            >>> result = await executor.execute(context)
        """
        if not context.worker_agent:
            error_msg = f"❌ {context.worker_name.capitalize()} Agent를 찾을 수 없습니다."
            logger.error("Worker agent not found", worker_name=context.worker_name)
            return {
                "content": [{"type": "text", "text": error_msg}]
            }

        worker_logger = get_logger(
            __name__,
            worker_name=context.worker_name,
            component="WorkerExecution"
        )
        worker_logger.debug(
            "Task execution started",
            task_description=context.task_description[:100]
        )

        # 1. Pre-execution hooks (복잡도: 1)
        pre_exec_result = await self._pre_execute(context)
        if pre_exec_result is not None:
            # Pre-execution 실패 시 즉시 반환
            return pre_exec_result

        # 2. Execute worker (복잡도: 1)
        start_time = datetime.now()
        success = False
        error_message = None

        try:
            result = await self._execute_worker_with_timeout(context)
            success = True

        except Exception as e:
            error_message = str(e)
            result = self._handle_error(context, e, worker_logger)

        # 3. Post-execution hooks (복잡도: 1)
        await self._post_execute(context, result, start_time, success, error_message)

        return result

    async def _pre_execute(self, context: WorkerExecutionContext) -> Optional[Dict[str, Any]]:
        """
        실행 전 검증 및 준비

        Args:
            context: 실행 컨텍스트

        Returns:
            None: 검증 통과
            Dict[str, Any]: 검증 실패 시 에러 응답
        """
        # 1. Review cycle 관리 (복잡도: 1)
        review_error = self._handle_review_cycle(context)
        if review_error:
            return review_error

        # 2. Commit safety 체크 (복잡도: 1)
        if context.worker_name == "committer":
            commit_error = await self._validate_commit_safety(context)
            if commit_error:
                return commit_error

        # 3. Workflow callback 트리거 (복잡도: 1)
        self.callback_handler.trigger_worker_event(
            worker_name=context.worker_name,
            status="running",
            metadata=context.metadata
        )

        return None

    def _handle_review_cycle(self, context: WorkerExecutionContext) -> Optional[Dict[str, Any]]:
        """
        Review cycle 관리 (초기화 및 체크)

        Args:
            context: 실행 컨텍스트

        Returns:
            None: 검증 통과
            Dict[str, Any]: Review cycle 최대치 초과 시 에러 응답
        """
        # Planner는 항상 새 작업의 시작이므로 Review cycle 초기화
        if context.worker_name == "planner":
            self.review_manager.reset()
            return None

        # Coder 호출 시
        if context.worker_name == "coder":
            # Reviewer 후가 아니면 새 작업 시작으로 간주하고 초기화
            if not self.review_manager.coder_called_after_reviewer:
                self.review_manager.reset()
            # Reviewer 후 Coder 호출 표시
            self.review_manager.mark_coder_called()
            return None

        # Reviewer 호출 시 cycle count 체크
        if context.worker_name == "reviewer":
            self.review_manager.mark_reviewer_called()
            should_continue, error_msg = self.review_manager.should_continue_review()

            if not should_continue:
                logger.error(error_msg)
                self.review_manager.reset()
                return {
                    "content": [{"type": "text", "text": error_msg}]
                }

        return None

    async def _validate_commit_safety(self, context: WorkerExecutionContext) -> Optional[Dict[str, Any]]:
        """
        Commit 안전성 검증

        Args:
            context: 실행 컨텍스트

        Returns:
            None: 검증 통과
            Dict[str, Any]: 검증 실패 시 에러 응답
        """
        validation_result = await self.commit_validator.validate_all()

        if not validation_result.is_safe:
            error_msg = f"❌ 커밋 거부 (보안 검증 실패):\n\n{validation_result.error_message}"
            logger.warning(
                f"[{context.worker_name.capitalize()} Tool] 커밋 거부 (민감 정보 감지): "
                f"{validation_result.error_message}"
            )
            return {
                "content": [{"type": "text", "text": error_msg}]
            }

        logger.info(
            f"[{context.worker_name.capitalize()} Tool] 보안 검증 통과 - "
            f"{context.worker_name.capitalize()} Agent 실행"
        )

        return None

    async def _execute_worker_with_timeout(
        self,
        context: WorkerExecutionContext
    ) -> Dict[str, Any]:
        """
        실제 Worker 실행 로직 (타임아웃 적용)

        Args:
            context: 실행 컨텍스트

        Returns:
            Worker 실행 결과

        Raises:
            asyncio.TimeoutError: 타임아웃 발생 시
            Exception: Worker 실행 중 오류 발생 시
        """
        # 에러 통계: 시도 기록
        self.error_manager.record_attempt(context.worker_name)

        async def execute():
            result = ""
            async for chunk in context.worker_agent.execute_task(context.task_description):
                result += chunk
                # Worker 출력 스트리밍 콜백 호출
                if context.worker_output_callback:
                    try:
                        context.worker_output_callback(context.worker_name, chunk)
                    except Exception as e:
                        logger.warning(f"Worker 출력 콜백 실행 실패: {e}")

            return {"content": [{"type": "text", "text": result}]}

        # 재시도 로직 또는 일반 실행 (복잡도: 1)
        if context.use_retry:
            from src.infrastructure.mcp.worker_tools import retry_with_backoff
            result = await asyncio.wait_for(
                retry_with_backoff(execute, context.worker_name),
                timeout=context.timeout
            )
        else:
            result = await asyncio.wait_for(execute(), timeout=context.timeout)

        return result

    async def _post_execute(
        self,
        context: WorkerExecutionContext,
        result: Dict[str, Any],
        start_time: datetime,
        success: bool,
        error_message: Optional[str]
    ) -> None:
        """
        실행 후 처리

        Args:
            context: 실행 컨텍스트
            result: 실행 결과
            start_time: 실행 시작 시각
            success: 성공 여부
            error_message: 에러 메시지 (실패 시)
        """
        # Review cycle 완료 기록 (복잡도: 1)
        if context.worker_name == "reviewer" and success:
            # Review 결과를 파싱하여 critical issues 추출 (간단한 예시)
            reviewer_output = result.get("content", [{}])[0].get("text", "")
            critical_issues = self._extract_critical_issues(reviewer_output)

            self.review_manager.record_review_result(
                critical_issues=critical_issues,
                reviewer_output=reviewer_output[:500]  # 너무 길면 잘라냄
            )

        # 워크플로우 콜백 (복잡도: 1)
        if success:
            self.callback_handler.trigger_worker_event(
                worker_name=context.worker_name,
                status="completed",
                metadata=context.metadata
            )
        else:
            self.callback_handler.trigger_worker_event(
                worker_name=context.worker_name,
                status="failed",
                error=error_message,
                metadata=context.metadata
            )

        # 메트릭 기록 (복잡도: 1)
        if context.metrics_collector and context.session_id:
            end_time = datetime.now()
            try:
                context.metrics_collector.record_worker_execution(
                    session_id=context.session_id,
                    worker_name=context.worker_name,
                    task_description=context.task_description[:100],
                    start_time=start_time,
                    end_time=end_time,
                    success=success,
                    tokens_used=None,  # 추후 Claude SDK에서 토큰 정보 가져오면 추가
                    error_message=error_message,
                )
            except Exception as metrics_error:
                logger.warning(f"메트릭 기록 실패: {metrics_error}")

    def _handle_error(
        self,
        context: WorkerExecutionContext,
        error: Exception,
        worker_logger: logging.Logger
    ) -> Dict[str, Any]:
        """
        에러 처리

        Args:
            context: 실행 컨텍스트
            error: 발생한 예외
            worker_logger: Worker 전용 로거

        Returns:
            에러 응답 딕셔너리
        """
        # 에러 통계 기록
        self.error_manager.record_error(
            worker_name=context.worker_name,
            error=error,
            context=context.to_dict()
        )

        # 타임아웃 에러 처리 (복잡도: 1)
        if isinstance(error, asyncio.TimeoutError):
            worker_logger.error(
                "Task execution timeout",
                timeout_seconds=context.timeout,
                exc_info=True
            )

            return {
                "content": [
                    {
                        "type": "text",
                        "text": (
                            f"❌ {context.worker_name.capitalize()} 실행 타임아웃\n\n"
                            f"작업이 {context.timeout}초 내에 완료되지 않았습니다.\n"
                            f"환경변수 WORKER_TIMEOUT_{context.worker_name.upper()}를 "
                            f"조정하여 타임아웃을 늘릴 수 있습니다."
                        )
                    }
                ]
            }

        # 일반 에러 처리 (복잡도: 1)
        log_exception_silently(
            worker_logger,
            error,
            f"Worker Tool ({context.worker_name}) execution failed",
            worker_name=context.worker_name,
            task_description=context.task_description[:100]
        )

        return {
            "content": [
                {
                    "type": "text",
                    "text": (
                        f"❌ {context.worker_name.capitalize()} 실행 실패\n\n"
                        f"에러: {error}\n\n"
                        f"스택 트레이스는 에러 로그 "
                        f"(~/.better-llm/{{project}}/logs/better-llm-error.log)를 확인하세요."
                    )
                }
            ]
        }

    def _extract_critical_issues(self, reviewer_output: str) -> list[str]:
        """
        Reviewer 출력에서 중요 이슈 추출 (간단한 휴리스틱)

        Args:
            reviewer_output: Reviewer 출력 텍스트

        Returns:
            중요 이슈 목록
        """
        critical_keywords = ["critical", "error", "bug", "security", "vulnerability"]
        issues = []

        for line in reviewer_output.split("\n"):
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in critical_keywords):
                issues.append(line.strip()[:100])  # 최대 100자

        return issues[:10]  # 최대 10개

    def set_review_max_cycles(self, max_cycles: int) -> None:
        """
        Review cycle 최대 횟수 설정

        Args:
            max_cycles: 최대 Review cycle 횟수
        """
        self.review_manager.max_cycles = max_cycles
        logger.info(f"Review cycle max_cycles updated: {max_cycles}")

    def get_error_summary(self) -> Dict[str, Any]:
        """
        에러 통계 요약 조회

        Returns:
            에러 통계 요약 딕셔너리
        """
        return self.error_manager.export_to_dict()

    def reset_review_cycle(self) -> None:
        """Review cycle 초기화"""
        self.review_manager.reset()

    def reset_error_statistics(self) -> None:
        """에러 통계 초기화"""
        self.error_manager.reset_statistics()
