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
from typing import Optional, List, Tuple, Union, Dict
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
    SessionManager,
    WorkerOutputManager,
    LayoutManager,
    MetricsUIManager,
    InputHandler,
    WorkflowUIManager,
)
from .managers.session_manager import SessionData
from .commands import SlashCommandHandler
from .runners import TaskRunner

logger = get_logger(__name__, component="TUI")


class WorkerTabPane(TabPane):
    """
    Worker 출력을 담는 커스텀 TabPane

    Textual의 공식 API를 사용하여 TabPane에 위젯을 추가합니다.
    Private API (_add_child)를 사용하지 않고 compose() 메서드를 오버라이드합니다.

    탭 제목 업데이트가 필요한 경우 TabPane.label을 직접 수정하는 대신
    탭을 재생성하는 방식을 사용합니다 (Textual 공식 권장 방식).
    """

    def __init__(self, title: str, worker_log: RichLog, **kwargs):
        """
        WorkerTabPane 초기화

        Args:
            title: 탭 제목
            worker_log: Worker 출력을 표시할 RichLog 위젯
            **kwargs: TabPane의 추가 인자 (id 등)
        """
        super().__init__(title, **kwargs)
        self._worker_log = worker_log

    def compose(self) -> ComposeResult:
        """TabPane에 표시할 위젯 구성"""
        yield self._worker_log


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
        # Ctrl+R은 MultilineInput 위젯에서 처리 (바인딩 충돌 방지)
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

    def __init__(self):
        super().__init__()
        # 멀티 세션 관리는 SessionManager가 담당 (Phase 1.4)
        # self.sessions와 self.active_session_index는 제거되고
        # self.session_manager.get_all_sessions() 및 get_active_session_index()로 대체됨

        # 현재 세션 참조 (편의를 위한 프로퍼티)
        self.manager: Optional[ManagerAgent] = None
        self.initialized = False
        self.current_task = None  # 현재 실행 중인 asyncio Task
        self.task_start_time = None  # 작업 시작 시간
        self.timer_active = False  # 타이머 활성화 여부
        self.ctrl_c_count = 0  # Ctrl+C 누른 횟수
        self.last_ctrl_c_time = 0  # 마지막 Ctrl+C 누른 시간

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

        # 자동 완성 엔진
        project_root = get_project_root()
        self.autocomplete_engine = AutocompleteEngine(working_dir=project_root)

        # 출력 모드 ("manager" 또는 "worker")
        self.output_mode: str = "manager"
        self.active_workers: Dict[str, RichLog] = {}  # Worker 이름 -> RichLog 매핑
        self.current_worker_tab: Optional[str] = None  # 현재 선택된 워커 탭

        # MessageRenderer 인스턴스 (상태 유지용)
        self.message_renderer = MessageRenderer()

        # Level 1 매니저 초기화 (6개)
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
        self.input_handler = InputHandler()
        self.workflow_ui_manager = WorkflowUIManager()

        # 슬래시 커맨드 핸들러 초기화
        self.slash_command_handler = SlashCommandHandler(self)

        # 작업 실행 핸들러 초기화
        self.task_runner = TaskRunner(self)

        # 액션 핸들러 초기화 (Phase 1.3)
        from src.presentation.tui.actions.action_handler import ActionHandler
        self.action_handler = ActionHandler(self)

    @property
    def current_session(self) -> SessionData:
        """현재 활성 세션 데이터 반환 (Phase 1.4: SessionManager 위임)"""
        active_index = self.session_manager.get_active_session_index()
        return self.session_manager.get_session_by_index(active_index)

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

    def compose(self) -> ComposeResult:
        """UI 구성"""
        # Manager 출력 영역
        with ScrollableContainer(id="output-container"):
            yield RichLog(id="output-log", markup=True, highlight=True, wrap=True)

        # Worker 출력 영역 (TabbedContent 기반, 기본 숨김)
        with Container(id="worker-output-container", classes="hidden"):
            with TabbedContent(id="worker-tabs"):
                # 기본 상태: "No active workers" 탭 표시
                with TabPane("No active workers", id="no-workers-tab"):
                    yield Static(
                        "[dim]실행 중인 Worker가 없습니다[/dim]",
                        id="no-workers-message"
                    )

        # Worker 상태 표시
        with Container(id="worker-status-container"):
            yield Static("⏳ 초기화 중...", id="worker-status")

        # 메트릭 대시보드
        with Container(id="metrics-container"):
            yield Static("📊 메트릭 없음", id="metrics-panel")

        # 워크플로우 비주얼라이저
        with Container(id="workflow-container"):
            yield WorkflowVisualizer(id="workflow-visualizer")

        # 입력 영역
        with Container(id="input-container"):
            yield MultilineInput(
                id="task-input"
            )
            yield Static("", id="autocomplete-preview", classes="hidden")

        # 하단 정보바
        with Horizontal(id="info-bar"):
            yield Static(f"Session: {self.session_id}", id="session-info")
            yield Static("Tokens: 0K", id="token-info")
            yield Static("Ready", id="status-info")

        yield Footer()

    async def on_mount(self) -> None:
        """앱 마운트 시 초기화"""
        await self.initialize_orchestrator()
        # 타이머: 0.2초마다 Worker Tool 실행 시간 업데이트
        self.set_interval(0.2, self.update_worker_status_timer)
        # 타이머: 1초마다 메트릭 대시보드 업데이트
        self.set_interval(1.0, self.update_metrics_panel)
        # 타이머: 1초마다 토큰 사용량 업데이트
        self.set_interval(1.0, self.update_token_info)
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

    async def initialize_orchestrator(self) -> None:
        """오케스트레이터 초기화"""
        worker_status = self.query_one("#worker-status", Static)
        status_info = self.query_one("#status-info", Static)
        output_log = self.query_one("#output-log", RichLog)

        try:
            worker_status.update("⏳ 초기화 중...")
            status_info.update("Initializing...")

            # 환경 검증
            validate_environment()
            work_dir = os.getcwd()
            oauth_token = os.getenv("CLAUDE_CODE_OAUTH_TOKEN", "").strip()
            token_status = "설정됨" if (oauth_token and len(oauth_token) > 10) else "미설정"

            # Worker Agent들 초기화
            config_path = get_project_root() / "config" / "agent_config.json"
            initialize_workers(config_path)

            # agent_config.json에서 Worker 목록 로드
            config_loader = JsonConfigLoader(get_project_root())
            agents = config_loader.load_agent_configs()

            if not agents:
                raise ValueError(
                    "agent_config.json에 Worker Agent가 정의되지 않았습니다. "
                    "config/agent_config.json 파일을 확인해주세요."
                )

            worker_names = [agent.name.capitalize() for agent in agents]
            worker_count = len(worker_names)
            worker_list = ", ".join(worker_names)

            # Worker Tools MCP Server 생성
            worker_tools_server = create_worker_tools_server()

            # system_config 로드
            system_config = config_loader.load_system_config()
            auto_commit_enabled = system_config.get("workflow", {}).get("auto_commit_enabled", False)
            manager_model = system_config.get("manager", {}).get("model", "unknown")

            # Manager Agent 초기화
            self.manager = ManagerAgent(
                worker_tools_server,
                auto_commit_enabled=auto_commit_enabled
            )

            # 메트릭 & 콜백 설정
            set_metrics_collector(self.metrics_collector, self.session_id)
            set_workflow_callback(self.on_workflow_update)
            set_worker_output_callback(self.on_worker_output)

            self.initialized = True
            worker_status.update("✅ 준비 완료")
            status_info.update("Ready")

            # 컴팩트한 초기화 완료 메시지
            self.write_log("")
            self.write_log(f"[bold green]🚀 준비 완료[/bold green] [dim]• Workers: {worker_count}개 • Model: {manager_model}[/dim]")
            self.write_log("")
            self.write_log("[dim]💡 Tip: Ctrl+R (입력 제출) | Ctrl+H (도움말) | Ctrl+F (검색) | Ctrl+M (메트릭)[/dim]")
            self.write_log("[dim]     Enter는 줄바꿈, Ctrl+R로 제출하세요[/dim]")
            self.write_log("")

        except Exception as e:
            # 피드백 시스템 사용
            error_panel = TUIFeedbackWidget.create_panel(
                "초기화에 실패했습니다",
                FeedbackType.ERROR,
                details=str(e)
            )
            self.write_log(error_panel)
            worker_status.update(f"❌ 오류: {e}")
            status_info.update("Error")

    async def on_multiline_input_submitted(self, event: MultilineInput.Submitted) -> None:
        """Ctrl+R 입력 시 작업 실행"""
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
            self.update_worker_status("")

        # 새 작업 시작
        logger.info(f"🚀 [TUI] 새 작업 시작: {user_request!r}")
        self.current_task = asyncio.create_task(self.task_runner.run_task(user_request))
        logger.info(f"✅ [TUI] asyncio Task 생성 완료")

    async def handle_slash_command(self, command: str) -> None:
        """슬래시 명령 처리 (SlashCommandHandler로 위임)"""
        await self.slash_command_handler.handle_slash_command(command)

    async def action_new_session(self) -> None:
        """Ctrl+N: 새 세션 (ActionHandler로 위임)"""
        await self.action_handler.action_new_session()

    def on_input_changed(self, event: Input.Changed) -> None:
        """입력 변경 이벤트 - 현재는 사용하지 않음."""
        # InputHandler는 슬래시 명령어 처리용이므로 여기서는 사용하지 않음
        pass

    def on_resize(self, event: events.Resize) -> None:
        """화면 크기 변경 이벤트 (LayoutManager로 위임)."""
        self.layout_manager.calculate_layout((event.size.width, event.size.height))

    def update_layout_for_size(self, width: int, height: int) -> None:
        """레이아웃 크기 업데이트 (LayoutManager로 위임)."""
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

    def update_worker_status(self, message: str) -> None:
        """Worker Tool 상태 메시지 업데이트"""
        try:
            worker_status = self.query_one("#worker-status", Static)
            worker_status.update(message)
        except Exception:
            pass  # 위젯이 아직 없으면 무시

    def apply_metrics_panel_visibility(self) -> None:
        """메트릭 패널 표시/숨김 상태 적용"""
        try:
            metrics_container = self.query_one("#metrics-container", Container)
            if self.show_metrics_panel:
                metrics_container.remove_class("hidden")
            else:
                metrics_container.add_class("hidden")
        except Exception:
            pass  # 위젯이 아직 없으면 무시

    def apply_workflow_panel_visibility(self) -> None:
        """워크플로우 패널 표시/숨김 상태 적용"""
        try:
            workflow_container = self.query_one("#workflow-container", Container)
            if self.show_workflow_panel:
                workflow_container.remove_class("hidden")
            else:
                workflow_container.add_class("hidden")
        except Exception:
            pass  # 위젯이 아직 없으면 무시

    def apply_worker_status_visibility(self) -> None:
        """Worker 상태 패널 표시/숨김 상태 적용"""
        try:
            worker_status_container = self.query_one("#worker-status-container", Container)
            if self.show_worker_status:
                worker_status_container.remove_class("hidden")
            else:
                worker_status_container.add_class("hidden")
        except Exception:
            pass  # 위젯이 아직 없으면 무시

    def on_workflow_update(self, worker_name: str, status: str, error: Optional[str] = None) -> None:
        """워크플로우 상태 업데이트 콜백."""
        # WorkflowVisualizer 위젯을 직접 업데이트
        self._update_workflow_ui(worker_name, status, error)

    def _update_workflow_ui(self, worker_name: str, status: str, error: Optional[str] = None) -> None:
        """워크플로우 UI 업데이트."""
        try:
            # WorkflowVisualizer 위젯 업데이트
            workflow_visualizer = self.query_one("#workflow-visualizer", WorkflowVisualizer)
            workflow_visualizer.update_worker_status(worker_name, status, error)

            # Worker 실행 시작 시 새 탭 생성 및 등록
            if status == "running":
                self._create_worker_tab(worker_name)
                self.current_worker_tab = worker_name

            # Worker 실행 완료/실패 시 탭 업데이트 (히스토리 보존)
            elif status in ["completed", "failed"]:
                self._update_worker_tab_status(worker_name, status)

        except Exception as e:
            logger.warning(f"워크플로우 업데이트 실패: {e}")

    def _create_worker_tab(self, worker_name: str) -> None:
        """Worker 탭 생성."""
        try:
            # 이미 생성된 탭이 있으면 스킵
            if worker_name in self.active_workers:
                return

            # RichLog 생성
            worker_log = RichLog(
                id=f"worker-log-{worker_name}",
                markup=True,  # 정제된 출력에서 Rich 마크업 사용
                highlight=False,  # Worker 출력은 구문 강조 비활성화
                wrap=True
            )
            self.active_workers[worker_name] = worker_log

            # WorkerTabPane 생성 및 추가
            worker_tabs = self.query_one("#worker-tabs", TabbedContent)

            # "No active workers" 탭 제거
            try:
                no_workers_tab = self.query_one("#no-workers-tab", TabPane)
                worker_tabs.remove_children([no_workers_tab])
            except NoMatches:
                pass  # 이미 제거됨

            # 새 탭 추가
            tab = WorkerTabPane(
                f"{worker_name.capitalize()} ▶️",
                worker_log,
                id=f"worker-tab-{worker_name}"
            )
            worker_tabs.add_pane(tab)
            worker_tabs.active = f"worker-tab-{worker_name}"

            logger.info(f"Worker 탭 생성: {worker_name}")

        except Exception as e:
            logger.error(f"Worker 탭 생성 실패: {worker_name} - {e}")

    def _update_worker_tab_status(self, worker_name: str, status: str) -> None:
        """Worker 탭 상태 업데이트."""
        try:
            if worker_name not in self.active_workers:
                return

            # 탭 제목 업데이트 (Textual API 제약으로 인해 재생성 방식 사용)
            worker_tabs = self.query_one("#worker-tabs", TabbedContent)

            # 상태 이모지 결정
            status_emoji = {
                "completed": "✅",
                "failed": "❌",
                "running": "▶️"
            }.get(status, "⏸️")

            # 기존 탭 제목 업데이트 (Textual의 TabPane.label 사용)
            try:
                tab = self.query_one(f"#worker-tab-{worker_name}", TabPane)
                # TabPane의 label 속성 직접 수정 (공식 API)
                new_title = f"{worker_name.capitalize()} {status_emoji}"
                # Textual 0.47+에서는 tab.label로 접근 가능
                if hasattr(tab, 'label'):
                    tab.label = new_title
                logger.info(f"Worker 탭 상태 업데이트: {worker_name} -> {status}")
            except NoMatches:
                logger.warning(f"Worker 탭을 찾을 수 없음: {worker_name}")

        except Exception as e:
            logger.error(f"Worker 탭 상태 업데이트 실패: {worker_name} - {e}")

    def on_worker_output(self, worker_name: str, chunk: str) -> None:
        """Worker 출력 콜백."""
        self._write_worker_output(worker_name, chunk)

    def _write_worker_output(self, worker_name: str, chunk: str) -> None:
        """Worker 출력 작성 (파싱 및 정제 적용)."""
        try:
            if worker_name not in self.active_workers:
                logger.warning(f"Worker 탭을 찾을 수 없음: {worker_name}")
                return

            # Worker 출력 파싱 및 정제
            formatted_chunk = WorkerOutputParser.format_for_display(chunk, worker_name)

            worker_log = self.active_workers[worker_name]
            # markup=False로 설정했으므로 Rich 마크업을 사용하려면 직접 처리 필요
            # 하지만 markup=False이므로 플레인 텍스트로 표시됨
            # 정제된 내용만 표시
            if formatted_chunk and formatted_chunk.strip():
                worker_log.write(formatted_chunk)

            # WorkerOutputManager에도 기록 (히스토리 관리, 원본 유지)
            self.worker_output_manager.stream_output(worker_name, chunk)

        except Exception as e:
            logger.error(f"Worker 출력 작성 실패: {worker_name} - {e}")

    def update_worker_status_timer(self) -> None:
        """타이머: Worker Tool 실행 시간 업데이트 (0.5초마다 호출)"""
        if not self.timer_active or self.task_start_time is None:
            return

        try:
            elapsed = time.time() - self.task_start_time
            # 애니메이션 효과를 위한 스피너
            spinner_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
            spinner = spinner_frames[int(elapsed * 2) % len(spinner_frames)]

            # WorkflowVisualizer에서 실행 중인 워커 정보 가져오기
            workflow_visualizer = self.query_one("#workflow-visualizer", WorkflowVisualizer)
            running_workers = workflow_visualizer.get_running_workers()

            # status-info에 실행 시간 및 워커 정보 표시
            status_info = self.query_one("#status-info", Static)

            if running_workers:
                # 실행 중인 워커가 있으면 워커 정보 표시
                worker_name, worker_elapsed = running_workers[0]  # 첫 번째 워커만 표시
                worker_emoji = {
                    "planner": "🧠",
                    "coder": "💻",
                    "reviewer": "🔍",
                    "tester": "🧪",
                    "committer": "📝",
                }.get(worker_name.lower(), "🔧")

                status_info.update(
                    f"{spinner} Running... ⏱️ {elapsed:.1f}s • "
                    f"{worker_emoji} {worker_name.capitalize()} ({worker_elapsed:.1f}s)"
                )
            else:
                # 워커 정보 없으면 기본 표시
                status_info.update(f"{spinner} Running... ⏱️  {elapsed:.1f}s")

            # worker-status는 표시되어 있을 때만 업데이트
            if self.show_worker_status:
                if running_workers:
                    worker_name, worker_elapsed = running_workers[0]
                    worker_emoji = {
                        "planner": "🧠",
                        "coder": "💻",
                        "reviewer": "🔍",
                        "tester": "🧪",
                        "committer": "📝",
                    }.get(worker_name.lower(), "🔧")
                    self.update_worker_status(
                        f"{spinner} {worker_emoji} {worker_name.capitalize()} 실행 중... ⏱️  {worker_elapsed:.1f}s"
                    )
                else:
                    self.update_worker_status(f"{spinner} Manager Agent 실행 중... ⏱️  {elapsed:.1f}s")
        except Exception:
            pass

    def update_token_info(self) -> None:
        """타이머: 토큰 사용량 업데이트 (1초마다 호출)"""
        try:
            if not self.manager:
                return

            token_info_widget = self.query_one("#token-info", Static)

            # Manager Agent에서 토큰 사용량 가져오기
            usage = self.manager.get_token_usage()
            total_tokens = usage["total_tokens"]
            input_tokens = usage["input_tokens"]
            output_tokens = usage["output_tokens"]

            # 모델별 컨텍스트 윈도우 (토큰 수)
            # Claude Sonnet 4.5: 200K context window
            context_window = 200_000

            # 사용률 계산
            usage_percentage = (total_tokens / context_window) * 100 if context_window > 0 else 0

            # 표시 형식: "Tokens: 15K/200K (7.5%)"
            if total_tokens >= 1000:
                total_display = f"{total_tokens // 1000}K"
            else:
                total_display = str(total_tokens)

            # 색상: 초록(< 50%), 노랑(50-80%), 빨강(>= 80%)
            if usage_percentage < 50:
                color = "green"
            elif usage_percentage < 80:
                color = "yellow"
            else:
                color = "red"

            token_info_widget.update(
                f"[{color}]Tokens: {total_display}/200K ({usage_percentage:.1f}%)[/{color}]"
            )

        except Exception as e:
            logger.warning(f"토큰 정보 업데이트 실패: {e}")

    def update_metrics_panel(self) -> None:
        """메트릭 패널 업데이트 (MetricsUIManager로 위임)."""
        try:
            metrics_panel = self.query_one("#metrics-panel", Static)
            # 현재 메트릭 수집기에서 메트릭 가져오기
            metrics = self.metrics_collector.get_all_metrics()
            if metrics:
                # MetricsUIManager의 render_dashboard() 사용
                dashboard = self.metrics_ui_manager.render_dashboard(metrics)
                metrics_panel.update(dashboard)
            else:
                metrics_panel.update("📊 메트릭 없음")
        except Exception as e:
            logger.warning(f"메트릭 패널 업데이트 실패: {e}")

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
        await self.action_handler.action_save_log()

    async def action_show_session_browser(self) -> None:
        """Ctrl+L: 세션 브라우저 표시 (ActionHandler로 위임)"""
        await self.action_handler.action_show_session_browser()

    async def action_search_log(self) -> None:
        """Ctrl+F: 로그 검색 (ActionHandler로 위임)"""
        await self.action_handler.action_search_log()

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
            worker_status = self.query_one("#worker-status", Static)
            status_info = self.query_one("#status-info", Static)

            self.write_log("")
            self.write_log(Panel(
                f"[bold cyan]🔄 세션 불러오는 중...[/bold cyan]\n\n"
                f"Session ID: {session_id}",
                border_style="cyan"
            ))
            self.write_log("")

            # 세션 파일 찾기
            sessions_dir = Path("sessions")
            session_files = list(sessions_dir.glob(f"{session_id}_*.json"))

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

            # 새 세션 생성 및 히스토리 복원 (Phase 1.4: SessionManager 사용)
            loaded_session = SessionData(
                session_id=session_id,
                history=ConversationHistory(),
                log_lines=[],
                start_time=time.time(),
                metrics_repository=InMemoryMetricsRepository(),
                metrics_collector=MetricsCollector(InMemoryMetricsRepository())
            )
            for msg in session_data.get("history", []):
                loaded_session.history.add_message(msg["role"], msg["content"])

            # 현재 세션 교체
            active_index = self.session_manager.get_active_session_index()
            self.session_manager.update_session_at_index(active_index, loaded_session)

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

            worker_status.update("✅ 세션 로드됨")
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

    def _track_log_output(self, content: str) -> None:
        """
        로그 출력 추적 (Phase 2.1: 로그 버퍼 관리)

        Args:
            content: 로그 내용
        """
        # 문자열로 변환 (Panel, Text 등의 객체 처리)
        if hasattr(content, "__str__"):
            content_str = str(content)
        else:
            content_str = content

        # 현재 세션의 log_lines에 추가 (property를 통해 접근)
        self.current_session.log_lines.append(content_str)

        # 최대 라인 수 제한
        max_lines = self.settings.max_log_lines
        if len(self.current_session.log_lines) > max_lines:
            # 오래된 라인 제거
            self.current_session.log_lines = self.current_session.log_lines[-max_lines:]

    def write_log(
        self, content: Union[str, Panel, Text], widget_id: str = "output-log"
    ) -> None:
        """
        로그 출력 및 추적 헬퍼 메서드

        Args:
            content: 출력할 내용 (str, Panel, Text 중 하나)
            widget_id: RichLog 위젯 ID
        """
        try:
            output_log = self.query_one(f"#{widget_id}", RichLog)

            # RichLog의 실제 너비 계산
            # (컨테이너 너비 - 패딩 - 스크롤바 - 보더)
            try:
                # output_log의 실제 표시 너비
                available_width = output_log.size.width
                # PANEL_PADDING 상수 사용 (padding(1)*2 + scrollbar(1) + border(2))
                PANEL_PADDING = 5
                effective_width = max(
                    available_width - PANEL_PADDING,
                    MessageRenderer.MIN_OUTPUT_WIDTH
                )

                # Rich Console 객체를 동적으로 생성하여 width 설정
                from rich.console import Console
                from io import StringIO

                # Panel이나 복잡한 객체의 경우, width를 고려하여 렌더링
                if isinstance(content, Panel):
                    # Panel의 경우 width 옵션 적용
                    content.width = effective_width

            except (AttributeError, ValueError) as e:
                # 크기 계산 실패 시 로깅 후 기본 동작
                logger.warning(f"로그 너비 계산 실패: {e}, 기본 동작 사용")
            except Exception as e:
                # 기타 예외 시 로깅 후 기본 동작
                logger.warning(f"로그 렌더링 중 예외: {e}, 기본 동작 사용")

            output_log.write(content)
            # 로그 버퍼에도 추가
            self._track_log_output(str(content))
        except Exception as e:
            # write_log 자체가 실패하면 로깅만 하고 넘어감
            logger.error(f"로그 출력 실패: {e}")

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
        await self.action_handler.action_show_error_stats()

    async def action_next_worker_tab(self) -> None:
        """Ctrl+Tab: 다음 워커 탭으로 전환 (ActionHandler로 위임)"""
        await self.action_handler.action_next_worker_tab()

    async def action_prev_worker_tab(self) -> None:
        """Ctrl+Shift+Tab: 이전 워커 탭으로 전환 (ActionHandler로 위임)"""
        await self.action_handler.action_prev_worker_tab()

    async def action_switch_to_session_1(self) -> None:
        """Ctrl+1: 세션 1로 전환 (ActionHandler로 위임)"""
        await self.action_handler.action_switch_to_session_1()

    async def action_switch_to_session_2(self) -> None:
        """Ctrl+2: 세션 2로 전환 (ActionHandler로 위임)"""
        await self.action_handler.action_switch_to_session_2()

    async def action_switch_to_session_3(self) -> None:
        """Ctrl+3: 세션 3로 전환 (ActionHandler로 위임)"""
        await self.action_handler.action_switch_to_session_3()

    async def switch_to_session(self, index: int) -> None:
        """
        세션 전환 (0, 1, 2)

        Args:
            index: 세션 인덱스 (0=Ctrl+1, 1=Ctrl+2, 2=Ctrl+3)
        """
        try:
            # 세션이 아직 없으면 생성 (Phase 1.4: SessionManager 사용)
            while self.session_manager.get_session_count() <= index:
                new_session_id = generate_session_id()
                new_index = self.session_manager.get_session_count()
                self.session_manager.create_session_at_index(new_index, new_session_id)

            # 이미 현재 세션이면 무시
            active_index = self.session_manager.get_active_session_index()
            if active_index == index:
                if self.settings.enable_notifications:
                    self.notify(f"이미 세션 {index + 1}입니다", severity="information")
                return

            # 세션 전환
            old_index = active_index
            self.session_manager.switch_to_session(index)

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

            # 알림 표시
            if self.settings.enable_notifications:
                self.notify(
                    f"세션 {index + 1}로 전환 (ID: {self.session_id[:8]}...)",
                    severity="information"
                )

        except Exception as e:
            logger.error(f"세션 전환 실패: {e}")
            if self.settings.enable_notifications and self.settings.notify_on_error:
                self.notify(f"세션 전환 실패: {e}", severity="error")

    async def action_interrupt_or_quit(self) -> None:
        """Ctrl+C: 작업 중단 또는 종료 (ActionHandler로 위임)"""
        await self.action_handler.action_interrupt_or_quit()

    async def action_show_help(self) -> None:
        """?: 도움말 표시 (ActionHandler로 위임)"""
        await self.action_handler.action_show_help()

    async def action_show_settings(self) -> None:
        """F2: 설정 표시 (ActionHandler로 위임)"""
        await self.action_handler.action_show_settings()

    async def action_toggle_metrics_panel(self) -> None:
        """Ctrl+M: 메트릭 패널 토글 (ActionHandler로 위임)"""
        await self.action_handler.action_toggle_metrics_panel()

    async def action_toggle_workflow_panel(self) -> None:
        """F4: 워크플로우 패널 토글 (ActionHandler로 위임)"""
        await self.action_handler.action_toggle_workflow_panel()

    async def action_toggle_worker_status(self) -> None:
        """F5: Worker 상태 패널 토글 (ActionHandler로 위임)"""
        await self.action_handler.action_toggle_worker_status()

    async def action_history_up(self) -> None:
        """Up: 이전 입력 히스토리 (ActionHandler로 위임)"""
        await self.action_handler.action_history_up()

    async def action_history_down(self) -> None:
        """Down: 다음 입력 히스토리 (ActionHandler로 위임)"""
        await self.action_handler.action_history_down()

    async def action_toggle_output_mode(self) -> None:
        """Ctrl+O: Manager/Worker 출력 전환 (ActionHandler로 위임)"""
        await self.action_handler.action_toggle_output_mode()


def main():
    """메인 함수"""
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
        # 터미널 상태 복원 (마우스 트래킹 모드 해제)
        import sys
        # ANSI escape codes for disabling mouse tracking
        sys.stdout.write('\033[?1000l')  # Disable mouse tracking
        sys.stdout.write('\033[?1003l')  # Disable all mouse tracking
        sys.stdout.write('\033[?1015l')  # Disable urxvt mouse mode
        sys.stdout.write('\033[?1006l')  # Disable SGR mouse mode
        sys.stdout.write('\033[?25h')    # Show cursor
        sys.stdout.write('\033[?1004l')  # Disable focus events
        sys.stdout.flush()


if __name__ == "__main__":
    main()
