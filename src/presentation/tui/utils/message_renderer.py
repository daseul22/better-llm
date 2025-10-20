"""TUI 메시지 렌더링 유틸리티

이 모듈은 TUI에서 사용자 메시지와 AI 응답을 시각적으로 렌더링하는 기능을 제공합니다.
"""

import textwrap
from typing import Optional
from rich.panel import Panel
from rich.text import Text
from rich.box import ROUNDED


class MessageRenderer:
    """메시지 렌더링 유틸리티 클래스

    사용자 메시지와 AI 응답을 Rich 포맷으로 렌더링합니다.
    스트리밍 청크 간 코드 블록 상태를 유지하기 위해 인스턴스로 사용합니다.
    """

    # 스타일 상수
    USER_BORDER_STYLE = "cyan"
    USER_EMOJI = "👤"
    USER_TITLE = "User"

    AI_BORDER_STYLE = "green"
    AI_EMOJI = "🤖"
    AI_TITLE = "Assistant"

    INDENT_PREFIX = "│ "
    SEPARATOR = "└" + "─" * 78

    # 줄바꿈 관련 상수
    OUTPUT_LOG_PADDING = 7  # padding(1)*2 + scrollbar(1) + border(2) + indent(2)
    MIN_OUTPUT_WIDTH = 40   # 최소 출력 너비

    def __init__(self):
        """MessageRenderer 인스턴스를 초기화합니다.

        코드 블록 상태를 유지하기 위해 인스턴스 변수를 사용합니다.
        """
        self.in_code_block = False  # 코드 블록 내부 여부 추적

    @staticmethod
    def wrap_text(
        text: str,
        max_width: Optional[int] = None,
        indent_prefix: str = ""
    ) -> str:
        """텍스트를 지정된 너비로 줄바꿈합니다.

        Args:
            text: 줄바꿈할 텍스트
            max_width: 최대 너비 (None이면 줄바꿈하지 않음)
            indent_prefix: 각 줄 앞에 추가할 프리픽스

        Returns:
            str: 줄바꿈된 텍스트

        Raises:
            ValueError: max_width가 너무 작은 경우
        """
        if max_width is None or max_width <= 0:
            return text

        # 코드 블록 감지
        in_code_block = False
        lines = text.split("\n")
        result = []

        for line in lines:
            # 코드 블록 시작/종료 감지
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                result.append(indent_prefix + line)
                continue

            # 코드 블록 내부는 줄바꿈하지 않음
            if in_code_block:
                result.append(indent_prefix + line)
                continue

            # 일반 텍스트는 줄바꿈 적용
            if line:
                # indent_prefix를 고려한 실제 사용 가능 너비
                effective_width = max_width - len(indent_prefix)
                if effective_width > 0:
                    try:
                        # textwrap.wrap() 사용하여 줄바꿈
                        wrapped_lines = textwrap.wrap(
                            line,
                            width=effective_width,
                            break_long_words=False,
                            break_on_hyphens=False
                        )
                        if wrapped_lines:
                            # 첫 번째 줄
                            result.append(indent_prefix + wrapped_lines[0])
                            # 나머지 줄들
                            for wrapped_line in wrapped_lines[1:]:
                                result.append(indent_prefix + wrapped_line)
                        else:
                            # wrap() 결과가 빈 리스트인 경우 (빈 줄)
                            result.append(indent_prefix + line)
                    except (AttributeError, ValueError) as e:
                        # textwrap 에러 발생 시 로깅 후 원본 유지
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.warning(f"텍스트 줄바꿈 실패: {e}, 원본 유지")
                        result.append(indent_prefix + line)
                else:
                    result.append(indent_prefix + line)
            else:
                # 빈 줄은 그대로 유지
                result.append("")

        return "\n".join(result)

    @staticmethod
    def render_user_message(message: str) -> Panel:
        """사용자 메시지를 패널로 렌더링합니다.

        Args:
            message: 사용자가 입력한 메시지

        Returns:
            Panel: 스타일이 적용된 Rich Panel 객체
        """
        text = Text(message)
        return Panel(
            text,
            title=f"{MessageRenderer.USER_EMOJI} {MessageRenderer.USER_TITLE}",
            border_style=MessageRenderer.USER_BORDER_STYLE,
            box=ROUNDED,
            padding=(0, 1),
        )

    @staticmethod
    def render_ai_response_start() -> str:
        """AI 응답 시작 헤더를 반환합니다.

        RichLog에서 Panel을 스트리밍할 수 없으므로, 헤더만 텍스트로 반환합니다.

        Returns:
            str: AI 응답 시작 헤더 (Rich 마크업 포함)
        """
        return f"[bold {MessageRenderer.AI_BORDER_STYLE}]{MessageRenderer.AI_EMOJI} {MessageRenderer.AI_TITLE}[/bold {MessageRenderer.AI_BORDER_STYLE}]"

    def render_ai_response_chunk(self, chunk: str, max_width: Optional[int] = None) -> str:
        """AI 응답 청크를 인덴트하여 반환합니다 (상태 유지).

        스트리밍 청크 간 코드 블록 상태를 유지하여 올바른 줄바꿈을 수행합니다.

        Args:
            chunk: AI 응답의 일부 텍스트
            max_width: 최대 너비 (None이면 줄바꿈하지 않음)

        Returns:
            str: 인덴트가 적용된 텍스트 (줄바꿈 포함)
        """
        # 줄바꿈 적용 (상태 유지 버전)
        if max_width:
            return self._wrap_text_stateful(chunk, max_width)

        # 줄바꿈 미적용 시 기본 동작 (기존 로직)
        if "\n" in chunk:
            lines = chunk.split("\n")
            # 빈 줄은 인덴트 프리픽스 제외
            indented_lines = [
                f"{MessageRenderer.INDENT_PREFIX}{line}" if line.strip() else ""
                for line in lines
            ]
            return "\n".join(indented_lines)
        else:
            return f"{MessageRenderer.INDENT_PREFIX}{chunk}"

    def _wrap_text_stateful(self, text: str, max_width: int) -> str:
        """상태를 유지하며 텍스트 줄바꿈을 수행합니다.

        스트리밍 청크 간 `self.in_code_block` 상태를 유지하여 코드 블록 내부에서는
        줄바꿈을 하지 않습니다.

        Args:
            text: 줄바꿈할 텍스트
            max_width: 최대 너비

        Returns:
            str: 줄바꿈된 텍스트

        Raises:
            ValueError: max_width가 너무 작은 경우
        """
        if max_width <= 0:
            return text

        lines = text.split("\n")
        result = []

        for line in lines:
            # 코드 블록 시작/종료 감지
            if line.strip().startswith("```"):
                self.in_code_block = not self.in_code_block
                result.append(MessageRenderer.INDENT_PREFIX + line)
                continue

            # 코드 블록 내부는 줄바꿈하지 않음
            if self.in_code_block:
                result.append(MessageRenderer.INDENT_PREFIX + line)
                continue

            # 일반 텍스트는 줄바꿈 적용
            if line:
                # indent_prefix를 고려한 실제 사용 가능 너비
                effective_width = max_width - len(MessageRenderer.INDENT_PREFIX)
                if effective_width > 0:
                    try:
                        # textwrap.wrap() 사용하여 줄바꿈
                        wrapped_lines = textwrap.wrap(
                            line,
                            width=effective_width,
                            break_long_words=False,
                            break_on_hyphens=False
                        )
                        if wrapped_lines:
                            # 첫 번째 줄
                            result.append(MessageRenderer.INDENT_PREFIX + wrapped_lines[0])
                            # 나머지 줄들
                            for wrapped_line in wrapped_lines[1:]:
                                result.append(MessageRenderer.INDENT_PREFIX + wrapped_line)
                        else:
                            # wrap() 결과가 빈 리스트인 경우 (빈 줄)
                            result.append(MessageRenderer.INDENT_PREFIX + line)
                    except (AttributeError, ValueError) as e:
                        # textwrap 에러 발생 시 로깅 후 원본 유지
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.warning(f"텍스트 줄바꿈 실패: {e}, 원본 유지")
                        result.append(MessageRenderer.INDENT_PREFIX + line)
                else:
                    result.append(MessageRenderer.INDENT_PREFIX + line)
            else:
                # 빈 줄은 그대로 유지
                result.append("")

        return "\n".join(result)

    def reset_state(self) -> None:
        """렌더러 상태를 초기화합니다.

        새로운 AI 응답이 시작될 때 호출하여 코드 블록 상태를 리셋합니다.
        """
        self.in_code_block = False

    @staticmethod
    def render_ai_response_end() -> str:
        """AI 응답 종료 구분선을 반환합니다.

        Returns:
            str: AI 응답 종료 구분선 (Rich 마크업 포함)
        """
        return f"[{MessageRenderer.AI_BORDER_STYLE}]{MessageRenderer.SEPARATOR}[/{MessageRenderer.AI_BORDER_STYLE}]"

    @staticmethod
    def render_error(error_message: str) -> Panel:
        """에러 메시지를 패널로 렌더링합니다.

        Args:
            error_message: 에러 메시지

        Returns:
            Panel: 에러 스타일이 적용된 Rich Panel 객체
        """
        text = Text(error_message)
        return Panel(
            text,
            title="❌ Error",
            border_style="red",
            box=ROUNDED,
            padding=(0, 1),
        )

    @staticmethod
    def render_warning(warning_message: str) -> Panel:
        """경고 메시지를 패널로 렌더링합니다.

        Args:
            warning_message: 경고 메시지

        Returns:
            Panel: 경고 스타일이 적용된 Rich Panel 객체
        """
        text = Text(warning_message)
        return Panel(
            text,
            title="⚠️  Warning",
            border_style="yellow",
            box=ROUNDED,
            padding=(0, 1),
        )

    @staticmethod
    def render_info(info_message: str) -> Panel:
        """정보 메시지를 패널로 렌더링합니다.

        Args:
            info_message: 정보 메시지

        Returns:
            Panel: 정보 스타일이 적용된 Rich Panel 객체
        """
        text = Text(info_message)
        return Panel(
            text,
            title="ℹ️  Info",
            border_style="blue",
            box=ROUNDED,
            padding=(0, 1),
        )
