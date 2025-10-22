#!/usr/bin/env python3
"""
그룹 챗 오케스트레이션 시스템 - TUI (Claude Code 스타일)

터미널에서 Claude Code처럼 사용할 수 있는 인터랙티브 인터페이스
"""

import asyncio
import time
import logging
import os
from pathlib import Path
from typing import Optional, List, Tuple, Union, Dict, Any, Callable
from enum import Enum

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, ScrollableContainer, Horizontal
from textual.widgets import Footer, Input, Static, RichLog, Header, TabbedContent, TabPane
from textual.binding import Binding
from textual import events
from textual.css.query import NoMatches
from rich.panel import Panel
from rich.markdown import Markdown
from rich.text import Text
from rich.table import Table

from src.domain.services import ConversationHistory, ProjectContextAnalyzer, MetricsCollector
from src.infrastructure.claude import ManagerAgent
from src.infrastructure.mcp import (
    initialize_workers,
    create_worker_tools_server,
    get_error_statistics,
    set_metrics_collector,
    update_session_id,
    set_workflow_callback,
    set_worker_output_callback,
)
from src.infrastructure.config import (
    validate_environment,
    get_project_root,
    JsonConfigLoader,
    get_data_dir,
)
from src.infrastructure.storage import JsonContextRepository, InMemoryMetricsRepository
from src.infrastructure.logging import get_logger, log_exception_silently, configure_structlog
from src.presentation.cli.utils import (
    generate_session_id,
)
from src.presentation.cli.feedback import TUIFeedbackWidget, FeedbackType
from .widgets import (
    HelpModal,
    SearchModal,
    MultilineInput,
    SessionBrowserModal,
    WorkflowVisualizer,
    WorkerStatus,
)
from .widgets.settings_modal import SettingsModal
from .widgets.search_input import SearchHighlighter
from .utils import (
    InputHistory,
    LogExporter,
    AutocompleteEngine,
    TUIConfig,
    TUISettings,
    MessageRenderer,
    WorkerOutputParser,
)
from .managers import (
    # Level 1 매니저 (기존)
    SessionManager,
    WorkerOutputManager,
    LayoutManager,
    MetricsUIManager,
    WorkflowUIManager,
    # Level 2 매니저 (새로 추가)
    UIComposer,
    InitializationManager,
    UpdateManager,
    CallbackHandlers,
    LogManager,
)
from .managers.session_manager import SessionData
from .commands import SlashCommandHandler
from .runners import TaskRunner

logger = get_logger(__name__, component="TUI")


class LayoutMode(Enum):
    """레이아웃 모드 정의"""
    LARGE = "Large"  # width >= 120, height >= 30 (모든 패널 표시)
    MEDIUM = "Medium"  # width >= 80, height >= 24 (메트릭 패널 토글 가능)
    SMALL = "Small"  # width < 80 or height < 24 (메트릭 패널 자동 숨김)


