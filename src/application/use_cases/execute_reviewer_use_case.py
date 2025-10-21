"""
Reviewer Use Case 구현

코드 리뷰 작업을 실행하는 Use Case입니다.
"""

import logging
from typing import Optional

from .base_worker_use_case import BaseWorkerUseCase
from src.domain.models import Task, TaskResult
from src.domain.exceptions import PreconditionFailedError
from ..ports import IAgentClient
from ..validation import UseCaseValidator


logger = logging.getLogger(__name__)


class ExecuteReviewerUseCase(BaseWorkerUseCase):
    """
    Reviewer Worker 실행 Use Case

    코드 리뷰 및 품질 검증 작업을 수행합니다.

    특징:
    - 리뷰할 코드가 있는지 검증
    - 리뷰 결과를 구조화하여 반환
    - 이슈 발견 여부 추출
    """

    def __init__(
        self,
        reviewer_client: IAgentClient,
        require_code_reference: bool = False
    ):
        """
        Args:
            reviewer_client: Reviewer Worker 클라이언트
            require_code_reference: 코드 참조 필수 여부
        """
        super().__init__(
            worker_name="reviewer",
            worker_client=reviewer_client
        )
        self.require_code_reference = require_code_reference

    def _check_preconditions(self, task: Task) -> None:
        """
        Reviewer 실행 사전 조건 체크

        Args:
            task: 체크할 작업

        Raises:
            PreconditionFailedError: 사전 조건 실패
        """
        # 1. 코드 참조가 필요한 경우 체크
        UseCaseValidator.validate_code_reference_requirement(
            description=task.description,
            require_code_reference=self.require_code_reference
        )

        logger.debug(f"[{self.worker_name}] ✅ 사전 조건 체크 완료")

    def _process_result(self, task: Task, output: str) -> TaskResult:
        """
        Reviewer 결과 후처리

        Args:
            task: 원본 작업
            output: Reviewer 실행 결과

        Returns:
            후처리된 TaskResult
        """
        # 기본 처리 수행
        result = super()._process_result(task, output)

        # 간단한 휴리스틱: 이슈 발견 여부 체크
        output_lower = output.lower()
        has_issues = any(
            keyword in output_lower
            for keyword in [
                "이슈", "issue", "문제", "problem",
                "개선", "improve", "수정", "fix"
            ]
        )

        # 메타데이터 추가
        result.metadata = {
            "worker_type": "reviewer",
            "output_length": len(output),
            "has_issues": has_issues,
            "review_status": "issues_found" if has_issues else "approved"
        }

        return result
