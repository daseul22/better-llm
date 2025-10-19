"""
템플릿 Use Cases 단위 테스트

테스트 범위:
- ListTemplatesUseCase (카테고리/태그 필터링)
- ApplyTemplateUseCase (변수 검증, 렌더링)
- CreateTemplateUseCase (템플릿 검증, 저장)
- SearchTemplatesUseCase (검색)
"""

import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, MagicMock

from src.application.use_cases.template_management import (
    ListTemplatesUseCase,
    ApplyTemplateUseCase,
    CreateTemplateUseCase,
    SearchTemplatesUseCase
)
from src.domain.models.template import (
    Template,
    TemplateCategory,
    TemplateVariable,
    TemplateFile,
    VariableType,
    TemplateNotFoundError,
    TemplateValidationError
)


class TestListTemplatesUseCase:
    """ListTemplatesUseCase 테스트"""

    def test_list_all_templates(self):
        """모든 템플릿 목록 조회 테스트"""
        # Mock 설정
        mock_repo = Mock()
        mock_repo.list.return_value = [
            Template(
                id="template-1",
                name="Template 1",
                description="Description 1",
                category=TemplateCategory.WEB_API
            ),
            Template(
                id="template-2",
                name="Template 2",
                description="Description 2",
                category=TemplateCategory.TESTING
            )
        ]

        # Use Case 실행
        use_case = ListTemplatesUseCase(mock_repo)
        templates = use_case.execute()

        # 검증
        assert len(templates) == 2
        assert templates[0].id == "template-1"
        assert templates[1].id == "template-2"
        mock_repo.list.assert_called_once_with(category=None, tags=None)

    def test_list_templates_by_category(self):
        """카테고리 필터링 테스트"""
        # Mock 설정
        mock_repo = Mock()
        mock_repo.list.return_value = [
            Template(
                id="api-template",
                name="API Template",
                description="API Description",
                category=TemplateCategory.WEB_API
            )
        ]

        # Use Case 실행
        use_case = ListTemplatesUseCase(mock_repo)
        templates = use_case.execute(category=TemplateCategory.WEB_API)

        # 검증
        assert len(templates) == 1
        assert templates[0].category == TemplateCategory.WEB_API
        mock_repo.list.assert_called_once_with(
            category=TemplateCategory.WEB_API,
            tags=None
        )

    def test_list_templates_by_tags(self):
        """태그 필터링 테스트"""
        # Mock 설정
        mock_repo = Mock()
        mock_repo.list.return_value = [
            Template(
                id="fastapi-template",
                name="FastAPI Template",
                description="FastAPI Description",
                category=TemplateCategory.WEB_API,
                tags=["fastapi", "api"]
            )
        ]

        # Use Case 실행
        use_case = ListTemplatesUseCase(mock_repo)
        templates = use_case.execute(tags=["fastapi"])

        # 검증
        assert len(templates) == 1
        assert "fastapi" in templates[0].tags
        mock_repo.list.assert_called_once_with(category=None, tags=["fastapi"])

    def test_list_templates_by_category_and_tags(self):
        """카테고리와 태그 동시 필터링 테스트"""
        # Mock 설정
        mock_repo = Mock()
        mock_repo.list.return_value = []

        # Use Case 실행
        use_case = ListTemplatesUseCase(mock_repo)
        templates = use_case.execute(
            category=TemplateCategory.WEB_API,
            tags=["fastapi", "crud"]
        )

        # 검증
        assert len(templates) == 0
        mock_repo.list.assert_called_once_with(
            category=TemplateCategory.WEB_API,
            tags=["fastapi", "crud"]
        )

    def test_list_templates_error(self):
        """저장소 에러 처리 테스트"""
        # Mock 설정
        mock_repo = Mock()
        mock_repo.list.side_effect = Exception("Database error")

        # Use Case 실행 및 검증
        use_case = ListTemplatesUseCase(mock_repo)
        with pytest.raises(Exception, match="Database error"):
            use_case.execute()


