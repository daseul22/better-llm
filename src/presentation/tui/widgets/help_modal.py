"""
도움말 모달 위젯

사용 가능한 키 바인딩, 슬래시 커맨드 등을 표시하는 모달
"""

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.screen import ModalScreen
from textual.widgets import Static, Button
from textual import events
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.console import Group


class HelpModal(ModalScreen):
    """도움말 모달 스크린"""

    CSS = """
    HelpModal {
        align: center middle;
    }

    #help-dialog {
        width: 80;
        height: auto;
        max-height: 90%;
        background: #0d1117;
        border: thick #388bfd;
        padding: 1 2;
    }

    #help-content {
        height: auto;
        background: transparent;
        color: #c9d1d9;
        padding: 1 0;
    }

    #help-close-button {
        width: 100%;
        margin-top: 1;
    }
    """

    def compose(self) -> ComposeResult:
        """UI 구성"""
        with Container(id="help-dialog"):
            yield Static(self._generate_help_content(), id="help-content")
            yield Button("닫기 (ESC)", id="help-close-button", variant="primary")

    def _generate_help_content(self) -> Panel:
        """도움말 내용 생성"""
        # 키 바인딩 테이블
        key_table = Table(show_header=True, header_style="bold cyan", border_style="dim")
        key_table.add_column("키", style="cyan", width=20)
        key_table.add_column("기능", width=40)

        key_bindings = [
            ("↑ / ↓", "히스토리 탐색 (최대 100개)"),
            ("Enter", "작업 실행 (제출)"),
            ("Shift+Enter", "줄바꿈 (멀티라인 입력)"),
            ("Ctrl+C", "작업 중단 / 프로그램 종료"),
            ("Ctrl+N", "새 세션 시작"),
            ("Ctrl+S", "로그 저장"),
            ("Ctrl+L", "세션 브라우저 (로드/삭제)"),
            ("/", "로그 검색 (주 단축키)"),
            ("Ctrl+F", "로그 검색 (보조)"),
            ("?", "도움말 표시 (주 단축키)"),
            ("Ctrl+H, F1", "도움말 표시 (대체 키)"),
            ("F2", "설정 패널"),
            ("Ctrl+M", "메트릭 패널 토글 (주 단축키)"),
            ("F3", "메트릭 패널 토글 (보조)"),
            ("F4", "워크플로우 패널 토글"),
            ("F5", "Worker 상태 패널 토글"),
            ("F6", "에러 통계 표시"),
            ("Ctrl+Tab", "다음 Worker 아웃풋 탭"),
            ("Ctrl+Shift+Tab", "이전 Worker 아웃풋 탭"),
            ("Ctrl+O", "출력 모드 전환"),
            ("ESC", "모달 닫기"),
        ]

        for key, description in key_bindings:
            key_table.add_row(key, description)

        # 슬래시 커맨드 테이블
        command_table = Table(show_header=True, header_style="bold cyan", border_style="dim")
        command_table.add_column("커맨드", style="cyan", width=25)
        command_table.add_column("설명", width=35)

        commands = [
            ("/help", "도움말 표시"),
            ("/init", "프로젝트 분석 및 context 초기화"),
            ("/load <session_id>", "이전 세션 불러오기"),
            ("/clear", "로그 화면 지우기"),
        ]

        for cmd, desc in commands:
            command_table.add_row(cmd, desc)

        # Worker Tools 테이블
        worker_table = Table(show_header=True, header_style="bold cyan", border_style="dim")
        worker_table.add_column("Worker Tool", style="cyan", width=25)
        worker_table.add_column("설명", width=35)

        workers = [
            ("execute_planner_task", "요구사항 분석 및 계획 수립"),
            ("execute_coder_task", "코드 작성 및 수정"),
            ("execute_reviewer_task", "코드 리뷰 및 품질 검증"),
            ("execute_tester_task", "테스트 작성 및 실행"),
        ]

        for worker, desc in workers:
            worker_table.add_row(worker, desc)

        # 전체 내용 조합 (Group으로 여러 렌더러블 객체 조합)
        content = Group(
            Text("AI Orchestration System - 도움말\n", style="bold"),
            Text("키 바인딩", style="bold yellow"),
            key_table,
            Text("\n슬래시 커맨드", style="bold yellow"),
            command_table,
            Text("\n사용 가능한 Worker Tools", style="bold yellow"),
            worker_table,
            Text("\n디버그 정보 표시", style="bold yellow"),
            Text("환경변수 WORKER_DEBUG_INFO=true를 설정하면\n"
                 "각 Worker 실행 시 시스템 프롬프트와 컨텍스트를 표시합니다.\n", style="dim"),
            Text("예: export WORKER_DEBUG_INFO=true\n", style="cyan"),
            Text("Manager Agent가 자동으로 적절한 Worker Tool을 호출합니다.", style="dim"),
        )

        return Panel(content, border_style="blue", title="[bold]도움말[/bold]")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        버튼 클릭 이벤트 처리.

        Args:
            event: 버튼 클릭 이벤트
        """
        if event.button.id == "help-close-button":
            self.dismiss()

    def on_key(self, event: events.Key) -> None:
        """
        키 입력 이벤트 처리.

        ESC 키를 눌러 모달을 닫습니다.

        Args:
            event: 키 입력 이벤트
        """
        if event.key == "escape":
            self.dismiss()
