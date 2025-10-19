"""
파일 기반 템플릿 저장소 구현

YAML 파일로 템플릿을 저장하고 관리합니다.
"""

import logging
import yaml
from pathlib import Path
from typing import Optional, List

from ...application.ports.template_port import ITemplateRepository
from ...domain.models.template import Template, TemplateCategory

logger = logging.getLogger(__name__)


class FileBasedTemplateRepository(ITemplateRepository):
    """
    파일 시스템 기반 템플릿 저장소

    YAML 파일로 템플릿을 저장하고 관리합니다.
    기본 경로: ~/.better-llm/templates/
    """

    def __init__(self, storage_path: Optional[Path] = None):
        """
        Args:
            storage_path: 템플릿 저장 경로 (기본값: ~/.better-llm/templates/)
        """
        if storage_path is None:
            storage_path = Path.home() / ".better-llm" / "templates"

        self.storage_path = Path(storage_path).resolve()
        self.storage_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"템플릿 저장소 초기화: {self.storage_path}")

    def get(self, template_id: str) -> Optional[Template]:
        """
        템플릿 조회

        Args:
            template_id: 템플릿 ID

        Returns:
            Template 객체 또는 None

        Raises:
            Exception: 조회 실패 시
        """
        template_file = self.storage_path / f"{template_id}.yaml"

        if not template_file.exists():
            logger.warning(f"템플릿을 찾을 수 없습니다: {template_id}")
            return None

        try:
            with template_file.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            template = Template.from_dict(data)
            logger.debug(f"템플릿 로드 완료: {template_id}")
            return template

        except Exception as e:
            logger.error(f"템플릿 로드 실패 ({template_id}): {e}")
            raise

    def list(
        self,
        category: Optional[TemplateCategory] = None,
        tags: Optional[List[str]] = None
    ) -> List[Template]:
        """
        템플릿 목록 조회

        Args:
            category: 카테고리 필터 (선택)
            tags: 태그 필터 (선택)

        Returns:
            Template 목록

        Raises:
            Exception: 조회 실패 시
        """
        templates = []

        # 모든 YAML 파일 읽기
        for template_file in self.storage_path.glob("*.yaml"):
            try:
                with template_file.open("r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)

                template = Template.from_dict(data)

                # 카테고리 필터링
                if category and template.category != category:
                    continue

                # 태그 필터링 (하나라도 일치하면 포함)
                if tags and not any(tag in template.tags for tag in tags):
                    continue

                templates.append(template)

            except Exception as e:
                logger.warning(f"템플릿 로드 실패 ({template_file.name}): {e}")
                continue

        logger.info(f"템플릿 목록 조회 완료: {len(templates)} 건")
        return templates

    def search(self, query: str) -> List[Template]:
        """
        템플릿 검색

        Args:
            query: 검색 쿼리 (이름, 설명, 태그에서 검색)

        Returns:
            검색된 Template 목록

        Raises:
            Exception: 검색 실패 시
        """
        query_lower = query.lower()
        templates = []

        # 모든 YAML 파일 읽기
        for template_file in self.storage_path.glob("*.yaml"):
            try:
                with template_file.open("r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)

                template = Template.from_dict(data)

                # 이름, 설명, 태그에서 검색
                if (
                    query_lower in template.name.lower()
                    or query_lower in template.description.lower()
                    or any(query_lower in tag.lower() for tag in template.tags)
                ):
                    templates.append(template)

            except Exception as e:
                logger.warning(f"템플릿 로드 실패 ({template_file.name}): {e}")
                continue

        logger.info(f"템플릿 검색 완료: '{query}' -> {len(templates)} 건")
        return templates

    def save(self, template: Template) -> None:
        """
        템플릿 저장

        Args:
            template: 저장할 Template 객체

        Raises:
            Exception: 저장 실패 시
        """
        template_file = self.storage_path / f"{template.id}.yaml"

        try:
            # 템플릿을 딕셔너리로 변환
            data = template.to_dict()

            # YAML 파일로 저장
            with template_file.open("w", encoding="utf-8") as f:
                yaml.safe_dump(
                    data,
                    f,
                    allow_unicode=True,
                    default_flow_style=False,
                    sort_keys=False
                )

            logger.info(f"템플릿 저장 완료: {template.id} -> {template_file}")

        except Exception as e:
            logger.error(f"템플릿 저장 실패 ({template.id}): {e}")
            raise

    def delete(self, template_id: str) -> bool:
        """
        템플릿 삭제

        Args:
            template_id: 템플릿 ID

        Returns:
            삭제 성공 여부

        Raises:
            Exception: 삭제 실패 시
        """
        template_file = self.storage_path / f"{template_id}.yaml"

        if not template_file.exists():
            logger.warning(f"템플릿을 찾을 수 없습니다: {template_id}")
            return False

        try:
            template_file.unlink()
            logger.info(f"템플릿 삭제 완료: {template_id}")
            return True

        except Exception as e:
            logger.error(f"템플릿 삭제 실패 ({template_id}): {e}")
            raise
