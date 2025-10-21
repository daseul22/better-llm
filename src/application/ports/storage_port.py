"""
저장소 포트 (인터페이스)

ISessionRepository: 세션 히스토리 저장소 인터페이스
IContextRepository: 프로젝트 컨텍스트 저장소 인터페이스
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, List

from src.domain.models import SessionResult, SessionMetadata, SessionSearchCriteria, SessionDetail
from src.domain.services import ConversationHistory, ProjectContext


class ISessionRepository(ABC):
    """
    세션 저장소 인터페이스

    Infrastructure 계층에서 구현됨 (JSON, DB 등)
    """

    @abstractmethod
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

        Raises:
            Exception: 저장 실패 시
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass


class IContextRepository(ABC):
    """
    프로젝트 컨텍스트 저장소 인터페이스

    Infrastructure 계층에서 구현됨 (JSON, DB 등)
    """

    @abstractmethod
    def load(self) -> Optional[ProjectContext]:
        """
        프로젝트 컨텍스트 로드

        Returns:
            ProjectContext 또는 None (파일 없을 경우)

        Raises:
            Exception: 로드 실패 시
        """
        pass

    @abstractmethod
    def save(self, context: ProjectContext) -> None:
        """
        프로젝트 컨텍스트 저장

        Args:
            context: 저장할 컨텍스트

        Raises:
            Exception: 저장 실패 시
        """
        pass
