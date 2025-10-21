"""
초기화 매니저.

OrchestratorTUI의 초기화 로직을 분리하여
앱 시작 시 필요한 초기화 작업을 담당합니다.
"""

import os
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Tuple, List, Any

from textual.widgets import Static, RichLog

from src.domain.services import ConversationHistory, ProjectContextAnalyzer, MetricsCollector
from src.infrastructure.claude import ManagerAgent
from src.infrastructure.mcp import (
    initialize_workers,
    create_worker_tools_server,
    set_metrics_collector,
    set_workflow_callback,
    set_worker_output_callback,
)
from src.infrastructure.config import (
    validate_environment,
    get_project_root,
    JsonConfigLoader,
)
from src.infrastructure.logging import get_logger
from src.presentation.cli.feedback import TUIFeedbackWidget, FeedbackType

if TYPE_CHECKING:
    from ..tui_app import OrchestratorTUI

logger = get_logger(__name__, component="InitializationManager")


class InitializationManager:
    """
    초기화 매니저.

    앱 시작 시 필요한 초기화 작업을 수행합니다:
    - 환경 검증
    - Worker Agent 초기화
    - Manager Agent 초기화
    - 콜백 설정
    """

    def __init__(self, app: "OrchestratorTUI") -> None:
        """
        초기화.

        Args:
            app: OrchestratorTUI 인스턴스
        """
        self.app = app

    async def initialize_orchestrator(self) -> None:
        """
        오케스트레이터 초기화.

        환경 검증 → Worker 초기화 → Manager 초기화 → 콜백 설정 순서로 진행
        """
        worker_status = self.app.query_one("#worker-status", Static)
        status_info = self.app.query_one("#status-info", Static)

        try:
            worker_status.update("⏳ 초기화 중...")
            status_info.update("Initializing...")

            # 1. 환경 검증
            await self._validate_environment()

            # 2. Worker Agent들 초기화
            worker_names, worker_count = await self._initialize_workers()

            # 3. Worker Tools MCP Server 생성
            worker_tools_server = create_worker_tools_server()

            # 4. Manager Agent 초기화
            auto_commit_enabled = await self._initialize_manager(worker_tools_server)

            # 5. 메트릭 & 콜백 설정
            await self._setup_callbacks()

            # 6. 초기화 완료 표시
            self.app.initialized = True
            worker_status.update("✅ 준비 완료")
            status_info.update("Ready")

            # 7. 환영 메시지 표시
            await self._display_welcome_message(worker_count, auto_commit_enabled)

        except Exception as e:
            # 피드백 시스템 사용
            error_panel = TUIFeedbackWidget.create_panel(
                "초기화에 실패했습니다",
                FeedbackType.ERROR,
                details=str(e)
            )
            self.app.log_manager.write_log(error_panel)
            worker_status.update(f"❌ 오류: {e}")
            status_info.update("Error")
            logger.error(f"초기화 실패: {e}", exc_info=True)

    async def _validate_environment(self) -> None:
        """
        환경 검증.

        Raises:
            Exception: 환경 검증 실패 시
        """
        validate_environment()
        work_dir = os.getcwd()
        oauth_token = os.getenv("CLAUDE_CODE_OAUTH_TOKEN", "").strip()
        token_status = "설정됨" if (oauth_token and len(oauth_token) > 10) else "미설정"
        logger.info(f"환경 검증 완료: work_dir={work_dir}, oauth_token={token_status}")

    async def _initialize_workers(self) -> Tuple[List[str], int]:
        """
        Worker Agent들 초기화.

        Returns:
            (worker_names, worker_count): Worker 이름 리스트 및 개수

        Raises:
            ValueError: Worker Agent가 정의되지 않은 경우
        """
        config_path = get_project_root() / "config" / "agent_config.json"
        initialize_workers(config_path)

        # agent_config.json에서 Worker 목록 로드
        config_loader = JsonConfigLoader(get_project_root())
        agents = config_loader.load_agent_configs()

        if not agents:
            raise ValueError(
                "agent_config.json에 Worker Agent가 정의되지 않았습니다. "
                "config/agent_config.json 파일을 확인해주세요."
            )

        worker_names = [agent.name.capitalize() for agent in agents]
        worker_count = len(worker_names)
        worker_list = ", ".join(worker_names)

        logger.info(f"Worker 초기화 완료: {worker_count}개 ({worker_list})")
        return worker_names, worker_count

    async def _initialize_manager(self, worker_tools_server: Any) -> bool:
        """
        Manager Agent 초기화.

        Args:
            worker_tools_server: Worker Tools MCP Server

        Returns:
            auto_commit_enabled: 자동 커밋 활성화 여부
        """
        # system_config 로드
        config_loader = JsonConfigLoader(get_project_root())
        system_config = config_loader.load_system_config()
        auto_commit_enabled = system_config.get("workflow", {}).get("auto_commit_enabled", False)
        manager_model = system_config.get("manager", {}).get("model", "unknown")

        # Manager Agent 초기화
        self.app.manager = ManagerAgent(
            worker_tools_server,
            auto_commit_enabled=auto_commit_enabled
        )

        logger.info(f"Manager Agent 초기화 완료: model={manager_model}, auto_commit={auto_commit_enabled}")
        return auto_commit_enabled

    async def _setup_callbacks(self) -> None:
        """
        메트릭 & 콜백 설정.
        """
        set_metrics_collector(self.app.metrics_collector, self.app.session_id)
        set_workflow_callback(self.app.callback_handlers.on_workflow_update)
        set_worker_output_callback(self.app.callback_handlers.on_worker_output)
        logger.info("콜백 설정 완료")

    async def _display_welcome_message(self, worker_count: int, auto_commit_enabled: bool) -> None:
        """
        환영 메시지 표시.

        Args:
            worker_count: Worker 개수
            auto_commit_enabled: 자동 커밋 활성화 여부
        """
        # system_config에서 Manager 모델 정보 가져오기
        config_loader = JsonConfigLoader(get_project_root())
        system_config = config_loader.load_system_config()
        manager_model = system_config.get("manager", {}).get("model", "unknown")

        # 컴팩트한 초기화 완료 메시지
        self.app.log_manager.write_log("")
        self.app.log_manager.write_log(
            f"[bold green]🚀 준비 완료[/bold green] [dim]• Workers: {worker_count}개 • Model: {manager_model}[/dim]"
        )
        self.app.log_manager.write_log("")
        self.app.log_manager.write_log("[dim]💡 Tip: Ctrl+R (입력 제출) | Ctrl+H (도움말) | Ctrl+F (검색) | Ctrl+M (메트릭)[/dim]")
        self.app.log_manager.write_log("[dim]     Enter는 줄바꿈, Ctrl+R로 제출하세요[/dim]")
        self.app.log_manager.write_log("")
