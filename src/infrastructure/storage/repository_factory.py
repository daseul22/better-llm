"""
리포지토리 팩토리

설정에 따라 기반 저장소를 선택하여 세션 리포지토리를 생성합니다.
"""

import json
import logging
from pathlib import Path
from typing import Optional

from ...application.ports import ISessionRepository, IApprovalRepository
from .session_repository import JsonSessionRepository
from .sqlite_session_repository import SqliteSessionRepository
from .sqlite_approval_repository import SqliteApprovalRepository

logger = logging.getLogger(__name__)

# 기본 스토리지 설정
DEFAULT_STORAGE_CONFIG = {
    "backend": "json",
    "json_dir": "sessions",
    "sqlite_db_path": "data/sessions.db",
    "retention_days": 90
}


def load_storage_config() -> dict:
    """
    시스템 설정에서 storage 설정 로드

    Returns:
        storage 설정 딕셔너리
    """
    config_path = Path("config/system_config.json")

    if not config_path.exists():
        logger.warning(f"시스템 설정 파일을 찾을 수 없습니다: {config_path}")
        return DEFAULT_STORAGE_CONFIG.copy()

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        storage_config = config.get("storage", {})

        # 기본 설정 병합
        result = DEFAULT_STORAGE_CONFIG.copy()
        result.update(storage_config)

        return result

    except Exception as e:
        logger.error(f"시스템 설정 로드 실패: {e}")
        return DEFAULT_STORAGE_CONFIG.copy()


def create_session_repository(
    backend: Optional[str] = None,
    config: Optional[dict] = None
) -> ISessionRepository:
    """
    세션 리포지토리 생성 팩토리 함수

    시스템 설정에 따라 JSON 또는 SQLite 리포지토리를 생성합니다.

    Args:
        backend: 리포지토리 타입 ("json" 또는 "sqlite", None이면 설정에서 로드)
        config: 리포지토리 설정 (None이면 설정 파일에서 로드)

    Returns:
        ISessionRepository 인스턴스

    Raises:
        ValueError: 유효하지 않은 타입인 경우
    """
    # 설정 로드
    if config is None:
        config = load_storage_config()

    # 타입 결정
    if backend is None:
        backend = config.get("backend", "json")

    # 리포지토리 생성
    if backend == "json":
        json_dir = Path(config.get("json_dir", "sessions"))
        logger.info(f"JSON 세션 리포지토리 생성: {json_dir}")
        return JsonSessionRepository(sessions_dir=json_dir)

    elif backend == "sqlite":
        db_path = Path(config.get("sqlite_db_path", "data/sessions.db"))
        logger.info(f"SQLite 세션 리포지토리 생성: {db_path}")
        return SqliteSessionRepository(db_path=db_path)

    else:
        raise ValueError(f"유효하지 않은 리포지토리 타입: {backend}")


def create_approval_repository(
    config: Optional[dict] = None
) -> IApprovalRepository:
    """
    승인 리포지토리 생성 팩토리 함수

    SQLite 기반 승인 리포지토리를 생성합니다.
    (승인은 SQLite만 지원)

    Args:
        config: 리포지토리 설정 (None이면 설정 파일에서 로드)

    Returns:
        IApprovalRepository 인스턴스
    """
    # 설정 로드
    if config is None:
        config = load_storage_config()

    # SQLite DB 경로
    db_path = Path(config.get("sqlite_db_path", "data/sessions.db"))
    logger.info(f"SQLite 승인 리포지토리 생성: {db_path}")

    return SqliteApprovalRepository(db_path=db_path)


def get_retention_days(config: Optional[dict] = None) -> int:
    """
    세션 보존 기간 조회

    Args:
        config: 리포지토리 설정 (None이면 설정 파일에서 로드)

    Returns:
        보존 기간 (일)
    """
    if config is None:
        config = load_storage_config()

    return config.get("retention_days", 90)
