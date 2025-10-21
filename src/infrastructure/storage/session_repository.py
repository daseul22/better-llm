"""
세션 저장소 구현

JsonSessionRepository: JSON 파일 기반 세션 저장소
"""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from src.application.ports import ISessionRepository
from src.domain.models import (
    SessionResult,
    SessionMetadata,
    SessionSearchCriteria,
    SessionDetail
)
from src.domain.services import ConversationHistory

logger = logging.getLogger(__name__)


class JsonSessionRepository(ISessionRepository):
    """
    JSON 파일 기반 세션 저장소

    sessions/ 디렉토리에 JSON 파일로 저장
    """

    def __init__(self, sessions_dir: Path = Path("sessions")):
        """
        Args:
            sessions_dir: 세션 디렉토리
        """
        self.sessions_dir = sessions_dir
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        session_id: str,
        user_request: str,
        history: ConversationHistory,
        result: SessionResult
    ) -> Path:
        """
        세션 히스토리 저장

        Args:
            session_id: 세션 ID
            user_request: 사용자 요청
            history: 대화 히스토리
            result: 작업 결과

        Returns:
            저장된 파일 경로
        """
        filename = self._create_filename(session_id, user_request)
        filepath = self.sessions_dir / filename

        # 대화 히스토리에서 에이전트 사용 목록 추출
        agents_used = list(set(
            msg.agent_name for msg in history.messages
            if msg.role == "agent" and msg.agent_name
        ))

        session_data = {
            "session_id": session_id,
            "created_at": history.messages[0].timestamp.isoformat() if history.messages else datetime.now().isoformat(),
            "completed_at": datetime.now().isoformat(),
            "user_request": user_request,
            "total_turns": sum(1 for msg in history.messages if msg.role == "agent"),
            "agents_used": sorted(agents_used),
            "messages": [msg.to_dict() for msg in history.messages],
            "result": result.to_dict()
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)

        logger.info(f"✅ 세션 저장 완료: {filepath}")
        return filepath

    def load(self, session_id: str) -> Optional[ConversationHistory]:
        """
        세션 히스토리 로드

        Args:
            session_id: 세션 ID

        Returns:
            대화 히스토리 또는 None
        """
        # 세션 ID로 파일 검색
        pattern = f"session_{session_id}_*.json"
        files = list(self.sessions_dir.glob(pattern))

        if not files:
            logger.warning(f"세션을 찾을 수 없습니다: {session_id}")
            return None

        filepath = files[0]
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            history_data = {
                "max_length": 50,
                "messages": data.get("messages", [])
            }

            return ConversationHistory.from_dict(history_data)

        except Exception as e:
            logger.error(f"세션 로드 실패: {e}")
            return None

    def _create_filename(self, session_id: str, user_request: str) -> str:
        """
        세션 히스토리 파일명 생성

        Args:
            session_id: 세션 ID
            user_request: 사용자 요청 (요약용)

        Returns:
            파일명 (예: session_abc123_20250118_145030_작업설명.json)
        """
        # 사용자 요청을 파일명으로 사용 가능한 형태로 변환
        safe_request = "".join(c for c in user_request if c.isalnum() or c.isspace())
        safe_request = safe_request.replace(" ", "")[:20]

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"session_{session_id}_{timestamp}_{safe_request}.json"

    def search_sessions(self, criteria: SessionSearchCriteria) -> List[SessionMetadata]:
        """
        세션 검색 (간단한 필터링)

        Note: JSON 파일 기반이므로 전문 검색은 제한적입니다.
        SQLite 저장소를 사용하면 더 나은 검색 기능을 사용할 수 있습니다.

        Args:
            criteria: 검색 조건

        Returns:
            검색된 세션 메타데이터 목록
        """
        sessions = []

        # 모든 JSON 파일 읽기
        for json_file in sorted(self.sessions_dir.glob("session_*.json"), reverse=True):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # 메타데이터 추출
                metadata = self._extract_metadata(data)

                # 필터 적용
                if not self._matches_criteria(metadata, criteria):
                    continue

                sessions.append(metadata)

                # 제한 확인
                if len(sessions) >= criteria.limit + criteria.offset:
                    break

            except Exception as e:
                logger.error(f"세션 파일 읽기 실패: {json_file} - {e}")
                continue

        # 오프셋 적용
        return sessions[criteria.offset:criteria.offset + criteria.limit]

    def get_session_detail(self, session_id: str) -> Optional[SessionDetail]:
        """
        세션 상세 정보 조회

        Args:
            session_id: 세션 ID

        Returns:
            세션 상세 정보 또는 None
        """
        # 세션 ID로 파일 검색
        pattern = f"session_{session_id}_*.json"
        files = list(self.sessions_dir.glob(pattern))

        if not files:
            logger.warning(f"세션을 찾을 수 없습니다: {session_id}")
            return None

        try:
            with open(files[0], 'r', encoding='utf-8') as f:
                data = json.load(f)

            metadata = self._extract_metadata(data)
            messages = data.get("messages", [])

            return SessionDetail(metadata=metadata, messages=messages)

        except Exception as e:
            logger.error(f"세션 상세 조회 실패: {e}")
            return None

    def list_sessions(self, limit: int = 50, offset: int = 0) -> List[SessionMetadata]:
        """
        세션 목록 조회 (최신순)

        Args:
            limit: 최대 결과 수
            offset: 결과 오프셋

        Returns:
            세션 메타데이터 목록
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
        """
        # 세션 ID로 파일 검색
        pattern = f"session_{session_id}_*.json"
        files = list(self.sessions_dir.glob(pattern))

        if not files:
            logger.warning(f"세션을 찾을 수 없습니다: {session_id}")
            return False

        try:
            files[0].unlink()
            logger.info(f"세션 삭제 완료: {session_id}")
            return True

        except Exception as e:
            logger.error(f"세션 삭제 실패: {e}")
            return False

    def _extract_metadata(self, data: dict) -> SessionMetadata:
        """
        JSON 데이터에서 메타데이터 추출

        Args:
            data: JSON 세션 데이터

        Returns:
            SessionMetadata 객체
        """
        result_data = data.get("result", {})

        return SessionMetadata(
            session_id=data["session_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            completed_at=datetime.fromisoformat(data["completed_at"]),
            user_request=data["user_request"],
            status=result_data.get("status", "completed"),
            total_turns=data.get("total_turns", 0),
            agents_used=data.get("agents_used", []),
            files_modified=result_data.get("files_modified", []),
            tests_passed=result_data.get("tests_passed"),
            error_message=result_data.get("error_message")
        )

    def _matches_criteria(self, metadata: SessionMetadata, criteria: SessionSearchCriteria) -> bool:
        """
        메타데이터가 검색 조건과 일치하는지 확인

        Args:
            metadata: 세션 메타데이터
            criteria: 검색 조건

        Returns:
            일치 여부
        """
        # 키워드 검색 (단순 문자열 검색)
        if criteria.keyword:
            keyword_lower = criteria.keyword.lower()
            if keyword_lower not in metadata.user_request.lower():
                return False

        # 상태 필터
        if criteria.status and metadata.status != criteria.status:
            return False

        # 에이전트 필터
        if criteria.agent_name and criteria.agent_name not in metadata.agents_used:
            return False

        # 날짜 필터
        if criteria.date_from:
            date_from = datetime.strptime(criteria.date_from, "%Y-%m-%d")
            if metadata.created_at < date_from:
                return False

        if criteria.date_to:
            date_to = datetime.strptime(criteria.date_to, "%Y-%m-%d")
            # 종료일 포함
            from datetime import timedelta
            date_to_inclusive = date_to + timedelta(days=1)
            if metadata.created_at >= date_to_inclusive:
                return False

        return True
