"""
템플릿 도메인 모델 단위 테스트

테스트 범위:
- TemplateVariable.validate() 테스트 (string, integer, boolean, list)
- TemplateVariable 직렬화/역직렬화
- Template.validate_variables() 테스트
- Template 직렬화/역직렬화
- Template.from_dict() 예외 처리
- TemplateCategory Enum 테스트
- 예외 클래스 테스트
"""

import pytest
from datetime import datetime
from src.domain.models.template import (
    Template,
    TemplateCategory,
    TemplateVariable,
    TemplateFile,
    VariableType,
    TemplateNotFoundError,
    TemplateValidationError,
    TemplateRenderError
)


class TestTemplateVariable:
    """TemplateVariable 도메인 모델 테스트"""

    def test_validate_string_type(self):
        """STRING 타입 변수 검증 테스트"""
        var = TemplateVariable(
            name="name",
            description="User name",
            type=VariableType.STRING,
            required=True
        )

        # 유효한 값
        assert var.validate("john") is True
        assert var.validate("") is True  # 빈 문자열도 문자열 타입

        # 유효하지 않은 값
        assert var.validate(123) is False
        assert var.validate(True) is False
        assert var.validate([]) is False

    def test_validate_integer_type(self):
        """INTEGER 타입 변수 검증 테스트"""
        var = TemplateVariable(
            name="age",
            description="User age",
            type=VariableType.INTEGER,
            required=True
        )

        # 유효한 값
        assert var.validate(25) is True
        assert var.validate(0) is True
        assert var.validate(-10) is True

        # 유효하지 않은 값
        assert var.validate("25") is False
        assert var.validate(25.5) is False
        # Note: Python에서 bool은 int의 서브클래스이므로 isinstance(True, int)는 True를 반환
        # 따라서 boolean 값도 INTEGER 타입 검증을 통과함 (이는 Python의 특성)

    def test_validate_boolean_type(self):
        """BOOLEAN 타입 변수 검증 테스트"""
        var = TemplateVariable(
            name="enabled",
            description="Feature enabled",
            type=VariableType.BOOLEAN,
            required=True
        )

        # 유효한 값
        assert var.validate(True) is True
        assert var.validate(False) is True

        # 유효하지 않은 값
        assert var.validate(1) is False
        assert var.validate(0) is False
        assert var.validate("true") is False

    def test_validate_list_type(self):
        """LIST 타입 변수 검증 테스트"""
        var = TemplateVariable(
            name="fields",
            description="Field list",
            type=VariableType.LIST,
            required=True
        )

        # 유효한 값
        assert var.validate([]) is True
        assert var.validate(["a", "b"]) is True
        assert var.validate([1, 2, 3]) is True

        # 유효하지 않은 값
        assert var.validate("a,b,c") is False
        assert var.validate(123) is False
        assert var.validate({}) is False

    def test_validate_required_field(self):
        """필수 필드 검증 테스트"""
        var = TemplateVariable(
            name="required_field",
            description="Required field",
            type=VariableType.STRING,
            required=True
        )

        # None은 필수 필드에서 유효하지 않음
        assert var.validate(None) is False

    def test_validate_optional_field(self):
        """선택적 필드 검증 테스트"""
        var = TemplateVariable(
            name="optional_field",
            description="Optional field",
            type=VariableType.STRING,
            required=False
        )

        # None은 선택적 필드에서 유효함
        assert var.validate(None) is True
        assert var.validate("value") is True

    def test_to_dict(self):
        """TemplateVariable 직렬화 테스트"""
        var = TemplateVariable(
            name="field_name",
            description="Field description",
            type=VariableType.STRING,
            required=True,
            default="default_value"
        )

        data = var.to_dict()

        assert data["name"] == "field_name"
        assert data["description"] == "Field description"
        assert data["type"] == "string"
        assert data["required"] is True
        assert data["default"] == "default_value"

    def test_from_dict(self):
        """딕셔너리에서 TemplateVariable 생성 테스트"""
        data = {
            "name": "test_var",
            "description": "Test variable",
            "type": "integer",
            "required": False,
            "default": 42
        }

        var = TemplateVariable.from_dict(data)

        assert var.name == "test_var"
        assert var.description == "Test variable"
        assert var.type == VariableType.INTEGER
        assert var.required is False
        assert var.default == 42

    def test_from_dict_with_defaults(self):
        """기본값 적용 테스트"""
        data = {
            "name": "minimal_var",
            "description": "Minimal variable"
        }

        var = TemplateVariable.from_dict(data)

        assert var.name == "minimal_var"
        assert var.description == "Minimal variable"
        assert var.type == VariableType.STRING  # 기본값
        assert var.required is True  # 기본값
        assert var.default is None  # 기본값


