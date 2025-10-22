"""
VS Code 스타일 명령 팔레트 위젯

Ctrl+P로 호출하여 키 바인딩과 슬래시 커맨드를 실시간 퍼지 검색
"""

from typing import List, Tuple, Callable, Any, Optional
from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Static, ListView, ListItem, Label
from textual.binding import Binding
from textual import events
from rich.text import Text
from rapidfuzz import fuzz, process


class CommandItem:
    """
    명령 팔레트 아이템

    Attributes:
        label: 표시할 명령어 이름
        description: 명령어 설명
        keybinding: 키 바인딩 (예: "Ctrl+N")
        action: 실행할 액션 (슬래시 커맨드 또는 액션 메서드 이름)
        item_type: 아이템 타입 ("keybinding" 또는 "command")
    """

    def __init__(
        self,
        label: str,
        description: str,
        keybinding: str = "",
        action: str = "",
        item_type: str = "keybinding"
    ):
        self.label = label
        self.description = description
        self.keybinding = keybinding
        self.action = action
        self.item_type = item_type

    def get_search_text(self) -> str:
        """
        검색에 사용할 텍스트 반환

        Returns:
            검색 대상 문자열 (레이블 + 설명)
        """
        return f"{self.label} {self.description}"

    def get_display_text(self) -> Text:
        """
        리스트에 표시할 Rich Text 반환

        Returns:
            Rich Text 객체
        """
        text = Text()
        # 아이콘
        if self.item_type == "keybinding":
            text.append("⌨️  ", style="cyan")
        else:
            text.append("💬 ", style="yellow")

        # 명령어 이름
        text.append(self.label, style="bold white")

        # 키 바인딩 (있으면)
        if self.keybinding:
            text.append(f"  [{self.keybinding}]", style="dim cyan")

        # 설명
        text.append(f"  {self.description}", style="dim")

        return text


class CommandPaletteModal(ModalScreen):
    """
    VS Code 스타일 명령 팔레트 모달

    Features:
    - 실시간 퍼지 검색 (rapidfuzz)
    - 키보드 내비게이션 (화살표, Enter, ESC)
    - 키 바인딩 및 슬래시 커맨드 통합 검색
    """

    CSS = """
    CommandPaletteModal {
        align: center top;
        padding-top: 5;
    }

    #command-palette-dialog {
        width: 70;
        height: auto;
        max-height: 80%;
        background: #0d1117;
        border: thick #388bfd;
        padding: 0;
    }

    #command-input-container {
        height: 3;
        background: #161b22;
        border-bottom: solid #21262d;
        padding: 1 2;
    }

    #command-input {
        background: transparent;
        border: none;
        color: #c9d1d9;
        width: 100%;
    }

    #command-results {
        height: auto;
        max-height: 20;
        background: transparent;
        padding: 0;
    }

    #command-results ListView {
        background: transparent;
        border: none;
        padding: 0;
    }

    #command-results ListItem {
        background: #0d1117;
        color: #c9d1d9;
        padding: 0 2;
        height: 1;
    }

    #command-results ListItem:hover {
        background: #1f6feb;
    }

    #command-results ListItem.-selected {
        background: #1f6feb;
    }

    #command-help-text {
        height: 1;
        background: #161b22;
        color: #8b949e;
        padding: 0 2;
        border-top: solid #21262d;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "닫기"),
        Binding("enter", "execute", "실행"),
        Binding("down", "move_down", "아래로", show=False),
        Binding("up", "move_up", "위로", show=False),
    ]

    def __init__(
        self,
        commands: List[CommandItem],
        on_execute: Callable[[CommandItem], None]
    ):
        """
        초기화

        Args:
            commands: 명령 아이템 리스트
            on_execute: 명령 실행 콜백 (CommandItem을 인자로 받음)
        """
        super().__init__()
        self.all_commands = commands
        self.filtered_commands: List[CommandItem] = []
        self.on_execute = on_execute

    def compose(self) -> ComposeResult:
        """UI 구성"""
        with Container(id="command-palette-dialog"):
            with Container(id="command-input-container"):
                yield Input(
                    placeholder="명령어를 입력하세요... (예: help, 새 세션)",
                    id="command-input"
                )
            with Container(id="command-results"):
                yield ListView(id="command-list")
            yield Static(
                "↑↓: 이동 | Enter: 실행 | ESC: 닫기",
                id="command-help-text"
            )

    def on_mount(self) -> None:
        """마운트 시 초기화"""
        # 초기 검색 결과 표시 (모든 명령)
        self._update_results("")
        # 입력 필드에 포커스
        input_widget = self.query_one("#command-input", Input)
        input_widget.focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        """
        입력 변경 이벤트 - 실시간 퍼지 검색

        Args:
            event: 입력 변경 이벤트
        """
        if event.input.id == "command-input":
            query = event.value.strip()
            self._update_results(query)

    def _update_results(self, query: str) -> None:
        """
        검색 결과 업데이트 (퍼지 검색)

        Args:
            query: 검색 쿼리
        """
        list_view = self.query_one("#command-list", ListView)
        list_view.clear()

        # 빈 검색어면 모든 명령 표시 (상위 10개)
        if not query:
            self.filtered_commands = self.all_commands[:10]
        else:
            # rapidfuzz를 사용한 퍼지 매칭
            results = process.extract(
                query,
                self.all_commands,
                scorer=fuzz.WRatio,
                processor=lambda cmd: cmd.get_search_text(),
                limit=10
            )
            # 점수 60 이상인 결과만 필터링
            self.filtered_commands = [cmd for cmd, score, _ in results if score >= 60]

        # 리스트뷰에 추가
        for cmd in self.filtered_commands:
            list_view.append(ListItem(Label(cmd.get_display_text())))

        # 첫 번째 아이템 선택
        if self.filtered_commands:
            list_view.index = 0

    def action_execute(self) -> None:
        """Enter: 선택된 명령 실행"""
        list_view = self.query_one("#command-list", ListView)
        if list_view.index is not None and 0 <= list_view.index < len(self.filtered_commands):
            selected_command = self.filtered_commands[list_view.index]
            self.dismiss(selected_command)

    def action_close(self) -> None:
        """ESC: 모달 닫기"""
        self.dismiss(None)

    def action_move_down(self) -> None:
        """화살표 아래: 다음 아이템으로 이동"""
        list_view = self.query_one("#command-list", ListView)
        if list_view.index is not None:
            new_index = min(list_view.index + 1, len(self.filtered_commands) - 1)
            list_view.index = new_index

    def action_move_up(self) -> None:
        """화살표 위: 이전 아이템으로 이동"""
        list_view = self.query_one("#command-list", ListView)
        if list_view.index is not None:
            new_index = max(list_view.index - 1, 0)
            list_view.index = new_index
