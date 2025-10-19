"""
승인 및 피드백 도메인 모델 단위 테스트

ApprovalRequest, ApprovalResponse, Feedback 모델 테스트
- Enum 값 검증
- to_dict() 및 from_dict() 메서드 테스트
- 불변성 테스트 (dataclass replace 동작 확인)
- 경계값 테스트
"""

import pytest
from datetime import datetime
from dataclasses import replace

from src.domain.models.approval import (
    ApprovalRequest, ApprovalResponse, ApprovalStatus, ApprovalType
)
from src.domain.models.feedback import Feedback


# ============================================================================
# ApprovalStatus Enum 테스트
# ============================================================================

class TestApprovalStatus:
    """ApprovalStatus Enum 테스트"""

    def test_enum_values(self):
        """Enum 값 검증"""
        assert ApprovalStatus.PENDING.value == "pending"
        assert ApprovalStatus.APPROVED.value == "approved"
        assert ApprovalStatus.REJECTED.value == "rejected"
        assert ApprovalStatus.MODIFIED.value == "modified"

    def test_enum_from_string(self):
        """문자열에서 Enum 생성"""
        assert ApprovalStatus("pending") == ApprovalStatus.PENDING
        assert ApprovalStatus("approved") == ApprovalStatus.APPROVED
        assert ApprovalStatus("rejected") == ApprovalStatus.REJECTED
        assert ApprovalStatus("modified") == ApprovalStatus.MODIFIED

    def test_enum_invalid_value(self):
        """잘못된 값으로 Enum 생성 시 ValueError"""
        with pytest.raises(ValueError):
            ApprovalStatus("invalid_status")


# ============================================================================
# ApprovalType Enum 테스트
# ============================================================================

class TestApprovalType:
    """ApprovalType Enum 테스트"""

    def test_enum_values(self):
        """Enum 값 검증"""
        assert ApprovalType.BEFORE_CODE_WRITE.value == "before_code_write"
        assert ApprovalType.AFTER_CODE_WRITE.value == "after_code_write"
        assert ApprovalType.BEFORE_TEST_RUN.value == "before_test_run"
        assert ApprovalType.BEFORE_DEPLOYMENT.value == "before_deployment"

    def test_enum_from_string(self):
        """문자열에서 Enum 생성"""
        assert ApprovalType("before_code_write") == ApprovalType.BEFORE_CODE_WRITE
        assert ApprovalType("after_code_write") == ApprovalType.AFTER_CODE_WRITE
        assert ApprovalType("before_test_run") == ApprovalType.BEFORE_TEST_RUN
        assert ApprovalType("before_deployment") == ApprovalType.BEFORE_DEPLOYMENT

    def test_enum_invalid_value(self):
        """잘못된 값으로 Enum 생성 시 ValueError"""
        with pytest.raises(ValueError):
            ApprovalType("invalid_type")


# ============================================================================
# ApprovalRequest 모델 테스트
# ============================================================================

