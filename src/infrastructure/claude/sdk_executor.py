"""
Agent SDK 실행 래퍼 모듈.

클라이언트 코드의 중복을 제거하기 위한 Template Method Pattern 기반 Executor.
"""

from dataclasses import dataclass
from typing import AsyncIterator, Callable, Optional, Any
from abc import ABC, abstractmethod

from domain.exceptions import WorkerExecutionError
from infrastructure.logging import get_logger

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
    """
    model: str = "claude-sonnet-4-5-20250929"
    max_tokens: int = 8000
    temperature: float = 0.7
    timeout: int = 300
    cli_path: Optional[str] = None
    permission_mode: str = "bypassPermissions"


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

    def extract_text_from_response(self, response: Any) -> Optional[str]:
        """응답 객체에서 텍스트 추출 (공통 로직).

        Args:
            response: SDK 응답 객체

        Returns:
            str: 추출된 텍스트 또는 None
        """
        # content 속성이 있는 경우
        if hasattr(response, 'content') and isinstance(response.content, list):
            for content in response.content:
                if hasattr(content, 'text') and content.text:
                    return content.text

        # text 속성이 직접 있는 경우
        elif hasattr(response, 'text') and isinstance(response.text, str):
            return response.text

        return None


class ManagerResponseHandler(SDKResponseHandler):
    """Manager Client용 응답 핸들러.

    ClaudeSDKClient의 receive_response()에서 반환된 응답을 처리합니다.
    텍스트 콘텐츠만 추출하여 yield하고, usage 정보는 콜백으로 전달합니다.
    """

    def __init__(self, usage_callback: Optional[Callable[[dict], None]] = None):
        """초기화.

        Args:
            usage_callback: 토큰 사용량 정보를 받을 콜백 함수
        """
        self.usage_callback = usage_callback

    async def process_response(self, response: Any) -> AsyncIterator[str]:
        """응답 처리 및 텍스트 추출.

        Args:
            response: ClaudeSDKClient.receive_response()의 응답 객체

        Yields:
            str: 추출된 텍스트 청크
        """
        # usage 정보 추출 및 콜백 호출
        if hasattr(response, 'usage') and response.usage and self.usage_callback:
            usage_dict = {}
            if hasattr(response.usage, 'input_tokens'):
                usage_dict['input_tokens'] = response.usage.input_tokens
            if hasattr(response.usage, 'output_tokens'):
                usage_dict['output_tokens'] = response.usage.output_tokens
            if hasattr(response.usage, 'cache_read_tokens'):
                usage_dict['cache_read_tokens'] = response.usage.cache_read_tokens
            if hasattr(response.usage, 'cache_creation_tokens'):
                usage_dict['cache_creation_tokens'] = response.usage.cache_creation_tokens

            if usage_dict:
                self.usage_callback(usage_dict)

        # 텍스트 추출
        text = self.extract_text_from_response(response)
        if text:
            yield text


class WorkerResponseHandler(SDKResponseHandler):
    """Worker Client용 응답 핸들러.

    query() 함수의 스트리밍 응답을 처리합니다.
    """

    async def process_response(self, response: Any) -> AsyncIterator[str]:
        """응답 처리 및 텍스트 추출.

        Args:
            response: query() 함수의 응답 객체

        Yields:
            str: 추출된 텍스트 청크
        """
        # 텍스트 추출
        text = self.extract_text_from_response(response)
        if text:
            yield text
        else:
            # 예상과 다른 형식일 경우 문자열 변환
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
        session_id: Optional[str] = None
    ):
        """초기화.

        Args:
            config: SDK 실행 설정
            mcp_servers: MCP 서버 딕셔너리
            allowed_tools: 허용된 도구 목록
            response_handler: 응답 핸들러
            session_id: 세션 ID (로깅용)
        """
        self.config = config
        self.mcp_servers = mcp_servers
        self.allowed_tools = allowed_tools
        self.response_handler = response_handler
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
            options = ClaudeAgentOptions(
                model=self.config.model,
                mcp_servers=self.mcp_servers,
                allowed_tools=self.allowed_tools,
                cli_path=self.config.cli_path,
                permission_mode=self.config.permission_mode
            )

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

        except GeneratorExit:
            # Generator가 중간에 종료될 때는 cleanup 하지 않음
            self.logger.debug("Generator exit - cleanup skipped")
            raise

        except Exception as e:
            from src.infrastructure.logging import log_exception_silently
            log_exception_silently(
                self.logger,
                e,
                "Manager SDK execution failed",
                model=self.config.model
            )
            yield f"\n[시스템 오류] Manager SDK 실행 중 오류가 발생했습니다. 에러 로그를 확인해주세요."

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
            async for response in query(
                prompt=prompt,
                options=ClaudeAgentOptions(
                    model=self.config.model,
                    allowed_tools=self.allowed_tools if self.allowed_tools else [],
                    cli_path=self.config.cli_path,
                    permission_mode=self.config.permission_mode
                )
            ):
                chunk_count += 1
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

        except Exception as e:
            from src.infrastructure.logging import log_exception_silently
            log_exception_silently(
                self.logger,
                e,
                f"Worker Agent ({self.worker_name}) execution failed",
                worker_name=self.worker_name,
                model=self.config.model
            )
            yield (
                f"\n[시스템 오류] {self.worker_name} Worker 실행 중 오류가 발생했습니다. "
                f"에러 로그를 확인해주세요."
            )
