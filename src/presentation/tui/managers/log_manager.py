"""
로그 매니저.

OrchestratorTUI의 로그 출력 및 추적 로직을 분리하여
로그 관리를 담당합니다.
"""

from typing import TYPE_CHECKING, Union

from textual.widgets import RichLog
from rich.panel import Panel
from rich.text import Text

from ..utils import MessageRenderer
from src.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from ..tui_app import OrchestratorTUI

logger = get_logger(__name__, component="LogManager")


class LogManager:
    """
    로그 매니저.

    로그 출력 및 추적을 담당합니다:
    - 로그 출력 (write_log)
    - 로그 버퍼 추적 (_track_log_output)
    - 로그 포매팅
    """

    def __init__(self, app: "OrchestratorTUI"):
        """
        초기화.

        Args:
            app: OrchestratorTUI 인스턴스
        """
        self.app = app

    def write_log(
        self, content: Union[str, Panel, Text], widget_id: str = "output-log"
    ) -> None:
        """
        로그 출력 및 추적 헬퍼 메서드.

        Args:
            content: 출력할 내용 (str, Panel, Text 중 하나)
            widget_id: RichLog 위젯 ID
        """
        try:
            output_log = self.app.query_one(f"#{widget_id}", RichLog)

            # RichLog의 실제 너비 계산
            # (컨테이너 너비 - 패딩 - 스크롤바 - 보더)
            try:
                # output_log의 실제 표시 너비
                available_width = output_log.size.width
                # PANEL_PADDING 상수 사용 (padding(1)*2 + scrollbar(1) + border(2))
                PANEL_PADDING = 5
                effective_width = max(
                    available_width - PANEL_PADDING,
                    MessageRenderer.MIN_OUTPUT_WIDTH
                )

                # Rich Console 객체를 동적으로 생성하여 width 설정
                from rich.console import Console
                from io import StringIO

                # Panel이나 복잡한 객체의 경우, width를 고려하여 렌더링
                if isinstance(content, Panel):
                    # Panel의 경우 width 옵션 적용
                    content.width = effective_width

            except (AttributeError, ValueError) as e:
                # 크기 계산 실패 시 로깅 후 기본 동작
                logger.warning(f"로그 너비 계산 실패: {e}, 기본 동작 사용")
            except Exception as e:
                # 기타 예외 시 로깅 후 기본 동작
                logger.warning(f"로그 렌더링 중 예외: {e}, 기본 동작 사용")

            output_log.write(content)
            # 로그 버퍼에도 추가
            self._track_log_output(str(content))
        except Exception as e:
            # write_log 자체가 실패하면 로깅만 하고 넘어감
            logger.error(f"로그 출력 실패: {e}")

    def _track_log_output(self, content: str) -> None:
        """
        로그 출력 추적 (Phase 2.1: 로그 버퍼 관리).

        Args:
            content: 로그 내용
        """
        # 문자열로 변환 (Panel, Text 등의 객체 처리)
        if hasattr(content, "__str__"):
            content_str = str(content)
        else:
            content_str = content

        # 현재 세션의 log_lines에 추가 (property를 통해 접근)
        self.app.current_session.log_lines.append(content_str)

        # 최대 라인 수 제한
        max_lines = self.app.settings.max_log_lines
        if len(self.app.current_session.log_lines) > max_lines:
            # 오래된 라인 제거
            self.app.current_session.log_lines = self.app.current_session.log_lines[-max_lines:]
