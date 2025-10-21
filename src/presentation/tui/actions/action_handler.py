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
from typing import TYPE_CHECKING, Optional, Dict, List, Any, Callable

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
    from src.presentation.tui.managers import (
        SessionManager,
        WorkerOutputManager,
        LayoutManager,
        MetricsUIManager,
        WorkflowUIManager,
        UpdateManager,
    )
    from src.presentation.tui.utils import TUISettings, InputHistory
    from src.infrastructure.claude import ManagerAgent

logger = get_logger(__name__)


class ActionHandler:
    """
    TUI 액션 핸들러 클래스

    OrchestratorTUI의 action_* 메서드들을 분리하여 관리합니다.

    의존성 역전 원칙(DIP)을 적용하여 TUI App 전체가 아닌
    필요한 Manager들만 참조합니다.
    """

    def __init__(
        self,
        session_manager: 'SessionManager',
        update_manager: 'UpdateManager',
        settings: 'TUISettings',
        input_history: 'InputHistory',
        manager: Optional['ManagerAgent'],
        query_one_func: Callable[..., Any],
        write_log_func: Callable[..., None],
        notify_func: Callable[..., None],
        switch_to_session_func: Callable[[int], Any],
        load_session_func: Callable[[str], Any],
        perform_search_func: Callable[[str], Any],
        push_screen_func: Callable[..., Any],
        apply_metrics_panel_visibility_func: Callable[[], None],
        apply_workflow_panel_visibility_func: Callable[[], None],
        apply_worker_status_visibility_func: Callable[[], None],
        apply_output_mode_func: Callable[[], None],
        update_status_bar_func: Callable[[], None],
        exit_func: Callable[[], None],
        display_error_statistics_func: Callable[[], None],
        invalidate_session_cache_func: Callable[[], None],  # Phase 3.3
    ) -> None:
        """
        ActionHandler 초기화

        Args:
            session_manager: SessionManager 인스턴스
            update_manager: UpdateManager 인스턴스
            settings: TUISettings 인스턴스
            input_history: InputHistory 인스턴스
            manager: ManagerAgent 인스턴스 (Optional)
            query_one_func: query_one 메서드 참조
            write_log_func: write_log 메서드 참조
            notify_func: notify 메서드 참조
            switch_to_session_func: switch_to_session 메서드 참조
            load_session_func: load_session 메서드 참조
            perform_search_func: perform_search 메서드 참조
            push_screen_func: push_screen 메서드 참조
            apply_metrics_panel_visibility_func: apply_metrics_panel_visibility 메서드 참조
            apply_workflow_panel_visibility_func: apply_workflow_panel_visibility 메서드 참조
            apply_worker_status_visibility_func: apply_worker_status_visibility 메서드 참조
            apply_output_mode_func: apply_output_mode 메서드 참조
            update_status_bar_func: _update_status_bar 메서드 참조
            exit_func: exit 메서드 참조
            display_error_statistics_func: _display_error_statistics 메서드 참조
        """
        self.session_manager = session_manager
        self.update_manager = update_manager
        self.settings = settings
        self.input_history = input_history
        self.manager = manager

        # 메서드 참조 (callable)
        self.query_one = query_one_func
        self.write_log = write_log_func
        self.notify = notify_func
        self.switch_to_session = switch_to_session_func
        self.load_session = load_session_func
        self.perform_search = perform_search_func
        self.push_screen = push_screen_func
        self.apply_metrics_panel_visibility = apply_metrics_panel_visibility_func
        self.apply_workflow_panel_visibility = apply_workflow_panel_visibility_func
        self.apply_worker_status_visibility = apply_worker_status_visibility_func
        self.apply_output_mode = apply_output_mode_func
        self.update_status_bar = update_status_bar_func
        self.exit = exit_func
        self.display_error_statistics = display_error_statistics_func
        self.invalidate_session_cache = invalidate_session_cache_func  # Phase 3.3

        # 상태 관리용 속성 (TUI App에서 가져올 값들)
        self.ctrl_c_count: int = 0
        self.last_ctrl_c_time: float = 0.0
        self.current_task: Optional[Any] = None
        self.timer_active: bool = False
        self.search_query: Optional[str] = None
        self.show_metrics_panel: bool = False
        self.show_workflow_panel: bool = False
        self.show_worker_status: bool = False
        self.output_mode: str = "manager"
        self.active_workers: Dict[str, Any] = {}
        self.current_worker_tab: Optional[str] = None
        self.log_lines: List[str] = []

    def sync_state_from_tui(
        self,
        ctrl_c_count: int,
        last_ctrl_c_time: float,
        current_task: Optional[Any],
        timer_active: bool,
        search_query: Optional[str],
        show_metrics_panel: bool,
        show_workflow_panel: bool,
        show_worker_status: bool,
        output_mode: str,
        active_workers: Dict[str, Any],
        current_worker_tab: Optional[str],
        log_lines: List[str],
    ) -> None:
        """
        TUI App의 상태를 ActionHandler로 동기화

        Args:
            ctrl_c_count: Ctrl+C 누른 횟수
            last_ctrl_c_time: 마지막 Ctrl+C 누른 시간
            current_task: 현재 실행 중인 asyncio Task
            timer_active: 타이머 활성화 여부
            search_query: 현재 검색어
            show_metrics_panel: 메트릭 패널 표시 여부
            show_workflow_panel: 워크플로우 패널 표시 여부
            show_worker_status: Worker 상태 패널 표시 여부
            output_mode: 출력 모드
            active_workers: 활성 워커 딕셔너리
            current_worker_tab: 현재 워커 탭
            log_lines: 로그 라인 리스트
        """
        self.ctrl_c_count = ctrl_c_count
        self.last_ctrl_c_time = last_ctrl_c_time
        self.current_task = current_task
        self.timer_active = timer_active
        self.search_query = search_query
        self.show_metrics_panel = show_metrics_panel
        self.show_workflow_panel = show_workflow_panel
        self.show_worker_status = show_worker_status
        self.output_mode = output_mode
        self.active_workers = active_workers
        self.current_worker_tab = current_worker_tab
        self.log_lines = log_lines

    def get_state_updates(self) -> Dict[str, Any]:
        """
        ActionHandler에서 변경된 상태를 TUI App로 반환.

        Returns:
            변경된 상태 딕셔너리
        """
        return {
            "ctrl_c_count": self.ctrl_c_count,
            "last_ctrl_c_time": self.last_ctrl_c_time,
            "current_task": self.current_task,
            "timer_active": self.timer_active,
            "search_query": self.search_query,
            "show_metrics_panel": self.show_metrics_panel,
            "show_workflow_panel": self.show_workflow_panel,
            "show_worker_status": self.show_worker_status,
            "output_mode": self.output_mode,
            "current_worker_tab": self.current_worker_tab,
        }

    # ==================== 세션 관리 ====================

    async def action_new_session(self) -> None:
        """Ctrl+N: 새 세션 (현재 활성 세션을 새로 만듦)"""
        # Phase 1 - Step 1.1: SessionManager의 캡슐화된 메서드 사용
        new_session_id = generate_session_id()

        # SessionConfig를 통해 새 세션 생성
        from src.presentation.tui.managers.session_manager import SessionConfig
        config = SessionConfig(
            session_id=new_session_id,
            user_request="New session"
        )

        # 현재 활성 인덱스의 세션을 새 세션으로 교체
        active_index = self.session_manager.get_active_session_index()

        # 기존 세션 삭제
        old_session = self.session_manager.get_session_by_index(active_index)
        self.session_manager.delete_session(old_session.session_id)

        # 새 세션 생성
        new_session_data = self.session_manager.create_session_at_index(
            active_index,
            new_session_id,
            "New session"
        )

        # 세션 전환
        self.session_manager.switch_to_session(active_index)

        # Phase 3.3: 세션 캐시 무효화 (새 세션 생성 시)
        self.invalidate_session_cache()

        # 현재 세션 ID 가져오기
        current_session = self.session_manager.get_session_by_index(active_index)
        session_id = current_session.session_id
        metrics_collector = current_session.metrics_collector

        update_session_id(session_id)
        set_metrics_collector(metrics_collector, session_id)

        if self.manager:
            self.manager.reset_token_usage()

        status_info = self.query_one("#status-info", Static)
        status_info.update(f"New session • {session_id[:8]}...")
        self.update_status_bar()

        output_log = self.query_one("#output-log", RichLog)
        output_log.clear()
        self.log_lines.clear()

        self.write_log("")
        self.write_log(Panel(
            f"[bold green]새 세션 시작[/bold green]\n\nSession ID: {session_id}",
            border_style="green"
        ))
        self.write_log("")

    async def action_save_log(self) -> None:
        """Ctrl+S: 로그 저장"""
        try:
            output_log = self.query_one("#output-log", RichLog)
            status_info = self.query_one("#status-info", Static)

            # 현재 세션 정보 가져오기
            current_session = self.session_manager.get_session_by_index(
                self.session_manager.get_active_session_index()
            )
            session_id = current_session.session_id

            # 로그 내보내기
            log_dir = Path(self.settings.log_export_dir)
            if self.settings.log_export_format == "markdown":
                filepath = LogExporter.export_to_markdown(
                    self.log_lines,
                    session_id,
                    log_dir
                )
            else:
                filepath = LogExporter.export_to_file(
                    self.log_lines,
                    session_id,
                    log_dir
                )

            if filepath:
                self.write_log("")
                self.write_log(Panel(
                    f"[bold green]✅ 로그 저장 완료[/bold green]\n\n"
                    f"파일: {filepath}",
                    border_style="green"
                ))
                self.write_log("")
                status_info.update(f"Saved • {filepath.name}")

                # 알림 표시
                if self.settings.enable_notifications:
                    self.notify(f"로그 저장 완료: {filepath.name}", severity="information")
            else:
                self.write_log("")
                self.write_log(Panel(
                    "[bold red]❌ 로그 저장 실패[/bold red]",
                    border_style="red"
                ))
                self.write_log("")

        except Exception as e:
            logger.error(f"로그 저장 실패: {e}")
            if self.settings.enable_notifications and self.settings.notify_on_error:
                self.notify(f"로그 저장 실패: {e}", severity="error")

    async def action_show_session_browser(self) -> None:
        """Ctrl+L: 세션 브라우저 표시"""
        try:
            sessions_dir = Path("sessions")
            result = await self.push_screen(SessionBrowserModal(sessions_dir))

            if result and isinstance(result, tuple):
                action, session_id = result

                if action == "load":
                    # 세션 로드
                    await self.load_session(session_id)

        except Exception as e:
            logger.error(f"세션 브라우저 표시 실패: {e}")
            if self.settings.enable_notifications and self.settings.notify_on_error:
                self.notify(f"세션 브라우저 오류: {e}", severity="error")

    async def action_switch_to_session_1(self) -> None:
        """Ctrl+1: 세션 1로 전환"""
        await self.switch_to_session(0)

    async def action_switch_to_session_2(self) -> None:
        """Ctrl+2: 세션 2로 전환"""
        await self.switch_to_session(1)

    async def action_switch_to_session_3(self) -> None:
        """Ctrl+3: 세션 3로 전환"""
        await self.switch_to_session(2)

    # ==================== 로그 검색 ====================

    async def action_search_log(self) -> None:
        """Ctrl+F: 로그 검색"""
        try:
            result = await self.push_screen(SearchModal())
            if result:
                # 검색어가 입력됨
                self.search_query = result
                await self.perform_search(result)
        except Exception as e:
            logger.error(f"검색 실패: {e}")

    # ==================== Worker 관리 ====================

    async def action_show_error_stats(self) -> None:
        """F6 키: 에러 통계 표시"""
        self.display_error_statistics()

    async def action_next_worker_tab(self) -> None:
        """Ctrl+Tab: 다음 워커 탭으로 전환"""
        try:
            # Worker 모드가 아니거나 활성 워커가 없으면 무시
            if self.output_mode != "worker" or not self.active_workers:
                return

            # 현재 워커 탭 인덱스 찾기
            worker_names = list(self.active_workers.keys())
            if not worker_names:
                return

            if self.current_worker_tab and self.current_worker_tab in worker_names:
                current_index = worker_names.index(self.current_worker_tab)
                next_index = (current_index + 1) % len(worker_names)
            else:
                next_index = 0

            # 다음 워커 탭으로 전환
            next_worker = worker_names[next_index]
            self.current_worker_tab = next_worker

            worker_tabs = self.query_one("#worker-tabs", TabbedContent)
            worker_tabs.active = f"worker-tab-{next_worker}"

            # 알림 표시
            if self.settings.enable_notifications:
                self.notify(
                    f"Worker 탭: {next_worker.capitalize()}",
                    severity="information"
                )

        except Exception as e:
            logger.error(f"다음 워커 탭 전환 실패: {e}")

    async def action_prev_worker_tab(self) -> None:
        """Ctrl+Shift+Tab: 이전 워커 탭으로 전환"""
        try:
            # Worker 모드가 아니거나 활성 워커가 없으면 무시
            if self.output_mode != "worker" or not self.active_workers:
                return

            # 현재 워커 탭 인덱스 찾기
            worker_names = list(self.active_workers.keys())
            if not worker_names:
                return

            if self.current_worker_tab and self.current_worker_tab in worker_names:
                current_index = worker_names.index(self.current_worker_tab)
                prev_index = (current_index - 1) % len(worker_names)
            else:
                prev_index = 0

            # 이전 워커 탭으로 전환
            prev_worker = worker_names[prev_index]
            self.current_worker_tab = prev_worker

            worker_tabs = self.query_one("#worker-tabs", TabbedContent)
            worker_tabs.active = f"worker-tab-{prev_worker}"

            # 알림 표시
            if self.settings.enable_notifications:
                self.notify(
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
            if current_time - self.last_ctrl_c_time < 2.0:
                self.ctrl_c_count += 1
            else:
                self.ctrl_c_count = 1

            self.last_ctrl_c_time = current_time

            # 1번째 Ctrl+C: 입력 영역 텍스트 초기화
            if self.ctrl_c_count == 1:
                task_input = self.query_one("#task-input", MultilineInput)
                task_input.clear()
                if self.settings.enable_notifications:
                    self.notify(
                        "입력 초기화 완료 (Ctrl+C 한 번 더: 작업 중단)",
                        severity="information"
                    )

            # 2번째 Ctrl+C: 작업 중단
            elif self.ctrl_c_count == 2:
                # 현재 작업이 실행 중이면 중단
                if self.current_task and not self.current_task.done():
                    self.current_task.cancel()
                    self.timer_active = False
                    self.update_manager.update_worker_status("⚠️ 작업 중단됨")

                    status_info = self.query_one("#status-info", Static)
                    status_info.update("Interrupted")

                    self.write_log("")
                    self.write_log("[bold yellow]⚠️ 작업이 중단되었습니다[/bold yellow]")
                    self.write_log("")
                else:
                    # 실행 중인 작업이 없으면 메시지만 표시
                    if self.settings.enable_notifications:
                        self.notify(
                            "중단할 작업이 없습니다",
                            severity="warning"
                        )

                if self.settings.enable_notifications:
                    self.notify(
                        "Ctrl+C 한 번 더: 프로세스 종료",
                        severity="warning"
                    )

            # 3번째 Ctrl+C: 프로세스 종료
            elif self.ctrl_c_count >= 3:
                self.exit()

        except Exception as e:
            logger.error(f"Ctrl+C 처리 실패: {e}")

    # ==================== 도움말 및 설정 ====================

    async def action_show_help(self) -> None:
        """?: 도움말 표시"""
        try:
            await self.push_screen(HelpModal())
        except Exception as e:
            logger.error(f"도움말 표시 실패: {e}")
            self.write_log(TUIFeedbackWidget.create_panel(
                "도움말 표시 실패", FeedbackType.ERROR, details=str(e)
            ))

    async def action_show_settings(self) -> None:
        """F2: 설정 표시"""
        try:
            result = await self.push_screen(SettingsModal(self.settings))
            if result:
                # 설정이 변경됨
                self.settings = result
                TUIConfig.save(self.settings)

                # 설정 적용
                self.show_metrics_panel = self.settings.show_metrics_panel
                self.show_workflow_panel = self.settings.show_workflow_panel
                self.show_worker_status = self.settings.show_worker_status

                self.apply_metrics_panel_visibility()
                self.apply_workflow_panel_visibility()
                self.apply_worker_status_visibility()

                if self.settings.enable_notifications:
                    self.notify("설정이 저장되었습니다", severity="information")

        except Exception as e:
            logger.error(f"설정 표시 실패: {e}")
            if self.settings.enable_notifications and self.settings.notify_on_error:
                self.notify(f"설정 오류: {e}", severity="error")

    # ==================== 패널 토글 ====================

    async def action_toggle_metrics_panel(self) -> None:
        """Ctrl+M: 메트릭 패널 토글"""
        try:
            self.show_metrics_panel = not self.show_metrics_panel
            self.apply_metrics_panel_visibility()

            # 설정 저장
            self.settings.show_metrics_panel = self.show_metrics_panel
            TUIConfig.save(self.settings)

            status = "표시" if self.show_metrics_panel else "숨김"
            if self.settings.enable_notifications:
                self.notify(f"메트릭 패널: {status}", severity="information")

        except Exception as e:
            logger.error(f"메트릭 패널 토글 실패: {e}")

    async def action_toggle_workflow_panel(self) -> None:
        """F4: 워크플로우 패널 토글"""
        try:
            self.show_workflow_panel = not self.show_workflow_panel
            self.apply_workflow_panel_visibility()

            # 설정 저장
            self.settings.show_workflow_panel = self.show_workflow_panel
            TUIConfig.save(self.settings)

            status = "표시" if self.show_workflow_panel else "숨김"
            if self.settings.enable_notifications:
                self.notify(f"워크플로우 패널: {status}", severity="information")

        except Exception as e:
            logger.error(f"워크플로우 패널 토글 실패: {e}")

    async def action_toggle_worker_status(self) -> None:
        """F5: Worker 상태 패널 토글"""
        try:
            self.show_worker_status = not self.show_worker_status
            self.apply_worker_status_visibility()

            # 설정 저장
            self.settings.show_worker_status = self.show_worker_status
            TUIConfig.save(self.settings)

            status = "표시" if self.show_worker_status else "숨김"
            if self.settings.enable_notifications:
                self.notify(f"Worker 상태 패널: {status}", severity="information")

        except Exception as e:
            logger.error(f"Worker 상태 패널 토글 실패: {e}")

    # ==================== 입력 히스토리 ====================

    async def action_history_up(self) -> None:
        """Up: 이전 입력 히스토리"""
        try:
            task_input = self.query_one("#task-input", MultilineInput)
            previous = self.input_history.get_previous()
            if previous:
                task_input.value = previous

        except Exception as e:
            logger.error(f"히스토리 이동 실패: {e}")

    async def action_history_down(self) -> None:
        """Down: 다음 입력 히스토리"""
        try:
            task_input = self.query_one("#task-input", MultilineInput)
            next_item = self.input_history.get_next()
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
            if self.output_mode == "manager":
                # Worker 모드로 전환
                # WorkflowVisualizer에서 실행 중인 워커 확인 (active_workers 대신)
                workflow_visualizer = self.query_one("#workflow-visualizer", WorkflowVisualizer)
                has_workers = workflow_visualizer.has_running_workers() or bool(self.active_workers)

                if not has_workers:
                    # 활성 Worker가 없으면 알림만 표시
                    if self.settings.enable_notifications:
                        self.notify(
                            "실행 중인 Worker가 없습니다",
                            severity="warning"
                        )
                    return

                self.output_mode = "worker"
            else:
                # Manager 모드로 전환
                self.output_mode = "manager"

            # UI 업데이트
            self.apply_output_mode()

            # 알림 표시
            mode_name = "Manager 출력" if self.output_mode == "manager" else "Worker 출력"
            if self.settings.enable_notifications:
                self.notify(f"출력 모드: {mode_name}", severity="information")

        except Exception as e:
            logger.error(f"출력 모드 전환 실패: {e}")
