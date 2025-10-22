"""
로그 필터 모달

로그 레벨, Worker, 시간대별 실시간 필터링 UI를 제공합니다.
Ctrl+Shift+F로 호출됩니다.
"""

from dataclasses import dataclass
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Input, Static, Button, Checkbox, Select
from textual.binding import Binding
from typing import Optional, Set, Dict, Any, List
from datetime import time, datetime

from ..utils.log_filter import LogFilter


@dataclass
class FilterConfig:
    """
    필터 설정.

    Attributes:
        levels: 선택된 로그 레벨 집합 (예: {"DEBUG", "INFO"})
        worker: 선택된 Worker 이름 (None 또는 "All"이면 모두)
        start_time: 시작 시각 (None이면 제한 없음)
        end_time: 종료 시각 (None이면 제한 없음)
    """
    levels: Set[str]
    worker: Optional[str]
    start_time: Optional[time]
    end_time: Optional[time]


class LogFilterModal(ModalScreen):
    """
    로그 필터 모달 스크린.

    로그 레벨, Worker, 시간대별 필터링 옵션을 제공합니다.
    """

    CSS = """
    LogFilterModal {
        align: center middle;
    }

    #filter-dialog {
        width: 70;
        height: auto;
        background: #0d1117;
        border: thick #388bfd;
        padding: 1 2;
    }

    .filter-section {
        height: auto;
        margin: 1 0;
        padding: 1;
        border: round #30363d;
    }

    .filter-label {
        color: #58a6ff;
        margin-bottom: 1;
    }

    .checkbox-container {
        height: auto;
        padding: 0 1;
    }

    #worker-select {
        width: 100%;
        margin: 1 0;
    }

    .time-input-container {
        height: auto;
        layout: horizontal;
    }

    .time-input {
        width: 1fr;
        margin: 0 1;
    }

    #filter-buttons {
        height: auto;
        margin-top: 1;
        layout: horizontal;
    }

    Button {
        margin: 0 1;
    }

    #filter-status {
        height: auto;
        color: #8b949e;
        padding: 1 0;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "닫기"),
        Binding("ctrl+a", "apply", "적용"),
        Binding("ctrl+r", "reset", "초기화"),
    ]

    def __init__(self, log_lines: List[str], available_workers: List[str]):
        """
        초기화.

        Args:
            log_lines: 현재 로그 라인 리스트 (Worker 추출용)
            available_workers: 사용 가능한 Worker 이름 리스트
        """
        super().__init__()
        self.log_lines = log_lines
        self.available_workers = available_workers
        self.log_filter = LogFilter()

        # 기본 필터 설정 (모든 레벨, 모든 Worker, 모든 시간)
        self.current_config = FilterConfig(
            levels={"DEBUG", "INFO", "WARNING", "ERROR"},
            worker="All",
            start_time=None,
            end_time=None
        )

    def compose(self) -> ComposeResult:
        """UI 구성"""
        with Container(id="filter-dialog"):
            yield Static("[bold cyan]🔍 로그 필터[/bold cyan]")

            # 1. 로그 레벨 필터 섹션
            with Vertical(classes="filter-section"):
                yield Static("[bold]로그 레벨[/bold]", classes="filter-label")
                with Vertical(classes="checkbox-container"):
                    yield Checkbox("DEBUG", id="level-debug", value=True)
                    yield Checkbox("INFO", id="level-info", value=True)
                    yield Checkbox("WARNING", id="level-warning", value=True)
                    yield Checkbox("ERROR", id="level-error", value=True)

            # 2. Worker 필터 섹션
            with Vertical(classes="filter-section"):
                yield Static("[bold]Worker[/bold]", classes="filter-label")
                # Worker 목록 생성 (All + 사용 가능한 Worker)
                worker_options = [("All", "All")] + \
                                 [(w, w) for w in self.available_workers]
                yield Select(
                    options=worker_options,
                    id="worker-select",
                    value="All"
                )

            # 3. 시간대 필터 섹션
            with Vertical(classes="filter-section"):
                yield Static("[bold]시간대 (HH:MM:SS)[/bold]", classes="filter-label")
                with Horizontal(classes="time-input-container"):
                    yield Input(
                        placeholder="시작 (예: 14:30:00)",
                        id="start-time-input",
                        classes="time-input"
                    )
                    yield Input(
                        placeholder="종료 (예: 15:30:00)",
                        id="end-time-input",
                        classes="time-input"
                    )

            # 4. 상태 메시지
            yield Static("", id="filter-status")

            # 5. 버튼
            with Horizontal(id="filter-buttons"):
                yield Button("적용 (Ctrl+A)", id="apply-button", variant="primary")
                yield Button("초기화 (Ctrl+R)", id="reset-button")
                yield Button("닫기 (ESC)", id="close-button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """버튼 클릭 이벤트"""
        if event.button.id == "apply-button":
            self.action_apply()
        elif event.button.id == "reset-button":
            self.action_reset()
        elif event.button.id == "close-button":
            self.action_close()

    def action_apply(self) -> None:
        """필터 적용"""
        try:
            # 1. 로그 레벨 수집
            levels = set()
            if self.query_one("#level-debug", Checkbox).value:
                levels.add("DEBUG")
            if self.query_one("#level-info", Checkbox).value:
                levels.add("INFO")
            if self.query_one("#level-warning", Checkbox).value:
                levels.add("WARNING")
            if self.query_one("#level-error", Checkbox).value:
                levels.add("ERROR")

            # 레벨이 하나도 선택되지 않았으면 경고
            if not levels:
                self._show_status("⚠️ 최소 하나의 로그 레벨을 선택하세요", error=True)
                return

            # 2. Worker 선택
            worker_select = self.query_one("#worker-select", Select)
            worker = worker_select.value

            # 3. 시간대 파싱
            start_time_input = self.query_one("#start-time-input", Input)
            end_time_input = self.query_one("#end-time-input", Input)

            start_time = None
            end_time = None

            # 시작 시각 파싱
            if start_time_input.value.strip():
                try:
                    start_time = datetime.strptime(
                        start_time_input.value.strip(),
                        "%H:%M:%S"
                    ).time()
                except ValueError:
                    self._show_status(
                        "⚠️ 시작 시각 형식이 잘못되었습니다 (HH:MM:SS)",
                        error=True
                    )
                    return

            # 종료 시각 파싱
            if end_time_input.value.strip():
                try:
                    end_time = datetime.strptime(
                        end_time_input.value.strip(),
                        "%H:%M:%S"
                    ).time()
                except ValueError:
                    self._show_status(
                        "⚠️ 종료 시각 형식이 잘못되었습니다 (HH:MM:SS)",
                        error=True
                    )
                    return

            # 시간 범위 검증
            if start_time and end_time and start_time > end_time:
                self._show_status(
                    "⚠️ 시작 시각이 종료 시각보다 늦습니다",
                    error=True
                )
                return

            # 4. 필터 설정 업데이트
            self.current_config = FilterConfig(
                levels=levels,
                worker=worker,
                start_time=start_time,
                end_time=end_time
            )

            # 5. 필터 적용 결과 전달 (부모 앱으로)
            self._show_status("✅ 필터 적용 중...", error=False)
            self.dismiss(self.current_config)

        except Exception as e:
            self._show_status(f"❌ 필터 적용 실패: {e}", error=True)

    def action_reset(self) -> None:
        """필터 초기화"""
        try:
            # 1. 모든 레벨 체크
            self.query_one("#level-debug", Checkbox).value = True
            self.query_one("#level-info", Checkbox).value = True
            self.query_one("#level-warning", Checkbox).value = True
            self.query_one("#level-error", Checkbox).value = True

            # 2. Worker를 "All"로 설정
            worker_select = self.query_one("#worker-select", Select)
            worker_select.value = "All"

            # 3. 시간대 입력 초기화
            self.query_one("#start-time-input", Input).value = ""
            self.query_one("#end-time-input", Input).value = ""

            # 4. 상태 메시지 표시
            self._show_status("🔄 필터가 초기화되었습니다", error=False)

            # 5. 필터 설정 초기화
            self.current_config = FilterConfig(
                levels={"DEBUG", "INFO", "WARNING", "ERROR"},
                worker="All",
                start_time=None,
                end_time=None
            )

        except Exception as e:
            self._show_status(f"❌ 초기화 실패: {e}", error=True)

    def action_close(self) -> None:
        """모달 닫기 (필터 적용 안 함)"""
        self.dismiss(None)

    def _show_status(self, message: str, error: bool = False) -> None:
        """
        상태 메시지 표시.

        Args:
            message: 표시할 메시지
            error: 에러 메시지 여부
        """
        try:
            status = self.query_one("#filter-status", Static)
            if error:
                status.update(f"[red]{message}[/red]")
            else:
                status.update(f"[green]{message}[/green]")
        except Exception:
            # 상태 위젯이 없으면 무시 (초기화 중일 수 있음)
            pass
