#!/usr/bin/env python3
"""
그룹 챗 오케스트레이션 시스템 - Textual TUI

터미널에서 실행되는 인터랙티브 텍스트 유저 인터페이스
"""

import asyncio
from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import Header, Footer, Input, Button, Static, Label, RichLog
from textual.binding import Binding
from rich.text import Text
from rich.panel import Panel
from rich.markdown import Markdown

from src.models import SessionResult
from src.manager_agent import ManagerAgent
from src.worker_agent import WorkerAgent
from src.conversation import ConversationHistory
from src.chat_manager import ChatManager
from src.utils import (
    load_agent_config,
    generate_session_id,
    save_session_history,
    validate_environment,
    get_agent_emoji
)


class OrchestratorTUI(App):
    """그룹 챗 오케스트레이션 TUI 애플리케이션"""

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

    Button {
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
        Binding("ctrl+r", "run", "실행"),
    ]

    def __init__(self):
        super().__init__()
        self.session_id = generate_session_id()
        self.manager: Optional[ManagerAgent] = None
        self.workers: dict = {}
        self.chat_manager: Optional[ChatManager] = None
        self.history: Optional[ConversationHistory] = None
        self.initialized = False

    def compose(self) -> ComposeResult:
        """UI 구성"""
        yield Header()
        yield Static("🤖 Group Chat Orchestration System", id="title")
        yield Static(f"세션 ID: {self.session_id} | 매니저: ManagerAgent | 워커: Loading...", id="session-info")

        with Container(id="input-container"):
            yield Label("작업 요청:")
            yield Input(placeholder="예: 'FastAPI로 간단한 CRUD API를 작성해줘. 파일명은 api.py로 해줘.'", id="task-input")
            with Horizontal():
                yield Button("🚀 실행 (Ctrl+R)", id="run-button", variant="primary")
                yield Button("🔄 새 세션 (Ctrl+N)", id="new-session-button")

        with ScrollableContainer(id="output-container"):
            yield RichLog(id="output-log", markup=True, highlight=True)

        yield Static("준비됨", id="status-bar")
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
            output_log.write("🔧 오케스트레이터를 초기화하는 중...")

            # 환경 검증
            validate_environment()
            output_log.write("✅ 환경 검증 완료")

            # 매니저 에이전트 초기화
            self.manager = ManagerAgent()
            output_log.write("✅ 매니저 에이전트 초기화 완료")

            # 워커 에이전트 설정 로드
            config_path = Path("config/agent_config.json")
            worker_configs = load_agent_config(config_path)

            # 워커 에이전트 초기화
            self.workers = {}
            for config in worker_configs:
                worker = WorkerAgent(config)
                self.workers[config.name] = worker
            output_log.write(f"✅ 워커 에이전트 초기화 완료: {', '.join(self.workers.keys())}")

            # 챗 매니저
            self.chat_manager = ChatManager(self.workers)

            # 대화 히스토리
            self.history = ConversationHistory()

            # 세션 정보 업데이트
            session_info = self.query_one("#session-info", Static)
            session_info.update(
                f"세션 ID: {self.session_id} | "
                f"매니저: ManagerAgent | "
                f"워커: {', '.join(self.workers.keys())}"
            )

            self.initialized = True
            status_bar.update("준비됨 - 작업을 입력하고 실행 버튼을 누르세요")
            output_log.write("🎉 초기화 완료! 작업을 시작할 수 있습니다.")

        except Exception as e:
            output_log.write(f"[red]❌ 초기화 실패: {e}[/red]")
            status_bar.update(f"오류: {e}")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """버튼 클릭 이벤트"""
        if event.button.id == "run-button":
            await self.run_orchestration()
        elif event.button.id == "new-session-button":
            await self.action_new_session()

    async def action_run(self) -> None:
        """Ctrl+R: 실행"""
        await self.run_orchestration()

    async def action_new_session(self) -> None:
        """Ctrl+N: 새 세션"""
        self.session_id = generate_session_id()
        self.history = ConversationHistory()

        session_info = self.query_one("#session-info", Static)
        session_info.update(
            f"세션 ID: {self.session_id} | "
            f"매니저: ManagerAgent | "
            f"워커: {', '.join(self.workers.keys())}"
        )

        output_log = self.query_one("#output-log", RichLog)
        output_log.clear()
        output_log.write(f"🔄 새 세션 시작: {self.session_id}")

        status_bar = self.query_one("#status-bar", Static)
        status_bar.update("새 세션 준비됨")

    async def run_orchestration(self) -> None:
        """오케스트레이션 실행"""
        if not self.initialized:
            return

        task_input = self.query_one("#task-input", Input)
        user_request = task_input.value.strip()

        if not user_request:
            return

        output_log = self.query_one("#output-log", RichLog)
        status_bar = self.query_one("#status-bar", Static)

        try:
            # 입력 필드 비우기
            task_input.value = ""

            # 사용자 요청 표시
            output_log.write("")
            output_log.write(Panel(f"[bold cyan]사용자 요청:[/bold cyan] {user_request}", border_style="cyan"))
            output_log.write("")

            # 히스토리에 추가
            self.history.add_message("user", user_request)

            turn = 0
            max_turns = 20

            while turn < max_turns:
                turn += 1
                status_bar.update(f"Turn {turn}/{max_turns} 진행 중...")

                # 1. 매니저가 작업 분석 및 계획
                output_log.write(f"[bold yellow]━━━ Turn {turn} ━━━ 👔 ManagerAgent ━━━[/bold yellow]")

                manager_response = await self.manager.analyze_and_plan(self.history.get_history())
                output_log.write(Markdown(manager_response))
                output_log.write("")

                # 히스토리에 추가
                self.history.add_message("manager", manager_response)

                # 2. 종료 조건 확인
                if "TERMINATE" in manager_response.upper() or "작업 완료" in manager_response:
                    output_log.write("[bold green]✅ 작업이 완료되었습니다![/bold green]")
                    status_bar.update("작업 완료")
                    break

                # 3. 다음 워커 선택
                next_worker = self.extract_worker_assignment(manager_response)

                if not next_worker:
                    continue

                if next_worker not in self.workers:
                    output_log.write(f"[yellow]⚠️ 알 수 없는 워커: {next_worker}[/yellow]")
                    continue

                # 4. 워커 실행
                worker = self.workers[next_worker]
                emoji = get_agent_emoji(next_worker)

                output_log.write(f"[bold magenta]━━━ Turn {turn} ━━━ {emoji} {worker.config.role} ({next_worker}) ━━━[/bold magenta]")

                task_description = self.extract_task_for_worker(manager_response, next_worker)

                try:
                    worker_response = ""
                    async for chunk in worker.execute_task(task_description):
                        worker_response += chunk
                        # 실시간 업데이트는 너무 빠르므로 최종 결과만 표시

                    output_log.write(Markdown(worker_response))
                    output_log.write("")

                    # 히스토리에 추가
                    self.history.add_message("agent", worker_response, next_worker)

                except Exception as e:
                    error_msg = f"❌ 워커 실행 실패: {e}"
                    output_log.write(f"[red]{error_msg}[/red]")
                    self.history.add_message("agent", error_msg, next_worker)

            # 최대 턴 수 도달
            if turn >= max_turns:
                output_log.write(f"[yellow]⚠️ 최대 턴 수({max_turns})에 도달했습니다.[/yellow]")
                status_bar.update(f"최대 턴 수 도달 ({max_turns})")

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

            output_log.write(f"[green]💾 세션이 저장되었습니다: {filepath.name}[/green]")
            status_bar.update("작업 완료 - 세션 저장됨")

        except Exception as e:
            output_log.write(f"[bold red]❌ 오류 발생: {e}[/bold red]")
            status_bar.update(f"오류: {e}")

    def extract_worker_assignment(self, manager_response: str) -> Optional[str]:
        """매니저 응답에서 @worker_name 추출"""
        import re
        pattern = r'@(\w+)'
        matches = re.findall(pattern, manager_response.lower())

        if matches:
            for match in matches:
                if match in self.workers:
                    return match
        return None

    def extract_task_for_worker(self, manager_response: str, worker_name: str) -> str:
        """매니저 응답에서 워커에게 전달할 작업 추출"""
        import re
        pattern = rf'@{worker_name}\s+(.+?)(?=@\w+|$)'
        match = re.search(pattern, manager_response, re.DOTALL | re.IGNORECASE)

        if match:
            return match.group(1).strip()
        return manager_response


def main():
    """메인 함수"""
    app = OrchestratorTUI()
    app.run()


if __name__ == "__main__":
    main()
