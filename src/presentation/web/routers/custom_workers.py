"""
커스텀 워커 API 라우터

커스텀 워커 생성, 저장, 조회, 삭제를 위한 엔드포인트를 제공합니다.
"""

import uuid
import json
import asyncio
from pathlib import Path
from typing import AsyncIterator, Optional, Dict
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Depends
from sse_starlette.sse import EventSourceResponse

from src.domain.models import AgentConfig
from src.infrastructure.config import JsonConfigLoader, get_project_root, get_data_dir
from src.infrastructure.claude.worker_client import WorkerAgent
from src.infrastructure.storage import CustomWorkerRepository
from src.infrastructure.logging import get_logger
from src.presentation.web.schemas.request import (
    CustomWorkerGenerateRequest,
    CustomWorkerSaveRequest,
    CustomWorkerInfo,
    CustomWorkerListResponse,
)

logger = get_logger(__name__)
router = APIRouter(prefix="/api/custom-workers", tags=["custom-workers"])

# 활성 세션 관리 (메모리)
_active_sessions: Dict[str, dict] = {}

def get_session_dir(session_id: str) -> Path:
    """세션 디렉토리 경로 반환"""
    data_dir = get_data_dir()
    session_dir = data_dir / "custom_worker_sessions" / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir

def save_session_state(session_id: str, state: dict):
    """세션 상태를 파일에 저장"""
    session_dir = get_session_dir(session_id)
    state_file = session_dir / "state.json"
    with open(state_file, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def load_session_state(session_id: str) -> Optional[dict]:
    """세션 상태를 파일에서 로드"""
    session_dir = get_session_dir(session_id)
    state_file = session_dir / "state.json"
    if state_file.exists():
        with open(state_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def append_session_output(session_id: str, chunk: str):
    """세션 출력을 파일에 추가"""
    session_dir = get_session_dir(session_id)
    output_file = session_dir / "output.txt"
    with open(output_file, 'a', encoding='utf-8') as f:
        f.write(chunk)

def read_session_output(session_id: str) -> str:
    """세션 출력을 파일에서 읽기"""
    session_dir = get_session_dir(session_id)
    output_file = session_dir / "output.txt"
    if output_file.exists():
        with open(output_file, 'r', encoding='utf-8') as f:
            return f.read()
    return ""


def get_worker_prompt_engineer_config() -> AgentConfig:
    """
    worker_prompt_engineer 설정 로드

    Returns:
        AgentConfig: worker_prompt_engineer 설정

    Raises:
        HTTPException: 설정 로드 실패 시
    """
    try:
        config_loader = JsonConfigLoader(get_project_root())
        agent_configs = config_loader.load_agent_configs()

        config = next(
            (cfg for cfg in agent_configs if cfg.name == "worker_prompt_engineer"),
            None,
        )

        if not config:
            raise HTTPException(
                status_code=500,
                detail="worker_prompt_engineer 설정을 찾을 수 없습니다",
            )

        return config

    except Exception as e:
        logger.error(f"worker_prompt_engineer 설정 로드 실패: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"워커 프롬프트 엔지니어 설정 로드 실패: {str(e)}",
        )


async def _execute_worker_prompt_engineer(
    requirements: str, session_id: str
) -> AsyncIterator[str]:
    """
    worker_prompt_engineer 실행 (스트리밍)

    Args:
        requirements: 워커 요구사항
        session_id: 세션 ID

    Yields:
        str: Worker 출력 청크
    """
    try:
        config = get_worker_prompt_engineer_config()

        # better-llm 프로젝트를 working directory로 설정
        # 다른 워커 프롬프트들을 참고하기 위함
        better_llm_project_dir = str(get_project_root())

        worker = WorkerAgent(
            config=config,
            project_dir=better_llm_project_dir
        )

        logger.info(
            f"[{session_id}] worker_prompt_engineer 실행 시작 "
            f"(working_dir: {better_llm_project_dir})"
        )

        async for chunk in worker.execute_task(requirements):
            yield chunk

        logger.info(f"[{session_id}] worker_prompt_engineer 실행 완료")

    except Exception as e:
        error_msg = f"워커 프롬프트 엔지니어 실행 실패: {str(e)}"
        logger.error(f"[{session_id}] {error_msg}", exc_info=True)
        raise


@router.post("/generate")
async def generate_custom_worker(request: CustomWorkerGenerateRequest):
    """
    커스텀 워커 프롬프트 생성 (SSE 스트리밍)

    worker_prompt_engineer를 실행하여 커스텀 워커 프롬프트를 생성합니다.
    사용자와 상호작용하며 프롬프트를 개선할 수 있습니다.
    세션 ID로 재접속하면 이전 출력부터 이어서 볼 수 있습니다.

    Args:
        request: 워커 생성 요청 (worker_requirements, session_id)

    Returns:
        EventSourceResponse: SSE 스트리밍 응답

    Example:
        POST /api/custom-workers/generate
        Body: {
            "worker_requirements": "데이터 분석 및 시각화를 수행하는 워커",
            "session_id": "optional-session-id"
        }

    SSE Response:
        data: 생성된 프롬프트 청크 1
        data: 생성된 프롬프트 청크 2
        ...
        data: [DONE]
    """
    session_id = request.session_id or str(uuid.uuid4())

    # 기존 세션 확인
    existing_state = load_session_state(session_id)
    is_reconnect = existing_state is not None and existing_state.get("status") in ["generating", "completed"]

    if is_reconnect:
        logger.info(f"[{session_id}] 세션 재접속 (상태: {existing_state.get('status')})")
    else:
        logger.info(
            f"[{session_id}] 커스텀 워커 생성 요청 "
            f"(요구사항 길이: {len(request.worker_requirements)})"
        )
        # 새 세션 상태 저장
        save_session_state(session_id, {
            "session_id": session_id,
            "status": "generating",
            "worker_requirements": request.worker_requirements,
            "created_at": datetime.now().isoformat(),
        })

    async def event_generator():
        try:
            # 재접속: 이전 출력 먼저 스트리밍
            if is_reconnect:
                previous_output = read_session_output(session_id)
                if previous_output:
                    logger.info(f"[{session_id}] 이전 출력 복원 (길이: {len(previous_output)})")
                    yield {"data": previous_output}

                # 이미 완료된 세션이면 [DONE] 전송
                if existing_state.get("status") == "completed":
                    logger.info(f"[{session_id}] 세션 이미 완료됨")
                    yield {"data": "[DONE]"}
                    return

            # 이미 실행 중인 세션이면 대기만 (중복 실행 방지)
            if session_id in _active_sessions:
                logger.info(f"[{session_id}] 이미 실행 중인 세션 - 출력 대기")
                # 실행 중인 세션의 새 출력을 기다림
                while session_id in _active_sessions:
                    await asyncio.sleep(0.5)
                # 완료 후 남은 출력 전송
                yield {"data": "[DONE]"}
                return

            # 새로운 실행: 워커 실행
            _active_sessions[session_id] = {"started_at": datetime.now().isoformat()}

            chunk_count = 0
            accumulated_output = ""

            async for chunk in _execute_worker_prompt_engineer(
                request.worker_requirements, session_id
            ):
                chunk_count += 1
                accumulated_output += chunk
                append_session_output(session_id, chunk)  # 파일에 저장
                logger.debug(f"[{session_id}] SSE Chunk #{chunk_count}: len={len(chunk)}")
                yield {"data": chunk}

            logger.info(f"[{session_id}] SSE 스트림 완료 (총 {chunk_count}개 청크)")
            logger.info(f"[{session_id}] 📊 전체 출력 길이: {len(accumulated_output)} characters")
            logger.info(f"[{session_id}] 📄 전체 출력 내용:\n{'-'*80}\n{accumulated_output}\n{'-'*80}")

            # 세션 완료 상태 저장
            save_session_state(session_id, {
                "session_id": session_id,
                "status": "completed",
                "worker_requirements": request.worker_requirements,
                "created_at": existing_state.get("created_at") if existing_state else datetime.now().isoformat(),
                "completed_at": datetime.now().isoformat(),
            })

            yield {"data": "[DONE]"}

        except Exception as e:
            error_msg = f"ERROR: {str(e)}"
            logger.error(f"[{session_id}] {error_msg}", exc_info=True)

            # 에러 상태 저장
            save_session_state(session_id, {
                "session_id": session_id,
                "status": "error",
                "error": str(e),
                "created_at": existing_state.get("created_at") if existing_state else datetime.now().isoformat(),
            })

            yield {"data": error_msg}
            yield {"data": "[DONE]"}

        finally:
            # 활성 세션에서 제거
            if session_id in _active_sessions:
                del _active_sessions[session_id]

    return EventSourceResponse(
        event_generator(),
        headers={
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache",
            "X-Session-Id": session_id,  # 세션 ID 헤더로 반환
        }
    )


@router.post("/save")
async def save_custom_worker(request: CustomWorkerSaveRequest):
    """
    커스텀 워커 저장

    생성된 커스텀 워커를 프로젝트 경로의 .better-llm/worker/ 폴더에 저장합니다.

    Args:
        request: 워커 저장 요청 (project_path, worker_name, role, prompt_content, allowed_tools, model, thinking)

    Returns:
        Dict: 저장 결과 (success, message, prompt_path)

    Example:
        POST /api/custom-workers/save
        Body: {
            "project_path": "/path/to/project",
            "worker_name": "data_analyzer",
            "role": "데이터 분석",
            "prompt_content": "# 당신은 데이터 분석 전문가입니다...",
            "allowed_tools": ["read", "bash", "glob"],
            "model": "claude-sonnet-4-5-20250929",
            "thinking": false
        }

    Response: {
        "success": true,
        "message": "커스텀 워커 저장 완료",
        "prompt_path": "/path/to/project/.better-llm/worker/data_analyzer.txt"
    }
    """
    try:
        project_path = Path(request.project_path)

        if not project_path.exists():
            raise HTTPException(
                status_code=400,
                detail=f"프로젝트 경로가 존재하지 않습니다: {project_path}",
            )

        # CustomWorkerRepository 인스턴스 생성
        repository = CustomWorkerRepository(project_path)

        # 커스텀 워커 저장
        prompt_path = repository.save_custom_worker(
            worker_name=request.worker_name,
            prompt_content=request.prompt_content,
            allowed_tools=request.allowed_tools,
            model=request.model,
            thinking=request.thinking,
            role=request.role,
        )

        logger.info(f"커스텀 워커 저장 완료: {request.worker_name} at {project_path}")

        return {
            "success": True,
            "message": f"커스텀 워커 '{request.worker_name}' 저장 완료",
            "prompt_path": str(prompt_path),
        }

    except ValueError as e:
        logger.warning(f"커스텀 워커 저장 실패 (유효성 검증): {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"커스텀 워커 저장 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"커스텀 워커 저장 실패: {str(e)}",
        )


@router.get("", response_model=CustomWorkerListResponse)
async def list_custom_workers(
    project_path: str = Query(..., description="프로젝트 경로")
):
    """
    커스텀 워커 목록 조회

    프로젝트 경로의 .better-llm/worker/ 폴더에서 커스텀 워커 목록을 조회합니다.

    Args:
        project_path: 프로젝트 경로 (Query 파라미터)

    Returns:
        CustomWorkerListResponse: 커스텀 워커 목록

    Example:
        GET /api/custom-workers?project_path=/path/to/project

    Response: {
        "workers": [
            {
                "name": "data_analyzer",
                "role": "데이터 분석",
                "allowed_tools": ["read", "bash", "glob"],
                "model": "claude-sonnet-4-5-20250929",
                "thinking": false,
                "prompt_preview": "# 당신은 데이터 분석 전문가입니다..."
            }
        ]
    }
    """
    try:
        project_path_obj = Path(project_path)

        if not project_path_obj.exists():
            raise HTTPException(
                status_code=400,
                detail=f"프로젝트 경로가 존재하지 않습니다: {project_path}",
            )

        # CustomWorkerRepository 인스턴스 생성
        repository = CustomWorkerRepository(project_path_obj)

        # 커스텀 워커 로드
        agent_configs = repository.load_custom_workers()

        # CustomWorkerInfo로 변환
        workers = []
        for config in agent_configs:
            # 프롬프트 미리보기 (첫 100자)
            prompt_preview = ""
            try:
                prompt_path = Path(config.system_prompt)
                if prompt_path.exists():
                    with open(prompt_path, 'r', encoding='utf-8') as f:
                        prompt_content = f.read()
                        prompt_preview = prompt_content[:100]
            except Exception as e:
                logger.warning(f"프롬프트 미리보기 로드 실패: {config.name}, {e}")

            workers.append(CustomWorkerInfo(
                name=config.name,
                role=config.role,
                allowed_tools=list(config.allowed_tools) if config.allowed_tools else [],
                model=config.model or "claude-sonnet-4-5-20250929",
                thinking=config.thinking if hasattr(config, 'thinking') else False,
                prompt_preview=prompt_preview,
            ))

        logger.info(f"커스텀 워커 목록 조회: {len(workers)}개 at {project_path}")

        return CustomWorkerListResponse(workers=workers)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"커스텀 워커 목록 조회 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"커스텀 워커 목록 조회 실패: {str(e)}",
        )


@router.delete("/{worker_name}")
async def delete_custom_worker(
    worker_name: str,
    project_path: str = Query(..., description="프로젝트 경로")
):
    """
    커스텀 워커 삭제

    프로젝트 경로의 .better-llm/worker/ 폴더에서 커스텀 워커를 삭제합니다.

    Args:
        worker_name: 삭제할 워커 이름 (Path 파라미터)
        project_path: 프로젝트 경로 (Query 파라미터)

    Returns:
        Dict: 삭제 결과 (success, message)

    Example:
        DELETE /api/custom-workers/data_analyzer?project_path=/path/to/project

    Response: {
        "success": true,
        "message": "커스텀 워커 'data_analyzer' 삭제 완료"
    }
    """
    try:
        project_path_obj = Path(project_path)

        if not project_path_obj.exists():
            raise HTTPException(
                status_code=400,
                detail=f"프로젝트 경로가 존재하지 않습니다: {project_path}",
            )

        # CustomWorkerRepository 인스턴스 생성
        repository = CustomWorkerRepository(project_path_obj)

        # 커스텀 워커 삭제
        success = repository.delete_custom_worker(worker_name)

        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"커스텀 워커를 찾을 수 없거나 삭제 실패: {worker_name}",
            )

        logger.info(f"커스텀 워커 삭제 완료: {worker_name} at {project_path}")

        return {
            "success": True,
            "message": f"커스텀 워커 '{worker_name}' 삭제 완료",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"커스텀 워커 삭제 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"커스텀 워커 삭제 실패: {str(e)}",
        )
