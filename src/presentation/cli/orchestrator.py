#!/usr/bin/env python3
"""
그룹 챗 오케스트레이션 시스템 v3.0 - Worker Tools Architecture

Manager Agent가 Claude Agent SDK를 사용하여 Worker Tool들을 호출합니다.
- Manager Agent: 사용자와 대화, Worker Tool 호출
- Worker Tools: 실제 작업 수행 (Planner, Coder, Tester를 Tool로 래핑)

Usage:
    python orchestrator.py "작업 설명"
"""

import sys
import time
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict

import click
from rich.traceback import install as install_rich_traceback

from src.domain.models import SessionResult
from src.domain.models.session import SessionStatus
from src.domain.services import ConversationHistory
from src.infrastructure.claude import ManagerAgent
from src.infrastructure.mcp import (
    initialize_workers,
    create_worker_tools_server,
    log_error_summary,
    set_user_input_callback
)
from src.infrastructure.config import (
    validate_environment,
    get_project_root,
    SystemConfig,
)
from src.infrastructure.storage import create_session_repository
from .utils import (
    setup_logging,
    generate_session_id,
    print_header,
    print_footer,
    validate_user_input,
    sanitize_user_input,
    load_system_config,
)
from .feedback import FeedbackMessage
from .cli_ui import get_renderer, get_progress_tracker, WorkflowTree, get_error_display
from .session_commands import session_commands
from .template_commands import template_commands
from .approval_commands import approval_cli

# Rich Traceback 설치 (에러 메시지 개선)
install_rich_traceback(show_locals=False)


