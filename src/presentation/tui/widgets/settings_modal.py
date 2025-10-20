"""
설정 모달 위젯

TUI 설정을 변경할 수 있는 모달 화면
"""

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, Grid, ScrollableContainer
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
        height: 25;
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

            with ScrollableContainer(id="settings-content"):
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

                # UI 패널 표시 설정
                with Horizontal(classes="setting-row"):
                    yield Static("메트릭 패널 표시:", classes="setting-label")
                    yield Switch(
                        self.settings.show_metrics_panel,
                        id="show-metrics-panel",
                        classes="setting-control"
                    )

                with Horizontal(classes="setting-row"):
                    yield Static("워크플로우 패널 표시:", classes="setting-label")
                    yield Switch(
                        self.settings.show_workflow_panel,
                        id="show-workflow-panel",
                        classes="setting-control"
                    )

                with Horizontal(classes="setting-row"):
                    yield Static("Worker 상태 표시:", classes="setting-label")
                    yield Switch(
                        self.settings.show_worker_status,
                        id="show-worker-status",
                        classes="setting-control"
                    )

                # 에러 통계 설정
                with Horizontal(classes="setting-row"):
                    yield Static("작업 완료 시 에러 통계 표시:", classes="setting-label")
                    yield Switch(
                        self.settings.show_error_stats_on_complete,
                        id="show-error-stats-on-complete",
                        classes="setting-control"
                    )

            with Horizontal(id="settings-buttons"):
                yield Button("저장 (Enter)", id="save-button", variant="primary")
                yield Button("기본값 복원", id="reset-button", variant="warning")
                yield Button("닫기 (ESC)", id="close-button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        버튼 클릭 이벤트 핸들러

        Args:
            event: 버튼 클릭 이벤트 객체
        """
        if event.button.id == "save-button":
            self.action_save()
        elif event.button.id == "reset-button":
            self.action_reset()
        elif event.button.id == "close-button":
            self.action_close()

    def action_save(self) -> None:
        """
        설정 저장 액션

        입력 필드와 스위치 값을 읽어서 설정 객체를 업데이트하고 파일에 저장합니다.
        저장 성공 시 업데이트된 설정을 반환하며 모달을 닫습니다.
        잘못된 입력 시 에러 알림을 표시하고 모달을 유지합니다.

        Raises:
            ValueError: 입력값이 유효하지 않을 때
        """
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
            show_metrics_panel = self.query_one("#show-metrics-panel", Switch).value
            show_workflow_panel = self.query_one("#show-workflow-panel", Switch).value
            show_worker_status = self.query_one("#show-worker-status", Switch).value
            show_error_stats_on_complete = self.query_one("#show-error-stats-on-complete", Switch).value

            # 설정 업데이트
            self.settings.max_log_lines = max_log_lines
            self.settings.max_history_size = max_history_size
            self.settings.worker_timeout = worker_timeout
            self.settings.enable_notifications = enable_notifications
            self.settings.notify_on_completion = notify_on_completion
            self.settings.notify_on_error = notify_on_error
            self.settings.enable_autocomplete = enable_autocomplete
            self.settings.log_export_format = log_export_format
            self.settings.show_metrics_panel = show_metrics_panel
            self.settings.show_workflow_panel = show_workflow_panel
            self.settings.show_worker_status = show_worker_status
            self.settings.show_error_stats_on_complete = show_error_stats_on_complete

            # 파일에 저장
            TUIConfig.save(self.settings)

            # 저장된 설정을 반환하며 모달 닫기
            self.dismiss(self.settings)

        except ValueError as e:
            # 사용자에게 에러 알림
            self.app.notify(f"잘못된 입력: {e}", severity="error")
            return  # 저장하지 않고 모달 유지

    def action_reset(self) -> None:
        """
        설정 기본값 복원 액션

        모든 설정을 기본값으로 리셋하고 파일에 저장한 후,
        기본값 설정을 반환하며 모달을 닫습니다.
        """
        default_settings = TUIConfig.reset_to_default()
        self.dismiss(default_settings)

    def action_close(self) -> None:
        """
        모달 닫기 액션

        변경사항을 저장하지 않고 모달을 닫습니다.
        None을 반환하여 설정이 변경되지 않았음을 알립니다.
        """
        self.dismiss(None)
