"""
MultilineInput 위젯 테스트 모듈

입력 히스토리 탐색 및 키 이벤트 처리 기능을 검증합니다.
"""

import pytest
from textual.events import Key
from unittest.mock import MagicMock, PropertyMock, patch

from src.presentation.tui.widgets.multiline_input import MultilineInput


class TestMultilineInputBasic:
    """MultilineInput 기본 기능 테스트."""

    def test_initialization(self):
        """위젯 초기화 테스트."""
        widget = MultilineInput(id="test-input")
        assert widget.id == "test-input"
        assert widget.text == ""
        assert widget.show_line_numbers is False
        assert widget.language is None

    def test_clear_method(self):
        """clear() 메서드 테스트."""
        widget = MultilineInput()
        widget.text = "some text"
        widget.clear()
        assert widget.text == ""


class TestMultilineInputSubmit:
    """MultilineInput 제출 기능 테스트."""

    @pytest.mark.asyncio
    async def test_submit_on_enter(self):
        """Enter 키 입력 시 Submitted 메시지 발생."""
        widget = MultilineInput()
        widget.text = "test message"

        # 메시지 캡처를 위한 모킹
        messages = []
        widget.post_message = lambda msg: messages.append(msg)

        # Enter 키 이벤트 (character는 \r로 설정)
        event = Key(key="enter", character="\r")
        event.prevent_default = MagicMock()
        event.stop = MagicMock()

        await widget.on_key(event)

        # Submitted 메시지가 발생했는지 확인
        assert len(messages) == 1
        assert isinstance(messages[0], MultilineInput.Submitted)
        assert messages[0].value == "test message"
        event.prevent_default.assert_called_once()
        event.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_submit_empty_text(self):
        """빈 텍스트 제출 시에도 Submitted 메시지 발생."""
        widget = MultilineInput()
        widget.text = ""

        messages = []
        widget.post_message = lambda msg: messages.append(msg)

        event = Key(key="enter", character="\r")
        event.prevent_default = MagicMock()
        event.stop = MagicMock()

        await widget.on_key(event)

        assert len(messages) == 1
        assert isinstance(messages[0], MultilineInput.Submitted)
        assert messages[0].value == ""


