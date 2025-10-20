"""
승인 관리 Use Cases

RequestApprovalUseCase: 승인 요청 생성
ProcessApprovalResponseUseCase: 승인 응답 처리
GetPendingApprovalsUseCase: 대기 중인 승인 목록 조회
ApprovalHistoryUseCase: 승인 이력 조회
"""

from typing import List, Optional, Tuple
from ..ports.approval_port import IApprovalRepository
from domain.models.approval import ApprovalRequest, ApprovalResponse, ApprovalStatus, ApprovalType
from domain.models.feedback import Feedback


def _validate_session_id(session_id: str) -> None:
    """
    세션 ID 입력 검증 (SQL Injection 방지)

    Args:
        session_id: 검증할 세션 ID

    Raises:
        ValueError: 세션 ID가 유효하지 않은 경우
    """
    if not session_id or not session_id.strip():
        raise ValueError("세션 ID는 공백일 수 없습니다.")

    # SQL Injection 패턴 검증
    dangerous_chars = ["'", '"', ";", "--", "/*", "*/", "\\"]
    if any(char in session_id for char in dangerous_chars):
        raise ValueError("세션 ID에 허용되지 않는 문자가 포함되어 있습니다.")


class RequestApprovalUseCase:
    """
    승인 요청 생성 Use Case

    사용자 승인이 필요한 지점에서 승인 요청을 생성하고 저장합니다.
    """

    def __init__(self, approval_repository: IApprovalRepository):
        """
        Args:
            approval_repository: 승인 저장소 인터페이스
        """
        self.approval_repository = approval_repository

    def execute(
        self,
        session_id: str,
        approval_type: ApprovalType,
        task_description: str,
        context_data: Optional[str] = None
    ) -> ApprovalRequest:
        """
        승인 요청 생성 및 저장

        Args:
            session_id: 세션 ID
            approval_type: 승인 지점 타입
            task_description: 작업 설명
            context_data: 컨텍스트 데이터 (JSON 문자열, 선택적)

        Returns:
            생성된 승인 요청 (ID 포함)

        Raises:
            ValueError: 세션이 존재하지 않거나 유효하지 않은 입력
            Exception: DB 저장 실패 시
        """
        # 입력 검증 (SQL Injection 방지 포함)
        _validate_session_id(session_id)

        if not task_description or not task_description.strip():
            raise ValueError("작업 설명은 필수입니다.")

        # 승인 요청 객체 생성
        request = ApprovalRequest(
            session_id=session_id,
            approval_type=approval_type,
            task_description=task_description,
            context_data=context_data,
            status=ApprovalStatus.PENDING
        )

        # 저장 및 반환
        return self.approval_repository.create_approval_request(request)


class ProcessApprovalResponseUseCase:
    """
    승인 응답 처리 Use Case

    사용자의 승인 응답을 처리하고 피드백을 기록합니다.
    """

    def __init__(self, approval_repository: IApprovalRepository):
        """
        Args:
            approval_repository: 승인 저장소 인터페이스
        """
        self.approval_repository = approval_repository

    def execute(
        self,
        approval_id: int,
        status: ApprovalStatus,
        feedback_content: Optional[str] = None,
        max_feedback_length: int = 2000
    ) -> Tuple[ApprovalRequest, Optional[Feedback]]:
        """
        승인 응답 처리 및 피드백 기록

        Args:
            approval_id: 승인 요청 ID
            status: 승인 상태 (APPROVED, REJECTED, MODIFIED)
            feedback_content: 피드백 내용 (선택적)
            max_feedback_length: 최대 피드백 길이 (기본값: 2000)

        Returns:
            (업데이트된 승인 요청, 생성된 피드백 또는 None)

        Raises:
            ValueError: 승인 요청이 존재하지 않거나 유효하지 않은 상태
            Exception: DB 업데이트 실패 시
        """
        # 승인 요청 존재 여부 확인
        existing_request = self.approval_repository.get_approval_by_id(approval_id)
        if not existing_request:
            raise ValueError(f"승인 요청을 찾을 수 없습니다: {approval_id}")

        # PENDING 상태만 응답 가능
        if existing_request.status != ApprovalStatus.PENDING:
            raise ValueError(
                f"이미 처리된 승인 요청입니다. 현재 상태: {existing_request.status.value}"
            )

        # 상태 검증 (PENDING은 불가)
        if status == ApprovalStatus.PENDING:
            raise ValueError("PENDING 상태로 업데이트할 수 없습니다.")

        # 피드백 길이 검증
        if feedback_content and len(feedback_content) > max_feedback_length:
            raise ValueError(
                f"피드백 내용이 너무 깁니다. (최대 {max_feedback_length}자)"
            )

        # 승인 응답 객체 생성
        response = ApprovalResponse(
            approval_id=approval_id,
            status=status,
            feedback_content=feedback_content
        )

        # 승인 상태 업데이트
        updated_request = self.approval_repository.update_approval_status(approval_id, response)

        # 피드백 생성 (있을 경우)
        created_feedback = None
        if feedback_content and feedback_content.strip():
            feedback = Feedback(
                approval_id=approval_id,
                session_id=existing_request.session_id,
                feedback_content=feedback_content
            )
            created_feedback = self.approval_repository.create_feedback(feedback)

        return updated_request, created_feedback


class GetPendingApprovalsUseCase:
    """
    대기 중인 승인 목록 조회 Use Case

    사용자가 응답해야 할 대기 중인 승인 요청들을 조회합니다.
    """

    def __init__(self, approval_repository: IApprovalRepository):
        """
        Args:
            approval_repository: 승인 저장소 인터페이스
        """
        self.approval_repository = approval_repository

    def execute(self, session_id: Optional[str] = None) -> List[ApprovalRequest]:
        """
        대기 중인 승인 요청 목록 조회

        Args:
            session_id: 세션 ID (선택적, 없으면 전체 조회)

        Returns:
            대기 중인 승인 요청 목록 (생성일시 오름차순)

        Raises:
            ValueError: 세션 ID가 유효하지 않은 경우
        """
        # 세션 ID가 제공된 경우 입력 검증
        if session_id:
            _validate_session_id(session_id)

        return self.approval_repository.get_pending_approvals(session_id)


class ApprovalHistoryUseCase:
    """
    승인 이력 조회 Use Case

    세션별 승인 요청 이력과 관련 피드백을 조회합니다.
    """

    def __init__(self, approval_repository: IApprovalRepository):
        """
        Args:
            approval_repository: 승인 저장소 인터페이스
        """
        self.approval_repository = approval_repository

    def execute(self, session_id: str) -> List[Tuple[ApprovalRequest, List[Feedback]]]:
        """
        세션별 승인 이력 및 피드백 조회

        Args:
            session_id: 세션 ID

        Returns:
            (승인 요청, 피드백 목록) 튜플의 리스트 (생성일시 내림차순)

        Raises:
            ValueError: 세션 ID가 유효하지 않은 경우
        """
        # 입력 검증 (SQL Injection 방지 포함)
        _validate_session_id(session_id)

        # 승인 이력 조회
        approval_history = self.approval_repository.get_approval_history(session_id)

        # 각 승인 요청별 피드백 조회
        result = []
        for approval in approval_history:
            feedbacks = self.approval_repository.get_feedbacks_by_approval(approval.id)
            result.append((approval, feedbacks))

        return result
