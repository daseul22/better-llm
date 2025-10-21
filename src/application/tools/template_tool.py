"""
템플릿 도구 - Worker Agent들이 사용할 수 있는 템플릿 Tool

Worker Agent들이 코드 생성 시 템플릿을 활용할 수 있도록 합니다.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional

from ..ports.template_port import ITemplateRepository, ITemplateEngine
from ..use_cases.template_management import (
    ApplyTemplateUseCase,
    ListTemplatesUseCase,
    SearchTemplatesUseCase
)
from src.domain.models.template import (
    TemplateCategory,
    TemplateNotFoundError,
    TemplateValidationError
)

logger = logging.getLogger(__name__)


class ApplyTemplateTool:
    """
    템플릿 적용 도구

    Worker Agent들이 템플릿을 조회하고 적용할 수 있도록 합니다.
    """

    def __init__(
        self,
        template_repository: ITemplateRepository,
        template_engine: ITemplateEngine
    ):
        """
        Args:
            template_repository: 템플릿 저장소
            template_engine: 템플릿 엔진
        """
        self.template_repository = template_repository
        self.template_engine = template_engine

        # Use Cases 초기화
        self.apply_use_case = ApplyTemplateUseCase(
            template_repository, template_engine
        )
        self.list_use_case = ListTemplatesUseCase(template_repository)
        self.search_use_case = SearchTemplatesUseCase(template_repository)

    def list_templates(
        self,
        category: Optional[str] = None,
        tags: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        템플릿 목록 조회

        Args:
            category: 카테고리 필터 (선택)
            tags: 태그 필터 (선택)

        Returns:
            템플릿 목록 정보
        """
        try:
            # 카테고리 변환
            category_enum = None
            if category:
                try:
                    category_enum = TemplateCategory(category)
                except ValueError:
                    return {
                        "success": False,
                        "error": f"잘못된 카테고리입니다: {category}"
                    }

            # 템플릿 조회
            templates = self.list_use_case.execute(
                category=category_enum,
                tags=tags
            )

            # 결과 포맷팅
            template_list = []
            for template in templates:
                template_list.append({
                    "id": template.id,
                    "name": template.name,
                    "description": template.description,
                    "category": template.category.value,
                    "tags": template.tags,
                    "variables": [
                        {
                            "name": v.name,
                            "description": v.description,
                            "required": v.required,
                            "default": v.default
                        }
                        for v in template.variables
                    ]
                })

            return {
                "success": True,
                "templates": template_list,
                "count": len(template_list)
            }

        except Exception as e:
            logger.error(f"템플릿 목록 조회 실패: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def search_templates(self, query: str) -> Dict[str, Any]:
        """
        템플릿 검색

        Args:
            query: 검색 쿼리

        Returns:
            검색 결과
        """
        try:
            templates = self.search_use_case.execute(query)

            # 결과 포맷팅
            template_list = []
            for template in templates:
                template_list.append({
                    "id": template.id,
                    "name": template.name,
                    "description": template.description,
                    "category": template.category.value,
                    "tags": template.tags
                })

            return {
                "success": True,
                "templates": template_list,
                "count": len(template_list),
                "query": query
            }

        except Exception as e:
            logger.error(f"템플릿 검색 실패: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def apply_template(
        self,
        template_id: str,
        variables: Dict[str, Any],
        output_dir: str
    ) -> Dict[str, Any]:
        """
        템플릿 적용

        Args:
            template_id: 템플릿 ID
            variables: 템플릿 변수 딕셔너리
            output_dir: 출력 디렉토리

        Returns:
            적용 결과
        """
        try:
            # 출력 디렉토리 경로 변환
            output_path = Path(output_dir).resolve()

            # 템플릿 적용
            created_files = self.apply_use_case.execute(
                template_id=template_id,
                variables=variables,
                output_dir=output_path
            )

            # 결과 포맷팅
            return {
                "success": True,
                "template_id": template_id,
                "created_files": [str(f) for f in created_files],
                "count": len(created_files),
                "output_dir": str(output_path)
            }

        except TemplateNotFoundError as e:
            logger.error(f"템플릿을 찾을 수 없습니다: {e}")
            return {
                "success": False,
                "error": f"템플릿을 찾을 수 없습니다: {template_id}"
            }

        except TemplateValidationError as e:
            logger.error(f"템플릿 변수 검증 실패: {e}")
            return {
                "success": False,
                "error": f"변수 검증 실패: {e}"
            }

        except Exception as e:
            logger.error(f"템플릿 적용 실패: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def get_template_info(self, template_id: str) -> Dict[str, Any]:
        """
        템플릿 상세 정보 조회

        Args:
            template_id: 템플릿 ID

        Returns:
            템플릿 상세 정보
        """
        try:
            template = self.template_repository.get(template_id)

            if not template:
                return {
                    "success": False,
                    "error": f"템플릿을 찾을 수 없습니다: {template_id}"
                }

            return {
                "success": True,
                "template": {
                    "id": template.id,
                    "name": template.name,
                    "description": template.description,
                    "category": template.category.value,
                    "tags": template.tags,
                    "variables": [
                        {
                            "name": v.name,
                            "description": v.description,
                            "type": v.type.value,
                            "required": v.required,
                            "default": v.default
                        }
                        for v in template.variables
                    ],
                    "files": [
                        {
                            "path": f.path,
                            "encoding": f.encoding
                        }
                        for f in template.files
                    ]
                }
            }

        except Exception as e:
            logger.error(f"템플릿 정보 조회 실패: {e}")
            return {
                "success": False,
                "error": str(e)
            }
