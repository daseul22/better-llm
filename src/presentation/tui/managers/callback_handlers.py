"""
콜백 핸들러 매니저.

OrchestratorTUI의 외부 콜백 메서드들을 분리하여
워크플로우 및 Worker 출력 콜백을 담당합니다.
"""

import asyncio
import re
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
        # 병렬 Worker 탭 자동 제거 타이머 추적
        # {worker_name: asyncio.Task}
        self._removal_timers: Dict[str, asyncio.Task] = {}

    @staticmethod
    def _is_parallel_worker(worker_name: str) -> bool:
        """
        병렬 실행 Worker 여부 체크.

        병렬 실행 중 동적으로 생성된 Worker ID는 `coder_task_*` 패턴을 따릅니다.

        Args:
            worker_name: Worker 이름 (예: "coder_task_1", "coder", "planner")

        Returns:
            병렬 Worker이면 True, 아니면 False
        """
        return bool(re.match(r'^coder_task_\d+$', worker_name))

    def _should_auto_close_parallel_tabs(self) -> bool:
        """
        병렬 Worker 탭 자동 정리 설정 확인.

        system_config.json의 parallel_tasks.auto_close_tabs 값을 확인합니다.

        Returns:
            자동 정리 활성화 여부 (기본값: True)
        """
        try:
            return self.app.settings.get("parallel_tasks", {}).get("auto_close_tabs", True)
        except Exception as e:
            logger.warning(f"병렬 탭 자동 정리 설정 로드 실패: {e}, 기본값 True 사용")
            return True

    def _get_auto_close_delay(self) -> int:
        """
        병렬 Worker 탭 자동 정리 대기 시간 (초).

        system_config.json의 parallel_tasks.auto_close_delay_seconds 값을 확인합니다.

        Returns:
            대기 시간 (초, 기본값: 5)
        """
        try:
            delay = self.app.settings.get("parallel_tasks", {}).get("auto_close_delay_seconds", 5)
            # 유효성 검증: 1초 이상, 60초 이하
            if not isinstance(delay, (int, float)) or delay < 1 or delay > 60:
                logger.warning(f"병렬 탭 자동 정리 대기 시간이 유효하지 않음: {delay}, 기본값 5초 사용")
                return 5
            return int(delay)
        except Exception as e:
            logger.warning(f"병렬 탭 자동 정리 대기 시간 로드 실패: {e}, 기본값 5초 사용")
            return 5

    @staticmethod
    def _get_parallel_tab_label(worker_name: str, status_emoji: str = "▶️") -> str:
        """
        병렬 Worker 탭 라벨 생성.

        Args:
            worker_name: Worker 이름 (예: "coder_task_1")
            status_emoji: 상태 이모지 (기본값: "▶️")

        Returns:
            탭 라벨 문자열 (예: "[Parallel] task_1 ▶️")
        """
        # "coder_task_1" -> "task_1"
        task_id = worker_name.replace("coder_", "")
        return f"[Parallel] {task_id} {status_emoji}"

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

        병렬 실행 Worker의 경우 탭 라벨을 "[Parallel] task_id ▶️" 형식으로 설정합니다.
        (예: worker_name="coder_task_1" -> 탭 라벨="[Parallel] task_1 ▶️")

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
                # 탭이 이미 제거되었거나 존재하지 않음 (정상적인 경우)
                logger.debug("No workers tab already removed or doesn't exist")

            # 탭 라벨 결정: 병렬 Worker이면 "[Parallel] task_id ▶️" 형식
            if self._is_parallel_worker(worker_name):
                tab_label = self._get_parallel_tab_label(worker_name, status_emoji="▶️")
            else:
                tab_label = f"{worker_name.capitalize()} ▶️"

            # 새 탭 추가
            tab = WorkerTabPane(
                tab_label,
                worker_log,
                id=f"worker-tab-{worker_name}"
            )
            worker_tabs.add_pane(tab)
            worker_tabs.active = f"worker-tab-{worker_name}"

            logger.info(f"Worker 탭 생성: {worker_name} (라벨: {tab_label})")

        except Exception as e:
            logger.error(f"Worker 탭 생성 실패: {worker_name} - {e}")

    def _update_worker_tab_status(self, worker_name: str, status: str) -> None:
        """
        Worker 탭 상태 업데이트.

        병렬 실행 Worker의 경우 "[Parallel] task_id {emoji}" 형식으로 업데이트합니다.

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

                # 탭 라벨 결정: 병렬 Worker이면 "[Parallel] task_id {emoji}" 형식
                if self._is_parallel_worker(worker_name):
                    new_title = self._get_parallel_tab_label(worker_name, status_emoji=status_emoji)
                else:
                    new_title = f"{worker_name.capitalize()} {status_emoji}"

                # Textual 0.47+에서는 tab.label로 접근 가능
                if hasattr(tab, 'label'):
                    tab.label = new_title
                logger.info(f"Worker 탭 상태 업데이트: {worker_name} -> {status} (라벨: {new_title})")

                # 병렬 Worker가 완료되면 자동 정리 타이머 시작
                if (status == "completed" and
                    self._is_parallel_worker(worker_name) and
                    self._should_auto_close_parallel_tabs()):
                    delay = self._get_auto_close_delay()
                    # 비동기 타이머 생성 및 추적
                    timer_task = asyncio.create_task(
                        self._schedule_tab_removal(worker_name, delay)
                    )
                    self._removal_timers[worker_name] = timer_task
                    logger.info(
                        f"병렬 Worker 탭 자동 제거 예약: {worker_name} ({delay}초 후)"
                    )

            except NoMatches:
                logger.warning(f"Worker 탭을 찾을 수 없음: {worker_name}")

        except Exception as e:
            logger.error(f"Worker 탭 상태 업데이트 실패: {worker_name} - {e}")

    async def _schedule_tab_removal(self, worker_name: str, delay_seconds: int = 5) -> None:
        """
        병렬 Worker 탭 자동 제거 예약.

        지정된 시간 후 탭을 자동으로 제거합니다.
        중복 타이머를 방지하고, 탭이 이미 제거된 경우 처리합니다.

        Args:
            worker_name: Worker 이름 (예: "coder_task_1")
            delay_seconds: 제거 대기 시간 (초, 기본값: 5)
        """
        try:
            # 이미 타이머가 실행 중이면 취소
            if worker_name in self._removal_timers:
                old_timer = self._removal_timers[worker_name]
                if not old_timer.done():
                    old_timer.cancel()
                    logger.debug(f"기존 제거 타이머 취소: {worker_name}")

            # 대기
            await asyncio.sleep(delay_seconds)

            # 탭이 아직 존재하는지 확인
            tab_id = f"worker-tab-{worker_name}"
            try:
                tab = self.app.query_one(f"#{tab_id}", TabPane)
                # 탭이 존재하면 제거
                await self._remove_worker_tab(worker_name)
            except NoMatches:
                # 탭이 이미 제거됨 (정상적인 경우)
                logger.debug(f"제거 대상 탭이 이미 없음: {worker_name}")

        except asyncio.CancelledError:
            # 타이머가 취소됨 (정상적인 경우)
            logger.debug(f"탭 제거 타이머 취소됨: {worker_name}")
        except Exception as e:
            logger.error(f"탭 제거 예약 실패: {worker_name} - {e}")
        finally:
            # 타이머 추적에서 제거
            self._removal_timers.pop(worker_name, None)

    async def _remove_worker_tab(self, worker_name: str) -> None:
        """
        Worker 탭 제거.

        병렬 Worker 탭을 제거하고, active_workers 딕셔너리에서도 제거합니다.
        모든 Worker 탭이 제거되면 "No active workers" 탭을 다시 추가합니다.

        Args:
            worker_name: Worker 이름 (예: "coder_task_1")
        """
        try:
            worker_tabs = self.app.query_one("#worker-tabs", TabbedContent)
            tab_id = f"worker-tab-{worker_name}"

            # 탭 존재 확인
            try:
                tab = self.app.query_one(f"#{tab_id}", TabPane)
            except NoMatches:
                logger.debug(f"제거할 탭을 찾을 수 없음: {worker_name}")
                return

            # active_workers에서 제거
            if worker_name in self.app.active_workers:
                del self.app.active_workers[worker_name]
                logger.debug(f"active_workers에서 제거: {worker_name}")

            # 탭 제거
            worker_tabs.remove_pane(tab_id)
            logger.info(f"병렬 Worker 탭 제거: {worker_name}")

            # 모든 Worker 탭이 제거되었으면 "No active workers" 탭 추가
            if not self.app.active_workers:
                from ..widgets import WorkerTabPlaceholder
                no_workers_placeholder = WorkerTabPlaceholder()
                no_workers_tab = TabPane(
                    "No active workers",
                    no_workers_placeholder,
                    id="no-workers-tab"
                )
                worker_tabs.add_pane(no_workers_tab)
                worker_tabs.active = "no-workers-tab"
                logger.info("모든 Worker 탭 제거됨, 'No active workers' 탭 추가")

        except Exception as e:
            logger.error(f"Worker 탭 제거 실패: {worker_name} - {e}")

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
