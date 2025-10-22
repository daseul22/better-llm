"""
Agent SDK 실행 래퍼 모듈.

클라이언트 코드의 중복을 제거하기 위한 Template Method Pattern 기반 Executor.
"""

from dataclasses import dataclass
from typing import AsyncIterator, Callable, Optional, Any
from abc import ABC, abstractmethod

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
    """
    model: str = "claude-sonnet-4-5-20250929"
    max_tokens: int = 8000
    temperature: float = 0.7
    timeout: int = 600
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
        # 디버깅: 응답 객체 구조 로깅
        logger.info(f"[Manager] Response type: {type(response).__name__}")
        logger.info(f"[Manager] Response repr: {repr(response)[:500]}")

        # 모든 속성 확인
        response_attrs = [attr for attr in dir(response) if not attr.startswith('_')]
        logger.info(f"[Manager] Response public attributes: {response_attrs}")

        logger.info(f"[Manager] Has usage: {hasattr(response, 'usage')}")

        if hasattr(response, 'usage'):
            logger.info(f"[Manager] usage type: {type(response.usage)}")
            logger.info(f"[Manager] usage value: {response.usage}")
            logger.info(f"[Manager] usage repr: {repr(response.usage)}")
            if response.usage:
                usage_attrs = [attr for attr in dir(response.usage) if not attr.startswith('_')]
                logger.info(f"[Manager] usage attributes: {usage_attrs}")

        # usage 정보 추출 및 콜백 호출
        if hasattr(response, 'usage') and response.usage and self.usage_callback:
            usage_dict = {}

            # usage가 dict인 경우와 object인 경우 모두 지원
            if isinstance(response.usage, dict):
                # Dictionary인 경우: 직접 접근
                usage_dict['input_tokens'] = response.usage.get('input_tokens', 0)
                usage_dict['output_tokens'] = response.usage.get('output_tokens', 0)
                usage_dict['cache_read_tokens'] = response.usage.get('cache_read_input_tokens', 0)  # 키 이름 주의!
                usage_dict['cache_creation_tokens'] = response.usage.get('cache_creation_input_tokens', 0)  # 키 이름 주의!
            else:
                # Object인 경우: 속성 접근
                if hasattr(response.usage, 'input_tokens'):
                    usage_dict['input_tokens'] = response.usage.input_tokens
                if hasattr(response.usage, 'output_tokens'):
                    usage_dict['output_tokens'] = response.usage.output_tokens
                if hasattr(response.usage, 'cache_read_tokens'):
                    usage_dict['cache_read_tokens'] = response.usage.cache_read_tokens
                if hasattr(response.usage, 'cache_creation_tokens'):
                    usage_dict['cache_creation_tokens'] = response.usage.cache_creation_tokens

            if usage_dict:
                logger.info(f"[Manager] Token usage received: {usage_dict}")
                self.usage_callback(usage_dict)
            else:
                logger.warning("[Manager] usage_dict is empty after extraction")
        else:
            # 디버깅: usage 정보가 없는 이유 확인
            if not hasattr(response, 'usage'):
                logger.warning("[Manager] Response has no 'usage' attribute")
            elif not response.usage:
                logger.warning(f"[Manager] Response.usage is None/False: {response.usage}")
            elif not self.usage_callback:
                logger.warning("[Manager] No usage_callback provided")

        # 텍스트 추출
        text = self.extract_text_from_response(response)
        if text:
            yield text


class WorkerResponseHandler(SDKResponseHandler):
    """Worker Client용 응답 핸들러.

    query() 함수의 스트리밍 응답을 처리합니다.
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
            response: query() 함수의 응답 객체

        Yields:
            str: 추출된 텍스트 청크
        """
        # 디버깅: 응답 객체 구조 로깅
        logger.debug(f"[Worker] Response type: {type(response)}")
        logger.debug(f"[Worker] Has usage: {hasattr(response, 'usage')}")

        if hasattr(response, 'usage'):
            logger.debug(f"[Worker] usage value: {response.usage}")

        # usage 정보 추출 및 콜백 호출 (Manager와 동일)
        if hasattr(response, 'usage') and response.usage and self.usage_callback:
            usage_dict = {}

            # usage가 dict인 경우와 object인 경우 모두 지원
            if isinstance(response.usage, dict):
                # Dictionary인 경우: 직접 접근
                usage_dict['input_tokens'] = response.usage.get('input_tokens', 0)
                usage_dict['output_tokens'] = response.usage.get('output_tokens', 0)
                usage_dict['cache_read_tokens'] = response.usage.get('cache_read_input_tokens', 0)  # 키 이름 주의!
                usage_dict['cache_creation_tokens'] = response.usage.get('cache_creation_input_tokens', 0)  # 키 이름 주의!
            else:
                # Object인 경우: 속성 접근
                if hasattr(response.usage, 'input_tokens'):
                    usage_dict['input_tokens'] = response.usage.input_tokens
                if hasattr(response.usage, 'output_tokens'):
                    usage_dict['output_tokens'] = response.usage.output_tokens
                if hasattr(response.usage, 'cache_read_tokens'):
                    usage_dict['cache_read_tokens'] = response.usage.cache_read_tokens
                if hasattr(response.usage, 'cache_creation_tokens'):
                    usage_dict['cache_creation_tokens'] = response.usage.cache_creation_tokens

            if usage_dict:
                logger.info(f"[Worker] Token usage received: {usage_dict}")
                self.usage_callback(usage_dict)
            else:
                logger.warning("[Worker] usage_dict is empty after extraction")
        else:
            # 디버깅: usage 정보가 없는 이유 확인
            if not hasattr(response, 'usage'):
                logger.warning("[Worker] Response has no 'usage' attribute")
            elif not response.usage:
                logger.warning(f"[Worker] Response.usage is None/False: {response.usage}")
            elif not self.usage_callback:
                logger.warning("[Worker] No usage_callback provided")

        # 텍스트 추출
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
                        if hasattr(client.usage, 'input_tokens'):
                            usage_dict['input_tokens'] = client.usage.input_tokens
                        if hasattr(client.usage, 'output_tokens'):
                            usage_dict['output_tokens'] = client.usage.output_tokens
                        if hasattr(client.usage, 'cache_read_tokens'):
                            usage_dict['cache_read_tokens'] = client.usage.cache_read_tokens
                        if hasattr(client.usage, 'cache_creation_tokens'):
                            usage_dict['cache_creation_tokens'] = client.usage.cache_creation_tokens

                    if usage_dict:
                        self.logger.info(f"[Manager] Found usage in client: {usage_dict}")
                        self.response_handler.usage_callback(usage_dict)

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
            last_response = None

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
