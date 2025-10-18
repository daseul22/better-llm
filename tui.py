#!/usr/bin/env python3
"""
그룹 챗 오케스트레이션 시스템 - TUI (Claude Code 스타일)

터미널에서 Claude Code처럼 사용할 수 있는 인터랙티브 인터페이스
"""

import asyncio
import time
from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, ScrollableContainer, Horizontal
from textual.widgets import Footer, Input, Static, RichLog, Header
from textual.binding import Binding
from rich.panel import Panel
from rich.markdown import Markdown
from rich.text import Text
from rich.table import Table

from src.models import SessionResult
from src.manager_agent import ManagerAgent
from src.worker_tools import (
    initialize_workers,
    create_worker_tools_server,
    get_error_statistics
)
from src.conversation import ConversationHistory
from src.utils import (
    generate_session_id,
    save_session_history,
    validate_environment,
    validate_user_input,
    sanitize_user_input,
    get_project_root
)


class OrchestratorTUI(App):
    """전문적인 오케스트레이션 TUI 애플리케이션"""

    CSS = """
    Screen {
        background: #0d1117;
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

    def compose(self) -> ComposeResult:
        """UI 구성"""
        # 출력 영역
        with ScrollableContainer(id="output-container"):
            yield RichLog(id="output-log", markup=True, highlight=True)

        # Worker 상태 표시
        with Container(id="worker-status-container"):
            yield Static("⏳ 초기화 중...", id="worker-status")

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

    async def initialize_orchestrator(self) -> None:
        """오케스트레이터 초기화"""
        worker_status = self.query_one("#worker-status", Static)
        status_info = self.query_one("#status-info", Static)
        output_log = self.query_one("#output-log", RichLog)

        try:
            worker_status.update("⏳ 초기화 중...")
            status_info.update("Initializing...")

            # Welcome 메시지
            output_log.write("")
            output_log.write(Panel(
                "[bold]AI Orchestration System[/bold]\n\n"
                "[dim]Manager Agent + Worker Tools Architecture[/dim]",
                border_style="blue"
            ))
            output_log.write("")

            # 환경 검증
            validate_environment()
            output_log.write("✅ [green]환경 검증 완료[/green]")

            # Worker Agent들 초기화 (프로젝트 루트 기준)
            config_path = get_project_root() / "config" / "agent_config.json"
            initialize_workers(config_path)
            output_log.write("✅ [green]Worker Agents 초기화[/green] [dim](Planner, Coder, Reviewer, Tester)[/dim]")

            # Worker Tools MCP Server 생성
            worker_tools_server = create_worker_tools_server()
            output_log.write("✅ [green]Worker Tools MCP Server 생성[/green]")

            # Manager Agent 초기화
            self.manager = ManagerAgent(worker_tools_server)
            output_log.write("✅ [green]Manager Agent 준비 완료[/green]")

            # 대화 히스토리
            self.history = ConversationHistory()

            self.initialized = True
            worker_status.update("✅ 준비 완료")
            status_info.update("Ready")

            output_log.write("")
            output_log.write(Panel(
                "[bold green]✅ 시스템 준비 완료[/bold green]\n\n"
                "[dim]사용 가능한 Worker Tools:[/dim]\n"
                "  • execute_planner_task - 요구사항 분석 및 계획 수립\n"
                "  • execute_coder_task - 코드 작성 및 수정\n"
                "  • execute_reviewer_task - 코드 리뷰 및 품질 검증\n"
                "  • execute_tester_task - 테스트 작성 및 실행\n\n"
                "[dim]작업을 입력하고 Enter를 눌러 시작하세요.[/dim]",
                border_style="green"
            ))
            output_log.write("")

        except Exception as e:
            output_log.write(f"[red]❌ 초기화 실패: {e}[/red]")
            worker_status.update(f"❌ 오류: {e}")
            status_info.update("Error")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Enter 키 입력 시 작업 실행"""
        if not self.initialized:
            return

        user_request = event.value.strip()
        if not user_request:
            return

        # 현재 실행 중인 작업이 있으면 중단
        if self.current_task and not self.current_task.done():
            self.current_task.cancel()
            self.timer_active = False
            self.update_worker_status("")

        # 새 작업 시작
        self.current_task = asyncio.create_task(self.run_task(user_request))

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
                output_log.write("")
                output_log.write(Panel(
                    f"[bold red]❌ 입력 검증 실패[/bold red]\n\n{error_msg}",
                    border_style="red"
                ))
                output_log.write("")
                task_input.value = ""
                return

            # 입력 정제
            user_request = sanitize_user_input(user_request)

            # 입력 필드 비우기
            task_input.value = ""

            # 사용자 요청 표시
            output_log.write("")
            output_log.write(Panel(
                f"[bold]💬 {user_request}[/bold]",
                border_style="blue"
            ))
            output_log.write("")

            # 히스토리에 추가
            self.history.add_message("user", user_request)

            # Manager Agent 실행
            status_info.update("Running...")
            output_log.write("[bold yellow]🤖 Manager Agent[/bold yellow]")
            output_log.write("[dim]" + "─" * 60 + "[/dim]")
            output_log.write("")

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
                    output_log.write(chunk)
            except asyncio.CancelledError:
                # 사용자가 Ctrl+I로 중단
                output_log.write(f"\n[bold yellow]⚠️  작업이 사용자에 의해 중단되었습니다[/bold yellow]")
                self.timer_active = False
                self.update_worker_status("")
                return
            except Exception as stream_error:
                output_log.write(f"\n[bold red]❌ 스트리밍 에러: {stream_error}[/bold red]")
                import traceback
                output_log.write(f"[dim]{traceback.format_exc()}[/dim]")
                self.timer_active = False
                self.update_worker_status("")
                raise

            # Worker Tool 상태 업데이트 (종료)
            self.timer_active = False

            output_log.write("")
            output_log.write("[dim]" + "─" * 60 + "[/dim]")
            output_log.write("")

            # 히스토리에 추가
            self.history.add_message("manager", manager_response)

            # 작업 완료
            task_duration = time.time() - task_start_time
            output_log.write(Panel(
                f"[bold green]✅ 작업 완료[/bold green]\n\n"
                f"⏱️  소요 시간: {task_duration:.1f}초",
                border_style="green"
            ))
            output_log.write("")

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

                output_log.write(Panel(
                    stats_table,
                    border_style="dim"
                ))
                output_log.write("")

            # 세션 저장
            result = SessionResult(status="completed")
            sessions_dir = Path("sessions")
            filepath = save_session_history(
                self.session_id,
                user_request,
                self.history,
                result.to_dict(),
                sessions_dir
            )

            worker_status.update(f"✅ 완료 ({task_duration:.1f}초)")
            status_info.update(f"Completed • {filepath.name}")

        except Exception as e:
            output_log.write("")
            output_log.write(Panel(
                f"[bold red]❌ 오류 발생[/bold red]\n\n{str(e)}",
                border_style="red"
            ))
            output_log.write("")
            worker_status.update(f"❌ 오류")
            status_info.update("Error")
            import traceback
            output_log.write(f"[dim]{traceback.format_exc()}[/dim]")

    async def action_new_session(self) -> None:
        """Ctrl+N: 새 세션"""
        self.session_id = generate_session_id()
        self.history = ConversationHistory()
        self.start_time = time.time()

        # UI 업데이트
        session_info = self.query_one("#session-info", Static)
        status_info = self.query_one("#status-info", Static)
        session_info.update(f"Session: {self.session_id}")

        output_log = self.query_one("#output-log", RichLog)
        output_log.clear()
        output_log.write("")
        output_log.write(Panel(
            f"[bold green]✅ 새 세션 시작[/bold green]\n\n"
            f"Session ID: {self.session_id}",
            border_style="green"
        ))
        output_log.write("")

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

    def update_worker_status_timer(self) -> None:
        """타이머: Worker Tool 실행 시간 업데이트 (0.5초마다 호출)"""
        if not self.timer_active or self.task_start_time is None:
            return

        elapsed = time.time() - self.task_start_time
        # 애니메이션 효과를 위한 스피너
        spinner_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        spinner = spinner_frames[int(elapsed * 2) % len(spinner_frames)]

        self.update_worker_status(f"{spinner} Manager Agent 실행 중... ⏱️  {elapsed:.1f}s")

    async def action_interrupt_or_quit(self) -> None:
        """Ctrl+C: 1번 누르면 작업 중단, 2초 내 2번 누르면 프로세스 종료"""
        current_time = time.time()
        time_since_last_ctrl_c = current_time - self.last_ctrl_c_time

        output_log = self.query_one("#output-log", RichLog)
        worker_status = self.query_one("#worker-status", Static)
        status_info = self.query_one("#status-info", Static)

        # 2초 이내에 다시 누르면 종료
        if time_since_last_ctrl_c < 2.0:
            output_log.write("")
            output_log.write(Panel(
                "[bold]👋 프로그램을 종료합니다...[/bold]",
                border_style="dim"
            ))
            output_log.write("")
            self.exit()
            return

        # 첫 번째 Ctrl+C: 작업 중단
        self.last_ctrl_c_time = current_time

        if self.current_task and not self.current_task.done():
            self.current_task.cancel()
            output_log.write("")
            output_log.write(Panel(
                "[bold yellow]⚠️  작업이 중단되었습니다[/bold yellow]\n\n"
                "[dim]다시 Ctrl+C를 누르면 프로그램이 종료됩니다[/dim]",
                border_style="yellow"
            ))
            output_log.write("")
            self.timer_active = False
            worker_status.update("⚠️  작업 중단됨")
            status_info.update("Interrupted")
        else:
            output_log.write("")
            output_log.write(Panel(
                "[bold]ℹ️  실행 중인 작업이 없습니다[/bold]\n\n"
                "[dim]다시 Ctrl+C를 누르면 프로그램이 종료됩니다[/dim]",
                border_style="dim"
            ))
            output_log.write("")
            worker_status.update("ℹ️  작업 없음")
            status_info.update("Idle")


def main():
    """메인 함수"""
    app = OrchestratorTUI()
    app.run()


if __name__ == "__main__":
    main()
