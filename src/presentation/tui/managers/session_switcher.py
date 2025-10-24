"""
SessionSwitcher 모듈

세션 전환 로직을 캡슐화합니다.
"""

from typing import TYPE_CHECKING
from src.presentation.cli.utils import generate_session_id
from src.infrastructure.mcp import set_metrics_collector, update_session_id
from src.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from ..tui_app import OrchestratorTUI

logger = get_logger(__name__, component="SessionSwitcher")


class SessionSwitcher:
    """
    세션 전환 로직을 담당하는 클래스

    7개의 헬퍼 메서드로 분산되어 있던 세션 전환 로직을 통합합니다.

    책임:
        - 세션 존재 확인 및 생성
        - 세션 전환 실행
        - UI 복원 (로그, 메트릭, 상태바)
        - 알림 및 에러 처리

    Example:
        >>> switcher = SessionSwitcher(tui_app)
        >>> await switcher.switch_to_session(0)  # Ctrl+1
    """

    def __init__(self, tui_app: "OrchestratorTUI"):
        """
        SessionSwitcher 초기화

        Args:
            tui_app: TUI 애플리케이션 인스턴스
        """
        self.tui = tui_app

    def ensure_session_exists(self, index: int) -> None:
        """
        세션이 존재하지 않으면 생성

        Args:
            index: 세션 인덱스 (0, 1, 2)
        """
        while self.tui.session_manager.get_session_count() <= index:
            new_session_id = generate_session_id()
            new_index = self.tui.session_manager.get_session_count()
            self.tui.session_manager.create_session_at_index(new_index, new_session_id)

    def is_already_active(self, index: int) -> bool:
        """
        이미 활성 세션인지 확인

        Args:
            index: 세션 인덱스 (0, 1, 2)

        Returns:
            이미 활성 세션이면 True, 아니면 False
        """
        active_index = self.tui.session_manager.get_active_session_index()
        return active_index == index

    def switch_session_in_manager(self, index: int) -> None:
        """
        SessionManager를 통해 세션 전환

        Args:
            index: 세션 인덱스 (0, 1, 2)
        """
        self.tui.session_manager.switch_to_session(index)

    def restore_session_ui(self) -> None:
        """세션 UI 복원 (로그, 메트릭, 상태바 등)"""
        # 세션 캐시 무효화
        self.tui.invalidate_session_cache()

        # UI 업데이트: 로그 교체
        from textual.widgets import RichLog
        output_log = self.tui.query_one("#output-log", RichLog)
        output_log.clear()

        # 현재 세션 로그 복원
        for log_line in self.tui.current_session.log_lines:
            output_log.write(log_line)

        # 메트릭 수집기 업데이트
        set_metrics_collector(
            self.tui.current_session.metrics_collector,
            self.tui.session_id
        )
        update_session_id(self.tui.session_id)

        # Manager Agent 토큰 사용량 초기화 (세션별로 독립적)
        if self.tui.manager:
            self.tui.manager.reset_token_usage()

        # 상태바 업데이트
        self.tui._update_status_bar()

    def notify_success(self, index: int) -> None:
        """
        세션 전환 성공 알림

        Args:
            index: 세션 인덱스 (0, 1, 2)
        """
        if self.tui.settings.enable_notifications:
            self.tui.notify(
                f"세션 {index + 1}로 전환 (ID: {self.tui.session_id[:8]}...)",
                severity="information"
            )

    def notify_already_active(self, index: int) -> None:
        """
        이미 활성 세션임을 알림

        Args:
            index: 세션 인덱스 (0, 1, 2)
        """
        if self.tui.settings.enable_notifications:
            self.tui.notify(f"이미 세션 {index + 1}입니다", severity="information")

    def handle_error(self, error: Exception) -> None:
        """
        세션 전환 에러 처리

        Args:
            error: 발생한 예외
        """
        logger.error(f"세션 전환 실패: {error}")
        if self.tui.settings.enable_notifications and self.tui.settings.notify_on_error:
            self.tui.notify(f"세션 전환 실패: {error}", severity="error")

    async def switch_to_session(self, index: int) -> None:
        """
        세션 전환 (0, 1, 2)

        Args:
            index: 세션 인덱스 (0=Ctrl+1, 1=Ctrl+2, 2=Ctrl+3)
        """
        try:
            # 세션이 아직 없으면 생성
            self.ensure_session_exists(index)

            # 이미 현재 세션이면 무시
            if self.is_already_active(index):
                self.notify_already_active(index)
                return

            # 세션 전환
            self.switch_session_in_manager(index)

            # UI 업데이트
            self.restore_session_ui()

            # 알림 표시
            self.notify_success(index)

        except Exception as e:
            self.handle_error(e)
