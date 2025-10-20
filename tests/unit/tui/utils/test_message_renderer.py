"""
MessageRenderer 단위 테스트

검증 항목:
1. render_user_message(): Panel 반환, 제목 "User", cyan border
2. render_ai_response_start(): 헤더 문자열 반환, green 스타일
3. render_ai_response_chunk():
   - 단순 텍스트: 인덴트 프리픽스 적용
   - 줄바꿈 포함 텍스트: 각 줄에 인덴트 적용
   - 빈 줄 포함 텍스트: 빈 줄은 인덴트 제외 (Warning #2 수정 검증)
4. render_ai_response_end(): 구분선 문자열 반환
5. render_error(): 에러 패널 반환
6. render_warning(): 경고 패널 반환
7. render_info(): 정보 패널 반환
"""

import pytest
from rich.panel import Panel
from rich.text import Text

from src.presentation.tui.utils.message_renderer import MessageRenderer


class TestMessageRendererUserMessage:
    """사용자 메시지 렌더링 테스트"""

    def test_render_user_message_returns_panel(self):
        """사용자 메시지가 Panel 객체로 반환되어야 함"""
        message = "Hello, world!"
        result = MessageRenderer.render_user_message(message)

        assert isinstance(result, Panel)

    def test_render_user_message_has_correct_title(self):
        """사용자 메시지 Panel의 제목이 올바른지 확인"""
        message = "Test message"
        result = MessageRenderer.render_user_message(message)

        # 제목에 User 포함 확인
        assert MessageRenderer.USER_TITLE in result.title

    def test_render_user_message_has_cyan_border(self):
        """사용자 메시지 Panel의 border가 cyan인지 확인"""
        message = "Test message"
        result = MessageRenderer.render_user_message(message)

        assert result.border_style == MessageRenderer.USER_BORDER_STYLE

    def test_render_user_message_preserves_content(self):
        """사용자 메시지 내용이 보존되는지 확인"""
        message = "This is a test message with special chars: @#$%"
        result = MessageRenderer.render_user_message(message)

        # Panel의 renderable이 Text 객체인지 확인
        assert isinstance(result.renderable, Text)
        # 메시지 내용이 포함되어 있는지 확인
        assert str(result.renderable).strip() == message

    def test_render_user_message_with_emoji(self):
        """이모지가 포함된 사용자 메시지 처리 확인"""
        message = "Hello 👋 World 🌍"
        result = MessageRenderer.render_user_message(message)

        assert isinstance(result, Panel)
        assert message in str(result.renderable)


class TestMessageRendererAIResponseStart:
    """AI 응답 시작 헤더 렌더링 테스트"""

    def test_render_ai_response_start_returns_string(self):
        """AI 응답 시작이 문자열로 반환되어야 함"""
        result = MessageRenderer.render_ai_response_start()

        assert isinstance(result, str)

    def test_render_ai_response_start_contains_assistant_title(self):
        """AI 응답 시작 헤더에 Assistant 제목이 포함되어야 함"""
        result = MessageRenderer.render_ai_response_start()

        assert MessageRenderer.AI_TITLE in result

    def test_render_ai_response_start_has_green_style(self):
        """AI 응답 시작 헤더에 green 스타일이 포함되어야 함"""
        result = MessageRenderer.render_ai_response_start()

        assert MessageRenderer.AI_BORDER_STYLE in result

    def test_render_ai_response_start_has_rich_markup(self):
        """AI 응답 시작 헤더가 Rich 마크업을 포함해야 함"""
        result = MessageRenderer.render_ai_response_start()

        # Rich 마크업 태그 확인 ([bold ...])
        assert "[bold" in result
        assert "[/bold" in result


