"""
템플릿 도메인 모델

Template: 코드 템플릿
TemplateCategory: 템플릿 카테고리 (Enum)
TemplateVariable: 템플릿 변수
TemplateFile: 템플릿 파일
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum


class TemplateCategory(str, Enum):
    """템플릿 카테고리"""
    WEB_API = "web_api"
    TESTING = "testing"
    DATABASE = "database"
    FRONTEND = "frontend"
    CLI = "cli"
    DATA_SCIENCE = "data_science"
    DEVOPS = "devops"
    CUSTOM = "custom"


class VariableType(str, Enum):
    """템플릿 변수 타입"""
    STRING = "string"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    LIST = "list"


@dataclass
class TemplateVariable:
    """
    템플릿 변수

    Attributes:
        name: 변수 이름
        description: 변수 설명
        type: 변수 타입
        required: 필수 여부
        default: 기본값
    """
    name: str
    description: str
    type: VariableType = VariableType.STRING
    required: bool = True
    default: Optional[Any] = None

    def validate(self, value: Any) -> bool:
        """
        변수 값 유효성 검증

        Args:
            value: 검증할 값

        Returns:
            bool: 유효성 여부
        """
        if self.required and value is None:
            return False

        if value is None:
            return True

        if self.type == VariableType.STRING:
            return isinstance(value, str)
        elif self.type == VariableType.INTEGER:
            return isinstance(value, int)
        elif self.type == VariableType.BOOLEAN:
            return isinstance(value, bool)
        elif self.type == VariableType.LIST:
            return isinstance(value, list)

        return False

    def to_dict(self) -> Dict[str, Any]:
        """JSON 직렬화용 딕셔너리 변환"""
        return {
            "name": self.name,
            "description": self.description,
            "type": self.type.value,
            "required": self.required,
            "default": self.default
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TemplateVariable":
        """
        딕셔너리에서 객체 생성

        Args:
            data: 템플릿 변수 딕셔너리

        Returns:
            TemplateVariable 객체
        """
        return cls(
            name=data["name"],
            description=data["description"],
            type=VariableType(data.get("type", "string")),
            required=data.get("required", True),
            default=data.get("default")
        )


@dataclass
class TemplateFile:
    """
    템플릿 파일

    Attributes:
        path: 상대 파일 경로 (템플릿 변수 포함 가능)
        content: 파일 내용 템플릿
        encoding: 파일 인코딩
    """
    path: str
    content: str
    encoding: str = "utf-8"

    def to_dict(self) -> Dict[str, Any]:
        """JSON 직렬화용 딕셔너리 변환"""
        return {
            "path": self.path,
            "content": self.content,
            "encoding": self.encoding
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TemplateFile":
        """
        딕셔너리에서 객체 생성

        Args:
            data: 템플릿 파일 딕셔너리

        Returns:
            TemplateFile 객체
        """
        return cls(
            path=data["path"],
            content=data["content"],
            encoding=data.get("encoding", "utf-8")
        )


@dataclass
class Template:
    """
    코드 템플릿 도메인 모델

    Attributes:
        id: 템플릿 고유 ID
        name: 템플릿 이름
        description: 템플릿 설명
        category: 템플릿 카테고리
        variables: 템플릿 변수 목록
        files: 템플릿 파일 목록
        tags: 검색 태그 목록
        created_at: 생성 시각
        updated_at: 수정 시각
    """
    id: str
    name: str
    description: str
    category: TemplateCategory
    variables: List[TemplateVariable] = field(default_factory=list)
    files: List[TemplateFile] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def validate_variables(self, values: Dict[str, Any]) -> List[str]:
        """
        변수 값들의 유효성 검증

        Args:
            values: 변수명-값 딕셔너리

        Returns:
            List[str]: 에러 메시지 목록 (빈 리스트면 유효)
        """
        errors = []

        for var in self.variables:
            value = values.get(var.name)

            # 필수 변수 체크
            if var.required and value is None:
                errors.append(f"Required variable '{var.name}' is missing")
                continue

            # 타입 체크
            if value is not None and not var.validate(value):
                errors.append(
                    f"Variable '{var.name}' has invalid type. "
                    f"Expected {var.type.value}, got {type(value).__name__}"
                )

        return errors

    def to_dict(self) -> Dict[str, Any]:
        """JSON 직렬화용 딕셔너리 변환"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "variables": [v.to_dict() for v in self.variables],
            "files": [f.to_dict() for f in self.files],
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Template":
        """
        딕셔너리에서 객체 생성

        Args:
            data: 템플릿 딕셔너리

        Returns:
            Template 객체

        Raises:
            ValueError: 필수 필드가 누락되었거나 형식이 잘못된 경우
        """
        try:
            return cls(
                id=data["id"],
                name=data["name"],
                description=data["description"],
                category=TemplateCategory(data["category"]),
                variables=[
                    TemplateVariable.from_dict(v) for v in data.get("variables", [])
                ],
                files=[
                    TemplateFile.from_dict(f) for f in data.get("files", [])
                ],
                tags=data.get("tags", []),
                created_at=datetime.fromisoformat(data.get(
                    "created_at", datetime.now().isoformat()
                )),
                updated_at=datetime.fromisoformat(data.get(
                    "updated_at", datetime.now().isoformat()
                ))
            )
        except KeyError as e:
            raise ValueError(f"필수 필드가 누락되었습니다: {e}")
        except (ValueError, TypeError) as e:
            raise ValueError(f"템플릿 데이터 형식 오류: {e}")


class TemplateNotFoundError(Exception):
    """템플릿을 찾을 수 없을 때 발생하는 예외"""
    pass


class TemplateValidationError(Exception):
    """템플릿 검증 실패 시 발생하는 예외"""
    pass


class TemplateRenderError(Exception):
    """템플릿 렌더링 실패 시 발생하는 예외"""
    pass
