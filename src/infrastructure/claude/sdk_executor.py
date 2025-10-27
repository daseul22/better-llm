"""
Agent SDK 실행 래퍼 모듈.

클라이언트 코드의 중복을 제거하기 위한 Template Method Pattern 기반 Executor.
"""

from dataclasses import dataclass
from typing import AsyncIterator, Callable, Optional, Any, List
from abc import ABC, abstractmethod

from claude_agent_sdk import (
    AssistantMessage,
    ResultMessage,
    UserMessage,
    SystemMessage,
    TextBlock,
    ThinkingBlock,
    ToolUseBlock,
    ToolResultBlock,
    CLINotFoundError,
    ProcessError,
    CLIJSONDecodeError,
    ClaudeSDKError
)

from src.domain.exceptions import WorkerExecutionError
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)


@dataclass
class SDKExecutionConfig:
    """SDK 실행 설정.

    Attributes:
        model: Claude 모델명
        max_tokens: 최대 생성 토큰 수
        temperature: 샘플링 온도
        timeout: 타임아웃 (초)
        cli_path: Claude CLI 경로
        permission_mode: 권한 모드
        max_turns: 최대 대화 턴 수 (None이면 무제한)
        continue_conversation: 이전 세션 재개 여부
        setting_sources: 설정 파일 로드 소스 리스트 (예: ["user", "project", "local"])
        system_prompt: 시스템 프롬프트 (선택, Manager/Worker에서 제공)
    """
    model: str = "claude-sonnet-4-5-20250929"
    max_tokens: int = 8000
    temperature: float = 0.7
    timeout: int = 600
    cli_path: Optional[str] = None
    permission_mode: str = "acceptEdits"  # 기본값: acceptEdits (프로덕션 안전)
    max_turns: Optional[int] = None
    continue_conversation: bool = False
    setting_sources: Optional[List[str]] = None
    system_prompt: Optional[str] = None  # 명시적 시스템 프롬프트 (SDK Best Practice)

    def __post_init__(self):
        """기본값 초기화 (List는 mutable이므로 __post_init__에서 처리)."""
        if self.setting_sources is None:
            self.setting_sources = ["user", "project"]

        # 환경변수로 permission_mode 오버라이드
        import os
        env_permission_mode = os.getenv("PERMISSION_MODE")
        if env_permission_mode:
            valid_modes = ["default", "acceptEdits", "bypassPermissions", "plan"]
            if env_permission_mode in valid_modes:
                self.permission_mode = env_permission_mode
            else:
                logger.warning(
                    f"Invalid PERMISSION_MODE: {env_permission_mode}, "
                    f"valid values: {valid_modes}, using default: {self.permission_mode}"
                )


