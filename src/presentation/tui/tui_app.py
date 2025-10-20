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
from typing import Optional, List, Tuple, Union
from enum import Enum

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, ScrollableContainer, Horizontal
from textual.widgets import Footer, Input, Static, RichLog, Header
from textual.binding import Binding
from textual import events
from rich.panel import Panel
from rich.markdown import Markdown
from rich.text import Text
from rich.table import Table

from src.domain.models import SessionResult
from src.domain.models.session import SessionStatus
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
from ..cli.utils import (
    generate_session_id,
    save_session_history,
    validate_user_input,
    sanitize_user_input,
    save_metrics_report,
)
from ..cli.feedback import TUIFeedbackWidget, FeedbackType
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
)

logger = logging.getLogger(__name__)


class SessionData:
    """세션별 데이터 저장 클래스"""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.history: Optional[ConversationHistory] = ConversationHistory()
        self.log_lines: List[str] = []
        self.start_time = time.time()
        self.metrics_repository = InMemoryMetricsRepository()
        self.metrics_collector = MetricsCollector(self.metrics_repository)

    def __repr__(self) -> str:
        return f"SessionData(id={self.session_id})"


class LayoutMode(Enum):
    """레이아웃 모드 정의"""
    LARGE = "Large"  # width >= 120, height >= 30 (모든 패널 표시)
    MEDIUM = "Medium"  # width >= 80, height >= 24 (메트릭 패널 토글 가능)
    SMALL = "Small"  # width < 80 or height < 24 (메트릭 패널 자동 숨김)


