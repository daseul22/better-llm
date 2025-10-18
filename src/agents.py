"""
에이전트 구현

Agent: Claude API를 사용하여 응답을 생성하는 에이전트
"""

from typing import List, Optional
from pathlib import Path
import logging

from anthropic import Anthropic

from .models import AgentConfig, Message

logger = logging.getLogger(__name__)


class Agent:
    """
    Claude 기반 에이전트

    설정된 역할과 도구를 사용하여 대화에 응답합니다.

    Attributes:
        config: 에이전트 설정
        client: Anthropic API 클라이언트
        system_prompt: 시스템 프롬프트 (파일에서 로드되거나 직접 지정)
    """

    def __init__(self, config: AgentConfig, client: Anthropic):
        """
        Args:
            config: 에이전트 설정
            client: Anthropic API 클라이언트
        """
        self.config = config
        self.client = client
        self.system_prompt = self._load_system_prompt()

    def _load_system_prompt(self) -> str:
        """
        시스템 프롬프트 로드

        config.system_prompt가 파일 경로로 보이면 파일에서 로드하고,
        그렇지 않으면 문자열 그대로 사용합니다.

        Returns:
            시스템 프롬프트 문자열
        """
        prompt_text = self.config.system_prompt

        # .txt 확장자가 있거나 경로처럼 보이면 파일에서 로드 시도
        if prompt_text.endswith('.txt') or '/' in prompt_text:
            try:
                prompt_path = Path(prompt_text)
                if not prompt_path.is_absolute():
                    # 상대 경로면 프로젝트 루트 기준으로 처리
                    prompt_path = Path.cwd() / prompt_text

                if prompt_path.exists():
                    with open(prompt_path, 'r', encoding='utf-8') as f:
                        loaded_prompt = f.read().strip()
                        logger.info(f"✅ 시스템 프롬프트 로드: {prompt_path}")
                        return loaded_prompt
                else:
                    logger.warning(f"⚠️  프롬프트 파일 없음: {prompt_path}, 기본값 사용")
            except Exception as e:
                logger.error(f"❌ 프롬프트 로드 실패: {e}, 기본값 사용")

        # 파일 로드 실패 또는 일반 문자열
        return prompt_text

    def _format_messages_for_api(self, history: List[Message]) -> List[dict]:
        """
        대화 히스토리를 Claude API 형식으로 변환

        Args:
            history: 대화 히스토리

        Returns:
            Claude API용 메시지 리스트
        """
        api_messages = []

        for msg in history:
            # 에이전트 메시지는 assistant로, 사용자 메시지는 user로
            role = "assistant" if msg.role == "agent" else "user"

            # 에이전트 이름을 메시지에 포함
            content = msg.content
            if msg.role == "agent" and msg.agent_name:
                content = f"[{msg.agent_name}] {content}"

            api_messages.append({
                "role": role,
                "content": content
            })

        # Claude API는 user 메시지로 시작해야 함
        # 첫 메시지가 assistant면 더미 user 메시지 추가
        if api_messages and api_messages[0]["role"] == "assistant":
            api_messages.insert(0, {
                "role": "user",
                "content": "[시스템] 작업을 시작합니다."
            })

        # 마지막 메시지는 user여야 함
        if api_messages and api_messages[-1]["role"] == "assistant":
            api_messages.append({
                "role": "user",
                "content": "[시스템] 다음 단계를 진행해주세요."
            })

        return api_messages

    def respond(self, history: List[Message]) -> str:
        """
        대화 히스토리를 기반으로 응답 생성

        Args:
            history: 전체 대화 히스토리

        Returns:
            에이전트의 응답 텍스트

        Raises:
            Exception: Claude API 호출 실패 시
        """
        try:
            # 대화 히스토리를 API 형식으로 변환
            api_messages = self._format_messages_for_api(history)

            logger.debug(f"[{self.config.name}] API 호출 시작 (메시지: {len(api_messages)}개)")

            # Claude API 호출
            response = self.client.messages.create(
                model=self.config.model,
                max_tokens=4096,
                system=self.system_prompt,
                messages=api_messages,
                temperature=0.7,
                timeout=30.0  # 30초 타임아웃
            )

            # 응답 텍스트 추출
            response_text = response.content[0].text

            logger.debug(f"[{self.config.name}] API 호출 완료 (응답 길이: {len(response_text)} chars)")

            return response_text

        except Exception as e:
            logger.error(f"❌ [{self.config.name}] API 호출 실패: {e}")
            raise

    def __repr__(self) -> str:
        return f"Agent(name={self.config.name}, role={self.config.role}, model={self.config.model})"
