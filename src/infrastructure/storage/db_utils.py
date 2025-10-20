"""Database query execution utilities.

이 모듈은 SQLite 쿼리 실행의 공통 패턴을 제공합니다:
- Connection 관리
- 예외 처리 및 로깅
- 쿼리 실행 (select, insert, update, delete)
"""

from typing import Any, List, Tuple, Optional
from pathlib import Path
import sqlite3
import logging

logger = logging.getLogger(__name__)


class DatabaseExecutor:
    """SQLite 쿼리 실행을 관리하는 헬퍼 클래스.

    Context Manager를 사용하여 Connection 생명주기를 자동 관리합니다.
    """

    def __init__(self, db_path: Path):
        """DatabaseExecutor 초기화.

        Args:
            db_path: SQLite DB 파일 경로
        """
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        self.cursor: Optional[sqlite3.Cursor] = None

    def __enter__(self) -> "DatabaseExecutor":
        """Context Manager 진입."""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context Manager 종료."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            if exc_type is None:
                self.conn.commit()
            else:
                self.conn.rollback()
            self.conn.close()

    def execute_query(
        self,
        query: str,
        params: Tuple[Any, ...] = (),
        operation: str = "query"
    ) -> List[sqlite3.Row]:
        """SELECT 쿼리를 실행하고 결과를 반환합니다.

        Args:
            query: SQL 쿼리 문자열
            params: 쿼리 파라미터 튜플
            operation: 로깅용 작업 이름

        Returns:
            쿼리 결과 리스트 (sqlite3.Row 객체)

        Raises:
            StorageError: DB 쿼리 실행 실패 시
        """
        from src.domain.exceptions import StorageError

        try:
            logger.debug(f"Executing {operation}: {query[:100]}...")
            if not self.cursor:
                raise StorageError("Database cursor not initialized")

            self.cursor.execute(query, params)
            results = self.cursor.fetchall()
            logger.debug(f"{operation} returned {len(results)} rows")
            return results

        except sqlite3.Error as e:
            logger.error(f"Database error during {operation}: {e}")
            raise StorageError(f"Failed to execute {operation}") from e

    def execute_update(
        self,
        query: str,
        params: Tuple[Any, ...] = (),
        operation: str = "update"
    ) -> int:
        """INSERT/UPDATE/DELETE 쿼리를 실행하고 영향받은 행 수를 반환합니다.

        Args:
            query: SQL 쿼리 문자열
            params: 쿼리 파라미터 튜플
            operation: 로깅용 작업 이름

        Returns:
            영향받은 행 수

        Raises:
            StorageError: DB 쿼리 실행 실패 시
        """
        from src.domain.exceptions import StorageError

        try:
            logger.debug(f"Executing {operation}: {query[:100]}...")
            if not self.cursor:
                raise StorageError("Database cursor not initialized")

            self.cursor.execute(query, params)
            rowcount = self.cursor.rowcount
            logger.debug(f"{operation} affected {rowcount} rows")
            return rowcount

        except sqlite3.Error as e:
            logger.error(f"Database error during {operation}: {e}")
            raise StorageError(f"Failed to execute {operation}") from e


def execute_single_query(
    db_path: Path,
    query: str,
    params: Tuple[Any, ...] = (),
    operation: str = "query"
) -> List[sqlite3.Row]:
    """단일 SELECT 쿼리를 실행하는 편의 함수.

    Args:
        db_path: SQLite DB 파일 경로
        query: SQL 쿼리 문자열
        params: 쿼리 파라미터 튜플
        operation: 로깅용 작업 이름

    Returns:
        쿼리 결과 리스트

    Raises:
        StorageError: DB 쿼리 실행 실패 시
    """
    with DatabaseExecutor(db_path) as executor:
        return executor.execute_query(query, params, operation)


def execute_single_update(
    db_path: Path,
    query: str,
    params: Tuple[Any, ...] = (),
    operation: str = "update"
) -> int:
    """단일 INSERT/UPDATE/DELETE 쿼리를 실행하는 편의 함수.

    Args:
        db_path: SQLite DB 파일 경로
        query: SQL 쿼리 문자열
        params: 쿼리 파라미터 튜플
        operation: 로깅용 작업 이름

    Returns:
        영향받은 행 수

    Raises:
        StorageError: DB 쿼리 실행 실패 시
    """
    with DatabaseExecutor(db_path) as executor:
        return executor.execute_update(query, params, operation)
