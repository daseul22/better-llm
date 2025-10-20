#!/usr/bin/env python3
"""
Claude Agent SDK query() 함수 테스트.

test_query_auth.py, test_query_simple.py를 통합한 파일입니다.
"""

import asyncio
import os

import pytest
from dotenv import load_dotenv
from claude_agent_sdk import query
from claude_agent_sdk.types import ClaudeAgentOptions


@pytest.fixture(scope="module")
def load_env():
    """환경변수를 로드합니다."""
    load_dotenv()


@pytest.mark.asyncio
async def test_query_authentication(load_env):
    """
    Claude Agent SDK query() 함수가 올바르게 인증되는지 테스트합니다.

    환경변수 ANTHROPIC_API_KEY 또는 CLAUDE_CODE_OAUTH_TOKEN이 필요합니다.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    oauth_token = os.getenv("CLAUDE_CODE_OAUTH_TOKEN")

    # 최소 하나의 인증 방식이 설정되어 있어야 함
    assert api_key or oauth_token, (
        "ANTHROPIC_API_KEY 또는 CLAUDE_CODE_OAUTH_TOKEN 환경변수가 설정되어야 합니다"
    )


@pytest.mark.asyncio
async def test_simple_query(load_env):
    """가장 간단한 query() 호출 테스트입니다."""
    prompt = "간단한 테스트입니다. 'OK'라고만 응답해주세요."

    response_count = 0
    full_response = ""

    async for response in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            model="claude-sonnet-4-5-20250929",
            allowed_tools=[],
            cli_path=os.path.expanduser("~/.claude/local/claude"),
            permission_mode="bypassPermissions"
        )
    ):
        response_count += 1

        # 응답에서 텍스트 추출
        if hasattr(response, "content"):
            for content in response.content:
                if hasattr(content, "text"):
                    full_response += content.text
        elif hasattr(response, "text"):
            full_response += response.text

    # 검증
    assert response_count > 0, "응답을 받지 못했습니다"
    assert full_response, "응답 텍스트가 비어있습니다"


@pytest.mark.asyncio
async def test_query_with_tools(load_env):
    """query() 함수가 도구를 사용하는지 테스트합니다."""
    prompt = "현재 디렉토리에 있는 파일 목록을 보여주세요."

    response_count = 0
    full_response = ""

    async for response in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            model="claude-sonnet-4-5-20250929",
            allowed_tools=["read", "bash"],
            cli_path=os.path.expanduser("~/.claude/local/claude"),
            permission_mode="bypassPermissions"
        )
    ):
        response_count += 1

        # 응답에서 텍스트 추출
        if hasattr(response, "content"):
            for content in response.content:
                if hasattr(content, "text"):
                    full_response += content.text
        elif hasattr(response, "text"):
            full_response += response.text

    # 검증
    assert response_count > 0, "응답을 받지 못했습니다"
    assert full_response, "응답 텍스트가 비어있습니다"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
