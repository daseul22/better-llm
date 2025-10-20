"""
SQLite 기반 세션 리포지토리 구현

SqliteSessionRepository: SQLite 데이터베이스 기반 세션 리포지토리
FTS5를 사용한 전문 검색 지원
"""

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from application.ports import ISessionRepository
from domain.models import (
    SessionResult,
    SessionMetadata,
    SessionSearchCriteria,
    SessionDetail
)
from domain.services import ConversationHistory

logger = logging.getLogger(__name__)


class SqliteSessionRepository(ISessionRepository):
    """
    SQLite 데이터베이스 기반 세션 리포지토리

    Features:
    - FTS5 전문 검색
    - 외래키 제약조건
    - 인덱싱 최적화
    """

    def __init__(self, db_path: Path = Path("data/sessions.db")):
        """
        Args:
            db_path: 데이터베이스 파일 경로
        """
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _init_database(self) -> None:
        """데이터베이스 기본 테이블 생성"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Foreign key 활성화
            cursor.execute("PRAGMA foreign_keys = ON")

            # sessions 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    completed_at TEXT NOT NULL,
                    user_request TEXT NOT NULL,
                    status TEXT NOT NULL,
                    total_turns INTEGER NOT NULL,
                    tests_passed INTEGER,
                    error_message TEXT
                )
            """)

            # messages 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    agent_name TEXT,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                )
            """)

            # session_files 테이블 (수정 파일)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS session_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                )
            """)

            # session_agents 테이블 (사용 에이전트)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS session_agents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    agent_name TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE,
                    UNIQUE(session_id, agent_name)
                )
            """)

            # FTS5 가상 테이블 (전문 검색용)
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS sessions_fts USING fts5(
                    session_id UNINDEXED,
                    user_request,
                    message_content,
                    content='',
                    tokenize='porter unicode61'
                )
            """)

            # 인덱스 생성
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_created_at
                ON sessions(created_at DESC)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_status
                ON sessions(status)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_session_id
                ON messages(session_id)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_session_agents_session_id
                ON session_agents(session_id)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_session_agents_agent_name
                ON session_agents(agent_name)
            """)

            conn.commit()
            logger.info(f"데이터베이스 기본 설정 완료: {self.db_path}")

    def _escape_fts_keyword(self, keyword: str) -> str:
        """
        FTS5 특수문자 이스케이프

        Args:
            keyword: 검색 키워드

        Returns:
            이스케이프된 키워드
        """
        return keyword.replace('"', '""')

    def save(
        self,
        session_id: str,
        user_request: str,
        history: ConversationHistory,
        result: SessionResult
    ) -> Path:
        """
        세션 데이터를 저장

        Args:
            session_id: 세션 ID
            user_request: 사용자 요청
            history: 대화 히스토리
            result: 작업 결과

        Returns:
            저장된 파일 경로 (데이터베이스 경로)

        Raises:
            Exception: 저장 실패 시
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 세션 메타데이터 추출
                created_at = history.messages[0].timestamp if history.messages else datetime.now()
                completed_at = datetime.now()
                total_turns = sum(1 for msg in history.messages if msg.role == "agent")

                # 에이전트 목록 추출
                agents_used = list(set(
                    msg.agent_name for msg in history.messages
                    if msg.role == "agent" and msg.agent_name
                ))

                # 중복 데이터 삭제 (세션 재저장 시)
                cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
                cursor.execute("DELETE FROM session_files WHERE session_id = ?", (session_id,))
                cursor.execute("DELETE FROM session_agents WHERE session_id = ?", (session_id,))
                cursor.execute("DELETE FROM sessions_fts WHERE session_id = ?", (session_id,))

                # sessions 테이블 삽입
                cursor.execute("""
                    INSERT OR REPLACE INTO sessions
                    (session_id, created_at, completed_at, user_request, status,
                     total_turns, tests_passed, error_message)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    session_id,
                    created_at.isoformat(),
                    completed_at.isoformat(),
                    user_request,
                    result.status.value,
                    total_turns,
                    1 if result.tests_passed else 0 if result.tests_passed is False else None,
                    result.error_message
                ))

                # messages 테이블 삽입
                for msg in history.messages:
                    cursor.execute("""
                        INSERT INTO messages
                        (session_id, role, content, agent_name, timestamp)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        session_id,
                        msg.role,
                        msg.content,
                        msg.agent_name,
                        msg.timestamp.isoformat()
                    ))

                # session_files 테이블 삽입
                for file_path in result.files_modified:
                    cursor.execute("""
                        INSERT INTO session_files (session_id, file_path)
                        VALUES (?, ?)
                    """, (session_id, file_path))

                # session_agents 테이블 삽입
                for agent_name in agents_used:
                    cursor.execute("""
                        INSERT OR IGNORE INTO session_agents (session_id, agent_name)
                        VALUES (?, ?)
                    """, (session_id, agent_name))

                # FTS5 테이블 업데이트
                message_content = " ".join(msg.content for msg in history.messages)
                cursor.execute("""
                    INSERT INTO sessions_fts (session_id, user_request, message_content)
                    VALUES (?, ?, ?)
                """, (session_id, user_request, message_content))

                conn.commit()
                logger.info(f"새 세션 저장 완료: {session_id}")
                return self.db_path

        except Exception as e:
            logger.error(f"세션 저장 실패: {e}")
            raise

    def load(self, session_id: str) -> Optional[ConversationHistory]:
        """
        세션 히스토리 로드

        Args:
            session_id: 세션 ID

        Returns:
            대화 히스토리 또는 None

        Raises:
            Exception: 로드 실패 시
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 세션 존재 확인
                cursor.execute("""
                    SELECT session_id FROM sessions WHERE session_id = ?
                """, (session_id,))

                if not cursor.fetchone():
                    logger.warning(f"세션을 찾을 수 없습니다: {session_id}")
                    return None

                # 메시지 조회
                cursor.execute("""
                    SELECT role, content, agent_name, timestamp
                    FROM messages
                    WHERE session_id = ?
                    ORDER BY id ASC
                """, (session_id,))

                messages = []
                for row in cursor.fetchall():
                    role, content, agent_name, timestamp = row
                    messages.append({
                        "role": role,
                        "content": content,
                        "agent_name": agent_name,
                        "timestamp": timestamp
                    })

                history_data = {
                    "max_length": 50,
                    "messages": messages
                }

                return ConversationHistory.from_dict(history_data)

        except Exception as e:
            logger.error(f"세션 로드 실패: {e}")
            return None

    def search_sessions(self, criteria: SessionSearchCriteria) -> List[SessionMetadata]:
        """
        세션 검색

        Args:
            criteria: 검색 조건

        Returns:
            검색된 세션 메타데이터 목록

        Raises:
            Exception: 검색 실패 시
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 기본 쿼리 (JOIN으로 N+1 문제 해결)
                query = """
                    SELECT DISTINCT s.session_id, s.created_at, s.completed_at,
                           s.user_request, s.status, s.total_turns,
                           s.tests_passed, s.error_message,
                           GROUP_CONCAT(DISTINCT sa.agent_name) as agents,
                           GROUP_CONCAT(DISTINCT sf.file_path) as files
                    FROM sessions s
                    LEFT JOIN session_agents sa ON s.session_id = sa.session_id
                    LEFT JOIN session_files sf ON s.session_id = sf.session_id
                """

                conditions = []
                params = []

                # 키워드 검색 (FTS5)
                if criteria.keyword:
                    escaped_keyword = self._escape_fts_keyword(criteria.keyword)
                    query = """
                        SELECT DISTINCT s.session_id, s.created_at, s.completed_at,
                               s.user_request, s.status, s.total_turns,
                               s.tests_passed, s.error_message,
                               GROUP_CONCAT(DISTINCT sa.agent_name) as agents,
                               GROUP_CONCAT(DISTINCT sf.file_path) as files
                        FROM sessions s
                        JOIN sessions_fts fts ON s.session_id = fts.session_id
                        LEFT JOIN session_agents sa ON s.session_id = sa.session_id
                        LEFT JOIN session_files sf ON s.session_id = sf.session_id
                    """
                    conditions.append("sessions_fts MATCH ?")
                    params.append(escaped_keyword)

                # 상태 필터
                if criteria.status:
                    conditions.append("s.status = ?")
                    params.append(criteria.status)

                # 에이전트 필터
                if criteria.agent_name:
                    conditions.append("sa.agent_name = ?")
                    params.append(criteria.agent_name)

                # 날짜 필터
                if criteria.date_from:
                    conditions.append("s.created_at >= ?")
                    params.append(criteria.date_from)

                if criteria.date_to:
                    # 종료일을 포함하기 위해 다음 날까지 포함
                    date_to_inclusive = datetime.strptime(
                        criteria.date_to, "%Y-%m-%d"
                    )
                    from datetime import timedelta
                    date_to_inclusive += timedelta(days=1)
                    conditions.append("s.created_at < ?")
                    params.append(date_to_inclusive.strftime("%Y-%m-%d"))

                # WHERE 절 추가
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)

                # GROUP BY 추가
                query += " GROUP BY s.session_id"

                # 정렬 및 페이징
                query += " ORDER BY s.created_at DESC LIMIT ? OFFSET ?"
                params.extend([criteria.limit, criteria.offset])

                cursor.execute(query, params)

                sessions = []
                for row in cursor.fetchall():
                    (session_id, created_at, completed_at, user_request,
                     status, total_turns, tests_passed, error_message,
                     agents_str, files_str) = row

                    # 에이전트 목록 파싱
                    agents_used = sorted(agents_str.split(',')) if agents_str else []

                    # 파일 목록 파싱
                    files_modified = files_str.split(',') if files_str else []

                    sessions.append(SessionMetadata(
                        session_id=session_id,
                        created_at=datetime.fromisoformat(created_at),
                        completed_at=datetime.fromisoformat(completed_at),
                        user_request=user_request,
                        status=status,
                        total_turns=total_turns,
                        agents_used=agents_used,
                        files_modified=files_modified,
                        tests_passed=bool(tests_passed) if tests_passed is not None else None,
                        error_message=error_message
                    ))

                return sessions

        except Exception as e:
            logger.error(f"세션 검색 실패: {e}")
            raise

    def get_session_detail(self, session_id: str) -> Optional[SessionDetail]:
        """
        세션 상세 정보 조회

        Args:
            session_id: 세션 ID

        Returns:
            세션 상세 정보 또는 None

        Raises:
            Exception: 조회 실패 시
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 세션 메타데이터 조회
                cursor.execute("""
                    SELECT session_id, created_at, completed_at, user_request,
                           status, total_turns, tests_passed, error_message
                    FROM sessions
                    WHERE session_id = ?
                """, (session_id,))

                row = cursor.fetchone()
                if not row:
                    logger.warning(f"세션을 찾을 수 없습니다: {session_id}")
                    return None

                (session_id, created_at, completed_at, user_request,
                 status, total_turns, tests_passed, error_message) = row

                # 에이전트 목록 조회
                cursor.execute("""
                    SELECT agent_name FROM session_agents
                    WHERE session_id = ?
                """, (session_id,))
                agents_used = [r[0] for r in cursor.fetchall()]

                # 파일 목록 조회
                cursor.execute("""
                    SELECT file_path FROM session_files
                    WHERE session_id = ?
                """, (session_id,))
                files_modified = [r[0] for r in cursor.fetchall()]

                # 메타데이터 생성
                metadata = SessionMetadata(
                    session_id=session_id,
                    created_at=datetime.fromisoformat(created_at),
                    completed_at=datetime.fromisoformat(completed_at),
                    user_request=user_request,
                    status=status,
                    total_turns=total_turns,
                    agents_used=sorted(agents_used),
                    files_modified=files_modified,
                    tests_passed=bool(tests_passed) if tests_passed is not None else None,
                    error_message=error_message
                )

                # 메시지 조회
                cursor.execute("""
                    SELECT role, content, agent_name, timestamp
                    FROM messages
                    WHERE session_id = ?
                    ORDER BY id ASC
                """, (session_id,))

                messages = []
                for row in cursor.fetchall():
                    role, content, agent_name, timestamp = row
                    messages.append({
                        "role": role,
                        "content": content,
                        "agent_name": agent_name,
                        "timestamp": timestamp
                    })

                return SessionDetail(metadata=metadata, messages=messages)

        except Exception as e:
            logger.error(f"세션 상세 조회 실패: {e}")
            raise

    def list_sessions(self, limit: int = 50, offset: int = 0) -> List[SessionMetadata]:
        """
        세션 목록 조회 (최신순)

        Args:
            limit: 최대 결과 수
            offset: 결과 오프셋

        Returns:
            세션 메타데이터 목록

        Raises:
            Exception: 조회 실패 시
        """
        criteria = SessionSearchCriteria(limit=limit, offset=offset)
        return self.search_sessions(criteria)

    def delete_session(self, session_id: str) -> bool:
        """
        세션 삭제

        Args:
            session_id: 세션 ID

        Returns:
            삭제 성공 여부

        Raises:
            Exception: 삭제 실패 시
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Foreign key 활성화
                cursor.execute("PRAGMA foreign_keys = ON")

                # 세션 존재 확인
                cursor.execute("""
                    SELECT session_id FROM sessions WHERE session_id = ?
                """, (session_id,))

                if not cursor.fetchone():
                    logger.warning(f"세션을 찾을 수 없습니다: {session_id}")
                    return False

                # 세션 삭제 (CASCADE로 관련 데이터 자동 삭제)
                cursor.execute("""
                    DELETE FROM sessions WHERE session_id = ?
                """, (session_id,))

                # FTS 테이블에서도 삭제
                cursor.execute("""
                    DELETE FROM sessions_fts WHERE session_id = ?
                """, (session_id,))

                conn.commit()
                logger.info(f"세션 삭제 완료: {session_id}")
                return True

        except Exception as e:
            logger.error(f"세션 삭제 실패: {e}")
            raise
