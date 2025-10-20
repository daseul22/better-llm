"""
Tester Use Case 구현

테스트 작성 및 실행 작업을 실행하는 Use Case입니다.
"""

import logging
from typing import Optional

from .base_worker_use_case import BaseWorkerUseCase
from domain.models import Task, TaskResult
from domain.exceptions import PreconditionFailedError
from ..ports import IAgentClient
from ..validation import UseCaseValidator


logger = logging.getLogger(__name__)


class ExecuteTesterUseCase(BaseWorkerUseCase):
    """
    Tester Worker 실행 Use Case

    테스트 작성 및 실행 작업을 수행합니다.

    특징:
    - 테스트 대상이 명확한지 검증
    - 테스트 실행 결과 파싱
    - 테스트 성공/실패 여부 추출
    """

    def __init__(
        self,
        tester_client: IAgentClient,
        require_test_target: bool = False
    ):
        """
        Args:
            tester_client: Tester Worker 클라이언트
            require_test_target: 테스트 대상 필수 여부
        """
        super().__init__(
            worker_name="tester",
            worker_client=tester_client
        )
        self.require_test_target = require_test_target

    def _check_preconditions(self, task: Task) -> None:
        """
        Tester 실행 사전 조건 체크

        Args:
            task: 체크할 작업

        Raises:
            PreconditionFailedError: 사전 조건 실패
        """
        # 1. 테스트 대상이 필요한 경우 체크
        UseCaseValidator.validate_test_target_requirement(
            description=task.description,
            require_test_target=self.require_test_target
        )

        logger.debug(f"[{self.worker_name}] ✅ 사전 조건 체크 완료")

    def _process_result(self, task: Task, output: str) -> TaskResult:
        """
        Tester 결과 후처리

        Args:
            task: 원본 작업
            output: Tester 실행 결과

        Returns:
            후처리된 TaskResult
        """
        # 기본 처리 수행
        result = super()._process_result(task, output)

        # 간단한 휴리스틱: 테스트 성공/실패 여부 체크
        output_lower = output.lower()

        # pytest 출력 패턴 체크
        has_passed = any(
            keyword in output_lower
            for keyword in ["passed", "성공", "✓", "ok"]
        )

        has_failed = any(
            keyword in output_lower
            for keyword in ["failed", "실패", "error", "❌"]
        )

        # 테스트 상태 결정
        if has_failed:
            test_status = "failed"
        elif has_passed:
            test_status = "passed"
        else:
            test_status = "unknown"

        # 메타데이터 추가
        result.metadata = {
            "worker_type": "tester",
            "output_length": len(output),
            "test_status": test_status,
            "has_test_results": has_passed or has_failed
        }

        return result