class SDKResponseHandler(ABC):
    """SDK 응답 핸들러 추상 클래스.

    Template Method Pattern의 Abstract Class 역할.
    각 클라이언트는 이 클래스를 상속하여 process_response 메서드를 구현.
    """

    @abstractmethod
    async def process_response(self, response: Any) -> AsyncIterator[str]:
        """응답 처리 및 텍스트 추출.

        Args:
            response: SDK 응답 객체

        Yields:
            str: 추출된 텍스트 청크
        """
        pass

    # ========================================================================
    # 텍스트 추출 헬퍼 메서드
    # ========================================================================

    def extract_text_from_response(self, response: Any) -> Optional[str]:
        """
        SDK 응답 객체에서 텍스트 추출 (공통 로직).

        처리 순서:
        1. AssistantMessage → content blocks 순회 → TextBlock/ThinkingBlock 추출
        2. ResultMessage → 텍스트 없음 (usage 정보만)
        3. 폴백 → hasattr()로 동적 추출 (하위 호환성)

        Args:
            response: SDK 응답 객체

        Returns:
            str: 추출된 텍스트 또는 None
        """
        # [1단계] AssistantMessage 처리
        # Claude가 생성한 응답 메시지 (텍스트, 사고 과정, 도구 호출 등)
        if isinstance(response, AssistantMessage):
            if not response.content:
                logger.debug("AssistantMessage has no content")
                return None

            # content blocks 순회 (여러 블록이 있을 수 있음)
            for i, content_block in enumerate(response.content):
                # TextBlock: 일반 텍스트 응답
                if isinstance(content_block, TextBlock):
                    logger.debug(f"Extracted text from TextBlock #{i}")
                    return content_block.text

                # ThinkingBlock: Extended Thinking 모드의 사고 과정
                elif isinstance(content_block, ThinkingBlock):
                    if hasattr(content_block, 'text') and content_block.text:
                        logger.debug(f"Extracted text from ThinkingBlock #{i}")
                        return content_block.text

            # content blocks는 있지만 텍스트가 없는 경우
            logger.debug(
                f"AssistantMessage has {len(response.content)} blocks but no text"
            )
            return None

        # [2단계] ResultMessage 처리
        # 스트리밍 종료 시 전송되는 메타 정보 (usage 통계 등)
        elif isinstance(response, ResultMessage):
            # ResultMessage는 텍스트가 아닌 메타데이터만 포함
            logger.debug("ResultMessage (no text content)")
            return None

        # [3단계] SystemMessage 처리
        # 시스템 메타데이터 메시지 (SDK 내부 상태 정보 등)
        elif isinstance(response, SystemMessage):
            # SystemMessage는 content를 가질 수 있음 (텍스트 또는 리스트)
            if hasattr(response, 'content'):
                # content가 문자열인 경우
                if isinstance(response.content, str):
                    logger.debug("Extracted text from SystemMessage (string content)")
                    return response.content

                # content가 리스트인 경우 (blocks)
                elif isinstance(response.content, list):
                    for i, content_block in enumerate(response.content):
                        if isinstance(content_block, TextBlock):
                            logger.debug(f"Extracted text from SystemMessage TextBlock #{i}")
                            return content_block.text

            logger.debug("SystemMessage has no extractable text content")
            return None

        # [4단계] 폴백 처리 (하위 호환성)
        # 알 수 없는 응답 타입이거나 SDK 버전 변경 시 대비
        logger.debug(f"Unknown response type: {type(response).__name__}, trying fallback")

        # 시도 1: content 리스트 확인
        if hasattr(response, 'content') and isinstance(response.content, list):
            for content in response.content:
                if hasattr(content, 'text') and content.text:
                    logger.debug("Extracted text from content list (fallback)")
                    return content.text

        # 시도 2: 직접 text 속성 확인
        if hasattr(response, 'text') and isinstance(response.text, str):
            logger.debug("Extracted text directly (fallback)")
            return response.text

        # 추출 실패
        logger.debug("No text found in response")
        return None

    # ========================================================================
    # Usage 정보 추출 헬퍼 메서드 (토큰 사용량)
    # ========================================================================

    def extract_usage_info(
        self,
        usage_obj: Any,
        context: str = "Unknown"
    ) -> Optional[dict]:
        """
        usage 객체에서 토큰 사용량 정보 추출.

        usage 객체는 dict 또는 object 타입일 수 있음 (SDK 버전에 따라 다름)

        Args:
            usage_obj: usage 정보 객체 또는 딕셔너리
            context: 로깅용 컨텍스트 (Manager/Worker 등)

        Returns:
            dict: 토큰 사용량 딕셔너리 또는 None
            {
                'input_tokens': int,           # 입력 토큰 수
                'output_tokens': int,          # 출력 토큰 수
                'cache_read_tokens': int,      # 캐시에서 읽은 토큰 수
                'cache_creation_tokens': int   # 캐시 생성 토큰 수
            }
        """
        if not usage_obj:
            logger.debug(f"[{context}] No usage object provided")
            return None

        usage_dict = {}

        # [방법 1] dict 타입인 경우
        if isinstance(usage_obj, dict):
            logger.debug(f"[{context}] Extracting usage from dict")
            usage_dict['input_tokens'] = usage_obj.get('input_tokens', 0)
            usage_dict['output_tokens'] = usage_obj.get('output_tokens', 0)
            usage_dict['cache_read_tokens'] = usage_obj.get('cache_read_input_tokens', 0)
            usage_dict['cache_creation_tokens'] = usage_obj.get(
                'cache_creation_input_tokens', 0
            )

        # [방법 2] object 타입인 경우 (속성 접근)
        else:
            logger.debug(f"[{context}] Extracting usage from object")
            # 각 속성이 존재하는지 확인 후 추출
            if hasattr(usage_obj, 'input_tokens'):
                usage_dict['input_tokens'] = usage_obj.input_tokens
            if hasattr(usage_obj, 'output_tokens'):
                usage_dict['output_tokens'] = usage_obj.output_tokens
            if hasattr(usage_obj, 'cache_read_tokens'):
                usage_dict['cache_read_tokens'] = usage_obj.cache_read_tokens
            if hasattr(usage_obj, 'cache_creation_tokens'):
                usage_dict['cache_creation_tokens'] = usage_obj.cache_creation_tokens

        # 추출 성공 여부 확인
        if usage_dict:
            logger.debug(f"[{context}] Usage extracted: {usage_dict}")
            return usage_dict
        else:
            logger.warning(f"[{context}] Failed to extract usage from: {type(usage_obj)}")
            return None


