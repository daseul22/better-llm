"""
작업 실행 담당 클래스

OrchestratorTUI의 작업 실행 관련 로직을 분리하여 단일 책임 원칙을 준수합니다.
"""

import time
import asyncio
from pathlib import Path
from typing import Tuple, Optional, TYPE_CHECKING

from src.domain.models import SessionResult
from src.domain.models.session import SessionStatus
from src.presentation.cli.utils import (
    validate_user_input,
    sanitize_user_input,
    save_session_history,
    save_metrics_report,
)
from src.presentation.cli.feedback import TUIFeedbackWidget, FeedbackType
from src.infrastructure.logging import get_logger
from src.infrastructure.mcp import get_and_clear_tool_results
from ..utils import MessageRenderer

if TYPE_CHECKING:
    from ..tui_app import OrchestratorTUI

logger = get_logger(__name__, component="TaskRunner")


class TaskRunner:
    """작업 실행을 담당하는 클래스"""

    def __init__(self, tui_app: 'OrchestratorTUI'):
        """
        TaskRunner 초기화

        Args:
            tui_app: OrchestratorTUI 인스턴스
        """
        self.tui_app = tui_app

    async def run_task(self, user_request: str) -> None:
        """
        작업 실행 - Manager가 Worker Tools를 자동으로 호출

        복잡도 감소를 위해 5개 헬퍼 함수로 책임 분리:
        1. _validate_and_prepare_input: 입력 검증 및 정제
        2. _execute_streaming_task: 스트리밍 실행
        3. _calculate_display_width: 터미널 너비 계산
        4. _handle_task_error: 에러 처리
        5. _save_and_cleanup: 세션 저장 및 정리

        Args:
            user_request: 사용자 요청 문자열

        Returns:
            None

        Raises:
            Exception: 작업 실행 중 예외 발생 시
        """
        from textual.widgets import Static
        from src.presentation.tui.widgets import MultilineInput

        task_input = self.tui_app.query_one("#task-input", MultilineInput)
        worker_status = self.tui_app.query_one("#worker-status", Static)
        status_info = self.tui_app.query_one("#status-info", Static)

        try:
            is_valid, sanitized_request = self._validate_and_prepare_input(user_request)
            if not is_valid:
                return

            task_input.clear()

            self.tui_app.write_log("")
            user_panel = MessageRenderer.render_user_message(sanitized_request)
            self.tui_app.write_log(user_panel)
            self.tui_app.write_log("")

            self.tui_app.history.add_message("user", sanitized_request)

            status_info.update("Running...")
            self.tui_app.task_start_time = time.time()
            self.tui_app.timer_active = True
            self.tui_app.update_manager.update_worker_status("🔄 Manager Agent 실행 중...")

            effective_width = self._calculate_display_width()

            manager_response, task_duration = await self._execute_streaming_task(
                effective_width
            )

            self.tui_app.timer_active = False
            # Manager 응답은 _execute_streaming_task 내에서 히스토리에 추가됨

            filepath, metrics_filepath = self._save_and_cleanup(
                sanitized_request, task_duration
            )

            completion_msg = (
                f"[bold green]✅ 완료[/bold green] [dim]({task_duration:.1f}초)[/dim]"
            )
            if metrics_filepath:
                completion_msg += (
                    f" [dim]• 세션: {filepath.name} • 메트릭: {metrics_filepath.name}[/dim]"
                )
            else:
                completion_msg += f" [dim]• 세션: {filepath.name}[/dim]"

            self.tui_app.write_log("")
            self.tui_app.write_log(completion_msg)

            if self.tui_app.settings.show_error_stats_on_complete:
                self.tui_app._display_error_statistics()
            else:
                self.tui_app.write_log("[dim]💡 Tip: F6 키로 에러 통계 확인 가능[/dim]")

            self.tui_app.write_log("")

            worker_status.update(f"✅ 완료 ({task_duration:.1f}초)")
            status_info.update(f"Completed • {filepath.name}")

        except Exception as e:
            self._handle_task_error(e)

    def _validate_and_prepare_input(self, user_request: str) -> Tuple[bool, str]:
        """
        입력 검증 및 task_name 추출

        Args:
            user_request: 사용자 입력 요청

        Returns:
            Tuple[bool, str]: (검증 성공 여부, 검증된/정제된 입력)

        Raises:
            ValueError: 입력이 None이거나 빈 문자열인 경우
        """
        from src.presentation.tui.widgets import MultilineInput

        try:
            if not user_request or not user_request.strip():
                raise ValueError("입력이 비어있습니다")

            is_valid, error_msg = validate_user_input(user_request)
            if not is_valid:
                task_input = self.tui_app.query_one("#task-input", MultilineInput)
                error_panel = TUIFeedbackWidget.create_panel(
                    "입력 검증 실패", FeedbackType.ERROR, details=error_msg
                )
                self.tui_app.write_log("")
                self.tui_app.write_log(error_panel)
                self.tui_app.write_log("")
                task_input.clear()
                return False, error_msg

            sanitized_request = sanitize_user_input(user_request)
            return True, sanitized_request

        except ValueError as e:
            logger.error(f"입력 검증 실패: {e}")
            return False, str(e)
        except Exception as e:
            logger.error(f"입력 준비 중 예외 발생: {e}")
            return False, f"입력 준비 실패: {str(e)}"

    async def _execute_streaming_task(
        self, effective_width: Optional[int]
    ) -> Tuple[str, float]:
        """
        스트리밍 실행 (astream_events)

        Args:
            effective_width: 출력 너비 (None인 경우 자동 계산)

        Returns:
            Tuple[str, float]: (Manager 응답, 실행 시간)

        Raises:
            asyncio.CancelledError: 작업이 사용자에 의해 중단된 경우
            Exception: 스트리밍 중 에러 발생 시
        """
        task_start_time = time.time()
        manager_response = ""

        try:
            self.tui_app.message_renderer.reset_state()
            self.tui_app.write_log(MessageRenderer.render_ai_response_start())
            self.tui_app.write_log("")

            async for chunk in self.tui_app.manager.analyze_and_plan_stream(
                self.tui_app.history.get_history()
            ):
                manager_response += chunk
                formatted_chunk = self.tui_app.message_renderer.render_ai_response_chunk(
                    chunk, max_width=effective_width
                )
                self.tui_app.write_log(formatted_chunk)

            self.tui_app.write_log("")
            self.tui_app.write_log(MessageRenderer.render_ai_response_end())

            # Worker Tool 실행 결과를 히스토리에 추가
            tool_results = get_and_clear_tool_results()
            for tool_result in tool_results:
                self.tui_app.history.add_message(
                    "agent",
                    tool_result["result"],
                    agent_name=tool_result["worker_name"]
                )

            # Manager 응답을 히스토리에 추가
            self.tui_app.history.add_message("manager", manager_response)

        except asyncio.CancelledError:
            self.tui_app.write_log(
                "\n[bold yellow]⚠️  작업이 사용자에 의해 중단되었습니다[/bold yellow]"
            )
            self.tui_app.timer_active = False
            self.tui_app.update_manager.update_worker_status("")
            raise

        except Exception as stream_error:
            self.tui_app.write_log(f"\n[bold red]❌ 스트리밍 에러: {stream_error}[/bold red]")
            import traceback
            self.tui_app.write_log(f"[dim]{traceback.format_exc()}[/dim]")
            self.tui_app.timer_active = False
            self.tui_app.update_manager.update_worker_status("")
            raise

        task_duration = time.time() - task_start_time
        return manager_response, task_duration

    def _calculate_display_width(self) -> Optional[int]:
        """
        터미널 너비 계산 (app.size.width 사용)

        Returns:
            Optional[int]: 유효 너비 (계산 실패 시 None)

        Raises:
            AttributeError: output_log 위젯이 존재하지 않는 경우
        """
        from textual.widgets import RichLog

        try:
            output_log_widget = self.tui_app.query_one("#output-log", RichLog)
            available_width = output_log_widget.size.width
            effective_width = max(
                available_width - MessageRenderer.OUTPUT_LOG_PADDING,
                MessageRenderer.MIN_OUTPUT_WIDTH
            )
            return effective_width
        except Exception as e:
            logger.warning(f"너비 계산 실패: {e}")
            return None

    def _handle_task_error(self, error: Exception) -> None:
        """
        에러 로깅 및 UI 업데이트

        Args:
            error: 발생한 예외 객체

        Returns:
            None

        Raises:
            Exception: UI 업데이트 중 치명적 오류 발생 시
        """
        from textual.widgets import Static

        try:
            import traceback

            worker_status = self.tui_app.query_one("#worker-status", Static)
            status_info = self.tui_app.query_one("#status-info", Static)

            error_panel = TUIFeedbackWidget.create_panel(
                "작업 실행 중 오류가 발생했습니다",
                FeedbackType.ERROR,
                details=f"{str(error)}\n\n{traceback.format_exc()}"
            )

            self.tui_app.write_log("")
            self.tui_app.write_log(error_panel)
            self.tui_app.write_log("")

            worker_status.update("❌ 오류")
            status_info.update("Error")

            logger.error(f"작업 실행 중 오류: {error}", exc_info=True)

        except Exception as ui_error:
            logger.critical(f"에러 핸들링 중 치명적 오류: {ui_error}", exc_info=True)

    def _save_and_cleanup(
        self, user_request: str, task_duration: float
    ) -> Tuple[Path, Optional[Path]]:
        """
        세션 저장 및 최종 상태 업데이트

        Args:
            user_request: 사용자 요청 문자열
            task_duration: 작업 실행 시간 (초)

        Returns:
            Tuple[Path, Optional[Path]]: (세션 파일 경로, 메트릭 파일 경로)

        Raises:
            IOError: 파일 저장 실패 시
            PermissionError: 파일 쓰기 권한 없을 시
        """
        try:
            result = SessionResult(status=SessionStatus.COMPLETED)
            # save_session_history는 기본 경로를 사용 (None 전달 시 자동 경로 사용)
            filepath = save_session_history(
                self.tui_app.session_id, user_request, self.tui_app.history,
                result.to_dict(), output_dir=None  # 기본 경로 사용: ~/.better-llm/{project-name}/sessions/
            )

            # save_metrics_report도 기본 경로를 사용
            metrics_filepath = save_metrics_report(
                self.tui_app.session_id, self.tui_app.metrics_collector, output_dir=None, format="text"
            )

            return filepath, metrics_filepath

        except Exception as e:
            logger.error(f"세션 저장 실패: {e}", exc_info=True)
            raise
