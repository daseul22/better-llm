"""
워커 에이전트 - Claude Agent SDK로 실제 작업 수행

WorkerAgent: Claude Code의 agentic harness를 사용하여 파일 읽기/쓰기, 코드 실행 등 수행
"""

from typing import List, AsyncIterator
from pathlib import Path
import logging

from claude_agent_sdk import query

from .models import AgentConfig

logger = logging.getLogger(__name__)


class WorkerAgent:
    """
    실제 작업을 수행하는 워커 에이전트

    Claude Agent SDK를 사용하여 Claude Code의 모든 기능(파일 읽기/쓰기,
    bash 실행, grep, edit 등)을 프로그래밍 방식으로 실행합니다.

    Attributes:
        config: 에이전트 설정
        system_prompt: 시스템 프롬프트
    """

    def __init__(self, config: AgentConfig):
        """
        Args:
            config: 에이전트 설정
        """
        self.config = config
        self.system_prompt = self._load_system_prompt()

    def _load_system_prompt(self) -> str:
        """
        시스템 프롬프트 로드

        config.system_prompt가 파일 경로면 파일에서 로드하고,
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

        return prompt_text

    async def execute_task(self, task_description: str) -> AsyncIterator[str]:
        """
        Claude Agent SDK를 사용하여 작업 실행

        Args:
            task_description: 작업 설명

        Yields:
            스트리밍 응답 청크

        Raises:
            Exception: 작업 실행 실패 시
        """
        try:
            # 시스템 프롬프트와 작업 설명 결합
            full_prompt = f"{self.system_prompt}\n\n{task_description}"

            logger.debug(f"[{self.config.name}] Claude Agent SDK 실행 시작")

            # Claude Agent SDK의 query() 함수 사용
            # 이 함수는 Claude Code의 agentic harness를 사용하여
            # 파일 시스템 접근, bash 실행 등을 수행합니다
            async for response in query(
                prompt=full_prompt,
                model=self.config.model
            ):
                # response는 SDK에서 반환하는 응답 객체
                # 텍스트 콘텐츠 추출
                if hasattr(response, 'content'):
                    for content in response.content:
                        if hasattr(content, 'text'):
                            yield content.text
                elif hasattr(response, 'text'):
                    yield response.text
                else:
                    # 응답 형식이 예상과 다를 경우
                    yield str(response)

            logger.debug(f"[{self.config.name}] Claude Agent SDK 실행 완료")

        except Exception as e:
            logger.error(f"❌ [{self.config.name}] 작업 실행 실패: {e}")
            raise

    def __repr__(self) -> str:
        return f"WorkerAgent(name={self.config.name}, role={self.config.role})"
