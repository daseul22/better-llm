"""
Multiline Input Widget - Enter로 제출, Ctrl+R로 줄바꿈

TextArea 기반 커스텀 위젯으로 입력 히스토리 기능 포함
"""

from typing import Optional

from textual.widgets import TextArea
from textual.message import Message
from textual import events
from textual.events import Paste
from textual.binding import Binding

from src.infrastructure.logging import get_logger
from ..utils.clipboard_helper import ClipboardHelper

logger = get_logger(__name__)


class MultilineInput(TextArea):
    """
    멀티라인 입력을 지원하는 커스텀 TextArea 위젯.

    Features:
        - Enter: 제출 (Submitted 메시지 발생)
        - Ctrl+R: 줄바꿈 (개행 삽입)
        - Up/Down: 입력 히스토리 탐색 (외부에서 처리)
        - Tab: 자동 완성 (AutocompleteRequested 메시지 발생)
    """

    # 키 바인딩: Ctrl+R로 줄바꿈
    BINDINGS = [
        Binding("ctrl+r", "insert_newline", "줄바꿈", priority=True),
    ]

    class Submitted(Message, bubble=True):
        """
        Enter로 입력이 제출되었을 때 발생하는 메시지.

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

    class HistoryUp(Message, bubble=True):
        """
        Up 키로 히스토리 이전 항목으로 이동 요청.

        커서가 첫 줄에 있을 때만 발생합니다.
        """
        pass

    class HistoryDown(Message, bubble=True):
        """
        Down 키로 히스토리 다음 항목으로 이동 요청.

        커서가 마지막 줄에 있을 때만 발생합니다.
        """
        pass

    class AutocompleteRequested(Message, bubble=True):
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

    class ImagePasted(Message, bubble=True):
        """
        이미지가 클립보드에서 붙여넣기되었을 때 발생하는 메시지.

        Attributes:
            file_path (str): 저장된 이미지 파일 경로
        """

        def __init__(self, file_path: str) -> None:
            """
            ImagePasted 메시지 초기화.

            Args:
                file_path: 저장된 이미지 파일 경로
            """
            super().__init__()
            self.file_path = file_path

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
        Enter 키로 입력 제출.

        on_key()에서 호출됩니다.
        입력창 초기화는 이벤트 핸들러에서 처리합니다.
        """
        logger.debug(f"[MultilineInput] action_submit_input 호출됨! text={self.text!r}")

        # 빈 입력은 무시
        if not self.text.strip():
            logger.debug("[MultilineInput] 빈 입력 무시")
            return

        # Submitted 메시지 전송
        logger.debug(f"[MultilineInput] Submitted 메시지 전송: {self.text!r}")
        self.post_message(self.Submitted(self.text))

    def action_insert_newline(self) -> None:
        """
        Ctrl+R 키로 줄바꿈 삽입.

        BINDINGS에서 자동으로 호출됩니다.
        """
        # 현재 커서 위치에 개행 문자 삽입
        self.insert("\n")

    def action_request_autocomplete(self) -> None:
        """
        Tab 키로 자동완성 요청.

        on_key()에서 호출됩니다.
        """
        self.post_message(self.AutocompleteRequested(self.text))

    async def on_key(self, event: events.Key) -> None:
        """
        키 입력 이벤트 처리.

        Enter: 제출
        Ctrl+R: 줄바꿈 (BINDINGS에서 처리)
        Tab: 자동 완성
        Up/Down: 히스토리 탐색 (첫/마지막 줄에서만)

        Args:
            event: 키 입력 이벤트
        """
        # Enter - 제출
        if event.key == "enter":
            event.prevent_default()
            event.stop()
            self.action_submit_input()
            return

        # Tab - 자동완성
        if event.key == "tab":
            event.prevent_default()
            event.stop()
            self.action_request_autocomplete()
            return

        # Up/Down 키 - 히스토리 탐색
        if event.key == "up":
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

    async def on_paste(self, event: Paste) -> None:
        """
        Paste 이벤트 처리 (텍스트 또는 이미지).

        이미지를 먼저 확인하고, 이미지가 없으면 텍스트 붙여넣기를 수행합니다.
        이미지가 발견되면 ImagePasted 메시지를 전송합니다.

        클립보드 이미지 미지원 환경에서는 자동으로 fallback되어 텍스트만 처리합니다.

        Args:
            event: Paste 이벤트
        """
        logger.info(f"[MultilineInput] on_paste 호출됨! event.text={event.text!r}")

        # 1. 먼저 이미지 확인 (우선순위 높음)
        try:
            image = ClipboardHelper.get_clipboard_image()
            if image:
                event.prevent_default()  # 기본 동작 차단
                logger.info(f"이미지 발견: {image.size}")
                try:
                    # 이미지를 임시 파일로 저장
                    file_path = ClipboardHelper.save_image_to_temp(image)
                    logger.info(f"이미지 저장 완료: {file_path}")
                    # ImagePasted 메시지 전송
                    self.post_message(self.ImagePasted(file_path))
                    logger.info(f"ImagePasted 메시지 전송 완료: {file_path}")
                finally:
                    # PIL Image 리소스 정리 보장
                    image.close()
                return

        except (RuntimeError, NotImplementedError) as e:
            # 클립보드 이미지 미지원 환경 (Pillow 미설치, Linux 등)
            logger.warning(f"이미지 붙여넣기 미지원: {e}")
            # Fallback: 텍스트 붙여넣기로 계속 진행

        except (OSError, ValueError) as e:
            # 이미지 저장 실패 또는 잘못된 이미지 형식
            logger.error(f"이미지 처리 실패: {e}", exc_info=True)
            # Fallback: 텍스트 붙여넣기로 계속 진행

        except Exception as e:
            # 예상하지 못한 오류 (버그 가능성 높음)
            logger.critical(f"예상하지 못한 오류 발생: {e}", exc_info=True)
            # Fallback: 텍스트 붙여넣기로 계속 진행

        # 2. 이미지가 없거나 처리 실패 시 텍스트 붙여넣기
        if event.text:
            logger.debug(f"텍스트 붙여넣기: {event.text!r}")
            self.insert(event.text)
        else:
            logger.debug("클립보드에 아무것도 없음")

    def clear(self) -> None:
        """입력 내용을 모두 지웁니다."""
        self.text = ""