class ManagerResponseHandler(SDKResponseHandler):
    """
    Manager Client용 응답 핸들러.

    ClaudeSDKClient의 receive_response()에서 반환된 응답을 처리합니다.

    처리 흐름:
    1. ResultMessage → usage 정보 추출 → 콜백 호출 → 종료
    2. AssistantMessage → usage 정보 추출 → 콜백 호출 → 텍스트 추출 → yield
    3. 알 수 없는 타입 → 폴백 처리
    """

    def __init__(self, usage_callback: Optional[Callable[[dict], None]] = None):
        """초기화.

        Args:
            usage_callback: 토큰 사용량 정보를 받을 콜백 함수
        """
        self.usage_callback = usage_callback

    async def process_response(self, response: Any) -> AsyncIterator[str]:
        """
        SDK 응답 처리 (Manager용).

        Args:
            response: ClaudeSDKClient.receive_response()의 응답 객체

        Yields:
            str: 추출된 텍스트 청크
        """
        # ====================================================================
        # [1단계] ResultMessage 처리 (스트리밍 종료, usage 정보만 존재)
        # ====================================================================
        if isinstance(response, ResultMessage):
            logger.debug("[Manager] Processing ResultMessage (usage info)")

            # usage 정보 추출 및 콜백 호출
            if response.usage and self.usage_callback:
                usage_dict = self.extract_usage_info(response.usage, context="Manager")
                if usage_dict:
                    logger.info(f"[Manager] Token usage (ResultMessage): {usage_dict}")
                    self.usage_callback(usage_dict)

            # ResultMessage는 텍스트가 없으므로 여기서 종료
            return

        # ====================================================================
        # [2단계] AssistantMessage 처리 (Claude의 응답, 텍스트 + usage 포함)
        # ====================================================================
        if isinstance(response, AssistantMessage):
            logger.debug("[Manager] Processing AssistantMessage")

            # (2-1) usage 정보 추출 및 콜백 호출
            if hasattr(response, 'usage') and response.usage and self.usage_callback:
                usage_dict = self.extract_usage_info(response.usage, context="Manager")
                if usage_dict:
                    logger.info(f"[Manager] Token usage (AssistantMessage): {usage_dict}")
                    self.usage_callback(usage_dict)

            # (2-2) 텍스트 추출 및 yield
            text = self.extract_text_from_response(response)
            if text:
                yield text
            return

        # ====================================================================
        # [3단계] SystemMessage 처리 (시스템 메타데이터)
        # ====================================================================
        if isinstance(response, SystemMessage):
            logger.debug("[Manager] Processing SystemMessage")

            # SystemMessage는 usage 정보가 없을 수 있으므로 확인 후 처리
            if hasattr(response, 'usage') and response.usage and self.usage_callback:
                usage_dict = self.extract_usage_info(response.usage, context="Manager")
                if usage_dict:
                    logger.info(f"[Manager] Token usage (SystemMessage): {usage_dict}")
                    self.usage_callback(usage_dict)

            # 텍스트 추출 및 yield
            text = self.extract_text_from_response(response)
            if text:
                yield text
            return

        # ====================================================================
        # [4단계] 폴백 처리 (알 수 없는 응답 타입)
        # ====================================================================
        logger.warning(f"[Manager] Unknown response type: {type(response).__name__}")

        # (3-1) usage 정보 추출 시도
        if hasattr(response, 'usage') and response.usage and self.usage_callback:
            usage_dict = self.extract_usage_info(response.usage, context="Manager")
            if usage_dict:
                logger.info(f"[Manager] Token usage (fallback): {usage_dict}")
                self.usage_callback(usage_dict)

        # (3-2) 텍스트 추출 시도
        text = self.extract_text_from_response(response)
        if text:
            yield text


