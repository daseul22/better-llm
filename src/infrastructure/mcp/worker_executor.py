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
import re
import os

from src.infrastructure.mcp.review_cycle_manager import ReviewCycleManager
from src.infrastructure.mcp.commit_validator import CommitSafetyValidator
from src.infrastructure.mcp.workflow_callback_handler import (
    WorkflowCallbackHandler,
    WorkflowEventType
)
from src.infrastructure.mcp.error_statistics_manager import ErrorStatisticsManager
from src.infrastructure.mcp.context_metadata_formatter import ContextMetadataFormatter
from src.infrastructure.mcp.output_summarizer import WorkerOutputSummarizer
from src.infrastructure.logging import get_logger, log_exception_silently

logger = get_logger(__name__, component="WorkerExecutor")

# 환경변수로 Worker 출력 요약 기능 제어
ENABLE_WORKER_OUTPUT_SUMMARY = os.getenv("DISABLE_WORKER_OUTPUT_SUMMARY", "false").lower() != "true"


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
    timeout: int = 600
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
        error_manager: Optional[ErrorStatisticsManager] = None,
        metadata_formatter: Optional[ContextMetadataFormatter] = None,
        output_summarizer: Optional[WorkerOutputSummarizer] = None
    ):
        """
        WorkerExecutor 초기화

        Args:
            review_manager: Review cycle 추적 관리자 (기본값: 새 인스턴스 생성)
            commit_validator: Commit 안전성 검증기 (기본값: 새 인스턴스 생성)
            callback_handler: 워크플로우 콜백 핸들러 (기본값: 새 인스턴스 생성)
            error_manager: 에러 통계 관리자 (기본값: 새 인스턴스 생성)
            metadata_formatter: 컨텍스트 메타데이터 포맷터 (기본값: 새 인스턴스 생성)
            output_summarizer: Worker 출력 요약기 (기본값: 새 인스턴스 생성)
        """
        self.review_manager = review_manager or ReviewCycleManager()
        self.commit_validator = commit_validator or CommitSafetyValidator()
        self.callback_handler = callback_handler or WorkflowCallbackHandler()
        self.error_manager = error_manager or ErrorStatisticsManager()
        self.metadata_formatter = metadata_formatter or ContextMetadataFormatter()
        self.output_summarizer = output_summarizer or WorkerOutputSummarizer()

        # Context metadata 활성화 여부 (system_config.json에서 로드)
        self.context_metadata_enabled = self._load_context_metadata_config()

        # Worker 출력 요약 활성화 여부
        self.output_summary_enabled = ENABLE_WORKER_OUTPUT_SUMMARY

        logger.info(
            "WorkerExecutor initialized",
            context_metadata_enabled=self.context_metadata_enabled,
            output_summary_enabled=self.output_summary_enabled
        )

    def _load_context_metadata_config(self) -> bool:
        """
        system_config.json에서 context_metadata.enabled 설정 로드

        Returns:
            True: context metadata 활성화
            False: 비활성화 (기본값)
        """
        try:
            from ..config import load_system_config
            config = load_system_config()
            enabled = config.get("context_metadata", {}).get("enabled", False)
            logger.debug(
                "Context metadata config loaded",
                enabled=enabled
            )
            return enabled
        except Exception as e:
            logger.warning(
                "Failed to load context_metadata config",
                error=str(e),
                default_value=False
            )
            return False

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
        실제 Worker 실행 로직 (타임아웃 적용 + 메타데이터 추가)

        Args:
            context: 실행 컨텍스트

        Returns:
            Worker 실행 결과 (메타데이터 포함, tokens_used 포함)

        Raises:
            asyncio.TimeoutError: 타임아웃 발생 시
            Exception: Worker 실행 중 오류 발생 시
        """
        # 에러 통계: 시도 기록
        self.error_manager.record_attempt(context.worker_name)

        # 토큰 사용량 수집 (usage_callback)
        tokens_used = {
            'input_tokens': 0,
            'output_tokens': 0,
            'cache_read_tokens': 0,
            'cache_creation_tokens': 0
        }

        def usage_callback(usage_dict: Dict[str, int]):
            """토큰 사용량 콜백"""
            tokens_used['input_tokens'] += usage_dict.get('input_tokens', 0)
            tokens_used['output_tokens'] += usage_dict.get('output_tokens', 0)
            tokens_used['cache_read_tokens'] += usage_dict.get('cache_read_tokens', 0)
            tokens_used['cache_creation_tokens'] += usage_dict.get('cache_creation_tokens', 0)

        async def execute():
            result = ""
            async for chunk in context.worker_agent.execute_task(
                context.task_description,
                usage_callback=usage_callback
            ):
                result += chunk
                # Worker 출력 스트리밍 콜백 호출 (TUI용, raw 출력)
                if context.worker_output_callback:
                    try:
                        context.worker_output_callback(context.worker_name, chunk)
                    except Exception as e:
                        logger.warning(f"Worker 출력 콜백 실행 실패: {e}")

            # 원본 출력 보관
            raw_output = result

            # 1. Worker 출력 요약 (활성화된 경우)
            if self.output_summary_enabled:
                result = self._summarize_worker_output(result, context)

            # 2. Context metadata 추가 (활성화된 경우)
            if self.context_metadata_enabled:
                result = self._add_context_metadata(result, context)

            # Worker 출력 반환 (요약된 버전 + raw_output + tokens_used 보관)
            return {
                "content": [{"type": "text", "text": result}],
                "raw_output": raw_output,
                "tokens_used": tokens_used
            }

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

    def _add_context_metadata(
        self,
        worker_output: str,
        context: WorkerExecutionContext
    ) -> str:
        """
        Worker 출력에 컨텍스트 메타데이터 추가

        Args:
            worker_output: Worker의 raw 출력
            context: 실행 컨텍스트

        Returns:
            메타데이터가 추가된 출력
        """
        try:
            # Artifact 경로 생성 (존재하는 경우)
            artifact_path = None
            if context.session_id:
                from ..storage.artifact_storage import get_artifact_storage
                storage = get_artifact_storage()
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                artifact_id = f"{context.worker_name}_{timestamp}"
                artifact_path = str(storage.get_artifact_path(
                    artifact_id,
                    session_id=context.session_id
                ))

            # Dependencies 추출 (metadata에서)
            dependencies = context.metadata.get("dependencies", [])

            # 메타데이터 추가
            enhanced_output = self.metadata_formatter.format_worker_output(
                worker_name=context.worker_name,
                output=worker_output,
                artifact_path=artifact_path,
                dependencies=dependencies
            )

            logger.debug(
                "Context metadata added to worker output",
                worker_name=context.worker_name,
                has_artifact=artifact_path is not None,
                dependencies_count=len(dependencies)
            )

            return enhanced_output

        except Exception as e:
            logger.warning(
                "Failed to add context metadata",
                worker_name=context.worker_name,
                error=str(e)
            )
            # 실패 시 원본 출력 반환
            return worker_output

    def _summarize_worker_output(
        self,
        worker_output: str,
        context: WorkerExecutionContext
    ) -> str:
        """
        Worker 출력을 자동 요약

        Args:
            worker_output: Worker의 raw 출력
            context: 실행 컨텍스트

        Returns:
            요약된 출력 (artifact 경로 포함)
        """
        try:
            # Artifact 저장 (전체 로그)
            if context.session_id:
                from ..storage.artifact_storage import get_artifact_storage
                storage = get_artifact_storage()
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                artifact_id = f"{context.worker_name}_{timestamp}"

                # 전체 로그를 artifact 파일로 저장
                artifact_path = storage.save_artifact(
                    artifact_id=artifact_id,
                    content=worker_output,
                    session_id=context.session_id
                )

                # 3단계 요약 생성
                summary = self.output_summarizer.summarize(
                    worker_name=context.worker_name,
                    full_output=worker_output,
                    artifact_path=str(artifact_path)
                )

                # 요약 포맷팅
                summarized = self.output_summarizer.format_summary_output(
                    worker_name=context.worker_name,
                    summary=summary
                )

                logger.info(
                    "Worker output summarized",
                    worker_name=context.worker_name,
                    original_length=len(worker_output),
                    summary_length=len(summarized),
                    reduction_ratio=f"{(1 - len(summarized)/len(worker_output))*100:.1f}%",
                    artifact_path=str(artifact_path)
                )

                return summarized
            else:
                # 세션 ID가 없으면 요약 없이 원본 반환
                logger.debug(
                    "Session ID not found, skipping summarization",
                    worker_name=context.worker_name
                )
                return worker_output

        except Exception as e:
            logger.warning(
                "Failed to summarize worker output",
                worker_name=context.worker_name,
                error=str(e)
            )
            # 실패 시 원본 출력 반환
            return worker_output

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
                # tokens_used 추출 (result에서)
                tokens_used_dict = result.get("tokens_used", None)
                total_tokens = None
                input_tokens = None
                output_tokens = None
                cache_read_tokens = None
                cache_creation_tokens = None

                if tokens_used_dict:
                    input_tokens = tokens_used_dict.get('input_tokens', 0)
                    output_tokens = tokens_used_dict.get('output_tokens', 0)
                    cache_read_tokens = tokens_used_dict.get('cache_read_tokens', 0)
                    cache_creation_tokens = tokens_used_dict.get('cache_creation_tokens', 0)
                    total_tokens = input_tokens + output_tokens

                    logger.debug(
                        "Token usage recorded",
                        worker_name=context.worker_name,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        cache_read_tokens=cache_read_tokens,
                        cache_creation_tokens=cache_creation_tokens,
                        total_tokens=total_tokens
                    )

                context.metrics_collector.record_worker_execution(
                    session_id=context.session_id,
                    worker_name=context.worker_name,
                    task_description=context.task_description[:100],
                    start_time=start_time,
                    end_time=end_time,
                    success=success,
                    tokens_used=total_tokens,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cache_read_tokens=cache_read_tokens,
                    cache_creation_tokens=cache_creation_tokens,
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

    def _summarize_worker_output(self, worker_name: str, output: str) -> str:
        """
        Worker 출력을 요약하여 Manager에게 전달할 컨텍스트를 절약합니다.

        제거 대상:
        - 파일 읽기 결과 (Read, cat 등의 긴 출력)
        - 파일 검색 결과 상세 (Grep, Glob의 긴 리스트)
        - 긴 코드 블록 (500자 이상)
        - 디버그 로그

        유지 대상:
        - 에러 메시지
        - 최종 결론/완료 메시지
        - 핵심 결정 사항
        - 요약 섹션
        - 통계 정보

        Args:
            worker_name: Worker 이름
            output: Worker의 raw 출력

        Returns:
            요약된 출력
        """
        lines = output.split("\n")
        summarized_lines = []
        in_code_block = False
        code_block_lines = []
        skip_file_content = False
        file_read_count = 0

        for i, line in enumerate(lines):
            # 코드 블록 시작/종료 감지
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                if not in_code_block and code_block_lines:
                    # 코드 블록 종료 - 너무 길면 요약
                    if len(code_block_lines) > 20:
                        summarized_lines.append("```")
                        summarized_lines.append(f"... ({len(code_block_lines)} lines of code omitted)")
                        summarized_lines.append("```")
                    else:
                        summarized_lines.extend(code_block_lines)
                        summarized_lines.append(line)
                    code_block_lines = []
                else:
                    code_block_lines.append(line)
                continue

            if in_code_block:
                code_block_lines.append(line)
                continue

            # 파일 읽기 결과 감지 및 요약
            if re.search(r"Reading|read file|파일 읽기", line, re.IGNORECASE):
                file_read_count += 1
                summarized_lines.append(f"📄 파일 읽기 #{file_read_count}: {line.strip()[:80]}")
                skip_file_content = True
                continue

            if skip_file_content:
                # 파일 내용은 건너뛰고 다음 액션까지만 스킵
                if re.search(r"^(Writing|Editing|Running|Searching|Complete|완료|에러|Error)", line, re.IGNORECASE):
                    skip_file_content = False
                else:
                    continue

            # 파일 검색 결과 요약 (Grep, Glob)
            if re.search(r"(Found|검색|Searching|Grepping)", line, re.IGNORECASE):
                summarized_lines.append(f"🔍 {line.strip()[:100]}")
                # 다음 10줄 정도는 상세 결과이므로 스킵
                next_lines = lines[i+1:i+10]
                match_count = sum(1 for l in next_lines if l.strip() and not l.startswith("#"))
                if match_count > 5:
                    summarized_lines.append(f"   ... ({match_count}개 결과 생략)")
                continue

            # 중요 섹션 유지 (에러, 완료, 결정, 요약)
            if re.search(r"(Error|에러|Failed|실패|Warning|경고|Critical|중요)", line, re.IGNORECASE):
                summarized_lines.append(f"⚠️  {line.strip()}")
                continue

            if re.search(r"(Complete|완료|Success|성공|Done|Finished)", line, re.IGNORECASE):
                summarized_lines.append(f"✅ {line.strip()}")
                continue

            if re.search(r"(Summary|요약|Conclusion|결론|Decision|결정)", line, re.IGNORECASE):
                summarized_lines.append(f"📋 {line.strip()}")
                continue

            # 통계 정보 유지
            if re.search(r"\d+\s*(files?|개|건|줄|lines?)", line, re.IGNORECASE):
                summarized_lines.append(line.strip())
                continue

            # 빈 줄이 아니고 너무 길지 않으면 유지
            if line.strip() and len(line) < 200:
                # 디버그 로그나 반복적인 내용은 제외
                if not re.search(r"(DEBUG|TRACE|Received chunk|청크|스트리밍)", line, re.IGNORECASE):
                    summarized_lines.append(line.strip())

        # 최종 요약
        summarized = "\n".join(summarized_lines)

        # 요약 통계
        original_length = len(output)
        summarized_length = len(summarized)
        reduction_ratio = (1 - summarized_length / original_length) * 100 if original_length > 0 else 0

        # 요약이 의미 있는 경우 (30% 이상 감소)에만 적용
        if reduction_ratio >= 30:
            logger.info(
                f"[{worker_name}] 출력 요약 완료: {original_length} → {summarized_length} chars "
                f"({reduction_ratio:.1f}% 감소)"
            )
            return summarized
        else:
            # 요약 효과가 적으면 원본 반환
            logger.debug(f"[{worker_name}] 요약 효과 미미 ({reduction_ratio:.1f}%), 원본 유지")
            return output

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
