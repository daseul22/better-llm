"""
Worker Tools 디버깅 테스트
"""

import asyncio
from pathlib import Path

from src.worker_tools import initialize_workers, create_worker_tools_server
from claude_agent_sdk import ClaudeSDKClient
from claude_agent_sdk.types import ClaudeAgentOptions


async def test_worker_tools():
    """Worker Tools MCP Server 테스트"""
    print("🔧 Worker Tools 초기화 중...")

    # Worker Agent들 초기화
    config_path = Path("config/agent_config.json")
    initialize_workers(config_path)

    # Worker Tools MCP Server 생성
    worker_tools_server = create_worker_tools_server()
    print(f"✅ Worker Tools MCP Server 생성 완료: {worker_tools_server}")

    # ClaudeSDKClient로 테스트
    print("\n🤖 ClaudeSDKClient 테스트 시작...")

    options = ClaudeAgentOptions(
        model="claude-sonnet-4-5-20250929",
        mcp_servers={"workers": worker_tools_server},
        allowed_tools=[
            "mcp__workers__execute_planner_task",
            "mcp__workers__execute_coder_task",
            "mcp__workers__execute_tester_task"
        ],
        cli_path="/Users/simdaseul/.claude/local/claude",
        permission_mode="bypassPermissions"
    )

    print(f"📋 Options: {options}")

    try:
        async with ClaudeSDKClient(options=options) as client:
            print("✅ ClaudeSDKClient 생성 완료")

            # 간단한 프롬프트 전송
            prompt = "execute_planner_task 툴을 사용해서 '간단한 Hello World 함수 작성' 계획을 세워주세요."
            print(f"\n📤 프롬프트 전송: {prompt}")

            await client.query(prompt)
            print("✅ 프롬프트 전송 완료")

            # 응답 수신
            print("\n📥 응답 수신 중...")
            async for msg in client.receive_response():
                print(f"응답: {msg}")

    except Exception as e:
        print(f"❌ 에러 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_worker_tools())
