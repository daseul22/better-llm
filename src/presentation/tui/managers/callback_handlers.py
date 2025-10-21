"""
콜백 핸들러 매니저.

OrchestratorTUI의 외부 콜백 메서드들을 분리하여
워크플로우 및 Worker 출력 콜백을 담당합니다.
"""

from typing import TYPE_CHECKING, Optional, Dict

from textual.widgets import RichLog, TabbedContent, TabPane
from textual.css.query import NoMatches

from ..widgets import WorkflowVisualizer
from ..utils import WorkerOutputParser
from src.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from ..tui_app import OrchestratorTUI

logger = get_logger(__name__, component="CallbackHandlers")


class WorkerTabPane(TabPane):
    """
    Worker 출력을 담는 커스텀 TabPane.

    Textual의 공식 API를 사용하여 TabPane에 위젯을 추가합니다.
    Private API (_add_child)를 사용하지 않고 compose() 메서드를 오버라이드합니다.

    탭 제목 업데이트가 필요한 경우 TabPane.label을 직접 수정하는 대신
    탭을 재생성하는 방식을 사용합니다 (Textual 공식 권장 방식).
    """

    def __init__(self, title: str, worker_log: RichLog, **kwargs):
        """
        WorkerTabPane 초기화.

        Args:
            title: 탭 제목
            worker_log: Worker 출력을 표시할 RichLog 위젯
            **kwargs: TabPane의 추가 인자 (id 등)
        """
        from textual.app import ComposeResult

        super().__init__(title, **kwargs)
        self._worker_log = worker_log

    def compose(self):
        """TabPane에 표시할 위젯 구성."""
        from textual.app import ComposeResult
        yield self._worker_log