class TestTemplateFile:
    """TemplateFile 도메인 모델 테스트"""

    def test_to_dict(self):
        """TemplateFile 직렬화 테스트"""
        file = TemplateFile(
            path="src/main.py",
            content="print('Hello')",
            encoding="utf-8"
        )

        data = file.to_dict()

        assert data["path"] == "src/main.py"
        assert data["content"] == "print('Hello')"
        assert data["encoding"] == "utf-8"

    def test_from_dict(self):
        """딕셔너리에서 TemplateFile 생성 테스트"""
        data = {
            "path": "test/test.py",
            "content": "def test(): pass",
            "encoding": "utf-8"
        }

        file = TemplateFile.from_dict(data)

        assert file.path == "test/test.py"
        assert file.content == "def test(): pass"
        assert file.encoding == "utf-8"

    def test_default_encoding(self):
        """기본 인코딩 테스트"""
        data = {
            "path": "file.txt",
            "content": "content"
        }

        file = TemplateFile.from_dict(data)

        assert file.encoding == "utf-8"  # 기본값


class TestTemplate:
    """Template 도메인 모델 테스트"""

    def test_validate_variables_success(self):
        """변수 검증 성공 테스트"""
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
                    name="count",
                    description="Count",
                    type=VariableType.INTEGER,
                    required=False
                )
            ]
        )

        values = {"name": "test", "count": 5}
        errors = template.validate_variables(values)

        assert errors == []

    def test_validate_variables_missing_required(self):
        """필수 변수 누락 시 에러 테스트"""
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

        values = {}  # 필수 변수 누락
        errors = template.validate_variables(values)

        assert len(errors) == 1
        assert "required_field" in errors[0]
        assert "missing" in errors[0].lower()

    def test_validate_variables_invalid_type(self):
        """잘못된 타입 시 에러 테스트"""
        template = Template(
            id="test-template",
            name="Test Template",
            description="Test",
            category=TemplateCategory.WEB_API,
            variables=[
                TemplateVariable(
                    name="age",
                    description="Age",
                    type=VariableType.INTEGER,
                    required=True
                )
            ]
        )

        values = {"age": "twenty"}  # 문자열이지만 정수 타입 기대
        errors = template.validate_variables(values)

        assert len(errors) == 1
        assert "age" in errors[0]
        assert "invalid type" in errors[0].lower()

    def test_validate_variables_optional_missing(self):
        """선택적 변수 누락은 에러가 아님"""
        template = Template(
            id="test-template",
            name="Test Template",
            description="Test",
            category=TemplateCategory.WEB_API,
            variables=[
                TemplateVariable(
                    name="optional_field",
                    description="Optional",
                    type=VariableType.STRING,
                    required=False
                )
            ]
        )

        values = {}  # 선택적 변수 누락
        errors = template.validate_variables(values)

        assert errors == []

    def test_to_dict(self):
        """Template 직렬화 테스트"""
        created_at = datetime(2024, 1, 1, 12, 0, 0)
        updated_at = datetime(2024, 1, 2, 13, 0, 0)

        template = Template(
            id="test-id",
            name="Test Template",
            description="Test Description",
            category=TemplateCategory.TESTING,
            variables=[
                TemplateVariable(
                    name="var1",
                    description="Variable 1",
                    type=VariableType.STRING
                )
            ],
            files=[
                TemplateFile(
                    path="test.py",
                    content="print('test')"
                )
            ],
            tags=["test", "unit"],
            created_at=created_at,
            updated_at=updated_at
        )

        data = template.to_dict()

        assert data["id"] == "test-id"
        assert data["name"] == "Test Template"
        assert data["description"] == "Test Description"
        assert data["category"] == "testing"
        assert len(data["variables"]) == 1
        assert data["variables"][0]["name"] == "var1"
        assert len(data["files"]) == 1
        assert data["files"][0]["path"] == "test.py"
        assert data["tags"] == ["test", "unit"]
        assert data["created_at"] == "2024-01-01T12:00:00"
        assert data["updated_at"] == "2024-01-02T13:00:00"

    def test_from_dict_success(self):
        """딕셔너리에서 Template 생성 테스트"""
        data = {
            "id": "from-dict-id",
            "name": "From Dict Template",
            "description": "Created from dict",
            "category": "web_api",
            "variables": [
                {
                    "name": "var1",
                    "description": "Variable 1",
                    "type": "string",
                    "required": True
                }
            ],
            "files": [
                {
                    "path": "main.py",
                    "content": "# Main file"
                }
            ],
            "tags": ["api", "rest"],
            "created_at": "2024-01-15T10:00:00",
            "updated_at": "2024-01-15T10:00:00"
        }

        template = Template.from_dict(data)

        assert template.id == "from-dict-id"
        assert template.name == "From Dict Template"
        assert template.description == "Created from dict"
        assert template.category == TemplateCategory.WEB_API
        assert len(template.variables) == 1
        assert template.variables[0].name == "var1"
        assert len(template.files) == 1
        assert template.files[0].path == "main.py"
        assert template.tags == ["api", "rest"]
        assert template.created_at == datetime(2024, 1, 15, 10, 0, 0)
        assert template.updated_at == datetime(2024, 1, 15, 10, 0, 0)

    def test_from_dict_with_defaults(self):
        """선택적 필드 기본값 테스트"""
        data = {
            "id": "minimal-id",
            "name": "Minimal Template",
            "description": "Minimal",
            "category": "frontend"
        }

        template = Template.from_dict(data)

        assert template.id == "minimal-id"
        assert template.variables == []
        assert template.files == []
        assert template.tags == []
        assert template.created_at is not None
        assert template.updated_at is not None

    def test_from_dict_missing_required_field(self):
        """필수 필드 누락 시 예외 발생 테스트"""
        data = {
            "id": "test-id",
            "name": "Test",
            # description 누락
            "category": "testing"
        }

        with pytest.raises(ValueError, match="필수 필드가 누락"):
            Template.from_dict(data)

    def test_from_dict_invalid_category(self):
        """잘못된 카테고리 시 예외 발생 테스트"""
        data = {
            "id": "test-id",
            "name": "Test",
            "description": "Test",
            "category": "invalid_category"
        }

        with pytest.raises(ValueError, match="템플릿 데이터 형식 오류"):
            Template.from_dict(data)

    def test_from_dict_invalid_date_format(self):
        """잘못된 날짜 형식 시 예외 발생 테스트"""
        data = {
            "id": "test-id",
            "name": "Test",
            "description": "Test",
            "category": "testing",
            "created_at": "invalid-date"
        }

        with pytest.raises(ValueError, match="템플릿 데이터 형식 오류"):
            Template.from_dict(data)