class TestMessageRendererAIResponseChunk:
    """AI 응답 청크 렌더링 테스트"""

    def test_render_ai_response_chunk_simple_text(self):
        """단순 텍스트에 인덴트 프리픽스가 적용되어야 함"""
        renderer = MessageRenderer()
        chunk = "This is a simple response."
        result = renderer.render_ai_response_chunk(chunk)

        expected = f"{MessageRenderer.INDENT_PREFIX}{chunk}"
        assert result == expected

    def test_render_ai_response_chunk_with_newline(self):
        """줄바꿈 포함 텍스트의 각 줄에 인덴트가 적용되어야 함"""
        renderer = MessageRenderer()
        chunk = "Line 1\nLine 2\nLine 3"
        result = renderer.render_ai_response_chunk(chunk)

        lines = result.split("\n")
        assert len(lines) == 3
        assert lines[0] == f"{MessageRenderer.INDENT_PREFIX}Line 1"
        assert lines[1] == f"{MessageRenderer.INDENT_PREFIX}Line 2"
        assert lines[2] == f"{MessageRenderer.INDENT_PREFIX}Line 3"

    def test_render_ai_response_chunk_with_empty_lines(self):
        """빈 줄은 인덴트 프리픽스가 제외되어야 함 (Warning #2 수정 검증)"""
        renderer = MessageRenderer()
        chunk = "Line 1\n\nLine 3"
        result = renderer.render_ai_response_chunk(chunk)

        lines = result.split("\n")
        assert len(lines) == 3
        assert lines[0] == f"{MessageRenderer.INDENT_PREFIX}Line 1"
        assert lines[1] == ""  # 빈 줄은 인덴트 없음
        assert lines[2] == f"{MessageRenderer.INDENT_PREFIX}Line 3"

    def test_render_ai_response_chunk_with_multiple_empty_lines(self):
        """여러 빈 줄이 연속으로 있을 때 처리 확인"""
        renderer = MessageRenderer()
        chunk = "Line 1\n\n\nLine 4"
        result = renderer.render_ai_response_chunk(chunk)

        lines = result.split("\n")
        assert len(lines) == 4
        assert lines[0] == f"{MessageRenderer.INDENT_PREFIX}Line 1"
        assert lines[1] == ""
        assert lines[2] == ""
        assert lines[3] == f"{MessageRenderer.INDENT_PREFIX}Line 4"

    def test_render_ai_response_chunk_with_whitespace_only_line(self):
        """공백만 있는 줄은 빈 줄로 처리되어야 함"""
        renderer = MessageRenderer()
        chunk = "Line 1\n   \nLine 3"
        result = renderer.render_ai_response_chunk(chunk)

        lines = result.split("\n")
        assert len(lines) == 3
        assert lines[0] == f"{MessageRenderer.INDENT_PREFIX}Line 1"
        assert lines[1] == ""  # 공백만 있는 줄도 빈 줄 처리
        assert lines[2] == f"{MessageRenderer.INDENT_PREFIX}Line 3"

    def test_render_ai_response_chunk_empty_string(self):
        """빈 문자열 처리 확인"""
        renderer = MessageRenderer()
        chunk = ""
        result = renderer.render_ai_response_chunk(chunk)

        # 빈 문자열은 인덴트 프리픽스만 반환
        assert result == f"{MessageRenderer.INDENT_PREFIX}"

    def test_render_ai_response_chunk_preserves_leading_spaces(self):
        """줄의 앞쪽 공백은 보존되어야 함 (코드 블록 등)"""
        renderer = MessageRenderer()
        chunk = "def foo():\n    print('hello')"
        result = renderer.render_ai_response_chunk(chunk)

        lines = result.split("\n")
        assert len(lines) == 2
        assert lines[0] == f"{MessageRenderer.INDENT_PREFIX}def foo():"
        # 원래 공백 4개 + 인덴트 프리픽스
        assert lines[1] == f"{MessageRenderer.INDENT_PREFIX}    print('hello')"


