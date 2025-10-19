"""
세션 브라우저 모달

세션 목록을 보고 선택/삭제할 수 있는 모달
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Tuple

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Static, Button, DataTable
from textual.binding import Binding
from rich.text import Text

logger = logging.getLogger(__name__)


class SessionBrowserModal(ModalScreen):
    """세션 브라우저 모달 스크린"""

    CSS = """
    SessionBrowserModal {
        align: center middle;
    }

    #session-dialog {
        width: 100;
        height: 30;
        background: #0d1117;
        border: thick #388bfd;
        padding: 1 2;
    }

    #session-title {
        height: auto;
        padding: 0 0 1 0;
    }

    #session-table-container {
        height: 1fr;
        background: transparent;
        border: round #21262d;
        margin: 1 0;
    }

    #session-table {
        height: 100%;
        background: transparent;
    }

    #session-hint {
        height: auto;
        color: #6e7681;
        padding: 1 0;
    }

    #session-buttons {
        height: auto;
        margin-top: 1;
    }

    Button {
        margin: 0 1;
    }

    /* DataTable 스타일 */
    DataTable {
        background: transparent;
        color: #c9d1d9;
    }

    DataTable > .datatable--header {
        background: #161b22;
        color: #58a6ff;
    }

    DataTable > .datatable--cursor {
        background: #1c2128;
    }

    DataTable > .datatable--hover {
        background: #161b22;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "닫기"),
        Binding("q", "close", "닫기", show=False),
        Binding("enter", "load_session", "로드"),
        Binding("d", "delete_session", "삭제", show=False),
        Binding("delete", "delete_session", "삭제", show=False),
        Binding("up", "cursor_up", "위로", show=False),
        Binding("down", "cursor_down", "아래로", show=False),
    ]

    def __init__(self, sessions_dir: Path = Path("sessions")):
        """
        세션 브라우저 모달 초기화

        Args:
            sessions_dir: 세션 파일이 저장된 디렉토리
        """
        super().__init__()
        self.sessions_dir = sessions_dir
        self.session_data: List[Tuple[str, datetime, datetime, int]] = []
        self.confirm_delete_id: Optional[str] = None

    def compose(self) -> ComposeResult:
        """UI 구성"""
        with Container(id="session-dialog"):
            yield Static("[bold cyan]세션 브라우저[/bold cyan]", id="session-title")
            with Container(id="session-table-container"):
                table = DataTable(id="session-table", cursor_type="row")
                table.add_columns("세션 ID", "생성 시간", "수정 시간", "메시지")
                yield table
            yield Static(
                "[dim]Enter[/dim]: 로드 • [dim]D/Delete[/dim]: 삭제 • "
                "[dim]ESC/Q[/dim]: 닫기 • [dim]↑/↓[/dim]: 이동",
                id="session-hint"
            )
            with Horizontal(id="session-buttons"):
                yield Button("로드 (Enter)", id="load-button", variant="primary")
                yield Button("삭제 (D)", id="delete-button", variant="error")
                yield Button("닫기 (ESC)", id="close-button")

    async def on_mount(self) -> None:
        """모달 마운트 시 세션 데이터 로드"""
        await self.load_sessions()

    async def load_sessions(self) -> None:
        """세션 디렉토리에서 세션 정보 수집"""
        table = self.query_one("#session-table", DataTable)
        table.clear()

        if not self.sessions_dir.exists():
            self.sessions_dir.mkdir(parents=True, exist_ok=True)
            return

        # JSON 파일만 필터링
        session_files = list(self.sessions_dir.glob("session_*.json"))

        if not session_files:
            table.add_row("", "세션 없음", "", "")
            return

        # 세션 메타데이터 수집
        sessions_info = []
        for filepath in session_files:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)

                session_id = data.get("session_id", "")
                created_at_str = data.get("created_at", "")
                completed_at_str = data.get("completed_at", created_at_str)
                messages = data.get("messages", [])
                message_count = len(messages)

                # 날짜 파싱
                try:
                    created_at = datetime.fromisoformat(created_at_str)
                except (ValueError, TypeError):
                    created_at = datetime.fromtimestamp(filepath.stat().st_ctime)

                try:
                    completed_at = datetime.fromisoformat(completed_at_str)
                except (ValueError, TypeError):
                    completed_at = datetime.fromtimestamp(filepath.stat().st_mtime)

                sessions_info.append((session_id, created_at, completed_at, message_count))

            except (json.JSONDecodeError, KeyError) as e:
                # 파싱 실패한 파일은 무시
                continue

        # 최근 수정 시간 기준 내림차순 정렬
        sessions_info.sort(key=lambda x: x[2], reverse=True)
        self.session_data = sessions_info

        # DataTable에 추가
        for session_id, created_at, completed_at, message_count in sessions_info:
            created_str = created_at.strftime("%m/%d %H:%M")
            completed_str = completed_at.strftime("%m/%d %H:%M")

            table.add_row(
                session_id,
                created_str,
                completed_str,
                str(message_count)
            )

        # 첫 번째 행에 커서 이동
        if len(sessions_info) > 0:
            table.move_cursor(row=0)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """버튼 클릭 이벤트"""
        if event.button.id == "load-button":
            self.action_load_session()
        elif event.button.id == "delete-button":
            self.action_delete_session()
        elif event.button.id == "close-button":
            self.action_close()

    def action_load_session(self) -> None:
        """선택한 세션 로드"""
        table = self.query_one("#session-table", DataTable)

        if table.cursor_row is None or table.cursor_row < 0:
            return

        if not self.session_data or table.cursor_row >= len(self.session_data):
            return

        # 선택한 세션 ID 가져오기
        session_id, _, _, _ = self.session_data[table.cursor_row]

        # 부모 앱에 세션 ID 전달
        self.dismiss(("load", session_id))

    async def action_delete_session(self) -> None:
        """선택한 세션 삭제 (확인 대화상자)"""
        table = self.query_one("#session-table", DataTable)

        if table.cursor_row is None or table.cursor_row < 0:
            return

        if not self.session_data or table.cursor_row >= len(self.session_data):
            return

        # 선택한 세션 ID 가져오기
        session_id, _, _, _ = self.session_data[table.cursor_row]

        # 삭제 확인 요청
        from .delete_confirm_modal import DeleteConfirmModal
        result = await self.app.push_screen(DeleteConfirmModal(session_id))

        if result:
            # 삭제 실행
            await self.delete_session_files(session_id)
            # 테이블 새로고침
            await self.load_sessions()

    async def delete_session_files(self, session_id: str) -> None:
        """
        세션 파일 삭제

        Args:
            session_id: 삭제할 세션 ID
        """
        deleted_count = 0
        failed_files = []

        # JSON 파일 삭제
        json_files = list(self.sessions_dir.glob(f"session_{session_id}_*.json"))
        for filepath in json_files:
            try:
                filepath.unlink()
                deleted_count += 1
                logger.info(f"세션 파일 삭제 성공: {filepath.name}")
            except Exception as e:
                logger.error(f"세션 파일 삭제 실패: {filepath.name} - {e}")
                failed_files.append(filepath.name)

        # 메트릭 파일 삭제
        metrics_files = list(self.sessions_dir.glob(f"{session_id}_metrics.txt"))
        for filepath in metrics_files:
            try:
                filepath.unlink()
                deleted_count += 1
                logger.info(f"메트릭 파일 삭제 성공: {filepath.name}")
            except Exception as e:
                logger.error(f"메트릭 파일 삭제 실패: {filepath.name} - {e}")
                failed_files.append(filepath.name)

        # 사용자에게 결과 알림
        if failed_files and hasattr(self.app, "notify"):
            # 실패한 파일 목록 (최대 3개까지 표시)
            failed_names = ", ".join(failed_files[:3])
            if len(failed_files) > 3:
                failed_names += f" 외 {len(failed_files) - 3}개"

            self.app.notify(
                f"일부 파일 삭제 실패: {failed_names}",
                severity="warning",
                timeout=5
            )
        elif deleted_count > 0 and hasattr(self.app, "notify"):
            self.app.notify(
                f"세션 삭제 완료 ({deleted_count}개 파일)",
                severity="information",
                timeout=3
            )

    def action_close(self) -> None:
        """모달 닫기"""
        self.dismiss(None)

    def action_cursor_up(self) -> None:
        """커서 위로 이동"""
        table = self.query_one("#session-table", DataTable)
        if table.cursor_row is not None and table.cursor_row > 0:
            table.move_cursor(row=table.cursor_row - 1)

    def action_cursor_down(self) -> None:
        """커서 아래로 이동"""
        table = self.query_one("#session-table", DataTable)
        if table.cursor_row is not None:
            max_row = len(self.session_data) - 1
            if table.cursor_row < max_row:
                table.move_cursor(row=table.cursor_row + 1)


