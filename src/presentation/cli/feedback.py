"""
사용자 친화적인 피드백 메시지 시스템.

Rich 라이브러리를 활용하여 다양한 타입의 피드백 메시지를 제공합니다.
"""

from typing import Optional, Union
from enum import Enum

from rich.console import Console
from rich.panel import Panel
from rich.text import Text


class FeedbackType(Enum):
    """피드백 메시지 타입"""
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    INFO = "info"


class FeedbackMessage:
    """
    피드백 메시지 생성 및 출력을 담당하는 클래스.

    Rich 라이브러리를 사용하여 색상, 아이콘, 패널로 구성된
    사용자 친화적인 피드백 메시지를 제공합니다.

    Attributes:
        console: Rich Console 인스턴스
    """

    # 아이콘 정의
    ICONS = {
        FeedbackType.SUCCESS: "✓",
        FeedbackType.WARNING: "⚠",
        FeedbackType.ERROR: "✗",
        FeedbackType.INFO: "ℹ",
    }

    # 색상 정의
    COLORS = {
        FeedbackType.SUCCESS: "green",
        FeedbackType.WARNING: "yellow",
        FeedbackType.ERROR: "red",
        FeedbackType.INFO: "blue",
    }

    def __init__(self, console: Optional[Console] = None):
        """
        FeedbackMessage 초기화.

        Args:
            console: Rich Console 인스턴스 (없으면 새로 생성)
        """
        self.console = console or Console()

    def show(
        self,
        message: str,
        feedback_type: FeedbackType = FeedbackType.INFO,
        title: Optional[str] = None,
        details: Optional[str] = None,
        use_panel: bool = True
    ) -> None:
        """
        피드백 메시지를 출력합니다.

        Args:
            message: 메시지 내용
            feedback_type: 피드백 타입 (성공, 경고, 에러, 정보)
            title: 패널 타이틀 (없으면 타입에 따라 자동 설정)
            details: 추가 상세 정보 (선택)
            use_panel: Panel 사용 여부 (False면 단순 텍스트 출력)
        """
        icon = self.ICONS[feedback_type]
        color = self.COLORS[feedback_type]

        # 기본 타이틀 설정
        if title is None:
            title = self._get_default_title(feedback_type)

        # 메시지 구성
        content_parts = [f"{icon} {message}"]
        if details:
            content_parts.append(f"\n[dim]{details}[/dim]")

        content = "".join(content_parts)

        # Panel 출력 또는 단순 텍스트 출력
        if use_panel:
            panel = Panel(
                content,
                title=f"[bold {color}]{title}[/bold {color}]",
                border_style=color,
            )
            self.console.print()
            self.console.print(panel)
            self.console.print()
        else:
            self.console.print(f"[{color}]{content}[/{color}]")

    def success(
        self,
        message: str,
        title: Optional[str] = None,
        details: Optional[str] = None,
        use_panel: bool = True
    ) -> None:
        """
        성공 메시지 출력 (초록색, ✓ 아이콘).

        Args:
            message: 메시지 내용
            title: 패널 타이틀
            details: 추가 상세 정보
            use_panel: Panel 사용 여부
        """
        self.show(message, FeedbackType.SUCCESS, title, details, use_panel)

    def warning(
        self,
        message: str,
        title: Optional[str] = None,
        details: Optional[str] = None,
        use_panel: bool = True
    ) -> None:
        """
        경고 메시지 출력 (노란색, ⚠ 아이콘).

        Args:
            message: 메시지 내용
            title: 패널 타이틀
            details: 추가 상세 정보
            use_panel: Panel 사용 여부
        """
        self.show(message, FeedbackType.WARNING, title, details, use_panel)

    def error(
        self,
        message: str,
        title: Optional[str] = None,
        details: Optional[str] = None,
        use_panel: bool = True
    ) -> None:
        """
        에러 메시지 출력 (빨간색, ✗ 아이콘).

        Args:
            message: 메시지 내용
            title: 패널 타이틀
            details: 추가 상세 정보
            use_panel: Panel 사용 여부
        """
        self.show(message, FeedbackType.ERROR, title, details, use_panel)

    def info(
        self,
        message: str,
        title: Optional[str] = None,
        details: Optional[str] = None,
        use_panel: bool = True
    ) -> None:
        """
        정보 메시지 출력 (파란색, ℹ 아이콘).

        Args:
            message: 메시지 내용
            title: 패널 타이틀
            details: 추가 상세 정보
            use_panel: Panel 사용 여부
        """
        self.show(message, FeedbackType.INFO, title, details, use_panel)

    def _get_default_title(self, feedback_type: FeedbackType) -> str:
        """
        피드백 타입에 따른 기본 타이틀 반환.

        Args:
            feedback_type: 피드백 타입

        Returns:
            기본 타이틀 문자열
        """
        titles = {
            FeedbackType.SUCCESS: "성공",
            FeedbackType.WARNING: "경고",
            FeedbackType.ERROR: "오류",
            FeedbackType.INFO: "정보",
        }
        return titles[feedback_type]


class TUIFeedbackWidget:
    """
    TUI용 피드백 위젯 유틸리티.

    Textual 앱 내에서 피드백 메시지를 Rich 객체로 변환하여 제공합니다.
    """

    @staticmethod
    def create_panel(
        message: str,
        feedback_type: FeedbackType = FeedbackType.INFO,
        title: Optional[str] = None,
        details: Optional[str] = None
    ) -> Panel:
        """
        피드백 Panel 객체 생성 (TUI에서 RichLog.write()에 사용).

        Args:
            message: 메시지 내용
            feedback_type: 피드백 타입
            title: 패널 타이틀
            details: 추가 상세 정보

        Returns:
            Rich Panel 객체
        """
        icon = FeedbackMessage.ICONS[feedback_type]
        color = FeedbackMessage.COLORS[feedback_type]

        # 기본 타이틀
        if title is None:
            titles = {
                FeedbackType.SUCCESS: "성공",
                FeedbackType.WARNING: "경고",
                FeedbackType.ERROR: "오류",
                FeedbackType.INFO: "정보",
            }
            title = titles[feedback_type]

        # 메시지 구성
        content_parts = [f"[bold]{icon} {message}[/bold]"]
        if details:
            content_parts.append(f"\n\n[dim]{details}[/dim]")

        content = "".join(content_parts)

        return Panel(
            content,
            title=f"[bold {color}]{title}[/bold {color}]",
            border_style=color,
        )

    @staticmethod
    def create_text(
        message: str,
        feedback_type: FeedbackType = FeedbackType.INFO
    ) -> Text:
        """
        피드백 Text 객체 생성 (TUI에서 간단한 메시지 출력).

        Args:
            message: 메시지 내용
            feedback_type: 피드백 타입

        Returns:
            Rich Text 객체
        """
        icon = FeedbackMessage.ICONS[feedback_type]
        color = FeedbackMessage.COLORS[feedback_type]

        text = Text()
        text.append(f"{icon} ", style=f"bold {color}")
        text.append(message, style=color)

        return text
