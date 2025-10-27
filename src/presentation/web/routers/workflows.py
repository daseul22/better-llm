"""
워크플로우 API 라우터

워크플로우 저장, 조회, 실행을 위한 엔드포인트를 제공합니다.
"""

import json
import uuid
from pathlib import Path
from typing import Dict, Any
from functools import lru_cache

from fastapi import APIRouter, HTTPException, Depends
from sse_starlette.sse import EventSourceResponse

from src.infrastructure.config import JsonConfigLoader, get_project_root
from src.infrastructure.logging import get_logger
from src.presentation.web.schemas.workflow import (
    Workflow,
    WorkflowExecuteRequest,
    WorkflowExecuteResponse,
    WorkflowSaveRequest,
    WorkflowSaveResponse,
    WorkflowListResponse,
)
from src.presentation.web.services.workflow_executor import WorkflowExecutor

logger = get_logger(__name__)
router = APIRouter(prefix="/api/workflows", tags=["workflows"])


# 워크플로우 저장 디렉토리
WORKFLOWS_DIR = Path.home() / ".better-llm" / "workflows"
WORKFLOWS_DIR.mkdir(parents=True, exist_ok=True)


@lru_cache()
def get_config_loader() -> JsonConfigLoader:
    """
    JsonConfigLoader 싱글톤 인스턴스 반환 (FastAPI Depends + lru_cache)

    Returns:
        JsonConfigLoader: 스레드 안전한 싱글톤 인스턴스
    """
    project_root = get_project_root()
    return JsonConfigLoader(project_root)


def get_workflow_executor(
    config_loader: JsonConfigLoader = Depends(get_config_loader)
) -> WorkflowExecutor:
    """
    WorkflowExecutor 인스턴스 반환 (FastAPI Depends)

    Args:
        config_loader: ConfigLoader 의존성 주입

    Returns:
        WorkflowExecutor: 워크플로우 실행 엔진
    """
    return WorkflowExecutor(config_loader)


@router.post("/execute")
async def execute_workflow(
    request: WorkflowExecuteRequest,
    executor: WorkflowExecutor = Depends(get_workflow_executor),
):
    """
    워크플로우 실행 (Server-Sent Events)

    Args:
        request: 워크플로우 실행 요청
        executor: WorkflowExecutor 의존성 주입

    Returns:
        EventSourceResponse: SSE 스트리밍 응답

    Example:
        POST /api/workflows/execute
        Body: {
            "workflow": {
                "name": "코드 리뷰 워크플로우",
                "nodes": [...],
                "edges": [...]
            },
            "initial_input": "main.py 파일 리뷰",
            "session_id": "optional-session-id"
        }

    SSE Response:
        data: {"event_type": "node_start", "node_id": "1", "data": {...}}
        data: {"event_type": "node_output", "node_id": "1", "data": {"chunk": "..."}}
        data: {"event_type": "node_complete", "node_id": "1", "data": {...}}
        ...
        data: {"event_type": "workflow_complete", "node_id": "", "data": {...}}
        data: [DONE]
    """
    # 세션 ID 생성 (미제공 시)
    session_id = request.session_id or str(uuid.uuid4())

    logger.info(
        f"[{session_id}] 워크플로우 실행 요청: {request.workflow.name} "
        f"(노드: {len(request.workflow.nodes)})"
    )

    # 워크플로우 검증
    if not request.workflow.nodes:
        raise HTTPException(
            status_code=400,
            detail="워크플로우에 노드가 없습니다"
        )

    # SSE 스트리밍 함수
    async def event_generator():
        try:
            event_count = 0

            async for event in executor.execute_workflow(
                workflow=request.workflow,
                initial_input=request.initial_input,
                session_id=session_id,
            ):
                event_count += 1

                # 이벤트를 JSON으로 직렬화
                event_data = event.model_dump()

                logger.debug(
                    f"[{session_id}] SSE Event #{event_count}: "
                    f"{event.event_type} (node: {event.node_id})"
                )

                # SSE 형식으로 전송
                yield {"data": json.dumps(event_data, ensure_ascii=False)}

            # 완료 시그널
            logger.info(f"[{session_id}] SSE 스트림 완료 (총 {event_count}개 이벤트)")
            yield {"data": "[DONE]"}

        except Exception as e:
            error_msg = f"ERROR: {str(e)}"
            logger.error(f"[{session_id}] {error_msg}", exc_info=True)

            # 에러 메시지 전송
            yield {"data": error_msg}
            yield {"data": "[DONE]"}

    # EventSourceResponse로 SSE 스트리밍 반환
    return EventSourceResponse(
        event_generator(),
        headers={
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache",
        }
    )


