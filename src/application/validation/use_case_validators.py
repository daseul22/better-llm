"""
Use Case 공통 검증 헬퍼.

이 모듈은 Worker Use Case들이 공통으로 사용하는 검증 로직을 제공합니다.
특히 키워드 기반 검증과 작업 설명 검증을 담당합니다.
"""

from typing import List, Optional
from domain.exceptions import PreconditionFailedError, ValidationError


class UseCaseValidator:
    """
    Use Case 실행 전 검증을 담당하는 헬퍼 클래스.

    이 클래스는 Worker Use Case들의 _check_preconditions()에서
    공통적으로 사용되는 검증 로직을 제공합니다.
    """

    @staticmethod
    def validate_min_length(
        text: str,
        min_length: int,
        field_name: str = "작업 설명"
    ) -> None:
        """
        텍스트 최소 길이 검증.

        Args:
            text: 검증할 텍스트
            min_length: 최소 길이
            field_name: 필드 이름 (에러 메시지용)

        Raises:
            PreconditionFailedError: 텍스트가 최소 길이보다 짧은 경우

        Example:
            >>> UseCaseValidator.validate_min_length("짧은 설명", 10, "작업 설명")
            PreconditionFailedError: 작업 설명이 너무 짧습니다. (최소 10자, 현재 5자)
        """
        actual_length = len(text.strip())
        if actual_length < min_length:
            raise PreconditionFailedError(
                f"{field_name}이 너무 짧습니다. "
                f"(최소 {min_length}자, 현재 {actual_length}자)"
            )

    @staticmethod
    def validate_max_length(
        text: str,
        max_length: int,
        field_name: str = "작업 설명"
    ) -> None:
        """
        텍스트 최대 길이 검증.

        Args:
            text: 검증할 텍스트
            max_length: 최대 길이
            field_name: 필드 이름 (에러 메시지용)

        Raises:
            ValidationError: 텍스트가 최대 길이보다 긴 경우
        """
        actual_length = len(text)
        if actual_length > max_length:
            raise ValidationError(
                f"{field_name}이 너무 깁니다. "
                f"(최대 {max_length}자, 현재 {actual_length}자)"
            )

    @staticmethod
    def validate_contains_keywords(
        text: str,
        keywords: List[str],
        error_message: str,
        case_sensitive: bool = False
    ) -> None:
        """
        텍스트에 특정 키워드가 포함되어 있는지 검증.

        Args:
            text: 검증할 텍스트
            keywords: 찾을 키워드 목록 (하나라도 포함되어야 함)
            error_message: 키워드가 없을 때 표시할 에러 메시지
            case_sensitive: 대소문자 구분 여부 (기본값: False)

        Raises:
            PreconditionFailedError: 키워드가 하나도 포함되지 않은 경우

        Example:
            >>> UseCaseValidator.validate_contains_keywords(
            ...     "파일을 작성하세요",
            ...     ["파일", "file", "코드", "code"],
            ...     "리뷰할 코드 파일이 명시되지 않았습니다."
            ... )
        """
        search_text = text if case_sensitive else text.lower()
        search_keywords = keywords if case_sensitive else [k.lower() for k in keywords]

        has_keyword = any(keyword in search_text for keyword in search_keywords)

        if not has_keyword:
            raise PreconditionFailedError(error_message)

    @staticmethod
    def validate_not_empty(
        text: Optional[str],
        field_name: str = "필드"
    ) -> None:
        """
        텍스트가 비어있지 않은지 검증.

        Args:
            text: 검증할 텍스트
            field_name: 필드 이름 (에러 메시지용)

        Raises:
            ValidationError: 텍스트가 None이거나 빈 문자열인 경우
        """
        if not text or not text.strip():
            raise ValidationError(f"{field_name}이(가) 비어있습니다.")

    @classmethod
    def validate_plan_requirement(
        cls,
        description: str,
        require_plan: bool,
        plan_keywords: Optional[List[str]] = None
    ) -> None:
        """
        계획 포함 여부 검증 (Coder Use Case용).

        Args:
            description: 작업 설명
            require_plan: 계획 포함 여부를 강제할지
            plan_keywords: 계획 관련 키워드 (기본값: ["계획", "plan", "단계", "step"])

        Raises:
            PreconditionFailedError: 계획이 필요하지만 포함되지 않은 경우
        """
        if not require_plan:
            return

        if plan_keywords is None:
            plan_keywords = ["계획", "plan", "단계", "step"]

        cls.validate_contains_keywords(
            text=description,
            keywords=plan_keywords,
            error_message=(
                "코드 작성 전 계획이 필요합니다. "
                "Planner를 먼저 실행하거나 작업 설명에 계획을 포함해주세요."
            )
        )

    @classmethod
    def validate_code_reference_requirement(
        cls,
        description: str,
        require_code_reference: bool,
        code_keywords: Optional[List[str]] = None
    ) -> None:
        """
        코드 참조 여부 검증 (Reviewer Use Case용).

        Args:
            description: 작업 설명
            require_code_reference: 코드 참조 필수 여부
            code_keywords: 코드 관련 키워드 (기본값: ["파일", "file", "코드", ...])

        Raises:
            PreconditionFailedError: 코드 참조가 필요하지만 명시되지 않은 경우
        """
        if not require_code_reference:
            return

        if code_keywords is None:
            code_keywords = [
                "파일", "file", "코드", "code",
                ".py", ".js", ".ts", ".java"
            ]

        cls.validate_contains_keywords(
            text=description,
            keywords=code_keywords,
            error_message=(
                "리뷰할 코드 파일이 명시되지 않았습니다. "
                "작업 설명에 파일 경로나 코드를 포함해주세요."
            )
        )

    @classmethod
    def validate_test_target_requirement(
        cls,
        description: str,
        require_test_target: bool,
        test_keywords: Optional[List[str]] = None
    ) -> None:
        """
        테스트 대상 여부 검증 (Tester Use Case용).

        Args:
            description: 작업 설명
            require_test_target: 테스트 대상 필수 여부
            test_keywords: 테스트 관련 키워드 (기본값: ["테스트", "test", ...])

        Raises:
            PreconditionFailedError: 테스트 대상이 필요하지만 명확하지 않은 경우
        """
        if not require_test_target:
            return

        if test_keywords is None:
            test_keywords = [
                "테스트", "test", "검증", "verify",
                "pytest", "unittest", "함수", "function"
            ]

        cls.validate_contains_keywords(
            text=description,
            keywords=test_keywords,
            error_message=(
                "테스트 대상이 명확하지 않습니다. "
                "작업 설명에 테스트할 대상을 포함해주세요."
            )
        )
