"""
UI 컴포넌트 조립 매니저.

OrchestratorTUI의 compose() 메서드 로직을 분리하여
UI 컴포넌트 구성을 담당합니다.
"""

from pathlib import Path
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, Vertical, ScrollableContainer, Horizontal
from textual.widgets import Footer, Input, Static, RichLog, Header, TabbedContent, TabPane

from ..widgets import (
    HelpModal,
    SearchModal,
    MultilineInput,
    SessionBrowserModal,
    WorkflowVisualizer,
    WorkerStatus,
)

if TYPE_CHECKING:
    from ..tui_app import OrchestratorTUI


class UIComposer:
    """
    UI 컴포넌트 조립 매니저.

    OrchestratorTUI의 compose() 메서드를 대신하여
    UI 컴포넌트를 구성합니다.
    """

    def __init__(self, app: "OrchestratorTUI"):
        """
        초기화.

        Args:
            app: OrchestratorTUI 인스턴스
        """
        self.app = app

    def compose(self) -> ComposeResult:
        """
        UI 컴포넌트 구성.

        Returns:
            UI 컴포넌트 생성기
        """
        # Manager 출력 영역
        with ScrollableContainer(id="output-container"):
            yield RichLog(id="output-log", markup=True, highlight=True, wrap=True)

        # Worker 출력 영역 (TabbedContent 기반, 기본 숨김)
        with Container(id="worker-output-container", classes="hidden"):
            with TabbedContent(id="worker-tabs"):
                # 기본 상태: "No active workers" 탭 표시
                with TabPane("No active workers", id="no-workers-tab"):
                    yield Static(
                        "[dim]실행 중인 Worker가 없습니다[/dim]",
                        id="no-workers-message"
                    )

        # Worker 상태 표시
        with Container(id="worker-status-container"):
            yield Static("⏳ 초기화 중...", id="worker-status")

        # 메트릭 대시보드
        with Container(id="metrics-container"):
            yield Static("📊 메트릭 없음", id="metrics-panel")

        # 워크플로우 비주얼라이저
        with Container(id="workflow-container"):
            yield WorkflowVisualizer(id="workflow-visualizer")

        # 입력 영역
        with Container(id="input-container"):
            yield MultilineInput(
                id="task-input"
            )
            yield Static("", id="autocomplete-preview", classes="hidden")

        # 하단 정보바
        with Horizontal(id="info-bar"):
            session_id = self.app.session_id
            yield Static(f"Session: {session_id}", id="session-info")
            yield Static("Ready", id="status-info")
            yield Static("Tokens: 0K", id="token-info")

        yield Footer()