class TestApprovalRequest:
    """ApprovalRequest 도메인 모델 테스트"""

    @pytest.fixture
    def sample_approval_request(self) -> ApprovalRequest:
        """샘플 승인 요청 객체"""
        return ApprovalRequest(
            session_id="session-123",
            approval_type=ApprovalType.BEFORE_CODE_WRITE,
            task_description="새로운 기능 추가",
            context_data='{"file": "main.py"}',
            status=ApprovalStatus.PENDING,
            created_at=datetime(2025, 10, 19, 10, 0, 0)
        )

    def test_create_approval_request(self, sample_approval_request):
        """승인 요청 객체 생성"""
        assert sample_approval_request.session_id == "session-123"
        assert sample_approval_request.approval_type == ApprovalType.BEFORE_CODE_WRITE
        assert sample_approval_request.task_description == "새로운 기능 추가"
        assert sample_approval_request.context_data == '{"file": "main.py"}'
        assert sample_approval_request.status == ApprovalStatus.PENDING
        assert sample_approval_request.id is None
        assert sample_approval_request.responded_at is None

    def test_default_status_is_pending(self):
        """기본 상태는 PENDING"""
        request = ApprovalRequest(
            session_id="session-123",
            approval_type=ApprovalType.BEFORE_CODE_WRITE,
            task_description="테스트 작업"
        )
        assert request.status == ApprovalStatus.PENDING

    def test_to_dict(self, sample_approval_request):
        """to_dict() 메서드 테스트"""
        data = sample_approval_request.to_dict()

        assert data["session_id"] == "session-123"
        assert data["approval_type"] == "before_code_write"
        assert data["status"] == "pending"
        assert data["task_description"] == "새로운 기능 추가"
        assert data["context_data"] == '{"file": "main.py"}'
        assert data["created_at"] == "2025-10-19T10:00:00"
        assert data["responded_at"] is None
        assert data["id"] is None

    def test_to_dict_with_id_and_responded_at(self, sample_approval_request):
        """ID와 responded_at이 있는 경우 to_dict() 테스트"""
        request = replace(
            sample_approval_request,
            id=1,
            responded_at=datetime(2025, 10, 19, 10, 30, 0)
        )
        data = request.to_dict()

        assert data["id"] == 1
        assert data["responded_at"] == "2025-10-19T10:30:00"

    def test_from_dict(self):
        """from_dict() 메서드 테스트"""
        data = {
            "id": 1,
            "session_id": "session-456",
            "approval_type": "after_code_write",
            "status": "approved",
            "task_description": "코드 리뷰",
            "context_data": '{"changes": ["file1.py", "file2.py"]}',
            "created_at": "2025-10-19T11:00:00",
            "responded_at": "2025-10-19T11:15:00"
        }

        request = ApprovalRequest.from_dict(data)

        assert request.id == 1
        assert request.session_id == "session-456"
        assert request.approval_type == ApprovalType.AFTER_CODE_WRITE
        assert request.status == ApprovalStatus.APPROVED
        assert request.task_description == "코드 리뷰"
        assert request.context_data == '{"changes": ["file1.py", "file2.py"]}'
        assert request.created_at == datetime(2025, 10, 19, 11, 0, 0)
        assert request.responded_at == datetime(2025, 10, 19, 11, 15, 0)

    def test_from_dict_missing_required_field(self):
        """필수 필드가 누락된 경우 ValueError"""
        data = {
            "session_id": "session-789",
            "approval_type": "before_test_run",
            # task_description 누락
            "created_at": "2025-10-19T12:00:00"
        }

        with pytest.raises(ValueError, match="필수 필드가 누락되었습니다"):
            ApprovalRequest.from_dict(data)

    def test_from_dict_invalid_date_format(self):
        """날짜 형식이 잘못된 경우 ValueError"""
        data = {
            "session_id": "session-789",
            "approval_type": "before_test_run",
            "status": "pending",
            "task_description": "테스트",
            "created_at": "invalid-date-format"
        }

        with pytest.raises(ValueError, match="데이터 형식 오류"):
            ApprovalRequest.from_dict(data)

    def test_from_dict_invalid_enum_value(self):
        """Enum 값이 잘못된 경우 ValueError"""
        data = {
            "session_id": "session-789",
            "approval_type": "invalid_approval_type",
            "status": "pending",
            "task_description": "테스트",
            "created_at": "2025-10-19T12:00:00"
        }

        with pytest.raises(ValueError, match="데이터 형식 오류"):
            ApprovalRequest.from_dict(data)

    def test_dataclass_immutability_with_replace(self, sample_approval_request):
        """dataclass replace()로 새 인스턴스 생성 확인 (불변성)"""
        original = sample_approval_request
        modified = replace(original, status=ApprovalStatus.APPROVED, id=1)

        # 원본은 변경되지 않음
        assert original.status == ApprovalStatus.PENDING
        assert original.id is None

        # 새 인스턴스는 변경된 값 포함
        assert modified.status == ApprovalStatus.APPROVED
        assert modified.id == 1

        # 다른 필드는 동일
        assert modified.session_id == original.session_id
        assert modified.task_description == original.task_description

    def test_from_dict_without_optional_fields(self):
        """선택적 필드 없이 from_dict() 테스트"""
        data = {
            "session_id": "session-999",
            "approval_type": "before_deployment",
            "status": "pending",
            "task_description": "배포 승인",
            "created_at": "2025-10-19T14:00:00"
        }

        request = ApprovalRequest.from_dict(data)

        assert request.id is None
        assert request.context_data is None
        assert request.responded_at is None


# ============================================================================
# ApprovalResponse 모델 테스트
# ============================================================================