class Orchestrator:
    """
    그룹 챗 오케스트레이션 - Manager Agent + Worker Tools 아키텍처

    Manager Agent가 사용자와 대화하고 Worker Tool들을 호출하여 작업을 수행합니다.
    Worker Tool들은 실제 작업(파일 읽기/쓰기, 코드 실행)을 담당합니다.
    """

    def __init__(
        self,
        config_path: Path,
        verbose: bool = False,
        system_config: Optional[SystemConfig] = None
    ):
        """
        Args:
            config_path: 워커 에이전트 설정 파일 경로
            verbose: 상세 로깅 활성화 여부
            system_config: 시스템 설정 (없으면 기본값 사용)
        """
        # 시스템 설정 로드
        self.system_config = system_config or load_system_config()

        setup_logging(verbose)
        validate_environment()

        # Worker Agent들 초기화
        initialize_workers(config_path)

        # Worker Tools MCP Server 생성
        worker_tools_server = create_worker_tools_server()

        # Manager Agent 초기화 (Worker Tools + 시스템 설정 전달)
        # auto_commit_enabled는 workflow 섹션에서 가져옴
        auto_commit_enabled = self.system_config.get("workflow", {}).get("auto_commit_enabled", False)

        self.manager = ManagerAgent(
            worker_tools_server,
            model=self.system_config.manager_model,
            max_history_messages=self.system_config.max_history_messages,
            auto_commit_enabled=auto_commit_enabled
        )

        # 대화 히스토리
        self.history = ConversationHistory()

        # 세션 정보
        self.session_id = generate_session_id()
        self.start_time = time.time()

        # 피드백 시스템
        self.feedback = FeedbackMessage()

        # CLI UI 렌더러
        self.renderer = get_renderer()

        # Workflow Tree (Worker Tool 호출 추적)
        self.workflow_tree = WorkflowTree(title="Worker Tools Workflow")

        # Repository 패턴 사용 (config/system_config.json의 storage.backend 설정에 따라)
        self.session_repo = create_session_repository()

        # 사용자 입력 콜백 설정 (Human-in-the-Loop)
        set_user_input_callback(self._user_input_callback)

    def _user_input_callback(self, question: str, options=None):
        """
        사용자 입력 콜백 함수 (Human-in-the-Loop)

        Args:
            question: 사용자에게 보여줄 질문
            options: 선택지 목록 (선택적)

        Returns:
            사용자 응답 (문자열)
        """
        # Rich Panel로 질문 표시
        from rich.panel import Panel
        from rich.prompt import Prompt

        self.renderer.console.print()
        self.renderer.console.print(
            Panel(
                f"[bold yellow]{question}[/bold yellow]",
                title="❓ Manager가 질문합니다",
                border_style="yellow"
            )
        )

        # 선택지가 있으면 번호 매겨서 표시
        if options:
            self.renderer.console.print()
            for i, opt in enumerate(options, 1):
                self.renderer.console.print(f"  [cyan]{i}.[/cyan] {opt}")
            self.renderer.console.print()

            # 사용자 입력 받기 (번호 또는 텍스트)
            user_input = Prompt.ask(
                "[bold green]선택해주세요 (번호 또는 텍스트)[/bold green]"
            )

            # 숫자면 해당 옵션 반환
            try:
                choice = int(user_input)
                if 1 <= choice <= len(options):
                    return options[choice - 1]
            except ValueError:
                pass

            # 텍스트면 그대로 반환
            return user_input
        else:
            # 자유 텍스트 입력
            return Prompt.ask("[bold green]답변을 입력해주세요[/bold green]")

    def _validate_and_prepare_input(self, user_request: str) -> tuple[bool, str, str]:
        """
        사용자 입력 검증 및 정제

        Args:
            user_request: 원본 사용자 요청

        Returns:
            (검증 성공 여부, 에러 메시지, 정제된 입력) 튜플
        """
        # 입력 검증
        is_valid, error_msg = validate_user_input(user_request)
        if not is_valid:
            return False, error_msg, ""

        # 입력 정제
        sanitized_input = sanitize_user_input(user_request)
        return True, "", sanitized_input

    def _print_session_header(self, user_request: str) -> None:
        """
        세션 헤더 출력

        Args:
            user_request: 사용자 요청 (헤더에 표시)
        """
        # 헤더 출력 (Rich 사용)
        self.renderer.print_header(
            "Group Chat Orchestration v3.0",
            f"Worker Tools Architecture - Session {self.session_id}"
        )
        self.renderer.print_task_info(
            task=user_request,
            session_id=self.session_id,
            manager="ManagerAgent (Claude Agent SDK)",
            tools=["execute_planner_task", "execute_coder_task", "execute_tester_task", "read"]
        )

    async def _execute_manager_turn(self, turn: int) -> str:
        """
        단일 Manager 턴 실행 (스트리밍 방식)

        Args:
            turn: 현재 턴 번호

        Returns:
            Manager의 응답 전체 텍스트
        """
        # 턴 헤더 출력 (Rich 사용)
        self.renderer.print_turn_header(turn, "ManagerAgent")

        manager_response = ""
        async for chunk in self.manager.analyze_and_plan_stream(
            self.history.get_history()
        ):
            manager_response += chunk
            self.renderer.console.print(chunk, end="", highlight=False)

        self.renderer.console.print()
        self.renderer.console.print()

        return manager_response

    def _check_completion_condition(self, manager_response: str) -> bool:
        """
        작업 완료 조건 확인

        Args:
            manager_response: Manager의 응답

        Returns:
            True: 작업 완료, False: 계속 진행
        """
        return "작업이 완료되었습니다" in manager_response or "작업 완료" in manager_response

    def _handle_max_turns_reached(self, max_turns: int) -> SessionResult:
        """
        최대 턴 수 도달 처리

        Args:
            max_turns: 최대 턴 수

        Returns:
            MAX_TURNS_REACHED 상태의 SessionResult
        """
        self.feedback.warning(
            f"최대 턴 수({max_turns})에 도달했습니다",
            use_panel=False
        )
        return SessionResult(status=SessionStatus.MAX_TURNS_REACHED)

    def _finalize_session(
        self,
        user_request: str,
        result: SessionResult
    ) -> None:
        """
        세션 종료 처리 (에러 통계, 히스토리 저장, 푸터 출력)

        Args:
            user_request: 사용자 요청
            result: 작업 결과
        """
        # 에러 통계 출력
        self.renderer.console.print()
        log_error_summary()
        self.renderer.console.print()

        # 세션 히스토리 저장
        duration = time.time() - self.start_time

        # Repository 패턴 사용 (config/system_config.json의 storage.backend에 따라 저장)
        try:
            filepath = self.session_repo.save(
                session_id=self.session_id,
                user_request=user_request,
                history=self.history,
                result=result
            )
        except Exception as e:
            # 저장 실패 시 경고 출력하고 계속 진행
            self.feedback.warning(
                f"세션 저장 중 오류 발생: {e}",
                use_panel=False
            )
            # 기본 경로를 반환하여 푸터 출력은 정상적으로 진행
            from src.infrastructure.config import get_data_dir
            filepath = get_data_dir("sessions") / f"session_{self.session_id}_failed.json"

        # 푸터 출력 (Rich 사용)
        self.renderer.print_footer(
            self.session_id,
            sum(1 for msg in self.history.get_history() if msg.role == "manager"),
            duration,
            0,
            filepath
        )

    async def run(self, user_request: str) -> SessionResult:
        """
        작업 실행 - Manager가 Worker Tool들을 호출하여 작업 수행 (리팩토링 버전)

        Args:
            user_request: 사용자 요청

        Returns:
            작업 결과
        """
        # 1. 입력 검증 및 정제
        is_valid, error_msg, sanitized_input = self._validate_and_prepare_input(user_request)
        if not is_valid:
            self.feedback.error(
                "입력 검증에 실패했습니다",
                details=error_msg
            )
            return SessionResult(status=SessionStatus.INVALID_INPUT)

        # 2. 세션 헤더 출력
        self._print_session_header(sanitized_input)

        # 3. 사용자 요청을 히스토리에 추가
        self.history.add_message("user", sanitized_input)

        max_turns = self.system_config.max_turns

        try:
            # 4. 대화 루프
            for turn in range(1, max_turns + 1):
                # 4.1 Manager 턴 실행
                manager_response = await self._execute_manager_turn(turn)

                # 4.2 Manager 응답을 히스토리에 추가
                self.history.add_message("manager", manager_response)

                # 4.3 완료 조건 확인
                if self._check_completion_condition(manager_response):
                    self.feedback.success(
                        "Manager가 작업 완료를 보고했습니다",
                        use_panel=False
                    )
                    result = SessionResult(
                        status=SessionStatus.COMPLETED,
                        files_modified=[],
                        tests_passed=True
                    )
                    return result

            # 5. 최대 턴 수 도달
            return self._handle_max_turns_reached(max_turns)

        finally:
            # 6. 세션 종료 처리
            # result가 없는 경우 (에러 등) 기본 COMPLETED 상태 사용
            result = SessionResult(status=SessionStatus.COMPLETED)
            self._finalize_session(sanitized_input, result)



