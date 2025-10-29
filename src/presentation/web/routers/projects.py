"""
프로젝트 API 라우터

프로젝트 디렉토리 선택 및 워크플로우 설정 저장/로드를 위한 엔드포인트를 제공합니다.
"""

import json
import shutil
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
    DisplayConfig,
    DisplayConfigLoadResponse,
    DisplayConfigSaveRequest,
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
        Path: .claude-flow/workflow-config.json 경로
    """
    project_dir = Path(project_path)
    config_dir = project_dir / ".claude-flow"
    return config_dir / "workflow-config.json"


def get_display_config_path(project_path: str) -> Path:
    """
    Display 설정 파일 경로 반환

    Args:
        project_path: 프로젝트 디렉토리 경로

    Returns:
        Path: .claude-flow/display-config.json 경로
    """
    project_dir = Path(project_path)
    config_dir = project_dir / ".claude-flow"
    return config_dir / "display-config.json"


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
            "config_path": "/Users/username/my-project/.claude-flow/workflow-config.json"
        }
    """
    # 프로젝트 경로 결정 (요청에 포함되지 않으면 현재 프로젝트 사용)
    project_path = request.project_path or _current_project_path

    # 명시적 검증: project_path가 None이거나 빈 문자열이면 에러
    if not project_path or project_path.strip() == "":
        logger.error(
            f"워크플로우 저장 실패: 프로젝트 경로 없음 "
            f"(request.project_path={request.project_path}, _current_project_path={_current_project_path})"
        )
        raise HTTPException(
            status_code=400,
            detail=(
                "프로젝트가 선택되지 않았습니다. "
                "먼저 '프로젝트 선택' 버튼을 클릭하여 프로젝트 디렉토리를 선택하세요."
            )
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
        workflow_dict = project_config.model_dump(mode='json', exclude_none=False)

        # 디버그: parallel_execution 필드 확인
        for node in request.workflow.nodes:
            node_data = node.data if hasattr(node, 'data') else node.get('data', {})
            if isinstance(node_data, dict):
                parallel_exec = node_data.get('parallel_execution')
                logger.info(
                    f"[저장] 노드 {node.id}: parallel_execution = {parallel_exec}"
                )

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(
                workflow_dict,
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

        # 디버그: parallel_execution 필드 확인
        for node in project_config.workflow.nodes:
            node_data = node.data if hasattr(node, 'data') else {}
            if isinstance(node_data, dict):
                parallel_exec = node_data.get('parallel_execution')
            else:
                parallel_exec = getattr(node_data, 'parallel_execution', None)
            logger.info(
                f"[로드] 노드 {node.id}: parallel_execution = {parallel_exec}"
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


@router.delete("/sessions")
async def clear_sessions() -> Dict[str, Any]:
    """
    현재 프로젝트의 웹 워크플로우 세션 데이터 비우기

    {project_path}/.claude-flow/web-sessions/ 디렉토리의 모든 세션 파일을 삭제합니다.

    Returns:
        Dict[str, Any]: 삭제 결과 (삭제된 파일 수, 확보된 용량)

    Example:
        DELETE /api/projects/sessions

        Response: {
            "message": "세션 데이터가 삭제되었습니다",
            "deleted_files": 5,
            "freed_space_mb": 12.3
        }
    """
    if not _current_project_path:
        raise HTTPException(
            status_code=400,
            detail="프로젝트가 선택되지 않았습니다."
        )

    # 웹 세션 디렉토리 경로: {project_path}/.claude-flow/web-sessions/
    project_dir = Path(_current_project_path)
    web_sessions_dir = project_dir / ".claude-flow" / "web-sessions"

    if not web_sessions_dir.exists():
        logger.info(f"웹 세션 디렉토리가 존재하지 않습니다: {web_sessions_dir}")
        return {
            "message": "삭제할 세션 데이터가 없습니다",
            "deleted_files": 0,
            "freed_space_mb": 0.0
        }

    try:
        # 디렉토리 크기 및 파일 개수 계산
        total_size = 0
        file_count = 0

        for file_path in web_sessions_dir.rglob("*"):
            if file_path.is_file():
                total_size += file_path.stat().st_size
                file_count += 1

        # 디렉토리 삭제 및 재생성 (빈 디렉토리 유지)
        shutil.rmtree(web_sessions_dir)
        web_sessions_dir.mkdir(parents=True, exist_ok=True)

        freed_space_mb = total_size / (1024 * 1024)

        logger.info(
            f"웹 세션 데이터 삭제 완료: {web_sessions_dir} "
            f"(파일: {file_count}개, 용량: {freed_space_mb:.2f} MB)"
        )

        return {
            "message": "세션 데이터가 삭제되었습니다",
            "deleted_files": file_count,
            "freed_space_mb": round(freed_space_mb, 2)
        }

    except Exception as e:
        logger.error(f"웹 세션 데이터 삭제 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"세션 데이터 삭제 실패: {str(e)}"
        )


@router.delete("/logs")
async def clear_logs() -> Dict[str, Any]:
    """
    현재 프로젝트의 로그 파일 비우기

    다음 위치의 로그 파일을 모두 삭제합니다:
    1. {project_path}/.claude-flow/logs/ (프로젝트 내 로그)
    2. ~/.claude-flow/{project-name}/logs/ (홈 디렉토리 로그)

    Returns:
        Dict[str, Any]: 삭제 결과 (삭제된 파일 수, 확보된 용량)

    Example:
        DELETE /api/projects/logs

        Response: {
            "message": "로그 파일이 삭제되었습니다",
            "deleted_files": 8,
            "freed_space_mb": 45.6
        }
    """
    if not _current_project_path:
        raise HTTPException(
            status_code=400,
            detail="프로젝트가 선택되지 않았습니다."
        )

    project_dir = Path(_current_project_path)
    project_name = project_dir.name
    home_dir = Path.home()

    # 로그 디렉토리 목록
    log_dirs = [
        project_dir / ".claude-flow" / "logs",  # 프로젝트 내 로그
        home_dir / ".claude-flow" / project_name / "logs",  # 홈 디렉토리 로그
    ]

    total_size = 0
    total_file_count = 0
    deleted_dirs = []

    try:
        for logs_dir in log_dirs:
            if not logs_dir.exists():
                logger.debug(f"로그 디렉토리가 존재하지 않습니다: {logs_dir}")
                continue

            # 디렉토리 크기 및 파일 개수 계산
            dir_size = 0
            dir_file_count = 0

            for file_path in logs_dir.rglob("*"):
                if file_path.is_file():
                    dir_size += file_path.stat().st_size
                    dir_file_count += 1

            # 디렉토리 삭제 및 재생성 (빈 디렉토리 유지)
            shutil.rmtree(logs_dir)
            logs_dir.mkdir(parents=True, exist_ok=True)

            total_size += dir_size
            total_file_count += dir_file_count
            deleted_dirs.append(str(logs_dir))

            logger.info(
                f"로그 파일 삭제: {logs_dir} "
                f"(파일: {dir_file_count}개, 용량: {dir_size / (1024 * 1024):.2f} MB)"
            )

        freed_space_mb = total_size / (1024 * 1024)

        if total_file_count == 0:
            return {
                "message": "삭제할 로그 파일이 없습니다",
                "deleted_files": 0,
                "freed_space_mb": 0.0
            }

        logger.info(
            f"로그 파일 삭제 완료 (총 {len(deleted_dirs)}개 위치): "
            f"{', '.join(deleted_dirs)} "
            f"(파일: {total_file_count}개, 용량: {freed_space_mb:.2f} MB)"
        )

        return {
            "message": "로그 파일이 삭제되었습니다",
            "deleted_files": total_file_count,
            "freed_space_mb": round(freed_space_mb, 2)
        }

    except Exception as e:
        logger.error(f"로그 파일 삭제 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"로그 파일 삭제 실패: {str(e)}"
        )


@router.get("/display-config", response_model=DisplayConfigLoadResponse)
async def load_display_config(
    project_path: Optional[str] = None
) -> DisplayConfigLoadResponse:
    """
    Display 설정 로드

    Args:
        project_path: 프로젝트 디렉토리 경로 (옵션, 미제공 시 현재 프로젝트)

    Returns:
        DisplayConfigLoadResponse: 로드된 Display 설정

    Example:
        GET /api/projects/display-config

        Response: {
            "config": {
                "left_sidebar_open": true,
                "right_sidebar_open": true,
                "expanded_sections": ["input", "manager", "general"]
            }
        }
    """
    # 프로젝트 경로 결정
    target_path = project_path or _current_project_path

    if not target_path:
        # 프로젝트 선택되지 않은 경우 기본값 반환
        logger.info("프로젝트 미선택 - Display 설정 기본값 반환")
        return DisplayConfigLoadResponse(
            config=DisplayConfig()
        )

    # 경로 검증
    try:
        validate_project_path(target_path)
    except HTTPException:
        # 경로 검증 실패 시 기본값 반환
        logger.warning(f"프로젝트 경로 검증 실패 - Display 설정 기본값 반환: {target_path}")
        return DisplayConfigLoadResponse(
            config=DisplayConfig()
        )

    # 설정 파일 확인
    config_path = get_display_config_path(target_path)

    if not config_path.exists():
        # 설정 파일 없으면 기본값 반환
        logger.info(f"Display 설정 파일 없음 - 기본값 반환: {config_path}")
        return DisplayConfigLoadResponse(
            config=DisplayConfig()
        )

    # JSON 로드
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = json.load(f)

        display_config = DisplayConfig(**config_data)

        logger.info(f"Display 설정 로드 완료: {config_path}")

        return DisplayConfigLoadResponse(
            config=display_config
        )

    except Exception as e:
        logger.error(f"Display 설정 로드 실패: {e}", exc_info=True)
        # 로드 실패 시 기본값 반환
        return DisplayConfigLoadResponse(
            config=DisplayConfig()
        )


@router.post("/display-config")
async def save_display_config(
    request: DisplayConfigSaveRequest
) -> Dict[str, str]:
    """
    Display 설정 저장

    Args:
        request: Display 설정 저장 요청

    Returns:
        Dict[str, str]: 응답 메시지

    Example:
        POST /api/projects/display-config
        Body: {
            "config": {
                "left_sidebar_open": false,
                "right_sidebar_open": true,
                "expanded_sections": ["input", "manager"]
            }
        }

        Response: {
            "message": "Display 설정이 저장되었습니다",
            "config_path": "/project/.claude-flow/display-config.json"
        }
    """
    if not _current_project_path:
        raise HTTPException(
            status_code=400,
            detail="프로젝트가 선택되지 않았습니다. 먼저 프로젝트를 선택하세요."
        )

    # 경로 검증
    validate_project_path(_current_project_path)

    # 설정 디렉토리 생성
    config_path = get_display_config_path(_current_project_path)
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # JSON 저장
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(
                request.config.model_dump(),
                f,
                ensure_ascii=False,
                indent=2,
            )

        logger.info(f"Display 설정 저장: {config_path}")

        return {
            "message": "Display 설정이 저장되었습니다",
            "config_path": str(config_path),
        }

    except Exception as e:
        logger.error(f"Display 설정 저장 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Display 설정 저장 실패: {str(e)}"
        )
