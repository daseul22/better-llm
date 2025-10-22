"""
슬래시 커맨드 처리 핸들러

OrchestratorTUI의 슬래시 커맨드 처리 로직을 분리하여
단일 책임 원칙(SRP)을 준수합니다.
"""

from typing import TYPE_CHECKING, Callable, Any, Dict, List
from pathlib import Path

from textual.widgets import RichLog, Static
from rich.panel import Panel
from rich.table import Table

from src.domain.services import ProjectContextAnalyzer
from src.infrastructure.config import get_project_root
from src.infrastructure.storage import JsonContextRepository
from src.infrastructure.logging import get_logger
from src.infrastructure.mcp import set_metrics_collector, update_session_id
from src.presentation.cli.utils import generate_session_id
from src.presentation.cli.feedback import TUIFeedbackWidget, FeedbackType

if TYPE_CHECKING:
    from src.presentation.tui.managers import SessionManager

logger = get_logger(__name__, component="SlashCommandHandler")


class SlashCommandHandler:
    """
    슬래시 커맨드 처리 전담 클래스

    OrchestratorTUI의 슬래시 커맨드 처리 로직을 분리하여
    단일 책임 원칙(SRP)을 준수합니다.

    의존성 역전 원칙(DIP)을 적용하여 TUI App 전체가 아닌
    필요한 Manager들과 메서드만 참조합니다.
    """

    def __init__(
        self,
        session_manager: 'SessionManager',
        query_one_func: Callable[..., Any],
        write_log_func: Callable[..., None],
        action_show_help_func: Callable[[], Any],
        action_toggle_metrics_panel_func: Callable[[], Any],
        action_search_log_func: Callable[[], Any],
        perform_search_func: Callable[[str], Any],
        load_session_func: Callable[[str], Any],
        update_status_bar_func: Callable[[], None],
    ) -> None:
        """
        초기화

        Args:
            session_manager: SessionManager 인스턴스
            query_one_func: query_one 메서드 참조
            write_log_func: write_log 메서드 참조
            action_show_help_func: action_show_help 메서드 참조
            action_toggle_metrics_panel_func: action_toggle_metrics_panel 메서드 참조
            action_search_log_func: action_search_log 메서드 참조
            perform_search_func: perform_search 메서드 참조
            load_session_func: load_session 메서드 참조
            update_status_bar_func: _update_status_bar 메서드 참조
        """
        self.session_manager = session_manager

        # 메서드 참조 (callable)
        self.query_one = query_one_func
        self.write_log = write_log_func
        self.action_show_help = action_show_help_func
        self.action_toggle_metrics_panel = action_toggle_metrics_panel_func
        self.action_search_log = action_search_log_func
        self.perform_search = perform_search_func
        self.load_session = load_session_func
        self.update_status_bar = update_status_bar_func

        # 상태 관리용 속성
        self.log_lines: List[str] = []

    def sync_state_from_tui(self, log_lines: List[str]) -> None:
        """
        TUI App의 상태를 SlashCommandHandler로 동기화

        Args:
            log_lines: 로그 라인 리스트
        """
        self.log_lines = log_lines

    async def handle_slash_command(self, command: str) -> None:
        """
        슬래시 명령 처리 (Command Pattern 적용)

        Args:
            command: 슬래시 명령 문자열 (예: "/help", "/search keyword")

        Returns:
            None

        Raises:
            Exception: 명령 처리 실패 시

        Example:
            >>> await handler.handle_slash_command("/help")
            >>> await handler.handle_slash_command("/search error")
        """
        task_input = self.query_one("#task-input")
        task_input.clear()

        cmd, _, args = command.partition(" ")
        cmd = cmd.lower().strip()
        args = args.strip()

        # Command Router (인자 없는 명령)
        handlers = {
            "/help": self._handle_help_command,
            "/metrics": self._handle_metrics_command,
            "/clear": self._handle_clear_command,
        }

        # 인자 필요한 명령
        if cmd == "/search":
            await self._handle_search_command(args)
        elif cmd == "/load":
            await self._handle_load_command(args)
        elif cmd == "/init":
            await self._handle_init_command(args)
        elif cmd in handlers:
            await handlers[cmd]()
        else:
            # 알 수 없는 명령
            available_commands = (
                "사용 가능한 커맨드:\n"
                "  /help - 도움말 표시\n"
                "  /metrics - 메트릭 패널 토글\n"
                "  /search - 로그 검색\n"
                "  /init - 프로젝트 분석 및 context 초기화\n"
                "  /load <session_id> - 이전 세션 불러오기\n"
                "  /clear - 로그 화면 지우기"
            )
            warning_panel = TUIFeedbackWidget.create_panel(
                f"알 수 없는 커맨드: {cmd}", FeedbackType.WARNING,
                details=available_commands
            )
            self.write_log("")
            self.write_log(warning_panel)
            self.write_log("")

    async def _handle_help_command(self) -> None:
        """
        /help 명령 처리: 도움말 메시지 표시

        Args:
            None

        Returns:
            None

        Raises:
            Exception: 도움말 모달 표시 실패 시
        """
        try:
            await self.action_show_help()
        except Exception as e:
            logger.error(f"도움말 표시 실패: {e}")
            self.write_log(TUIFeedbackWidget.create_panel(
                "도움말 표시 실패", FeedbackType.ERROR, details=str(e)
            ))

    async def _handle_metrics_command(self) -> None:
        """
        /metrics 명령 처리: 메트릭 통계 표시

        Args:
            None

        Returns:
            None

        Raises:
            Exception: 메트릭 패널 토글 실패 시
        """
        try:
            await self.action_toggle_metrics_panel()
        except Exception as e:
            logger.error(f"메트릭 패널 토글 실패: {e}")
            self.write_log(TUIFeedbackWidget.create_panel(
                "메트릭 패널 토글 실패", FeedbackType.ERROR, details=str(e)
            ))

    async def _handle_search_command(self, keyword: str) -> None:
        """
        /search 명령 처리: 세션 검색 및 결과 표시

        Args:
            keyword: 검색 키워드 (빈 문자열 가능)

        Returns:
            None

        Raises:
            Exception: 검색 모달 표시 실패 시

        Example:
            >>> await self._handle_search_command("error")
        """
        try:
            if not keyword.strip():
                # 키워드가 없으면 검색 모달 표시
                await self.action_search_log()
            else:
                # 키워드가 있으면 즉시 검색 수행
                await self.perform_search(keyword)
        except Exception as e:
            logger.error(f"검색 실패: {e}")
            self.write_log(TUIFeedbackWidget.create_panel(
                "검색 실패", FeedbackType.ERROR, details=str(e)
            ))

    async def _handle_clear_command(self) -> None:
        """
        /clear 명령 처리: 화면 지우기

        Args:
            None

        Returns:
            None

        Raises:
            Exception: 로그 화면 지우기 실패 시
        """
        try:
            output_log = self.query_one("#output-log", RichLog)
            output_log.clear()
            self.log_lines.clear()

            success_panel = TUIFeedbackWidget.create_panel(
                "로그 화면이 지워졌습니다", FeedbackType.SUCCESS
            )
            self.write_log("")
            self.write_log(success_panel)
            self.write_log("")
        except Exception as e:
            logger.error(f"로그 화면 지우기 실패: {e}")

    async def _handle_load_command(self, session_id: str) -> None:
        """
        /load 명령 처리: 세션 로드

        Args:
            session_id: 로드할 세션 ID (빈 문자열 가능)

        Returns:
            None

        Raises:
            Exception: 세션 로드 실패 시

        Example:
            >>> await self._handle_load_command("abc123")
        """
        try:
            if not session_id.strip():
                warning_panel = TUIFeedbackWidget.create_panel(
                    "사용법: /load <session_id>", FeedbackType.WARNING
                )
                self.write_log("")
                self.write_log(warning_panel)
                self.write_log("")
            else:
                await self.load_session(session_id)
        except Exception as e:
            logger.error(f"세션 로드 실패: {e}")
            self.write_log(TUIFeedbackWidget.create_panel(
                "세션 로드 실패", FeedbackType.ERROR, details=str(e)
            ))

    async def _handle_init_command(self, args: str) -> None:
        """
        /init 명령 처리: 프로젝트 초기화 및 컨텍스트 생성

        Args:
            args: 명령줄 인자 (현재 미사용, 향후 확장 가능)

        Returns:
            None

        Raises:
            Exception: 프로젝트 초기화 실패 시

        Example:
            >>> await self._handle_init_command("")
        """
        status_info = self.query_one("#status-info", Static)

        try:
            # 인자 파싱 (현재는 사용하지 않음)
            parsed_args = self._parse_init_args(args)

            self.write_log("")
            self.write_log(Panel(
                "[bold cyan]🔍 프로젝트 분석 시작...[/bold cyan]",
                border_style="cyan"
            ))
            self.write_log("")

            status_info.update("Analyzing...")

            project_root = get_project_root()
            self.write_log("[dim]프로젝트 루트:[/dim] " + str(project_root))
            self.write_log("[dim]파일 스캔 중...[/dim]")

            analyzer = ProjectContextAnalyzer(project_root)
            context = analyzer.analyze()

            self.write_log("")
            self.write_log("[bold green]✅ 분석 완료[/bold green]")
            self.write_log("")

            # 분석 결과 테이블 렌더링
            result_table = self._render_project_analysis_table(context)
            self.write_log(Panel(
                result_table,
                title="[bold cyan]분석 결과[/bold cyan]",
                border_style="cyan"
            ))
            self.write_log("")

            self.write_log("[dim]컨텍스트 저장 중...[/dim]")

            # 컨텍스트 저장
            context_file = self._save_project_context(context)

            self.write_log(f"[green]✅ 저장 완료:[/green] {context_file.name}")
            self.write_log("")

            self.write_log("[dim]새 세션 시작...[/dim]")
            new_session_id = generate_session_id()

            # Phase 1 - Step 1.1: SessionManager의 캡슐화된 메서드 사용
            from src.presentation.tui.managers.session_manager import SessionConfig

            # 현재 활성 인덱스의 세션을 새 세션으로 교체
            active_index = self.session_manager.get_active_session_index()

            # 기존 세션 삭제
            old_session = self.session_manager.get_session_by_index(active_index)
            self.session_manager.delete_session(old_session.session_id)

            # 새 세션 생성
            new_session_data = self.session_manager.create_session_at_index(
                active_index,
                new_session_id,
                f"Project initialization: {context.project_name}"
            )

            # 세션 전환
            self.session_manager.switch_to_session(active_index)

            # 현재 세션 정보 가져오기
            current_session = self.session_manager.get_session_by_index(active_index)

            update_session_id(current_session.session_id)
            set_metrics_collector(current_session.metrics_collector, current_session.session_id)

            self.update_status_bar()

            self.write_log("")
            self.write_log(Panel(
                f"[bold green]✅ 초기화 완료[/bold green]\n\n"
                f"Session ID: {current_session.session_id}\n"
                f"Context: {context.project_name} ({context.architecture})",
                border_style="green"
            ))
            self.write_log("")

            status_info.update("Ready")

        except Exception as e:
            import traceback
            error_panel = TUIFeedbackWidget.create_panel(
                "프로젝트 초기화 실패", FeedbackType.ERROR,
                details=f"{str(e)}\n\n{traceback.format_exc()}"
            )
            self.write_log("")
            self.write_log(error_panel)
            self.write_log("")
            status_info.update("Error")

    def _parse_init_args(self, args: str) -> Dict[str, str]:
        """
        /init 명령 인자 파싱 (--path, --name, --description 등).

        Args:
            args: 명령줄 인자 문자열

        Returns:
            파싱된 인자 딕셔너리

        Raises:
            ValueError: 인자 파싱 실패 시

        Example:
            >>> self._parse_init_args("--path /tmp --name myproject")
            {'path': '/tmp', 'name': 'myproject'}
        """
        parsed_args: Dict[str, str] = {}
        if not args:
            return parsed_args

        # 간단한 인자 파싱 (향후 argparse로 확장 가능)
        parts = args.split()
        i = 0
        while i < len(parts):
            if parts[i].startswith("--"):
                key = parts[i][2:]
                if i + 1 < len(parts) and not parts[i + 1].startswith("--"):
                    parsed_args[key] = parts[i + 1]
                    i += 2
                else:
                    parsed_args[key] = "true"
                    i += 1
            else:
                i += 1

        return parsed_args

    def _render_project_analysis_table(self, context: Any) -> Table:
        """
        프로젝트 분석 결과를 Rich Table로 렌더링.

        Args:
            context: 프로젝트 컨텍스트 분석 결과

        Returns:
            Rich Table 객체

        Raises:
            AttributeError: context 객체에 필수 속성이 없을 시

        Example:
            >>> table = self._render_project_analysis_table(context)
            >>> self.write_log(table)
        """
        result_table = Table(
            show_header=False,
            border_style="cyan",
            box=None,
            padding=(0, 2)
        )
        result_table.add_column("항목", style="dim")
        result_table.add_column("값", style="white")
        result_table.add_row("프로젝트", context.project_name)
        result_table.add_row("언어", context.language)
        result_table.add_row("프레임워크", context.framework)
        result_table.add_row("아키텍처", context.architecture)
        result_table.add_row("의존성", f"{len(context.dependencies)}개 패키지")

        return result_table

    def _save_project_context(self, context: Any) -> Path:
        """
        프로젝트 컨텍스트를 파일 시스템에 저장.

        Args:
            context: 프로젝트 컨텍스트 분석 결과

        Returns:
            저장된 파일 경로

        Raises:
            IOError: 파일 저장 실패 시
            PermissionError: 파일 쓰기 권한 없을 시

        Example:
            >>> path = self._save_project_context(context)
            >>> print(f"Saved to {path}")
        """
        project_root = get_project_root()
        context_file = project_root / ".context.json"
        repo = JsonContextRepository(context_file)
        repo.save(context)

        return context_file
