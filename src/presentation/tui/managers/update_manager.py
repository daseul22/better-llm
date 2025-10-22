"""
업데이트 매니저.

OrchestratorTUI의 update_* 메서드들을 분리하여
타이머 기반 UI 업데이트를 담당합니다.
"""

import time
from typing import TYPE_CHECKING, Optional

from textual.widgets import Static

from ..widgets import WorkflowVisualizer
from src.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from ..tui_app import OrchestratorTUI

logger = get_logger(__name__, component="UpdateManager")


class UpdateManager:
    """
    업데이트 매니저.

    타이머 기반 UI 업데이트를 담당합니다:
    - Worker 상태 업데이트 (0.2초마다)
    - 메트릭 패널 업데이트 (1초마다)
    - 토큰 사용량 업데이트 (1초마다)
    """

    def __init__(self, app: "OrchestratorTUI") -> None:
        """
        초기화.

        Args:
            app: OrchestratorTUI 인스턴스
        """
        self.app = app

    def update_worker_status(self, message: str) -> None:
        """
        Worker Tool 상태 메시지 업데이트.

        Args:
            message: 상태 메시지
        """
        try:
            worker_status = self.app.query_one("#worker-status", Static)
            worker_status.update(message)
        except Exception as e:
            # 위젯이 아직 마운트되지 않았거나 접근 불가능한 경우 (정상적인 초기화 과정)
            logger.debug(f"Worker status widget not available, skipping update: {e}")

    def update_worker_status_timer(self) -> None:
        """
        타이머: Worker Tool 실행 시간 업데이트 (0.2초마다 호출).
        """
        if not self.app.timer_active or self.app.task_start_time is None:
            return

        try:
            elapsed = time.time() - self.app.task_start_time
            # 애니메이션 효과를 위한 스피너
            spinner_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
            spinner = spinner_frames[int(elapsed * 2) % len(spinner_frames)]

            # WorkflowVisualizer에서 실행 중인 워커 정보 가져오기
            workflow_visualizer = self.app.query_one("#workflow-visualizer", WorkflowVisualizer)
            running_workers = workflow_visualizer.get_running_workers()

            # status-info에 실행 시간 및 워커 정보 표시
            status_info = self.app.query_one("#status-info", Static)

            if running_workers:
                # 실행 중인 워커가 있으면 워커 정보 표시
                worker_name, worker_elapsed = running_workers[0]  # 첫 번째 워커만 표시
                worker_emoji = {
                    "planner": "🧠",
                    "coder": "💻",
                    "reviewer": "🔍",
                    "tester": "🧪",
                    "committer": "📝",
                }.get(worker_name.lower(), "🔧")

                status_info.update(
                    f"{spinner} Running... ⏱️ {elapsed:.1f}s • "
                    f"{worker_emoji} {worker_name.capitalize()} ({worker_elapsed:.1f}s)"
                )
            else:
                # 워커 정보 없으면 기본 표시
                status_info.update(f"{spinner} Running... ⏱️  {elapsed:.1f}s")

            # worker-status는 표시되어 있을 때만 업데이트
            if self.app.show_worker_status:
                if running_workers:
                    worker_name, worker_elapsed = running_workers[0]
                    worker_emoji = {
                        "planner": "🧠",
                        "coder": "💻",
                        "reviewer": "🔍",
                        "tester": "🧪",
                        "committer": "📝",
                    }.get(worker_name.lower(), "🔧")
                    self.update_worker_status(
                        f"{spinner} {worker_emoji} {worker_name.capitalize()} 실행 중... ⏱️  {worker_elapsed:.1f}s"
                    )
                else:
                    self.update_worker_status(f"{spinner} Manager Agent 실행 중... ⏱️  {elapsed:.1f}s")
        except Exception as e:
            # 타이머 업데이트 중 예외 발생 (위젯 접근 실패 등)
            # 타이머는 계속 실행되므로 debug 레벨로 로깅
            logger.debug(f"Worker status timer update failed: {e}")

    def update_token_info(self) -> None:
        """
        타이머: 토큰 사용량 업데이트 (1초마다 호출).
        Manager + Worker 토큰 사용량을 통합하여 표시합니다.
        """
        try:
            token_info_widget = self.app.query_one("#token-info", Static)

            if not self.app.manager:
                # Manager 초기화 전: 기본값 표시
                token_info_widget.update("🟢 Tokens: 0/200K (0% used, 100% free)")
                return

            # Manager Agent에서 토큰 사용량 가져오기
            manager_usage = self.app.manager.get_token_usage()
            logger.debug(f"[TUI] Manager usage: {manager_usage}")

            manager_total = manager_usage["total_tokens"]
            manager_input = manager_usage["input_tokens"]
            manager_output = manager_usage["output_tokens"]

            # Worker Agent 토큰 사용량 가져오기 (세션 메트릭에서)
            session_metrics = self.app.metrics_collector.get_session_summary(self.app.session_id)
            logger.debug(f"[TUI] Session metrics exists: {session_metrics is not None}")

            worker_total = 0
            worker_input = 0
            worker_output = 0
            worker_cache_read = 0
            worker_cache_creation = 0

            if session_metrics:
                logger.debug(f"[TUI] Number of worker metrics: {len(session_metrics.workers_metrics)}")
                for metric in session_metrics.workers_metrics:
                    logger.debug(
                        f"[TUI] Worker {metric.worker_name}: "
                        f"input={metric.input_tokens}, output={metric.output_tokens}, "
                        f"cache_read={metric.cache_read_tokens}, cache_creation={metric.cache_creation_tokens}"
                    )
                    worker_input += metric.input_tokens or 0
                    worker_output += metric.output_tokens or 0
                    worker_cache_read += metric.cache_read_tokens or 0
                    worker_cache_creation += metric.cache_creation_tokens or 0
                worker_total = worker_input + worker_output
            else:
                logger.debug("[TUI] No session metrics found")

            # 전체 토큰 계산
            total_tokens = manager_total + worker_total
            total_input = manager_input + worker_input
            total_output = manager_output + worker_output

            logger.debug(
                f"[TUI] Total tokens: {total_tokens} (Manager: {manager_total}, Worker: {worker_total})"
            )

            # 모델별 컨텍스트 윈도우 (토큰 수)
            # Claude Sonnet 4.5: 200K context window
            context_window = 200_000

            # 사용률 계산
            usage_percentage = (total_tokens / context_window) * 100 if context_window > 0 else 0
            remaining_percentage = 100 - usage_percentage

            # 표시 형식 생성
            if total_tokens >= 1000:
                total_display = f"{total_tokens / 1000:.1f}K"
            else:
                total_display = str(total_tokens)

            # 색상: 초록(< 50%), 노랑(50-80%), 빨강(>= 80%)
            if usage_percentage < 50:
                color = "green"
                emoji = "🟢"
            elif usage_percentage < 80:
                color = "yellow"
                emoji = "🟡"
            else:
                color = "red"
                emoji = "🔴"

            # 상세 정보 표시 (한 줄)
            # 형식: 🟢 Tokens: 15.2K/200K (7.6% used, 92.4% free) • M: 10K W: 5K
            token_info_widget.update(
                f"[{color}]{emoji} {total_display}/200K ({usage_percentage:.1f}% used, {remaining_percentage:.1f}% free)[/{color}] "
                f"[dim]• M:{manager_total:,} W:{worker_total:,}[/dim]"
            )

        except Exception as e:
            logger.warning(f"토큰 정보 업데이트 실패: {e}")

    def update_metrics_panel(self) -> None:
        """
        메트릭 패널 업데이트 (MetricsUIManager로 위임).
        """
        try:
            metrics_panel = self.app.query_one("#metrics-panel", Static)
            # 현재 메트릭 수집기에서 메트릭 가져오기
            metrics = self.app.metrics_collector.get_all_metrics()
            if metrics:
                # MetricsUIManager의 render_dashboard() 사용
                dashboard = self.app.metrics_ui_manager.render_dashboard(metrics)
                metrics_panel.update(dashboard)
            else:
                metrics_panel.update("📊 메트릭 없음")
        except Exception as e:
            logger.warning(f"메트릭 패널 업데이트 실패: {e}")
