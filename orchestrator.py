#!/usr/bin/env python3
"""
그룹 챗 오케스트레이션 시스템

여러 Claude 에이전트가 협업하여 복잡한 소프트웨어 개발 작업을 자동화합니다.

Usage:
    python orchestrator.py "작업 설명"
    python orchestrator.py --config custom_agents.json "작업 설명"
    python orchestrator.py --verbose "작업 설명"
"""

import sys
import time
import select
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict

import click
from anthropic import Anthropic

from src.models import AgentConfig, SessionResult
from src.agents import Agent
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
    그룹 챗 오케스트레이션 메인 클래스

    에이전트들을 초기화하고 대화 루프를 관리합니다.
    """

    def __init__(self, config_path: Path, verbose: bool = False):
        """
        Args:
            config_path: 에이전트 설정 파일 경로
            verbose: 상세 로깅 활성화 여부
        """
        setup_logging(verbose)
        validate_environment()

        # 설정 로드
        self.agent_configs = load_agent_config(config_path)

        # Anthropic 클라이언트 초기화
        self.client = Anthropic()

        # 에이전트 초기화
        self.agents: Dict[str, Agent] = {}
        for config in self.agent_configs:
            agent = Agent(config, self.client)
            self.agents[config.name] = agent

        # 챗 매니저 초기화
        self.chat_manager = ChatManager(self.agents)

        # 대화 히스토리
        self.history = ConversationHistory()

        # 세션 정보
        self.session_id = generate_session_id()
        self.start_time = time.time()

    def run(self, user_request: str) -> SessionResult:
        """
        작업 실행

        Args:
            user_request: 사용자 요청

        Returns:
            작업 결과
        """
        # 헤더 출력
        print_header(f"Group Chat Orchestration - Session {self.session_id}")
        print(f"📝 작업: {user_request}")
        print(f"🤖 활성 에이전트: {', '.join(self.agents.keys())}")
        print()

        # 사용자 요청을 히스토리에 추가
        self.history.add_message("user", user_request)

        turn = 0
        max_turns = self.chat_manager.max_turns

        try:
            while turn < max_turns:
                turn += 1

                # 다음 에이전트 선택
                next_agent = self.chat_manager.select_next_agent(self.history.get_history())

                # 종료 조건 확인
                if next_agent == "TERMINATE":
                    print("\n✅ 작업이 정상적으로 완료되었습니다.")
                    break

                if next_agent == "USER_INPUT":
                    # 사용자 입력 대기
                    user_input = self._get_user_input()
                    if user_input:
                        self.history.add_message("user", user_input)
                        continue

                # 에이전트 실행
                if next_agent not in self.agents:
                    print(f"⚠️  알 수 없는 에이전트: {next_agent}")
                    break

                agent = self.agents[next_agent]
                emoji = get_agent_emoji(next_agent)

                print(f"\n[Turn {turn}] {emoji} {agent.config.role} ({next_agent}):")
                print("─" * 60)

                # 에이전트 응답 생성
                try:
                    response = agent.respond(self.history.get_history())
                    print(response)
                    print()

                    # 히스토리에 추가
                    self.history.add_message("agent", response, agent.config.name)

                except Exception as e:
                    print(f"❌ 에러 발생: {e}")
                    return SessionResult(
                        status="error",
                        error_message=str(e)
                    )

                # 사용자 개입 대기 (5초)
                user_input = self._prompt_user_intervention()
                if user_input:
                    # 명령어 처리
                    if user_input.startswith("/"):
                        command = self._handle_command(user_input)
                        if command == "STOP":
                            print("\n🛑 사용자가 작업을 중단했습니다.")
                            return SessionResult(status="terminated")
                        elif command == "PAUSE":
                            # 일시정지 모드
                            paused_input = input("💬 메시지를 입력하세요 (또는 Enter로 계속): ")
                            if paused_input:
                                self.history.add_message("user", paused_input)
                    else:
                        # 일반 메시지
                        self.history.add_message("user", user_input)

            # 최대 턴 수 도달
            if turn >= max_turns:
                print(f"\n⚠️  최대 턴 수({max_turns})에 도달했습니다.")
                return SessionResult(status="max_turns_reached")

            # 정상 완료
            return SessionResult(
                status="completed",
                files_modified=[],  # TODO: 실제 수정된 파일 추적
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
                sum(1 for msg in self.history.get_history() if msg.role == "agent"),
                duration,
                0,  # TODO: 실제 파일 개수
                filepath
            )

    def _prompt_user_intervention(self, timeout: int = 5) -> Optional[str]:
        """
        사용자 개입 대기 (timeout 포함)

        Args:
            timeout: 대기 시간 (초)

        Returns:
            사용자 입력 또는 None
        """
        print(f"⏸  [Enter: 계속 | /pause: 일시정지 | /stop: 종료] ({timeout}초 대기)", end="", flush=True)

        # Unix 계열 시스템에서만 동작
        if sys.platform != "win32":
            ready, _, _ = select.select([sys.stdin], [], [], timeout)
            if ready:
                user_input = sys.stdin.readline().strip()
                return user_input if user_input else None
            else:
                print()  # 새 줄
                return None
        else:
            # Windows에서는 timeout 없이 대기
            print(" (Enter를 눌러 계속)")
            user_input = input().strip()
            return user_input if user_input else None

    def _get_user_input(self) -> Optional[str]:
        """일반 사용자 입력 받기"""
        user_input = input("💬 입력: ").strip()
        return user_input if user_input else None

    def _handle_command(self, command: str) -> Optional[str]:
        """
        사용자 명령어 처리

        Args:
            command: 명령어 문자열

        Returns:
            처리 결과 ("STOP", "PAUSE", None)
        """
        if command == "/stop":
            return "STOP"
        elif command == "/pause":
            return "PAUSE"
        else:
            print(f"⚠️  알 수 없는 명령어: {command}")
            return None


@click.command()
@click.argument("request", type=str)
@click.option(
    "--config",
    default="config/agent_config.json",
    type=click.Path(exists=True),
    help="에이전트 설정 파일 경로"
)
@click.option(
    "--verbose",
    is_flag=True,
    help="상세 로깅 활성화"
)
def main(request: str, config: str, verbose: bool):
    """
    그룹 챗 오케스트레이션 시스템

    여러 Claude 에이전트가 협업하여 복잡한 소프트웨어 개발 작업을 자동화합니다.

    \b
    예시:
        python orchestrator.py "FastAPI로 /users CRUD 엔드포인트 구현해줘"
        python orchestrator.py --verbose "로그인 API 버그 수정해줘"
        python orchestrator.py --config custom.json "작업 설명"
    """
    try:
        orchestrator = Orchestrator(Path(config), verbose)
        orchestrator.run(request)
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
