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
from textual.containers import Container, Vertical, ScrollableContainer
from textual.widgets import Footer, Input, Static, RichLog
from textual.binding import Binding
from rich.panel import Panel
from rich.markdown import Markdown
from rich.text import Text

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
    """Claude Code 스타일 TUI 애플리케이션"""

    CSS = """
    Screen {
        background: $surface;
    }

    #output-container {
        border: solid $primary;
        height: 1fr;
        margin: 1 0;
    }

    #output-log {
        height: 1fr;
        background: $surface;
    }

    #worker-status {
        background: $boost;
        color: $text;
        padding: 1;
        margin: 1 0;
        height: auto;
        border: solid $accent;
    }

    #input-container {
        height: auto;
        background: $panel;
        padding: 1;
        margin: 1 0;
    }

    Input {
        margin: 0 1;
    }

    #session-id {
        background: $panel;
        color: $text-muted;
        padding: 0 1;
        text-align: right;
        height: 1;
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
        # 출력 영역 (위)
        with ScrollableContainer(id="output-container"):
            yield RichLog(id="output-log", markup=True, highlight=True)

        # Worker Tool 실행 상태 + Status (중간)
        yield Static("준비 중...", id="worker-status")

        # 입력 영역 (아래)
        with Container(id="input-container"):
            yield Input(
                placeholder="작업을 입력하세요 (예: 'FastAPI로 CRUD API 작성해줘')...",
                id="task-input"
            )

        yield Footer()
        yield Static(f"세션 ID: {self.session_id}", id="session-id")

    async def on_mount(self) -> None:
        """앱 마운트 시 초기화"""
        await self.initialize_orchestrator()
        # 타이머: 0.5초마다 Worker Tool 실행 시간 업데이트
        self.set_interval(0.5, self.update_worker_status_timer)

    async def initialize_orchestrator(self) -> None:
        """오케스트레이터 초기화"""
        worker_status = self.query_one("#worker-status", Static)
        output_log = self.query_one("#output-log", RichLog)

        try:
            worker_status.update("초기화 중...")
            output_log.write("🔧 Worker Tools 초기화 중...")

            # 환경 검증
            validate_environment()
            output_log.write("✅ 환경 검증 완료")

            # Worker Agent들 초기화 (프로젝트 루트 기준)
            config_path = get_project_root() / "config" / "agent_config.json"
            initialize_workers(config_path)
            output_log.write("✅ Worker Agents 초기화 완료 (Planner, Coder, Reviewer, Tester)")

            # Worker Tools MCP Server 생성
            worker_tools_server = create_worker_tools_server()
            output_log.write("✅ Worker Tools MCP Server 생성 완료")

            # Manager Agent 초기화
            self.manager = ManagerAgent(worker_tools_server)
            output_log.write("✅ Manager Agent 초기화 완료")

            # 대화 히스토리
            self.history = ConversationHistory()

            self.initialized = True
            worker_status.update("준비됨 - 작업을 입력하고 Enter를 누르세요")
            output_log.write("")
            output_log.write(Panel(
                "[bold green]초기화 완료![/bold green]\n\n"
                "Manager Agent가 자동으로 Worker Tools를 호출하여 작업을 수행합니다.\n"
                "- execute_planner_task: 요구사항 분석 및 계획\n"
                "- execute_coder_task: 코드 작성\n"
                "- execute_tester_task: 테스트 작성 및 실행",
                border_style="green"
            ))
            output_log.write("")

        except Exception as e:
            output_log.write(f"[red]❌ 초기화 실패: {e}[/red]")
            worker_status.update(f"오류: {e}")

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

        try:
            # 입력 검증
            is_valid, error_msg = validate_user_input(user_request)
            if not is_valid:
                output_log.write(f"[bold red]❌ 입력 검증 실패: {error_msg}[/bold red]")
                task_input.value = ""
                return

            # 입력 정제
            user_request = sanitize_user_input(user_request)

            # 입력 필드 비우기
            task_input.value = ""

            # 사용자 요청 표시
            output_log.write("")
            output_log.write(Panel(
                f"[bold cyan]{user_request}[/bold cyan]",
                title="[bold]사용자 요청[/bold]",
                border_style="cyan"
            ))
            output_log.write("")

            # 히스토리에 추가
            self.history.add_message("user", user_request)

            # Manager Agent 실행
            worker_status.update("Manager Agent 실행 중...")
            output_log.write("[bold yellow]🤖 Manager Agent:[/bold yellow]")
            output_log.write("")

            # Worker Tool 상태 업데이트 (시작)
            self.task_start_time = time.time()
            self.timer_active = True
            self.update_worker_status("🔧 Manager Agent 실행 중...")

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
            self.update_worker_status("")

            output_log.write("")
            output_log.write("")

            # 히스토리에 추가
            self.history.add_message("manager", manager_response)

            # 작업 완료
            task_duration = time.time() - task_start_time
            output_log.write(Panel(
                f"[bold green]작업 완료[/bold green]\n"
                f"소요 시간: {task_duration:.1f}초",
                border_style="green"
            ))
            output_log.write("")

            # 에러 통계 표시
            error_stats = get_error_statistics()
            stats_lines = ["📊 [bold]Worker Tools 에러 통계[/bold]\n"]
            for worker_name, data in error_stats.items():
                stats_lines.append(
                    f"[cyan]{worker_name.upper()}[/cyan]: "
                    f"시도 {data['attempts']}, "
                    f"성공 {data['successes']}, "
                    f"실패 {data['failures']}, "
                    f"에러율 {data['error_rate']}%"
                )

            output_log.write(Panel(
                "\n".join(stats_lines),
                border_style="yellow"
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

            worker_status.update(f"완료 ({task_duration:.1f}초) - 세션 저장: {filepath.name}")

        except Exception as e:
            output_log.write(f"[bold red]❌ 오류 발생: {e}[/bold red]")
            worker_status.update(f"오류: {e}")
            import traceback
            output_log.write(f"[dim]{traceback.format_exc()}[/dim]")

    async def action_new_session(self) -> None:
        """Ctrl+N: 새 세션"""
        self.session_id = generate_session_id()
        self.history = ConversationHistory()
        self.start_time = time.time()

        # 세션 ID 업데이트
        session_id_widget = self.query_one("#session-id", Static)
        session_id_widget.update(f"세션 ID: {self.session_id}")

        output_log = self.query_one("#output-log", RichLog)
        output_log.clear()
        output_log.write(Panel(
            f"[bold green]새 세션 시작[/bold green]\n세션 ID: {self.session_id}",
            border_style="green"
        ))
        output_log.write("")

        worker_status = self.query_one("#worker-status", Static)
        worker_status.update("새 세션 준비됨")

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
        self.update_worker_status(f"🔧 Manager Agent 실행 중... ⏱️  {elapsed:.1f}s")

    async def action_interrupt_or_quit(self) -> None:
        """Ctrl+C: 1번 누르면 작업 중단, 2초 내 2번 누르면 프로세스 종료"""
        current_time = time.time()
        time_since_last_ctrl_c = current_time - self.last_ctrl_c_time

        # 2초 이내에 다시 누르면 종료
        if time_since_last_ctrl_c < 2.0:
            output_log = self.query_one("#output-log", RichLog)
            output_log.write("[bold red]👋 종료합니다...[/bold red]")
            self.exit()
            return

        # 첫 번째 Ctrl+C: 작업 중단
        self.last_ctrl_c_time = current_time

        if self.current_task and not self.current_task.done():
            self.current_task.cancel()
            output_log = self.query_one("#output-log", RichLog)
            output_log.write("[bold yellow]⚠️  작업 중단됨 (다시 Ctrl+C를 누르면 종료)[/bold yellow]")
            self.timer_active = False
            self.update_worker_status("작업 중단됨 (Ctrl+C 다시 누르면 종료)")
        else:
            output_log = self.query_one("#output-log", RichLog)
            output_log.write("[bold yellow]ℹ️  실행 중인 작업이 없습니다 (다시 Ctrl+C를 누르면 종료)[/bold yellow]")
            self.update_worker_status("Ctrl+C 다시 누르면 종료")


def main():
    """메인 함수"""
    app = OrchestratorTUI()
    app.run()


if __name__ == "__main__":
    main()
