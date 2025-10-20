"""
Use Case Validators 단위 테스트

테스트 범위:
- validate_min_length() 테스트 (4개)
- validate_max_length() 테스트 (3개)
- validate_contains_keywords() 테스트 (4개)
- validate_not_empty() 테스트 (3개)
- validate_plan_requirement() 테스트 (2개)
- validate_code_reference_requirement() 테스트 (2개)
- validate_test_target_requirement() 테스트 (2개)

총 20개 테스트
"""

import pytest
from src.application.validation import UseCaseValidator
from src.domain.exceptions import PreconditionFailedError, ValidationError


class TestValidateMinLength:
    """validate_min_length() 메서드 테스트"""

    def test_valid_min_length(self):
        """유효한 최소 길이 검증"""
        # 정확히 최소 길이
        UseCaseValidator.validate_min_length("1234567890", 10, "작업 설명")

        # 최소 길이보다 긴 경우
        UseCaseValidator.validate_min_length("12345678901", 10, "작업 설명")

    def test_too_short_text(self):
        """너무 짧은 텍스트 - 실패"""
        with pytest.raises(PreconditionFailedError) as exc_info:
            UseCaseValidator.validate_min_length("짧은", 10, "작업 설명")

        assert "작업 설명이 너무 짧습니다" in str(exc_info.value)
        assert "최소 10자" in str(exc_info.value)
        assert "현재 2자" in str(exc_info.value)

    def test_empty_text(self):
        """빈 문자열 - 실패"""
        with pytest.raises(PreconditionFailedError) as exc_info:
            UseCaseValidator.validate_min_length("", 1, "필드")

        assert "필드이 너무 짧습니다" in str(exc_info.value)

    def test_whitespace_only_text(self):
        """공백만 있는 문자열 - 실패"""
        with pytest.raises(PreconditionFailedError) as exc_info:
            UseCaseValidator.validate_min_length("   ", 5, "설명")

        assert "설명이 너무 짧습니다" in str(exc_info.value)
        assert "현재 0자" in str(exc_info.value)


class TestValidateMaxLength:
    """validate_max_length() 메서드 테스트"""

    def test_valid_max_length(self):
        """유효한 최대 길이 검증"""
        # 정확히 최대 길이
        UseCaseValidator.validate_max_length("1234567890", 10, "작업 설명")

        # 최대 길이보다 짧은 경우
        UseCaseValidator.validate_max_length("123", 10, "작업 설명")

    def test_too_long_text(self):
        """너무 긴 텍스트 - 실패"""
        with pytest.raises(ValidationError) as exc_info:
            UseCaseValidator.validate_max_length("12345678901", 10, "작업 설명")

        assert "작업 설명이 너무 깁니다" in str(exc_info.value)
        assert "최대 10자" in str(exc_info.value)
        assert "현재 11자" in str(exc_info.value)

    def test_empty_text_within_limit(self):
        """빈 문자열은 최대 길이 제한 내 - 성공"""
        UseCaseValidator.validate_max_length("", 10, "필드")


class TestValidateContainsKeywords:
    """validate_contains_keywords() 메서드 테스트"""

    def test_keyword_found(self):
        """키워드 포함 - 성공"""
        UseCaseValidator.validate_contains_keywords(
            text="파일을 작성하세요",
            keywords=["파일", "file", "코드"],
            error_message="키워드가 없습니다."
        )

    def test_keyword_not_found(self):
        """키워드 미포함 - 실패"""
        with pytest.raises(PreconditionFailedError) as exc_info:
            UseCaseValidator.validate_contains_keywords(
                text="그냥 작성하세요",
                keywords=["파일", "file", "코드"],
                error_message="키워드가 없습니다."
            )

        assert "키워드가 없습니다." in str(exc_info.value)

    def test_case_insensitive_search(self):
        """대소문자 구분 없음 - 성공"""
        UseCaseValidator.validate_contains_keywords(
            text="FILE을 작성하세요",
            keywords=["file"],
            error_message="키워드가 없습니다.",
            case_sensitive=False
        )

    def test_case_sensitive_search(self):
        """대소문자 구분 있음 - 실패"""
        with pytest.raises(PreconditionFailedError):
            UseCaseValidator.validate_contains_keywords(
                text="FILE을 작성하세요",
                keywords=["file"],
                error_message="키워드가 없습니다.",
                case_sensitive=True
            )


