"""
템플릿 시스템 통합 테스트

테스트 범위:
- 전체 워크플로우 테스트 (템플릿 초기화 -> 목록 조회 -> 적용)
- LIST 타입 변수 파싱 테스트 (Critical 이슈 수정 검증)
- React Component 템플릿 렌더링 테스트 (Critical 이슈 수정 검증)
- 내장 템플릿 검증
"""

import pytest
import json
from pathlib import Path
from datetime import datetime

from src.application.use_cases.template_management import (
    ListTemplatesUseCase,
    ApplyTemplateUseCase,
    CreateTemplateUseCase,
    SearchTemplatesUseCase
)
from src.infrastructure.template.file_template_repository import FileBasedTemplateRepository
from src.infrastructure.template.jinja2_template_engine import Jinja2TemplateEngine
from src.infrastructure.template.builtin_templates import get_builtin_templates
from src.domain.models.template import (
    Template,
    TemplateCategory,
    TemplateVariable,
    TemplateFile,
    VariableType
)


class TestTemplateWorkflow:
    """템플릿 시스템 전체 워크플로우 테스트"""

    def test_full_workflow_fastapi_crud(self, tmp_path):
        """
        전체 워크플로우 테스트: FastAPI CRUD 템플릿

        1. 내장 템플릿 초기화
        2. 템플릿 목록 조회
        3. 템플릿 적용 (FastAPI CRUD)
        4. 생성된 파일 검증
        """
        # 1. 저장소 및 엔진 초기화
        storage_path = tmp_path / "templates"
        repo = FileBasedTemplateRepository(storage_path)
        engine = Jinja2TemplateEngine()

        # 2. 내장 템플릿 초기화
        builtin_templates = get_builtin_templates()
        for template in builtin_templates:
            repo.save(template)

        # 3. 템플릿 목록 조회
        list_use_case = ListTemplatesUseCase(repo)
        all_templates = list_use_case.execute()
        assert len(all_templates) == 4  # FastAPI, pytest, Django, React

        # 4. FastAPI CRUD 템플릿 적용
        apply_use_case = ApplyTemplateUseCase(repo, engine)
        output_dir = tmp_path / "output"

        variables = {
            "entity_name": "user",
            "entity_name_plural": "users",
            "fields": ["id: int", "name: str", "email: str"]
        }

        created_files = apply_use_case.execute("fastapi-crud", variables, output_dir)

        # 5. 생성된 파일 검증
        assert len(created_files) == 3  # routes, schemas, models

        # routes/user.py 검증
        routes_file = output_dir / "routes" / "user.py"
        assert routes_file.exists()
        routes_content = routes_file.read_text()
        assert "def list_users()" in routes_content
        assert "def get_user(id: int)" in routes_content
        assert "def create_user(" in routes_content

        # schemas/user.py 검증
        schemas_file = output_dir / "schemas" / "user.py"
        assert schemas_file.exists()
        schemas_content = schemas_file.read_text()
        assert "class UserBase(BaseModel)" in schemas_content
        assert "class UserCreate(UserBase)" in schemas_content

        # models/user.py 검증
        models_file = output_dir / "models" / "user.py"
        assert models_file.exists()
        models_content = models_file.read_text()
        assert "class User(Base)" in models_content
        assert '__tablename__ = "users"' in models_content

    def test_list_type_variable_parsing_json_array(self, tmp_path):
        """
        LIST 타입 변수 파싱 테스트 - JSON 배열 입력

        Critical 이슈 수정 검증:
        - JSON 배열 형식 입력: ["id", "name", "email"]
        """
        repo = FileBasedTemplateRepository(tmp_path / "templates")
        engine = Jinja2TemplateEngine()

        # 템플릿 생성
        template = Template(
            id="list-test",
            name="List Test",
            description="Test LIST type variable",
            category=TemplateCategory.WEB_API,
            variables=[
                TemplateVariable(
                    name="fields",
                    description="Field list",
                    type=VariableType.LIST,
                    required=True
                )
            ],
            files=[
                TemplateFile(
                    path="test.py",
                    content="fields = {{fields}}"
                )
            ]
        )

        repo.save(template)

        # JSON 배열 형식 변수
        variables = {
            "fields": ["id", "name", "email"]  # 리스트 타입
        }

        # 템플릿 적용
        apply_use_case = ApplyTemplateUseCase(repo, engine)
        output_dir = tmp_path / "output"

        created_files = apply_use_case.execute("list-test", variables, output_dir)

        # 검증
        assert len(created_files) == 1
        content = created_files[0].read_text()
        assert "['id', 'name', 'email']" in content

    def test_list_type_variable_in_loop(self, tmp_path):
        """
        LIST 타입 변수를 반복문에서 사용하는 테스트
        """
        repo = FileBasedTemplateRepository(tmp_path / "templates")
        engine = Jinja2TemplateEngine()

        # 템플릿 생성
        template = Template(
            id="list-loop-test",
            name="List Loop Test",
            description="Test LIST in loop",
            category=TemplateCategory.WEB_API,
            variables=[
                TemplateVariable(
                    name="fields",
                    description="Field list",
                    type=VariableType.LIST,
                    required=True
                )
            ],
            files=[
                TemplateFile(
                    path="model.py",
                    content="""class Model:
{% for field in fields %}    {{field}}
{% endfor %}"""
                )
            ]
        )

        repo.save(template)

        # 변수
        variables = {
            "fields": ["id: int", "name: str", "created_at: datetime"]
        }

        # 템플릿 적용
        apply_use_case = ApplyTemplateUseCase(repo, engine)
        output_dir = tmp_path / "output"

        created_files = apply_use_case.execute("list-loop-test", variables, output_dir)

        # 검증
        assert len(created_files) == 1
        content = created_files[0].read_text()
        assert "id: int" in content
        assert "name: str" in content
        assert "created_at: datetime" in content

    def test_react_component_template_rendering(self, tmp_path):
        """
        React Component 템플릿 렌더링 테스트

        Critical 이슈 수정 검증:
        - JavaScript 주석 문법 검증 (/* ... */)
        - TypeScript interface export 검증
        """
        repo = FileBasedTemplateRepository(tmp_path / "templates")
        engine = Jinja2TemplateEngine()

        # 내장 React Component 템플릿 로드
        builtin_templates = get_builtin_templates()
        react_template = next(
            t for t in builtin_templates if t.id == "react-component"
        )
        repo.save(react_template)

        # 변수
        variables = {
            "component_name": "UserProfile",
            "use_typescript": True
        }

        # 템플릿 적용
        apply_use_case = ApplyTemplateUseCase(repo, engine)
        output_dir = tmp_path / "output"

        created_files = apply_use_case.execute("react-component", variables, output_dir)

        # 검증
        assert len(created_files) == 3  # Component.tsx, .css, index.ts

        # Component.tsx 검증
        component_file = output_dir / "components" / "UserProfile" / "UserProfile.tsx"
        assert component_file.exists()
        component_content = component_file.read_text()

        # JavaScript 주석 문법 검증
        assert "/* React UserProfile 컴포넌트 */" in component_content

        # TypeScript interface export 검증
        assert "export interface UserProfileProps" in component_content
        assert "export const UserProfile: React.FC<UserProfileProps>" in component_content
        assert "export default UserProfile;" in component_content

        # CSS 파일 검증
        css_file = output_dir / "components" / "UserProfile" / "UserProfile.css"
        assert css_file.exists()
        css_content = css_file.read_text()
        assert ".userprofile" in css_content

        # index.ts 검증
        index_file = output_dir / "components" / "UserProfile" / "index.ts"
        assert index_file.exists()
        index_content = index_file.read_text()
        assert "export { UserProfile }" in index_content
        assert "export type { UserProfileProps }" in index_content

    def test_template_search_and_apply(self, tmp_path):
        """
        템플릿 검색 및 적용 테스트
        """
        storage_path = tmp_path / "templates"
        repo = FileBasedTemplateRepository(storage_path)
        engine = Jinja2TemplateEngine()

        # 내장 템플릿 초기화
        builtin_templates = get_builtin_templates()
        for template in builtin_templates:
            repo.save(template)

        # 1. 템플릿 검색
        search_use_case = SearchTemplatesUseCase(repo)
        results = search_use_case.execute("pytest")

        assert len(results) == 1
        assert results[0].id == "pytest-test"

        # 2. 검색된 템플릿 적용
        apply_use_case = ApplyTemplateUseCase(repo, engine)
        output_dir = tmp_path / "output"

        variables = {
            "module_name": "utils",
            "test_cases": ["test_basic", "test_advanced"]
        }

        created_files = apply_use_case.execute("pytest-test", variables, output_dir)

        # 검증
        assert len(created_files) == 1
        test_file = output_dir / "test_utils.py"
        assert test_file.exists()

        content = test_file.read_text()
        assert "class TestUtils:" in content
        assert "def test_basic_functionality(self):" in content

    def test_category_filtering_workflow(self, tmp_path):
        """
        카테고리 필터링 워크플로우 테스트
        """
        storage_path = tmp_path / "templates"
        repo = FileBasedTemplateRepository(storage_path)

        # 내장 템플릿 초기화
        builtin_templates = get_builtin_templates()
        for template in builtin_templates:
            repo.save(template)

        # 카테고리별 조회
        list_use_case = ListTemplatesUseCase(repo)

        # WEB_API 카테고리
        web_api_templates = list_use_case.execute(category=TemplateCategory.WEB_API)
        assert len(web_api_templates) == 1
        assert web_api_templates[0].id == "fastapi-crud"

        # TESTING 카테고리
        testing_templates = list_use_case.execute(category=TemplateCategory.TESTING)
        assert len(testing_templates) == 1
        assert testing_templates[0].id == "pytest-test"

        # DATABASE 카테고리
        database_templates = list_use_case.execute(category=TemplateCategory.DATABASE)
        assert len(database_templates) == 1
        assert database_templates[0].id == "django-model"

        # FRONTEND 카테고리
        frontend_templates = list_use_case.execute(category=TemplateCategory.FRONTEND)
        assert len(frontend_templates) == 1
        assert frontend_templates[0].id == "react-component"

    def test_tag_filtering_workflow(self, tmp_path):
        """
        태그 필터링 워크플로우 테스트
        """
        storage_path = tmp_path / "templates"
        repo = FileBasedTemplateRepository(storage_path)

        # 내장 템플릿 초기화
        builtin_templates = get_builtin_templates()
        for template in builtin_templates:
            repo.save(template)

        # 태그별 조회
        list_use_case = ListTemplatesUseCase(repo)

        # "api" 태그
        api_templates = list_use_case.execute(tags=["api"])
        assert len(api_templates) >= 1
        assert any(t.id == "fastapi-crud" for t in api_templates)

        # "testing" 태그
        testing_templates = list_use_case.execute(tags=["testing"])
        assert len(testing_templates) >= 1
        assert any(t.id == "pytest-test" for t in testing_templates)

        # "react" 태그
        react_templates = list_use_case.execute(tags=["react"])
        assert len(react_templates) >= 1
        assert any(t.id == "react-component" for t in react_templates)

    def test_custom_template_creation_and_usage(self, tmp_path):
        """
        커스텀 템플릿 생성 및 사용 테스트
        """
        storage_path = tmp_path / "templates"
        repo = FileBasedTemplateRepository(storage_path)
        engine = Jinja2TemplateEngine()

        # 1. 커스텀 템플릿 생성
        custom_template = Template(
            id="custom-flask-api",
            name="Flask REST API",
            description="Flask를 사용한 REST API",
            category=TemplateCategory.WEB_API,
            variables=[
                TemplateVariable(
                    name="resource_name",
                    description="리소스 이름",
                    type=VariableType.STRING,
                    required=True
                ),
                TemplateVariable(
                    name="port",
                    description="포트 번호",
                    type=VariableType.INTEGER,
                    required=False,
                    default=5000
                )
            ],
            files=[
                TemplateFile(
                    path="app.py",
                    content="""from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/{{resource_name}}', methods=['GET'])
def get_{{resource_name}}():
    return jsonify({"message": "GET {{resource_name}}"})

if __name__ == '__main__':
    app.run(port={{port}})
"""
                )
            ],
            tags=["flask", "api", "rest"]
        )

        # 2. 템플릿 저장
        create_use_case = CreateTemplateUseCase(repo)
        create_use_case.execute(custom_template)

        # 3. 템플릿 조회
        saved_template = repo.get("custom-flask-api")
        assert saved_template is not None
        assert saved_template.name == "Flask REST API"

        # 4. 템플릿 적용
        apply_use_case = ApplyTemplateUseCase(repo, engine)
        output_dir = tmp_path / "output"

        variables = {
            "resource_name": "users"
            # port는 기본값 사용
        }

        created_files = apply_use_case.execute("custom-flask-api", variables, output_dir)

        # 5. 검증
        assert len(created_files) == 1
        app_file = output_dir / "app.py"
        assert app_file.exists()

        content = app_file.read_text()
        assert "def get_users():" in content
        assert "app.run(port=5000)" in content  # 기본값 적용

    def test_django_model_template(self, tmp_path):
        """
        Django Model 템플릿 테스트
        """
        storage_path = tmp_path / "templates"
        repo = FileBasedTemplateRepository(storage_path)
        engine = Jinja2TemplateEngine()

        # 내장 템플릿 로드
        builtin_templates = get_builtin_templates()
        django_template = next(
            t for t in builtin_templates if t.id == "django-model"
        )
        repo.save(django_template)

        # 변수
        variables = {
            "model_name": "Article",
            "app_name": "blog"
        }

        # 템플릿 적용
        apply_use_case = ApplyTemplateUseCase(repo, engine)
        output_dir = tmp_path / "output"

        created_files = apply_use_case.execute("django-model", variables, output_dir)

        # 검증
        assert len(created_files) == 2  # models/article.py, admin.py

        # models/article.py 검증
        model_file = output_dir / "blog" / "models" / "article.py"
        assert model_file.exists()
        model_content = model_file.read_text()
        assert "class Article(models.Model):" in model_content

        # admin.py 검증
        admin_file = output_dir / "blog" / "admin.py"
        assert admin_file.exists()
        admin_content = admin_file.read_text()
        assert "@admin.register(Article)" in admin_content
        assert "class ArticleAdmin(admin.ModelAdmin):" in admin_content

    def test_error_handling_workflow(self, tmp_path):
        """
        에러 처리 워크플로우 테스트
        """
        storage_path = tmp_path / "templates"
        repo = FileBasedTemplateRepository(storage_path)
        engine = Jinja2TemplateEngine()

        # 내장 템플릿 초기화
        builtin_templates = get_builtin_templates()
        for template in builtin_templates:
            repo.save(template)

        apply_use_case = ApplyTemplateUseCase(repo, engine)
        output_dir = tmp_path / "output"

        # 1. 존재하지 않는 템플릿
        from src.domain.models.template import TemplateNotFoundError
        with pytest.raises(TemplateNotFoundError):
            apply_use_case.execute("non-existent", {}, output_dir)

        # 2. 필수 변수 누락
        from src.domain.models.template import TemplateValidationError
        with pytest.raises(TemplateValidationError):
            apply_use_case.execute("fastapi-crud", {}, output_dir)  # 필수 변수 없음

        # 3. 잘못된 변수 타입
        with pytest.raises(TemplateValidationError):
            apply_use_case.execute(
                "react-component",
                {
                    "component_name": "Test",
                    "use_typescript": "yes"  # boolean이 아닌 string
                },
                output_dir
            )

    def test_builtin_templates_integrity(self, tmp_path):
        """
        내장 템플릿 무결성 테스트
        """
        builtin_templates = get_builtin_templates()

        # 4개의 내장 템플릿 확인
        assert len(builtin_templates) == 4

        template_ids = [t.id for t in builtin_templates]
        assert "fastapi-crud" in template_ids
        assert "pytest-test" in template_ids
        assert "django-model" in template_ids
        assert "react-component" in template_ids

        # 각 템플릿 검증
        for template in builtin_templates:
            # 필수 필드 확인
            assert template.id
            assert template.name
            assert template.description
            assert template.category
            assert len(template.files) > 0

            # 변수 검증
            for var in template.variables:
                assert var.name
                assert var.description
                assert var.type in VariableType

            # 파일 검증
            for file in template.files:
                assert file.path
                assert file.content
                assert file.encoding == "utf-8"

    def test_utf8_encoding_workflow(self, tmp_path):
        """
        UTF-8 인코딩 워크플로우 테스트 (한글 지원)
        """
        storage_path = tmp_path / "templates"
        repo = FileBasedTemplateRepository(storage_path)
        engine = Jinja2TemplateEngine()

        # 한글 템플릿 생성
        korean_template = Template(
            id="korean-readme",
            name="한글 README",
            description="한글 README 템플릿",
            category=TemplateCategory.CUSTOM,
            variables=[
                TemplateVariable(
                    name="project_name",
                    description="프로젝트 이름",
                    type=VariableType.STRING,
                    required=True
                ),
                TemplateVariable(
                    name="author",
                    description="작성자",
                    type=VariableType.STRING,
                    required=True
                )
            ],
            files=[
                TemplateFile(
                    path="README_KO.md",
                    content="""# {{project_name}}

## 소개

이 프로젝트는 {{author}}가 작성했습니다.

## 설치 방법

```bash
pip install {{project_name}}
```

## 사용 방법

자세한 내용은 문서를 참조하세요.
""",
                    encoding="utf-8"
                )
            ],
            tags=["한글", "문서", "readme"]
        )

        # 저장 및 적용
        create_use_case = CreateTemplateUseCase(repo)
        create_use_case.execute(korean_template)

        apply_use_case = ApplyTemplateUseCase(repo, engine)
        output_dir = tmp_path / "output"

        variables = {
            "project_name": "한글프로젝트",
            "author": "홍길동"
        }

        created_files = apply_use_case.execute("korean-readme", variables, output_dir)

        # 검증
        assert len(created_files) == 1
        readme_file = output_dir / "README_KO.md"
        assert readme_file.exists()

        content = readme_file.read_text(encoding="utf-8")
        assert "# 한글프로젝트" in content
        assert "이 프로젝트는 홍길동가 작성했습니다." in content
        assert "설치 방법" in content