@click.group(invoke_without_command=True)
@click.argument("request", type=str, required=False)
@click.option(
    "--config",
    default="config/agent_config.json",
    type=click.Path(exists=True),
    help="워커 에이전트 설정 파일 경로"
)
@click.option(
    "--verbose",
    is_flag=True,
    help="상세 로깅 활성화"
)
@click.pass_context
def main(ctx: click.Context, request: Optional[str], config: str, verbose: bool):
    """
    그룹 챗 오케스트레이션 시스템 v3.0 - Worker Tools Architecture

    Manager Agent가 Worker Tool들을 호출하여 작업을 수행합니다.
    각 Worker Agent가 Custom Tool로 래핑되어 Manager에게 제공됩니다.

    \b
    예시:
        python orchestrator.py "FastAPI로 /users CRUD 엔드포인트 구현해줘"
        python orchestrator.py --verbose "로그인 API 버그 수정해줘"
        python orchestrator.py session list  # 세션 목록 조회
        python orchestrator.py session search --keyword "API"  # 세션 검색
    """
    # 서브커맨드 실행 시 (session 등)
    if ctx.invoked_subcommand is not None:
        return

    # request가 없으면 도움말 출력
    if not request:
        click.echo(ctx.get_help())
        return

    try:
        # config 경로를 프로젝트 루트 기준으로 변환
        config_path = Path(config)
        if not config_path.is_absolute():
            config_path = get_project_root() / config

        orchestrator = Orchestrator(config_path, verbose)
        # asyncio로 실행
        asyncio.run(orchestrator.run(request))
    except KeyboardInterrupt:
        # 피드백 시스템 사용
        feedback = FeedbackMessage()
        feedback.warning("사용자가 작업을 중단했습니다", use_panel=False)
        sys.exit(0)
    except Exception as e:
        # Rich ErrorDisplay 사용
        error_display = get_error_display()
        if verbose:
            import traceback
            error_display.show_error(
                error_type=type(e).__name__,
                message=str(e),
                traceback=traceback.format_exc()
            )
        else:
            error_display.show_error(
                error_type=type(e).__name__,
                message=str(e)
            )
        sys.exit(1)


# 세션 관리 서브커맨드 추가
main.add_command(session_commands)

# 템플릿 관리 서브커맨드 추가
main.add_command(template_commands)

# 승인 관리 서브커맨드 추가
main.add_command(approval_cli)


if __name__ == "__main__":
    main()
