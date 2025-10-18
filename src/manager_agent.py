"""
매니저 에이전트 - 사용자와 대화하고 작업을 계획

ManagerAgent: Claude Agent SDK를 사용하여 Worker Tool들을 호출하고 작업 조율
"""

from typing import List, Optional
import logging

from claude_agent_sdk import query
from claude_agent_sdk.types import ClaudeAgentOptions

from .models import Message

logger = logging.getLogger(__name__)


class ManagerAgent:
    """
    사용자와 대화하는 매니저 에이전트

    Claude Agent SDK를 사용하여 사용자 요청을 분석하고,
    Worker Tool들을 호출하여 작업을 수행합니다.

    Attributes:
        model: 사용할 Claude 모델
        worker_tools_server: Worker Tools MCP 서버
    """

    SYSTEM_PROMPT = """당신은 소프트웨어 개발 프로젝트를 관리하는 매니저입니다.

## 역할
- 사용자 요청을 분석하고 이해합니다
- 작업을 계획하고 우선순위를 정합니다
- Worker Agent Tool을 호출하여 작업을 할당합니다
- 진행 상황을 사용자에게 보고합니다

## 사용 가능한 Tool
다음 Tool들을 사용할 수 있습니다:
- **execute_planner_task**: 요구사항 분석 및 계획 수립
- **execute_coder_task**: 코드 작성, 수정, 리팩토링
- **execute_tester_task**: 테스트 작성 및 실행
- **read**: 파일 읽기 (필요 시)

## 작업 수행 방법
1. 사용자 요청을 분석합니다
2. 필요한 Worker Tool을 순차적으로 호출합니다
3. 각 Tool의 결과를 확인하고 다음 단계를 결정합니다
4. 모든 작업이 완료되면 사용자에게 결과를 보고합니다

## 예시
사용자: "FastAPI로 /users CRUD API를 작성해줘"

1단계: execute_planner_task 호출 → 요구사항 분석 및 설계
2단계: execute_coder_task 호출 → 코드 작성
3단계: execute_tester_task 호출 → 테스트 작성 및 실행
4단계: 사용자에게 완료 보고

## 규칙
- Tool을 직접 호출하세요 (@ 표기 불필요)
- 각 Tool 호출 전에 무엇을 할 것인지 설명하세요
- Tool 결과를 확인하고 문제가 있으면 재시도하세요
- 모든 작업이 완료되면 "작업이 완료되었습니다"라고 명시하세요
"""

    def __init__(self, worker_tools_server, model: str = "claude-sonnet-4-5-20250929"):
        """
        Args:
            worker_tools_server: Worker Tools MCP 서버
            model: 사용할 Claude 모델
        """
        self.model = model
        self.worker_tools_server = worker_tools_server

    def _build_prompt_from_history(self, history: List[Message]) -> str:
        """
        대화 히스토리를 프롬프트 텍스트로 변환

        Args:
            history: 대화 히스토리

        Returns:
            프롬프트 문자열
        """
        # 시스템 프롬프트로 시작
        prompt_parts = [self.SYSTEM_PROMPT, "\n\n## 대화 히스토리:\n"]

        for msg in history:
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

    async def analyze_and_plan(self, history: List[Message]) -> str:
        """
        사용자 요청을 분석하고 작업 수행

        Args:
            history: 전체 대화 히스토리

        Returns:
            매니저의 응답 (Tool 호출 결과 포함)

        Raises:
            Exception: SDK 호출 실패 시
        """
        try:
            # 대화 히스토리를 프롬프트로 변환
            prompt = self._build_prompt_from_history(history)

            logger.debug(f"[Manager] Claude Agent SDK 호출 시작 (Worker Tools 사용)")

            # Claude Agent SDK의 query() 함수 사용
            # Worker Tools MCP Server를 등록하고, read 툴도 허용
            response_text = ""
            async for response in query(
                prompt=prompt,
                options=ClaudeAgentOptions(
                    model=self.model,
                    mcp_servers={"workers": self.worker_tools_server},
                    allowed_tools=[
                        "mcp__workers__execute_planner_task",
                        "mcp__workers__execute_coder_task",
                        "mcp__workers__execute_tester_task",
                        "read"  # 파일 읽기 툴
                    ],
                    cli_path="/Users/simdaseul/.claude/local/claude",
                    permission_mode="bypassPermissions"
                )
            ):
                # 응답 텍스트 추출
                if hasattr(response, 'content'):
                    for content in response.content:
                        if hasattr(content, 'text'):
                            response_text += content.text
                elif hasattr(response, 'text'):
                    response_text += response.text
                else:
                    response_text += str(response)

            logger.debug(f"[Manager] Claude Agent SDK 호출 완료 (응답 길이: {len(response_text)} chars)")

            return response_text

        except Exception as e:
            logger.error(f"❌ [Manager] SDK 호출 실패: {e}")
            raise

    def __repr__(self) -> str:
        return f"ManagerAgent(model={self.model})"
