"""
세션 데이터 마이그레이션 도구

JSON 파일 기반 세션 데이터를 SQLite 데이터베이스로 마이그레이션
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from .sqlite_session_repository import SqliteSessionRepository
from domain.models import SessionResult, SessionStatus
from domain.services import ConversationHistory

logger = logging.getLogger(__name__)


class SessionMigration:
    """
    세션 데이터 마이그레이션

    JSON 파일을 SQLite 데이터베이스로 마이그레이션합니다.
    """

    def __init__(
        self,
        json_dir: Path = Path("sessions"),
        sqlite_repo: Optional[SqliteSessionRepository] = None
    ):
        """
        Args:
            json_dir: JSON 세션 파일 디렉토리
            sqlite_repo: SQLite 리포지토리 (없으면 기본 생성)
        """
        self.json_dir = json_dir
        self.sqlite_repo = sqlite_repo or SqliteSessionRepository()

    def migrate_all(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        모든 JSON 세션 파일을 SQLite로 마이그레이션

        Args:
            dry_run: True면 실제 저장은 하지 않고 검증만 수행

        Returns:
            마이그레이션 결과 통계
        """
        if not self.json_dir.exists():
            logger.warning(f"세션 디렉토리가 존재하지 않습니다: {self.json_dir}")
            return {
                "total_files": 0,
                "success": 0,
                "failed": 0,
                "skipped": 0,
                "errors": []
            }

        # JSON 파일 목록 조회
        json_files = list(self.json_dir.glob("session_*.json"))
        logger.info(f"마이그레이션 대상: {len(json_files)} 파일")

        stats = {
            "total_files": len(json_files),
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "errors": []
        }

        for json_file in json_files:
            try:
                result = self._migrate_file(json_file, dry_run=dry_run)
                if result == "success":
                    stats["success"] += 1
                elif result == "skipped":
                    stats["skipped"] += 1
            except Exception as e:
                stats["failed"] += 1
                stats["errors"].append({
                    "file": str(json_file),
                    "error": str(e)
                })
                logger.error(f"마이그레이션 실패: {json_file} - {e}")

        logger.info(
            f"마이그레이션 완료: "
            f"성공={stats['success']}, 실패={stats['failed']}, 건너뜀={stats['skipped']}"
        )

        return stats

    def _migrate_file(self, json_file: Path, dry_run: bool = False) -> str:
        """
        개별 JSON 파일 마이그레이션

        Args:
            json_file: JSON 파일 경로
            dry_run: True면 실제 저장은 하지 않음

        Returns:
            "success", "skipped", "failed" 중 하나

        Raises:
            Exception: 마이그레이션 실패 시
        """
        # JSON 파일 읽기
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 필수 필드 확인
        required_fields = ["session_id", "user_request", "messages", "result"]
        if not all(field in data for field in required_fields):
            logger.warning(f"필수 필드 누락: {json_file}")
            return "skipped"

        session_id = data["session_id"]
        user_request = data["user_request"]
        messages = data["messages"]
        result_data = data["result"]

        # SessionResult 객체 생성
        status_str = result_data.get("status", "completed")
        # 문자열을 SessionStatus Enum으로 변환
        try:
            status = SessionStatus(status_str)
        except ValueError:
            # 알 수 없는 상태는 ERROR로 처리
            status = SessionStatus.ERROR

        result = SessionResult(
            status=status,
            files_modified=result_data.get("files_modified", []),
            tests_passed=result_data.get("tests_passed"),
            error_message=result_data.get("error_message")
        )

        # ConversationHistory 객체 생성
        history_data = {
            "max_length": 50,
            "messages": messages
        }
        history = ConversationHistory.from_dict(history_data)

        if dry_run:
            logger.info(f"[DRY RUN] 마이그레이션 대상: {session_id}")
            return "success"

        # SQLite에 저장
        self.sqlite_repo.save(
            session_id=session_id,
            user_request=user_request,
            history=history,
            result=result
        )

        logger.info(f"마이그레이션 완료: {session_id}")
        return "success"

    def validate_migration(self) -> Dict[str, Any]:
        """
        마이그레이션 검증

        JSON 파일 수와 SQLite 세션 수를 비교합니다.

        Returns:
            검증 결과
        """
        # JSON 파일 수
        json_files = list(self.json_dir.glob("session_*.json")) if self.json_dir.exists() else []
        json_count = len(json_files)

        # SQLite 세션 수
        sessions = self.sqlite_repo.list_sessions(limit=10000)
        sqlite_count = len(sessions)

        result = {
            "json_count": json_count,
            "sqlite_count": sqlite_count,
            "match": json_count == sqlite_count,
            "difference": abs(json_count - sqlite_count)
        }

        if result["match"]:
            logger.info(f"마이그레이션 검증 성공: {sqlite_count} 세션")
        else:
            logger.warning(
                f"마이그레이션 검증 실패: "
                f"JSON={json_count}, SQLite={sqlite_count}, 차이={result['difference']}"
            )

        return result


def migrate_sessions_cli(
    json_dir: str = "sessions",
    db_path: str = "data/sessions.db",
    dry_run: bool = False
) -> None:
    """
    CLI용 마이그레이션 함수

    Args:
        json_dir: JSON 세션 디렉토리
        db_path: SQLite 데이터베이스 경로
        dry_run: True면 실제 저장은 하지 않음
    """
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    print(f"\n{'='*60}")
    print("세션 데이터 마이그레이션: JSON → SQLite")
    print(f"{'='*60}\n")
    print(f"JSON 디렉토리: {json_dir}")
    print(f"SQLite 경로: {db_path}")
    print(f"Dry Run: {dry_run}\n")

    # SQLite 리포지토리 생성
    sqlite_repo = SqliteSessionRepository(db_path=Path(db_path))

    # 마이그레이션 실행
    migration = SessionMigration(
        json_dir=Path(json_dir),
        sqlite_repo=sqlite_repo
    )

    stats = migration.migrate_all(dry_run=dry_run)

    # 결과 출력
    print(f"\n{'='*60}")
    print("마이그레이션 결과")
    print(f"{'='*60}\n")
    print(f"총 파일 수: {stats['total_files']}")
    print(f"성공: {stats['success']}")
    print(f"실패: {stats['failed']}")
    print(f"건너뜀: {stats['skipped']}")

    if stats['errors']:
        print(f"\n에러 목록:")
        for error in stats['errors']:
            print(f"  - {error['file']}: {error['error']}")

    # 검증
    if not dry_run and stats['success'] > 0:
        print(f"\n{'='*60}")
        print("마이그레이션 검증")
        print(f"{'='*60}\n")

        validation = migration.validate_migration()
        print(f"JSON 파일 수: {validation['json_count']}")
        print(f"SQLite 세션 수: {validation['sqlite_count']}")
        print(f"검증 결과: {'✓ 성공' if validation['match'] else '✗ 실패'}")

        if not validation['match']:
            print(f"차이: {validation['difference']}")

    print()


if __name__ == "__main__":
    import sys
    from typing import Optional

    # CLI 인자 파싱
    args = sys.argv[1:]
    dry_run = "--dry-run" in args or "-n" in args

    migrate_sessions_cli(dry_run=dry_run)
