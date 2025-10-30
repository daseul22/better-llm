"""
Agent SDK 실행 래퍼 모듈.

클라이언트 코드의 중복을 제거하기 위한 Template Method Pattern 기반 Executor.
"""

import json
from dataclasses import dataclass
from typing import AsyncIterator, Callable, Optional, Any, List, Awaitable
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
    ClaudeSDKError,
    ClaudeSDKClient
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
            text_parts = []
            for i, content_block in enumerate(response.content):
                # TextBlock: 일반 텍스트 응답
                if isinstance(content_block, TextBlock):
                    logger.debug(f"Extracted text from TextBlock #{i}")
                    text_parts.append(content_block.text)

                # ThinkingBlock: Extended Thinking 모드의 사고 과정
                # JSON 형식으로 직렬화하여 프론트엔드에서 파싱 가능하도록 전달
                elif isinstance(content_block, ThinkingBlock):
                    if hasattr(content_block, 'thinking') and content_block.thinking:
                        logger.debug(
                            f"🧠 ThinkingBlock detected (#{i})",
                            length=len(content_block.thinking),
                            preview=content_block.thinking[:100] + "..." if len(content_block.thinking) > 100 else content_block.thinking
                        )
                        # JSON 형식으로 직렬화하여 프론트엔드로 전달
                        thinking_json = json.dumps({
                            "role": "assistant",
                            "content": [{
                                "type": "thinking",
                                "thinking": content_block.thinking
                            }]
                        }, ensure_ascii=False)
                        text_parts.append(thinking_json)

                # ToolUseBlock: 도구 호출 정보 (JSON 형식)
                elif isinstance(content_block, ToolUseBlock):
                    logger.debug(f"Found ToolUseBlock #{i}: {content_block.name}")
                    # JSON 형식으로 직렬화하여 프론트엔드에서 파싱 가능하도록

                    # tool_input 안전하게 추출
                    tool_input = {}
                    if hasattr(content_block, 'input'):
                        try:
                            # Pydantic 모델인 경우
                            if hasattr(content_block.input, 'model_dump'):
                                tool_input = content_block.input.model_dump()
                            elif hasattr(content_block.input, 'dict'):
                                tool_input = content_block.input.dict()
                            elif isinstance(content_block.input, dict):
                                tool_input = content_block.input
                            else:
                                tool_input = {"value": str(content_block.input)}
                        except Exception:
                            tool_input = {"value": str(content_block.input)}

                    tool_json = json.dumps({
                        "role": "assistant",
                        "content": [{
                            "type": "tool_use",
                            "id": content_block.id,
                            "name": content_block.name,
                            "input": tool_input
                        }]
                    }, ensure_ascii=False)
                    text_parts.append(tool_json)

                # ToolResultBlock: 도구 실행 결과 (JSON 형식)
                elif isinstance(content_block, ToolResultBlock):
                    logger.debug(f"Found ToolResultBlock #{i}: tool_use_id={content_block.tool_use_id}")

                    # Tool 결과 추출
                    tool_result = None
                    if hasattr(content_block, 'content'):
                        # content가 리스트인 경우 (TextBlock 등)
                        if isinstance(content_block.content, list):
                            result_parts = []
                            for result_block in content_block.content:
                                if isinstance(result_block, TextBlock):
                                    result_parts.append(result_block.text)
                                elif hasattr(result_block, 'text'):
                                    result_parts.append(result_block.text)
                            tool_result = '\n'.join(result_parts) if result_parts else None
                        # content가 문자열인 경우
                        elif isinstance(content_block.content, str):
                            tool_result = content_block.content

                    # 결과가 없으면 빈 문자열
                    if tool_result is None:
                        tool_result = ""

                    tool_result_json = json.dumps({
                        "role": "user",
                        "content": [{
                            "type": "tool_result",
                            "tool_use_id": content_block.tool_use_id,
                            "content": tool_result
                        }]
                    }, ensure_ascii=False)
                    text_parts.append(tool_result_json)

                # 폴백: hasattr로 type='tool_use' 체크 (하위 호환성)
                elif hasattr(content_block, 'type') and content_block.type == 'tool_use':
                    logger.debug(f"Found tool_use block (fallback) #{i}")

                    # tool_input 안전하게 추출
                    tool_input = {}
                    raw_input = getattr(content_block, 'input', {})
                    try:
                        if hasattr(raw_input, 'model_dump'):
                            tool_input = raw_input.model_dump()
                        elif hasattr(raw_input, 'dict'):
                            tool_input = raw_input.dict()
                        elif isinstance(raw_input, dict):
                            tool_input = raw_input
                        else:
                            tool_input = {"value": str(raw_input)}
                    except Exception:
                        tool_input = {"value": str(raw_input)}

                    tool_json = json.dumps({
                        "role": "assistant",
                        "content": [{
                            "type": "tool_use",
                            "id": getattr(content_block, 'id', 'unknown'),
                            "name": getattr(content_block, 'name', 'unknown'),
                            "input": tool_input
                        }]
                    }, ensure_ascii=False)
                    text_parts.append(tool_json)

            # 텍스트 파트들을 결합하여 반환
            if text_parts:
                return '\n'.join(text_parts)

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

        # [3단계] UserMessage 처리
        # 사용자 입력 메시지 (대화 히스토리에 포함될 수 있음)
        elif isinstance(response, UserMessage):
            if not response.content:
                logger.debug("UserMessage has no content")
                return None

            # content가 문자열인 경우
            if isinstance(response.content, str):
                logger.debug("Extracted text from UserMessage (string content)")
                return response.content

            # content가 리스트인 경우 (blocks)
            if isinstance(response.content, list):
                text_parts = []
                for i, content_block in enumerate(response.content):
                    if isinstance(content_block, TextBlock):
                        logger.debug(f"Extracted text from UserMessage TextBlock #{i}")
                        text_parts.append(content_block.text)

                    # ToolResultBlock: 도구 실행 결과 (UserMessage에 포함될 수 있음)
                    elif isinstance(content_block, ToolResultBlock):
                        logger.debug(f"Found ToolResultBlock in UserMessage #{i}: tool_use_id={content_block.tool_use_id}")

                        # Tool 결과 추출
                        tool_result = None
                        if hasattr(content_block, 'content'):
                            if isinstance(content_block.content, list):
                                result_parts = []
                                for result_block in content_block.content:
                                    if isinstance(result_block, TextBlock):
                                        result_parts.append(result_block.text)
                                    elif hasattr(result_block, 'text'):
                                        result_parts.append(result_block.text)
                                tool_result = '\n'.join(result_parts) if result_parts else None
                            elif isinstance(content_block.content, str):
                                tool_result = content_block.content

                        if tool_result is None:
                            tool_result = ""

                        tool_result_json = json.dumps({
                            "role": "user",
                            "content": [{
                                "type": "tool_result",
                                "tool_use_id": content_block.tool_use_id,
                                "content": tool_result
                            }]
                        }, ensure_ascii=False)
                        text_parts.append(tool_result_json)

                if text_parts:
                    return '\n'.join(text_parts)

            logger.debug("UserMessage has no extractable text content")
            return None

        # [4단계] SystemMessage 처리
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

        # [5단계] 폴백 처리 (하위 호환성)
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

    def extract_final_output_from_response(self, response: Any) -> Optional[str]:
        """
        SDK 응답 객체에서 **최종 표준 출력**만 추출 (TextBlock만).

        다음 노드로 전달할 출력을 추출합니다.
        ThinkingBlock, ToolUseBlock, ToolResultBlock은 제외됩니다.

        Args:
            response: SDK 응답 객체

        Returns:
            str: 최종 표준 출력 (TextBlock만) 또는 None
        """
        if isinstance(response, AssistantMessage):
            if not response.content:
                return None

            # TextBlock만 추출
            text_parts = []
            for content_block in response.content:
                if isinstance(content_block, TextBlock):
                    text_parts.append(content_block.text)

            if text_parts:
                return "".join(text_parts)

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
            logger.info(f"⚠️  [{context}] Failed to extract usage from: {type(usage_obj)}")
            return None


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
        # [3단계] UserMessage 처리 (사용자 입력 메시지)
        # ====================================================================
        if isinstance(response, UserMessage):
            logger.debug("[Worker] Processing UserMessage")

            # UserMessage는 usage 정보가 없을 수 있으므로 확인 후 처리
            if hasattr(response, 'usage') and response.usage and self.usage_callback:
                usage_dict = self.extract_usage_info(response.usage, context="Worker")
                if usage_dict:
                    logger.info(f"[Worker] Token usage (UserMessage): {usage_dict}")
                    self.usage_callback(usage_dict)

            # 텍스트 추출 및 yield
            text = self.extract_text_from_response(response)
            if text:
                yield text
            return

        # ====================================================================
        # [4단계] SystemMessage 처리 (시스템 메타데이터)
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
        # [5단계] 폴백 처리 (알 수 없는 응답 타입)
        # ====================================================================
        logger.info(f"⚠️  [Worker] Unknown response type: {type(response).__name__}")

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
        self.last_session_id: Optional[str] = None  # 마지막 실행의 세션 ID 저장

    async def execute_stream(
        self,
        prompt: str,
        resume_session_id: Optional[str] = None,
        user_input_callback: Optional[Callable[[str], Awaitable[str]]] = None
    ) -> AsyncIterator[str]:
        """스트림 실행 (연속 대화 지원).

        Args:
            prompt: 프롬프트
            resume_session_id: 재개할 SDK 세션 ID (선택, 이전 실행의 컨텍스트 유지)
            user_input_callback: 사용자 입력이 필요할 때 호출되는 async 함수
                                 질문(str)을 받아서 답변(str)을 반환해야 함

        Yields:
            str: 응답 텍스트 청크

        Raises:
            WorkerExecutionError: SDK 실행 중 에러 발생 시

        Note:
            Worker가 "@ASK_USER: 질문내용" 패턴으로 출력하면
            user_input_callback이 호출되어 사용자 입력을 받고,
            같은 세션에서 대화를 계속 진행합니다.
        """
        from claude_agent_sdk.types import ClaudeAgentOptions

        try:
            self.logger.info(
                f"[{self.worker_name}] Claude Agent SDK 실행 시작",
                model=self.config.model,
                allowed_tools_count=len(self.allowed_tools),
                resume_session=resume_session_id[:8] + "..." if resume_session_id and len(resume_session_id) > 8 else resume_session_id
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
            if self.config.setting_sources:
                options_dict["setting_sources"] = self.config.setting_sources

            # resume_session_id가 주어진 경우 이전 세션 재개
            if resume_session_id:
                options_dict["resume"] = resume_session_id
                self.logger.info(
                    f"[{self.worker_name}] 이전 세션 재개: {resume_session_id[:8]}... "
                    f"(대화 컨텍스트 유지)"
                )
            else:
                self.logger.info(
                    f"[{self.worker_name}] 새 세션 시작"
                )

            # ClaudeSDKClient를 context manager로 사용 (자동 connect/disconnect)
            async with ClaudeSDKClient(options=ClaudeAgentOptions(**options_dict)) as client:
                current_prompt = prompt
                conversation_turn = 0
                max_conversation_turns = 10  # 무한 루프 방지

                while conversation_turn < max_conversation_turns:
                    conversation_turn += 1
                    self.logger.info(
                        f"[{self.worker_name}] 대화 턴 {conversation_turn} 시작"
                    )

                    # query 메서드로 질의 전송
                    await client.query(prompt=current_prompt)

                    # 응답 수집을 위한 버퍼
                    collected_texts = []

                    # receive_response()로 응답 스트리밍 수신
                    async for response in client.receive_response():
                        chunk_count += 1
                        last_response = response  # 마지막 응답 저장

                        self.logger.info(
                            f"[{self.worker_name}] response #{chunk_count} 수신: "
                            f"{type(response).__name__}"
                        )

                        # 첫 응답에서 실제 SDK 세션 ID 추출 (session_id 필드가 있으면)
                        if chunk_count == 1:
                            if hasattr(response, 'session_id') and response.session_id:
                                self.last_session_id = response.session_id
                                self.logger.info(
                                    f"[{self.worker_name}] ✓ SDK 세션 ID 저장 성공: {self.last_session_id[:8]}..."
                                )
                            else:
                                self.logger.warning(
                                    f"[{self.worker_name}] ⚠️ 첫 응답에 session_id가 없습니다. "
                                    "추가 프롬프트 기능을 사용할 수 없습니다."
                                )

                        # 응답 처리하면서 텍스트 수집
                        async for text in self.response_handler.process_response(response):
                            collected_texts.append(text)
                            yield text

                    # 전체 응답 확인
                    full_response = "".join(collected_texts)

                    # 사용자 입력 요청 패턴 확인
                    if "@ASK_USER:" in full_response and user_input_callback:
                        question = self._extract_question_from_response(full_response)
                        self.logger.info(
                            f"[{self.worker_name}] 사용자 입력 요청 감지: {question[:50]}..."
                        )

                        try:
                            # 특수 이벤트 마커 전송 (workflow_executor가 감지하여 이벤트 생성)
                            import json as json_module
                            event_marker = "@EVENT:user_input_request:" + json_module.dumps({"question": question}, ensure_ascii=False)
                            yield event_marker

                            # 사용자 입력 받기 (Queue 대기)
                            user_answer = await user_input_callback(question)
                            self.logger.info(
                                f"[{self.worker_name}] 사용자 답변 수신: {user_answer[:50]}..."
                            )

                            # 다음 프롬프트로 설정
                            current_prompt = user_answer

                            # 대화 구분자 출력
                            yield f"\n\n{'='*60}\n💬 사용자 답변: {user_answer}\n{'='*60}\n\n"

                            # 루프 계속
                            continue

                        except Exception as e:
                            self.logger.error(
                                f"[{self.worker_name}] 사용자 입력 처리 중 에러: {e}"
                            )
                            # 에러 발생 시 대화 종료
                            break
                    else:
                        # 사용자 입력 요청 없음 → 대화 종료
                        break

                self.logger.info(
                    f"[{self.worker_name}] Claude Agent SDK 실행 완료. "
                    f"총 {chunk_count}개 청크, {conversation_turn}개 대화 턴"
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
                        self.logger.info(f"⚠️  [{self.worker_name}] Last response has no usage information")

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

    def _extract_question_from_response(self, response: str) -> str:
        """응답에서 사용자 입력 요청 질문 추출.

        Args:
            response: Worker의 전체 응답 텍스트

        Returns:
            str: 추출된 질문 (패턴이 없으면 전체 응답 반환)

        Note:
            "@ASK_USER: 질문내용" 패턴에서 질문을 추출합니다.
            여러 개의 패턴이 있으면 마지막 것을 사용합니다.
        """
        marker = "@ASK_USER:"
        if marker not in response:
            return response.strip()

        # 마지막 @ASK_USER 위치 찾기
        last_index = response.rfind(marker)
        question_start = last_index + len(marker)

        # 질문 추출 (다음 줄바꿈 또는 끝까지)
        question = response[question_start:].strip()

        # 다음 마커가 있으면 그 전까지만
        next_marker_index = question.find("@")
        if next_marker_index > 0:
            question = question[:next_marker_index].strip()

        return question if question else response.strip()
