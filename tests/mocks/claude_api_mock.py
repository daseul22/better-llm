"""
Mock Claude API for testing

이 모듈은 테스트를 위한 Mock Claude API를 제공합니다.
"""
import json
from typing import Dict, Any, List, Optional, AsyncIterator
from datetime import datetime


class MockClaudeAPI:
    """Claude API Mock Server"""

    def __init__(self):
        self.requests: List[Dict[str, Any]] = []
        self.response_delay = 0.1  # 100ms
        self._custom_responses: Dict[str, Any] = {}

    def create_message(
        self,
        model: str,
        messages: List[Dict],
        max_tokens: int = 4096,
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Mock /v1/messages endpoint

        Args:
            model: 모델 ID
            messages: 메시지 리스트
            max_tokens: 최대 토큰 수
            tools: 사용 가능한 도구 리스트
            **kwargs: 추가 파라미터

        Returns:
            Mock API 응답
        """
        self.requests.append({
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "tools": tools,
            "timestamp": datetime.now().isoformat()
        })

        # 커스텀 응답이 설정되어 있으면 반환
        if self._custom_responses:
            return self._custom_responses.copy()

        # 기본 응답
        return {
            "id": f"msg_mock_{len(self.requests)}",
            "type": "message",
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": "Mock response from Claude API"
                }
            ],
            "model": model,
            "stop_reason": "end_turn",
            "usage": {
                "input_tokens": 100,
                "output_tokens": 50
            }
        }

    async def create_message_stream(
        self,
        model: str,
        messages: List[Dict],
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Mock streaming endpoint

        Args:
            model: 모델 ID
            messages: 메시지 리스트
            **kwargs: 추가 파라미터

        Yields:
            Mock streaming events
        """
        self.requests.append({
            "model": model,
            "messages": messages,
            "stream": True,
            "timestamp": datetime.now().isoformat()
        })

        # Mock streaming events
        events = [
            {
                "type": "message_start",
                "message": {
                    "id": f"msg_mock_stream_{len(self.requests)}",
                    "type": "message",
                    "role": "assistant",
                    "model": model
                }
            },
            {
                "type": "content_block_start",
                "index": 0,
                "content_block": {"type": "text", "text": ""}
            },
            {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "text_delta", "text": "Mock "}
            },
            {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "text_delta", "text": "streaming "}
            },
            {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "text_delta", "text": "response"}
            },
            {
                "type": "content_block_stop",
                "index": 0
            },
            {
                "type": "message_stop"
            }
        ]

        for event in events:
            yield f"data: {json.dumps(event)}\n\n"

    def set_custom_response(self, response: Dict[str, Any]) -> None:
        """
        커스텀 응답 설정

        Args:
            response: 반환할 응답 딕셔너리
        """
        self._custom_responses = response

    def reset(self) -> None:
        """Reset mock state"""
        self.requests.clear()
        self._custom_responses.clear()


# Global mock instance
mock_claude_api = MockClaudeAPI()
