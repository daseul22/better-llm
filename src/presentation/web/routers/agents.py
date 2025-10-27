"""
Agent API 라우터

Worker Agent 목록 조회 및 실행을 위한 엔드포인트를 제공합니다.
"""

import asyncio
import uuid
from functools import lru_cache
from typing import AsyncIterator

from fastapi import APIRouter, HTTPException, Depends
from sse_starlette.sse import EventSourceResponse

from src.domain.models import AgentConfig
from src.infrastructure.config import JsonConfigLoader, get_project_root
from src.infrastructure.claude.worker_client import WorkerAgent
from src.infrastructure.logging import get_logger
from src.presentation.web.schemas.request import (
    AgentExecuteRequest,
    AgentListResponse,
    ErrorResponse,
)

logger = get_logger(__name__)
router = APIRouter(prefix="/api", tags=["agents"])


@lru_cache()
def get_config_loader() -> JsonConfigLoader:
    """
    JsonConfigLoader 싱글톤 인스턴스 반환 (FastAPI Depends + lru_cache)

    Returns:
        JsonConfigLoader: 스레드 안전한 싱글톤 인스턴스
    """
    project_root = get_project_root()
    return JsonConfigLoader(project_root)


@router.get("/agents", response_model=AgentListResponse)
async def list_agents(
    config_loader: JsonConfigLoader = Depends(get_config_loader)
) -> AgentListResponse:
    """
    사용 가능한 Worker Agent 목록 조회

    Args:
        config_loader: ConfigLoader 의존성 주입 (Depends)

    Returns:
        AgentListResponse: Agent 목록 (name, role, description)

    Example:
        GET /api/agents
        Response: {
            "agents": [
                {
                    "name": "planner",
                    "role": "계획 수립",
                    "description": "요구사항 분석 및 작업 계획 수립"
                },
                ...
            ]
        }
    """
    try:
        agent_configs = config_loader.load_agent_configs()

        agents = [
            {
                "name": config.name,
                "role": config.role,
                # description은 role을 사용 (JSON 설정에서 로드)
                "description": f"{config.role} 전문가",
            }
            for config in agent_configs
        ]

        logger.info(f"✅ Agent 목록 조회: {len(agents)}개")
        return AgentListResponse(agents=agents)

    except Exception as e:
        logger.error(f"❌ Agent 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"Agent 목록 조회 실패: {str(e)}")


async def _execute_worker_stream(
    agent_config: AgentConfig, task_description: str, session_id: str
) -> AsyncIterator[str]:
    """
    Worker Agent 실행 (스트리밍)

    Args:
        agent_config: Agent 설정
        task_description: 작업 설명
        session_id: 세션 ID

    Yields:
        str: Worker Agent 실행 결과 청크 (순수 텍스트)

    Raises:
        Exception: Agent 실행 실패 시
    """
    worker = None
    try:
        logger.info(f"[{session_id}] Worker 실행 시작: {agent_config.name}")

        # WorkerAgent 인스턴스 생성
        worker = WorkerAgent(config=agent_config)

        # 스트리밍 실행
        async for chunk in worker.execute_task(task_description):
            yield chunk

        logger.info(f"[{session_id}] Worker 실행 완료: {agent_config.name}")

    except Exception as e:
        error_msg = f"Worker 실행 실패: {str(e)}"
        logger.error(f"[{session_id}] {error_msg}", exc_info=True)
        raise
    finally:
        # 리소스 정리 (필요 시)
        if worker:
            logger.debug(f"[{session_id}] Worker 리소스 정리: {agent_config.name}")
            # 현재 WorkerAgent는 명시적 정리 메서드가 없지만, 향후 추가 시 여기서 호출


@router.post("/execute")
async def execute_agent(
    request: AgentExecuteRequest,
    config_loader: JsonConfigLoader = Depends(get_config_loader)
):
    """
    Worker Agent 실행 (Server-Sent Events)

    Args:
        request: Agent 실행 요청 (agent_name, task_description, session_id)
        config_loader: ConfigLoader 의존성 주입 (Depends)

    Returns:
        EventSourceResponse: SSE 스트리밍 응답

    Example:
        POST /api/execute
        Body: {
            "agent_name": "planner",
            "task_description": "웹 UI 추가 계획 수립",
            "session_id": "optional-session-id"
        }

    SSE Response:
        data: Worker 출력 청크 1
        data: Worker 출력 청크 2
        ...
        data: [DONE]
    """
    # 세션 ID 생성 (미제공 시)
    session_id = request.session_id or str(uuid.uuid4())

    try:
        # Agent 설정 로드
        agent_configs = config_loader.load_agent_configs()

        agent_config = next(
            (cfg for cfg in agent_configs if cfg.name == request.agent_name),
            None,
        )

        if not agent_config:
            logger.warning(f"❌ 존재하지 않는 Agent: {request.agent_name}")
            raise HTTPException(
                status_code=404,
                detail=f"Agent '{request.agent_name}'를 찾을 수 없습니다",
            )

        logger.info(
            f"[{session_id}] Agent 실행 요청: {request.agent_name} "
            f"(작업 길이: {len(request.task_description)})"
        )

        # SSE 스트리밍 함수
        async def event_generator():
            try:
                chunk_count = 0
                async for chunk in _execute_worker_stream(
                    agent_config, request.task_description, session_id
                ):
                    chunk_count += 1
                    # 디버깅 로그: chunk 길이 및 첫 50자 출력
                    chunk_preview = chunk[:50] if len(chunk) > 50 else chunk
                    logger.debug(
                        f"[{session_id}] SSE Chunk #{chunk_count}: "
                        f"len={len(chunk)}, preview='{chunk_preview}'"
                    )

                    # SSE 표준 형식: sse-starlette가 딕셔너리를 자동 변환
                    yield {"data": chunk}

                # 완료 시그널
                logger.info(f"[{session_id}] SSE 스트림 완료 (총 {chunk_count}개 청크)")
                yield {"data": "[DONE]"}

            except Exception as e:
                error_msg = f"ERROR: {str(e)}"
                logger.error(f"[{session_id}] {error_msg}", exc_info=True)
                # 에러 메시지 전송
                yield {"data": error_msg}
                # 에러 발생 시에도 [DONE] 전송 (클라이언트 무한 대기 방지)
                yield {"data": "[DONE]"}

        # EventSourceResponse로 SSE 스트리밍 반환 (버퍼링 비활성화)
        return EventSourceResponse(
            event_generator(),
            headers={
                "X-Accel-Buffering": "no",  # nginx 버퍼링 비활성화
                "Cache-Control": "no-cache",
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{session_id}] Agent 실행 요청 처리 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Agent 실행 요청 처리 실패: {str(e)}",
        )