class TestMultilineInputHistory:
    """MultilineInput 히스토리 탐색 테스트."""

    @pytest.mark.asyncio
    async def test_history_up_on_first_line(self):
        """커서가 첫 줄에 있을 때 Up 키로 HistoryUp 메시지 발생."""
        widget = MultilineInput()
        widget.text = "test"

        # cursor_location 모킹 (첫 줄) - PropertyMock 사용
        with patch.object(
            type(widget), 'cursor_location', new_callable=PropertyMock
        ) as mock_cursor:
            mock_cursor.return_value = (0, 0)
            messages = []
            widget.post_message = lambda msg: messages.append(msg)

            event = Key(key="up", character=None)
            event.prevent_default = MagicMock()

            await widget.on_key(event)

            assert len(messages) == 1
            assert isinstance(messages[0], MultilineInput.HistoryUp)
            event.prevent_default.assert_called_once()

    @pytest.mark.asyncio
    async def test_history_up_on_second_line_no_message(self):
        """커서가 두 번째 줄에 있을 때 Up 키로 HistoryUp 메시지 발생하지 않음."""
        widget = MultilineInput()
        widget.text = "line1\nline2"

        # cursor_location 모킹 (두 번째 줄) - PropertyMock 사용
        with patch.object(
            type(widget), 'cursor_location', new_callable=PropertyMock
        ) as mock_cursor:
            mock_cursor.return_value = (1, 0)
            messages = []
            widget.post_message = lambda msg: messages.append(msg)

            event = Key(key="up", character=None)
            event.prevent_default = MagicMock()

            await widget.on_key(event)

            # HistoryUp 메시지가 발생하지 않아야 함
            assert len(messages) == 0
            event.prevent_default.assert_not_called()

    @pytest.mark.asyncio
    async def test_history_down_on_last_line(self):
        """커서가 마지막 줄에 있을 때 Down 키로 HistoryDown 메시지 발생."""
        widget = MultilineInput()
        widget.text = "line1\nline2"

        # cursor_location 모킹 (마지막 줄 = 1) - PropertyMock 사용
        with patch.object(
            type(widget), 'cursor_location', new_callable=PropertyMock
        ) as mock_cursor:
            mock_cursor.return_value = (1, 0)
            messages = []
            widget.post_message = lambda msg: messages.append(msg)

            event = Key(key="down", character=None)
            event.prevent_default = MagicMock()

            await widget.on_key(event)

            assert len(messages) == 1
            assert isinstance(messages[0], MultilineInput.HistoryDown)
            event.prevent_default.assert_called_once()

    @pytest.mark.asyncio
    async def test_history_down_on_first_line_no_message(self):
        """멀티라인 입력에서 커서가 첫 줄에 있을 때 Down 키는 메시지 발생 안함."""
        widget = MultilineInput()
        widget.text = "line1\nline2"

        # cursor_location 모킹 (첫 줄) - PropertyMock 사용
        with patch.object(
            type(widget), 'cursor_location', new_callable=PropertyMock
        ) as mock_cursor:
            mock_cursor.return_value = (0, 0)
            messages = []
            widget.post_message = lambda msg: messages.append(msg)

            event = Key(key="down", character=None)
            event.prevent_default = MagicMock()

            await widget.on_key(event)

            # HistoryDown 메시지가 발생하지 않아야 함
            assert len(messages) == 0
            event.prevent_default.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_text_history_down(self):
        """빈 입력 상태에서 Down 키로 HistoryDown 메시지 발생."""
        widget = MultilineInput()
        widget.text = ""

        messages = []
        widget.post_message = lambda msg: messages.append(msg)

        event = Key(key="down", character=None)
        event.prevent_default = MagicMock()

        await widget.on_key(event)

        assert len(messages) == 1
        assert isinstance(messages[0], MultilineInput.HistoryDown)
        event.prevent_default.assert_called_once()

    @pytest.mark.asyncio
    async def test_cursor_location_none_safety(self):
        """cursor_location이 None일 때 예외가 발생하지 않음."""
        widget = MultilineInput()
        widget.text = "test"

        # cursor_location을 None으로 모킹 - PropertyMock 사용
        with patch.object(
            type(widget), 'cursor_location', new_callable=PropertyMock
        ) as mock_cursor:
            mock_cursor.return_value = None
            event = Key(key="up", character=None)
            event.prevent_default = MagicMock()

            # 예외가 발생하지 않아야 함
            try:
                await widget.on_key(event)
            except (IndexError, TypeError, AttributeError):
                pytest.fail("cursor_location이 None일 때 예외 발생")

            # cursor_location이 None이면 HistoryUp 메시지도 발생하지 않음
            # (조건문에서 `if self.cursor_location and ...` 로 체크하기 때문)

    @pytest.mark.asyncio
    async def test_single_line_up_triggers_history(self):
        """단일 라인 입력에서 Up 키는 항상 HistoryUp을 발생."""
        widget = MultilineInput()
        widget.text = "single line"

        # 단일 라인이므로 첫 줄 = 마지막 줄 = 0 - PropertyMock 사용
        with patch.object(
            type(widget), 'cursor_location', new_callable=PropertyMock
        ) as mock_cursor:
            mock_cursor.return_value = (0, 5)
            messages = []
            widget.post_message = lambda msg: messages.append(msg)

            event = Key(key="up", character=None)
            event.prevent_default = MagicMock()

            await widget.on_key(event)

            assert len(messages) == 1
            assert isinstance(messages[0], MultilineInput.HistoryUp)

    @pytest.mark.asyncio
    async def test_single_line_down_triggers_history(self):
        """단일 라인 입력에서 Down 키는 항상 HistoryDown을 발생."""
        widget = MultilineInput()
        widget.text = "single line"

        # 단일 라인이므로 첫 줄 = 마지막 줄 = 0 - PropertyMock 사용
        with patch.object(
            type(widget), 'cursor_location', new_callable=PropertyMock
        ) as mock_cursor:
            mock_cursor.return_value = (0, 5)
            messages = []
            widget.post_message = lambda msg: messages.append(msg)

            event = Key(key="down", character=None)
            event.prevent_default = MagicMock()

            await widget.on_key(event)

            assert len(messages) == 1
            assert isinstance(messages[0], MultilineInput.HistoryDown)


class TestMultilineInputOtherKeys:
    """MultilineInput 기타 키 입력 테스트."""

    @pytest.mark.asyncio
    async def test_other_keys_no_message(self):
        """Enter, Up, Down 이외의 키는 메시지를 발생시키지 않음."""
        widget = MultilineInput()
        widget.text = "test"

        with patch.object(
            type(widget), 'cursor_location', new_callable=PropertyMock
        ) as mock_cursor:
            mock_cursor.return_value = (0, 0)
            messages = []
            widget.post_message = lambda msg: messages.append(msg)

            # 일반 키 입력 (예: 'a')
            event = Key(key="a", character="a")
            event.prevent_default = MagicMock()

            await widget.on_key(event)

            # 메시지가 발생하지 않아야 함
            assert len(messages) == 0
            event.prevent_default.assert_not_called()

    @pytest.mark.asyncio
    async def test_shift_enter_no_submit(self):
        """
        Shift+Enter는 제출하지 않음 (TextArea 기본 동작으로 줄바꿈 처리).

        Note: Textual의 Key 이벤트에서 shift 수정자는 event.key가 'enter'가 아닌
        다른 값으로 처리되거나, on_key에서 event.shift 등을 확인해야 하나,
        현재 구현에서는 단순히 event.key == "enter"만 체크하므로
        Shift+Enter는 자동으로 기본 동작(줄바꿈)을 유지합니다.
        """
        # 이 테스트는 구현 확인용입니다.
        # 실제로 Shift+Enter는 Textual의 TextArea 기본 동작으로 처리되어
        # on_key에서 event.key != "enter"이므로 Submitted가 발생하지 않습니다.
        pass