class TestMessageRendererAIResponseEnd:
    """AI 응답 종료 구분선 렌더링 테스트"""

    def test_render_ai_response_end_returns_string(self):
        """AI 응답 종료가 문자열로 반환되어야 함"""
        result = MessageRenderer.render_ai_response_end()

        assert isinstance(result, str)

    def test_render_ai_response_end_contains_separator(self):
        """AI 응답 종료 구분선이 포함되어야 함"""
        result = MessageRenderer.render_ai_response_end()

        assert MessageRenderer.SEPARATOR in result

    def test_render_ai_response_end_has_green_style(self):
        """AI 응답 종료가 green 스타일을 포함해야 함"""
        result = MessageRenderer.render_ai_response_end()

        assert MessageRenderer.AI_BORDER_STYLE in result

    def test_render_ai_response_end_has_rich_markup(self):
        """AI 응답 종료가 Rich 마크업을 포함해야 함"""
        result = MessageRenderer.render_ai_response_end()

        # Rich 마크업 태그 확인 ([...] 형식)
        assert result.startswith("[")
        assert result.endswith("]")


class TestMessageRendererErrorPanel:
    """에러 메시지 패널 렌더링 테스트"""

    def test_render_error_returns_panel(self):
        """에러 메시지가 Panel 객체로 반환되어야 함"""
        error_message = "An error occurred"
        result = MessageRenderer.render_error(error_message)

        assert isinstance(result, Panel)

    def test_render_error_has_red_border(self):
        """에러 패널의 border가 red인지 확인"""
        error_message = "Test error"
        result = MessageRenderer.render_error(error_message)

        assert result.border_style == "red"

    def test_render_error_has_error_title(self):
        """에러 패널의 제목에 Error가 포함되는지 확인"""
        error_message = "Test error"
        result = MessageRenderer.render_error(error_message)

        assert "Error" in result.title

    def test_render_error_preserves_content(self):
        """에러 메시지 내용이 보존되는지 확인"""
        error_message = "File not found: /path/to/file"
        result = MessageRenderer.render_error(error_message)

        assert isinstance(result.renderable, Text)
        assert str(result.renderable).strip() == error_message


class TestMessageRendererWarningPanel:
    """경고 메시지 패널 렌더링 테스트"""

    def test_render_warning_returns_panel(self):
        """경고 메시지가 Panel 객체로 반환되어야 함"""
        warning_message = "This is a warning"
        result = MessageRenderer.render_warning(warning_message)

        assert isinstance(result, Panel)

    def test_render_warning_has_yellow_border(self):
        """경고 패널의 border가 yellow인지 확인"""
        warning_message = "Test warning"
        result = MessageRenderer.render_warning(warning_message)

        assert result.border_style == "yellow"

    def test_render_warning_has_warning_title(self):
        """경고 패널의 제목에 Warning이 포함되는지 확인"""
        warning_message = "Test warning"
        result = MessageRenderer.render_warning(warning_message)

        assert "Warning" in result.title

    def test_render_warning_preserves_content(self):
        """경고 메시지 내용이 보존되는지 확인"""
        warning_message = "Configuration may be outdated"
        result = MessageRenderer.render_warning(warning_message)

        assert isinstance(result.renderable, Text)
        assert str(result.renderable).strip() == warning_message


class TestMessageRendererInfoPanel:
    """정보 메시지 패널 렌더링 테스트"""

    def test_render_info_returns_panel(self):
        """정보 메시지가 Panel 객체로 반환되어야 함"""
        info_message = "This is information"
        result = MessageRenderer.render_info(info_message)

        assert isinstance(result, Panel)

    def test_render_info_has_blue_border(self):
        """정보 패널의 border가 blue인지 확인"""
        info_message = "Test info"
        result = MessageRenderer.render_info(info_message)

        assert result.border_style == "blue"

    def test_render_info_has_info_title(self):
        """정보 패널의 제목에 Info가 포함되는지 확인"""
        info_message = "Test info"
        result = MessageRenderer.render_info(info_message)

        assert "Info" in result.title

    def test_render_info_preserves_content(self):
        """정보 메시지 내용이 보존되는지 확인"""
        info_message = "Session initialized successfully"
        result = MessageRenderer.render_info(info_message)

        assert isinstance(result.renderable, Text)
        assert str(result.renderable).strip() == info_message