class CallbackHandlers:
    """
    콜백 핸들러 매니저.

    외부에서 호출되는 콜백 메서드들을 담당합니다:
    - 워크플로우 상태 업데이트 콜백
    - Worker 출력 콜백
    """

    def __init__(self, app: "OrchestratorTUI"):
        """
        초기화.

        Args:
            app: OrchestratorTUI 인스턴스
        """
        self.app = app

    def on_workflow_update(self, worker_name: str, status: str, error: Optional[str] = None) -> None:
        """
        워크플로우 상태 업데이트 콜백.

        Args:
            worker_name: Worker 이름
            status: 상태 (running, completed, failed 등)
            error: 에러 메시지 (옵션)
        """
        # WorkflowVisualizer 위젯을 직접 업데이트
        self._update_workflow_ui(worker_name, status, error)

    def _update_workflow_ui(self, worker_name: str, status: str, error: Optional[str] = None) -> None:
        """
        워크플로우 UI 업데이트.

        Args:
            worker_name: Worker 이름
            status: 상태
            error: 에러 메시지 (옵션)
        """
        try:
            # WorkflowVisualizer 위젯 업데이트
            workflow_visualizer = self.app.query_one("#workflow-visualizer", WorkflowVisualizer)
            workflow_visualizer.update_worker_status(worker_name, status, error)

            # Worker 실행 시작 시 새 탭 생성 및 등록
            if status == "running":
                self._create_worker_tab(worker_name)
                self.app.current_worker_tab = worker_name

            # Worker 실행 완료/실패 시 탭 업데이트 (히스토리 보존)
            elif status in ["completed", "failed"]:
                self._update_worker_tab_status(worker_name, status)

        except Exception as e:
            logger.warning(f"워크플로우 업데이트 실패: {e}")

    def _create_worker_tab(self, worker_name: str) -> None:
        """
        Worker 탭 생성.

        Args:
            worker_name: Worker 이름
        """
        try:
            # 이미 생성된 탭이 있으면 스킵
            if worker_name in self.app.active_workers:
                return

            # RichLog 생성
            worker_log = RichLog(
                id=f"worker-log-{worker_name}",
                markup=True,  # 정제된 출력에서 Rich 마크업 사용
                highlight=False,  # Worker 출력은 구문 강조 비활성화
                wrap=True
            )
            self.app.active_workers[worker_name] = worker_log

            # WorkerTabPane 생성 및 추가
            worker_tabs = self.app.query_one("#worker-tabs", TabbedContent)

            # "No active workers" 탭 제거
            try:
                no_workers_tab = self.app.query_one("#no-workers-tab", TabPane)
                worker_tabs.remove_children([no_workers_tab])
            except NoMatches:
                pass  # 이미 제거됨

            # 새 탭 추가
            tab = WorkerTabPane(
                f"{worker_name.capitalize()} ▶️",
                worker_log,
                id=f"worker-tab-{worker_name}"
            )
            worker_tabs.add_pane(tab)
            worker_tabs.active = f"worker-tab-{worker_name}"

            logger.info(f"Worker 탭 생성: {worker_name}")

        except Exception as e:
            logger.error(f"Worker 탭 생성 실패: {worker_name} - {e}")

    def _update_worker_tab_status(self, worker_name: str, status: str) -> None:
        """
        Worker 탭 상태 업데이트.

        Args:
            worker_name: Worker 이름
            status: 상태 (completed, failed 등)
        """
        try:
            if worker_name not in self.app.active_workers:
                return

            # 탭 제목 업데이트 (Textual API 제약으로 인해 재생성 방식 사용)
            worker_tabs = self.app.query_one("#worker-tabs", TabbedContent)

            # 상태 이모지 결정
            status_emoji = {
                "completed": "✅",
                "failed": "❌",
                "running": "▶️"
            }.get(status, "⏸️")

            # 기존 탭 제목 업데이트 (Textual의 TabPane.label 사용)
            try:
                tab = self.app.query_one(f"#worker-tab-{worker_name}", TabPane)
                # TabPane의 label 속성 직접 수정 (공식 API)
                new_title = f"{worker_name.capitalize()} {status_emoji}"
                # Textual 0.47+에서는 tab.label로 접근 가능
                if hasattr(tab, 'label'):
                    tab.label = new_title
                logger.info(f"Worker 탭 상태 업데이트: {worker_name} -> {status}")
            except NoMatches:
                logger.warning(f"Worker 탭을 찾을 수 없음: {worker_name}")

        except Exception as e:
            logger.error(f"Worker 탭 상태 업데이트 실패: {worker_name} - {e}")

    def on_worker_output(self, worker_name: str, chunk: str) -> None:
        """
        Worker 출력 콜백.

        Args:
            worker_name: Worker 이름
            chunk: 출력 청크
        """
        self._write_worker_output(worker_name, chunk)

    def _write_worker_output(self, worker_name: str, chunk: str) -> None:
        """
        Worker 출력 작성 (파싱 및 정제 적용, v2.0 Rich UI 지원).

        Args:
            worker_name: Worker 이름
            chunk: 출력 청크
        """
        try:
            if worker_name not in self.app.active_workers:
                logger.warning(f"Worker 탭을 찾을 수 없음: {worker_name}")
                return

            # Worker 출력 파싱 및 정제 (v2.0: Rich Renderable 반환 가능)
            formatted_chunk = WorkerOutputParser.format_for_display(chunk, worker_name)

            worker_log = self.app.active_workers[worker_name]

            # 빈 값 체크 (str과 Rich Renderable 모두 지원)
            if formatted_chunk is None:
                return

            # 문자열인 경우 빈 값 체크
            if isinstance(formatted_chunk, str) and not formatted_chunk.strip():
                return

            # RichLog.write()는 str과 Rich Renderable (Panel, Table 등)을 모두 지원
            worker_log.write(formatted_chunk)

            # WorkerOutputManager에도 기록 (히스토리 관리, 원본 유지)
            self.app.worker_output_manager.stream_output(worker_name, chunk)

        except Exception as e:
            logger.error(f"Worker 출력 작성 실패: {worker_name} - {e}")