class TestTemplateCategory:
    """TemplateCategory Enum 테스트"""

    def test_category_values(self):
        """카테고리 값 테스트"""
        assert TemplateCategory.WEB_API.value == "web_api"
        assert TemplateCategory.TESTING.value == "testing"
        assert TemplateCategory.DATABASE.value == "database"
        assert TemplateCategory.FRONTEND.value == "frontend"
        assert TemplateCategory.CLI.value == "cli"
        assert TemplateCategory.DATA_SCIENCE.value == "data_science"
        assert TemplateCategory.DEVOPS.value == "devops"
        assert TemplateCategory.CUSTOM.value == "custom"

    def test_category_from_string(self):
        """문자열에서 카테고리 생성 테스트"""
        category = TemplateCategory("web_api")
        assert category == TemplateCategory.WEB_API

        category = TemplateCategory("testing")
        assert category == TemplateCategory.TESTING

    def test_category_invalid_value(self):
        """잘못된 값으로 생성 시 예외 발생"""
        with pytest.raises(ValueError):
            TemplateCategory("invalid_category")


class TestTemplateExceptions:
    """템플릿 예외 클래스 테스트"""

    def test_template_not_found_error(self):
        """TemplateNotFoundError 테스트"""
        with pytest.raises(TemplateNotFoundError, match="not found"):
            raise TemplateNotFoundError("Template not found")

    def test_template_validation_error(self):
        """TemplateValidationError 테스트"""
        with pytest.raises(TemplateValidationError, match="validation failed"):
            raise TemplateValidationError("Template validation failed")

    def test_template_render_error(self):
        """TemplateRenderError 테스트"""
        with pytest.raises(TemplateRenderError, match="render failed"):
            raise TemplateRenderError("Template render failed")

    def test_exception_inheritance(self):
        """예외 클래스 상속 테스트"""
        assert issubclass(TemplateNotFoundError, Exception)
        assert issubclass(TemplateValidationError, Exception)
        assert issubclass(TemplateRenderError, Exception)