class OrchestratorTUI(App):
    """전문적인 오케스트레이션 TUI 애플리케이션"""

    CSS = """
    Screen {
        background: #0d1117;
    }

    /* 숨김 클래스 */
    .hidden {
        display: none;
    }

    /* 출력 영역 */
    #output-container {
        border: tall #21262d;
        background: #0d1117;
        height: 1fr;
        margin: 0 1;
        padding: 0;
    }

    #output-log {
        height: 1fr;
        background: #0d1117;
        padding: 1;
        scrollbar-gutter: stable;
    }

    /* Worker 출력 영역 */
    #worker-output-container {
        border: tall #21262d;
        background: #0d1117;
        height: 1fr;
        margin: 0 1;
        padding: 0;
    }

    #worker-output-log {
        height: 1fr;
        background: #0d1117;
        padding: 1;
        scrollbar-gutter: stable;
    }

    /* Worker 상태 표시 */
    #worker-status-container {
        height: auto;
        margin: 0 1;
        background: transparent;
        border: round #21262d;
        padding: 0;
    }

    #worker-status {
        background: transparent;
        color: #8b949e;
        padding: 0 2;
        height: auto;
    }

    /* 메트릭 대시보드 */
    #metrics-container {
        height: auto;
        margin: 0 1;
        background: transparent;
        border: round #21262d;
        padding: 0;
    }

    #metrics-panel {
        background: transparent;
        color: #8b949e;
        padding: 0 2;
        height: auto;
    }

    /* 워크플로우 비주얼라이저 */
    #workflow-container {
        height: auto;
        max-height: 20;
        margin: 0 1;
        background: transparent;
        border: round #21262d;
        padding: 0 2;
    }

    WorkflowVisualizer {
        background: transparent;
        height: auto;
    }

    /* 입력 영역 */
    #input-container {
        height: auto;
        background: #0d1117;
        border: round #388bfd;
        margin: 0 1;
        padding: 1 2;
    }

    Input {
        background: transparent;
        border: none;
        color: #c9d1d9;
        padding: 0;
        margin: 0;
    }

    Input:focus {
        border: none;
        background: transparent;
    }

    Input.-placeholder {
        color: #6e7681;
    }

    /* MultilineInput 스타일 (TextArea 기반) */
    MultilineInput {
        background: #0d1117;
        border: none;
        color: #c9d1d9;
        padding: 0;
        margin: 0;
        height: auto;
        max-height: 10;
    }

    MultilineInput:focus {
        border: none;
        background: #0d1117;
    }

    MultilineInput > .text-area--cursor {
        background: #c9d1d9;
    }

    MultilineInput > .text-area--selection {
        background: #388bfd40;
    }

    /* 자동 완성 미리보기 */
    #autocomplete-preview {
        height: auto;
        background: transparent;
        color: #6e7681;
        padding: 0;
        margin-top: 1;
    }

    #autocomplete-preview.hidden {
        display: none;
    }

    /* 하단 정보바 */
    #info-bar {
        dock: bottom;
        height: 1;
        background: #0d1117;
        color: #6e7681;
        padding: 0 2;
        border-top: tall #21262d;
    }

    #session-info {
        text-align: left;
        width: 2fr;
    }

    #token-info {
        text-align: center;
        width: 1fr;
        color: #58a6ff;
    }

    #status-info {
        text-align: right;
        width: 2fr;
    }

    /* Footer 스타일 */
    Footer {
        background: #0d1117;
        border-top: tall #21262d;
    }

    Footer > .footer--key {
        background: #1c2128;
        color: #58a6ff;
    }

    Footer > .footer--description {
        color: #8b949e;
    }

    /* 반응형 레이아웃 클래스 */
    .layout-warning {
        background: #4d1d00;
        border: tall #ff8800;
    }

    .layout-small #metrics-container {
        display: none;
    }

    .layout-small #input-container {
        margin: 0 1;
    }
    """

    BINDINGS = [
        # 기본 동작
        Binding("ctrl+c", "interrupt_or_quit", "중단/종료"),
        Binding("ctrl+n", "new_session", "새 세션"),
        Binding("ctrl+s", "save_log", "로그 저장"),
        Binding("ctrl+l", "show_session_browser", "세션"),

        # 검색 (수정됨!)
        Binding("/", "search_log", "검색"),
        Binding("ctrl+f", "search_log", "검색", show=False),

        # 도움말 (수정됨!)
        Binding("?", "show_help", "도움말"),
        Binding("ctrl+h", "show_help", "도움말", show=False),
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

        # 세션 전환
        Binding("ctrl+1", "switch_to_session_1", "세션 1"),
        Binding("ctrl+2", "switch_to_session_2", "세션 2"),
        Binding("ctrl+3", "switch_to_session_3", "세션 3"),
    ]

    def __init__(self):
        super().__init__()
        # 멀티 세션 관리
        initial_session_id = generate_session_id()
        self.sessions: List[SessionData] = [
            SessionData(initial_session_id)
        ]
        self.active_session_index: int = 0  # 현재 활성 세션 인덱스 (0, 1, 2)

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
        self.current_worker_name: Optional[str] = None  # 현재 실행 중인 Worker 이름

        # MessageRenderer 인스턴스 (상태 유지용)
        self.message_renderer = MessageRenderer()

    @property
    def current_session(self) -> SessionData:
        """현재 활성 세션 데이터 반환"""
        return self.sessions[self.active_session_index]

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

        # Worker 출력 영역 (기본 숨김)
        with ScrollableContainer(id="worker-output-container", classes="hidden"):
            yield RichLog(id="worker-output-log", markup=True, highlight=True, wrap=True)

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
        # 타이머: 0.5초마다 Worker Tool 실행 시간 업데이트
        self.set_interval(0.5, self.update_worker_status_timer)
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
            api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
            api_key_status = "설정됨" if (api_key and len(api_key) > 10) else "미설정"

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
        """Enter 키 입력 시 작업 실행"""
        if not self.initialized:
            return

        user_request = event.value.strip()
        if not user_request:
            return

        # 히스토리에 추가
        self.input_history.add(user_request)

        # 슬래시 커맨드 처리
        if user_request.startswith('/'):
            await self.handle_slash_command(user_request)
            return

        # 현재 실행 중인 작업이 있으면 중단
        if self.current_task and not self.current_task.done():
            self.current_task.cancel()
            self.timer_active = False
            self.update_worker_status("")

        # 새 작업 시작
        self.current_task = asyncio.create_task(self.run_task(user_request))

    def on_input_changed(self, event: Input.Changed) -> None:
        """
        입력 변경 이벤트 - Phase 2.3: 실시간 입력 검증

        입력 길이 표시 및 최대 길이 경고
        """
        try:
            status_info = self.query_one("#status-info", Static)
            input_length = len(event.value)
            max_length = self.settings.max_log_lines  # 임시로 설정 값 사용

            # 입력 길이가 길 때 경고
            if input_length > 4000:
                status_info.update(f"[yellow]입력: {input_length}자 (길이 주의)[/yellow]")
            elif input_length > 500:
                status_info.update(f"입력: {input_length}자")
            else:
                status_info.update("Ready")

        except Exception:
            pass  # 위젯이 없으면 무시

    async def on_text_area_changed(self, event) -> None:
        """
        TextArea (MultilineInput) 입력 변경 이벤트

        자동 완성 상태를 리셋합니다 (Tab 키 외의 입력 시).
        """
        try:
            # 자동 완성 미리보기 숨기기
            autocomplete_preview = self.query_one("#autocomplete-preview", Static)
            autocomplete_preview.add_class("hidden")

            # 자동 완성 엔진 리셋
            self.autocomplete_engine.reset()

        except Exception:
            pass  # 위젯이 없으면 무시

    async def run_task(self, user_request: str) -> None:
        """작업 실행 - Manager가 Worker Tools를 자동으로 호출"""
        task_input = self.query_one("#task-input", MultilineInput)
        output_log = self.query_one("#output-log", RichLog)
        worker_status = self.query_one("#worker-status", Static)
        status_info = self.query_one("#status-info", Static)

        try:
            # 입력 검증
            is_valid, error_msg = validate_user_input(user_request)
            if not is_valid:
                # 피드백 시스템 사용
                error_panel = TUIFeedbackWidget.create_panel(
                    "입력 검증 실패",
                    FeedbackType.ERROR,
                    details=error_msg
                )
                self.write_log("")
                self.write_log(error_panel)
                self.write_log("")
                task_input.clear()
                return

            # 입력 정제
            user_request = sanitize_user_input(user_request)

            # 입력 필드 비우기
            task_input.clear()

            # 사용자 요청 표시 (MessageRenderer 정적 메서드 사용)
            self.write_log("")
            user_panel = MessageRenderer.render_user_message(user_request)
            self.write_log(user_panel)
            self.write_log("")

            # 히스토리에 추가
            self.history.add_message("user", user_request)

            # Manager Agent 실행
            status_info.update("Running...")

            # Worker Tool 상태 업데이트 (시작)
            self.task_start_time = time.time()
            self.timer_active = True
            self.update_worker_status("🔄 Manager Agent 실행 중...")

            # Manager가 Worker Tools를 호출하여 작업 수행 (스트리밍)
            task_start_time = time.time()
            manager_response = ""

            # 스트리밍으로 실시간 출력 (MessageRenderer 인스턴스 사용)
            try:
                # MessageRenderer 상태 초기화
                self.message_renderer.reset_state()

                # AI 응답 시작 헤더 표시
                self.write_log(MessageRenderer.render_ai_response_start())
                self.write_log("")

                # output_log의 실제 너비 계산 (줄바꿈용)
                try:
                    output_log_widget = self.query_one("#output-log", RichLog)
                    available_width = output_log_widget.size.width
                    # OUTPUT_LOG_PADDING 사용 (매직 넘버 제거)
                    effective_width = max(
                        available_width - MessageRenderer.OUTPUT_LOG_PADDING,
                        MessageRenderer.MIN_OUTPUT_WIDTH
                    )
                except Exception:
                    effective_width = None  # 계산 실패 시 줄바꿈 비활성화

                async for chunk in self.manager.analyze_and_plan_stream(
                    self.history.get_history()
                ):
                    manager_response += chunk
                    # 모든 청크에 일관된 인덴트 적용 및 줄바꿈 (인스턴스 메서드 사용)
                    formatted_chunk = self.message_renderer.render_ai_response_chunk(
                        chunk, max_width=effective_width
                    )
                    self.write_log(formatted_chunk)

                # AI 응답 종료 구분선 표시
                self.write_log("")
                self.write_log(MessageRenderer.render_ai_response_end())
            except asyncio.CancelledError:
                # 사용자가 Ctrl+I로 중단
                self.write_log(f"\n[bold yellow]⚠️  작업이 사용자에 의해 중단되었습니다[/bold yellow]")
                self.timer_active = False
                self.update_worker_status("")
                return
            except Exception as stream_error:
                self.write_log(f"\n[bold red]❌ 스트리밍 에러: {stream_error}[/bold red]")
                import traceback
                self.write_log(f"[dim]{traceback.format_exc()}[/dim]")
                self.timer_active = False
                self.update_worker_status("")
                raise

            # Worker Tool 상태 업데이트 (종료)
            self.timer_active = False

            # 히스토리에 추가
            self.history.add_message("manager", manager_response)

            # 작업 완료 (컴팩트 버전)
            task_duration = time.time() - task_start_time

            # 세션 저장
            result = SessionResult(status=SessionStatus.COMPLETED)
            sessions_dir = Path("sessions")
            filepath = save_session_history(
                self.session_id,
                user_request,
                self.history,
                result.to_dict(),
                sessions_dir
            )

            # 메트릭 리포트 저장
            metrics_filepath = save_metrics_report(
                self.session_id,
                self.metrics_collector,
                sessions_dir,
                format="text"
            )

            # 컴팩트한 완료 메시지 (한 줄)
            completion_msg = f"[bold green]✅ 완료[/bold green] [dim]({task_duration:.1f}초)[/dim]"
            if metrics_filepath:
                completion_msg += f" [dim]• 세션: {filepath.name} • 메트릭: {metrics_filepath.name}[/dim]"
            else:
                completion_msg += f" [dim]• 세션: {filepath.name}[/dim]"

            self.write_log("")
            self.write_log(completion_msg)

            # 에러 통계 표시 (설정에 따라)
            if self.settings.show_error_stats_on_complete:
                self._display_error_statistics()
            else:
                # 에러 통계 안내 (한 번만)
                self.write_log("[dim]💡 Tip: F6 키로 에러 통계 확인 가능[/dim]")

            self.write_log("")

            worker_status.update(f"✅ 완료 ({task_duration:.1f}초)")
            status_info.update(f"Completed • {filepath.name}")

        except Exception as e:
            # 피드백 시스템 사용
            import traceback
            error_panel = TUIFeedbackWidget.create_panel(
                "작업 실행 중 오류가 발생했습니다",
                FeedbackType.ERROR,
                details=f"{str(e)}\n\n{traceback.format_exc()}"
            )
            self.write_log("")
            self.write_log(error_panel)
            self.write_log("")
            worker_status.update(f"❌ 오류")
            status_info.update("Error")

    async def handle_slash_command(self, command: str) -> None:
        """
        슬래시 커맨드 처리

        지원 커맨드:
        - /init: 현재 작업공간 분석하여 context 생성 및 새 세션 시작
        - /help: 도움말 표시
        - /clear: 로그 화면 지우기
        - /load <session_id>: 이전 세션 불러오기
        - /metrics: 메트릭 패널 토글
        - /search: 로그 검색
        """
        task_input = self.query_one("#task-input", MultilineInput)
        output_log = self.query_one("#output-log", RichLog)
        worker_status = self.query_one("#worker-status", Static)
        status_info = self.query_one("#status-info", Static)

        # 입력 필드 비우기
        task_input.clear()

        # 커맨드 파싱 (공백으로 분리)
        parts = command.strip().split()
        cmd = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []

        if cmd == '/help':
            # 도움말 표시
            await self.action_show_help()

        elif cmd == '/metrics':
            # 메트릭 패널 토글
            await self.action_toggle_metrics_panel()

        elif cmd == '/search':
            # 로그 검색
            await self.action_search_log()

        elif cmd == '/clear':
            # 로그 화면 지우기
            output_log.clear()
            self.log_lines.clear()
            # 피드백 시스템 사용
            success_panel = TUIFeedbackWidget.create_panel(
                "로그 화면이 지워졌습니다",
                FeedbackType.SUCCESS
            )
            self.write_log("")
            self.write_log(success_panel)
            self.write_log("")

        elif cmd == '/load':
            # 세션 불러오기 (Phase 3.1)
            if not args:
                # 피드백 시스템 사용
                warning_panel = TUIFeedbackWidget.create_panel(
                    "사용법: /load <session_id>",
                    FeedbackType.WARNING
                )
                self.write_log("")
                self.write_log(warning_panel)
                self.write_log("")
            else:
                session_id_to_load = args[0]
                await self.load_session(session_id_to_load)

        elif cmd == '/init':
            # /init 커맨드: 프로젝트 분석 및 context 생성
            try:
                self.write_log("")
                self.write_log(Panel(
                    "[bold cyan]🔍 프로젝트 분석 시작...[/bold cyan]",
                    border_style="cyan"
                ))
                self.write_log("")

                worker_status.update("🔍 프로젝트 구조 분석 중...")
                status_info.update("Analyzing...")

                # 프로젝트 루트 가져오기
                project_root = get_project_root()

                # 프로젝트 분석
                self.write_log("[dim]프로젝트 루트:[/dim] " + str(project_root))
                self.write_log("[dim]파일 스캔 중...[/dim]")

                analyzer = ProjectContextAnalyzer(project_root)
                context = analyzer.analyze()

                self.write_log("")
                self.write_log("[bold green]✅ 분석 완료[/bold green]")
                self.write_log("")

                # 분석 결과 표시
                result_table = Table(show_header=False, border_style="cyan", box=None, padding=(0, 2))
                result_table.add_column("항목", style="dim")
                result_table.add_column("값", style="white")

                result_table.add_row("프로젝트", context.project_name)
                result_table.add_row("언어", context.language)
                result_table.add_row("프레임워크", context.framework)
                result_table.add_row("아키텍처", context.architecture)
                result_table.add_row("의존성", f"{len(context.dependencies)}개 패키지")

                self.write_log(Panel(
                    result_table,
                    title="[bold cyan]분석 결과[/bold cyan]",
                    border_style="cyan"
                ))
                self.write_log("")

                # .context.json 저장
                self.write_log("[dim]컨텍스트 저장 중...[/dim]")
                worker_status.update("💾 컨텍스트 저장 중...")

                context_file = project_root / ".context.json"
                repo = JsonContextRepository(context_file)
                repo.save(context)

                self.write_log(f"[green]✅ 저장 완료:[/green] {context_file.name}")
                self.write_log("")

                # 새 세션 시작
                self.write_log("[dim]새 세션 시작...[/dim]")
                new_session_id = generate_session_id()
                new_session = SessionData(new_session_id)

                # 현재 세션 교체
                self.sessions[self.active_session_index] = new_session

                # 세션 ID 업데이트 (메트릭 수집용)
                update_session_id(self.session_id)
                set_metrics_collector(self.metrics_collector, self.session_id)

                # UI 업데이트
                self._update_status_bar()  # 터미널 크기 및 레이아웃 모드 포함

                self.write_log("")
                self.write_log(Panel(
                    f"[bold green]✅ 초기화 완료[/bold green]\n\n"
                    f"Session ID: {self.session_id}\n"
                    f"Context: {context.project_name} ({context.architecture})",
                    border_style="green"
                ))
                self.write_log("")

                worker_status.update("✅ 초기화 완료")
                status_info.update("Ready")

            except Exception as e:
                # 피드백 시스템 사용
                import traceback
                error_panel = TUIFeedbackWidget.create_panel(
                    "프로젝트 초기화 실패",
                    FeedbackType.ERROR,
                    details=f"{str(e)}\n\n{traceback.format_exc()}"
                )
                self.write_log("")
                self.write_log(error_panel)
                self.write_log("")
                worker_status.update(f"❌ 오류")
                status_info.update("Error")

        else:
            # 알 수 없는 커맨드 - 피드백 시스템 사용
            available_commands = (
                "사용 가능한 커맨드:\n"
                "  /help - 도움말 표시\n"
                "  /metrics - 메트릭 패널 토글\n"
                "  /search - 로그 검색\n"
                "  /init - 프로젝트 분석 및 context 초기화\n"
                "  /load <session_id> - 이전 세션 불러오기\n"
                "  /clear - 로그 화면 지우기"
            )
            warning_panel = TUIFeedbackWidget.create_panel(
                f"알 수 없는 커맨드: {cmd}",
                FeedbackType.WARNING,
                details=available_commands
            )
            self.write_log("")
            self.write_log(warning_panel)
            self.write_log("")

    async def action_new_session(self) -> None:
        """Ctrl+N: 새 세션 (현재 활성 세션을 새로 만듦)"""
        new_session_id = generate_session_id()
        new_session = SessionData(new_session_id)

        # 현재 세션 교체
        self.sessions[self.active_session_index] = new_session

        # 세션 ID 업데이트 (메트릭 수집용)
        update_session_id(self.session_id)
        set_metrics_collector(self.metrics_collector, self.session_id)

        # Manager Agent 토큰 사용량 초기화
        if self.manager:
            self.manager.reset_token_usage()

        # UI 업데이트
        status_info = self.query_one("#status-info", Static)
        self._update_status_bar()  # 터미널 크기 및 레이아웃 모드 포함

        output_log = self.query_one("#output-log", RichLog)
        output_log.clear()
        self.write_log("")
        self.write_log(f"[bold green]✅ 새 세션[/bold green] [dim]• ID: {self.session_id}[/dim]")
        self.write_log("")

        worker_status = self.query_one("#worker-status", Static)
        worker_status.update("✅ 준비 완료")
        status_info.update("Ready")

    def on_resize(self, event: events.Resize) -> None:
        """
        터미널 크기 변경 이벤트 핸들러

        터미널 크기가 변경될 때마다 호출되며, 레이아웃을 동적으로 조정합니다.

        Args:
            event: Resize 이벤트 (width, height 포함)
        """
        self.update_layout_for_size(event.size.width, event.size.height)

    def update_layout_for_size(self, width: int, height: int) -> None:
        """
        화면 크기에 따라 레이아웃 동적 조정

        반응형 브레이크포인트:
        - Large: width >= 120, height >= 30 (모든 패널 표시)
        - Medium: width >= 80, height >= 24 (메트릭 패널 토글 가능)
        - Small: width < 80 or height < 24 (메트릭 패널 자동 숨김, 경고)

        Args:
            width: 터미널 너비
            height: 터미널 높이
        """
        self.terminal_width = width
        self.terminal_height = height

        # 레이아웃 모드 결정
        old_mode = self.current_layout_mode

        if width >= 120 and height >= 30:
            self.current_layout_mode = LayoutMode.LARGE
        elif width >= 80 and height >= 24:
            self.current_layout_mode = LayoutMode.MEDIUM
        else:
            self.current_layout_mode = LayoutMode.SMALL

        # 레이아웃 모드가 변경된 경우에만 UI 업데이트
        if old_mode != self.current_layout_mode:
            self._apply_layout_mode()
            self._update_status_bar()

            # 레이아웃 변경 알림
            if self.settings.enable_notifications:
                self.notify(
                    f"레이아웃: {self.current_layout_mode.value} ({width}x{height})",
                    severity="information"
                )
        else:
            # 모드는 동일하지만 크기만 업데이트
            self._update_status_bar()

    def _apply_layout_mode(self) -> None:
        """
        현재 레이아웃 모드에 따라 UI 요소 조정

        - LARGE: 모든 패널 표시, 사용자 메트릭 설정 존중
        - MEDIUM: 메트릭 패널 토글 가능, 사용자 메트릭 설정 존중
        - SMALL: 메트릭 패널 강제 숨김, 경고 표시
        """
        try:
            # CSS 클래스 업데이트
            screen = self.screen
            screen.remove_class("layout-large")
            screen.remove_class("layout-medium")
            screen.remove_class("layout-small")

            if self.current_layout_mode == LayoutMode.LARGE:
                screen.add_class("layout-large")
                # 사용자 설정에 따라 메트릭 패널 표시
                if self.metrics_panel_hidden_by_layout:
                    self.metrics_panel_hidden_by_layout = False
                self.apply_metrics_panel_visibility()

            elif self.current_layout_mode == LayoutMode.MEDIUM:
                screen.add_class("layout-medium")
                # 사용자 설정에 따라 메트릭 패널 표시
                if self.metrics_panel_hidden_by_layout:
                    self.metrics_panel_hidden_by_layout = False
                self.apply_metrics_panel_visibility()

            elif self.current_layout_mode == LayoutMode.SMALL:
                screen.add_class("layout-small")
                # 메트릭 패널 강제 숨김
                metrics_container = self.query_one("#metrics-container", Container)
                if not metrics_container.has_class("hidden"):
                    self.metrics_panel_hidden_by_layout = True
                metrics_container.add_class("hidden")

                # 경고 메시지 표시 (최소 크기 미달)
                if self.terminal_width < 60 or self.terminal_height < 20:
                    worker_status = self.query_one("#worker-status", Static)
                    worker_status.update(
                        f"⚠️  터미널 크기가 너무 작습니다 ({self.terminal_width}x{self.terminal_height}). "
                        f"권장: 80x24 이상"
                    )

        except Exception as e:
            logger.warning(f"레이아웃 모드 적용 실패: {e}")

    def _update_status_bar(self) -> None:
        """
        상태바에 세션 탭 및 레이아웃 모드 표시

        형식: "[1*] [2] [3] • {session_id} • Layout: {mode} ({width}x{height})"
        """
        try:
            session_info = self.query_one("#session-info", Static)

            # 세션 탭 표시: [1*] [2] [3]
            session_tabs = []
            for i in range(3):
                if i < len(self.sessions):
                    # 세션이 존재하면
                    if i == self.active_session_index:
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
        """
        워크플로우 상태 업데이트 콜백

        Worker Tool 실행 시 호출되어 워크플로우 비주얼라이저를 업데이트합니다.

        Args:
            worker_name: Worker 이름 (예: "planner", "coder")
            status: 상태 ("running", "completed", "failed")
            error: 에러 메시지 (실패 시)
        """
        try:
            workflow_visualizer = self.query_one("#workflow-visualizer", WorkflowVisualizer)

            # 상태 문자열을 WorkerStatus enum으로 변환
            status_map = {
                "pending": WorkerStatus.PENDING,
                "running": WorkerStatus.RUNNING,
                "completed": WorkerStatus.COMPLETED,
                "failed": WorkerStatus.FAILED,
            }
            worker_status_enum = status_map.get(status, WorkerStatus.PENDING)

            # 워크플로우 비주얼라이저 업데이트
            workflow_visualizer.update_worker_status(
                worker_name=worker_name,
                status=worker_status_enum,
                error_message=error
            )

            # Worker 실행 시작 시 현재 Worker 이름 저장
            if status == "running":
                self.current_worker_name = worker_name
                # Worker 출력 화면 초기화
                try:
                    worker_output_log = self.query_one("#worker-output-log", RichLog)
                    worker_output_log.clear()
                    # 헤더 추가
                    worker_output_log.write(Panel(
                        f"[bold cyan]🤖 {worker_name.capitalize()} Worker[/bold cyan]",
                        border_style="cyan"
                    ))
                    worker_output_log.write("")
                except Exception:
                    pass

            # Worker 실행 완료/실패 시 현재 Worker 이름 초기화
            elif status in ["completed", "failed"]:
                self.current_worker_name = None

        except Exception as e:
            logger.warning(f"워크플로우 업데이트 실패: {e}")

    def on_worker_output(self, worker_name: str, chunk: str) -> None:
        """
        Worker 출력 스트리밍 콜백

        Worker Tool 실행 중 실시간으로 출력을 받아서 Worker 출력 화면에 표시합니다.

        Args:
            worker_name: Worker 이름 (예: "planner", "coder")
            chunk: 출력 청크
        """
        try:
            worker_output_log = self.query_one("#worker-output-log", RichLog)
            # 실시간으로 청크 출력
            worker_output_log.write(chunk)

        except Exception as e:
            logger.warning(f"Worker 출력 표시 실패: {e}")

    def update_worker_status_timer(self) -> None:
        """타이머: Worker Tool 실행 시간 업데이트 (0.5초마다 호출)"""
        if not self.timer_active or self.task_start_time is None:
            return

        try:
            elapsed = time.time() - self.task_start_time
            # 애니메이션 효과를 위한 스피너
            spinner_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
            spinner = spinner_frames[int(elapsed * 2) % len(spinner_frames)]

            # status-info에 실행 시간 표시
            status_info = self.query_one("#status-info", Static)
            status_info.update(f"{spinner} Running... ⏱️  {elapsed:.1f}s")

            # worker-status는 표시되어 있을 때만 업데이트
            if self.show_worker_status:
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
        """타이머: 메트릭 대시보드 업데이트 (1초마다 호출)"""
        try:
            metrics_panel = self.query_one("#metrics-panel", Static)

            # 세션 메트릭 조회
            session_metrics = self.metrics_collector.get_session_summary(self.session_id)

            if not session_metrics or not session_metrics.workers_metrics:
                metrics_panel.update("📊 메트릭 없음")
                return

            # 통계 테이블 생성
            stats_table = Table(
                show_header=True,
                header_style="bold cyan",
                border_style="dim",
                box=None,
                padding=(0, 1)
            )
            stats_table.add_column("Worker", style="cyan", width=12)
            stats_table.add_column("시도", justify="right", width=6)
            stats_table.add_column("성공", justify="right", width=6, style="green")
            stats_table.add_column("실패", justify="right", width=6, style="red")
            stats_table.add_column("성공률", justify="right", width=8)
            stats_table.add_column("평균시간", justify="right", width=10)

            # 모든 Worker 통계 조회
            all_stats = self.metrics_collector.get_all_workers_statistics(self.session_id)

            for worker_name, stats in all_stats.items():
                success_rate = stats["success_rate"]
                success_rate_style = (
                    "green" if success_rate >= 80
                    else "yellow" if success_rate >= 50
                    else "red"
                )

                stats_table.add_row(
                    worker_name.upper(),
                    str(stats["attempts"]),
                    str(stats["successes"]),
                    str(stats["failures"]),
                    f"[{success_rate_style}]{success_rate:.1f}%[/{success_rate_style}]",
                    f"{stats['avg_execution_time']:.2f}s",
                )

            # 세션 요약 추가
            total_duration = session_metrics.total_duration
            total_attempts = len(session_metrics.workers_metrics)
            overall_success_rate = session_metrics.get_success_rate()

            summary_text = (
                f"[bold]세션 요약[/bold]: "
                f"총 {total_attempts}회 실행, "
                f"소요시간 {total_duration:.1f}s, "
                f"성공률 {overall_success_rate:.1f}%"
            )

            # Rich 렌더링 (테이블 + 요약)
            from rich.console import Group
            content = Group(
                Text("📊 성능 메트릭", style="bold"),
                Text(""),
                stats_table,
                Text(""),
                Text.from_markup(summary_text),
            )

            metrics_panel.update(content)

        except Exception as e:
            # 메트릭 업데이트 실패는 로그만 남기고 무시
            logger.warning(f"메트릭 패널 업데이트 실패: {e}")

    async def action_interrupt_or_quit(self) -> None:
        """
        Ctrl+C: 3단계 로직
        1회: 입력 초기화
        2회: 작업 중단
        3회: 프로그램 종료
        """
        current_time = time.time()
        time_since_last_ctrl_c = current_time - self.last_ctrl_c_time

        task_input = self.query_one("#task-input", MultilineInput)
        output_log = self.query_one("#output-log", RichLog)
        worker_status = self.query_one("#worker-status", Static)
        status_info = self.query_one("#status-info", Static)

        # 2초 이상 지나면 카운터 리셋
        if time_since_last_ctrl_c >= 2.0:
            self.ctrl_c_count = 0

        self.ctrl_c_count += 1
        self.last_ctrl_c_time = current_time

        if self.ctrl_c_count == 1:
            # 1회: 입력 초기화 (로그 없이)
            task_input.clear()

        elif self.ctrl_c_count == 2:
            # 2회: 작업 중단
            if self.current_task and not self.current_task.done():
                self.current_task.cancel()
                self.write_log("")
                self.write_log(Panel(
                    "[bold yellow]⚠️  작업이 중단되었습니다[/bold yellow]\n\n"
                    "[dim]Ctrl+C를 다시 누르면 프로그램이 종료됩니다[/dim]",
                    border_style="yellow"
                ))
                self.write_log("")
                self.timer_active = False
                worker_status.update("⚠️  작업 중단됨")
                status_info.update("작업 중단 • Ctrl+C 다시 누르면 종료")
            else:
                # 작업이 없으면 즉시 종료 (메시지 없이)
                self.exit()

        else:  # self.ctrl_c_count >= 3
            # 3회: 프로그램 종료
            self.write_log("")
            self.write_log(Panel(
                "[bold]👋 프로그램을 종료합니다...[/bold]",
                border_style="dim"
            ))
            self.write_log("")
            self.exit()

    # ==================== 새로운 액션 메서드 (Phase 1-4) ====================

    async def action_history_up(self) -> None:
        """↑ 키: 히스토리 이전 항목으로 이동"""
        try:
            task_input = self.query_one("#task-input", MultilineInput)
            previous = self.input_history.navigate_up(task_input.text)
            if previous is not None:
                task_input.load_text(previous)
                # 커서를 텍스트 끝으로 이동 (충분히 큰 값 사용)
                task_input.move_cursor_relative(rows=1000, columns=1000)
        except Exception:
            pass

    async def action_history_down(self) -> None:
        """↓ 키: 히스토리 다음 항목으로 이동"""
        try:
            task_input = self.query_one("#task-input", MultilineInput)
            next_item = self.input_history.navigate_down()
            if next_item is not None:
                task_input.load_text(next_item)
                # 커서를 텍스트 끝으로 이동 (충분히 큰 값 사용)
                task_input.move_cursor_relative(rows=1000, columns=1000)
        except Exception:
            pass

    async def on_multiline_input_history_up(
        self, message: MultilineInput.HistoryUp
    ) -> None:
        """
        MultilineInput에서 발생한 HistoryUp 메시지 처리.

        Args:
            message: HistoryUp 메시지
        """
        await self.action_history_up()

    async def on_multiline_input_history_down(
        self, message: MultilineInput.HistoryDown
    ) -> None:
        """
        MultilineInput에서 발생한 HistoryDown 메시지 처리.

        Args:
            message: HistoryDown 메시지
        """
        await self.action_history_down()

    async def on_multiline_input_autocomplete_requested(
        self, message: MultilineInput.AutocompleteRequested
    ) -> None:
        """
        MultilineInput에서 발생한 AutocompleteRequested 메시지 처리.

        Tab 키를 누르면 자동 완성을 수행하고, 여러 후보가 있으면 순환합니다.

        Args:
            message: AutocompleteRequested 메시지
        """
        try:
            task_input = self.query_one("#task-input", MultilineInput)
            autocomplete_preview = self.query_one("#autocomplete-preview", Static)

            current_text = message.current_text.strip()

            # 빈 입력이면 자동 완성 비활성화
            if not current_text:
                autocomplete_preview.add_class("hidden")
                self.autocomplete_engine.reset()
                return

            # 자동 완성 수행 (순환 모드)
            completed_text = self.autocomplete_engine.complete(current_text, cycle=True)

            if completed_text:
                # 입력 텍스트 업데이트
                task_input.load_text(completed_text)
                # 커서를 텍스트 끝으로 이동
                task_input.move_cursor_relative(rows=1000, columns=1000)

                # 미리보기 업데이트
                preview_text = self.autocomplete_engine.get_preview()
                if preview_text:
                    autocomplete_preview.update(f"[dim]{preview_text}[/dim]")
                    autocomplete_preview.remove_class("hidden")
                else:
                    autocomplete_preview.add_class("hidden")
            else:
                # 자동 완성 후보가 없으면 미리보기 숨김
                autocomplete_preview.add_class("hidden")

        except Exception as e:
            logger.warning(f"자동 완성 처리 실패: {e}")

    async def action_show_help(self) -> None:
        """F1 키: 도움말 모달 표시"""
        try:
            await self.push_screen(HelpModal())
        except Exception as e:
            logger.error(f"도움말 표시 실패: {e}")

    async def action_show_settings(self) -> None:
        """F2 키: 설정 모달 표시"""
        try:
            result = await self.push_screen(SettingsModal(self.settings))
            if result:
                # 설정이 변경됨
                self.settings = result
                # 히스토리 크기 업데이트
                self.input_history = InputHistory(max_size=self.settings.max_history_size)
                # 패널 표시 상태 업데이트
                self.show_metrics_panel = self.settings.show_metrics_panel
                self.show_workflow_panel = self.settings.show_workflow_panel
                self.show_worker_status = self.settings.show_worker_status
                self.apply_metrics_panel_visibility()
                self.apply_workflow_panel_visibility()
                self.apply_worker_status_visibility()
                # 알림 표시
                if self.settings.enable_notifications:
                    self.notify("설정이 저장되었습니다", severity="information")
        except Exception as e:
            logger.error(f"설정 표시 실패: {e}")

    async def action_toggle_metrics_panel(self) -> None:
        """
        F3 키: 메트릭 패널 표시/숨김 토글

        메트릭 패널의 표시 상태를 토글하고, 변경된 설정을 파일에 저장합니다.
        설정 저장에 실패하면 경고 로그를 남기고 사용자에게 알림을 표시합니다.

        Raises:
            Exception: 메트릭 패널 토글 중 예상치 못한 오류 발생 시
        """
        try:
            # 상태 토글
            self.show_metrics_panel = not self.show_metrics_panel

            # UI 업데이트
            self.apply_metrics_panel_visibility()

            # 설정 저장
            self.settings.show_metrics_panel = self.show_metrics_panel
            save_success = TUIConfig.save(self.settings)

            # 저장 실패 시 경고
            if not save_success:
                logger.warning("메트릭 패널 설정 저장 실패")
                if self.settings.notify_on_error:
                    self.notify("설정 저장 실패", severity="warning")

            # 알림 표시
            if self.settings.enable_notifications:
                status_msg = "표시" if self.show_metrics_panel else "숨김"
                self.notify(f"메트릭 패널: {status_msg}", severity="information")

        except Exception as e:
            logger.error(f"메트릭 패널 토글 실패: {e}")

    async def action_toggle_workflow_panel(self) -> None:
        """
        F4 키: 워크플로우 패널 표시/숨김 토글

        워크플로우 패널의 표시 상태를 토글하고, 변경된 설정을 파일에 저장합니다.

        Raises:
            Exception: 워크플로우 패널 토글 중 예상치 못한 오류 발생 시
        """
        try:
            # 상태 토글
            self.show_workflow_panel = not self.show_workflow_panel

            # UI 업데이트
            self.apply_workflow_panel_visibility()

            # 설정 저장
            self.settings.show_workflow_panel = self.show_workflow_panel
            save_success = TUIConfig.save(self.settings)

            # 저장 실패 시 경고
            if not save_success:
                logger.warning("워크플로우 패널 설정 저장 실패")
                if self.settings.notify_on_error:
                    self.notify("설정 저장 실패", severity="warning")

            # 알림 표시
            if self.settings.enable_notifications:
                status_msg = "표시" if self.show_workflow_panel else "숨김"
                self.notify(f"워크플로우 패널: {status_msg}", severity="information")

        except Exception as e:
            logger.error(f"워크플로우 패널 토글 실패: {e}")

    async def action_toggle_worker_status(self) -> None:
        """
        F5 키: Worker 상태 패널 표시/숨김 토글

        Worker 상태 패널의 표시 상태를 토글하고, 변경된 설정을 파일에 저장합니다.

        Raises:
            Exception: Worker 상태 패널 토글 중 예상치 못한 오류 발생 시
        """
        try:
            # 상태 토글
            self.show_worker_status = not self.show_worker_status

            # UI 업데이트
            self.apply_worker_status_visibility()

            # 설정 저장
            self.settings.show_worker_status = self.show_worker_status
            save_success = TUIConfig.save(self.settings)

            # 저장 실패 시 경고
            if not save_success:
                logger.warning("Worker 상태 패널 설정 저장 실패")
                if self.settings.notify_on_error:
                    self.notify("설정 저장 실패", severity="warning")

            # 알림 표시
            if self.settings.enable_notifications:
                status_msg = "표시" if self.show_worker_status else "숨김"
                self.notify(f"Worker 상태 패널: {status_msg}", severity="information")

        except Exception as e:
            logger.error(f"Worker 상태 패널 토글 실패: {e}")

    async def action_toggle_output_mode(self) -> None:
        """
        Ctrl+O: 출력 모드 전환 (Manager <-> Worker)

        Manager 출력과 Worker 출력을 전환합니다.
        Worker가 실행 중이지 않으면 경고 메시지를 표시합니다.
        """
        try:
            # 출력 모드 토글
            if self.output_mode == "manager":
                # Worker 출력으로 전환
                if self.current_worker_name:
                    self.output_mode = "worker"
                    self.apply_output_mode()
                    # 알림 표시
                    if self.settings.enable_notifications:
                        self.notify(
                            f"출력 모드: Worker ({self.current_worker_name.capitalize()})",
                            severity="information"
                        )
                else:
                    # Worker가 실행 중이지 않으면 경고
                    if self.settings.enable_notifications:
                        self.notify(
                            "실행 중인 Worker가 없습니다",
                            severity="warning"
                        )
            else:
                # Manager 출력으로 전환
                self.output_mode = "manager"
                self.apply_output_mode()
                # 알림 표시
                if self.settings.enable_notifications:
                    self.notify("출력 모드: Manager", severity="information")

        except Exception as e:
            logger.error(f"출력 모드 토글 실패: {e}")

    def apply_output_mode(self) -> None:
        """
        현재 출력 모드에 따라 출력 화면 표시/숨김 적용
        """
        try:
            output_container = self.query_one("#output-container", ScrollableContainer)
            worker_output_container = self.query_one("#worker-output-container", ScrollableContainer)

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
        """Ctrl+S: 로그 저장"""
        try:
            output_log = self.query_one("#output-log", RichLog)
            status_info = self.query_one("#status-info", Static)

            # 로그 내보내기
            log_dir = Path(self.settings.log_export_dir)
            if self.settings.log_export_format == "markdown":
                filepath = LogExporter.export_to_markdown(
                    self.log_lines,
                    self.session_id,
                    log_dir
                )
            else:
                filepath = LogExporter.export_to_file(
                    self.log_lines,
                    self.session_id,
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

            # 새 세션 생성 및 히스토리 복원
            loaded_session = SessionData(session_id)
            for msg in session_data.get("history", []):
                loaded_session.history.add_message(msg["role"], msg["content"])

            # 현재 세션 교체
            self.sessions[self.active_session_index] = loaded_session

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
        """F6 키: 에러 통계 표시"""
        self._display_error_statistics()

    async def action_switch_to_session_1(self) -> None:
        """Ctrl+1: 세션 1로 전환"""
        await self.switch_to_session(0)

    async def action_switch_to_session_2(self) -> None:
        """Ctrl+2: 세션 2로 전환"""
        await self.switch_to_session(1)

    async def action_switch_to_session_3(self) -> None:
        """Ctrl+3: 세션 3로 전환"""
        await self.switch_to_session(2)

    async def switch_to_session(self, index: int) -> None:
        """
        세션 전환 (0, 1, 2)

        Args:
            index: 세션 인덱스 (0=Ctrl+1, 1=Ctrl+2, 2=Ctrl+3)
        """
        try:
            # 세션이 아직 없으면 생성
            while len(self.sessions) <= index:
                new_session_id = generate_session_id()
                self.sessions.append(SessionData(new_session_id))

            # 이미 현재 세션이면 무시
            if self.active_session_index == index:
                if self.settings.enable_notifications:
                    self.notify(f"이미 세션 {index + 1}입니다", severity="information")
                return

            # 세션 전환
            old_index = self.active_session_index
            self.active_session_index = index

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


def main():
    """메인 함수"""
    # 구조화된 로깅 설정
    from src.infrastructure.logging import configure_structlog

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

    # 앱 실행
    app = OrchestratorTUI()
    app.run()


if __name__ == "__main__":
    main()
