"""
템플릿 포트 (인터페이스)

ITemplateRepository: 템플릿 저장소 인터페이스
ITemplateEngine: 템플릿 렌더링 엔진 인터페이스
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from pathlib import Path

from src.domain.models.template import Template, TemplateCategory


class ITemplateRepository(ABC):
    """
    템플릿 저장소 인터페이스

    Infrastructure 계층에서 구현됨 (파일 시스템, DB 등)
    """

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def save(self, template: Template) -> None:
        """
        템플릿 저장

        Args:
            template: 저장할 Template 객체

        Raises:
            Exception: 저장 실패 시
        """
        pass

    @abstractmethod
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
        pass


class ITemplateEngine(ABC):
    """
    템플릿 렌더링 엔진 인터페이스

    Infrastructure 계층에서 구현됨 (Jinja2 등)
    """

    @abstractmethod
    def render(
        self,
        template: Template,
        variables: Dict[str, Any],
        output_dir: Path
    ) -> List[Path]:
        """
        템플릿을 렌더링하여 파일 생성

        Args:
            template: 렌더링할 Template 객체
            variables: 템플릿 변수 딕셔너리
            output_dir: 출력 디렉토리

        Returns:
            생성된 파일 경로 목록

        Raises:
            TemplateValidationError: 변수 검증 실패 시
            TemplateRenderError: 렌더링 실패 시
            Exception: 파일 생성 실패 시
        """
        pass

    @abstractmethod
    def render_string(self, template_str: str, variables: Dict[str, Any]) -> str:
        """
        템플릿 문자열 렌더링

        Args:
            template_str: 템플릿 문자열
            variables: 템플릿 변수 딕셔너리

        Returns:
            렌더링된 문자열

        Raises:
            TemplateRenderError: 렌더링 실패 시
        """
        pass
