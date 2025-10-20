"""
매니저 에이전트 - 사용자와 대화하고 작업을 계획

ManagerAgent: Claude Agent SDK를 사용하여 Worker Tool들을 호출하고 작업 조율
"""

from typing import List, Optional
import logging
import os

from claude_agent_sdk import ClaudeSDKClient
from claude_agent_sdk.types import ClaudeAgentOptions

from ...domain.models import Message
from ..config import get_claude_cli_path
from ..logging import get_logger, log_exception_silently

logger = get_logger(__name__)


class ManagerAgent:
    """
    사용자와 대화하는 매니저 에이전트

    Claude Agent SDK를 사용하여 사용자 요청을 분석하고,
    Worker Tool들을 호출하여 작업을 수행합니다.

    Attributes:
        model: 사용할 Claude 모델
        worker_tools_server: Worker Tools MCP 서버
        auto_commit_enabled: Git 커밋 자동 생성 활성화 여부
    """

    @property
    def SYSTEM_PROMPT(self) -> str:
        """
        시스템 프롬프트 생성 (auto_commit_enabled 설정 반영)

        Returns:
            시스템 프롬프트 문자열
        """
        # 기본 프롬프트
        base_prompt = """당신은 소프트웨어 개발 프로젝트를 관리하는 매니저입니다.

## 역할
- 사용자 요청을 분석하고 이해합니다
- 작업을 계획하고 우선순위를 정합니다
- Worker Agent Tool을 호출하여 작업을 할당합니다
- 진행 상황을 사용자에게 보고합니다

## 사용 가능한 Tool
다음 Tool들을 사용할 수 있습니다:
- **execute_planner_task**: 요구사항 분석 및 계획 수립
- **execute_coder_task**: 코드 작성, 수정, 리팩토링
- **execute_reviewer_task**: 코드 리뷰 및 품질 검증
- **execute_tester_task**: 테스트 작성 및 실행"""

        # auto_commit_enabled에 따라 committer 관련 내용 추가
        if self.auto_commit_enabled:
            base_prompt += """
- **execute_committer_task**: Git 커밋 생성 (테스트 성공 후)"""

        base_prompt += """
- **read**: 파일 읽기 (필요 시)

## 작업 수행 방법
1. 사용자 요청을 분석합니다
2. 필요한 Worker Tool을 순차적으로 호출합니다
3. 각 Tool의 결과를 확인하고 다음 단계를 결정합니다
4. 모든 작업이 완료되면 사용자에게 결과를 보고합니다

## 표준 작업 흐름
1. execute_planner_task → 요구사항 분석 및 계획
2. execute_coder_task → 코드 작성
3. execute_reviewer_task → 코드 리뷰 (품질 검증)
4. execute_tester_task → 테스트 작성 및 실행"""

        if self.auto_commit_enabled:
            base_prompt += """
5. execute_committer_task → Git 커밋 생성 (테스트 성공 시)"""

        base_prompt += """

**중요**:
- Reviewer가 Critical 이슈를 발견하면 Coder에게 수정 요청 후 다시 Review
- **무한 루프 방지**: Review → Coder → Review 사이클은 최대 3회까지만 허용
  - 3회 반복 후에도 Critical 이슈가 남으면 사용자에게 수동 개입 요청
  - 반복 횟수를 명시적으로 추적하세요 (예: "Review 사이클 1/3")"""

        if self.auto_commit_enabled:
            base_prompt += """
- Committer는 Tester가 성공한 경우에만 실행하세요
- Committer 실행 여부는 작업 성격에 따라 판단하세요 (새 기능, 버그 수정 등은 커밋 권장)"""

        base_prompt += """

## 예시
사용자: "FastAPI로 /users CRUD API를 작성해줘"

1단계: execute_planner_task 호출 → 요구사항 분석 및 설계
2단계: execute_coder_task 호출 → 코드 작성
3단계: execute_reviewer_task 호출 → 코드 리뷰
  - Critical 이슈 발견 시 → execute_coder_task로 수정 → 다시 execute_reviewer_task
  - 승인 시 → 다음 단계 진행
4단계: execute_tester_task 호출 → 테스트 작성 및 실행"""

        if self.auto_commit_enabled:
            base_prompt += """
5단계: execute_committer_task 호출 → Git 커밋 (테스트 성공 시)
6단계: 사용자에게 완료 보고"""
        else:
            base_prompt += """
5단계: 사용자에게 완료 보고"""

        base_prompt += """

## 규칙
- Tool을 직접 호출하세요 (@ 표기 불필요)
- 각 Tool 호출 전에 무엇을 할 것인지 설명하세요
- Reviewer의 피드백을 반드시 반영하세요 (Critical 이슈는 필수 수정)
- Tool 결과를 확인하고 문제가 있으면 재시도하세요
- 모든 작업이 완료되면 "작업이 완료되었습니다"라고 명시하세요

## 무한 루프 방지 규칙
- Review → Coder → Review 사이클을 추적하세요
- 최대 반복 횟수: 3회
- 사이클 진행 시마다 "Review 사이클 X/3" 형태로 표시
- 3회 초과 시 다음 메시지를 출력하고 중단:
  "⚠️ Review 사이클이 3회를 초과했습니다. 수동 개입이 필요합니다.
   Critical 이슈: [이슈 요약]
   다음 단계: 사용자가 직접 코드를 수정하거나 요구사항을 조정해주세요."
"""

        return base_prompt

    def __init__(
        self,
        worker_tools_server,
        model: str = "claude-sonnet-4-5-20250929",
        max_history_messages: int = 20,
        auto_commit_enabled: bool = False,
        session_id: Optional[str] = None
    ):
        """
        Args:
            worker_tools_server: Worker Tools MCP 서버
            model: 사용할 Claude 모델
            max_history_messages: 프롬프트에 포함할 최대 히스토리 메시지 수 (슬라이딩 윈도우)
            auto_commit_enabled: Git 커밋 자동 생성 활성화 여부
            session_id: 세션 ID (로깅용, 선택사항)
        """
        self.model = model
        self.worker_tools_server = worker_tools_server
        self.max_history_messages = max_history_messages
        self.auto_commit_enabled = auto_commit_enabled
        self.session_id = session_id or "unknown"

        # 세션 컨텍스트를 포함한 로거 생성
        self.logger = get_logger(__name__, session_id=self.session_id, component="ManagerAgent")

        # Review cycle 추적 변수 (무한 루프 방지)
        self.review_cycle_count = 0

        # 토큰 사용량 추적
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cache_read_tokens = 0
        self.total_cache_creation_tokens = 0

        # system_config.json에서 max_review_iterations 로드
        try:
            from ..config import load_system_config
            config = load_system_config()
            self.max_review_cycles = config.get("workflow_limits", {}).get(
                "max_review_iterations", 3
            )
        except Exception as e:
            self.logger.warning(
                "Failed to load max_review_iterations from config",
                error=str(e),
                default_value=3
            )
            self.max_review_cycles = 3

        self.logger.info(
            "ManagerAgent initialized",
            model=self.model,
            max_history_messages=self.max_history_messages,
            auto_commit_enabled=self.auto_commit_enabled,
            max_review_cycles=self.max_review_cycles
        )

    def _build_prompt_from_history(self, history: List[Message]) -> str:
        """
        대화 히스토리를 프롬프트 텍스트로 변환 (슬라이딩 윈도우 적용)

        Args:
            history: 대화 히스토리

        Returns:
            프롬프트 문자열
        """
        # 시스템 프롬프트로 시작
        prompt_parts = [self.SYSTEM_PROMPT, "\n\n## 대화 히스토리:\n"]

        # 슬라이딩 윈도우: 최근 N개 메시지만 포함
        # 단, 첫 번째 사용자 요청은 항상 포함 (컨텍스트 유지)
        if len(history) > self.max_history_messages:
            # 첫 번째 사용자 메시지 + 최근 메시지들
            first_user_msg = next((msg for msg in history if msg.role == "user"), None)
            recent_messages = history[-(self.max_history_messages - 1):]

            if first_user_msg and first_user_msg not in recent_messages:
                messages_to_include = [first_user_msg] + recent_messages
                prompt_parts.append("\n[참고: 초기 요청과 최근 대화만 표시]\n")
            else:
                messages_to_include = recent_messages
        else:
            messages_to_include = history

        for msg in messages_to_include:
            if msg.role == "user":
                prompt_parts.append(f"\n[사용자]\n{msg.content}\n")
            elif msg.role == "agent":
                # 워커 Tool의 실행 결과
                prompt_parts.append(f"\n[{msg.agent_name} Tool 완료]\n{msg.content}\n")
            elif msg.role == "manager":
                # 매니저 자신의 이전 응답
                prompt_parts.append(f"\n[매니저 (당신)]\n{msg.content}\n")

        prompt_parts.append("\n다음 단계를 수행해주세요:")

        return "".join(prompt_parts)

    async def analyze_and_plan_stream(self, history: List[Message]):
        """
        사용자 요청을 분석하고 작업 수행 (스트리밍)

        Args:
            history: 전체 대화 히스토리

        Yields:
            매니저의 응답 청크 (텍스트만)

        Raises:
            Exception: SDK 호출 실패 시
        """
        client = None
        cleanup_done = False

        try:
            # 대화 히스토리를 프롬프트로 변환
            prompt = self._build_prompt_from_history(history)

            self.logger.debug(
                "Starting Claude Agent SDK call",
                worker_tools_enabled=True,
                working_dir=os.getcwd(),
                history_size=len(history)
            )

            # ClaudeSDKClient를 사용 (query()는 툴을 지원하지 않음)
            # Worker Tools MCP Server를 등록하고, read 툴도 허용
            # Note: working_dir는 ClaudeAgentOptions에서 지원하지 않음 (os.getcwd()가 기본값)

            # allowed_tools 리스트 생성 (auto_commit_enabled에 따라 조건부)
            allowed_tools = [
                "mcp__workers__execute_planner_task",
                "mcp__workers__execute_coder_task",
                "mcp__workers__execute_reviewer_task",
                "mcp__workers__execute_tester_task",
                "read"  # 파일 읽기 툴
            ]

            # auto_commit_enabled가 True일 때만 committer tool 추가
            if self.auto_commit_enabled:
                allowed_tools.append("mcp__workers__execute_committer_task")

            options = ClaudeAgentOptions(
                model=self.model,
                mcp_servers={"workers": self.worker_tools_server},
                allowed_tools=allowed_tools,
                cli_path=get_claude_cli_path(),
                permission_mode="bypassPermissions"
            )

            # 명시적으로 client 생성 및 연결 (async with 대신)
            # Generator 내부에서 async with를 사용하면 cleanup이 다른 태스크에서 실행될 수 있음
            client = ClaudeSDKClient(options=options)
            await client.connect()

            # 프롬프트 전송
            await client.query(prompt)

            # 응답 수신 (스트리밍)
            async for msg in client.receive_response():
                # usage 정보 추출 (있는 경우)
                if hasattr(msg, 'usage') and msg.usage:
                    usage = msg.usage
                    # 토큰 사용량 업데이트
                    if hasattr(usage, 'input_tokens'):
                        self.total_input_tokens += usage.input_tokens
                    if hasattr(usage, 'output_tokens'):
                        self.total_output_tokens += usage.output_tokens
                    if hasattr(usage, 'cache_read_tokens'):
                        self.total_cache_read_tokens += usage.cache_read_tokens
                    if hasattr(usage, 'cache_creation_tokens'):
                        self.total_cache_creation_tokens += usage.cache_creation_tokens

                    self.logger.debug(
                        "Token usage updated",
                        input_tokens=self.total_input_tokens,
                        output_tokens=self.total_output_tokens,
                        cache_read_tokens=self.total_cache_read_tokens,
                        cache_creation_tokens=self.total_cache_creation_tokens
                    )

                # 텍스트 콘텐츠만 추출 (JSON 형태는 제외)
                if hasattr(msg, 'content') and isinstance(msg.content, list):
                    for content in msg.content:
                        if hasattr(content, 'text') and content.text:
                            yield content.text
                elif hasattr(msg, 'text') and isinstance(msg.text, str):
                    yield msg.text

            self.logger.debug("Claude Agent SDK call completed")

        except GeneratorExit:
            # Generator가 중간에 종료될 때는 cleanup 하지 않음
            # (다른 태스크에서 실행되어 cancel scope 에러 발생)
            self.logger.debug("Generator exit - cleanup skipped")
            raise

        except Exception as e:
            # 런타임 에러를 조용히 로그에 기록 (프로그램 종료하지 않음)
            log_exception_silently(
                self.logger,
                e,
                "Manager Agent SDK call failed",
                session_id=self.session_id,
                model=self.model
            )
            # 예외를 재발생시키지 않고 빈 응답 반환
            yield f"\n[시스템 오류] Manager Agent 실행 중 오류가 발생했습니다. 에러 로그를 확인해주세요."

        finally:
            # 리소스 정리 (try-finally 보장)
            # GeneratorExit 제외한 모든 경로에서 cleanup 시도
            if client is not None and not cleanup_done:
                try:
                    await client.disconnect()
                    cleanup_done = True
                    self.logger.debug("Client connection closed successfully")
                except Exception as e:
                    self.logger.debug("Client disconnect failed (ignored)", error=str(e))

    def get_token_usage(self) -> dict:
        """
        현재까지의 토큰 사용량 반환

        Returns:
            dict: {
                "input_tokens": int,
                "output_tokens": int,
                "cache_read_tokens": int,
                "cache_creation_tokens": int,
                "total_tokens": int
            }
        """
        return {
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "cache_read_tokens": self.total_cache_read_tokens,
            "cache_creation_tokens": self.total_cache_creation_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens
        }

    def reset_token_usage(self) -> None:
        """토큰 사용량 초기화 (새 세션 시작 시)"""
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cache_read_tokens = 0
        self.total_cache_creation_tokens = 0

    def __repr__(self) -> str:
        return f"ManagerAgent(model={self.model})"
