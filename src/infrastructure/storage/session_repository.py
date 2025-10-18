"""
세션 저장소 구현

JsonSessionRepository: JSON 파일 기반 세션 저장소
"""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from ...application.ports import ISessionRepository
from ...domain.models import SessionResult
from ...domain.services import ConversationHistory

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
