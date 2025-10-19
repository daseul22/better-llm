"""
Jinja2 템플릿 엔진 단위 테스트

테스트 범위:
- 템플릿 렌더링 테스트
- Path traversal 공격 방지 테스트 (보안)
- 변수 치환 테스트
- 에러 처리 테스트
"""

import pytest
from pathlib import Path
from datetime import datetime

from src.infrastructure.template.jinja2_template_engine import Jinja2TemplateEngine
from src.domain.models.template import (
    Template,
    TemplateCategory,
    TemplateVariable,
    TemplateFile,
    VariableType,
    TemplateValidationError,
    TemplateRenderError
)


class TestJinja2TemplateEngine:
    """Jinja2TemplateEngine 테스트"""

    def test_render_string_simple(self):
        """간단한 문자열 렌더링 테스트"""
        engine = Jinja2TemplateEngine()

        template_str = "Hello, {{name}}!"
        variables = {"name": "World"}

        result = engine.render_string(template_str, variables)

        assert result == "Hello, World!"

    def test_render_string_multiple_variables(self):
        """여러 변수 렌더링 테스트"""
        engine = Jinja2TemplateEngine()

        template_str = "{{greeting}}, {{name}}! You are {{age}} years old."
        variables = {"greeting": "Hello", "name": "Alice", "age": 30}

        result = engine.render_string(template_str, variables)

        assert result == "Hello, Alice! You are 30 years old."

    def test_render_string_with_filters(self):
        """Jinja2 필터 사용 테스트"""
        engine = Jinja2TemplateEngine()

        template_str = "{{name|capitalize}}"
        variables = {"name": "john"}

        result = engine.render_string(template_str, variables)

        assert result == "John"

    def test_render_string_with_loop(self):
        """반복문 렌더링 테스트"""
        engine = Jinja2TemplateEngine()

        template_str = "{% for item in items %}{{item}}, {% endfor %}"
        variables = {"items": ["a", "b", "c"]}

        result = engine.render_string(template_str, variables)

        assert result == "a, b, c, "

    def test_render_string_error(self):
        """렌더링 에러 테스트"""
        engine = Jinja2TemplateEngine()

        # 잘못된 템플릿 문법
        template_str = "{{name"
        variables = {"name": "test"}

        with pytest.raises(TemplateRenderError, match="템플릿 렌더링 실패"):
            engine.render_string(template_str, variables)

    def test_render_file_simple(self, tmp_path):
        """간단한 파일 렌더링 테스트"""
        engine = Jinja2TemplateEngine()

        template = Template(
            id="test-template",
            name="Test",
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
                    path="hello.txt",
                    content="Hello, {{name}}!"
                )
            ]
        )

        variables = {"name": "World"}
        output_dir = tmp_path / "output"

        created_files = engine.render(template, variables, output_dir)

        assert len(created_files) == 1
        assert created_files[0].name == "hello.txt"
        assert created_files[0].read_text() == "Hello, World!"

    def test_render_multiple_files(self, tmp_path):
        """여러 파일 렌더링 테스트"""
        engine = Jinja2TemplateEngine()

        template = Template(
            id="test-template",
            name="Test",
            description="Test",
            category=TemplateCategory.WEB_API,
            variables=[
                TemplateVariable(
                    name="module_name",
                    description="Module name",
                    type=VariableType.STRING,
                    required=True
                )
            ],
            files=[
                TemplateFile(
                    path="{{module_name}}.py",
                    content="# {{module_name}} module"
                ),
                TemplateFile(
                    path="test_{{module_name}}.py",
                    content="# Test for {{module_name}}"
                )
            ]
        )

        variables = {"module_name": "auth"}
        output_dir = tmp_path / "output"

        created_files = engine.render(template, variables, output_dir)

        assert len(created_files) == 2
        assert (output_dir / "auth.py").exists()
        assert (output_dir / "test_auth.py").exists()
        assert (output_dir / "auth.py").read_text() == "# auth module"
        assert (output_dir / "test_auth.py").read_text() == "# Test for auth"

    def test_render_with_subdirectory(self, tmp_path):
        """하위 디렉토리 생성 테스트"""
        engine = Jinja2TemplateEngine()

        template = Template(
            id="test-template",
            name="Test",
            description="Test",
            category=TemplateCategory.WEB_API,
            variables=[],
            files=[
                TemplateFile(
                    path="src/models/user.py",
                    content="# User model"
                )
            ]
        )

        variables = {}
        output_dir = tmp_path / "output"

        created_files = engine.render(template, variables, output_dir)

        assert len(created_files) == 1
        assert (output_dir / "src" / "models" / "user.py").exists()
        assert (output_dir / "src" / "models" / "user.py").read_text() == "# User model"

    def test_render_validation_error_required_field(self, tmp_path):
        """필수 변수 누락 시 검증 에러 테스트"""
        engine = Jinja2TemplateEngine()

        template = Template(
            id="test-template",
            name="Test",
            description="Test",
            category=TemplateCategory.WEB_API,
            variables=[
                TemplateVariable(
                    name="required_field",
                    description="Required",
                    type=VariableType.STRING,
                    required=True
                )
            ],
            files=[
                TemplateFile(path="test.txt", content="test")
            ]
        )

        variables = {}  # 필수 변수 누락
        output_dir = tmp_path / "output"

        with pytest.raises(TemplateValidationError, match="변수 검증 실패"):
            engine.render(template, variables, output_dir)

    def test_render_validation_error_wrong_type(self, tmp_path):
        """잘못된 타입 시 검증 에러 테스트"""
        engine = Jinja2TemplateEngine()

        template = Template(
            id="test-template",
            name="Test",
            description="Test",
            category=TemplateCategory.WEB_API,
            variables=[
                TemplateVariable(
                    name="count",
                    description="Count",
                    type=VariableType.INTEGER,
                    required=True
                )
            ],
            files=[
                TemplateFile(path="test.txt", content="{{count}}")
            ]
        )

        variables = {"count": "ten"}  # 문자열이지만 정수 타입 기대
        output_dir = tmp_path / "output"

        with pytest.raises(TemplateValidationError, match="변수 검증 실패"):
            engine.render(template, variables, output_dir)

    def test_render_path_traversal_in_path(self, tmp_path):
        """Path traversal 공격 방지 테스트 (파일 경로)"""
        engine = Jinja2TemplateEngine()

        template = Template(
            id="test-template",
            name="Test",
            description="Test",
            category=TemplateCategory.WEB_API,
            variables=[],
            files=[
                TemplateFile(
                    path="../../../etc/passwd",  # Path traversal 시도
                    content="malicious"
                )
            ]
        )

        variables = {}
        output_dir = tmp_path / "output"

        with pytest.raises(TemplateValidationError, match="보안 위반"):
            engine.render(template, variables, output_dir)

    def test_render_path_traversal_in_variable(self, tmp_path):
        """Path traversal 공격 방지 테스트 (변수 치환)"""
        engine = Jinja2TemplateEngine()

        template = Template(
            id="test-template",
            name="Test",
            description="Test",
            category=TemplateCategory.WEB_API,
            variables=[
                TemplateVariable(
                    name="filename",
                    description="File name",
                    type=VariableType.STRING,
                    required=True
                )
            ],
            files=[
                TemplateFile(
                    path="{{filename}}",
                    content="test"
                )
            ]
        )

        variables = {"filename": "../../../etc/passwd"}  # Path traversal 시도
        output_dir = tmp_path / "output"

        with pytest.raises(TemplateValidationError, match="보안 위반"):
            engine.render(template, variables, output_dir)

    def test_render_absolute_path(self, tmp_path):
        """절대 경로 방지 테스트"""
        engine = Jinja2TemplateEngine()

        template = Template(
            id="test-template",
            name="Test",
            description="Test",
            category=TemplateCategory.WEB_API,
            variables=[],
            files=[
                TemplateFile(
                    path="/etc/passwd",  # 절대 경로
                    content="malicious"
                )
            ]
        )

        variables = {}
        output_dir = tmp_path / "output"

        with pytest.raises(TemplateValidationError, match="보안 위반"):
            engine.render(template, variables, output_dir)

    def test_render_with_encoding(self, tmp_path):
        """UTF-8 인코딩 테스트 (한글 지원)"""
        engine = Jinja2TemplateEngine()

        template = Template(
            id="test-template",
            name="Test",
            description="Test",
            category=TemplateCategory.WEB_API,
            variables=[
                TemplateVariable(
                    name="name",
                    description="이름",
                    type=VariableType.STRING,
                    required=True
                )
            ],
            files=[
                TemplateFile(
                    path="한글파일.txt",
                    content="안녕하세요, {{name}}님!",
                    encoding="utf-8"
                )
            ]
        )

        variables = {"name": "홍길동"}
        output_dir = tmp_path / "output"

        created_files = engine.render(template, variables, output_dir)

        assert len(created_files) == 1
        assert created_files[0].name == "한글파일.txt"
        assert created_files[0].read_text(encoding="utf-8") == "안녕하세요, 홍길동님!"

    def test_render_template_syntax_error(self, tmp_path):
        """템플릿 문법 오류 테스트"""
        engine = Jinja2TemplateEngine()

        template = Template(
            id="test-template",
            name="Test",
            description="Test",
            category=TemplateCategory.WEB_API,
            variables=[],
            files=[
                TemplateFile(
                    path="test.txt",
                    content="{{name"  # 닫는 괄호 누락
                )
            ]
        )

        variables = {}
        output_dir = tmp_path / "output"

        with pytest.raises(TemplateRenderError, match="템플릿 렌더링 실패"):
            engine.render(template, variables, output_dir)

    def test_render_undefined_variable(self, tmp_path):
        """정의되지 않은 변수 사용 테스트"""
        engine = Jinja2TemplateEngine()

        template = Template(
            id="test-template",
            name="Test",
            description="Test",
            category=TemplateCategory.WEB_API,
            variables=[],
            files=[
                TemplateFile(
                    path="test.txt",
                    content="{{undefined_variable}}"  # 정의되지 않은 변수
                )
            ]
        )

        variables = {}
        output_dir = tmp_path / "output"

        # Jinja2는 기본적으로 undefined 변수를 빈 문자열로 처리
        created_files = engine.render(template, variables, output_dir)

        assert len(created_files) == 1
        assert created_files[0].read_text() == ""

    def test_render_creates_output_directory(self, tmp_path):
        """출력 디렉토리 자동 생성 테스트"""
        engine = Jinja2TemplateEngine()

        template = Template(
            id="test-template",
            name="Test",
            description="Test",
            category=TemplateCategory.WEB_API,
            variables=[],
            files=[
                TemplateFile(path="test.txt", content="test")
            ]
        )

        variables = {}
        output_dir = tmp_path / "non_existent_dir" / "output"

        # 디렉토리가 존재하지 않아도 자동으로 생성됨
        created_files = engine.render(template, variables, output_dir)

        assert output_dir.exists()
        assert len(created_files) == 1

    def test_render_variable_in_path_and_content(self, tmp_path):
        """경로와 내용 모두에 변수 사용 테스트"""
        engine = Jinja2TemplateEngine()

        template = Template(
            id="test-template",
            name="Test",
            description="Test",
            category=TemplateCategory.WEB_API,
            variables=[
                TemplateVariable(
                    name="module_name",
                    description="Module name",
                    type=VariableType.STRING,
                    required=True
                ),
                TemplateVariable(
                    name="author",
                    description="Author",
                    type=VariableType.STRING,
                    required=True
                )
            ],
            files=[
                TemplateFile(
                    path="src/{{module_name}}.py",
                    content='"""\n{{module_name}} module\n\nAuthor: {{author}}\n"""'
                )
            ]
        )

        variables = {"module_name": "utils", "author": "John Doe"}
        output_dir = tmp_path / "output"

        created_files = engine.render(template, variables, output_dir)

        assert len(created_files) == 1
        assert created_files[0].name == "utils.py"

        expected_content = '"""\nutils module\n\nAuthor: John Doe\n"""'
        assert created_files[0].read_text() == expected_content

    def test_render_with_list_variable(self, tmp_path):
        """LIST 타입 변수 렌더링 테스트"""
        engine = Jinja2TemplateEngine()

        template = Template(
            id="test-template",
            name="Test",
            description="Test",
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
                    path="schema.py",
                    content="fields = {{fields}}"
                )
            ]
        )

        variables = {"fields": ["id", "name", "email"]}
        output_dir = tmp_path / "output"

        created_files = engine.render(template, variables, output_dir)

        assert len(created_files) == 1
        assert "['id', 'name', 'email']" in created_files[0].read_text()

    def test_render_with_boolean_variable(self, tmp_path):
        """BOOLEAN 타입 변수 렌더링 테스트"""
        engine = Jinja2TemplateEngine()

        template = Template(
            id="test-template",
            name="Test",
            description="Test",
            category=TemplateCategory.WEB_API,
            variables=[
                TemplateVariable(
                    name="enabled",
                    description="Enabled",
                    type=VariableType.BOOLEAN,
                    required=True
                )
            ],
            files=[
                TemplateFile(
                    path="config.py",
                    content="ENABLED = {{enabled}}"
                )
            ]
        )

        variables = {"enabled": True}
        output_dir = tmp_path / "output"

        created_files = engine.render(template, variables, output_dir)

        assert len(created_files) == 1
        assert "ENABLED = True" in created_files[0].read_text()