class WorkerResponseHandler(SDKResponseHandler):
    """
    Worker Client용 응답 핸들러.

    query() 함수의 스트리밍 응답을 처리합니다.

    처리 흐름:
    1. ResultMessage → usage 정보 추출 → 콜백 호출 → 종료
    2. AssistantMessage → usage 정보 추출 → 콜백 호출 → 텍스트 추출 → yield
    3. 알 수 없는 타입 → 폴백 처리
    """

    def __init__(self, usage_callback: Optional[Callable[[dict], None]] = None):
        """초기화.

        Args:
            usage_callback: 토큰 사용량 정보를 받을 콜백 함수
        """
        self.usage_callback = usage_callback

    async def process_response(self, response: Any) -> AsyncIterator[str]:
        """
        SDK 응답 처리 (Worker용).

        Args:
            response: query() 함수의 응답 객체

        Yields:
            str: 추출된 텍스트 청크
        """
        # ====================================================================
        # [1단계] ResultMessage 처리 (스트리밍 종료, usage 정보만 존재)
        # ====================================================================
        if isinstance(response, ResultMessage):
            logger.debug("[Worker] Processing ResultMessage (usage info)")

            # usage 정보 추출 및 콜백 호출
            if response.usage and self.usage_callback:
                usage_dict = self.extract_usage_info(response.usage, context="Worker")
                if usage_dict:
                    logger.info(f"[Worker] Token usage (ResultMessage): {usage_dict}")
                    self.usage_callback(usage_dict)

            # ResultMessage는 텍스트가 없으므로 여기서 종료
            return

        # ====================================================================
        # [2단계] AssistantMessage 처리 (Claude의 응답, 텍스트 + usage 포함)
        # ====================================================================
        if isinstance(response, AssistantMessage):
            logger.debug("[Worker] Processing AssistantMessage")

            # (2-1) usage 정보 추출 및 콜백 호출
            if hasattr(response, 'usage') and response.usage and self.usage_callback:
                usage_dict = self.extract_usage_info(response.usage, context="Worker")
                if usage_dict:
                    logger.info(f"[Worker] Token usage (AssistantMessage): {usage_dict}")
                    self.usage_callback(usage_dict)

            # (2-2) 텍스트 추출 및 yield
            text = self.extract_text_from_response(response)
            if text:
                yield text
            return

        # ====================================================================
        # [3단계] SystemMessage 처리 (시스템 메타데이터)
        # ====================================================================
        if isinstance(response, SystemMessage):
            logger.debug("[Worker] Processing SystemMessage")

            # SystemMessage는 usage 정보가 없을 수 있으므로 확인 후 처리
            if hasattr(response, 'usage') and response.usage and self.usage_callback:
                usage_dict = self.extract_usage_info(response.usage, context="Worker")
                if usage_dict:
                    logger.info(f"[Worker] Token usage (SystemMessage): {usage_dict}")
                    self.usage_callback(usage_dict)

            # 텍스트 추출 및 yield
            text = self.extract_text_from_response(response)
            if text:
                yield text
            return

        # ====================================================================
        # [4단계] 폴백 처리 (알 수 없는 응답 타입)
        # ====================================================================
        logger.warning(f"[Worker] Unknown response type: {type(response).__name__}")

        # (3-1) usage 정보 추출 시도
        if hasattr(response, 'usage') and response.usage and self.usage_callback:
            usage_dict = self.extract_usage_info(response.usage, context="Worker")
            if usage_dict:
                logger.info(f"[Worker] Token usage (fallback): {usage_dict}")
                self.usage_callback(usage_dict)

        # (3-2) 텍스트 추출 시도
        text = self.extract_text_from_response(response)
        if text:
            yield text
        else:
            # 예상과 다른 형식일 경우 JSON으로 직렬화
            # (파서가 JSON을 파싱해서 보기 좋게 표시할 수 있도록)
            import json
            try:
                # response 객체를 JSON으로 변환 (pydantic 모델인 경우)
                if hasattr(response, 'model_dump'):
                    response_dict = response.model_dump()
                elif hasattr(response, 'dict'):
                    response_dict = response.dict()
                elif hasattr(response, '__dict__'):
                    response_dict = response.__dict__
                else:
                    response_dict = {'raw': str(response)}

                yield json.dumps(response_dict, ensure_ascii=False, indent=2)
            except Exception:
                # JSON 변환 실패 시 문자열로 폴백
                yield str(response)