class TestMessageRendererIntegration:
    """MessageRenderer 통합 테스트"""

    def test_full_conversation_flow(self):
        """전체 대화 흐름 시뮬레이션"""
        renderer = MessageRenderer()

        # 1. 사용자 메시지
        user_msg = MessageRenderer.render_user_message("Hello, AI!")
        assert isinstance(user_msg, Panel)

        # 2. AI 응답 시작
        ai_start = MessageRenderer.render_ai_response_start()
        assert isinstance(ai_start, str)

        # 3. AI 응답 청크들
        chunk1 = renderer.render_ai_response_chunk("Hello!")
        chunk2 = renderer.render_ai_response_chunk("How can I help you?")
        assert MessageRenderer.INDENT_PREFIX in chunk1
        assert MessageRenderer.INDENT_PREFIX in chunk2

        # 4. AI 응답 종료
        ai_end = MessageRenderer.render_ai_response_end()
        assert isinstance(ai_end, str)

    def test_streaming_response_with_code_block(self):
        """코드 블록을 포함한 스트리밍 응답 시뮬레이션 (Warning #1 수정 검증)"""
        renderer = MessageRenderer()

        # 코드 블록 형태의 청크
        code_chunk = "Here's a Python example:\n\ndef hello():\n    print('world')\n\nThat's it!"
        result = renderer.render_ai_response_chunk(code_chunk)

        lines = result.split("\n")

        # 모든 비어있지 않은 줄에 인덴트가 적용되어야 함
        assert lines[0] == f"{MessageRenderer.INDENT_PREFIX}Here's a Python example:"
        assert lines[1] == ""  # 빈 줄
        assert lines[2] == f"{MessageRenderer.INDENT_PREFIX}def hello():"
        assert lines[3] == f"{MessageRenderer.INDENT_PREFIX}    print('world')"
        assert lines[4] == ""  # 빈 줄
        assert lines[5] == f"{MessageRenderer.INDENT_PREFIX}That's it!"

    def test_consistent_indentation_across_chunks(self):
        """여러 청크에 걸쳐 일관된 인덴트 적용 확인 (Warning #1 수정 검증)"""
        renderer = MessageRenderer()
        chunks = [
            "First line",
            "\nSecond line",
            "\n\nThird line after empty",
        ]

        results = [renderer.render_ai_response_chunk(chunk) for chunk in chunks]

        # 각 청크의 결과 확인
        assert results[0] == f"{MessageRenderer.INDENT_PREFIX}First line"

        # 두 번째 청크: 줄바꿈으로 시작
        lines1 = results[1].split("\n")
        assert lines1[0] == ""  # 빈 줄 (줄바꿈 문자)
        assert lines1[1] == f"{MessageRenderer.INDENT_PREFIX}Second line"

        # 세 번째 청크: 빈 줄 포함
        lines2 = results[2].split("\n")
        assert lines2[0] == ""
        assert lines2[1] == ""
        assert lines2[2] == f"{MessageRenderer.INDENT_PREFIX}Third line after empty"