class OrchestratorTUI(App):
    """전문적인 오케스트레이션 TUI 애플리케이션"""

    CSS_PATH = Path(__file__).parent / "styles.tcss"

    BINDINGS = [
        # 기본 동작
        # Enter는 MultilineInput 위젯에서 제출로 처리
        # Ctrl+R은 MultilineInput 위젯에서 줄바꿈으로 처리
        Binding("ctrl+c", "interrupt_or_quit", "중단/종료"),
        Binding("ctrl+n", "new_session", "새 세션"),
        Binding("ctrl+s", "save_log", "로그 저장"),
        Binding("ctrl+l", "show_session_browser", "세션"),

        # 검색 (한글 모드 지원)
        Binding("/", "search_log", "검색", show=False),  # 한글 모드에서 작동 안 함
        Binding("ctrl+f", "search_log", "검색"),  # Footer에 표시 (한글 모드 OK)

        # 도움말 (한글 모드 지원)
        Binding("?", "show_help", "도움말", show=False),  # 한글 모드에서 작동 안 함
        Binding("ctrl+h", "show_help", "도움말"),  # Footer에 표시 (한글 모드 OK)
        Binding("f1", "show_help", "도움말", show=False),

        # 설정
        Binding("f2", "show_settings", "설정", show=False),
        Binding("ctrl+comma", "show_settings", "설정", show=False),

        # 메트릭 (수정됨!)
        Binding("ctrl+m", "toggle_metrics_panel", "메트릭"),
        Binding("f3", "toggle_metrics_panel", "메트릭", show=False),

        # 워크플로우
        Binding("f4", "toggle_workflow_panel", "워크플로우", show=False),

        # Worker 상태
        Binding("f5", "toggle_worker_status", "Worker 상태", show=False),

        # 에러 통계
        Binding("f6", "show_error_stats", "에러 통계", show=False),

        # 히스토리
        Binding("up", "history_up", "이전 입력", show=False),
        Binding("down", "history_down", "다음 입력", show=False),

        # 출력 전환
        Binding("ctrl+o", "toggle_output_mode", "출력 전환"),

        # 워커 탭 전환
        Binding("ctrl+tab", "next_worker_tab", "다음 워커", show=False),
        Binding("ctrl+shift+tab", "prev_worker_tab", "이전 워커", show=False),

        # 세션 전환
        Binding("ctrl+1", "switch_to_session_1", "세션 1"),
        Binding("ctrl+2", "switch_to_session_2", "세션 2"),
        Binding("ctrl+3", "switch_to_session_3", "세션 3"),
    ]

    def __init__(self) -> None:
        super().__init__()
        # 멀티 세션 관리는 SessionManager가 담당 (Phase 1.4)
        # self.sessions와 self.active_session_index는 제거되고
        # self.session_manager.get_all_sessions() 및 get_active_session_index()로 대체됨

        # 현재 세션 참조 (편의를 위한 프로퍼티)
        self.manager: Optional[ManagerAgent] = None
        self.initialized: bool = False
        self.current_task: Optional[Any] = None  # 현재 실행 중인 asyncio Task
        self.task_start_time: Optional[float] = None  # 작업 시작 시간
        self.timer_active: bool = False  # 타이머 활성화 여부
        self.ctrl_c_count: int = 0  # Ctrl+C 누른 횟수
        self.last_ctrl_c_time: float = 0  # 마지막 Ctrl+C 누른 시간

        # 새로운 기능 - Phase 1~4
        self.input_history = InputHistory(max_size=100)  # 히스토리 네비게이션
        self.settings = TUIConfig.load()  # 설정 로드
        self.search_query: Optional[str] = None  # 현재 검색어
        self.show_metrics_panel: bool = self.settings.show_metrics_panel  # 메트릭 패널 표시 여부
        self.show_workflow_panel: bool = self.settings.show_workflow_panel  # 워크플로우 패널 표시 여부
        self.show_worker_status: bool = self.settings.show_worker_status  # Worker 상태 패널 표시 여부

        # 레이아웃 반응성
        self.current_layout_mode: LayoutMode = LayoutMode.LARGE
        self.terminal_width: int = 120
        self.terminal_height: int = 30
        self.metrics_panel_hidden_by_layout: bool = False  # 레이아웃에 의해 강제로 숨겨졌는지 여부

        # Phase 3.3: 프로퍼티 캐싱 (세션 관련 프로퍼티)
        self._cached_current_session: Optional[SessionData] = None
        self._cached_session_index: int = -1

        # 자동 완성 엔진
        project_root = get_project_root()
        self.autocomplete_engine = AutocompleteEngine(working_dir=project_root)

        # 출력 모드 ("manager" 또는 "worker")
        self.output_mode: str = "manager"
        self.active_workers: Dict[str, RichLog] = {}  # Worker 이름 -> RichLog 매핑
        self.current_worker_tab: Optional[str] = None  # 현재 선택된 워커 탭

        # MessageRenderer 인스턴스 (상태 유지용)
        self.message_renderer = MessageRenderer()

        # Level 1 매니저 초기화 (5개)
        self.session_manager = SessionManager()

        # 초기 세션 생성 (Phase 1.4)
        initial_session_id = generate_session_id()
        from .managers.session_manager import SessionConfig
        initial_config = SessionConfig(
            session_id=initial_session_id,
            user_request="Initial session"
        )
        self.session_manager.start_session(initial_config)

        self.worker_output_manager = WorkerOutputManager()
        self.layout_manager = LayoutManager()
        self.metrics_ui_manager = MetricsUIManager()
        self.workflow_ui_manager = WorkflowUIManager()

        # Level 2 매니저 초기화 (5개)
        self.ui_composer = UIComposer(self)
        self.log_manager = LogManager(self)
        self.initialization_manager = InitializationManager(self)
        self.update_manager = UpdateManager(self)
        self.callback_handlers = CallbackHandlers(self)

        # 슬래시 커맨드 핸들러 초기화
        self.slash_command_handler = SlashCommandHandler(
            session_manager=self.session_manager,
            query_one_func=self.query_one,
            write_log_func=self.write_log,
            action_show_help_func=self.action_show_help,
            action_toggle_metrics_panel_func=self.action_toggle_metrics_panel,
            action_search_log_func=self.action_search_log,
            perform_search_func=self.perform_search,
            load_session_func=self.load_session,
            update_status_bar_func=self._update_status_bar,
        )

        # 작업 실행 핸들러 초기화
        self.task_runner = TaskRunner(self)

        # 액션 핸들러 초기화 (Phase 1.3)
        from src.presentation.tui.actions.action_handler import ActionHandler
        self.action_handler = ActionHandler(
            session_manager=self.session_manager,
            update_manager=self.update_manager,
            settings=self.settings,
            input_history=self.input_history,
            manager=self.manager,
            query_one_func=self.query_one,
            write_log_func=self.write_log,
            notify_func=self.notify,
            switch_to_session_func=self.switch_to_session,
            load_session_func=self.load_session,
            perform_search_func=self.perform_search,
            push_screen_func=self.push_screen,
            apply_metrics_panel_visibility_func=self.apply_metrics_panel_visibility,
            apply_workflow_panel_visibility_func=self.apply_workflow_panel_visibility,
            apply_worker_status_visibility_func=self.apply_worker_status_visibility,
            apply_output_mode_func=self.apply_output_mode,
            update_status_bar_func=self._update_status_bar,
            exit_func=self.exit,
            display_error_statistics_func=self._display_error_statistics,
            invalidate_session_cache_func=self.invalidate_session_cache,  # Phase 3.3
        )

    @property
    def current_session(self) -> SessionData:
        """
        현재 활성 세션 데이터 반환 (Phase 1.4: SessionManager 위임).

        Phase 3.3: 프로퍼티 캐싱 적용 (세션 인덱스 기반).
        """
        active_index = self.session_manager.get_active_session_index()

        # 캐시가 유효한 경우 (세션 인덱스가 동일)
        if self._cached_session_index == active_index and self._cached_current_session is not None:
            return self._cached_current_session

        # 캐시 갱신
        self._cached_session_index = active_index
        self._cached_current_session = self.session_manager.get_session_by_index(active_index)
        return self._cached_current_session

    @property
    def session_id(self) -> str:
        """현재 세션 ID 반환"""
        return self.current_session.session_id

    @property
    def history(self) -> ConversationHistory:
        """현재 세션 히스토리 반환"""
        return self.current_session.history

    @property
    def log_lines(self) -> List[str]:
        """현재 세션 로그 라인 반환"""
        return self.current_session.log_lines

    @property
    def metrics_collector(self) -> MetricsCollector:
        """현재 세션 메트릭 수집기 반환"""
        return self.current_session.metrics_collector

    @property
    def start_time(self) -> float:
        """현재 세션 시작 시간 반환"""
        return self.current_session.start_time

    def invalidate_session_cache(self) -> None:
        """
        세션 캐시 무효화 (Phase 3.3).

        세션이 전환되거나 세션 데이터가 변경될 때 호출해야 합니다.
        """
        self._cached_current_session = None
        self._cached_session_index = -1

    def compose(self) -> ComposeResult:
        """UI 구성 (UIComposer로 위임)"""
        return self.ui_composer.compose()

    async def on_mount(self) -> None:
        """앱 마운트 시 초기화"""
        await self.initialization_manager.initialize_orchestrator()
        # 타이머: 0.2초마다 Worker Tool 실행 시간 업데이트
        self.set_interval(0.2, self.update_manager.update_worker_status_timer)
        # 타이머: 1초마다 메트릭 대시보드 업데이트
        self.set_interval(1.0, self.update_manager.update_metrics_panel)
        # 타이머: 1초마다 토큰 사용량 업데이트
        self.set_interval(1.0, self.update_manager.update_token_info)
        # 메트릭 패널 초기 상태 적용
        self.apply_metrics_panel_visibility()
        # 워크플로우 패널 초기 상태 적용
        self.apply_workflow_panel_visibility()
        # Worker 상태 패널 초기 상태 적용
        self.apply_worker_status_visibility()
        # 출력 모드 초기 상태 적용 (Manager 출력 표시, Worker 출력 숨김)
        self.apply_output_mode()
        # 초기 레이아웃 업데이트
        self.update_layout_for_size(self.size.width, self.size.height)
        # 자동 포커스: task-input 위젯에 포커스 설정
        task_input = self.query_one("#task-input", MultilineInput)
        task_input.focus()

    async def on_unmount(self) -> None:
        """앱 종료 시 정리 작업"""
        logger.info("TUI 앱 종료 시작")
        # 진행 중인 작업 정리
        if self.current_task and not self.current_task.done():
            logger.info("진행 중인 작업 중단")
            self.current_task.cancel()
            # 작업이 취소될 때까지 잠시 대기
            try:
                await asyncio.wait_for(self.current_task, timeout=1.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
        logger.info("TUI 앱 종료 완료")

    async def on_multiline_input_submitted(self, event: MultilineInput.Submitted) -> None:
        """Enter 입력 시 작업 실행"""
        logger.info(f"🟢 [TUI] on_multiline_input_submitted 호출됨! event.value={event.value!r}")

        if not self.initialized:
            logger.warning(f"⚠️ [TUI] 초기화되지 않음, 무시")
            return

        user_request = event.value.strip()
        if not user_request:
            logger.warning(f"⚠️ [TUI] 빈 요청, 무시")
            return

        logger.info(f"✅ [TUI] 요청 처리 시작: {user_request!r}")

        # 입력창 초기화
        task_input = self.query_one("#task-input", MultilineInput)
        task_input.clear()
        logger.info(f"🧹 [TUI] 입력창 초기화 완료")

        # 히스토리에 추가
        self.input_history.add(user_request)

        # 슬래시 커맨드 처리
        if user_request.startswith('/'):
            logger.info(f"📋 [TUI] 슬래시 커맨드 감지: {user_request}")
            await self.handle_slash_command(user_request)
            return

        # 현재 실행 중인 작업이 있으면 중단
        if self.current_task and not self.current_task.done():
            logger.info(f"⏹️ [TUI] 기존 작업 중단")
            self.current_task.cancel()
            self.timer_active = False
            self.update_manager.update_worker_status("")

        # 새 작업 시작
        logger.info(f"🚀 [TUI] 새 작업 시작: {user_request!r}")
        self.current_task = asyncio.create_task(self.task_runner.run_task(user_request))
        logger.info(f"✅ [TUI] asyncio Task 생성 완료")

    async def handle_slash_command(self, command: str) -> None:
        """슬래시 명령 처리 (SlashCommandHandler로 위임)"""
        self.slash_command_handler.sync_state_from_tui(log_lines=self.log_lines)
        await self.slash_command_handler.handle_slash_command(command)

    def _sync_action_handler_state(self) -> None:
        """ActionHandler에 TUI 상태 동기화"""
        self.action_handler.sync_state_from_tui(
            ctrl_c_count=self.ctrl_c_count,
            last_ctrl_c_time=self.last_ctrl_c_time,
            current_task=self.current_task,
            timer_active=self.timer_active,
            search_query=self.search_query,
            show_metrics_panel=self.show_metrics_panel,
            show_workflow_panel=self.show_workflow_panel,
            show_worker_status=self.show_worker_status,
            output_mode=self.output_mode,
            active_workers=self.active_workers,
            current_worker_tab=self.current_worker_tab,
            log_lines=self.log_lines,
        )

    def _apply_action_handler_state(self) -> None:
        """ActionHandler의 상태를 TUI로 반영"""
        state_updates = self.action_handler.get_state_updates()
        self.ctrl_c_count = state_updates["ctrl_c_count"]
        self.last_ctrl_c_time = state_updates["last_ctrl_c_time"]
        self.current_task = state_updates["current_task"]
        self.timer_active = state_updates["timer_active"]
        self.search_query = state_updates["search_query"]
        self.show_metrics_panel = state_updates["show_metrics_panel"]
        self.show_workflow_panel = state_updates["show_workflow_panel"]
        self.show_worker_status = state_updates["show_worker_status"]
        self.output_mode = state_updates["output_mode"]
        self.current_worker_tab = state_updates["current_worker_tab"]

    async def action_new_session(self) -> None:
        """Ctrl+N: 새 세션 (ActionHandler로 위임)"""
        self._sync_action_handler_state()
        await self.action_handler.action_new_session()
        self._apply_action_handler_state()

    def on_input_changed(self, event: Input.Changed) -> None:
        """입력 변경 이벤트 - 현재는 사용하지 않음."""
        pass

    def on_resize(self, event: events.Resize) -> None:
        """
        화면 크기 변경 이벤트 (LayoutManager로 위임).

        Args:
            event: Resize 이벤트 객체
        """
        self.layout_manager.calculate_layout((event.size.width, event.size.height))

    def update_layout_for_size(self, width: int, height: int) -> None:
        """
        레이아웃 크기 업데이트 (LayoutManager로 위임).

        Args:
            width: 터미널 너비
            height: 터미널 높이
        """
        self.layout_manager.calculate_layout((width, height))

    def _apply_layout_mode(self) -> None:
        """레이아웃 모드 적용."""
        # LayoutManager.calculate_layout이 이미 레이아웃을 적용하므로 추가 작업 불필요
        pass

    def _update_status_bar(self) -> None:
        """
        상태바에 세션 탭 및 레이아웃 모드 표시

        형식: "[1*] [2] [3] • {session_id} • Layout: {mode} ({width}x{height})"
        """
        try:
            session_info = self.query_one("#session-info", Static)

            # 세션 탭 표시: [1*] [2] [3] (Phase 1.4: SessionManager 사용)
            session_tabs = []
            session_count = self.session_manager.get_session_count()
            active_index = self.session_manager.get_active_session_index()
            for i in range(3):
                if i < session_count:
                    # 세션이 존재하면
                    if i == active_index:
                        session_tabs.append(f"[bold cyan][{i + 1}*][/bold cyan]")
                    else:
                        session_tabs.append(f"[dim][{i + 1}][/dim]")
                else:
                    # 세션이 없으면
                    session_tabs.append(f"[dim][{i + 1}][/dim]")

            session_tabs_str = " ".join(session_tabs)

            session_info.update(
                f"{session_tabs_str} • "
                f"ID: {self.session_id[:8]}... • "
                f"Layout: {self.current_layout_mode.value} ({self.terminal_width}x{self.terminal_height})"
            )
        except Exception as e:
            logger.warning(f"상태바 업데이트 실패: {e}")

    def apply_metrics_panel_visibility(self) -> None:
        """메트릭 패널 표시/숨김 상태 적용"""
        try:
            metrics_container = self.query_one("#metrics-container", Container)
            if self.show_metrics_panel:
                metrics_container.remove_class("hidden")
            else:
                metrics_container.add_class("hidden")
        except NoMatches:
            # 위젯이 아직 마운트되지 않은 경우 (정상적인 초기화 과정)
            logger.debug("Metrics container not yet mounted, skipping visibility update")
        except Exception as e:
            # 예상치 못한 에러
            logger.error(f"Failed to apply metrics panel visibility: {e}", exc_info=True)

    def apply_workflow_panel_visibility(self) -> None:
        """워크플로우 패널 표시/숨김 상태 적용"""
        try:
            workflow_container = self.query_one("#workflow-container", Container)
            if self.show_workflow_panel:
                workflow_container.remove_class("hidden")
            else:
                workflow_container.add_class("hidden")
        except NoMatches:
            # 위젯이 아직 마운트되지 않은 경우 (정상적인 초기화 과정)
            logger.debug("Workflow container not yet mounted, skipping visibility update")
        except Exception as e:
            # 예상치 못한 에러
            logger.error(f"Failed to apply workflow panel visibility: {e}", exc_info=True)

    def apply_worker_status_visibility(self) -> None:
        """Worker 상태 패널 표시/숨김 상태 적용 (Worker 상태 컨테이너 제거됨)"""
        # Worker 상태 컨테이너가 제거되었으므로 이 메서드는 더 이상 필요하지 않음
        pass

    def on_workflow_update(self, worker_name: str, status: str, error: Optional[str] = None) -> None:
        """
        워크플로우 상태 업데이트 콜백 (CallbackHandlers로 위임).

        Args:
            worker_name: Worker 이름
            status: 상태 문자열
            error: 에러 메시지 (선택적)
        """
        self.callback_handlers.on_workflow_update(worker_name, status, error)

    def on_worker_output(self, worker_name: str, chunk: str) -> None:
        """
        Worker 출력 콜백 (CallbackHandlers로 위임).

        Args:
            worker_name: Worker 이름
            chunk: 출력 청크
        """
        self.callback_handlers.on_worker_output(worker_name, chunk)

    def apply_output_mode(self) -> None:
        """
        현재 출력 모드에 따라 출력 화면 표시/숨김 적용
        """
        try:
            output_container = self.query_one("#output-container", ScrollableContainer)
            worker_output_container = self.query_one("#worker-output-container", Container)

            if self.output_mode == "manager":
                # Manager 출력 표시, Worker 출력 숨김
                output_container.remove_class("hidden")
                worker_output_container.add_class("hidden")
            else:
                # Worker 출력 표시, Manager 출력 숨김
                output_container.add_class("hidden")
                worker_output_container.remove_class("hidden")

        except Exception as e:
            logger.warning(f"출력 모드 적용 실패: {e}")

    async def action_save_log(self) -> None:
        """Ctrl+S: 로그 저장 (ActionHandler로 위임)"""
        self._sync_action_handler_state()
        await self.action_handler.action_save_log()
        self._apply_action_handler_state()

    async def action_show_session_browser(self) -> None:
        """Ctrl+L: 세션 브라우저 표시 (ActionHandler로 위임)"""
        self._sync_action_handler_state()
        await self.action_handler.action_show_session_browser()
        self._apply_action_handler_state()

    async def action_search_log(self) -> None:
        """Ctrl+F: 로그 검색 (ActionHandler로 위임)"""
        self._sync_action_handler_state()
        await self.action_handler.action_search_log()
        self._apply_action_handler_state()

    async def perform_search(self, query: str) -> None:
        """
        로그 검색 수행

        Args:
            query: 검색어
        """
        try:
            output_log = self.query_one("#output-log", RichLog)

            # 검색 결과 찾기
            results = SearchHighlighter.search_in_lines(self.log_lines, query)

            self.write_log("")
            if results:
                self.write_log(Panel(
                    f"[bold cyan]🔍 검색 결과: '{query}'[/bold cyan]\n\n"
                    f"총 {len(results)}개 결과 발견",
                    border_style="cyan"
                ))
                self.write_log("")

                # 상위 10개 결과 표시
                for i, (line_num, line) in enumerate(results[:10]):
                    # 하이라이트된 텍스트 생성
                    highlighted = SearchHighlighter.highlight_text(line, query)
                    self.write_log(f"[dim]Line {line_num + 1}:[/dim] ")
                    self.write_log(highlighted)

                if len(results) > 10:
                    self.write_log("")
                    self.write_log(f"[dim]...그 외 {len(results) - 10}개 결과[/dim]")

            else:
                self.write_log(Panel(
                    f"[bold yellow]⚠️  검색 결과 없음: '{query}'[/bold yellow]",
                    border_style="yellow"
                ))

            self.write_log("")

        except Exception as e:
            logger.error(f"검색 수행 실패: {e}")

    async def load_session(self, session_id: str) -> None:
        """
        이전 세션 불러오기 (Phase 3.1)

        Args:
            session_id: 불러올 세션 ID
        """
        try:
            output_log = self.query_one("#output-log", RichLog)
            status_info = self.query_one("#status-info", Static)

            self.write_log("")
            self.write_log(Panel(
                f"[bold cyan]🔄 세션 불러오는 중...[/bold cyan]\n\n"
                f"Session ID: {session_id}",
                border_style="cyan"
            ))
            self.write_log("")

            # 세션 파일 찾기 (새 경로 시스템 사용)
            sessions_dir = get_data_dir("sessions")
            session_files = list(sessions_dir.glob(f"session_{session_id}_*.json"))

            if not session_files:
                # 피드백 시스템 사용
                error_panel = TUIFeedbackWidget.create_panel(
                    "세션을 찾을 수 없습니다",
                    FeedbackType.ERROR,
                    details=f"Session ID: {session_id}"
                )
                self.write_log("")
                self.write_log(error_panel)
                self.write_log("")
                return

            # 가장 최근 파일 선택
            session_file = max(session_files, key=lambda p: p.stat().st_mtime)

            # 세션 데이터 로드
            import json
            with open(session_file, "r", encoding="utf-8") as f:
                session_data = json.load(f)

            # Phase 1 - Step 1.2: 중앙화된 팩토리 메서드 사용
            initial_messages = session_data.get("history", [])
            loaded_session = self.session_manager.create_session_data(
                session_id=session_id,
                user_request="Loaded session",
                initial_messages=initial_messages
            )

            # 현재 세션 교체
            active_index = self.session_manager.get_active_session_index()
            self.session_manager.update_session_at_index(active_index, loaded_session)

            # Phase 3.3: 세션 캐시 무효화 (세션 데이터 변경 시)
            self.invalidate_session_cache()

            # 세션 ID 업데이트
            update_session_id(session_id)
            set_metrics_collector(self.metrics_collector, self.session_id)

            # Manager Agent 토큰 사용량 초기화
            if self.manager:
                self.manager.reset_token_usage()

            # UI 업데이트
            self._update_status_bar()  # 터미널 크기 및 레이아웃 모드 포함

            self.write_log(Panel(
                f"[bold green]✅ 세션 불러오기 완료[/bold green]\n\n"
                f"Session ID: {session_id}\n"
                f"메시지 수: {len(session_data.get('history', []))}",
                border_style="green"
            ))
            self.write_log("")

            status_info.update("Ready")

        except Exception as e:
            # 피드백 시스템 사용
            error_panel = TUIFeedbackWidget.create_panel(
                "세션 불러오기 실패",
                FeedbackType.ERROR,
                details=str(e)
            )
            self.write_log("")
            self.write_log(error_panel)
            self.write_log("")
            logger.error(f"세션 불러오기 실패: {e}")

    def write_log(
        self, content: Union[str, Panel, Text], widget_id: str = "output-log"
    ) -> None:
        """로그 출력 및 추적 (LogManager로 위임)."""
        self.log_manager.write_log(content, widget_id)

    def _display_error_statistics(self) -> None:
        """에러 통계를 로그에 표시"""
        try:
            error_stats = get_error_statistics()
            if not error_stats:
                self.write_log("[dim]에러 통계가 없습니다[/dim]")
                return

            stats_table = Table(show_header=True, header_style="bold cyan", border_style="dim", box=None)
            stats_table.add_column("Worker", style="cyan", width=12)
            stats_table.add_column("시도", justify="right", width=6)
            stats_table.add_column("성공", justify="right", width=6, style="green")
            stats_table.add_column("실패", justify="right", width=6, style="red")
            stats_table.add_column("에러율", justify="right", width=8)

            for worker_name, data in error_stats.items():
                error_rate_style = "red" if data['error_rate'] > 20 else "yellow" if data['error_rate'] > 0 else "green"
                stats_table.add_row(
                    worker_name.upper(),
                    str(data['attempts']),
                    str(data['successes']),
                    str(data['failures']),
                    f"[{error_rate_style}]{data['error_rate']}%[/{error_rate_style}]"
                )

            self.write_log("")
            self.write_log("[bold cyan]📊 에러 통계[/bold cyan]")
            self.write_log(stats_table)

        except Exception as e:
            logger.error(f"에러 통계 표시 실패: {e}")

    async def action_show_error_stats(self) -> None:
        """F6 키: 에러 통계 표시 (ActionHandler로 위임)"""
        self._sync_action_handler_state()
        await self.action_handler.action_show_error_stats()
        self._apply_action_handler_state()

    async def action_next_worker_tab(self) -> None:
        """Ctrl+Tab: 다음 워커 탭으로 전환 (ActionHandler로 위임)"""
        self._sync_action_handler_state()
        await self.action_handler.action_next_worker_tab()
        self._apply_action_handler_state()

    async def action_prev_worker_tab(self) -> None:
        """Ctrl+Shift+Tab: 이전 워커 탭으로 전환 (ActionHandler로 위임)"""
        self._sync_action_handler_state()
        await self.action_handler.action_prev_worker_tab()
        self._apply_action_handler_state()

    async def action_switch_to_session_1(self) -> None:
        """Ctrl+1: 세션 1로 전환 (ActionHandler로 위임)"""
        self._sync_action_handler_state()
        await self.action_handler.action_switch_to_session_1()
        self._apply_action_handler_state()

    async def action_switch_to_session_2(self) -> None:
        """Ctrl+2: 세션 2로 전환 (ActionHandler로 위임)"""
        self._sync_action_handler_state()
        await self.action_handler.action_switch_to_session_2()
        self._apply_action_handler_state()

    async def action_switch_to_session_3(self) -> None:
        """Ctrl+3: 세션 3로 전환 (ActionHandler로 위임)"""
        self._sync_action_handler_state()
        await self.action_handler.action_switch_to_session_3()
        self._apply_action_handler_state()

    def _ensure_session_exists(self, index: int) -> None:
        """
        세션이 존재하지 않으면 생성.

        Args:
            index: 세션 인덱스 (0, 1, 2)
        """
        while self.session_manager.get_session_count() <= index:
            new_session_id = generate_session_id()
            new_index = self.session_manager.get_session_count()
            self.session_manager.create_session_at_index(new_index, new_session_id)

    def _is_already_active_session(self, index: int) -> bool:
        """
        이미 활성 세션인지 확인.

        Args:
            index: 세션 인덱스 (0, 1, 2)

        Returns:
            이미 활성 세션이면 True, 아니면 False
        """
        active_index = self.session_manager.get_active_session_index()
        return active_index == index

    def _switch_session_in_manager(self, index: int) -> None:
        """
        SessionManager를 통해 세션 전환.

        Args:
            index: 세션 인덱스 (0, 1, 2)
        """
        self.session_manager.switch_to_session(index)

    def _restore_session_ui(self) -> None:
        """세션 UI 복원 (로그, 메트릭, 상태바 등)."""
        # Phase 3.3: 세션 캐시 무효화 (세션 전환 시)
        self.invalidate_session_cache()

        # UI 업데이트: 로그 교체
        output_log = self.query_one("#output-log", RichLog)
        output_log.clear()

        # 현재 세션 로그 복원
        for log_line in self.current_session.log_lines:
            output_log.write(log_line)

        # 메트릭 수집기 업데이트
        set_metrics_collector(self.current_session.metrics_collector, self.session_id)
        update_session_id(self.session_id)

        # Manager Agent 토큰 사용량 초기화 (세션별로 독립적)
        if self.manager:
            self.manager.reset_token_usage()

        # 상태바 업데이트
        self._update_status_bar()

    def _notify_session_switch_success(self, index: int) -> None:
        """
        세션 전환 성공 알림.

        Args:
            index: 세션 인덱스 (0, 1, 2)
        """
        if self.settings.enable_notifications:
            self.notify(
                f"세션 {index + 1}로 전환 (ID: {self.session_id[:8]}...)",
                severity="information"
            )

    def _notify_already_active_session(self, index: int) -> None:
        """
        이미 활성 세션임을 알림.

        Args:
            index: 세션 인덱스 (0, 1, 2)
        """
        if self.settings.enable_notifications:
            self.notify(f"이미 세션 {index + 1}입니다", severity="information")

    def _handle_session_switch_error(self, error: Exception) -> None:
        """
        세션 전환 에러 처리.

        Args:
            error: 발생한 예외
        """
        logger.error(f"세션 전환 실패: {error}")
        if self.settings.enable_notifications and self.settings.notify_on_error:
            self.notify(f"세션 전환 실패: {error}", severity="error")

    async def switch_to_session(self, index: int) -> None:
        """
        세션 전환 (0, 1, 2)

        Args:
            index: 세션 인덱스 (0=Ctrl+1, 1=Ctrl+2, 2=Ctrl+3)
        """
        try:
            # 세션이 아직 없으면 생성
            self._ensure_session_exists(index)

            # 이미 현재 세션이면 무시
            if self._is_already_active_session(index):
                self._notify_already_active_session(index)
                return

            # 세션 전환
            self._switch_session_in_manager(index)

            # UI 업데이트
            self._restore_session_ui()

            # 알림 표시
            self._notify_session_switch_success(index)

        except Exception as e:
            self._handle_session_switch_error(e)

    async def action_interrupt_or_quit(self) -> None:
        """Ctrl+C: 작업 중단 또는 종료 (ActionHandler로 위임)"""
        self._sync_action_handler_state()
        await self.action_handler.action_interrupt_or_quit()
        self._apply_action_handler_state()

    async def action_show_help(self) -> None:
        """?: 도움말 표시 (ActionHandler로 위임)"""
        self._sync_action_handler_state()
        await self.action_handler.action_show_help()
        self._apply_action_handler_state()

    async def action_show_settings(self) -> None:
        """F2: 설정 표시 (ActionHandler로 위임)"""
        self._sync_action_handler_state()
        await self.action_handler.action_show_settings()
        self._apply_action_handler_state()

    async def action_toggle_metrics_panel(self) -> None:
        """Ctrl+M: 메트릭 패널 토글 (ActionHandler로 위임)"""
        self._sync_action_handler_state()
        await self.action_handler.action_toggle_metrics_panel()
        self._apply_action_handler_state()

    async def action_toggle_workflow_panel(self) -> None:
        """F4: 워크플로우 패널 토글 (ActionHandler로 위임)"""
        self._sync_action_handler_state()
        await self.action_handler.action_toggle_workflow_panel()
        self._apply_action_handler_state()

    async def action_toggle_worker_status(self) -> None:
        """F5: Worker 상태 패널 토글 (ActionHandler로 위임)"""
        self._sync_action_handler_state()
        await self.action_handler.action_toggle_worker_status()
        self._apply_action_handler_state()

    async def action_history_up(self) -> None:
        """Up: 이전 입력 히스토리 (ActionHandler로 위임)"""
        self._sync_action_handler_state()
        await self.action_handler.action_history_up()
        self._apply_action_handler_state()

    async def action_history_down(self) -> None:
        """Down: 다음 입력 히스토리 (ActionHandler로 위임)"""
        self._sync_action_handler_state()
        await self.action_handler.action_history_down()
        self._apply_action_handler_state()

    async def action_toggle_output_mode(self) -> None:
        """Ctrl+O: Manager/Worker 출력 전환 (ActionHandler로 위임)"""
        self._sync_action_handler_state()
        await self.action_handler.action_toggle_output_mode()
        self._apply_action_handler_state()


def main() -> None:
    """메인 함수."""
    # 환경변수에서 로깅 설정 로드
    log_level = os.getenv("LOG_LEVEL", "INFO")
    log_format = os.getenv("LOG_FORMAT", "json")
    # LOG_DIR 환경변수가 설정되지 않으면 None (기본 경로 사용: ~/.better-llm/{project-name}/logs)
    log_dir = os.getenv("LOG_DIR")

    # structlog 초기화
    configure_structlog(
        log_dir=log_dir,
        log_level=log_level,
        enable_json=(log_format == "json")
    )

    # 앱 실행 (터미널 상태 복원 보장)
    app = OrchestratorTUI()
    try:
        app.run()
    except KeyboardInterrupt:
        # Ctrl+C로 종료 시 정상 종료 처리
        pass
    except Exception as e:
        logger.error(f"TUI 실행 중 에러 발생: {e}", exc_info=True)
        raise
    finally:
        # 터미널 상태 완전 복원
        import sys
        # 1. 대체 화면 버퍼 해제 (alternate screen buffer)
        sys.stdout.write('\033[?1049l')  # Exit alternate screen
        # 2. 마우스 트래킹 모드 해제
        sys.stdout.write('\033[?1000l')  # Disable mouse tracking
        sys.stdout.write('\033[?1003l')  # Disable all mouse tracking
        sys.stdout.write('\033[?1015l')  # Disable urxvt mouse mode
        sys.stdout.write('\033[?1006l')  # Disable SGR mouse mode
        # 3. 기타 모드 해제
        sys.stdout.write('\033[?25h')    # Show cursor
        sys.stdout.write('\033[?1004l')  # Disable focus events
        sys.stdout.write('\033[?2004l')  # Disable bracketed paste mode
        # 4. 터미널 속성 리셋
        sys.stdout.write('\033[0m')      # Reset all attributes (colors, styles)
        sys.stdout.write('\033[H')       # Move cursor to home position
        sys.stdout.write('\033[2J')      # Clear entire screen
        # 5. 모든 변경사항 플러시
        sys.stdout.flush()


if __name__ == "__main__":
    main()
