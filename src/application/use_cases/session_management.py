"""
세션 관련 Use Cases

SessionSearchUseCase: 세션 검색
SessionReplayUseCase: 세션 재생
SessionAnalyticsUseCase: 세션 분석
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from collections import Counter

from ..ports import ISessionRepository
from domain.models import SessionMetadata, SessionSearchCriteria, SessionDetail

logger = logging.getLogger(__name__)


class SessionSearchUseCase:
    """
    세션 검색 Use Case

    키워드, 상태, 날짜, 에이전트로 세션을 검색합니다.
    """

    def __init__(self, session_repository: ISessionRepository):
        """
        Args:
            session_repository: 세션 저장소 리포지토리
        """
        self.session_repository = session_repository

    def execute(self, criteria: SessionSearchCriteria) -> List[SessionMetadata]:
        """
        세션 검색 실행

        Args:
            criteria: 검색 조건

        Returns:
            검색된 세션 메타데이터 목록

        Raises:
            ValueError: 검색 조건이 유효하지 않은 경우
            Exception: 검색 실패 시
        """
        # 입력 검증
        self._validate_criteria(criteria)

        try:
            # 리포지토리로 위임 검색
            sessions = self.session_repository.search_sessions(criteria)
            logger.info(f"세션 검색 완료: {len(sessions)} 건")
            return sessions

        except Exception as e:
            logger.error(f"세션 검색 실패: {e}")
            raise

    def _validate_criteria(self, criteria: SessionSearchCriteria) -> None:
        """
        검색 조건 검증

        Args:
            criteria: 검색 조건

        Raises:
            ValueError: 검색 조건이 유효하지 않은 경우
        """
        if criteria.limit <= 0:
            raise ValueError("limit은 양수여야 합니다")

        if criteria.offset < 0:
            raise ValueError("offset은 0 이상이어야 합니다")

        # 날짜 형식 검증
        if criteria.date_from:
            try:
                datetime.strptime(criteria.date_from, "%Y-%m-%d")
            except ValueError:
                raise ValueError("date_from 형식 오류입니다 (YYYY-MM-DD)")

        if criteria.date_to:
            try:
                datetime.strptime(criteria.date_to, "%Y-%m-%d")
            except ValueError:
                raise ValueError("date_to 형식 오류입니다 (YYYY-MM-DD)")


class SessionReplayUseCase:
    """
    세션 재생 Use Case

    특정 세션의 전체 대화를 조회합니다.
    """

    def __init__(self, session_repository: ISessionRepository):
        """
        Args:
            session_repository: 세션 저장소 리포지토리
        """
        self.session_repository = session_repository

    def execute(self, session_id: str) -> Optional[SessionDetail]:
        """
        세션 재생 실행

        Args:
            session_id: 세션 ID

        Returns:
            세션 상세 정보 또는 None

        Raises:
            ValueError: 세션 ID가 유효하지 않은 경우
            Exception: 조회 실패 시
        """
        # 입력 검증
        if not session_id or not session_id.strip():
            raise ValueError("세션 ID가 필요합니다")

        try:
            # 리포지토리로 위임 조회
            detail = self.session_repository.get_session_detail(session_id)

            if detail:
                logger.info(f"세션 조회 완료: {session_id}")
            else:
                logger.warning(f"세션을 찾을 수 없습니다: {session_id}")

            return detail

        except Exception as e:
            logger.error(f"세션 조회 실패: {e}")
            raise

    def format_for_display(self, detail: SessionDetail) -> str:
        """
        세션 상세 정보를 사람이 읽기 쉬운 형식으로 포맷

        Args:
            detail: 세션 상세 정보

        Returns:
            포맷된 문자열
        """
        lines = []
        lines.append(f"세션 ID: {detail.metadata.session_id}")
        lines.append(f"사용자 요청: {detail.metadata.user_request}")
        lines.append(f"상태: {detail.metadata.status}")
        lines.append(f"생성 시각: {detail.metadata.created_at}")
        lines.append(f"완료 시각: {detail.metadata.completed_at}")
        lines.append(f"총 턴 수: {detail.metadata.total_turns}")
        lines.append(f"사용 에이전트: {', '.join(detail.metadata.agents_used)}")

        if detail.metadata.files_modified:
            lines.append(f"수정 파일: {', '.join(detail.metadata.files_modified)}")

        if detail.metadata.tests_passed is not None:
            lines.append(f"테스트 통과: {detail.metadata.tests_passed}")

        if detail.metadata.error_message:
            lines.append(f"에러 메시지: {detail.metadata.error_message}")

        lines.append("\n--- 전체 대화 이력 ---\n")

        for msg in detail.messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            agent_name = msg.get("agent_name", "")

            if role == "user":
                lines.append(f"[사용자] {content}")
            elif role == "agent":
                lines.append(f"[{agent_name}] {content}")
            else:
                lines.append(f"[{role}] {content}")

        return "\n".join(lines)


class SessionAnalyticsUseCase:
    """
    세션 분석 Use Case

    세션 통계 및 분석 정보를 제공합니다.
    """

    def __init__(self, session_repository: ISessionRepository):
        """
        Args:
            session_repository: 세션 저장소 리포지토리
        """
        self.session_repository = session_repository

    def get_summary_stats(self, days: int = 30) -> Dict[str, Any]:
        """
        요약 통계 조회

        Args:
            days: 조회 기간 (일)

        Returns:
            통계 정보 딕셔너리

        Raises:
            ValueError: 조회 기간이 유효하지 않은 경우
            Exception: 조회 실패 시
        """
        if days <= 0:
            raise ValueError("조회 기간은 양수여야 합니다")

        try:
            # 최근 N일간 세션 조회
            date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            criteria = SessionSearchCriteria(
                date_from=date_from,
                limit=1000  # 충분히 큰 값
            )

            sessions = self.session_repository.search_sessions(criteria)

            # 통계 계산
            stats = self._calculate_stats(sessions)
            stats["period_days"] = days
            stats["date_from"] = date_from

            logger.info(f"통계 조회 완료: {len(sessions)} 세션")
            return stats

        except Exception as e:
            logger.error(f"통계 조회 실패: {e}")
            raise

    def _calculate_stats(self, sessions: List[SessionMetadata]) -> Dict[str, Any]:
        """
        통계 계산

        Args:
            sessions: 세션 메타데이터 목록

        Returns:
            통계 정보 딕셔너리
        """
        if not sessions:
            return {
                "total_sessions": 0,
                "status_distribution": {},
                "agent_usage": {},
                "avg_turns": 0,
                "success_rate": 0,
                "total_files_modified": 0
            }

        # 상태 분포
        status_counter = Counter(s.status for s in sessions)

        # 에이전트 사용 빈도
        agent_counter = Counter()
        for session in sessions:
            agent_counter.update(session.agents_used)

        # 평균 턴 수
        avg_turns = sum(s.total_turns for s in sessions) / len(sessions)

        # 성공률 (completed 상태인 세션 비율)
        success_count = status_counter.get("completed", 0)
        success_rate = success_count / len(sessions) * 100

        # 총 수정 파일 수
        total_files = sum(len(s.files_modified) for s in sessions)

        return {
            "total_sessions": len(sessions),
            "status_distribution": dict(status_counter),
            "agent_usage": dict(agent_counter.most_common(10)),  # 상위 10
            "avg_turns": round(avg_turns, 2),
            "success_rate": round(success_rate, 2),
            "total_files_modified": total_files
        }

    def get_agent_performance(self, agent_name: str, days: int = 30) -> Dict[str, Any]:
        """
        특정 에이전트의 성능 분석

        Args:
            agent_name: 에이전트 이름
            days: 조회 기간 (일)

        Returns:
            에이전트 성능 통계

        Raises:
            ValueError: 입력값이 유효하지 않은 경우
            Exception: 조회 실패 시
        """
        if not agent_name or not agent_name.strip():
            raise ValueError("에이전트 이름이 필요합니다")

        if days <= 0:
            raise ValueError("조회 기간은 양수여야 합니다")

        try:
            # 해당 에이전트를 사용한 세션 조회
            date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            criteria = SessionSearchCriteria(
                agent_name=agent_name,
                date_from=date_from,
                limit=1000
            )

            sessions = self.session_repository.search_sessions(criteria)

            # 성능 통계 계산
            performance = self._calculate_agent_performance(sessions, agent_name)
            performance["period_days"] = days
            performance["date_from"] = date_from

            logger.info(f"에이전트 성능 조회 완료: {agent_name}")
            return performance

        except Exception as e:
            logger.error(f"에이전트 성능 조회 실패: {e}")
            raise

    def _calculate_agent_performance(
        self,
        sessions: List[SessionMetadata],
        agent_name: str
    ) -> Dict[str, Any]:
        """
        에이전트 성능 계산

        Args:
            sessions: 세션 메타데이터 목록
            agent_name: 에이전트 이름

        Returns:
            성능 통계 딕셔너리
        """
        if not sessions:
            return {
                "agent_name": agent_name,
                "total_uses": 0,
                "success_rate": 0,
                "avg_turns": 0,
                "status_distribution": {}
            }

        # 상태 분포
        status_counter = Counter(s.status for s in sessions)

        # 평균 턴 수
        avg_turns = sum(s.total_turns for s in sessions) / len(sessions)

        # 성공률
        success_count = status_counter.get("completed", 0)
        success_rate = success_count / len(sessions) * 100

        return {
            "agent_name": agent_name,
            "total_uses": len(sessions),
            "success_rate": round(success_rate, 2),
            "avg_turns": round(avg_turns, 2),
            "status_distribution": dict(status_counter)
        }