class TestApprovalResponse:
    """ApprovalResponse 도메인 모델 테스트"""

    @pytest.fixture
    def sample_approval_response(self) -> ApprovalResponse:
        """샘플 승인 응답 객체"""
        return ApprovalResponse(
            approval_id=1,
            status=ApprovalStatus.APPROVED,
            feedback_content="잘 작성되었습니다.",
            responded_at=datetime(2025, 10, 19, 15, 0, 0)
        )

    def test_create_approval_response(self, sample_approval_response):
        """승인 응답 객체 생성"""
        assert sample_approval_response.approval_id == 1
        assert sample_approval_response.status == ApprovalStatus.APPROVED
        assert sample_approval_response.feedback_content == "잘 작성되었습니다."
        assert sample_approval_response.responded_at == datetime(2025, 10, 19, 15, 0, 0)

    def test_create_response_without_feedback(self):
        """피드백 없이 승인 응답 생성"""
        response = ApprovalResponse(
            approval_id=2,
            status=ApprovalStatus.REJECTED
        )

        assert response.approval_id == 2
        assert response.status == ApprovalStatus.REJECTED
        assert response.feedback_content is None
        assert response.responded_at is not None  # 기본값: datetime.now()

    def test_to_dict(self, sample_approval_response):
        """to_dict() 메서드 테스트"""
        data = sample_approval_response.to_dict()

        assert data["approval_id"] == 1
        assert data["status"] == "approved"
        assert data["feedback_content"] == "잘 작성되었습니다."
        assert data["responded_at"] == "2025-10-19T15:00:00"

    def test_to_dict_without_feedback(self):
        """피드백 없는 경우 to_dict() 테스트"""
        response = ApprovalResponse(
            approval_id=3,
            status=ApprovalStatus.MODIFIED,
            responded_at=datetime(2025, 10, 19, 16, 0, 0)
        )
        data = response.to_dict()

        assert data["feedback_content"] is None

    def test_from_dict(self):
        """from_dict() 메서드 테스트"""
        data = {
            "approval_id": 5,
            "status": "rejected",
            "feedback_content": "다시 작성해주세요.",
            "responded_at": "2025-10-19T17:00:00"
        }

        response = ApprovalResponse.from_dict(data)

        assert response.approval_id == 5
        assert response.status == ApprovalStatus.REJECTED
        assert response.feedback_content == "다시 작성해주세요."
        assert response.responded_at == datetime(2025, 10, 19, 17, 0, 0)

    def test_from_dict_missing_required_field(self):
        """필수 필드가 누락된 경우 ValueError"""
        data = {
            "status": "approved",
            # approval_id 누락
            "responded_at": "2025-10-19T18:00:00"
        }

        with pytest.raises(ValueError, match="필수 필드가 누락되었습니다"):
            ApprovalResponse.from_dict(data)

    def test_from_dict_without_responded_at(self):
        """responded_at 없이 from_dict() 호출 시 기본값 사용"""
        data = {
            "approval_id": 7,
            "status": "approved"
        }

        response = ApprovalResponse.from_dict(data)

        assert response.approval_id == 7
        assert response.status == ApprovalStatus.APPROVED
        assert response.responded_at is not None  # 기본값 (datetime.now())


# ============================================================================
# Feedback 모델 테스트
# ============================================================================