class TestMessageRendererConstants:
    """MessageRenderer 상수 정의 테스트"""

    def test_constants_are_defined(self):
        """모든 필요한 상수가 정의되어 있는지 확인"""
        assert hasattr(MessageRenderer, "USER_BORDER_STYLE")
        assert hasattr(MessageRenderer, "USER_EMOJI")
        assert hasattr(MessageRenderer, "USER_TITLE")
        assert hasattr(MessageRenderer, "AI_BORDER_STYLE")
        assert hasattr(MessageRenderer, "AI_EMOJI")
        assert hasattr(MessageRenderer, "AI_TITLE")
        assert hasattr(MessageRenderer, "INDENT_PREFIX")
        assert hasattr(MessageRenderer, "SEPARATOR")

    def test_constants_have_correct_types(self):
        """상수들의 타입이 올바른지 확인"""
        assert isinstance(MessageRenderer.USER_BORDER_STYLE, str)
        assert isinstance(MessageRenderer.USER_EMOJI, str)
        assert isinstance(MessageRenderer.USER_TITLE, str)
        assert isinstance(MessageRenderer.AI_BORDER_STYLE, str)
        assert isinstance(MessageRenderer.AI_EMOJI, str)
        assert isinstance(MessageRenderer.AI_TITLE, str)
        assert isinstance(MessageRenderer.INDENT_PREFIX, str)
        assert isinstance(MessageRenderer.SEPARATOR, str)

    def test_indent_prefix_format(self):
        """인덴트 프리픽스 형식이 올바른지 확인"""
        # "│ " 형태여야 함
        assert MessageRenderer.INDENT_PREFIX == "│ "

    def test_separator_format(self):
        """구분선 형식이 올바른지 확인"""
        # "└" + "─" * n 형태여야 함
        assert MessageRenderer.SEPARATOR.startswith("└")
        assert "─" in MessageRenderer.SEPARATOR