class TestValidateNotEmpty:
    """validate_not_empty() 메서드 테스트"""

    def test_valid_text(self):
        """유효한 텍스트 - 성공"""
        UseCaseValidator.validate_not_empty("유효한 텍스트", "작업 설명")

    def test_none_value(self):
        """None 값 - 실패"""
        with pytest.raises(ValidationError) as exc_info:
            UseCaseValidator.validate_not_empty(None, "작업 설명")

        assert "작업 설명이(가) 비어있습니다" in str(exc_info.value)

    def test_empty_string(self):
        """빈 문자열 - 실패"""
        with pytest.raises(ValidationError) as exc_info:
            UseCaseValidator.validate_not_empty("", "필드")

        assert "필드이(가) 비어있습니다" in str(exc_info.value)

    def test_whitespace_only(self):
        """공백만 있는 문자열 - 실패"""
        with pytest.raises(ValidationError) as exc_info:
            UseCaseValidator.validate_not_empty("   ", "설명")

        assert "설명이(가) 비어있습니다" in str(exc_info.value)


class TestValidatePlanRequirement:
    """validate_plan_requirement() 메서드 테스트"""

    def test_plan_not_required(self):
        """계획 불필요 - 성공"""
        UseCaseValidator.validate_plan_requirement(
            description="그냥 코드 작성",
            require_plan=False
        )

    def test_plan_required_and_present(self):
        """계획 필요 & 포함 - 성공"""
        UseCaseValidator.validate_plan_requirement(
            description="다음 계획에 따라 코드를 작성합니다",
            require_plan=True
        )

    def test_plan_required_but_missing(self):
        """계획 필요 & 미포함 - 실패"""
        with pytest.raises(PreconditionFailedError) as exc_info:
            UseCaseValidator.validate_plan_requirement(
                description="코드를 작성합니다",
                require_plan=True
            )

        assert "계획이 필요합니다" in str(exc_info.value)

    def test_plan_with_custom_keywords(self):
        """커스텀 키워드 검증 - 성공"""
        UseCaseValidator.validate_plan_requirement(
            description="다음 단계로 진행합니다",
            require_plan=True,
            plan_keywords=["단계", "절차"]
        )


class TestValidateCodeReferenceRequirement:
    """validate_code_reference_requirement() 메서드 테스트"""

    def test_code_reference_not_required(self):
        """코드 참조 불필요 - 성공"""
        UseCaseValidator.validate_code_reference_requirement(
            description="리뷰하세요",
            require_code_reference=False
        )

    def test_code_reference_required_and_present(self):
        """코드 참조 필요 & 포함 - 성공"""
        UseCaseValidator.validate_code_reference_requirement(
            description="src/main.py 파일을 리뷰하세요",
            require_code_reference=True
        )

    def test_code_reference_required_but_missing(self):
        """코드 참조 필요 & 미포함 - 실패"""
        with pytest.raises(PreconditionFailedError) as exc_info:
            UseCaseValidator.validate_code_reference_requirement(
                description="리뷰하세요",
                require_code_reference=True
            )

        assert "리뷰할 코드 파일이 명시되지 않았습니다" in str(exc_info.value)

    def test_code_reference_with_extension(self):
        """파일 확장자 검증 - 성공"""
        UseCaseValidator.validate_code_reference_requirement(
            description="app.ts 파일을 리뷰하세요",
            require_code_reference=True
        )


class TestValidateTestTargetRequirement:
    """validate_test_target_requirement() 메서드 테스트"""

    def test_test_target_not_required(self):
        """테스트 대상 불필요 - 성공"""
        UseCaseValidator.validate_test_target_requirement(
            description="작업을 수행하세요",
            require_test_target=False
        )

    def test_test_target_required_and_present(self):
        """테스트 대상 필요 & 포함 - 성공"""
        UseCaseValidator.validate_test_target_requirement(
            description="login 함수를 테스트하세요",
            require_test_target=True
        )

    def test_test_target_required_but_missing(self):
        """테스트 대상 필요 & 미포함 - 실패"""
        with pytest.raises(PreconditionFailedError) as exc_info:
            UseCaseValidator.validate_test_target_requirement(
                description="작업을 수행하세요",
                require_test_target=True
            )

        assert "테스트 대상이 명확하지 않습니다" in str(exc_info.value)

    def test_test_target_with_pytest(self):
        """pytest 키워드 검증 - 성공"""
        UseCaseValidator.validate_test_target_requirement(
            description="pytest로 검증하세요",
            require_test_target=True
        )
