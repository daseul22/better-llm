"""
프로젝트 API 라우터

프로젝트 디렉토리 선택 및 워크플로우 설정 저장/로드를 위한 엔드포인트를 제공합니다.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException
from src.infrastructure.logging import get_logger
from src.presentation.web.schemas.workflow import (
    ProjectSelectRequest,
    ProjectSelectResponse,
    ProjectWorkflowSaveRequest,
    ProjectWorkflowLoadResponse,
    Workflow,
    ProjectConfig,
)

logger = get_logger(__name__)
router = APIRouter(prefix="/api/projects", tags=["projects"])

# 현재 선택된 프로젝트 경로 (서버 메모리에 저장)
_current_project_path: Optional[str] = None


def get_config_path(project_path: str) -> Path:
    """
    프로젝트 설정 파일 경로 반환

    Args:
        project_path: 프로젝트 디렉토리 경로

    Returns:
        Path: .better-llm/workflow-config.json 경로
    """
    project_dir = Path(project_path)
    config_dir = project_dir / ".better-llm"
    return config_dir / "workflow-config.json"


def validate_project_path(project_path: str) -> Path:
    """
    프로젝트 경로 검증

    Args:
        project_path: 프로젝트 디렉토리 경로

    Returns:
        Path: 검증된 경로 객체

    Raises:
        HTTPException: 경로가 유효하지 않은 경우
    """
    path = Path(project_path).resolve()

    if not path.exists():
        raise HTTPException(
            status_code=400,
            detail=f"프로젝트 디렉토리가 존재하지 않습니다: {project_path}"
        )

    if not path.is_dir():
        raise HTTPException(
            status_code=400,
            detail=f"디렉토리가 아닙니다: {project_path}"
        )

    return path


@router.post("/select", response_model=ProjectSelectResponse)
async def select_project(request: ProjectSelectRequest) -> ProjectSelectResponse:
    """
    프로젝트 디렉토리 선택

    Args:
        request: 프로젝트 선택 요청 (프로젝트 경로 포함)

    Returns:
        ProjectSelectResponse: 선택 결과 및 기존 설정 존재 여부

    Example:
        POST /api/projects/select
        Body: {
            "project_path": "/Users/username/my-project"
        }

        Response: {
            "project_path": "/Users/username/my-project",
            "message": "프로젝트가 선택되었습니다",
            "has_existing_config": true
        }
    """
    global _current_project_path

    # 경로 검증
    project_path = validate_project_path(request.project_path)
    _current_project_path = str(project_path)

    # 기존 설정 확인
    config_path = get_config_path(str(project_path))
    has_existing = config_path.exists()

    logger.info(
        f"프로젝트 선택: {project_path} "
        f"(기존 설정: {'있음' if has_existing else '없음'})"
    )

    return ProjectSelectResponse(
        project_path=str(project_path),
        message="프로젝트가 선택되었습니다",
        has_existing_config=has_existing,
    )


@router.get("/current")
async def get_current_project() -> Dict[str, Any]:
    """
    현재 선택된 프로젝트 정보 조회

    Returns:
        Dict[str, Any]: 프로젝트 정보 (경로, 설정 존재 여부)

    Example:
        GET /api/projects/current

        Response: {
            "project_path": "/Users/username/my-project",
            "has_existing_config": true
        }
    """
    if not _current_project_path:
        return {
            "project_path": None,
            "has_existing_config": False,
        }

    config_path = get_config_path(_current_project_path)
    has_existing = config_path.exists()

    return {
        "project_path": _current_project_path,
        "has_existing_config": has_existing,
    }


@router.post("/workflow")
async def save_project_workflow(
    request: ProjectWorkflowSaveRequest
) -> Dict[str, str]:
    """
    프로젝트에 워크플로우 저장

    Args:
        request: 워크플로우 저장 요청

    Returns:
        Dict[str, str]: 응답 메시지

    Example:
        POST /api/projects/workflow
        Body: {
            "project_path": "/Users/username/my-project",  # 옵션
            "workflow": {
                "name": "코드 리뷰 워크플로우",
                "nodes": [...],
                "edges": [...]
            }
        }

        Response: {
            "message": "워크플로우가 저장되었습니다",
            "config_path": "/Users/username/my-project/.better-llm/workflow-config.json"
        }
    """
    # 프로젝트 경로 결정 (요청에 포함되지 않으면 현재 프로젝트 사용)
    project_path = request.project_path or _current_project_path

    if not project_path:
        raise HTTPException(
            status_code=400,
            detail="프로젝트가 선택되지 않았습니다. 먼저 /api/projects/select를 호출하세요."
        )

    # 경로 검증
    validate_project_path(project_path)

    # 설정 디렉토리 생성
    config_path = get_config_path(project_path)
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # ProjectConfig 생성
    project_config = ProjectConfig(
        project_path=project_path,
        workflow=request.workflow,
        metadata={
            "last_modified": datetime.now().isoformat(),
            "version": "1.0",
        },
    )

    # JSON 저장
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(
                project_config.model_dump(),
                f,
                ensure_ascii=False,
                indent=2,
            )

        logger.info(
            f"워크플로우 저장: {request.workflow.name} → {config_path}"
        )

        return {
            "message": "워크플로우가 저장되었습니다",
            "config_path": str(config_path),
        }

    except Exception as e:
        logger.error(f"워크플로우 저장 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"워크플로우 저장 실패: {str(e)}"
        )


@router.get("/workflow", response_model=ProjectWorkflowLoadResponse)
async def load_project_workflow(
    project_path: Optional[str] = None
) -> ProjectWorkflowLoadResponse:
    """
    프로젝트에서 워크플로우 로드

    Args:
        project_path: 프로젝트 디렉토리 경로 (옵션, 미제공 시 현재 프로젝트)

    Returns:
        ProjectWorkflowLoadResponse: 로드된 워크플로우 및 메타데이터

    Example:
        GET /api/projects/workflow?project_path=/Users/username/my-project

        Response: {
            "project_path": "/Users/username/my-project",
            "workflow": {
                "name": "코드 리뷰 워크플로우",
                "nodes": [...],
                "edges": [...]
            },
            "last_modified": "2025-10-27T12:34:56.789Z"
        }
    """
    # 프로젝트 경로 결정
    target_path = project_path or _current_project_path

    if not target_path:
        raise HTTPException(
            status_code=400,
            detail="프로젝트가 선택되지 않았습니다. 먼저 /api/projects/select를 호출하세요."
        )

    # 경로 검증
    validate_project_path(target_path)

    # 설정 파일 확인
    config_path = get_config_path(target_path)

    if not config_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"워크플로우 설정 파일을 찾을 수 없습니다: {config_path}"
        )

    # JSON 로드
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = json.load(f)

        project_config = ProjectConfig(**config_data)

        logger.info(
            f"워크플로우 로드: {project_config.workflow.name} ← {config_path}"
        )

        return ProjectWorkflowLoadResponse(
            project_path=target_path,
            workflow=project_config.workflow,
            last_modified=project_config.metadata.get("last_modified"),
        )

    except Exception as e:
        logger.error(f"워크플로우 로드 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"워크플로우 로드 실패: {str(e)}"
        )
