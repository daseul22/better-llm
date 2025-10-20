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

from domain.models import AgentConfig
from domain.services import ProjectContext
from ..config import get_claude_cli_path, get_project_root
from ..storage import JsonContextRepository
from ..logging import get_logger, log_exception_silently

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
                logger.debug(f"✅ 프로젝트 컨텍스트 로드: {context.project_name}")
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
            logger.debug(f"✅ 프로젝트 컨텍스트 추가: {self.project_context.project_name}")

        return prompt_text

    def _generate_debug_info(self, task_description: str) -> str:
        """
        Worker 실행 시 디버그 정보 생성

        Args:
            task_description: 작업 설명

        Returns:
            포맷팅된 디버그 정보
        """
        lines = []
        lines.append("\n" + "="*70)
        lines.append(f"🔍 [{self.config.name.upper()}] 실행 정보")
        lines.append("="*70)

        # 1. 기본 정보
        lines.append(f"\n📋 Worker: {self.config.name} ({self.config.role})")
        lines.append(f"🤖 Model: {self.config.model}")
        lines.append(f"🛠️  Tools: {', '.join(self.config.tools)}")

        # 2. 시스템 프롬프트 정보
        lines.append(f"\n📄 System Prompt File: {self.config.system_prompt}")
        lines.append(f"   Length: {len(self.system_prompt)} characters")

        # 3. 프로젝트 컨텍스트 정보
        if self.project_context:
            lines.append(f"\n🏗️  Project Context:")
            lines.append(f"   - Project: {self.project_context.project_name}")
            lines.append(f"   - Description: {self.project_context.description[:80]}..."
                        if len(self.project_context.description) > 80
                        else f"   - Description: {self.project_context.description}")

            if self.project_context.coding_style:
                style = self.project_context.coding_style
                lines.append(f"   - Coding Style: {style.language}, indentation={style.indentation}")

            if self.project_context.testing_approach:
                lines.append(f"   - Testing: {self.project_context.testing_approach.framework}")
        else:
            lines.append(f"\n🏗️  Project Context: None")

        # 4. 작업 설명
        lines.append(f"\n📝 Task Description:")
        task_lines = task_description.split('\n')
        for i, line in enumerate(task_lines[:5]):  # 최대 5줄만 표시
            lines.append(f"   {line}")
        if len(task_lines) > 5:
            lines.append(f"   ... ({len(task_lines) - 5} more lines)")

        lines.append("\n" + "="*70)
        lines.append("⚡ Starting execution...\n")

        return "\n".join(lines)

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
        import time

        try:
            # 디버그 정보 출력 (환경변수로 제어)
            # WORKER_DEBUG_INFO=true로 설정하면 활성화
            show_debug_info = os.getenv("WORKER_DEBUG_INFO", "false").lower() in ("true", "1", "yes")
            if show_debug_info:
                debug_info = self._generate_debug_info(task_description)
                yield debug_info

            # 시스템 프롬프트와 작업 설명 결합
            full_prompt = f"{self.system_prompt}\n\n{task_description}"

            logger.debug(f"[{self.config.name}] Claude Agent SDK 실행 시작")
            logger.debug(f"[{self.config.name}] Working Directory: {os.getcwd()}")

            # 응답 없음 감지를 위한 타임스탬프 (30초 동안 응답 없으면 경고)
            last_chunk_time = time.time()
            no_response_timeout = 30  # 초

            # 조기 종료 감지를 위한 버퍼 (마지막 N 청크 저장)
            recent_chunks = []
            completion_keywords = [
                "완료되었습니다",
                "완료했습니다",
                "완료하였습니다",
                "작업 완료",
                "실행 완료"
            ]

            # 에러 키워드 감지 (에러 발생 시 즉시 종료)
            error_keywords = [
                "오류가 발생했습니다",
                "시스템 오류",
                "실패했습니다",
                "실행 실패",
                "에러가 발생",
                "[ERROR]",
                "Exception:",
                "Error:",
                "Failed to",
                "파일을 찾을 수 없습니다",
                "권한이 없습니다"
            ]

            # Claude Agent SDK의 query() 함수 사용
            # 이 함수는 Claude Code의 agentic harness를 사용하여
            # 파일 시스템 접근, bash 실행 등을 수행합니다
            # Note: working_dir는 ClaudeAgentOptions에서 지원하지 않음 (os.getcwd()가 기본값)
            async for response in query(
                prompt=full_prompt,
                options=ClaudeAgentOptions(
                    model=self.config.model,
                    allowed_tools=self.config.tools if self.config.tools else [],
                    cli_path=get_claude_cli_path(),
                    permission_mode="bypassPermissions"  # 자동 승인
                )
            ):
                # response는 SDK에서 반환하는 응답 객체
                # 텍스트 콘텐츠 추출
                chunk_text = None
                if hasattr(response, 'content'):
                    for content in response.content:
                        if hasattr(content, 'text'):
                            chunk_text = content.text
                            yield chunk_text
                elif hasattr(response, 'text'):
                    chunk_text = response.text
                    yield chunk_text
                else:
                    # 응답 형식이 예상과 다를 경우
                    chunk_text = str(response)
                    yield chunk_text

                # 조기 종료 감지: 최근 청크들을 버퍼에 저장
                if chunk_text:
                    # 청크를 받았으므로 타임스탬프 갱신
                    last_chunk_time = time.time()

                    recent_chunks.append(chunk_text)
                    # 최근 10개 청크만 유지
                    if len(recent_chunks) > 10:
                        recent_chunks.pop(0)

                    # 최근 청크들을 합쳐서 키워드 검색
                    recent_text = "".join(recent_chunks)

                    # 에러 키워드 우선 확인 (즉시 종료)
                    if any(keyword in recent_text for keyword in error_keywords):
                        logger.warning(
                            f"[{self.config.name}] 조기 종료 감지: "
                            f"에러 키워드 발견. 스트리밍 종료."
                        )
                        # 에러 발생 시 즉시 종료 (타임아웃까지 기다리지 않음)
                        break

                    # 완료 키워드 확인
                    if any(keyword in recent_text for keyword in completion_keywords):
                        logger.debug(
                            f"[{self.config.name}] 조기 종료 감지: "
                            f"완료 키워드 발견. 스트리밍 종료."
                        )
                        # 스트리밍 종료 (더 이상 응답을 기다리지 않음)
                        break

                # 응답 없음 감지: 마지막 청크 이후 시간 확인
                elapsed = time.time() - last_chunk_time
                if elapsed > no_response_timeout:
                    logger.warning(
                        f"[{self.config.name}] {no_response_timeout}초 동안 응답 없음. "
                        f"스트리밍 조기 종료."
                    )
                    # 응답이 멈춘 것으로 간주하고 종료
                    break

            logger.debug(f"[{self.config.name}] Claude Agent SDK 실행 완료")

        except Exception as e:
            # 런타임 에러를 조용히 로그에 기록 (프로그램 종료하지 않음)
            log_exception_silently(
                logger,
                e,
                f"Worker Agent ({self.config.name}) execution failed",
                worker_name=self.config.name,
                worker_role=self.config.role,
                model=self.config.model
            )
            # 예외를 재발생시키지 않고 에러 메시지 반환
            yield f"\n[시스템 오류] {self.config.name} Worker 실행 중 오류가 발생했습니다. 에러 로그를 확인해주세요."

    def __repr__(self) -> str:
        return f"WorkerAgent(name={self.config.name}, role={self.config.role})"
