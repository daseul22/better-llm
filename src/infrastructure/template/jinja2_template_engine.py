"""
Jinja2 기반 템플릿 엔진 구현

Jinja2를 사용하여 템플릿을 렌더링합니다.
"""

import logging
from pathlib import Path
from typing import Dict, Any, List

from jinja2 import Template as Jinja2Template, Environment, TemplateError

from src.application.ports.template_port import ITemplateEngine
from src.domain.models.template import (
    Template,
    TemplateValidationError,
    TemplateRenderError
)

logger = logging.getLogger(__name__)


class Jinja2TemplateEngine(ITemplateEngine):
    """
    Jinja2 기반 템플릿 렌더링 엔진

    Jinja2를 사용하여 템플릿을 렌더링하고 파일을 생성합니다.
    """

    def __init__(self):
        """Jinja2 Environment 초기화"""
        self.env = Environment(
            autoescape=False,  # 코드 템플릿이므로 자동 이스케이핑 비활성화
            trim_blocks=True,
            lstrip_blocks=True
        )

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
        # 1. 변수 검증
        errors = template.validate_variables(variables)
        if errors:
            error_msg = "\n".join(errors)
            raise TemplateValidationError(f"변수 검증 실패:\n{error_msg}")

        # 2. 출력 디렉토리 확인 및 생성
        output_dir = Path(output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        created_files = []

        # 3. 각 파일 템플릿 렌더링
        for template_file in template.files:
            try:
                # 3-1. 파일 경로 렌더링 (변수 포함 가능)
                rendered_path = self.render_string(template_file.path, variables)

                # 3-2. 보안: path traversal 공격 방지
                file_path = (output_dir / rendered_path).resolve()
                if not file_path.is_relative_to(output_dir):
                    raise TemplateValidationError(
                        f"보안 위반: 파일 경로가 출력 디렉토리를 벗어납니다: {rendered_path}"
                    )

                # 3-3. 파일 내용 렌더링
                rendered_content = self.render_string(template_file.content, variables)

                # 3-4. 디렉토리 생성
                file_path.parent.mkdir(parents=True, exist_ok=True)

                # 3-5. 파일 쓰기
                file_path.write_text(
                    rendered_content,
                    encoding=template_file.encoding
                )

                created_files.append(file_path)
                logger.info(f"파일 생성 완료: {file_path}")

            except TemplateValidationError:
                raise
            except TemplateError as e:
                raise TemplateRenderError(
                    f"템플릿 렌더링 실패 ({template_file.path}): {e}"
                )
            except Exception as e:
                raise TemplateRenderError(
                    f"파일 생성 실패 ({template_file.path}): {e}"
                )

        logger.info(
            f"템플릿 렌더링 완료: {template.name}, "
            f"파일 {len(created_files)}개 생성"
        )
        return created_files

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
        try:
            jinja_template = self.env.from_string(template_str)
            return jinja_template.render(**variables)

        except TemplateError as e:
            raise TemplateRenderError(f"템플릿 렌더링 실패: {e}")