class TestApplyTemplateUseCase:
    """ApplyTemplateUseCase 테스트"""

    def test_apply_template_success(self, tmp_path):
        """템플릿 적용 성공 테스트"""
        # 템플릿 생성
        template = Template(
            id="test-template",
            name="Test Template",
            description="Test",
            category=TemplateCategory.WEB_API,
            variables=[
                TemplateVariable(
                    name="name",
                    description="Name",
                    type=VariableType.STRING,
                    required=True
                )
            ],
            files=[
                TemplateFile(
                    path="test.py",
                    content="# {{name}}"
                )
            ]
        )

        # Mock 설정
        mock_repo = Mock()
        mock_repo.get.return_value = template

        mock_engine = Mock()
        mock_engine.render.return_value = [tmp_path / "test.py"]

        # Use Case 실행
        use_case = ApplyTemplateUseCase(mock_repo, mock_engine)
        variables = {"name": "test_value"}
        created_files = use_case.execute("test-template", variables, tmp_path)

        # 검증
        assert len(created_files) == 1
        mock_repo.get.assert_called_once_with("test-template")
        mock_engine.render.assert_called_once()

    def test_apply_template_not_found(self, tmp_path):
        """템플릿을 찾을 수 없는 경우 테스트"""
        # Mock 설정
        mock_repo = Mock()
        mock_repo.get.return_value = None

        mock_engine = Mock()

        # Use Case 실행 및 검증
        use_case = ApplyTemplateUseCase(mock_repo, mock_engine)
        with pytest.raises(TemplateNotFoundError, match="템플릿을 찾을 수 없습니다"):
            use_case.execute("non-existent", {}, tmp_path)

        mock_repo.get.assert_called_once_with("non-existent")
        mock_engine.render.assert_not_called()

    def test_apply_template_validation_error(self, tmp_path):
        """변수 검증 실패 테스트"""
        # 템플릿 생성
        template = Template(
            id="test-template",
            name="Test Template",
            description="Test",
            category=TemplateCategory.WEB_API,
            variables=[
                TemplateVariable(
                    name="required_field",
                    description="Required",
                    type=VariableType.STRING,
                    required=True
                )
            ]
        )

        # Mock 설정
        mock_repo = Mock()
        mock_repo.get.return_value = template

        mock_engine = Mock()

        # Use Case 실행 및 검증
        use_case = ApplyTemplateUseCase(mock_repo, mock_engine)
        variables = {}  # 필수 변수 누락

        with pytest.raises(TemplateValidationError, match="변수 검증 실패"):
            use_case.execute("test-template", variables, tmp_path)

        mock_engine.render.assert_not_called()

    def test_apply_template_with_defaults(self, tmp_path):
        """기본값 적용 테스트"""
        # 템플릿 생성
        template = Template(
            id="test-template",
            name="Test Template",
            description="Test",
            category=TemplateCategory.WEB_API,
            variables=[
                TemplateVariable(
                    name="name",
                    description="Name",
                    type=VariableType.STRING,
                    required=True
                ),
                TemplateVariable(
                    name="version",
                    description="Version",
                    type=VariableType.STRING,
                    required=False,
                    default="1.0.0"
                )
            ]
        )

        # Mock 설정
        mock_repo = Mock()
        mock_repo.get.return_value = template

        mock_engine = Mock()
        mock_engine.render.return_value = []

        # Use Case 실행
        use_case = ApplyTemplateUseCase(mock_repo, mock_engine)
        variables = {"name": "test"}  # version은 기본값 사용
        use_case.execute("test-template", variables, tmp_path)

        # 렌더링 시 기본값이 적용되었는지 검증
        call_args = mock_engine.render.call_args
        rendered_variables = call_args[1]["variables"]
        assert rendered_variables["name"] == "test"
        assert rendered_variables["version"] == "1.0.0"  # 기본값

    def test_apply_template_type_validation(self, tmp_path):
        """변수 타입 검증 테스트"""
        # 템플릿 생성
        template = Template(
            id="test-template",
            name="Test Template",
            description="Test",
            category=TemplateCategory.WEB_API,
            variables=[
                TemplateVariable(
                    name="count",
                    description="Count",
                    type=VariableType.INTEGER,
                    required=True
                )
            ]
        )

        # Mock 설정
        mock_repo = Mock()
        mock_repo.get.return_value = template

        mock_engine = Mock()

        # Use Case 실행 및 검증
        use_case = ApplyTemplateUseCase(mock_repo, mock_engine)
        variables = {"count": "ten"}  # 문자열이지만 정수 타입 기대

        with pytest.raises(TemplateValidationError, match="변수 검증 실패"):
            use_case.execute("test-template", variables, tmp_path)


