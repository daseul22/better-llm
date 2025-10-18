"""
Worker Agent Tools - Worker Agent들을 Custom Tool로 래핑

각 Worker Agent를 Claude Agent SDK의 Custom Tool로 만들어,
Manager Agent가 필요할 때 호출할 수 있도록 합니다.
"""

from typing import Any, Dict
from pathlib import Path
import logging

from claude_agent_sdk import tool, create_sdk_mcp_server
from claude_agent_sdk.types import ClaudeAgentOptions

from .worker_agent import WorkerAgent
from .models import AgentConfig
from .utils import load_agent_config

logger = logging.getLogger(__name__)


# 전역 변수로 Worker Agent 인스턴스들을 저장
_WORKER_AGENTS: Dict[str, WorkerAgent] = {}


def initialize_workers(config_path: Path):
    """
    Worker Agent들을 초기화합니다.

    Args:
        config_path: Agent 설정 파일 경로
    """
    global _WORKER_AGENTS

    worker_configs = load_agent_config(config_path)

    for config in worker_configs:
        worker = WorkerAgent(config)
        _WORKER_AGENTS[config.name] = worker
        logger.info(f"✅ Worker Agent 초기화: {config.name} ({config.role})")


@tool(
    "execute_planner_task",
    "Planner Agent에게 작업을 할당합니다. 요구사항 분석 및 계획 수립을 담당합니다.",
    {"task_description": str}
)
async def execute_planner_task(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Planner Agent 실행

    Args:
        args: {"task_description": "작업 설명"}

    Returns:
        Agent 실행 결과
    """
    task = args["task_description"]
    logger.debug(f"[Planner Tool] 작업 실행: {task[:50]}...")

    worker = _WORKER_AGENTS.get("planner")
    if not worker:
        return {
            "content": [
                {"type": "text", "text": "❌ Planner Agent를 찾을 수 없습니다."}
            ]
        }

    try:
        # Worker Agent 실행 (스트리밍)
        result = ""
        async for chunk in worker.execute_task(task):
            result += chunk

        return {
            "content": [
                {"type": "text", "text": result}
            ]
        }
    except Exception as e:
        logger.error(f"[Planner Tool] 실행 실패: {e}")
        return {
            "content": [
                {"type": "text", "text": f"❌ Planner 실행 실패: {e}"}
            ]
        }


@tool(
    "execute_coder_task",
    "Coder Agent에게 작업을 할당합니다. 코드 작성, 수정, 리팩토링을 담당합니다.",
    {"task_description": str}
)
async def execute_coder_task(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Coder Agent 실행

    Args:
        args: {"task_description": "작업 설명"}

    Returns:
        Agent 실행 결과
    """
    task = args["task_description"]
    logger.debug(f"[Coder Tool] 작업 실행: {task[:50]}...")

    worker = _WORKER_AGENTS.get("coder")
    if not worker:
        return {
            "content": [
                {"type": "text", "text": "❌ Coder Agent를 찾을 수 없습니다."}
            ]
        }

    try:
        # Worker Agent 실행 (스트리밍)
        result = ""
        async for chunk in worker.execute_task(task):
            result += chunk

        return {
            "content": [
                {"type": "text", "text": result}
            ]
        }
    except Exception as e:
        logger.error(f"[Coder Tool] 실행 실패: {e}")
        return {
            "content": [
                {"type": "text", "text": f"❌ Coder 실행 실패: {e}"}
            ]
        }


@tool(
    "execute_tester_task",
    "Tester Agent에게 작업을 할당합니다. 테스트 작성 및 실행을 담당합니다.",
    {"task_description": str}
)
async def execute_tester_task(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tester Agent 실행

    Args:
        args: {"task_description": "작업 설명"}

    Returns:
        Agent 실행 결과
    """
    task = args["task_description"]
    logger.debug(f"[Tester Tool] 작업 실행: {task[:50]}...")

    worker = _WORKER_AGENTS.get("tester")
    if not worker:
        return {
            "content": [
                {"type": "text", "text": "❌ Tester Agent를 찾을 수 없습니다."}
            ]
        }

    try:
        # Worker Agent 실행 (스트리밍)
        result = ""
        async for chunk in worker.execute_task(task):
            result += chunk

        return {
            "content": [
                {"type": "text", "text": result}
            ]
        }
    except Exception as e:
        logger.error(f"[Tester Tool] 실행 실패: {e}")
        return {
            "content": [
                {"type": "text", "text": f"❌ Tester 실행 실패: {e}"}
            ]
        }


def create_worker_tools_server():
    """
    Worker Tool들을 포함하는 MCP 서버 생성

    Returns:
        MCP 서버 인스턴스
    """
    server = create_sdk_mcp_server(
        name="workers",
        version="1.0.0",
        tools=[
            execute_planner_task,
            execute_coder_task,
            execute_tester_task
        ]
    )

    logger.info("✅ Worker Tools MCP Server 생성 완료")

    return server
