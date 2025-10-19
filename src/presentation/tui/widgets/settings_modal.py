"""
설정 모달 위젯

TUI 설정을 변경할 수 있는 모달 화면
"""

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, Grid
from textual.screen import ModalScreen
from textual.widgets import Static, Button, Switch, Input, Select
from textual.binding import Binding
from rich.panel import Panel
from rich.table import Table

from ..utils.tui_config import TUISettings, TUIConfig


class SettingsModal(ModalScreen):
    """설정 모달 스크린"""

    CSS = """
    SettingsModal {
        align: center middle;
    }

    #settings-dialog {
        width: 80;
        height: auto;
        max-height: 90%;
        background: #0d1117;
        border: thick #388bfd;
        padding: 1 2;
    }

    #settings-content {
        height: auto;
        background: transparent;
        color: #c9d1d9;
        padding: 1 0;
    }

    .setting-row {
        height: auto;
        margin: 1 0;
        padding: 1;
        background: #161b22;
        border: round #21262d;
    }

    .setting-label {
        width: 30;
        color: #8b949e;
    }

    .setting-control {
        width: 1fr;
    }

    #settings-buttons {
        height: auto;
        margin-top: 1;
    }

    Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "닫기"),
    ]

    def __init__(self, current_settings: TUISettings):
        super().__init__()
        self.settings = current_settings

    def compose(self) -> ComposeResult:
        """UI 구성"""
        with Container(id="settings-dialog"):
            yield Static("[bold cyan]설정[/bold cyan]")

            with Vertical(id="settings-content"):
                # 버퍼 크기 설정
                with Horizontal(classes="setting-row"):
                    yield Static("최대 로그 라인:", classes="setting-label")
                    yield Input(
                        str(self.settings.max_log_lines),
                        id="max-log-lines",
                        classes="setting-control"
                    )

                with Horizontal(classes="setting-row"):
                    yield Static("히스토리 크기:", classes="setting-label")
                    yield Input(
                        str(self.settings.max_history_size),
                        id="max-history-size",
                        classes="setting-control"
                    )

                # 타임아웃 설정
                with Horizontal(classes="setting-row"):
                    yield Static("Worker 타임아웃 (초):", classes="setting-label")
                    yield Input(
                        str(self.settings.worker_timeout),
                        id="worker-timeout",
                        classes="setting-control"
                    )

                # 알림 설정
                with Horizontal(classes="setting-row"):
                    yield Static("알림 활성화:", classes="setting-label")
                    yield Switch(
                        self.settings.enable_notifications,
                        id="enable-notifications",
                        classes="setting-control"
                    )

                with Horizontal(classes="setting-row"):
                    yield Static("완료 시 알림:", classes="setting-label")
                    yield Switch(
                        self.settings.notify_on_completion,
                        id="notify-on-completion",
                        classes="setting-control"
                    )

                with Horizontal(classes="setting-row"):
                    yield Static("에러 시 알림:", classes="setting-label")
                    yield Switch(
                        self.settings.notify_on_error,
                        id="notify-on-error",
                        classes="setting-control"
                    )

                # 자동 완성 설정
                with Horizontal(classes="setting-row"):
                    yield Static("자동 완성:", classes="setting-label")
                    yield Switch(
                        self.settings.enable_autocomplete,
                        id="enable-autocomplete",
                        classes="setting-control"
                    )

                # 로그 내보내기 형식
                with Horizontal(classes="setting-row"):
                    yield Static("로그 저장 형식:", classes="setting-label")
                    yield Input(
                        self.settings.log_export_format,
                        id="log-export-format",
                        classes="setting-control",
                        placeholder="text 또는 markdown"
                    )

            with Horizontal(id="settings-buttons"):
                yield Button("저장 (Enter)", id="save-button", variant="primary")
                yield Button("기본값 복원", id="reset-button", variant="warning")
                yield Button("닫기 (ESC)", id="close-button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """버튼 클릭 이벤트"""
        if event.button.id == "save-button":
            self.action_save()
        elif event.button.id == "reset-button":
            self.action_reset()
        elif event.button.id == "close-button":
            self.action_close()

    def action_save(self) -> None:
        """설정 저장"""
        try:
            # 입력 필드에서 값 읽기
            max_log_lines = int(self.query_one("#max-log-lines", Input).value)
            max_history_size = int(self.query_one("#max-history-size", Input).value)
            worker_timeout = int(self.query_one("#worker-timeout", Input).value)
            log_export_format = self.query_one("#log-export-format", Input).value

            # Switch 상태 읽기
            enable_notifications = self.query_one("#enable-notifications", Switch).value
            notify_on_completion = self.query_one("#notify-on-completion", Switch).value
            notify_on_error = self.query_one("#notify-on-error", Switch).value
            enable_autocomplete = self.query_one("#enable-autocomplete", Switch).value

            # 설정 업데이트
            self.settings.max_log_lines = max_log_lines
            self.settings.max_history_size = max_history_size
            self.settings.worker_timeout = worker_timeout
            self.settings.enable_notifications = enable_notifications
            self.settings.notify_on_completion = notify_on_completion
            self.settings.notify_on_error = notify_on_error
            self.settings.enable_autocomplete = enable_autocomplete
            self.settings.log_export_format = log_export_format

            # 파일에 저장
            TUIConfig.save(self.settings)

            # 저장된 설정을 반환하며 모달 닫기
            self.dismiss(self.settings)

        except ValueError as e:
            # 사용자에게 에러 알림
            self.app.notify(f"잘못된 입력: {e}", severity="error")
            return  # 저장하지 않고 모달 유지

    def action_reset(self) -> None:
        """설정 기본값 복원"""
        default_settings = TUIConfig.reset_to_default()
        self.dismiss(default_settings)

    def action_close(self) -> None:
        """모달 닫기 (저장하지 않음)"""
        self.dismiss(None)
