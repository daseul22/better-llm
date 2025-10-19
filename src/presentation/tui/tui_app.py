#!/usr/bin/env python3
"""
그룹 챗 오케스트레이션 시스템 - TUI (Claude Code 스타일)

터미널에서 Claude Code처럼 사용할 수 있는 인터랙티브 인터페이스
"""

import asyncio
import time
import logging
from pathlib import Path
from typing import Optional, List, Tuple, Any

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, ScrollableContainer, Horizontal
from textual.widgets import Footer, Input, Static, RichLog, Header
from textual.binding import Binding
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
    update_session_id
)
from src.infrastructure.config import (
    validate_environment,
    get_project_root,
)
from src.infrastructure.storage import JsonContextRepository, InMemoryMetricsRepository
from ..cli.utils import (
    generate_session_id,
    save_session_history,
    validate_user_input,
    sanitize_user_input,
    save_metrics_report,
)
from .widgets import HelpModal, SearchModal
from .widgets.settings_modal import SettingsModal
from .widgets.search_input import SearchHighlighter
from .utils import InputHistory, LogExporter, AutocompleteEngine, TUIConfig, TUISettings

logger = logging.getLogger(__name__)


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
        margin: 1 1 0 1;
        padding: 0;
    }

    #output-log {
        height: 1fr;
        background: #0d1117;
        padding: 1;
        scrollbar-gutter: stable;
    }

    /* Worker 상태 표시 */
    #worker-status-container {
        height: auto;
        margin: 1 1 0 1;
        background: transparent;
        border: round #21262d;
        padding: 0;
    }

    #worker-status {
        background: transparent;
        color: #8b949e;
        padding: 1 2;
        height: auto;
    }

    /* 메트릭 대시보드 */
    #metrics-container {
        height: auto;
        margin: 1 1 0 1;
        background: transparent;
        border: round #21262d;
        padding: 0;
    }

    #metrics-panel {
        background: transparent;
        color: #8b949e;
        padding: 1 2;
        height: auto;
    }

    /* 입력 영역 */
    #input-container {
        height: auto;
        background: transparent;
        border: round #388bfd;
        margin: 1 1 0 1;
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
        width: 1fr;
    }

    #status-info {
        text-align: right;
        width: 1fr;
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
    """

    BINDINGS = [
        Binding("ctrl+c", "interrupt_or_quit", "중단/종료"),
        Binding("ctrl+n", "new_session", "새 세션"),
        Binding("ctrl+s", "save_log", "로그 저장"),
        Binding("ctrl+f", "search_log", "로그 검색"),
        Binding("f1", "show_help", "도움말"),
        Binding("f2", "show_settings", "설정"),
        Binding("f3", "toggle_metrics_panel", "메트릭"),
        Binding("up", "history_up", "이전 입력", show=False),
        Binding("down", "history_down", "다음 입력", show=False),
    ]

    def __init__(self):
        super().__init__()
        self.session_id = generate_session_id()
        self.manager: Optional[ManagerAgent] = None
        self.history: Optional[ConversationHistory] = None
        self.initialized = False
        self.start_time = time.time()
        self.current_task = None  # 현재 실행 중인 asyncio Task
        self.task_start_time = None  # 작업 시작 시간
        self.timer_active = False  # 타이머 활성화 여부
        self.last_ctrl_c_time = 0  # 마지막 Ctrl+C 누른 시간

        # 메트릭 수집
        self.metrics_repository = InMemoryMetricsRepository()
        self.metrics_collector = MetricsCollector(self.metrics_repository)

        # 새로운 기능 - Phase 1~4
        self.input_history = InputHistory(max_size=100)  # 히스토리 네비게이션
        self.settings = TUIConfig.load()  # 설정 로드
        self.log_lines: List[str] = []  # 로그 버퍼 (검색 및 저장용)
        self.search_query: Optional[str] = None  # 현재 검색어
        self.show_metrics_panel: bool = self.settings.show_metrics_panel  # 메트릭 패널 표시 여부

    def compose(self) -> ComposeResult:
        """UI 구성"""
        # 출력 영역
        with ScrollableContainer(id="output-container"):
            yield RichLog(id="output-log", markup=True, highlight=True)

        # Worker 상태 표시
        with Container(id="worker-status-container"):
            yield Static("⏳ 초기화 중...", id="worker-status")

        # 메트릭 대시보드
        with Container(id="metrics-container"):
            yield Static("📊 메트릭 없음", id="metrics-panel")

        # 입력 영역
        with Container(id="input-container"):
            yield Input(
                placeholder="작업을 입력하세요...",
                id="task-input"
            )

        # 하단 정보바
        with Horizontal(id="info-bar"):
            yield Static(f"Session: {self.session_id}", id="session-info")
            yield Static("Ready", id="status-info")

        yield Footer()

    async def on_mount(self) -> None:
        """앱 마운트 시 초기화"""
        await self.initialize_orchestrator()
        # 타이머: 0.5초마다 Worker Tool 실행 시간 업데이트
        self.set_interval(0.5, self.update_worker_status_timer)
        # 타이머: 1초마다 메트릭 대시보드 업데이트
        self.set_interval(1.0, self.update_metrics_panel)
        # 메트릭 패널 초기 상태 적용
        self.apply_metrics_panel_visibility()

    async def initialize_orchestrator(self) -> None:
        """오케스트레이터 초기화"""
        worker_status = self.query_one("#worker-status", Static)
        status_info = self.query_one("#status-info", Static)
        output_log = self.query_one("#output-log", RichLog)

        try:
            worker_status.update("⏳ 초기화 중...")
            status_info.update("Initializing...")

            # Welcome 메시지
            self.write_log("")
            self.write_log(Panel(
                "[bold]AI Orchestration System[/bold]\n\n"
                "[dim]Manager Agent + Worker Tools Architecture[/dim]",
                border_style="blue"
            ))
            self.write_log("")

            # 환경 검증
            validate_environment()
            self.write_log("✅ [green]환경 검증 완료[/green]")

            # Worker Agent들 초기화 (프로젝트 루트 기준)
            config_path = get_project_root() / "config" / "agent_config.json"
            initialize_workers(config_path)
            self.write_log("✅ [green]Worker Agents 초기화[/green] [dim](Planner, Coder, Reviewer, Tester)[/dim]")

            # Worker Tools MCP Server 생성
            worker_tools_server = create_worker_tools_server()
            self.write_log("✅ [green]Worker Tools MCP Server 생성[/green]")

            # Manager Agent 초기화
            self.manager = ManagerAgent(worker_tools_server)
            self.write_log("✅ [green]Manager Agent 준비 완료[/green]")

            # 대화 히스토리
            self.history = ConversationHistory()

            # 메트릭 컬렉터 설정
            set_metrics_collector(self.metrics_collector, self.session_id)
            self.write_log("✅ [green]메트릭 수집기 준비 완료[/green]")

            self.initialized = True
            worker_status.update("✅ 준비 완료")
            status_info.update("Ready")

            self.write_log("")
            self.write_log(Panel(
                "[bold green]✅ 시스템 준비 완료[/bold green]\n\n"
                "[dim]사용 가능한 Worker Tools:[/dim]\n"
                "  • execute_planner_task - 요구사항 분석 및 계획 수립\n"
                "  • execute_coder_task - 코드 작성 및 수정\n"
                "  • execute_reviewer_task - 코드 리뷰 및 품질 검증\n"
                "  • execute_tester_task - 테스트 작성 및 실행\n\n"
                "[dim]작업을 입력하고 Enter를 눌러 시작하세요.[/dim]",
                border_style="green"
            ))
            self.write_log("")

        except Exception as e:
            self.write_log(f"[red]❌ 초기화 실패: {e}[/red]")
            worker_status.update(f"❌ 오류: {e}")
            status_info.update("Error")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
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

    async def run_task(self, user_request: str) -> None:
        """작업 실행 - Manager가 Worker Tools를 자동으로 호출"""
        task_input = self.query_one("#task-input", Input)
        output_log = self.query_one("#output-log", RichLog)
        worker_status = self.query_one("#worker-status", Static)
        status_info = self.query_one("#status-info", Static)

        try:
            # 입력 검증
            is_valid, error_msg = validate_user_input(user_request)
            if not is_valid:
                self.write_log("")
                self.write_log(Panel(
                    f"[bold red]❌ 입력 검증 실패[/bold red]\n\n{error_msg}",
                    border_style="red"
                ))
                self.write_log("")
                task_input.value = ""
                return

            # 입력 정제
            user_request = sanitize_user_input(user_request)

            # 입력 필드 비우기
            task_input.value = ""

            # 사용자 요청 표시
            self.write_log("")
            self.write_log(Panel(
                f"[bold]💬 {user_request}[/bold]",
                border_style="blue"
            ))
            self.write_log("")

            # 히스토리에 추가
            self.history.add_message("user", user_request)

            # Manager Agent 실행
            status_info.update("Running...")
            self.write_log("[bold yellow]🤖 Manager Agent[/bold yellow]")
            self.write_log("[dim]" + "─" * 60 + "[/dim]")
            self.write_log("")

            # Worker Tool 상태 업데이트 (시작)
            self.task_start_time = time.time()
            self.timer_active = True
            self.update_worker_status("🔄 Manager Agent 실행 중...")

            # Manager가 Worker Tools를 호출하여 작업 수행 (스트리밍)
            task_start_time = time.time()
            manager_response = ""

            # 스트리밍으로 실시간 출력
            try:
                async for chunk in self.manager.analyze_and_plan_stream(
                    self.history.get_history()
                ):
                    manager_response += chunk
                    # 실시간으로 텍스트 출력
                    # RichLog.write()는 'end' 파라미터를 지원하지 않음
                    self.write_log(chunk)
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

            self.write_log("")
            self.write_log("[dim]" + "─" * 60 + "[/dim]")
            self.write_log("")

            # 히스토리에 추가
            self.history.add_message("manager", manager_response)

            # 작업 완료
            task_duration = time.time() - task_start_time
            self.write_log(Panel(
                f"[bold green]✅ 작업 완료[/bold green]\n\n"
                f"⏱️  소요 시간: {task_duration:.1f}초",
                border_style="green"
            ))
            self.write_log("")

            # 에러 통계 표시
            error_stats = get_error_statistics()
            if error_stats:
                stats_table = Table(show_header=True, header_style="bold cyan", border_style="dim")
                stats_table.add_column("Worker", style="cyan", width=15)
                stats_table.add_column("시도", justify="right", width=8)
                stats_table.add_column("성공", justify="right", width=8, style="green")
                stats_table.add_column("실패", justify="right", width=8, style="red")
                stats_table.add_column("에러율", justify="right", width=10)

                for worker_name, data in error_stats.items():
                    error_rate_style = "red" if data['error_rate'] > 20 else "yellow" if data['error_rate'] > 0 else "green"
                    stats_table.add_row(
                        worker_name.upper(),
                        str(data['attempts']),
                        str(data['successes']),
                        str(data['failures']),
                        f"[{error_rate_style}]{data['error_rate']}%[/{error_rate_style}]"
                    )

                self.write_log(Panel(
                    stats_table,
                    border_style="dim"
                ))
                self.write_log("")

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
            if metrics_filepath:
                self.write_log(f"[dim]메트릭 리포트 저장: {metrics_filepath.name}[/dim]")

            worker_status.update(f"✅ 완료 ({task_duration:.1f}초)")
            status_info.update(f"Completed • {filepath.name}")

        except Exception as e:
            self.write_log("")
            self.write_log(Panel(
                f"[bold red]❌ 오류 발생[/bold red]\n\n{str(e)}",
                border_style="red"
            ))
            self.write_log("")
            worker_status.update(f"❌ 오류")
            status_info.update("Error")
            import traceback
            self.write_log(f"[dim]{traceback.format_exc()}[/dim]")

    async def handle_slash_command(self, command: str) -> None:
        """
        슬래시 커맨드 처리

        지원 커맨드:
        - /init: 현재 작업공간 분석하여 context 생성 및 새 세션 시작
        - /help: 도움말 표시
        - /clear: 로그 화면 지우기
        - /load <session_id>: 이전 세션 불러오기
        """
        task_input = self.query_one("#task-input", Input)
        output_log = self.query_one("#output-log", RichLog)
        worker_status = self.query_one("#worker-status", Static)
        status_info = self.query_one("#status-info", Static)

        # 입력 필드 비우기
        task_input.value = ""

        # 커맨드 파싱 (공백으로 분리)
        parts = command.strip().split()
        cmd = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []

        if cmd == '/help':
            # 도움말 표시
            await self.action_show_help()

        elif cmd == '/clear':
            # 로그 화면 지우기
            output_log.clear()
            self.log_lines.clear()
            self.write_log("")
            self.write_log(Panel(
                "[bold green]✅ 로그 화면이 지워졌습니다[/bold green]",
                border_style="green"
            ))
            self.write_log("")

        elif cmd == '/load':
            # 세션 불러오기 (Phase 3.1)
            if not args:
                self.write_log("")
                self.write_log(Panel(
                    "[bold yellow]⚠️  사용법: /load <session_id>[/bold yellow]",
                    border_style="yellow"
                ))
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
                self.session_id = generate_session_id()
                self.history = ConversationHistory()
                self.start_time = time.time()

                # 세션 ID 업데이트 (메트릭 수집용)
                update_session_id(self.session_id)

                # UI 업데이트
                session_info = self.query_one("#session-info", Static)
                session_info.update(f"Session: {self.session_id}")

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
                self.write_log("")
                self.write_log(Panel(
                    f"[bold red]❌ 초기화 실패[/bold red]\n\n{str(e)}",
                    border_style="red"
                ))
                self.write_log("")
                worker_status.update(f"❌ 오류")
                status_info.update("Error")
                import traceback
                self.write_log(f"[dim]{traceback.format_exc()}[/dim]")

        else:
            # 알 수 없는 커맨드
            self.write_log("")
            self.write_log(Panel(
                f"[bold yellow]⚠️  알 수 없는 커맨드: {cmd}[/bold yellow]\n\n"
                f"사용 가능한 커맨드:\n"
                f"  /help - 도움말 표시\n"
                f"  /init - 프로젝트 분석 및 context 초기화\n"
                f"  /load <session_id> - 이전 세션 불러오기\n"
                f"  /clear - 로그 화면 지우기",
                border_style="yellow"
            ))
            self.write_log("")

    async def action_new_session(self) -> None:
        """Ctrl+N: 새 세션"""
        self.session_id = generate_session_id()
        self.history = ConversationHistory()
        self.start_time = time.time()

        # 세션 ID 업데이트 (메트릭 수집용)
        update_session_id(self.session_id)

        # UI 업데이트
        session_info = self.query_one("#session-info", Static)
        status_info = self.query_one("#status-info", Static)
        session_info.update(f"Session: {self.session_id}")

        output_log = self.query_one("#output-log", RichLog)
        output_log.clear()
        self.write_log("")
        self.write_log(Panel(
            f"[bold green]✅ 새 세션 시작[/bold green]\n\n"
            f"Session ID: {self.session_id}",
            border_style="green"
        ))
        self.write_log("")

        worker_status = self.query_one("#worker-status", Static)
        worker_status.update("✅ 준비 완료")
        status_info.update("Ready")

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

    def update_worker_status_timer(self) -> None:
        """타이머: Worker Tool 실행 시간 업데이트 (0.5초마다 호출)"""
        if not self.timer_active or self.task_start_time is None:
            return

        elapsed = time.time() - self.task_start_time
        # 애니메이션 효과를 위한 스피너
        spinner_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        spinner = spinner_frames[int(elapsed * 2) % len(spinner_frames)]

        self.update_worker_status(f"{spinner} Manager Agent 실행 중... ⏱️  {elapsed:.1f}s")

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
        """Ctrl+C: 1번 누르면 작업 중단, 2초 내 2번 누르면 프로세스 종료"""
        current_time = time.time()
        time_since_last_ctrl_c = current_time - self.last_ctrl_c_time

        output_log = self.query_one("#output-log", RichLog)
        worker_status = self.query_one("#worker-status", Static)
        status_info = self.query_one("#status-info", Static)

        # 2초 이내에 다시 누르면 종료
        if time_since_last_ctrl_c < 2.0:
            self.write_log("")
            self.write_log(Panel(
                "[bold]👋 프로그램을 종료합니다...[/bold]",
                border_style="dim"
            ))
            self.write_log("")
            self.exit()
            return

        # 첫 번째 Ctrl+C: 작업 중단
        self.last_ctrl_c_time = current_time

        if self.current_task and not self.current_task.done():
            self.current_task.cancel()
            self.write_log("")
            self.write_log(Panel(
                "[bold yellow]⚠️  작업이 중단되었습니다[/bold yellow]\n\n"
                "[dim]다시 Ctrl+C를 누르면 프로그램이 종료됩니다[/dim]",
                border_style="yellow"
            ))
            self.write_log("")
            self.timer_active = False
            worker_status.update("⚠️  작업 중단됨")
            status_info.update("Interrupted")
        else:
            self.write_log("")
            self.write_log(Panel(
                "[bold]ℹ️  실행 중인 작업이 없습니다[/bold]\n\n"
                "[dim]다시 Ctrl+C를 누르면 프로그램이 종료됩니다[/dim]",
                border_style="dim"
            ))
            self.write_log("")
            worker_status.update("ℹ️  작업 없음")
            status_info.update("Idle")

    # ==================== 새로운 액션 메서드 (Phase 1-4) ====================

    async def action_history_up(self) -> None:
        """↑ 키: 히스토리 이전 항목으로 이동"""
        try:
            task_input = self.query_one("#task-input", Input)
            previous = self.input_history.navigate_up(task_input.value)
            if previous is not None:
                task_input.value = previous
                # 커서를 끝으로 이동
                task_input.cursor_position = len(previous)
        except Exception:
            pass

    async def action_history_down(self) -> None:
        """↓ 키: 히스토리 다음 항목으로 이동"""
        try:
            task_input = self.query_one("#task-input", Input)
            next_item = self.input_history.navigate_down()
            if next_item is not None:
                task_input.value = next_item
                # 커서를 끝으로 이동
                task_input.cursor_position = len(next_item)
        except Exception:
            pass

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
                self.write_log(Panel(
                    f"[bold red]❌ 세션을 찾을 수 없습니다[/bold red]\n\n"
                    f"Session ID: {session_id}",
                    border_style="red"
                ))
                self.write_log("")
                return

            # 가장 최근 파일 선택
            session_file = max(session_files, key=lambda p: p.stat().st_mtime)

            # 세션 데이터 로드
            import json
            with open(session_file, "r", encoding="utf-8") as f:
                session_data = json.load(f)

            # 히스토리 복원
            self.history = ConversationHistory()
            for msg in session_data.get("history", []):
                self.history.add_message(msg["role"], msg["content"])

            # 세션 ID 업데이트
            self.session_id = session_id
            update_session_id(session_id)

            # UI 업데이트
            session_info = self.query_one("#session-info", Static)
            session_info.update(f"Session: {session_id}")

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
            self.write_log("")
            self.write_log(Panel(
                f"[bold red]❌ 세션 불러오기 실패[/bold red]\n\n{str(e)}",
                border_style="red"
            ))
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

        self.log_lines.append(content_str)

        # 최대 라인 수 제한
        max_lines = self.settings.max_log_lines
        if len(self.log_lines) > max_lines:
            # 오래된 라인 제거
            self.log_lines = self.log_lines[-max_lines:]

    def write_log(self, content: Any, widget_id: str = "output-log") -> None:
        """
        로그 출력 및 추적 헬퍼 메서드

        Args:
            content: 출력할 내용 (Any 타입)
            widget_id: RichLog 위젯 ID
        """
        try:
            output_log = self.query_one(f"#{widget_id}", RichLog)
            output_log.write(content)
            # 로그 버퍼에도 추가
            self._track_log_output(str(content))
        except Exception:
            pass


def main():
    """메인 함수"""
    app = OrchestratorTUI()
    app.run()


if __name__ == "__main__":
    main()
