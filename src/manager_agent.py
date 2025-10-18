"""
매니저 에이전트 - 사용자와 대화하고 작업을 계획

ManagerAgent: Claude Agent SDK를 사용하여 사용자와 대화하고 워커 에이전트에게 작업 할당
"""

from typing import List, Optional, AsyncIterator
import logging

from claude_agent_sdk import query

from .models import Message

logger = logging.getLogger(__name__)


class ManagerAgent:
    """
    사용자와 대화하는 매니저 에이전트

    Claude Agent SDK를 사용하여 사용자 요청을 분석하고,
    워커 에이전트에게 전달할 작업을 계획합니다.

    Attributes:
        model: 사용할 Claude 모델
    """

    SYSTEM_PROMPT = """당신은 소프트웨어 개발 프로젝트를 관리하는 매니저입니다.

## 역할
- 사용자 요청을 분석하고 이해합니다
- 작업을 계획하고 우선순위를 정합니다
- 워커 에이전트(Planner, Coder, Tester)에게 작업을 할당합니다
- 진행 상황을 사용자에게 보고합니다

## 작업 분석
사용자 요청을 받으면 다음을 수행하세요:
1. 요구사항 명확화
2. 필요한 에이전트 결정
3. 작업 순서 계획
4. 각 에이전트에게 전달할 구체적인 지시사항 작성

## 출력 형식
다음 형식으로 응답하세요:

**작업 분석:**
[사용자 요청에 대한 요약]

**작업 계획:**
1. [단계 1] - [@agent_name]에게 할당
2. [단계 2] - [@agent_name]에게 할당
...

**다음 단계:**
@[first_agent_name] [구체적인 지시사항]

## 규칙
- 명확하고 구체적인 지시사항을 제공하세요
- 에이전트 이름 앞에 @를 붙이세요 (@planner, @coder, @tester)
- 작업이 완료되면 사용자에게 요약 보고하세요
"""

    def __init__(self, model: str = "claude-sonnet-4-5-20250929"):
        """
        Args:
            model: 사용할 Claude 모델
        """
        self.model = model

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
                # 워커 에이전트의 작업 결과
                prompt_parts.append(f"\n[{msg.agent_name} 작업 완료]\n{msg.content}\n")
            elif msg.role == "manager":
                # 매니저 자신의 이전 응답
                prompt_parts.append(f"\n[매니저 (당신)]\n{msg.content}\n")

        prompt_parts.append("\n다음 단계를 계획해주세요:")

        return "".join(prompt_parts)

    async def analyze_and_plan(self, history: List[Message]) -> str:
        """
        사용자 요청을 분석하고 작업 계획 수립

        Args:
            history: 전체 대화 히스토리

        Returns:
            매니저의 분석 및 계획 응답

        Raises:
            Exception: SDK 호출 실패 시
        """
        try:
            # 대화 히스토리를 프롬프트로 변환
            prompt = self._build_prompt_from_history(history)

            logger.debug(f"[Manager] Claude Agent SDK 호출 시작")

            # Claude Agent SDK의 query() 함수 사용
            response_text = ""
            async for response in query(
                prompt=prompt,
                model=self.model
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
