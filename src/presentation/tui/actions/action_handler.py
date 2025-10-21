"""
ActionHandler

TUI의 키보드 액션(action_*) 메서드들을 모아둔 핸들러 클래스.
OrchestratorTUI의 책임을 분리하여 코드 복잡도를 낮춥니다.

Phase 1.3: ActionHandler 분리
- 19개 action 메서드를 분리
- 예상 감소량: ~400 라인
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from textual.containers import Container, ScrollableContainer
from textual.widgets import Static, TabbedContent, TabPane
from textual.widgets import RichLog
from rich.panel import Panel
from rich.table import Table

# tui_app.py의 import 경로와 동일하게 수정
from src.infrastructure.logging import get_logger
from src.infrastructure.mcp import (
    get_error_statistics,
    set_metrics_collector,
    update_session_id,
)
from src.presentation.cli.utils import generate_session_id
from src.presentation.cli.feedback import TUIFeedbackWidget, FeedbackType
from src.presentation.tui.widgets import (
    HelpModal,
    SearchModal,
    SessionBrowserModal,
    MultilineInput,
)
from src.presentation.tui.widgets.settings_modal import SettingsModal
from src.presentation.tui.widgets.search_input import SearchHighlighter
from src.presentation.tui.utils import LogExporter, TUIConfig

if TYPE_CHECKING:
    from src.presentation.tui.tui_app import OrchestratorTUI, SessionData

logger = get_logger(__name__)


class ActionHandler:
    """
    TUI 액션 핸들러 클래스

    OrchestratorTUI의 action_* 메서드들을 분리하여 관리합니다.
    """

    def __init__(self, tui: OrchestratorTUI):
        """
        ActionHandler 초기화

        Args:
            tui: OrchestratorTUI 인스턴스 (의존성 주입)
        """
        self.tui = tui

    # ==================== 세션 관리 ====================

    async def action_new_session(self) -> None:
        """Ctrl+N: 새 세션 (현재 활성 세션을 새로 만듦)"""
        # SessionData는 tui_app.py에 정의되어 있으므로 런타임에 import
        from src.presentation.tui.tui_app import SessionData

        new_session_id = generate_session_id()
        new_session = SessionData(new_session_id)
        self.tui.sessions[self.tui.active_session_index] = new_session
        update_session_id(self.tui.session_id)
        set_metrics_collector(self.tui.metrics_collector, self.tui.session_id)

        if self.tui.manager:
            self.tui.manager.reset_token_usage()

        status_info = self.tui.query_one("#status-info", Static)
        status_info.update(f"New session • {self.tui.session_id[:8]}...")
        self.tui._update_status_bar()

        output_log = self.tui.query_one("#output-log", RichLog)
        output_log.clear()
        self.tui.log_lines.clear()

        self.tui.write_log("")
        self.tui.write_log(Panel(
            f"[bold green]새 세션 시작[/bold green]\n\nSession ID: {self.tui.session_id}",
            border_style="green"
        ))
        self.tui.write_log("")

    async def action_save_log(self) -> None:
        """Ctrl+S: 로그 저장"""
        try:
            output_log = self.tui.query_one("#output-log", RichLog)
            status_info = self.tui.query_one("#status-info", Static)

            # 로그 내보내기
            log_dir = Path(self.tui.settings.log_export_dir)
            if self.tui.settings.log_export_format == "markdown":
                filepath = LogExporter.export_to_markdown(
                    self.tui.log_lines,
                    self.tui.session_id,
                    log_dir
                )
            else:
                filepath = LogExporter.export_to_file(
                    self.tui.log_lines,
                    self.tui.session_id,
                    log_dir
                )

            if filepath:
                self.tui.write_log("")
                self.tui.write_log(Panel(
                    f"[bold green]✅ 로그 저장 완료[/bold green]\n\n"
                    f"파일: {filepath}",
                    border_style="green"
                ))
                self.tui.write_log("")
                status_info.update(f"Saved • {filepath.name}")

                # 알림 표시
                if self.tui.settings.enable_notifications:
                    self.tui.notify(f"로그 저장 완료: {filepath.name}", severity="information")
            else:
                self.tui.write_log("")
                self.tui.write_log(Panel(
                    "[bold red]❌ 로그 저장 실패[/bold red]",
                    border_style="red"
                ))
                self.tui.write_log("")

        except Exception as e:
            logger.error(f"로그 저장 실패: {e}")
            if self.tui.settings.enable_notifications and self.tui.settings.notify_on_error:
                self.tui.notify(f"로그 저장 실패: {e}", severity="error")

    async def action_show_session_browser(self) -> None:
        """Ctrl+L: 세션 브라우저 표시"""
        try:
            sessions_dir = Path("sessions")
            result = await self.tui.push_screen(SessionBrowserModal(sessions_dir))

            if result and isinstance(result, tuple):
                action, session_id = result

                if action == "load":
                    # 세션 로드
                    await self.tui.load_session(session_id)

        except Exception as e:
            logger.error(f"세션 브라우저 표시 실패: {e}")
            if self.tui.settings.enable_notifications and self.tui.settings.notify_on_error:
                self.tui.notify(f"세션 브라우저 오류: {e}", severity="error")

    async def action_switch_to_session_1(self) -> None:
        """Ctrl+1: 세션 1로 전환"""
        await self.tui.switch_to_session(0)

    async def action_switch_to_session_2(self) -> None:
        """Ctrl+2: 세션 2로 전환"""
        await self.tui.switch_to_session(1)

    async def action_switch_to_session_3(self) -> None:
        """Ctrl+3: 세션 3로 전환"""
        await self.tui.switch_to_session(2)

    # ==================== 로그 검색 ====================

    async def action_search_log(self) -> None:
        """Ctrl+F: 로그 검색"""
        try:
            result = await self.tui.push_screen(SearchModal())
            if result:
                # 검색어가 입력됨
                self.tui.search_query = result
                await self.tui.perform_search(result)
        except Exception as e:
            logger.error(f"검색 실패: {e}")

    # ==================== Worker 관리 ====================

    async def action_show_error_stats(self) -> None:
        """F6 키: 에러 통계 표시"""
        self.tui._display_error_statistics()

    async def action_next_worker_tab(self) -> None:
        """Ctrl+Tab: 다음 워커 탭으로 전환"""
        try:
            # Worker 모드가 아니거나 활성 워커가 없으면 무시
            if self.tui.output_mode != "worker" or not self.tui.active_workers:
                return

            # 현재 워커 탭 인덱스 찾기
            worker_names = list(self.tui.active_workers.keys())
            if not worker_names:
                return

            if self.tui.current_worker_tab and self.tui.current_worker_tab in worker_names:
                current_index = worker_names.index(self.tui.current_worker_tab)
                next_index = (current_index + 1) % len(worker_names)
            else:
                next_index = 0

            # 다음 워커 탭으로 전환
            next_worker = worker_names[next_index]
            self.tui.current_worker_tab = next_worker

            worker_tabs = self.tui.query_one("#worker-tabs", TabbedContent)
            worker_tabs.active = f"worker-tab-{next_worker}"

            # 알림 표시
            if self.tui.settings.enable_notifications:
                self.tui.notify(
                    f"Worker 탭: {next_worker.capitalize()}",
                    severity="information"
                )

        except Exception as e:
            logger.error(f"다음 워커 탭 전환 실패: {e}")

    async def action_prev_worker_tab(self) -> None:
        """Ctrl+Shift+Tab: 이전 워커 탭으로 전환"""
        try:
            # Worker 모드가 아니거나 활성 워커가 없으면 무시
            if self.tui.output_mode != "worker" or not self.tui.active_workers:
                return

            # 현재 워커 탭 인덱스 찾기
            worker_names = list(self.tui.active_workers.keys())
            if not worker_names:
                return

            if self.tui.current_worker_tab and self.tui.current_worker_tab in worker_names:
                current_index = worker_names.index(self.tui.current_worker_tab)
                prev_index = (current_index - 1) % len(worker_names)
            else:
                prev_index = 0

            # 이전 워커 탭으로 전환
            prev_worker = worker_names[prev_index]
            self.tui.current_worker_tab = prev_worker

            worker_tabs = self.tui.query_one("#worker-tabs", TabbedContent)
            worker_tabs.active = f"worker-tab-{prev_worker}"

            # 알림 표시
            if self.tui.settings.enable_notifications:
                self.tui.notify(
                    f"Worker 탭: {prev_worker.capitalize()}",
                    severity="information"
                )

        except Exception as e:
            logger.error(f"이전 워커 탭 전환 실패: {e}")

    # ==================== 애플리케이션 제어 ====================

    async def action_interrupt_or_quit(self) -> None:
        """Ctrl+C: 3단계 동작 - 1) 입력 초기화, 2) 작업 중단, 3) 프로세스 종료"""
        try:
            # 2초 내에 Ctrl+C를 누른 경우 카운트 증가
            current_time = time.time()
            if current_time - self.tui.last_ctrl_c_time < 2.0:
                self.tui.ctrl_c_count += 1
            else:
                self.tui.ctrl_c_count = 1

            self.tui.last_ctrl_c_time = current_time

            # 1번째 Ctrl+C: 입력 영역 텍스트 초기화
            if self.tui.ctrl_c_count == 1:
                task_input = self.tui.query_one("#task-input", MultilineInput)
                task_input.clear()
                if self.tui.settings.enable_notifications:
                    self.tui.notify(
                        "입력 초기화 완료 (Ctrl+C 한 번 더: 작업 중단)",
                        severity="information"
                    )

            # 2번째 Ctrl+C: 작업 중단
            elif self.tui.ctrl_c_count == 2:
                # 현재 작업이 실행 중이면 중단
                if self.tui.current_task and not self.tui.current_task.done():
                    self.tui.current_task.cancel()
                    self.tui.timer_active = False
                    self.tui.update_manager.update_worker_status("⚠️ 작업 중단됨")

                    status_info = self.tui.query_one("#status-info", Static)
                    status_info.update("Interrupted")

                    self.tui.write_log("")
                    self.tui.write_log("[bold yellow]⚠️ 작업이 중단되었습니다[/bold yellow]")
                    self.tui.write_log("")
                else:
                    # 실행 중인 작업이 없으면 메시지만 표시
                    if self.tui.settings.enable_notifications:
                        self.tui.notify(
                            "중단할 작업이 없습니다",
                            severity="warning"
                        )

                if self.tui.settings.enable_notifications:
                    self.tui.notify(
                        "Ctrl+C 한 번 더: 프로세스 종료",
                        severity="warning"
                    )

            # 3번째 Ctrl+C: 프로세스 종료
            elif self.tui.ctrl_c_count >= 3:
                self.tui.exit()

        except Exception as e:
            logger.error(f"Ctrl+C 처리 실패: {e}")

    # ==================== 도움말 및 설정 ====================

    async def action_show_help(self) -> None:
        """?: 도움말 표시"""
        try:
            await self.tui.push_screen(HelpModal())
        except Exception as e:
            logger.error(f"도움말 표시 실패: {e}")
            self.tui.write_log(TUIFeedbackWidget.create_panel(
                "도움말 표시 실패", FeedbackType.ERROR, details=str(e)
            ))

    async def action_show_settings(self) -> None:
        """F2: 설정 표시"""
        try:
            result = await self.tui.push_screen(SettingsModal(self.tui.settings))
            if result:
                # 설정이 변경됨
                self.tui.settings = result
                TUIConfig.save(self.tui.settings)

                # 설정 적용
                self.tui.show_metrics_panel = self.tui.settings.show_metrics_panel
                self.tui.show_workflow_panel = self.tui.settings.show_workflow_panel
                self.tui.show_worker_status = self.tui.settings.show_worker_status

                self.tui.apply_metrics_panel_visibility()
                self.tui.apply_workflow_panel_visibility()
                self.tui.apply_worker_status_visibility()

                if self.tui.settings.enable_notifications:
                    self.tui.notify("설정이 저장되었습니다", severity="information")

        except Exception as e:
            logger.error(f"설정 표시 실패: {e}")
            if self.tui.settings.enable_notifications and self.tui.settings.notify_on_error:
                self.tui.notify(f"설정 오류: {e}", severity="error")

    # ==================== 패널 토글 ====================

    async def action_toggle_metrics_panel(self) -> None:
        """Ctrl+M: 메트릭 패널 토글"""
        try:
            self.tui.show_metrics_panel = not self.tui.show_metrics_panel
            self.tui.apply_metrics_panel_visibility()

            # 설정 저장
            self.tui.settings.show_metrics_panel = self.tui.show_metrics_panel
            TUIConfig.save(self.tui.settings)

            status = "표시" if self.tui.show_metrics_panel else "숨김"
            if self.tui.settings.enable_notifications:
                self.tui.notify(f"메트릭 패널: {status}", severity="information")

        except Exception as e:
            logger.error(f"메트릭 패널 토글 실패: {e}")

    async def action_toggle_workflow_panel(self) -> None:
        """F4: 워크플로우 패널 토글"""
        try:
            self.tui.show_workflow_panel = not self.tui.show_workflow_panel
            self.tui.apply_workflow_panel_visibility()

            # 설정 저장
            self.tui.settings.show_workflow_panel = self.tui.show_workflow_panel
            TUIConfig.save(self.tui.settings)

            status = "표시" if self.tui.show_workflow_panel else "숨김"
            if self.tui.settings.enable_notifications:
                self.tui.notify(f"워크플로우 패널: {status}", severity="information")

        except Exception as e:
            logger.error(f"워크플로우 패널 토글 실패: {e}")

    async def action_toggle_worker_status(self) -> None:
        """F5: Worker 상태 패널 토글"""
        try:
            self.tui.show_worker_status = not self.tui.show_worker_status
            self.tui.apply_worker_status_visibility()

            # 설정 저장
            self.tui.settings.show_worker_status = self.tui.show_worker_status
            TUIConfig.save(self.tui.settings)

            status = "표시" if self.tui.show_worker_status else "숨김"
            if self.tui.settings.enable_notifications:
                self.tui.notify(f"Worker 상태 패널: {status}", severity="information")

        except Exception as e:
            logger.error(f"Worker 상태 패널 토글 실패: {e}")

    # ==================== 입력 히스토리 ====================

    async def action_history_up(self) -> None:
        """Up: 이전 입력 히스토리"""
        try:
            task_input = self.tui.query_one("#task-input", MultilineInput)
            previous = self.tui.input_history.get_previous()
            if previous:
                task_input.value = previous

        except Exception as e:
            logger.error(f"히스토리 이동 실패: {e}")

    async def action_history_down(self) -> None:
        """Down: 다음 입력 히스토리"""
        try:
            task_input = self.tui.query_one("#task-input", MultilineInput)
            next_item = self.tui.input_history.get_next()
            if next_item:
                task_input.value = next_item
            else:
                # 히스토리 끝에 도달하면 입력 지우기
                task_input.clear()

        except Exception as e:
            logger.error(f"히스토리 이동 실패: {e}")

    # ==================== 출력 모드 ====================

    async def action_toggle_output_mode(self) -> None:
        """Ctrl+O: Manager/Worker 출력 전환"""
        try:
            from src.presentation.tui.widgets.workflow_visualizer import WorkflowVisualizer

            # 출력 모드 전환
            if self.tui.output_mode == "manager":
                # Worker 모드로 전환
                # WorkflowVisualizer에서 실행 중인 워커 확인 (active_workers 대신)
                workflow_visualizer = self.tui.query_one("#workflow-visualizer", WorkflowVisualizer)
                has_workers = workflow_visualizer.has_running_workers() or bool(self.tui.active_workers)

                if not has_workers:
                    # 활성 Worker가 없으면 알림만 표시
                    if self.tui.settings.enable_notifications:
                        self.tui.notify(
                            "실행 중인 Worker가 없습니다",
                            severity="warning"
                        )
                    return

                self.tui.output_mode = "worker"
            else:
                # Manager 모드로 전환
                self.tui.output_mode = "manager"

            # UI 업데이트
            self.tui.apply_output_mode()

            # 알림 표시
            mode_name = "Manager 출력" if self.tui.output_mode == "manager" else "Worker 출력"
            if self.tui.settings.enable_notifications:
                self.tui.notify(f"출력 모드: {mode_name}", severity="information")

        except Exception as e:
            logger.error(f"출력 모드 전환 실패: {e}")