class TestMessageRendererTextWrapping:
    """텍스트 자동 줄바꿈 기능 테스트"""

    def test_wrap_text_stateful_code_block_across_chunks(self):
        """스트리밍 청크 간 코드 블록 상태 유지 테스트 (최우선)"""
        renderer = MessageRenderer()

        # 첫 번째 청크: 코드 블록 시작
        chunk1 = "```python\ndef foo():"
        result1 = renderer._wrap_text_stateful(chunk1, max_width=80)
        assert renderer.in_code_block is True
        # 코드 블록 시작 라인과 코드 내용이 올바르게 처리됨
        assert "```python" in result1
        assert "def foo():" in result1

        # 두 번째 청크: 코드 블록 내부
        chunk2 = "    return 42"
        result2 = renderer._wrap_text_stateful(chunk2, max_width=80)
        assert renderer.in_code_block is True
        # 코드 블록 내부는 줄바꿈 없이 인덴트 유지
        assert "    return 42" in result2

        # 세 번째 청크: 코드 블록 종료
        chunk3 = "```"
        result3 = renderer._wrap_text_stateful(chunk3, max_width=80)
        assert renderer.in_code_block is False
        assert "```" in result3

    def test_wrap_text_stateful_multiple_code_blocks(self):
        """여러 코드 블록 간 상태 전환 테스트"""
        renderer = MessageRenderer()

        # 첫 번째 코드 블록
        chunk1 = "```python\nprint('hello')\n```"
        result1 = renderer._wrap_text_stateful(chunk1, max_width=80)
        assert renderer.in_code_block is False

        # 일반 텍스트
        chunk2 = "Some text"
        result2 = renderer._wrap_text_stateful(chunk2, max_width=80)
        assert renderer.in_code_block is False

        # 두 번째 코드 블록 시작
        chunk3 = "```javascript\nconst x = 1;"
        result3 = renderer._wrap_text_stateful(chunk3, max_width=80)
        assert renderer.in_code_block is True

        # 두 번째 코드 블록 종료
        chunk4 = "```"
        result4 = renderer._wrap_text_stateful(chunk4, max_width=80)
        assert renderer.in_code_block is False

    def test_reset_state(self):
        """reset_state() 호출 시 상태가 초기화되는지 검증"""
        renderer = MessageRenderer()

        # 코드 블록 상태로 변경
        chunk = "```python\ndef foo():"
        renderer._wrap_text_stateful(chunk, max_width=80)
        assert renderer.in_code_block is True

        # 상태 리셋
        renderer.reset_state()
        assert renderer.in_code_block is False

    def test_long_text_wrapping(self):
        """긴 텍스트가 올바르게 줄바꿈되는지 검증"""
        renderer = MessageRenderer()

        # 80자를 초과하는 긴 텍스트
        long_text = "This is a very long line of text that should be wrapped because it exceeds the maximum width specified for the output area in the TUI application."
        result = renderer._wrap_text_stateful(long_text, max_width=80)

        lines = result.split("\n")
        # 여러 줄로 분할되어야 함
        assert len(lines) > 1

        # 각 줄이 max_width를 초과하지 않아야 함
        for line in lines:
            assert len(line) <= 80

    def test_long_text_wrapping_with_indent_prefix(self):
        """인덴트 프리픽스가 각 줄에 추가되는지 확인"""
        renderer = MessageRenderer()

        # 긴 텍스트
        long_text = "This is a very long line of text that should be wrapped and each wrapped line should have the indent prefix added."
        result = renderer._wrap_text_stateful(long_text, max_width=50)

        lines = result.split("\n")
        # 모든 줄이 인덴트 프리픽스로 시작해야 함
        for line in lines:
            if line:  # 빈 줄이 아닌 경우
                assert line.startswith(MessageRenderer.INDENT_PREFIX)

    def test_wrap_text_empty_string(self):
        """빈 문자열 처리"""
        renderer = MessageRenderer()

        result = renderer._wrap_text_stateful("", max_width=80)
        # 빈 문자열은 빈 줄로 처리
        assert result == ""

    def test_wrap_text_max_width_none(self):
        """max_width가 None인 경우 (정적 메서드 테스트)"""
        text = "This is a long text that should not be wrapped when max_width is None."
        result = MessageRenderer.wrap_text(text, max_width=None)

        # 줄바꿈이 일어나지 않아야 함
        assert result == text

    def test_wrap_text_max_width_zero(self):
        """max_width가 0인 경우"""
        renderer = MessageRenderer()

        text = "Some text"
        result = renderer._wrap_text_stateful(text, max_width=0)

        # max_width가 0이면 원본 반환
        assert result == text

    def test_wrap_text_max_width_very_small(self):
        """max_width가 매우 작은 경우 (인덴트 프리픽스보다 작음)"""
        renderer = MessageRenderer()

        text = "Short text"
        # INDENT_PREFIX는 "│ " (2자)이므로 max_width=5면 effective_width=3
        result = renderer._wrap_text_stateful(text, max_width=5)

        # 에러 없이 처리되어야 함
        assert result is not None
        # 인덴트 프리픽스가 포함되어야 함
        assert MessageRenderer.INDENT_PREFIX in result

    def test_wrap_text_preserves_newlines(self):
        """텍스트 내의 기존 줄바꿈이 보존되는지 확인"""
        renderer = MessageRenderer()

        text = "Line 1\nLine 2\nLine 3"
        result = renderer._wrap_text_stateful(text, max_width=80)

        lines = result.split("\n")
        assert len(lines) == 3
        # 각 줄이 인덴트되어야 함
        assert lines[0].strip().endswith("Line 1")
        assert lines[1].strip().endswith("Line 2")
        assert lines[2].strip().endswith("Line 3")

    def test_wrap_text_code_block_no_wrapping(self):
        """코드 블록 내부는 줄바꿈되지 않는지 확인"""
        renderer = MessageRenderer()

        # 매우 긴 코드 라인
        long_code = "```python\nthis_is_a_very_long_line_of_code_that_would_normally_be_wrapped_but_should_not_be_wrapped_inside_code_blocks = 42\n```"
        result = renderer._wrap_text_stateful(long_code, max_width=50)

        # 코드 블록 상태가 올바르게 종료되었는지 확인
        assert renderer.in_code_block is False

        # 긴 코드 라인이 그대로 유지되어야 함
        assert "this_is_a_very_long_line_of_code" in result

    def test_render_ai_response_chunk_with_max_width(self):
        """render_ai_response_chunk()에서 max_width 사용 테스트"""
        renderer = MessageRenderer()

        # 긴 텍스트
        long_text = "This is a very long response from the AI that should be wrapped automatically when max_width is specified."
        result = renderer.render_ai_response_chunk(long_text, max_width=50)

        lines = result.split("\n")
        # 여러 줄로 분할되어야 함
        assert len(lines) > 1

        # 각 줄이 max_width를 초과하지 않아야 함
        for line in lines:
            assert len(line) <= 50

    def test_render_ai_response_chunk_code_block_streaming(self):
        """코드 블록 스트리밍 시나리오 테스트"""
        renderer = MessageRenderer()

        # 스트리밍 청크 1: 코드 블록 시작
        chunk1 = "Here is some code:\n```python"
        result1 = renderer.render_ai_response_chunk(chunk1, max_width=80)
        assert renderer.in_code_block is True

        # 스트리밍 청크 2: 코드 내용
        chunk2 = "\ndef calculate_sum(a, b):"
        result2 = renderer.render_ai_response_chunk(chunk2, max_width=80)
        assert renderer.in_code_block is True

        # 스트리밍 청크 3: 코드 계속
        chunk3 = "\n    return a + b"
        result3 = renderer.render_ai_response_chunk(chunk3, max_width=80)
        assert renderer.in_code_block is True

        # 스트리밍 청크 4: 코드 블록 종료
        chunk4 = "\n```"
        result4 = renderer.render_ai_response_chunk(chunk4, max_width=80)
        assert renderer.in_code_block is False

        # 스트리밍 청크 5: 일반 텍스트
        chunk5 = "\nThat's the function!"
        result5 = renderer.render_ai_response_chunk(chunk5, max_width=80)
        assert renderer.in_code_block is False

    def test_static_wrap_text_with_indent_prefix(self):
        """정적 wrap_text 메서드의 indent_prefix 기능 테스트"""
        text = "This is a long line that needs to be wrapped with a custom indent prefix."
        custom_prefix = "  > "
        result = MessageRenderer.wrap_text(text, max_width=40, indent_prefix=custom_prefix)

        lines = result.split("\n")
        # 모든 줄이 custom_prefix로 시작해야 함
        for line in lines:
            if line:
                assert line.startswith(custom_prefix)

    def test_static_wrap_text_code_block_detection(self):
        """정적 wrap_text 메서드의 코드 블록 감지 테스트"""
        text = "Normal text\n```python\nlong_code_line_that_should_not_wrap = 12345678901234567890\n```\nMore text"
        result = MessageRenderer.wrap_text(text, max_width=40, indent_prefix="")

        # 코드 블록 내용이 줄바꿈되지 않아야 함
        assert "long_code_line_that_should_not_wrap" in result


class TestMessageRendererRichMarkup:
    """Rich 마크업 보존 테스트"""

    def test_wrap_text_preserves_rich_markup(self):
        """Rich 마크업이 포함된 텍스트 처리 테스트"""
        renderer = MessageRenderer()

        # Rich 마크업 포함 텍스트
        text = "[bold]This is bold text[/bold] and [green]this is green[/green]."
        result = renderer._wrap_text_stateful(text, max_width=80)

        # 마크업이 보존되어야 함
        assert "[bold]" in result
        assert "[/bold]" in result
        assert "[green]" in result
        assert "[/green]" in result

    def test_render_ai_response_chunk_preserves_markup(self):
        """render_ai_response_chunk()가 Rich 마크업을 보존하는지 확인"""
        renderer = MessageRenderer()

        chunk = "[bold cyan]Important:[/bold cyan] This is a message."
        result = renderer.render_ai_response_chunk(chunk, max_width=None)

        # 마크업이 보존되어야 함
        assert "[bold cyan]" in result
        assert "[/bold cyan]" in result
