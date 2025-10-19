"""
파일 기반 템플릿 저장소 단위 테스트

테스트 범위:
- YAML 저장/로드 테스트
- 템플릿 검색 테스트
- 카테고리/태그 필터링 테스트
- UTF-8 인코딩 테스트 (한글 지원)
"""

import pytest
from pathlib import Path
from datetime import datetime

from src.infrastructure.template.file_template_repository import FileBasedTemplateRepository
from src.domain.models.template import (
    Template,
    TemplateCategory,
    TemplateVariable,
    TemplateFile,
    VariableType
)


class TestFileBasedTemplateRepository:
    """FileBasedTemplateRepository 테스트"""

    def test_init_creates_storage_directory(self, tmp_path):
        """저장소 초기화 시 디렉토리 생성 테스트"""
        storage_path = tmp_path / "templates"

        repo = FileBasedTemplateRepository(storage_path)

        assert storage_path.exists()
        assert storage_path.is_dir()
        assert repo.storage_path == storage_path.resolve()

    def test_init_default_path(self):
        """기본 경로 설정 테스트"""
        repo = FileBasedTemplateRepository()

        expected_path = Path.home() / ".better-llm" / "templates"
        assert repo.storage_path == expected_path.resolve()

    def test_save_and_get_template(self, tmp_path):
        """템플릿 저장 및 조회 테스트"""
        repo = FileBasedTemplateRepository(tmp_path)

        template = Template(
            id="test-template",
            name="Test Template",
            description="Test Description",
            category=TemplateCategory.WEB_API,
            variables=[
                TemplateVariable(
                    name="var1",
                    description="Variable 1",
                    type=VariableType.STRING,
                    required=True
                )
            ],
            files=[
                TemplateFile(
                    path="test.py",
                    content="print('test')"
                )
            ],
            tags=["test", "unit"]
        )

        # 저장
        repo.save(template)

        # 조회
        loaded_template = repo.get("test-template")

        assert loaded_template is not None
        assert loaded_template.id == "test-template"
        assert loaded_template.name == "Test Template"
        assert loaded_template.description == "Test Description"
        assert loaded_template.category == TemplateCategory.WEB_API
        assert len(loaded_template.variables) == 1
        assert loaded_template.variables[0].name == "var1"
        assert len(loaded_template.files) == 1
        assert loaded_template.files[0].path == "test.py"
        assert loaded_template.tags == ["test", "unit"]

    def test_get_non_existent_template(self, tmp_path):
        """존재하지 않는 템플릿 조회 테스트"""
        repo = FileBasedTemplateRepository(tmp_path)

        result = repo.get("non-existent")

        assert result is None

    def test_list_all_templates(self, tmp_path):
        """모든 템플릿 목록 조회 테스트"""
        repo = FileBasedTemplateRepository(tmp_path)

        # 템플릿 저장
        template1 = Template(
            id="template-1",
            name="Template 1",
            description="Description 1",
            category=TemplateCategory.WEB_API,
            files=[TemplateFile(path="file1.py", content="content1")]
        )
        template2 = Template(
            id="template-2",
            name="Template 2",
            description="Description 2",
            category=TemplateCategory.TESTING,
            files=[TemplateFile(path="file2.py", content="content2")]
        )

        repo.save(template1)
        repo.save(template2)

        # 목록 조회
        templates = repo.list()

        assert len(templates) == 2
        assert any(t.id == "template-1" for t in templates)
        assert any(t.id == "template-2" for t in templates)

    def test_list_templates_by_category(self, tmp_path):
        """카테고리별 템플릿 목록 조회 테스트"""
        repo = FileBasedTemplateRepository(tmp_path)

        # 템플릿 저장
        template1 = Template(
            id="api-template",
            name="API Template",
            description="API Description",
            category=TemplateCategory.WEB_API,
            files=[TemplateFile(path="api.py", content="api")]
        )
        template2 = Template(
            id="test-template",
            name="Test Template",
            description="Test Description",
            category=TemplateCategory.TESTING,
            files=[TemplateFile(path="test.py", content="test")]
        )

        repo.save(template1)
        repo.save(template2)

        # 카테고리 필터링
        api_templates = repo.list(category=TemplateCategory.WEB_API)

        assert len(api_templates) == 1
        assert api_templates[0].id == "api-template"
        assert api_templates[0].category == TemplateCategory.WEB_API

    def test_list_templates_by_tags(self, tmp_path):
        """태그별 템플릿 목록 조회 테스트"""
        repo = FileBasedTemplateRepository(tmp_path)

        # 템플릿 저장
        template1 = Template(
            id="fastapi-template",
            name="FastAPI Template",
            description="FastAPI Description",
            category=TemplateCategory.WEB_API,
            files=[TemplateFile(path="api.py", content="api")],
            tags=["fastapi", "api", "rest"]
        )
        template2 = Template(
            id="django-template",
            name="Django Template",
            description="Django Description",
            category=TemplateCategory.WEB_API,
            files=[TemplateFile(path="views.py", content="views")],
            tags=["django", "api"]
        )
        template3 = Template(
            id="pytest-template",
            name="Pytest Template",
            description="Pytest Description",
            category=TemplateCategory.TESTING,
            files=[TemplateFile(path="test.py", content="test")],
            tags=["pytest", "testing"]
        )

        repo.save(template1)
        repo.save(template2)
        repo.save(template3)

        # 태그 필터링 - "fastapi" 태그
        fastapi_templates = repo.list(tags=["fastapi"])
        assert len(fastapi_templates) == 1
        assert fastapi_templates[0].id == "fastapi-template"

        # 태그 필터링 - "api" 태그 (두 개 일치)
        api_templates = repo.list(tags=["api"])
        assert len(api_templates) == 2

        # 태그 필터링 - "testing" 태그
        testing_templates = repo.list(tags=["testing"])
        assert len(testing_templates) == 1
        assert testing_templates[0].id == "pytest-template"

    def test_list_templates_by_category_and_tags(self, tmp_path):
        """카테고리와 태그 동시 필터링 테스트"""
        repo = FileBasedTemplateRepository(tmp_path)

        # 템플릿 저장
        template1 = Template(
            id="fastapi-crud",
            name="FastAPI CRUD",
            description="FastAPI CRUD API",
            category=TemplateCategory.WEB_API,
            files=[TemplateFile(path="api.py", content="api")],
            tags=["fastapi", "crud", "api"]
        )
        template2 = Template(
            id="fastapi-auth",
            name="FastAPI Auth",
            description="FastAPI Auth",
            category=TemplateCategory.WEB_API,
            files=[TemplateFile(path="auth.py", content="auth")],
            tags=["fastapi", "auth", "api"]
        )
        template3 = Template(
            id="django-crud",
            name="Django CRUD",
            description="Django CRUD",
            category=TemplateCategory.WEB_API,
            files=[TemplateFile(path="views.py", content="views")],
            tags=["django", "crud", "api"]
        )

        repo.save(template1)
        repo.save(template2)
        repo.save(template3)

        # 카테고리와 태그 필터링
        templates = repo.list(
            category=TemplateCategory.WEB_API,
            tags=["fastapi"]
        )

        assert len(templates) == 2
        assert all(t.category == TemplateCategory.WEB_API for t in templates)
        assert all("fastapi" in t.tags for t in templates)

    def test_search_templates_by_name(self, tmp_path):
        """이름으로 템플릿 검색 테스트"""
        repo = FileBasedTemplateRepository(tmp_path)

        # 템플릿 저장
        template1 = Template(
            id="fastapi-crud",
            name="FastAPI CRUD API",
            description="FastAPI CRUD API Description",
            category=TemplateCategory.WEB_API,
            files=[TemplateFile(path="api.py", content="api")]
        )
        template2 = Template(
            id="django-model",
            name="Django Model",
            description="Django Model Description",
            category=TemplateCategory.DATABASE,
            files=[TemplateFile(path="model.py", content="model")]
        )

        repo.save(template1)
        repo.save(template2)

        # 검색
        results = repo.search("fastapi")

        assert len(results) == 1
        assert results[0].id == "fastapi-crud"

    def test_search_templates_by_description(self, tmp_path):
        """설명으로 템플릿 검색 테스트"""
        repo = FileBasedTemplateRepository(tmp_path)

        # 템플릿 저장
        template = Template(
            id="pytest-test",
            name="Pytest Test",
            description="Unit testing with pytest framework",
            category=TemplateCategory.TESTING,
            files=[TemplateFile(path="test.py", content="test")]
        )

        repo.save(template)

        # 검색
        results = repo.search("unit testing")

        assert len(results) == 1
        assert results[0].id == "pytest-test"

    def test_search_templates_by_tags(self, tmp_path):
        """태그로 템플릿 검색 테스트"""
        repo = FileBasedTemplateRepository(tmp_path)

        # 템플릿 저장
        template = Template(
            id="react-component",
            name="React Component",
            description="React functional component",
            category=TemplateCategory.FRONTEND,
            files=[TemplateFile(path="Component.tsx", content="component")],
            tags=["react", "typescript", "frontend"]
        )

        repo.save(template)

        # 검색
        results = repo.search("typescript")

        assert len(results) == 1
        assert results[0].id == "react-component"

    def test_search_templates_case_insensitive(self, tmp_path):
        """대소문자 구분 없는 검색 테스트"""
        repo = FileBasedTemplateRepository(tmp_path)

        # 템플릿 저장
        template = Template(
            id="template-id",
            name="FastAPI Template",
            description="Description",
            category=TemplateCategory.WEB_API,
            files=[TemplateFile(path="api.py", content="api")]
        )

        repo.save(template)

        # 대소문자 다르게 검색
        results_lower = repo.search("fastapi")
        results_upper = repo.search("FASTAPI")
        results_mixed = repo.search("FaStApI")

        assert len(results_lower) == 1
        assert len(results_upper) == 1
        assert len(results_mixed) == 1

    def test_search_templates_no_results(self, tmp_path):
        """검색 결과 없음 테스트"""
        repo = FileBasedTemplateRepository(tmp_path)

        # 템플릿 저장
        template = Template(
            id="template-id",
            name="Template Name",
            description="Description",
            category=TemplateCategory.WEB_API,
            files=[TemplateFile(path="file.py", content="content")]
        )

        repo.save(template)

        # 검색
        results = repo.search("nonexistent")

        assert len(results) == 0

    def test_delete_template(self, tmp_path):
        """템플릿 삭제 테스트"""
        repo = FileBasedTemplateRepository(tmp_path)

        # 템플릿 저장
        template = Template(
            id="delete-me",
            name="Delete Me",
            description="To be deleted",
            category=TemplateCategory.WEB_API,
            files=[TemplateFile(path="file.py", content="content")]
        )

        repo.save(template)
        assert repo.get("delete-me") is not None

        # 삭제
        result = repo.delete("delete-me")

        assert result is True
        assert repo.get("delete-me") is None

    def test_delete_non_existent_template(self, tmp_path):
        """존재하지 않는 템플릿 삭제 테스트"""
        repo = FileBasedTemplateRepository(tmp_path)

        result = repo.delete("non-existent")

        assert result is False

    def test_save_with_korean_name(self, tmp_path):
        """한글 이름 템플릿 저장 테스트 (UTF-8 인코딩)"""
        repo = FileBasedTemplateRepository(tmp_path)

        template = Template(
            id="korean-template",
            name="한글 템플릿",
            description="한글 설명입니다",
            category=TemplateCategory.WEB_API,
            files=[
                TemplateFile(
                    path="파일.py",
                    content="# 한글 주석"
                )
            ],
            tags=["한글", "테스트"]
        )

        # 저장
        repo.save(template)

        # 조회
        loaded_template = repo.get("korean-template")

        assert loaded_template is not None
        assert loaded_template.name == "한글 템플릿"
        assert loaded_template.description == "한글 설명입니다"
        assert loaded_template.files[0].path == "파일.py"
        assert loaded_template.files[0].content == "# 한글 주석"
        assert "한글" in loaded_template.tags
        assert "테스트" in loaded_template.tags

    def test_search_with_korean_query(self, tmp_path):
        """한글 검색 쿼리 테스트"""
        repo = FileBasedTemplateRepository(tmp_path)

        # 템플릿 저장
        template = Template(
            id="korean-template",
            name="한글 템플릿",
            description="FastAPI를 사용한 REST API",
            category=TemplateCategory.WEB_API,
            files=[TemplateFile(path="api.py", content="api")],
            tags=["한글", "API"]
        )

        repo.save(template)

        # 한글 검색
        results = repo.search("한글")

        assert len(results) == 1
        assert results[0].id == "korean-template"

    def test_yaml_format_integrity(self, tmp_path):
        """YAML 파일 형식 무결성 테스트"""
        repo = FileBasedTemplateRepository(tmp_path)

        template = Template(
            id="yaml-test",
            name="YAML Test",
            description="Test YAML format",
            category=TemplateCategory.WEB_API,
            variables=[
                TemplateVariable(
                    name="test_var",
                    description="Test variable",
                    type=VariableType.STRING,
                    required=True,
                    default="default_value"
                )
            ],
            files=[
                TemplateFile(
                    path="test.py",
                    content="# Test content"
                )
            ],
            tags=["test"]
        )

        # 저장
        repo.save(template)

        # YAML 파일 직접 확인
        yaml_file = tmp_path / "yaml-test.yaml"
        assert yaml_file.exists()

        # 다시 로드하여 데이터 무결성 확인
        loaded_template = repo.get("yaml-test")
        assert loaded_template.variables[0].name == "test_var"
        assert loaded_template.variables[0].default == "default_value"

    def test_list_handles_corrupted_file(self, tmp_path):
        """손상된 파일이 있을 때 목록 조회 테스트"""
        repo = FileBasedTemplateRepository(tmp_path)

        # 정상 템플릿 저장
        template = Template(
            id="valid-template",
            name="Valid Template",
            description="Valid",
            category=TemplateCategory.WEB_API,
            files=[TemplateFile(path="file.py", content="content")]
        )
        repo.save(template)

        # 손상된 파일 생성
        corrupted_file = tmp_path / "corrupted.yaml"
        corrupted_file.write_text("invalid: yaml: content: ::::", encoding="utf-8")

        # 목록 조회 - 정상 템플릿만 반환되어야 함
        templates = repo.list()

        assert len(templates) == 1
        assert templates[0].id == "valid-template"

    def test_update_template(self, tmp_path):
        """템플릿 업데이트 테스트"""
        repo = FileBasedTemplateRepository(tmp_path)

        # 초기 템플릿 저장
        template = Template(
            id="update-test",
            name="Original Name",
            description="Original Description",
            category=TemplateCategory.WEB_API,
            files=[TemplateFile(path="file.py", content="original")]
        )
        repo.save(template)

        # 템플릿 수정
        updated_template = Template(
            id="update-test",
            name="Updated Name",
            description="Updated Description",
            category=TemplateCategory.TESTING,
            files=[TemplateFile(path="file.py", content="updated")]
        )
        repo.save(updated_template)

        # 조회
        loaded_template = repo.get("update-test")

        assert loaded_template.name == "Updated Name"
        assert loaded_template.description == "Updated Description"
        assert loaded_template.category == TemplateCategory.TESTING
        assert loaded_template.files[0].content == "updated"

    def test_empty_repository(self, tmp_path):
        """빈 저장소 테스트"""
        repo = FileBasedTemplateRepository(tmp_path)

        templates = repo.list()

        assert len(templates) == 0

    def test_list_with_no_matches(self, tmp_path):
        """필터링 결과가 없는 경우 테스트"""
        repo = FileBasedTemplateRepository(tmp_path)

        # 템플릿 저장
        template = Template(
            id="template-id",
            name="Template",
            description="Description",
            category=TemplateCategory.WEB_API,
            files=[TemplateFile(path="file.py", content="content")],
            tags=["api"]
        )
        repo.save(template)

        # 일치하지 않는 카테고리로 필터링
        templates = repo.list(category=TemplateCategory.TESTING)

        assert len(templates) == 0

        # 일치하지 않는 태그로 필터링
        templates = repo.list(tags=["nonexistent"])

        assert len(templates) == 0