class TestFeedback:
    """Feedback 도메인 모델 테스트"""

    @pytest.fixture
    def sample_feedback(self) -> Feedback:
        """샘플 피드백 객체"""
        return Feedback(
            approval_id=10,
            session_id="session-abc",
            feedback_content="변수명을 더 명확하게 변경하세요.",
            created_at=datetime(2025, 10, 19, 18, 0, 0)
        )

    def test_create_feedback(self, sample_feedback):
        """피드백 객체 생성"""
        assert sample_feedback.approval_id == 10
        assert sample_feedback.session_id == "session-abc"
        assert sample_feedback.feedback_content == "변수명을 더 명확하게 변경하세요."
        assert sample_feedback.created_at == datetime(2025, 10, 19, 18, 0, 0)
        assert sample_feedback.id is None

    def test_to_dict(self, sample_feedback):
        """to_dict() 메서드 테스트"""
        data = sample_feedback.to_dict()

        assert data["approval_id"] == 10
        assert data["session_id"] == "session-abc"
        assert data["feedback_content"] == "변수명을 더 명확하게 변경하세요."
        assert data["created_at"] == "2025-10-19T18:00:00"
        assert data["id"] is None

    def test_to_dict_with_id(self, sample_feedback):
        """ID가 있는 경우 to_dict() 테스트"""
        feedback = replace(sample_feedback, id=100)
        data = feedback.to_dict()

        assert data["id"] == 100

    def test_from_dict(self):
        """from_dict() 메서드 테스트"""
        data = {
            "id": 20,
            "approval_id": 15,
            "session_id": "session-xyz",
            "feedback_content": "로직 개선이 필요합니다.",
            "created_at": "2025-10-19T19:00:00"
        }

        feedback = Feedback.from_dict(data)

        assert feedback.id == 20
        assert feedback.approval_id == 15
        assert feedback.session_id == "session-xyz"
        assert feedback.feedback_content == "로직 개선이 필요합니다."
        assert feedback.created_at == datetime(2025, 10, 19, 19, 0, 0)

    def test_from_dict_missing_required_field(self):
        """필수 필드가 누락된 경우 ValueError"""
        data = {
            "approval_id": 25,
            "session_id": "session-def",
            # feedback_content 누락
            "created_at": "2025-10-19T20:00:00"
        }

        with pytest.raises(ValueError, match="필수 필드가 누락되었습니다"):
            Feedback.from_dict(data)

    def test_from_dict_without_created_at(self):
        """created_at 없이 from_dict() 호출 시 기본값 사용"""
        data = {
            "approval_id": 30,
            "session_id": "session-ghi",
            "feedback_content": "추가 검토 필요"
        }

        feedback = Feedback.from_dict(data)

        assert feedback.approval_id == 30
        assert feedback.session_id == "session-ghi"
        assert feedback.feedback_content == "추가 검토 필요"
        assert feedback.created_at is not None  # 기본값 (datetime.now())

    def test_dataclass_immutability_with_replace(self, sample_feedback):
        """dataclass replace()로 새 인스턴스 생성 확인 (불변성)"""
        original = sample_feedback
        modified = replace(original, id=50, feedback_content="수정된 피드백")

        # 원본은 변경되지 않음
        assert original.id is None
        assert original.feedback_content == "변수명을 더 명확하게 변경하세요."

        # 새 인스턴스는 변경된 값 포함
        assert modified.id == 50
        assert modified.feedback_content == "수정된 피드백"

        # 다른 필드는 동일
        assert modified.approval_id == original.approval_id
        assert modified.session_id == original.session_id


# ============================================================================
# 경계값 및 특수 케이스 테스트
# ============================================================================

class TestEdgeCases:
    """경계값 및 특수 케이스 테스트"""

    def test_approval_request_with_empty_context_data(self):
        """빈 context_data로 승인 요청 생성"""
        request = ApprovalRequest(
            session_id="session-123",
            approval_type=ApprovalType.BEFORE_CODE_WRITE,
            task_description="테스트 작업",
            context_data=""
        )

        assert request.context_data == ""

    def test_feedback_with_very_long_content(self):
        """매우 긴 피드백 내용"""
        long_content = "A" * 5000
        feedback = Feedback(
            approval_id=1,
            session_id="session-123",
            feedback_content=long_content
        )

        assert len(feedback.feedback_content) == 5000

    def test_approval_response_with_empty_feedback(self):
        """빈 피드백 내용으로 승인 응답 생성"""
        response = ApprovalResponse(
            approval_id=1,
            status=ApprovalStatus.MODIFIED,
            feedback_content=""
        )

        assert response.feedback_content == ""

    def test_approval_request_with_unicode_characters(self):
        """유니코드 문자 (한글, 이모지) 포함 테스트"""
        request = ApprovalRequest(
            session_id="세션-한글-123",
            approval_type=ApprovalType.BEFORE_CODE_WRITE,
            task_description="새로운 기능 추가 🚀",
            context_data='{"message": "안녕하세요 👋"}'
        )

        assert request.session_id == "세션-한글-123"
        assert "🚀" in request.task_description
        assert "👋" in request.context_data

    def test_round_trip_serialization(self):
        """직렬화 → 역직렬화 → 재직렬화 일관성 테스트"""
        original = ApprovalRequest(
            session_id="session-999",
            approval_type=ApprovalType.AFTER_CODE_WRITE,
            task_description="원본 요청",
            context_data='{"test": true}',
            status=ApprovalStatus.APPROVED,
            created_at=datetime(2025, 10, 19, 22, 0, 0),
            responded_at=datetime(2025, 10, 19, 22, 30, 0)
        )

        # 직렬화
        data = original.to_dict()

        # 역직렬화
        restored = ApprovalRequest.from_dict(data)

        # 재직렬화
        data2 = restored.to_dict()

        # 일관성 검증
        assert data == data2
