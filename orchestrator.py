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

from src.models import SessionResult
from src.manager_agent import ManagerAgent
from src.worker_tools import (
    initialize_workers,
    create_worker_tools_server,
    log_error_summary
)
from src.conversation import ConversationHistory
from src.utils import (
    setup_logging,
    generate_session_id,
    save_session_history,
    print_header,
    print_footer,
    validate_environment,
    validate_user_input,
    sanitize_user_input,
    load_system_config,
    SystemConfig
)


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
        self.manager = ManagerAgent(
            worker_tools_server,
            model=self.system_config.manager_model,
            max_history_messages=self.system_config.max_history_messages
        )

        # 대화 히스토리
        self.history = ConversationHistory()

        # 세션 정보
        self.session_id = generate_session_id()
        self.start_time = time.time()

    async def run(self, user_request: str) -> SessionResult:
        """
        작업 실행 - Manager가 Worker Tool들을 호출하여 작업 수행

        Args:
            user_request: 사용자 요청

        Returns:
            작업 결과
        """
        # 입력 검증
        is_valid, error_msg = validate_user_input(user_request)
        if not is_valid:
            print(f"\n❌ 입력 검증 실패: {error_msg}")
            return SessionResult(status="invalid_input")

        # 입력 정제
        user_request = sanitize_user_input(user_request)

        # 헤더 출력
        print_header(f"Group Chat Orchestration v3.0 (Worker Tools) - Session {self.session_id}")
        print(f"📝 작업: {user_request}")
        print(f"👔 매니저: ManagerAgent (Claude Agent SDK + Worker Tools)")
        print(f"🛠️  도구: execute_planner_task, execute_coder_task, execute_tester_task, read")
        print()

        # 사용자 요청을 히스토리에 추가
        self.history.add_message("user", user_request)

        turn = 0
        max_turns = self.system_config.max_turns  # 설정에서 로드

        try:
            while turn < max_turns:
                turn += 1

                # Manager가 Worker Tool들을 호출하여 작업 수행 (스트리밍)
                print(f"\n[Turn {turn}] 👔 ManagerAgent:")
                print("─" * 60)

                manager_response = ""
                async for chunk in self.manager.analyze_and_plan_stream(
                    self.history.get_history()
                ):
                    manager_response += chunk
                    print(chunk, end="", flush=True)

                print()
                print()

                # Manager 응답을 히스토리에 추가
                self.history.add_message("manager", manager_response)

                # 종료 조건 확인
                if "작업이 완료되었습니다" in manager_response or "작업 완료" in manager_response:
                    print("\n✅ Manager가 작업 완료를 보고했습니다.")
                    break

            # 최대 턴 수 도달
            if turn >= max_turns:
                print(f"\n⚠️  최대 턴 수({max_turns})에 도달했습니다.")
                return SessionResult(status="max_turns_reached")

            # 정상 완료
            return SessionResult(
                status="completed",
                files_modified=[],
                tests_passed=True
            )

        finally:
            # 에러 통계 출력
            print()
            log_error_summary()
            print()

            # 세션 히스토리 저장
            duration = time.time() - self.start_time
            result = SessionResult(status="completed")

            sessions_dir = Path("sessions")
            filepath = save_session_history(
                self.session_id,
                user_request,
                self.history,
                result.to_dict(),
                sessions_dir
            )

            print_footer(
                self.session_id,
                sum(1 for msg in self.history.get_history() if msg.role == "manager"),
                duration,
                0,
                filepath
            )



@click.command()
@click.argument("request", type=str)
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
def main(request: str, config: str, verbose: bool):
    """
    그룹 챗 오케스트레이션 시스템 v3.0 - Worker Tools Architecture

    Manager Agent가 Worker Tool들을 호출하여 작업을 수행합니다.
    각 Worker Agent가 Custom Tool로 래핑되어 Manager에게 제공됩니다.

    \b
    예시:
        python orchestrator.py "FastAPI로 /users CRUD 엔드포인트 구현해줘"
        python orchestrator.py --verbose "로그인 API 버그 수정해줘"
    """
    try:
        orchestrator = Orchestrator(Path(config), verbose)
        # asyncio로 실행
        asyncio.run(orchestrator.run(request))
    except KeyboardInterrupt:
        print("\n\n🛑 사용자가 작업을 중단했습니다.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