class TestCreateTemplateUseCase:
    """CreateTemplateUseCase 테스트"""

    def test_create_template_success(self):
        """템플릿 생성 성공 테스트"""
        # 템플릿 생성
        template = Template(
            id="new-template",
            name="New Template",
            description="New Description",
            category=TemplateCategory.WEB_API,
            files=[
                TemplateFile(
                    path="main.py",
                    content="# Main file"
                )
            ]
        )

        # Mock 설정
        mock_repo = Mock()

        # Use Case 실행
        use_case = CreateTemplateUseCase(mock_repo)
        use_case.execute(template)

        # 검증
        mock_repo.save.assert_called_once_with(template)

    def test_create_template_empty_id(self):
        """빈 ID로 생성 시도 테스트"""
        # 템플릿 생성
        template = Template(
            id="",  # 빈 ID
            name="Template",
            description="Description",
            category=TemplateCategory.WEB_API,
            files=[
                TemplateFile(path="file.py", content="content")
            ]
        )

        # Mock 설정
        mock_repo = Mock()

        # Use Case 실행 및 검증
        use_case = CreateTemplateUseCase(mock_repo)
        with pytest.raises(ValueError, match="템플릿 ID는 필수"):
            use_case.execute(template)

        mock_repo.save.assert_not_called()

    def test_create_template_empty_name(self):
        """빈 이름으로 생성 시도 테스트"""
        # 템플릿 생성
        template = Template(
            id="template-id",
            name="",  # 빈 이름
            description="Description",
            category=TemplateCategory.WEB_API,
            files=[
                TemplateFile(path="file.py", content="content")
            ]
        )

        # Mock 설정
        mock_repo = Mock()

        # Use Case 실행 및 검증
        use_case = CreateTemplateUseCase(mock_repo)
        with pytest.raises(ValueError, match="템플릿 이름은 필수"):
            use_case.execute(template)

        mock_repo.save.assert_not_called()

    def test_create_template_no_files(self):
        """파일 없이 생성 시도 테스트"""
        # 템플릿 생성
        template = Template(
            id="template-id",
            name="Template",
            description="Description",
            category=TemplateCategory.WEB_API,
            files=[]  # 파일 없음
        )

        # Mock 설정
        mock_repo = Mock()

        # Use Case 실행 및 검증
        use_case = CreateTemplateUseCase(mock_repo)
        with pytest.raises(ValueError, match="최소 1개의 파일이 필요"):
            use_case.execute(template)

        mock_repo.save.assert_not_called()

    def test_create_template_path_traversal(self):
        """Path traversal 공격 방지 테스트"""
        # 템플릿 생성
        template = Template(
            id="template-id",
            name="Template",
            description="Description",
            category=TemplateCategory.WEB_API,
            files=[
                TemplateFile(
                    path="../../../etc/passwd",  # Path traversal 시도
                    content="malicious"
                )
            ]
        )

        # Mock 설정
        mock_repo = Mock()

        # Use Case 실행 및 검증
        use_case = CreateTemplateUseCase(mock_repo)
        with pytest.raises(ValueError, match="잘못된 파일 경로"):
            use_case.execute(template)

        mock_repo.save.assert_not_called()

    def test_create_template_absolute_path(self):
        """절대 경로 방지 테스트"""
        # 템플릿 생성
        template = Template(
            id="template-id",
            name="Template",
            description="Description",
            category=TemplateCategory.WEB_API,
            files=[
                TemplateFile(
                    path="/etc/passwd",  # 절대 경로
                    content="malicious"
                )
            ]
        )

        # Mock 설정
        mock_repo = Mock()

        # Use Case 실행 및 검증
        use_case = CreateTemplateUseCase(mock_repo)
        with pytest.raises(ValueError, match="잘못된 파일 경로"):
            use_case.execute(template)

        mock_repo.save.assert_not_called()

    def test_create_template_save_error(self):
        """저장 실패 테스트"""
        # 템플릿 생성
        template = Template(
            id="template-id",
            name="Template",
            description="Description",
            category=TemplateCategory.WEB_API,
            files=[
                TemplateFile(path="file.py", content="content")
            ]
        )

        # Mock 설정
        mock_repo = Mock()
        mock_repo.save.side_effect = Exception("Save error")

        # Use Case 실행 및 검증
        use_case = CreateTemplateUseCase(mock_repo)
        with pytest.raises(Exception, match="Save error"):
            use_case.execute(template)