class ManagerSDKExecutor:
    """Manager용 SDK 실행 래퍼.

    ClaudeSDKClient를 사용하여 스트리밍 응답을 처리합니다.
    """

    def __init__(
        self,
        config: SDKExecutionConfig,
        mcp_servers: dict,
        allowed_tools: list[str],
        response_handler: ManagerResponseHandler,
        session_id: Optional[str] = None,
        hooks: Optional[dict] = None
    ):
        """초기화.

        Args:
            config: SDK 실행 설정
            mcp_servers: MCP 서버 딕셔너리
            allowed_tools: 허용된 도구 목록
            response_handler: 응답 핸들러
            session_id: 세션 ID (로깅용)
            hooks: Agent SDK Hooks (선택, {"PreToolUse": [...], "PostToolUse": [...]})
        """
        self.config = config
        self.mcp_servers = mcp_servers
        self.allowed_tools = allowed_tools
        self.response_handler = response_handler
        self.hooks = hooks or {}
        self.logger = get_logger(__name__, session_id=session_id or "unknown")

    async def execute_stream(self, prompt: str) -> AsyncIterator[str]:
        """스트림 실행.

        Args:
            prompt: 프롬프트

        Yields:
            str: 응답 텍스트 청크

        Raises:
            WorkerExecutionError: SDK 실행 중 에러 발생 시
        """
        from claude_agent_sdk import ClaudeSDKClient
        from claude_agent_sdk.types import ClaudeAgentOptions

        client = None
        cleanup_done = False

        try:
            self.logger.debug(
                "Starting Claude Agent SDK call (Manager)",
                model=self.config.model,
                allowed_tools_count=len(self.allowed_tools)
            )

            # ClaudeAgentOptions 생성
            options_dict = {
                "model": self.config.model,
                "mcp_servers": self.mcp_servers,
                "allowed_tools": self.allowed_tools,
                "cli_path": self.config.cli_path,
                "permission_mode": self.config.permission_mode
            }

            # 선택적 컨텍스트 관리 옵션 추가 (None이 아니면)
            if self.config.max_turns is not None:
                options_dict["max_turns"] = self.config.max_turns
            if self.config.continue_conversation:
                options_dict["continue_conversation"] = self.config.continue_conversation
            if self.config.setting_sources:
                options_dict["setting_sources"] = self.config.setting_sources

            # System Prompt 명시적 설정 (SDK Best Practice)
            # ClaudeAgentOptions에서 system_prompt를 직접 지원하지 않으므로
            # 프롬프트에 포함하여 전달 (현재 방식 유지)
            # 참고: system_prompt는 query() 호출 시 프롬프트에 포함됨

            # Hooks 추가 (비어있지 않으면)
            if self.hooks:
                options_dict["hooks"] = self.hooks
                self.logger.debug(
                    "Hooks enabled",
                    hook_events=list(self.hooks.keys())
                )

            options = ClaudeAgentOptions(**options_dict)

            # Client 생성 및 연결
            client = ClaudeSDKClient(options=options)
            await client.connect()

            # 프롬프트 전송
            await client.query(prompt)

            # 응답 수신 (스트리밍)
            async for response in client.receive_response():
                async for text in self.response_handler.process_response(response):
                    yield text

            self.logger.debug("Claude Agent SDK call completed (Manager)")

            # 스트리밍 완료 후 client 객체에서 usage 확인
            self.logger.info(f"[Manager] Checking client for usage after streaming...")
            self.logger.info(f"[Manager] Client type: {type(client).__name__}")
            client_attrs = [attr for attr in dir(client) if not attr.startswith('_') and 'usage' in attr.lower()]
            self.logger.info(f"[Manager] Client usage-related attributes: {client_attrs}")

            # client 객체에 usage 정보가 있는지 확인
            if hasattr(client, 'usage'):
                self.logger.info(f"[Manager] client.usage: {client.usage}")
                if client.usage and self.response_handler.usage_callback:
                    usage_dict = {}

                    # usage가 dict인 경우와 object인 경우 모두 지원
                    if isinstance(client.usage, dict):
                        usage_dict['input_tokens'] = client.usage.get('input_tokens', 0)
                        usage_dict['output_tokens'] = client.usage.get('output_tokens', 0)
                        usage_dict['cache_read_tokens'] = client.usage.get('cache_read_input_tokens', 0)
                        usage_dict['cache_creation_tokens'] = client.usage.get('cache_creation_input_tokens', 0)
                    else:
                        # hasattr 체크 후 None이 아닌지도 확인
                        if hasattr(client.usage, 'input_tokens') and client.usage.input_tokens is not None:
                            usage_dict['input_tokens'] = client.usage.input_tokens
                        if hasattr(client.usage, 'output_tokens') and client.usage.output_tokens is not None:
                            usage_dict['output_tokens'] = client.usage.output_tokens
                        if hasattr(client.usage, 'cache_read_tokens') and client.usage.cache_read_tokens is not None:
                            usage_dict['cache_read_tokens'] = client.usage.cache_read_tokens
                        if hasattr(client.usage, 'cache_creation_tokens') and client.usage.cache_creation_tokens is not None:
                            usage_dict['cache_creation_tokens'] = client.usage.cache_creation_tokens

                    if usage_dict:
                        self.logger.info(f"[Manager] Found usage in client: {usage_dict}")
                        self.response_handler.usage_callback(usage_dict)

        except GeneratorExit:
            # Generator가 중간에 종료될 때는 cleanup 하지 않음
            self.logger.debug("Generator exit - cleanup skipped")
            raise

        except asyncio.CancelledError:
            # 작업 취소는 정상 종료로 간주 (에러 로깅 없이 조용히 종료)
            self.logger.debug("Task cancelled by user")
            return

        except Exception as e:
            from src.infrastructure.logging import log_exception_silently

            # SDK 예외를 구체적으로 처리
            if isinstance(e, CLINotFoundError):
                self.logger.error("Claude Code CLI가 설치되지 않았습니다")
                yield (
                    "\n[시스템 오류] Claude Code CLI가 설치되지 않았습니다.\n"
                    "설치 방법: npm install -g @anthropic-ai/claude-code"
                )

            elif isinstance(e, ProcessError):
                exit_code = getattr(e, 'exit_code', 'unknown')
                self.logger.error(
                    f"Claude CLI 프로세스 실행 실패: exit_code={exit_code}"
                )
                yield (
                    f"\n[시스템 오류] Claude CLI 프로세스 실행 실패 "
                    f"(exit_code: {exit_code})\n에러 로그를 확인해주세요."
                )

            elif isinstance(e, CLIJSONDecodeError):
                self.logger.error(f"Claude CLI 응답 파싱 실패: {e}")
                yield (
                    "\n[시스템 오류] Claude CLI 응답을 파싱할 수 없습니다. "
                    "CLI 버전을 확인해주세요."
                )

            elif isinstance(e, ClaudeSDKError):
                log_exception_silently(
                    self.logger,
                    e,
                    "Claude SDK 에러 발생",
                    model=self.config.model
                )
                yield (
                    "\n[시스템 오류] Claude SDK 실행 중 오류가 발생했습니다. "
                    "에러 로그를 확인해주세요."
                )

            else:
                # 기타 예상하지 못한 에러
                log_exception_silently(
                    self.logger,
                    e,
                    "Manager SDK execution failed (unknown error)",
                    model=self.config.model
                )
                yield (
                    f"\n[시스템 오류] 예상하지 못한 오류가 발생했습니다: "
                    f"{type(e).__name__}"
                )

        finally:
            # 리소스 정리
            if client is not None and not cleanup_done:
                try:
                    await client.disconnect()
                    cleanup_done = True
                    self.logger.debug("Client connection closed successfully")
                except Exception as e:
                    self.logger.debug("Client disconnect failed (ignored)", error=str(e))


