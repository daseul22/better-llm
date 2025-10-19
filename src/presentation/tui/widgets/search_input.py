"""
검색 입력 위젯

로그 검색을 위한 입력 필드 및 결과 하이라이트
"""

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Input, Static, Button
from textual.binding import Binding
from rich.text import Text
from typing import List, Tuple, Optional


class SearchModal(ModalScreen):
    """검색 모달 스크린"""

    CSS = """
    SearchModal {
        align: center middle;
    }

    #search-dialog {
        width: 60;
        height: auto;
        background: #0d1117;
        border: thick #388bfd;
        padding: 1 2;
    }

    #search-input-container {
        height: auto;
        background: transparent;
        border: round #388bfd;
        margin: 1 0;
        padding: 1;
    }

    #search-input {
        background: transparent;
        border: none;
        color: #c9d1d9;
    }

    #search-results {
        height: auto;
        color: #8b949e;
        padding: 1 0;
    }

    #search-buttons {
        height: auto;
        margin-top: 1;
    }

    Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "닫기"),
        Binding("enter", "search", "검색"),
    ]

    def __init__(self):
        super().__init__()
        self.search_results: List[Tuple[int, str]] = []  # (라인 번호, 라인 내용)

    def compose(self) -> ComposeResult:
        """UI 구성"""
        with Container(id="search-dialog"):
            yield Static("[bold cyan]로그 검색[/bold cyan]")
            with Container(id="search-input-container"):
                yield Input(
                    placeholder="검색어를 입력하세요...",
                    id="search-input"
                )
            yield Static("", id="search-results")
            with Horizontal(id="search-buttons"):
                yield Button("검색 (Enter)", id="search-button", variant="primary")
                yield Button("닫기 (ESC)", id="close-button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """버튼 클릭 이벤트"""
        if event.button.id == "search-button":
            self.action_search()
        elif event.button.id == "close-button":
            self.action_close()

    def action_search(self) -> None:
        """검색 실행"""
        search_input = self.query_one("#search-input", Input)
        query = search_input.value.strip()

        if not query:
            return

        # 검색 결과를 부모 앱에 전달하여 처리
        self.dismiss(query)

    def action_close(self) -> None:
        """모달 닫기"""
        self.dismiss(None)


class SearchHighlighter:
    """
    검색 결과 하이라이트 유틸리티

    로그에서 검색어를 찾아 하이라이트 표시
    """

    @staticmethod
    def search_in_lines(lines: List[str], query: str) -> List[Tuple[int, str]]:
        """
        라인 리스트에서 검색어 찾기

        Args:
            lines: 검색할 라인 리스트
            query: 검색어

        Returns:
            (라인 번호, 라인 내용) 튜플 리스트
        """
        if not query:
            return []

        results = []
        query_lower = query.lower()

        for i, line in enumerate(lines):
            if query_lower in line.lower():
                results.append((i, line))

        return results

    @staticmethod
    def highlight_text(text: str, query: str) -> Text:
        """
        텍스트에서 검색어를 하이라이트

        Args:
            text: 원본 텍스트
            query: 검색어

        Returns:
            하이라이트된 Rich Text 객체
        """
        if not query:
            return Text(text)

        rich_text = Text()
        text_lower = text.lower()
        query_lower = query.lower()
        last_index = 0

        # 검색어가 나타나는 모든 위치 찾기
        while True:
            index = text_lower.find(query_lower, last_index)
            if index == -1:
                # 남은 텍스트 추가
                rich_text.append(text[last_index:])
                break

            # 검색어 이전 텍스트 추가
            rich_text.append(text[last_index:index])

            # 검색어 하이라이트 (노란색 배경)
            rich_text.append(
                text[index:index + len(query)],
                style="black on yellow"
            )

            last_index = index + len(query)

        return rich_text

    @staticmethod
    def get_context_lines(
        lines: List[str],
        line_index: int,
        context_size: int = 2
    ) -> List[Tuple[int, str]]:
        """
        특정 라인 주변의 컨텍스트 라인 가져오기

        Args:
            lines: 전체 라인 리스트
            line_index: 중심 라인 인덱스
            context_size: 앞뒤로 가져올 라인 수

        Returns:
            (라인 번호, 라인 내용) 튜플 리스트
        """
        start = max(0, line_index - context_size)
        end = min(len(lines), line_index + context_size + 1)

        return [(i, lines[i]) for i in range(start, end)]