class TestSearchTemplatesUseCase:
    """SearchTemplatesUseCase 테스트"""

    def test_search_templates_success(self):
        """템플릿 검색 성공 테스트"""
        # Mock 설정
        mock_repo = Mock()
        mock_repo.search.return_value = [
            Template(
                id="fastapi-template",
                name="FastAPI Template",
                description="FastAPI CRUD API",
                category=TemplateCategory.WEB_API,
                tags=["fastapi", "api"]
            )
        ]

        # Use Case 실행
        use_case = SearchTemplatesUseCase(mock_repo)
        templates = use_case.execute("fastapi")

        # 검증
        assert len(templates) == 1
        assert "fastapi" in templates[0].name.lower()
        mock_repo.search.assert_called_once_with("fastapi")

    def test_search_templates_empty_query(self):
        """빈 검색 쿼리 테스트"""
        # Mock 설정
        mock_repo = Mock()

        # Use Case 실행 및 검증
        use_case = SearchTemplatesUseCase(mock_repo)
        with pytest.raises(ValueError, match="검색 쿼리는 필수"):
            use_case.execute("")

        mock_repo.search.assert_not_called()

    def test_search_templates_whitespace_query(self):
        """공백만 있는 검색 쿼리 테스트"""
        # Mock 설정
        mock_repo = Mock()

        # Use Case 실행 및 검증
        use_case = SearchTemplatesUseCase(mock_repo)
        with pytest.raises(ValueError, match="검색 쿼리는 필수"):
            use_case.execute("   ")

        mock_repo.search.assert_not_called()

    def test_search_templates_no_results(self):
        """검색 결과 없음 테스트"""
        # Mock 설정
        mock_repo = Mock()
        mock_repo.search.return_value = []

        # Use Case 실행
        use_case = SearchTemplatesUseCase(mock_repo)
        templates = use_case.execute("nonexistent")

        # 검증
        assert len(templates) == 0
        mock_repo.search.assert_called_once_with("nonexistent")

    def test_search_templates_trimmed_query(self):
        """검색 쿼리 공백 제거 테스트"""
        # Mock 설정
        mock_repo = Mock()
        mock_repo.search.return_value = []

        # Use Case 실행
        use_case = SearchTemplatesUseCase(mock_repo)
        use_case.execute("  django  ")

        # 검증 - 공백이 제거된 쿼리로 호출되었는지 확인
        mock_repo.search.assert_called_once_with("django")

    def test_search_templates_error(self):
        """검색 실패 테스트"""
        # Mock 설정
        mock_repo = Mock()
        mock_repo.search.side_effect = Exception("Search error")

        # Use Case 실행 및 검증
        use_case = SearchTemplatesUseCase(mock_repo)
        with pytest.raises(Exception, match="Search error"):
            use_case.execute("query")
