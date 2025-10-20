"""TUI 메시지 렌더링 유틸리티

이 모듈은 TUI에서 사용자 메시지와 AI 응답을 시각적으로 렌더링하는 기능을 제공합니다.
"""

from rich.panel import Panel
from rich.text import Text
from rich.box import ROUNDED


class MessageRenderer:
    """메시지 렌더링 유틸리티 클래스

    사용자 메시지와 AI 응답을 Rich 포맷으로 렌더링합니다.
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

    @staticmethod
    def render_ai_response_chunk(chunk: str) -> str:
        """AI 응답 청크를 인덴트하여 반환합니다.

        Args:
            chunk: AI 응답의 일부 텍스트

        Returns:
            str: 인덴트가 적용된 텍스트
        """
        # 청크가 이미 줄바꿈을 포함하는 경우, 각 줄에 인덴트 적용
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