class DeleteConfirmModal(ModalScreen):
    """세션 삭제 확인 모달"""

    CSS = """
    DeleteConfirmModal {
        align: center middle;
    }

    #delete-confirm-dialog {
        width: 60;
        height: auto;
        background: #0d1117;
        border: thick #da3633;
        padding: 1 2;
    }

    #delete-confirm-title {
        height: auto;
        padding: 0 0 1 0;
    }

    #delete-confirm-message {
        height: auto;
        color: #c9d1d9;
        padding: 1 0;
    }

    #delete-confirm-buttons {
        height: auto;
        margin-top: 1;
    }

    Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "취소"),
        Binding("n", "cancel", "취소", show=False),
        Binding("y", "confirm", "삭제", show=False),
    ]

    def __init__(self, session_id: str):
        """
        삭제 확인 모달 초기화

        Args:
            session_id: 삭제할 세션 ID
        """
        super().__init__()
        self.session_id = session_id

    def compose(self) -> ComposeResult:
        """UI 구성"""
        with Container(id="delete-confirm-dialog"):
            yield Static(
                "[bold red]⚠️  세션 삭제 확인[/bold red]",
                id="delete-confirm-title"
            )
            yield Static(
                f"세션 [yellow]{self.session_id}[/yellow]을(를) 삭제하시겠습니까?\n\n"
                f"[dim]이 작업은 되돌릴 수 없습니다.[/dim]",
                id="delete-confirm-message"
            )
            with Horizontal(id="delete-confirm-buttons"):
                yield Button("삭제 (Y)", id="confirm-button", variant="error")
                yield Button("취소 (N/ESC)", id="cancel-button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """버튼 클릭 이벤트"""
        if event.button.id == "confirm-button":
            self.action_confirm()
        elif event.button.id == "cancel-button":
            self.action_cancel()

    def action_confirm(self) -> None:
        """삭제 확인"""
        self.dismiss(True)

    def action_cancel(self) -> None:
        """삭제 취소"""
        self.dismiss(False)
