"""
Multiline Input Widget - Enter로 제출, Shift+Enter로 줄바꿈

TextArea 기반 커스텀 위젯으로 입력 히스토리 기능 포함
"""

from typing import Optional

from textual.widgets import TextArea
from textual.message import Message
from textual import events


class MultilineInput(TextArea):
    """
    멀티라인 입력을 지원하는 커스텀 TextArea 위젯.

    Features:
        - Enter: 제출 (Submitted 메시지 발생)
        - Shift+Enter: 줄바꿈
        - Up/Down: 입력 히스토리 탐색 (외부에서 처리)
    """

    class Submitted(Message):
        """
        Enter 키로 입력이 제출되었을 때 발생하는 메시지.

        Attributes:
            value (str): 제출된 텍스트 (전체 내용)
        """

        def __init__(self, value: str) -> None:
            """
            Submitted 메시지 초기화.

            Args:
                value: 제출된 텍스트
            """
            super().__init__()
            self.value = value

    class HistoryUp(Message):
        """
        Up 키로 히스토리 이전 항목으로 이동 요청.

        커서가 첫 줄에 있을 때만 발생합니다.
        """
        pass

    class HistoryDown(Message):
        """
        Down 키로 히스토리 다음 항목으로 이동 요청.

        커서가 마지막 줄에 있을 때만 발생합니다.
        """
        pass

    def __init__(
        self,
        *,
        id: Optional[str] = None,
        name: Optional[str] = None,
        classes: Optional[str] = None,
        disabled: bool = False,
    ) -> None:
        """
        MultilineInput 초기화.

        Args:
            id: 위젯 ID
            name: 위젯 이름
            classes: CSS 클래스
            disabled: 비활성화 여부
        """
        super().__init__(
            id=id,
            name=name,
            classes=classes,
            disabled=disabled,
            show_line_numbers=False,  # 라인 번호 숨김
            language=None,  # 구문 강조 비활성화
        )

    async def on_key(self, event: events.Key) -> None:
        """
        키 입력 이벤트 처리.

        Enter: 제출 (일반 Enter만)
        Shift+Enter: 줄바꿈 (TextArea 기본 동작)
        Up/Down: 히스토리 탐색 (첫/마지막 줄에서만)

        Args:
            event: 키 입력 이벤트
        """
        # Enter 키 단독 (Shift 없이) - 제출
        if event.key == "enter":
            self.post_message(self.Submitted(self.text))
            event.prevent_default()
            event.stop()
            return
        # Up/Down 키 - 히스토리 탐색
        elif event.key == "up":
            # 커서가 첫 줄에 있으면 히스토리 업
            if self.cursor_location and self.cursor_location[0] == 0:
                event.prevent_default()
                self.post_message(self.HistoryUp())
                return
        elif event.key == "down":
            # 커서가 마지막 줄에 있으면 히스토리 다운
            if not self.text:
                # 빈 입력일 때 히스토리 탐색 허용
                event.prevent_default()
                self.post_message(self.HistoryDown())
                return

            line_count = len(self.text.split('\n'))
            if self.cursor_location and self.cursor_location[0] == line_count - 1:
                event.prevent_default()
                self.post_message(self.HistoryDown())
                return
        # Shift+Enter 및 기타 키는 기본 동작 유지

    def clear(self) -> None:
        """입력 내용을 모두 지웁니다."""
        self.text = ""
