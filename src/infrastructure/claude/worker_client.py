"""
워커 에이전트 - Claude Agent SDK로 실제 작업 수행

WorkerAgent: Claude Code의 agentic harness를 사용하여 파일 읽기/쓰기, 코드 실행 등 수행
"""

from typing import List, AsyncIterator, Optional
from pathlib import Path
import logging
import os

from claude_agent_sdk import query
from claude_agent_sdk.types import ClaudeAgentOptions

from src.domain.models import AgentConfig
from src.domain.services import ProjectContext
from src.infrastructure.config import get_claude_cli_path, get_project_root
from src.infrastructure.storage import JsonContextRepository
from src.infrastructure.logging import get_logger, log_exception_silently
from .sdk_executor import (
    SDKExecutionConfig,
    WorkerResponseHandler,
    WorkerSDKExecutor
)

logger = get_logger(__name__)


class WorkerAgent:
    """
    실제 작업을 수행하는 워커 에이전트

    Claude Agent SDK를 사용하여 Claude Code의 모든 기능(파일 읽기/쓰기,
    bash 실행, grep, edit 등)을 프로그래밍 방식으로 실행합니다.

    Attributes:
        config: 에이전트 설정
        system_prompt: 시스템 프롬프트
    """

    def __init__(self, config: AgentConfig, project_context: Optional[ProjectContext] = None):
        """
        Args:
            config: 에이전트 설정
            project_context: 프로젝트 컨텍스트 (선택)
        """
        self.config = config
        self.project_context = project_context or self._load_project_context()
        self.system_prompt = self._load_system_prompt()

    def _load_project_context(self) -> Optional[ProjectContext]:
        """
        프로젝트 컨텍스트 로드

        Returns:
            ProjectContext 또는 None
        """
        try:
            repo = JsonContextRepository(get_project_root() / ".context.json")
            context = repo.load()
            if context:
                logger.info(f"✅ 프로젝트 컨텍스트 로드: {context.project_name}")
            return context
        except Exception as e:
            logger.warning(f"⚠️  프로젝트 컨텍스트 로드 실패: {e}")
            return None

    def _load_system_prompt(self) -> str:
        """
        시스템 프롬프트 로드 (프로젝트 루트 기준)

        config.system_prompt가 파일 경로면 파일에서 로드하고,
        그렇지 않으면 문자열 그대로 사용합니다.
        프로젝트 컨텍스트가 있으면 프롬프트에 추가합니다.

        Returns:
            시스템 프롬프트 문자열
        """
        prompt_text = self.config.system_prompt

        # .txt 확장자가 있거나 경로처럼 보이면 파일에서 로드 시도
        if prompt_text.endswith('.txt') or '/' in prompt_text:
            try:
                prompt_path = Path(prompt_text)
                if not prompt_path.is_absolute():
                    # 프로젝트 루트 기준으로 경로 해석
                    prompt_path = get_project_root() / prompt_text

                if prompt_path.exists():
                    with open(prompt_path, 'r', encoding='utf-8') as f:
                        loaded_prompt = f.read().strip()
                        logger.info(f"✅ 시스템 프롬프트 로드: {prompt_path}")
                        prompt_text = loaded_prompt
                else:
                    logger.warning(f"⚠️  프롬프트 파일 없음: {prompt_path}, 기본값 사용")
            except Exception as e:
                logger.error(f"❌ 프롬프트 로드 실패: {e}, 기본값 사용")

        # 프로젝트 컨텍스트 추가
        if self.project_context:
            context_text = self.project_context.to_prompt_context()
            prompt_text = f"{prompt_text}\n\n{context_text}"
            logger.info(f"✅ 프로젝트 컨텍스트 추가: {self.project_context.project_name}")

        return prompt_text

    def _generate_debug_info(self, task_description: str) -> str:
        """
        Worker 실행 시 디버그 정보 생성 (시스템 프롬프트, 맥락 포함)

        Args:
            task_description: 작업 설명

        Returns:
            포맷팅된 디버그 정보
        """
        lines = []
        lines.append("\n" + "="*70)
        lines.append(f"🔍 [{self.config.name.upper()}] Worker 실행 정보")
        lines.append("="*70)

        # 1. 기본 정보
        lines.append(f"\n📋 Worker: {self.config.name} ({self.config.role})")
        lines.append(f"🤖 Model: {self.config.model}")
        lines.append(f"🛠️  Tools: {', '.join(self.config.tools) if self.config.tools else 'None'}")

        # 2. 시스템 프롬프트 정보 (전체 내용 표시)
        lines.append(f"\n📄 System Prompt:")
        lines.append(f"   Source: {self.config.system_prompt}")
        lines.append(f"   Length: {len(self.system_prompt)} characters")
        lines.append("\n" + "-"*70)
        # 시스템 프롬프트 전체 표시 (indented)
        for line in self.system_prompt.split('\n'):
            lines.append(f"   {line}")
        lines.append("-"*70)

        # 3. 프로젝트 컨텍스트 정보 (상세)
        if self.project_context:
            lines.append(f"\n🏗️  Project Context:")
            lines.append(f"   - Project: {self.project_context.project_name}")
            lines.append(f"   - Description: {self.project_context.description}")

            if self.project_context.coding_style:
                style = self.project_context.coding_style
                lines.append(f"   - Coding Style:")
                lines.append(f"     • Docstring: {style.docstring_style}")
                lines.append(f"     • Type Hints: {'사용' if style.type_hints else '미사용'}")
                lines.append(f"     • Line Length: {style.line_length}")
                lines.append(f"     • Quote Style: {style.quote_style}")
                lines.append(f"     • Import Style: {style.import_style}")
        else:
            lines.append(f"\n🏗️  Project Context: None")

        # 4. 작업 설명 (전체 표시)
        lines.append(f"\n📝 Task Description:")
        lines.append("-"*70)
        for line in task_description.split('\n'):
            lines.append(f"   {line}")
        lines.append("-"*70)

        lines.append("\n" + "="*70)
        lines.append("⚡ Starting Worker execution...")
        lines.append("="*70 + "\n")

        return "\n".join(lines)

    async def execute_task(
        self,
        task_description: str,
        usage_callback: Optional[callable] = None
    ) -> AsyncIterator[str]:
        """
        Claude Agent SDK를 사용하여 작업 실행

        Args:
            task_description: 작업 설명
            usage_callback: 토큰 사용량 정보를 받을 콜백 함수 (선택)

        Yields:
            스트리밍 응답 청크

        Raises:
            Exception: 작업 실행 실패 시
        """
        # 디버그 정보 출력 (기본 비활성화 - 컨텍스트 절약)
        # WORKER_DEBUG_INFO=true로 설정하면 활성화
        show_debug_info = os.getenv("WORKER_DEBUG_INFO", "false").lower() in (
            "true", "1", "yes"
        )
        if show_debug_info:
            debug_info = self._generate_debug_info(task_description)
            yield debug_info

        # 시스템 프롬프트와 작업 설명 결합
        full_prompt = f"{self.system_prompt}\n\n{task_description}"

        logger.info(f"[{self.config.name}] Claude Agent SDK 실행 시작")
        logger.info(f"[{self.config.name}] Working Directory: {os.getcwd()}")
        logger.info(f"[{self.config.name}] Prompt 길이: {len(full_prompt)} characters")
        logger.info(f"[{self.config.name}] Model: {self.config.model}")
        logger.info(f"[{self.config.name}] Tools: {self.config.tools}")
        logger.info(f"[{self.config.name}] CLI Path: {get_claude_cli_path()}")

        # SDK 실행 설정
        config = SDKExecutionConfig(
            model=self.config.model,
            cli_path=get_claude_cli_path(),
            permission_mode="bypassPermissions"
        )

        # 응답 핸들러 생성 (usage_callback 전달)
        response_handler = WorkerResponseHandler(usage_callback=usage_callback)

        # Executor 생성
        executor = WorkerSDKExecutor(
            config=config,
            allowed_tools=self.config.tools if self.config.tools else [],
            response_handler=response_handler,
            worker_name=self.config.name
        )

        # 스트림 실행
        async for text in executor.execute_stream(full_prompt):
            yield text

        # Worker 실행 완료 표시
        yield f"\n{'='*70}\n✅ [{self.config.name.upper()}] Worker execution completed\n{'='*70}\n"

    def __repr__(self) -> str:
        return f"WorkerAgent(name={self.config.name}, role={self.config.role})"
