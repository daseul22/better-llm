"""
Multiline Input Widget - Ctrl+R로 제출, Enter는 줄바꿈

TextArea 기반 커스텀 위젯으로 입력 히스토리 기능 포함
"""

from typing import Optional

from textual.widgets import TextArea
from textual.message import Message
from textual import events
from textual.binding import Binding


class MultilineInput(TextArea):
    """
    멀티라인 입력을 지원하는 커스텀 TextArea 위젯.

    Features:
        - Ctrl+R: 제출 (Submitted 메시지 발생)
        - Enter: 줄바꿈 (TextArea 기본 동작)
        - Up/Down: 입력 히스토리 탐색 (외부에서 처리)
        - Tab: 자동 완성 (AutocompleteRequested 메시지 발생)
    """

    # Ctrl+R로 제출
    BINDINGS = [
        Binding("ctrl+r", "submit_input", "Submit", show=False, priority=True),
    ]

    class Submitted(Message):
        """
        Ctrl+R로 입력이 제출되었을 때 발생하는 메시지.

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

    class AutocompleteRequested(Message):
        """
        Tab 키로 자동 완성이 요청되었을 때 발생하는 메시지.

        Attributes:
            current_text (str): 현재 입력 텍스트
        """

        def __init__(self, current_text: str) -> None:
            """
            AutocompleteRequested 메시지 초기화.

            Args:
                current_text: 현재 입력 텍스트
            """
            super().__init__()
            self.current_text = current_text

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

    def action_submit_input(self) -> None:
        """
        Ctrl+R 액션: 입력 제출.

        BINDINGS에서 호출됩니다.
        입력창 초기화는 이벤트 핸들러에서 처리합니다.
        """
        from src.infrastructure.logging import get_logger
        logger = get_logger(__name__)

        logger.info(f"🔴 [MultilineInput] action_submit_input 호출됨! text={self.text!r}")

        # 빈 입력은 무시
        if not self.text.strip():
            logger.warning(f"⚠️ [MultilineInput] 빈 입력 무시")
            return

        # Submitted 메시지 전송
        logger.info(f"📤 [MultilineInput] Submitted 메시지 전송: {self.text!r}")
        self.post_message(self.Submitted(self.text))
        logger.info(f"✅ [MultilineInput] Submitted 메시지 전송 완료")

    async def on_key(self, event: events.Key) -> None:
        """
        키 입력 이벤트 처리.

        Enter: 줄바꿈 (TextArea 기본 동작 유지)
        Ctrl+R: 제출 (BINDINGS에서 처리)
        Tab: 자동 완성
        Up/Down: 히스토리 탐색 (첫/마지막 줄에서만)

        Args:
            event: 키 입력 이벤트
        """
        # Tab 키 - 자동 완성
        if event.key == "tab":
            self.post_message(self.AutocompleteRequested(self.text))
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
        # Enter 키는 기본 동작 유지 (줄바꿈)
        # 기타 키도 기본 동작 유지 (TextArea 기본 처리)

    def clear(self) -> None:
        """입력 내용을 모두 지웁니다."""
        self.text = ""
