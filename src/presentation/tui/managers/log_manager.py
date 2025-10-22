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
            # 위젯 존재 여부 확인 (화면 종료 시 위젯이 없을 수 있음)
            widgets = self.app.query(f"#{widget_id}")
            if not widgets:
                # 위젯이 없으면 조용히 실패 (화면 종료 중일 수 있음)
                logger.debug(f"위젯 '{widget_id}'를 찾을 수 없습니다 (화면 종료 중일 수 있음)")
                return

            output_log = widgets.first(RichLog)

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
                # 크기 계산 실패 시 로깅 후 기본 동작 (위젯 초기화 중 발생 가능)
                logger.debug(f"로그 너비 계산 실패 (초기화 중일 수 있음): {e}")
            except Exception as e:
                # 기타 예외 시 로깅 후 기본 동작
                logger.warning(f"로그 렌더링 중 예상치 못한 예외: {e}", exc_info=True)

            output_log.write(content)
            # 로그 버퍼에도 추가
            self._track_log_output(str(content))
        except Exception as e:
            # write_log 자체가 실패하면 로깅만 하고 넘어감 (critical한 에러)
            logger.error(f"로그 출력 실패: {e}", exc_info=True)

    def _track_log_output(self, content: str) -> None:
        """
        로그 출력 추적 (Phase 2.1: 로그 버퍼 관리).

        Race Condition 방지: deque.append는 thread-safe합니다.

        Args:
            content: 로그 내용
        """
        # 문자열로 변환 (Panel, Text 등의 객체 처리)
        if hasattr(content, "__str__"):
            content_str = str(content)
        else:
            content_str = content

        # 현재 세션의 log_lines에 추가 (deque.append는 thread-safe)
        # deque는 maxlen이 설정되어 있어 자동으로 오래된 항목 제거
        self.app.current_session.log_lines.append(content_str)

    def apply_filter(self, filter_config) -> None:
        """
        로그 필터 적용 (LogFilter 사용).

        Args:
            filter_config: FilterConfig 객체 (levels, worker, start_time, end_time)
        """
        try:
            from ..utils.log_filter import LogFilter

            # 필터 적용
            log_filter = LogFilter()
            filtered_lines = log_filter.apply_filters(
                self.app.log_lines,
                levels=filter_config.levels,
                worker=filter_config.worker,
                start_time=filter_config.start_time,
                end_time=filter_config.end_time
            )

            # 출력 로그 갱신
            output_log = self.app.query_one("#output-log", RichLog)
            output_log.clear()

            # 필터 정보 표시
            filter_info = self._format_filter_info(filter_config)
            output_log.write(Panel(
                f"[bold cyan]🔍 로그 필터 적용[/bold cyan]\n\n{filter_info}",
                border_style="cyan"
            ))
            output_log.write("")

            # 필터링된 로그 출력
            if filtered_lines:
                for line in filtered_lines:
                    output_log.write(line)
                output_log.write("")
                output_log.write(
                    f"[dim]총 {len(filtered_lines)}개 라인 (전체: {len(self.app.log_lines)}개)[/dim]"
                )
            else:
                output_log.write("[yellow]⚠️ 필터링된 로그가 없습니다[/yellow]")

            logger.info(f"로그 필터 적용 완료: {len(filtered_lines)}개 라인")

        except Exception as e:
            logger.error(f"로그 필터 적용 실패: {e}", exc_info=True)
            raise

    def _format_filter_info(self, filter_config) -> str:
        """
        필터 설정 정보 포매팅.

        Args:
            filter_config: FilterConfig 객체

        Returns:
            포매팅된 필터 정보 문자열
        """
        lines = []

        # 로그 레벨
        levels_str = ", ".join(sorted(filter_config.levels))
        lines.append(f"**레벨**: {levels_str}")

        # Worker
        worker_str = filter_config.worker or "All"
        lines.append(f"**Worker**: {worker_str}")

        # 시간대
        if filter_config.start_time or filter_config.end_time:
            start_str = filter_config.start_time.strftime("%H:%M:%S") if filter_config.start_time else "제한 없음"
            end_str = filter_config.end_time.strftime("%H:%M:%S") if filter_config.end_time else "제한 없음"
            lines.append(f"**시간대**: {start_str} ~ {end_str}")
        else:
            lines.append("**시간대**: 제한 없음")

        return "\n".join(lines)
