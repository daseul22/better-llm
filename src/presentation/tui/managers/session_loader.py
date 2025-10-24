"""
SessionLoader 모듈

세션 불러오기 로직을 캡슐화합니다.
"""

import json
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Dict, Any
from rich.panel import Panel
from src.infrastructure.config import get_data_dir
from src.infrastructure.mcp import set_metrics_collector, update_session_id
from src.infrastructure.logging import get_logger
from src.presentation.cli.feedback import TUIFeedbackWidget, FeedbackType

if TYPE_CHECKING:
    from ..tui_app import OrchestratorTUI

logger = get_logger(__name__, component="SessionLoader")


class SessionLoader:
    """
    세션 불러오기 처리를 담당하는 클래스

    tui_app.py의 load_session 메서드에서 분리된 로직을 통합합니다.

    책임:
        - 세션 파일 찾기
        - JSON 데이터 로드
        - 세션 객체 생성 및 교체
        - UI 업데이트 (상태바, 메트릭)
        - 에러 처리

    Example:
        >>> loader = SessionLoader(tui_app)
        >>> await loader.load_session("abc123def")
    """

    def __init__(self, tui_app: "OrchestratorTUI"):
        """
        SessionLoader 초기화

        Args:
            tui_app: TUI 애플리케이션 인스턴스
        """
        self.tui = tui_app

    def find_session_file(self, session_id: str) -> Optional[Path]:
        """
        세션 파일 찾기 (가장 최근 파일 선택)

        Args:
            session_id: 세션 ID

        Returns:
            세션 파일 경로, 없으면 None
        """
        sessions_dir = get_data_dir("sessions")
        session_files = list(sessions_dir.glob(f"session_{session_id}_*.json"))

        if not session_files:
            return None

        # 가장 최근 파일 선택
        return max(session_files, key=lambda p: p.stat().st_mtime)

    def load_session_data(self, session_file: Path) -> Dict[str, Any]:
        """
        세션 파일에서 JSON 데이터 로드

        Args:
            session_file: 세션 파일 경로

        Returns:
            세션 데이터 딕셔너리
        """
        with open(session_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def create_loaded_session(self, session_id: str, session_data: Dict[str, Any]):
        """
        로드된 세션 데이터에서 SessionData 객체 생성

        Args:
            session_id: 세션 ID
            session_data: 로드된 세션 데이터

        Returns:
            SessionData 객체
        """
        initial_messages = session_data.get("history", [])
        return self.tui.session_manager.create_session_data(
            session_id=session_id,
            user_request="Loaded session",
            initial_messages=initial_messages
        )

    def replace_current_session(self, loaded_session) -> None:
        """
        현재 활성 세션을 로드된 세션으로 교체

        Args:
            loaded_session: 로드된 SessionData 객체
        """
        active_index = self.tui.session_manager.get_active_session_index()
        self.tui.session_manager.update_session_at_index(active_index, loaded_session)

        # 세션 캐시 무효화
        self.tui.invalidate_session_cache()

    def update_ui_after_load(self, session_id: str) -> None:
        """
        세션 로드 후 UI 업데이트

        Args:
            session_id: 로드된 세션 ID
        """
        # 세션 ID 및 메트릭 수집기 업데이트
        update_session_id(session_id)
        set_metrics_collector(self.tui.metrics_collector, self.tui.session_id)

        # Manager Agent 토큰 사용량 초기화
        if self.tui.manager:
            self.tui.manager.reset_token_usage()

        # 상태바 업데이트
        self.tui._update_status_bar()

        # 상태 정보 업데이트
        from textual.widgets import Static
        status_info = self.tui.query_one("#status-info", Static)
        status_info.update("Ready")

    def write_loading_message(self, session_id: str) -> None:
        """
        세션 로딩 중 메시지 출력

        Args:
            session_id: 세션 ID
        """
        self.tui.write_log("")
        self.tui.write_log(Panel(
            f"[bold cyan]🔄 세션 불러오는 중...[/bold cyan]\n\n"
            f"Session ID: {session_id}",
            border_style="cyan"
        ))
        self.tui.write_log("")

    def write_success_message(self, session_id: str, message_count: int) -> None:
        """
        세션 로드 성공 메시지 출력

        Args:
            session_id: 세션 ID
            message_count: 메시지 수
        """
        self.tui.write_log(Panel(
            f"[bold green]✅ 세션 불러오기 완료[/bold green]\n\n"
            f"Session ID: {session_id}\n"
            f"메시지 수: {message_count}",
            border_style="green"
        ))
        self.tui.write_log("")

    def write_not_found_error(self, session_id: str) -> None:
        """
        세션 파일을 찾을 수 없을 때 에러 메시지 출력

        Args:
            session_id: 세션 ID
        """
        error_panel = TUIFeedbackWidget.create_panel(
            "세션을 찾을 수 없습니다",
            FeedbackType.ERROR,
            details=f"Session ID: {session_id}"
        )
        self.tui.write_log("")
        self.tui.write_log(error_panel)
        self.tui.write_log("")

    def write_load_error(self, error: Exception) -> None:
        """
        세션 로드 실패 에러 메시지 출력

        Args:
            error: 발생한 예외
        """
        error_panel = TUIFeedbackWidget.create_panel(
            "세션 불러오기 실패",
            FeedbackType.ERROR,
            details=str(error)
        )
        self.tui.write_log("")
        self.tui.write_log(error_panel)
        self.tui.write_log("")
        logger.error(f"세션 불러오기 실패: {error}")

    async def load_session(self, session_id: str) -> None:
        """
        이전 세션 불러오기 메인 로직

        Args:
            session_id: 불러올 세션 ID
        """
        try:
            # 로딩 메시지 출력
            self.write_loading_message(session_id)

            # 세션 파일 찾기
            session_file = self.find_session_file(session_id)
            if not session_file:
                self.write_not_found_error(session_id)
                return

            # 세션 데이터 로드
            session_data = self.load_session_data(session_file)

            # 세션 객체 생성
            loaded_session = self.create_loaded_session(session_id, session_data)

            # 현재 세션 교체
            self.replace_current_session(loaded_session)

            # UI 업데이트
            self.update_ui_after_load(session_id)

            # 성공 메시지 출력
            message_count = len(session_data.get("history", []))
            self.write_success_message(session_id, message_count)

        except Exception as e:
            self.write_load_error(e)
