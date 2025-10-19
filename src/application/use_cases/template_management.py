"""
템플릿 관련 Use Cases

ListTemplatesUseCase: 템플릿 목록 조회
ApplyTemplateUseCase: 템플릿 적용
CreateTemplateUseCase: 템플릿 생성
SearchTemplatesUseCase: 템플릿 검색
"""

import logging
from pathlib import Path
from typing import List, Optional, Dict, Any

from ..ports.template_port import ITemplateRepository, ITemplateEngine
from ...domain.models.template import (
    Template,
    TemplateCategory,
    TemplateNotFoundError,
    TemplateValidationError
)

logger = logging.getLogger(__name__)


class ListTemplatesUseCase:
    """
    템플릿 목록 조회 Use Case

    카테고리와 태그로 필터링된 템플릿 목록을 조회합니다.
    """

    def __init__(self, template_repository: ITemplateRepository):
        """
        Args:
            template_repository: 템플릿 저장소 리포지토리
        """
        self.template_repository = template_repository

    def execute(
        self,
        category: Optional[TemplateCategory] = None,
        tags: Optional[List[str]] = None
    ) -> List[Template]:
        """
        템플릿 목록 조회 실행

        Args:
            category: 카테고리 필터 (선택)
            tags: 태그 필터 (선택)

        Returns:
            Template 목록

        Raises:
            Exception: 조회 실패 시
        """
        try:
            templates = self.template_repository.list(category=category, tags=tags)
            logger.info(f"템플릿 목록 조회 완료: {len(templates)} 건")
            return templates

        except Exception as e:
            logger.error(f"템플릿 목록 조회 실패: {e}")
            raise


class ApplyTemplateUseCase:
    """
    템플릿 적용 Use Case

    템플릿을 렌더링하여 파일을 생성합니다.
    """

    def __init__(
        self,
        template_repository: ITemplateRepository,
        template_engine: ITemplateEngine
    ):
        """
        Args:
            template_repository: 템플릿 저장소 리포지토리
            template_engine: 템플릿 렌더링 엔진
        """
        self.template_repository = template_repository
        self.template_engine = template_engine

    def execute(
        self,
        template_id: str,
        variables: Dict[str, Any],
        output_dir: Path
    ) -> List[Path]:
        """
        템플릿 적용 실행

        Args:
            template_id: 템플릿 ID
            variables: 템플릿 변수 딕셔너리
            output_dir: 출력 디렉토리

        Returns:
            생성된 파일 경로 목록

        Raises:
            TemplateNotFoundError: 템플릿을 찾을 수 없는 경우
            TemplateValidationError: 변수 검증 실패 시
            Exception: 렌더링 실패 시
        """
        # 1. 템플릿 조회
        template = self.template_repository.get(template_id)
        if not template:
            raise TemplateNotFoundError(f"템플릿을 찾을 수 없습니다: {template_id}")

        # 2. 변수 검증
        errors = template.validate_variables(variables)
        if errors:
            error_msg = "\n".join(errors)
            raise TemplateValidationError(f"변수 검증 실패:\n{error_msg}")

        # 3. 기본값 적용
        final_variables = self._apply_defaults(template, variables)

        # 4. 출력 디렉토리 생성
        output_dir = Path(output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        # 5. 템플릿 렌더링
        try:
            created_files = self.template_engine.render(
                template=template,
                variables=final_variables,
                output_dir=output_dir
            )
            logger.info(
                f"템플릿 적용 완료: {template_id}, "
                f"파일 {len(created_files)}개 생성"
            )
            return created_files

        except Exception as e:
            logger.error(f"템플릿 렌더링 실패: {e}")
            raise

    def _apply_defaults(
        self,
        template: Template,
        variables: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        기본값 적용

        Args:
            template: Template 객체
            variables: 사용자 제공 변수

        Returns:
            기본값이 적용된 변수 딕셔너리
        """
        final_variables = variables.copy()

        for var in template.variables:
            if var.name not in final_variables and var.default is not None:
                final_variables[var.name] = var.default

        return final_variables


class CreateTemplateUseCase:
    """
    템플릿 생성 Use Case

    새로운 템플릿을 생성하여 저장합니다.
    """

    def __init__(self, template_repository: ITemplateRepository):
        """
        Args:
            template_repository: 템플릿 저장소 리포지토리
        """
        self.template_repository = template_repository

    def execute(self, template: Template) -> None:
        """
        템플릿 생성 실행

        Args:
            template: 생성할 Template 객체

        Raises:
            ValueError: 템플릿 데이터가 유효하지 않은 경우
            Exception: 저장 실패 시
        """
        # 1. 템플릿 검증
        self._validate_template(template)

        # 2. 템플릿 저장
        try:
            self.template_repository.save(template)
            logger.info(f"템플릿 생성 완료: {template.id}")

        except Exception as e:
            logger.error(f"템플릿 저장 실패: {e}")
            raise

    def _validate_template(self, template: Template) -> None:
        """
        템플릿 검증

        Args:
            template: 검증할 Template 객체

        Raises:
            ValueError: 템플릿이 유효하지 않은 경우
        """
        if not template.id or not template.id.strip():
            raise ValueError("템플릿 ID는 필수입니다")

        if not template.name or not template.name.strip():
            raise ValueError("템플릿 이름은 필수입니다")

        if not template.description or not template.description.strip():
            raise ValueError("템플릿 설명은 필수입니다")

        if not template.files:
            raise ValueError("템플릿에는 최소 1개의 파일이 필요합니다")

        # 파일 경로 검증 (보안: path traversal 방지)
        for file in template.files:
            if ".." in file.path or file.path.startswith("/"):
                raise ValueError(
                    f"잘못된 파일 경로입니다: {file.path}. "
                    "절대 경로 또는 상위 디렉토리 참조는 허용되지 않습니다."
                )


class SearchTemplatesUseCase:
    """
    템플릿 검색 Use Case

    키워드로 템플릿을 검색합니다.
    """

    def __init__(self, template_repository: ITemplateRepository):
        """
        Args:
            template_repository: 템플릿 저장소 리포지토리
        """
        self.template_repository = template_repository

    def execute(self, query: str) -> List[Template]:
        """
        템플릿 검색 실행

        Args:
            query: 검색 쿼리

        Returns:
            검색된 Template 목록

        Raises:
            ValueError: 검색 쿼리가 유효하지 않은 경우
            Exception: 검색 실패 시
        """
        # 입력 검증
        if not query or not query.strip():
            raise ValueError("검색 쿼리는 필수입니다")

        try:
            templates = self.template_repository.search(query.strip())
            logger.info(f"템플릿 검색 완료: '{query}' -> {len(templates)} 건")
            return templates

        except Exception as e:
            logger.error(f"템플릿 검색 실패: {e}")
            raise
