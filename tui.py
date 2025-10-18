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
from textual.widgets import Header, Footer, Input, Static, RichLog
from textual.binding import Binding
from rich.panel import Panel
from rich.markdown import Markdown
from rich.text import Text

from src.models import SessionResult
from src.manager_agent import ManagerAgent
from src.worker_tools import initialize_workers, create_worker_tools_server
from src.conversation import ConversationHistory
from src.utils import (
    generate_session_id,
    save_session_history,
    validate_environment,
)


class OrchestratorTUI(App):
    """Claude Code 스타일 TUI 애플리케이션"""

    CSS = """
    Screen {
        background: $surface;
    }

    #title {
        background: $primary;
        color: $text;
        padding: 1;
        text-align: center;
        text-style: bold;
    }

    #session-info {
        background: $panel;
        color: $text;
        padding: 1;
        margin: 1 0;
    }

    #input-container {
        height: auto;
        background: $panel;
        padding: 1;
        margin: 1 0;
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

    Input {
        margin: 0 1;
    }

    #status-bar {
        background: $panel;
        color: $text;
        padding: 1;
        text-align: center;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "종료"),
        Binding("ctrl+n", "new_session", "새 세션"),
    ]

    def __init__(self):
        super().__init__()
        self.session_id = generate_session_id()
        self.manager: Optional[ManagerAgent] = None
        self.history: Optional[ConversationHistory] = None
        self.initialized = False
        self.start_time = time.time()

    def compose(self) -> ComposeResult:
        """UI 구성"""
        yield Header()
        yield Static("🤖 Group Chat Orchestration (Claude Code Style)", id="title")
        yield Static(
            f"세션 ID: {self.session_id} | Worker Tools Architecture",
            id="session-info"
        )

        with Container(id="input-container"):
            yield Input(
                placeholder="작업을 입력하세요 (예: 'FastAPI로 CRUD API 작성해줘')...",
                id="task-input"
            )

        with ScrollableContainer(id="output-container"):
            yield RichLog(id="output-log", markup=True, highlight=True)

        yield Static("준비 중...", id="status-bar")
        yield Footer()

    async def on_mount(self) -> None:
        """앱 마운트 시 초기화"""
        await self.initialize_orchestrator()

    async def initialize_orchestrator(self) -> None:
        """오케스트레이터 초기화"""
        status_bar = self.query_one("#status-bar", Static)
        output_log = self.query_one("#output-log", RichLog)

        try:
            status_bar.update("초기화 중...")
            output_log.write("🔧 Worker Tools 초기화 중...")

            # 환경 검증
            validate_environment()
            output_log.write("✅ 환경 검증 완료")

            # Worker Agent들 초기화
            config_path = Path("config/agent_config.json")
            initialize_workers(config_path)
            output_log.write("✅ Worker Agents 초기화 완료 (Planner, Coder, Tester)")

            # Worker Tools MCP Server 생성
            worker_tools_server = create_worker_tools_server()
            output_log.write("✅ Worker Tools MCP Server 생성 완료")

            # Manager Agent 초기화
            self.manager = ManagerAgent(worker_tools_server)
            output_log.write("✅ Manager Agent 초기화 완료")

            # 대화 히스토리
            self.history = ConversationHistory()

            self.initialized = True
            status_bar.update("준비됨 - 작업을 입력하고 Enter를 누르세요")
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
            status_bar.update(f"오류: {e}")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Enter 키 입력 시 작업 실행"""
        if not self.initialized:
            return

        user_request = event.value.strip()
        if not user_request:
            return

        await self.run_task(user_request)

    async def run_task(self, user_request: str) -> None:
        """작업 실행 - Manager가 Worker Tools를 자동으로 호출"""
        task_input = self.query_one("#task-input", Input)
        output_log = self.query_one("#output-log", RichLog)
        status_bar = self.query_one("#status-bar", Static)

        try:
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
            status_bar.update("Manager Agent 실행 중...")
            output_log.write("[bold yellow]🤖 Manager Agent:[/bold yellow]")
            output_log.write("")

            # Manager가 Worker Tools를 호출하여 작업 수행
            task_start_time = time.time()
            manager_response = await self.manager.analyze_and_plan(
                self.history.get_history()
            )

            # 응답 표시 (Markdown 렌더링)
            output_log.write(Markdown(manager_response))
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

            status_bar.update(f"완료 ({task_duration:.1f}초) - 세션 저장: {filepath.name}")

        except Exception as e:
            output_log.write(f"[bold red]❌ 오류 발생: {e}[/bold red]")
            status_bar.update(f"오류: {e}")
            import traceback
            output_log.write(f"[dim]{traceback.format_exc()}[/dim]")

    async def action_new_session(self) -> None:
        """Ctrl+N: 새 세션"""
        self.session_id = generate_session_id()
        self.history = ConversationHistory()
        self.start_time = time.time()

        session_info = self.query_one("#session-info", Static)
        session_info.update(
            f"세션 ID: {self.session_id} | Worker Tools Architecture"
        )

        output_log = self.query_one("#output-log", RichLog)
        output_log.clear()
        output_log.write(Panel(
            f"[bold green]새 세션 시작[/bold green]\n세션 ID: {self.session_id}",
            border_style="green"
        ))
        output_log.write("")

        status_bar = self.query_one("#status-bar", Static)
        status_bar.update("새 세션 준비됨")


def main():
    """메인 함수"""
    app = OrchestratorTUI()
    app.run()


if __name__ == "__main__":
    main()