@router.post("", response_model=WorkflowSaveResponse)
async def save_workflow(request: WorkflowSaveRequest) -> WorkflowSaveResponse:
    """
    워크플로우 저장

    Args:
        request: 워크플로우 저장 요청

    Returns:
        WorkflowSaveResponse: 저장된 워크플로우 ID

    Example:
        POST /api/workflows
        Body: {
            "workflow": {
                "name": "코드 리뷰 워크플로우",
                "description": "코드 작성 → 리뷰 → 커밋",
                "nodes": [...],
                "edges": [...]
            }
        }

        Response: {
            "workflow_id": "uuid-v4",
            "message": "워크플로우가 저장되었습니다"
        }
    """
    try:
        workflow = request.workflow

        # 워크플로우 ID 생성 (미제공 시)
        workflow_id = workflow.id or str(uuid.uuid4())
        workflow.id = workflow_id

        # 파일로 저장
        workflow_path = WORKFLOWS_DIR / f"{workflow_id}.json"
        with open(workflow_path, "w", encoding="utf-8") as f:
            json.dump(
                workflow.model_dump(),
                f,
                ensure_ascii=False,
                indent=2
            )

        logger.info(f"워크플로우 저장: {workflow.name} (ID: {workflow_id})")

        return WorkflowSaveResponse(
            workflow_id=workflow_id,
            message="워크플로우가 저장되었습니다"
        )

    except Exception as e:
        logger.error(f"워크플로우 저장 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"워크플로우 저장 실패: {str(e)}"
        )


@router.get("", response_model=WorkflowListResponse)
async def list_workflows() -> WorkflowListResponse:
    """
    워크플로우 목록 조회

    Returns:
        WorkflowListResponse: 워크플로우 목록 (메타데이터만)

    Example:
        GET /api/workflows
        Response: {
            "workflows": [
                {
                    "id": "uuid-v4",
                    "name": "코드 리뷰 워크플로우",
                    "description": "코드 작성 → 리뷰 → 커밋",
                    "node_count": 3,
                    "edge_count": 2
                },
                ...
            ]
        }
    """
    try:
        workflows = []

        for workflow_path in WORKFLOWS_DIR.glob("*.json"):
            try:
                with open(workflow_path, "r", encoding="utf-8") as f:
                    workflow_data = json.load(f)

                # 메타데이터만 추출
                workflows.append({
                    "id": workflow_data.get("id"),
                    "name": workflow_data.get("name"),
                    "description": workflow_data.get("description"),
                    "node_count": len(workflow_data.get("nodes", [])),
                    "edge_count": len(workflow_data.get("edges", [])),
                })

            except Exception as e:
                logger.warning(f"워크플로우 로드 실패: {workflow_path} - {e}")
                continue

        logger.info(f"워크플로우 목록 조회: {len(workflows)}개")

        return WorkflowListResponse(workflows=workflows)

    except Exception as e:
        logger.error(f"워크플로우 목록 조회 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"워크플로우 목록 조회 실패: {str(e)}"
        )


@router.get("/{workflow_id}", response_model=Workflow)
async def get_workflow(workflow_id: str) -> Workflow:
    """
    워크플로우 조회 (단일)

    Args:
        workflow_id: 워크플로우 ID

    Returns:
        Workflow: 워크플로우 전체 데이터

    Example:
        GET /api/workflows/{workflow_id}
        Response: {
            "id": "uuid-v4",
            "name": "코드 리뷰 워크플로우",
            "description": "...",
            "nodes": [...],
            "edges": [...]
        }
    """
    try:
        workflow_path = WORKFLOWS_DIR / f"{workflow_id}.json"

        if not workflow_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"워크플로우를 찾을 수 없습니다: {workflow_id}"
            )

        with open(workflow_path, "r", encoding="utf-8") as f:
            workflow_data = json.load(f)

        logger.info(f"워크플로우 조회: {workflow_data.get('name')} (ID: {workflow_id})")

        return Workflow(**workflow_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"워크플로우 조회 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"워크플로우 조회 실패: {str(e)}"
        )


@router.delete("/{workflow_id}")
async def delete_workflow(workflow_id: str) -> Dict[str, str]:
    """
    워크플로우 삭제

    Args:
        workflow_id: 워크플로우 ID

    Returns:
        Dict[str, str]: 응답 메시지

    Example:
        DELETE /api/workflows/{workflow_id}
        Response: {
            "message": "워크플로우가 삭제되었습니다"
        }
    """
    try:
        workflow_path = WORKFLOWS_DIR / f"{workflow_id}.json"

        if not workflow_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"워크플로우를 찾을 수 없습니다: {workflow_id}"
            )

        workflow_path.unlink()

        logger.info(f"워크플로우 삭제: {workflow_id}")

        return {"message": "워크플로우가 삭제되었습니다"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"워크플로우 삭제 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"워크플로우 삭제 실패: {str(e)}"
        )
