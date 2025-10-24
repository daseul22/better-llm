"""
LogFilterManager 모듈

로그 필터링 관련 로직을 캡슐화합니다.
"""

from typing import TYPE_CHECKING, List, Any
from rich.panel import Panel
from src.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from ..tui_app import OrchestratorTUI

logger = get_logger(__name__, component="LogFilterManager")


class LogFilterManager:
    """
    로그 필터링 처리를 담당하는 클래스

    tui_app.py의 로그 필터 관련 메서드(action_show_log_filter,
    apply_log_filter, _format_filter_info)에서 분리된 로직을 통합합니다.

    책임:
        - 로그 필터 모달 표시
        - 필터 적용 및 결과 출력
        - 필터 정보 포맷팅
        - 알림 표시

    Example:
        >>> manager = LogFilterManager(tui_app)
        >>> await manager.show_log_filter()
    """

    def __init__(self, tui_app: "OrchestratorTUI"):
        """
        LogFilterManager 초기화

        Args:
            tui_app: TUI 애플리케이션 인스턴스
        """
        self.tui = tui_app

    def extract_workers(self, log_lines: List[Any]) -> List[str]:
        """
        로그에서 Worker 목록 추출

        Args:
            log_lines: 로그 라인 리스트

        Returns:
            Worker 이름 리스트
        """
        from ..utils.log_filter import LogFilter
        log_filter = LogFilter()
        return log_filter.extract_workers(log_lines)

    def format_filter_info(self, filter_config) -> str:
        """
        필터 설정 정보 포매팅

        Args:
            filter_config: FilterConfig 객체 (levels, worker, start_time, end_time)

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
            start_str = (
                filter_config.start_time.strftime("%H:%M:%S")
                if filter_config.start_time
                else "제한 없음"
            )
            end_str = (
                filter_config.end_time.strftime("%H:%M:%S")
                if filter_config.end_time
                else "제한 없음"
            )
            lines.append(f"**시간대**: {start_str} ~ {end_str}")
        else:
            lines.append("**시간대**: 제한 없음")

        return "\n".join(lines)

    def apply_filters(
        self,
        log_lines: List[Any],
        levels: List[str],
        worker: str,
        start_time,
        end_time
    ) -> List[Any]:
        """
        로그 필터 적용

        Args:
            log_lines: 원본 로그 라인 리스트
            levels: 필터링할 로그 레벨 리스트
            worker: 필터링할 Worker 이름
            start_time: 시작 시간
            end_time: 종료 시간

        Returns:
            필터링된 로그 라인 리스트
        """
        from ..utils.log_filter import LogFilter
        log_filter = LogFilter()
        return log_filter.apply_filters(
            log_lines,
            levels=levels,
            worker=worker,
            start_time=start_time,
            end_time=end_time
        )

    def write_filter_info_to_log(self, filter_config) -> None:
        """
        필터 정보를 로그에 출력

        Args:
            filter_config: FilterConfig 객체
        """
        from textual.widgets import RichLog
        output_log = self.tui.query_one("#output-log", RichLog)
        filter_info = self.format_filter_info(filter_config)
        output_log.write(Panel(
            f"[bold cyan]🔍 로그 필터 적용[/bold cyan]\n\n{filter_info}",
            border_style="cyan"
        ))
        output_log.write("")

    def write_filtered_lines_to_log(
        self,
        filtered_lines: List[Any],
        total_lines: int
    ) -> None:
        """
        필터링된 로그를 출력

        Args:
            filtered_lines: 필터링된 로그 라인 리스트
            total_lines: 전체 로그 라인 수
        """
        from textual.widgets import RichLog
        output_log = self.tui.query_one("#output-log", RichLog)

        if filtered_lines:
            for line in filtered_lines:
                output_log.write(line)
            output_log.write("")
            output_log.write(
                f"[dim]총 {len(filtered_lines)}개 라인 (전체: {total_lines}개)[/dim]"
            )
        else:
            output_log.write("[yellow]⚠️ 필터링된 로그가 없습니다[/yellow]")

    def notify_filter_result(self, filtered_count: int) -> None:
        """
        필터 적용 결과 알림

        Args:
            filtered_count: 필터링된 로그 라인 수
        """
        if self.tui.settings.enable_notifications:
            self.tui.notify(
                f"로그 필터 적용: {filtered_count}개 라인",
                severity="information"
            )

    def notify_error(self, error: Exception, context: str) -> None:
        """
        에러 알림

        Args:
            error: 발생한 예외
            context: 에러 발생 컨텍스트 ("표시" 또는 "적용")
        """
        logger.error(f"로그 필터 {context} 실패: {error}", exc_info=True)
        if self.tui.settings.enable_notifications and self.tui.settings.notify_on_error:
            self.tui.notify(
                f"로그 필터 {context} 실패: {error}",
                severity="error"
            )

    async def show_log_filter(self) -> None:
        """
        Ctrl+Shift+F: 로그 필터 모달 표시

        로그 레벨, Worker, 시간대별 필터링 옵션을 제공합니다.
        """
        try:
            # Worker 목록 추출
            available_workers = self.extract_workers(self.tui.log_lines)

            # 로그 필터 모달 표시
            from ..widgets import LogFilterModal
            result = await self.tui.push_screen(
                LogFilterModal(self.tui.log_lines, available_workers)
            )

            # 필터 적용 결과 처리
            if result is not None:
                await self.apply_log_filter(result)

        except Exception as e:
            self.notify_error(e, "표시")

    async def apply_log_filter(self, filter_config) -> None:
        """
        로그 필터 적용

        Args:
            filter_config: FilterConfig 객체 (levels, worker, start_time, end_time)
        """
        try:
            # 필터 적용
            filtered_lines = self.apply_filters(
                self.tui.log_lines,
                levels=filter_config.levels,
                worker=filter_config.worker,
                start_time=filter_config.start_time,
                end_time=filter_config.end_time
            )

            # 출력 로그 갱신
            from textual.widgets import RichLog
            output_log = self.tui.query_one("#output-log", RichLog)
            output_log.clear()

            # 필터 정보 표시
            self.write_filter_info_to_log(filter_config)

            # 필터링된 로그 출력
            self.write_filtered_lines_to_log(filtered_lines, len(self.tui.log_lines))

            # 알림 표시
            self.notify_filter_result(len(filtered_lines))

        except Exception as e:
            self.notify_error(e, "적용")