class WorkerSDKExecutor:
    """Worker용 SDK 실행 래퍼.

    query() 함수를 사용하여 스트리밍 응답을 처리합니다.
    """

    def __init__(
        self,
        config: SDKExecutionConfig,
        allowed_tools: list[str],
        response_handler: WorkerResponseHandler,
        worker_name: Optional[str] = None
    ):
        """초기화.

        Args:
            config: SDK 실행 설정
            allowed_tools: 허용된 도구 목록
            response_handler: 응답 핸들러
            worker_name: Worker 이름 (로깅용)
        """
        self.config = config
        self.allowed_tools = allowed_tools
        self.response_handler = response_handler
        self.worker_name = worker_name or "Unknown"
        self.logger = get_logger(__name__, component=self.worker_name)

    async def execute_stream(self, prompt: str) -> AsyncIterator[str]:
        """스트림 실행.

        Args:
            prompt: 프롬프트

        Yields:
            str: 응답 텍스트 청크

        Raises:
            WorkerExecutionError: SDK 실행 중 에러 발생 시
        """
        from claude_agent_sdk import query
        from claude_agent_sdk.types import ClaudeAgentOptions

        try:
            self.logger.info(
                f"[{self.worker_name}] Claude Agent SDK 실행 시작",
                model=self.config.model,
                allowed_tools_count=len(self.allowed_tools)
            )

            chunk_count = 0
            last_response = None

            # ClaudeAgentOptions 생성
            options_dict = {
                "model": self.config.model,
                "allowed_tools": self.allowed_tools if self.allowed_tools else [],
                "cli_path": self.config.cli_path,
                "permission_mode": self.config.permission_mode
            }

            # 선택적 컨텍스트 관리 옵션 추가 (None이 아니면)
            if self.config.max_turns is not None:
                options_dict["max_turns"] = self.config.max_turns
            if self.config.continue_conversation:
                options_dict["continue_conversation"] = self.config.continue_conversation
            if self.config.setting_sources:
                options_dict["setting_sources"] = self.config.setting_sources

            # System Prompt 명시적 설정 (SDK Best Practice)
            # ClaudeAgentOptions에서 system_prompt를 직접 지원하지 않으므로
            # 프롬프트에 포함하여 전달 (현재 방식 유지)
            # 참고: system_prompt는 WorkerAgent._load_system_prompt()에서 이미 포함됨

            async for response in query(
                prompt=prompt,
                options=ClaudeAgentOptions(**options_dict)
            ):
                chunk_count += 1
                last_response = response  # 마지막 응답 저장

                self.logger.info(
                    f"[{self.worker_name}] response #{chunk_count} 수신: "
                    f"{type(response).__name__}"
                )

                async for text in self.response_handler.process_response(response):
                    yield text

            self.logger.info(
                f"[{self.worker_name}] Claude Agent SDK 실행 완료. "
                f"총 {chunk_count}개 청크 수신"
            )

            # 마지막 응답에서 usage 정보 재확인
            if last_response:
                self.logger.info(f"[{self.worker_name}] Checking last response for usage...")
                if hasattr(last_response, 'usage') and last_response.usage:
                    self.logger.info(f"[{self.worker_name}] Last response has usage: {last_response.usage}")
                    # 한 번 더 process_response 호출 (usage만 처리)
                    async for _ in self.response_handler.process_response(last_response):
                        pass  # 텍스트는 무시하고 usage만 수집
                else:
                    self.logger.warning(f"[{self.worker_name}] Last response has no usage information")

        except Exception as e:
            from src.infrastructure.logging import log_exception_silently

            # SDK 예외를 구체적으로 처리
            if isinstance(e, CLINotFoundError):
                self.logger.error("Claude Code CLI가 설치되지 않았습니다")
                yield (
                    "\n[시스템 오류] Claude Code CLI가 설치되지 않았습니다.\n"
                    "설치 방법: npm install -g @anthropic-ai/claude-code"
                )

            elif isinstance(e, ProcessError):
                exit_code = getattr(e, 'exit_code', 'unknown')
                self.logger.error(
                    f"Claude CLI 프로세스 실행 실패: exit_code={exit_code}",
                    worker_name=self.worker_name
                )
                yield (
                    f"\n[시스템 오류] Claude CLI 프로세스 실행 실패 "
                    f"(exit_code: {exit_code})\n에러 로그를 확인해주세요."
                )

            elif isinstance(e, CLIJSONDecodeError):
                self.logger.error(
                    f"Claude CLI 응답 파싱 실패: {e}",
                    worker_name=self.worker_name
                )
                yield (
                    "\n[시스템 오류] Claude CLI 응답을 파싱할 수 없습니다. "
                    "CLI 버전을 확인해주세요."
                )

            elif isinstance(e, ClaudeSDKError):
                log_exception_silently(
                    self.logger,
                    e,
                    f"Claude SDK 에러 발생 ({self.worker_name})",
                    worker_name=self.worker_name,
                    model=self.config.model
                )
                yield (
                    f"\n[시스템 오류] {self.worker_name} Worker SDK 실행 중 "
                    f"오류가 발생했습니다. 에러 로그를 확인해주세요."
                )

            else:
                # 기타 예상하지 못한 에러
                log_exception_silently(
                    self.logger,
                    e,
                    f"Worker Agent ({self.worker_name}) execution failed (unknown error)",
                    worker_name=self.worker_name,
                    model=self.config.model
                )
                yield (
                    f"\n[시스템 오류] {self.worker_name} Worker 실행 중 "
                    f"예상하지 못한 오류가 발생했습니다: {type(e).__name__}"
                )
