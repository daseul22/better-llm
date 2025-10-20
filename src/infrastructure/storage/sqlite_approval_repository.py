# -*- coding: utf-8 -*-
"""
SQLite 기반 승인 리포지토리 구현

SqliteApprovalRepository: SQLite 데이터베이스 기반 승인 및 피드백 리포지토리
"""

import logging
import sqlite3
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Tuple

from application.ports import IApprovalRepository
from domain.models.approval import ApprovalRequest, ApprovalResponse, ApprovalStatus, ApprovalType
from domain.models.feedback import Feedback
from infrastructure.storage.db_utils import DatabaseExecutor

logger = logging.getLogger(__name__)


class SqliteApprovalRepository(IApprovalRepository):
    """
    SQLite 데이터베이스 기반 승인 및 피드백 리포지토리

    Features:
    - 승인 요청 생성 및 조회
    - 승인 상태 업데이트
    - 피드백 기록
    - 외래키 제약조건
    - 인덱싱 최적화
    """

    def __init__(self, db_path: Path = Path("data/sessions.db")):
        """
        Args:
            db_path: 데이터베이스 파일 경로 (sessions.db와 동일)
        """
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _init_database(self) -> None:
        """
        데이터베이스 승인 및 피드백 테이블 생성

        Raises:
            RuntimeError: sessions 테이블이 존재하지 않는 경우
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # sessions 테이블 존재 및 스키마 검증
            cursor.execute("""
                SELECT sql FROM sqlite_master
                WHERE type='table' AND name='sessions'
            """)
            result = cursor.fetchone()
            if not result:
                raise RuntimeError(
                    "sessions 테이블이 존재하지 않습니다. "
                    "먼저 세션 마이그레이션을 실행하세요."
                )

            # Foreign key 활성화
            cursor.execute("PRAGMA foreign_keys = ON")

            # approvals 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS approvals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    approval_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    task_description TEXT NOT NULL,
                    context_data TEXT,
                    created_at TEXT NOT NULL,
                    responded_at TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                )
            """)

            # feedbacks 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS feedbacks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    approval_id INTEGER NOT NULL,
                    session_id TEXT NOT NULL,
                    feedback_content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (approval_id) REFERENCES approvals(id) ON DELETE CASCADE,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                )
            """)

            # 인덱스 생성
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_approvals_session
                ON approvals(session_id)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_approvals_status
                ON approvals(status)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_approvals_created_at
                ON approvals(created_at)
            """)

            # 복합 인덱스 추가 (세션별 대기 중인 승인 조회 최적화)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_approvals_session_status
                ON approvals(session_id, status)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_feedbacks_approval
                ON feedbacks(approval_id)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_feedbacks_session
                ON feedbacks(session_id)
            """)

            conn.commit()
            logger.debug("승인 및 피드백 테이블 초기화 완료")

    def _row_to_approval_request(self, row: tuple) -> ApprovalRequest:
        """
        데이터베이스 row를 ApprovalRequest 객체로 변환

        Args:
            row: 데이터베이스 쿼리 결과 튜플
                (id, session_id, approval_type, status, task_description,
                 context_data, created_at, responded_at)

        Returns:
            변환된 ApprovalRequest 객체

        Note:
            - responded_at이 None인 경우 처리
            - approval_type과 status는 Enum으로 변환
            - created_at과 responded_at은 datetime 객체로 변환
        """
        (id, session_id, approval_type, status, task_description,
         context_data, created_at, responded_at) = tuple(row)

        return ApprovalRequest(
            id=id,
            session_id=session_id,
            approval_type=ApprovalType(approval_type),
            status=ApprovalStatus(status),
            task_description=task_description,
            context_data=context_data,
            created_at=datetime.fromisoformat(created_at),
            responded_at=datetime.fromisoformat(responded_at) if responded_at else None
        )

    def create_approval_request(self, request: ApprovalRequest) -> ApprovalRequest:
        """
        승인 요청 생성

        Args:
            request: 승인 요청 객체 (id는 None)

        Returns:
            생성된 승인 요청 (id 포함)

        Raises:
            ValueError: 세션 ID가 존재하지 않는 경우
            Exception: DB 저장 실패 시
        """
        try:
            with DatabaseExecutor(self.db_path) as executor:
                # Foreign key 활성화
                executor.execute_update(
                    "PRAGMA foreign_keys = ON",
                    operation="enable foreign keys"
                )

                # 세션 존재 확인
                rows = executor.execute_query(
                    "SELECT session_id FROM sessions WHERE session_id = ?",
                    (request.session_id,),
                    operation=f"check session {request.session_id}"
                )
                if not rows:
                    raise ValueError(f"세션을 찾을 수 없습니다: {request.session_id}")

                # 승인 요청 삽입
                executor.execute_update(
                    """
                    INSERT INTO approvals
                    (session_id, approval_type, status, task_description, context_data, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        request.session_id,
                        request.approval_type.value,
                        request.status.value,
                        request.task_description,
                        request.context_data,
                        request.created_at.isoformat()
                    ),
                    operation="create approval request"
                )

                approval_id = executor.cursor.lastrowid

                # 생성된 객체 반환 (ID 포함) - 불변성 유지를 위해 새 인스턴스 생성
                created_request = replace(request, id=approval_id)
                logger.debug(f"승인 요청 생성 완료: {approval_id}")
                return created_request

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"승인 요청 생성 실패: {e}")
            raise

    def update_approval_status(
        self, approval_id: int, response: ApprovalResponse
    ) -> ApprovalRequest:
        """
        승인 상태 업데이트

        Args:
            approval_id: 승인 요청 ID
            response: 승인 응답 객체

        Returns:
            업데이트된 승인 요청

        Raises:
            ValueError: 승인 요청이 존재하지 않는 경우
            Exception: DB 업데이트 실패 시
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 승인 요청 존재 확인
                existing = self.get_approval_by_id(approval_id)
                if not existing:
                    raise ValueError(f"승인 요청을 찾을 수 없습니다: {approval_id}")

                # 상태 업데이트
                cursor.execute("""
                    UPDATE approvals
                    SET status = ?, responded_at = ?
                    WHERE id = ?
                """, (
                    response.status.value,
                    response.responded_at.isoformat(),
                    approval_id
                ))

                conn.commit()

                # 업데이트된 객체 조회 및 반환
                updated = self.get_approval_by_id(approval_id)
                logger.debug(f"승인 상태 업데이트 완료: {approval_id} -> {response.status.value}")
                return updated

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"승인 상태 업데이트 실패: {e}")
            raise

    def update_approval_with_feedback(
        self,
        approval_id: int,
        response: ApprovalResponse,
        feedback: Optional[Feedback] = None
    ) -> Tuple[ApprovalRequest, Optional[Feedback]]:
        """
        승인 상태 업데이트와 피드백 생성을 하나의 트랜잭션으로 처리

        Args:
            approval_id: 승인 요청 ID
            response: 승인 응답 객체
            feedback: 피드백 객체 (선택적)

        Returns:
            (업데이트된 승인 요청, 생성된 피드백) 튜플

        Raises:
            ValueError: 승인 요청이 존재하지 않는 경우
            Exception: DB 업데이트 실패 시
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 승인 요청 존재 확인
                existing = self.get_approval_by_id(approval_id)
                if not existing:
                    raise ValueError(f"승인 요청을 찾을 수 없습니다: {approval_id}")

                # 1. 승인 상태 업데이트
                cursor.execute("""
                    UPDATE approvals
                    SET status = ?, responded_at = ?
                    WHERE id = ?
                """, (
                    response.status.value,
                    response.responded_at.isoformat(),
                    approval_id
                ))

                # 2. 피드백 생성 (있는 경우)
                created_feedback = None
                if feedback:
                    cursor.execute("""
                        INSERT INTO feedbacks (approval_id, session_id, feedback_content, created_at)
                        VALUES (?, ?, ?, ?)
                    """, (
                        feedback.approval_id,
                        feedback.session_id,
                        feedback.feedback_content,
                        feedback.created_at.isoformat()
                    ))
                    feedback_id = cursor.lastrowid
                    created_feedback = replace(feedback, id=feedback_id)

                # 3. 트랜잭션 커밋
                conn.commit()

                # 4. 업데이트된 승인 요청 조회
                updated_approval = self.get_approval_by_id(approval_id)
                logger.debug(f"승인 응답 처리 완료: {approval_id} -> {response.status.value}")

                return updated_approval, created_feedback

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"승인 응답 처리 실패: {e}")
            raise

    def get_approval_by_id(self, approval_id: int) -> Optional[ApprovalRequest]:
        """
        ID로 승인 요청 조회

        Args:
            approval_id: 승인 요청 ID

        Returns:
            승인 요청 객체 (없으면 None)
        """
        try:
            with DatabaseExecutor(self.db_path) as executor:
                rows = executor.execute_query(
                    """
                    SELECT id, session_id, approval_type, status, task_description,
                           context_data, created_at, responded_at
                    FROM approvals
                    WHERE id = ?
                    """,
                    (approval_id,),
                    operation=f"get approval {approval_id}"
                )

                if not rows:
                    return None

                return self._row_to_approval_request(rows[0])

        except Exception as e:
            logger.error(f"승인 요청 조회 실패: {e}")
            return None

    def get_pending_approvals(self, session_id: Optional[str] = None) -> List[ApprovalRequest]:
        """
        대기 중인 승인 요청 목록 조회

        Args:
            session_id: 세션 ID (선택적, 없으면 전체 조회)

        Returns:
            대기 중인 승인 요청 목록 (생성일시 오름차순)
        """
        try:
            with DatabaseExecutor(self.db_path) as executor:
                if session_id:
                    rows = executor.execute_query(
                        """
                        SELECT id, session_id, approval_type, status, task_description,
                               context_data, created_at, responded_at
                        FROM approvals
                        WHERE status = ? AND session_id = ?
                        ORDER BY created_at ASC
                        """,
                        (ApprovalStatus.PENDING.value, session_id),
                        operation=f"get pending approvals for {session_id}"
                    )
                else:
                    rows = executor.execute_query(
                        """
                        SELECT id, session_id, approval_type, status, task_description,
                               context_data, created_at, responded_at
                        FROM approvals
                        WHERE status = ?
                        ORDER BY created_at ASC
                        """,
                        (ApprovalStatus.PENDING.value,),
                        operation="get all pending approvals"
                    )

                return [self._row_to_approval_request(row) for row in rows]

        except Exception as e:
            logger.error(f"대기 중인 승인 요청 조회 실패: {e}")
            raise

    def get_approval_history(self, session_id: str) -> List[ApprovalRequest]:
        """
        세션별 승인 이력 조회

        Args:
            session_id: 세션 ID

        Returns:
            승인 요청 목록 (생성일시 내림차순)
        """
        try:
            with DatabaseExecutor(self.db_path) as executor:
                rows = executor.execute_query(
                    """
                    SELECT id, session_id, approval_type, status, task_description,
                           context_data, created_at, responded_at
                    FROM approvals
                    WHERE session_id = ?
                    ORDER BY created_at DESC
                    """,
                    (session_id,),
                    operation=f"get approval history for {session_id}"
                )

                return [self._row_to_approval_request(row) for row in rows]

        except Exception as e:
            logger.error(f"승인 이력 조회 실패: {e}")
            raise

    def create_feedback(self, feedback: Feedback) -> Feedback:
        """
        피드백 생성

        Args:
            feedback: 피드백 객체 (id는 None)

        Returns:
            생성된 피드백 (id 포함)

        Raises:
            ValueError: 승인 요청이나 세션이 존재하지 않는 경우
            Exception: DB 저장 실패 시
        """
        try:
            with DatabaseExecutor(self.db_path) as executor:
                # Foreign key 활성화
                executor.execute_update(
                    "PRAGMA foreign_keys = ON",
                    operation="enable foreign keys"
                )

                # 승인 요청 존재 확인
                rows = executor.execute_query(
                    "SELECT id FROM approvals WHERE id = ?",
                    (feedback.approval_id,),
                    operation=f"check approval {feedback.approval_id}"
                )
                if not rows:
                    raise ValueError(f"승인 요청을 찾을 수 없습니다: {feedback.approval_id}")

                # 세션 존재 확인
                rows = executor.execute_query(
                    "SELECT session_id FROM sessions WHERE session_id = ?",
                    (feedback.session_id,),
                    operation=f"check session {feedback.session_id}"
                )
                if not rows:
                    raise ValueError(f"세션을 찾을 수 없습니다: {feedback.session_id}")

                # 피드백 삽입
                executor.execute_update(
                    """
                    INSERT INTO feedbacks
                    (approval_id, session_id, feedback_content, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        feedback.approval_id,
                        feedback.session_id,
                        feedback.feedback_content,
                        feedback.created_at.isoformat()
                    ),
                    operation="create feedback"
                )

                feedback_id = executor.cursor.lastrowid

                # 생성된 객체 반환 (ID 포함) - 불변성 유지를 위해 새 인스턴스 생성
                created_feedback = replace(feedback, id=feedback_id)
                logger.debug(f"피드백 생성 완료: {feedback_id}")
                return created_feedback

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"피드백 생성 실패: {e}")
            raise

    def get_feedbacks_by_approval(self, approval_id: int) -> List[Feedback]:
        """
        승인 요청별 피드백 조회

        Args:
            approval_id: 승인 요청 ID

        Returns:
            피드백 목록 (생성일시 오름차순)
        """
        try:
            with DatabaseExecutor(self.db_path) as executor:
                rows = executor.execute_query(
                    """
                    SELECT id, approval_id, session_id, feedback_content, created_at
                    FROM feedbacks
                    WHERE approval_id = ?
                    ORDER BY created_at ASC
                    """,
                    (approval_id,),
                    operation=f"get feedbacks for approval {approval_id}"
                )

                feedbacks = []
                for row in rows:
                    id, approval_id, session_id, feedback_content, created_at = tuple(row)

                    feedbacks.append(Feedback(
                        id=id,
                        approval_id=approval_id,
                        session_id=session_id,
                        feedback_content=feedback_content,
                        created_at=datetime.fromisoformat(created_at)
                    ))

                return feedbacks

        except Exception as e:
            logger.error(f"피드백 조회 실패 (승인 요청별): {e}")
            raise

    def get_feedbacks_by_session(self, session_id: str) -> List[Feedback]:
        """
        세션별 피드백 조회

        Args:
            session_id: 세션 ID

        Returns:
            피드백 목록 (생성일시 내림차순)
        """
        try:
            with DatabaseExecutor(self.db_path) as executor:
                rows = executor.execute_query(
                    """
                    SELECT id, approval_id, session_id, feedback_content, created_at
                    FROM feedbacks
                    WHERE session_id = ?
                    ORDER BY created_at DESC
                    """,
                    (session_id,),
                    operation=f"get feedbacks for session {session_id}"
                )

                feedbacks = []
                for row in rows:
                    id, approval_id, session_id, feedback_content, created_at = tuple(row)

                    feedbacks.append(Feedback(
                        id=id,
                        approval_id=approval_id,
                        session_id=session_id,
                        feedback_content=feedback_content,
                        created_at=datetime.fromisoformat(created_at)
                    ))

                return feedbacks

        except Exception as e:
            logger.error(f"피드백 조회 실패 (세션별): {e}")
            raise
