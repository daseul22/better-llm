#!/usr/bin/env python3
"""
그룹 챗 오케스트레이션 시스템

매니저 에이전트와 워커 에이전트 모두 Claude Agent SDK를 사용합니다.
- 매니저: 사용자와 대화, 작업 계획
- 워커: 실제 작업 수행 (파일 읽기/쓰기, 코드 실행)

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
from src.worker_agent import WorkerAgent
from src.conversation import ConversationHistory
from src.chat_manager import ChatManager
from src.utils import (
    setup_logging,
    load_agent_config,
    generate_session_id,
    save_session_history,
    print_header,
    print_footer,
    get_agent_emoji,
    validate_environment
)


class Orchestrator:
    """
    그룹 챗 오케스트레이션 - 매니저/워커 분리 아키텍처

    매니저가 사용자와 대화하고 작업을 계획하며,
    워커들이 실제 작업(파일 읽기/쓰기, 코드 실행)을 수행합니다.
    """

    def __init__(self, config_path: Path, verbose: bool = False):
        """
        Args:
            config_path: 워커 에이전트 설정 파일 경로
            verbose: 상세 로깅 활성화 여부
        """
        setup_logging(verbose)
        validate_environment()

        # 매니저 에이전트 초기화 (Claude Agent SDK)
        self.manager = ManagerAgent()

        # 워커 에이전트 설정 로드
        worker_configs = load_agent_config(config_path)

        # 워커 에이전트 초기화 (Claude Agent SDK)
        # CLAUDE_CODE_OAUTH_TOKEN 환경 변수 사용
        self.workers: Dict[str, WorkerAgent] = {}
        for config in worker_configs:
            worker = WorkerAgent(config)
            self.workers[config.name] = worker

        # 챗 매니저
        self.chat_manager = ChatManager(
            {name: worker for name, worker in self.workers.items()}
        )

        # 대화 히스토리
        self.history = ConversationHistory()

        # 세션 정보
        self.session_id = generate_session_id()
        self.start_time = time.time()

    async def run(self, user_request: str) -> SessionResult:
        """
        작업 실행

        Args:
            user_request: 사용자 요청

        Returns:
            작업 결과
        """
        # 헤더 출력
        print_header(f"Group Chat Orchestration v2.0 - Session {self.session_id}")
        print(f"📝 작업: {user_request}")
        print(f"👔 매니저: ManagerAgent (Claude Agent SDK)")
        print(f"👷 워커: {', '.join(self.workers.keys())} (Claude Agent SDK)")
        print()

        # 사용자 요청을 히스토리에 추가
        self.history.add_message("user", user_request)

        turn = 0
        max_turns = 20  # 매니저-워커 루프 최대 반복

        try:
            while turn < max_turns:
                turn += 1

                # 1. 매니저가 작업 분석 및 계획
                print(f"\n[Turn {turn}] 👔 ManagerAgent:")
                print("─" * 60)

                manager_response = await self.manager.analyze_and_plan(
                    self.history.get_history()
                )
                print(manager_response)
                print()

                # 매니저 응답을 히스토리에 추가
                self.history.add_message("manager", manager_response)

                # 2. 종료 조건 확인
                if "TERMINATE" in manager_response.upper() or "작업 완료" in manager_response:
                    print("\n✅ 매니저가 작업 완료를 보고했습니다.")
                    break

                # 3. 다음 워커 선택 (@agent_name 추출)
                next_worker = self._extract_worker_assignment(manager_response)

                if not next_worker:
                    # 매니저가 워커를 지정하지 않으면 사용자 개입 대기
                    user_input = input("💬 추가 지시사항 (Enter: 계속): ").strip()
                    if user_input:
                        self.history.add_message("user", user_input)
                    continue

                if next_worker not in self.workers:
                    print(f"⚠️  알 수 없는 워커: {next_worker}")
                    continue

                # 4. 워커 실행 (Claude Agent SDK)
                worker = self.workers[next_worker]
                emoji = get_agent_emoji(next_worker)

                print(f"[Turn {turn}] {emoji} {worker.config.role} ({next_worker}) - Claude Agent SDK:")
                print("─" * 60)

                # 워커에게 전달할 작업 추출
                task_description = self._extract_task_for_worker(manager_response, next_worker)

                try:
                    # Claude Agent SDK로 작업 실행 (비동기)
                    worker_response = ""
                    async for chunk in worker.execute_task(task_description):
                        print(chunk, end="", flush=True)
                        worker_response += chunk
                    print()

                    # 워커 응답을 히스토리에 추가
                    self.history.add_message("agent", worker_response, next_worker)

                except Exception as e:
                    error_msg = f"❌ 워커 실행 실패: {e}"
                    print(error_msg)
                    self.history.add_message("agent", error_msg, next_worker)

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
                sum(1 for msg in self.history.get_history() if msg.role in ["agent", "manager"]),
                duration,
                0,
                filepath
            )

    def _extract_worker_assignment(self, manager_response: str) -> Optional[str]:
        """
        매니저 응답에서 @worker_name 추출

        Args:
            manager_response: 매니저 응답

        Returns:
            워커 이름 또는 None
        """
        import re

        # @planner, @coder, @tester 패턴 찾기
        pattern = r'@(\w+)'
        matches = re.findall(pattern, manager_response.lower())

        if matches:
            for match in matches:
                if match in self.workers:
                    return match

        return None

    def _extract_task_for_worker(self, manager_response: str, worker_name: str) -> str:
        """
        매니저 응답에서 워커에게 전달할 작업 추출

        Args:
            manager_response: 매니저 응답
            worker_name: 워커 이름

        Returns:
            작업 설명
        """
        # @worker_name 이후의 텍스트를 작업으로 간주
        import re

        pattern = rf'@{worker_name}\s+(.+?)(?=@\w+|$)'
        match = re.search(pattern, manager_response, re.DOTALL | re.IGNORECASE)

        if match:
            task = match.group(1).strip()
            return task

        # 매칭 실패 시 전체 응답 반환
        return manager_response


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
    그룹 챗 오케스트레이션 시스템 v2.0

    매니저 에이전트가 사용자와 대화하고 작업을 계획하며,
    워커 에이전트들이 Claude Agent SDK로 실제 작업을 수행합니다.

    \b
    예시:
        python orchestrator_v2.py "FastAPI로 /users CRUD 엔드포인트 구현해줘"
        python orchestrator_v2.py --verbose "로그인 API 버그 수정해줘"
    """
    try:
        orchestrator = OrchestratorV2(Path(config), verbose)
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
