"""
승인 저장소 인터페이스 (Port)

IApprovalRepository: 승인 요청 및 피드백 저장소 인터페이스
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from domain.models.approval import ApprovalRequest, ApprovalResponse, ApprovalStatus
from domain.models.feedback import Feedback


class IApprovalRepository(ABC):
    """
    승인 요청 및 피드백 저장소 인터페이스

    Infrastructure 계층에서 SQLiteApprovalRepository로 구현됨
    """

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def get_approval_by_id(self, approval_id: int) -> Optional[ApprovalRequest]:
        """
        ID로 승인 요청 조회

        Args:
            approval_id: 승인 요청 ID

        Returns:
            승인 요청 객체 (없으면 None)
        """
        pass

    @abstractmethod
    def get_pending_approvals(self, session_id: Optional[str] = None) -> List[ApprovalRequest]:
        """
        대기 중인 승인 요청 목록 조회

        Args:
            session_id: 세션 ID (선택적, 없으면 전체 조회)

        Returns:
            대기 중인 승인 요청 목록 (생성일시 오름차순)
        """
        pass

    @abstractmethod
    def get_approval_history(self, session_id: str) -> List[ApprovalRequest]:
        """
        세션별 승인 이력 조회

        Args:
            session_id: 세션 ID

        Returns:
            승인 요청 목록 (생성일시 내림차순)
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def get_feedbacks_by_approval(self, approval_id: int) -> List[Feedback]:
        """
        승인 요청별 피드백 조회

        Args:
            approval_id: 승인 요청 ID

        Returns:
            피드백 목록 (생성일시 오름차순)
        """
        pass

    @abstractmethod
    def get_feedbacks_by_session(self, session_id: str) -> List[Feedback]:
        """
        세션별 피드백 조회

        Args:
            session_id: 세션 ID

        Returns:
            피드백 목록 (생성일시 내림차순)
        """
        pass
