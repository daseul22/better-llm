"""
내장 템플릿 정의

자주 사용되는 코드 템플릿들을 제공합니다.
"""

from datetime import datetime
from typing import List

from ...domain.models.template import (
    Template,
    TemplateCategory,
    TemplateVariable,
    TemplateFile,
    VariableType
)


def get_builtin_templates() -> List[Template]:
    """
    내장 템플릿 목록 반환

    Returns:
        Template 목록
    """
    return [
        _get_fastapi_crud_template(),
        _get_pytest_template(),
        _get_django_model_template(),
        _get_react_component_template(),
    ]


def _get_fastapi_crud_template() -> Template:
    """FastAPI CRUD 템플릿"""
    return Template(
        id="fastapi-crud",
        name="FastAPI CRUD API",
        description="FastAPI를 사용한 CRUD API 엔드포인트, 스키마, 모델 생성",
        category=TemplateCategory.WEB_API,
        variables=[
            TemplateVariable(
                name="entity_name",
                description="엔티티 이름 (예: user, product)",
                type=VariableType.STRING,
                required=True
            ),
            TemplateVariable(
                name="entity_name_plural",
                description="엔티티 복수형 이름 (예: users, products)",
                type=VariableType.STRING,
                required=True
            ),
            TemplateVariable(
                name="fields",
                description="필드 목록",
                type=VariableType.LIST,
                required=True,
                default=["id: int", "name: str", "created_at: datetime"]
            ),
        ],
        files=[
            TemplateFile(
                path="routes/{{entity_name}}.py",
                content='''"""
{{entity_name_plural}} API 라우터
"""

from fastapi import APIRouter, HTTPException, status
from typing import List

from ..schemas.{{entity_name}} import {{entity_name|capitalize}}Create, {{entity_name|capitalize}}Response
from ..models.{{entity_name}} import {{entity_name|capitalize}}

router = APIRouter(prefix="/{{entity_name_plural}}", tags=["{{entity_name_plural}}"])


@router.get("/", response_model=List[{{entity_name|capitalize}}Response])
async def list_{{entity_name_plural}}():
    """{{entity_name_plural}} 목록 조회"""
    # TODO: 실제 DB 조회 로직 구현
    return []


@router.get("/{id}", response_model={{entity_name|capitalize}}Response)
async def get_{{entity_name}}(id: int):
    """{{entity_name}} 상세 조회"""
    # TODO: 실제 DB 조회 로직 구현
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="{{entity_name|capitalize}} not found")


@router.post("/", response_model={{entity_name|capitalize}}Response, status_code=status.HTTP_201_CREATED)
async def create_{{entity_name}}({{entity_name}}: {{entity_name|capitalize}}Create):
    """{{entity_name}} 생성"""
    # TODO: 실제 DB 저장 로직 구현
    return {{entity_name}}


@router.put("/{id}", response_model={{entity_name|capitalize}}Response)
async def update_{{entity_name}}(id: int, {{entity_name}}: {{entity_name|capitalize}}Create):
    """{{entity_name}} 수정"""
    # TODO: 실제 DB 업데이트 로직 구현
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="{{entity_name|capitalize}} not found")


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_{{entity_name}}(id: int):
    """{{entity_name}} 삭제"""
    # TODO: 실제 DB 삭제 로직 구현
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="{{entity_name|capitalize}} not found")
'''
            ),
            TemplateFile(
                path="schemas/{{entity_name}}.py",
                content='''"""
{{entity_name|capitalize}} Pydantic 스키마
"""

from pydantic import BaseModel
from datetime import datetime


class {{entity_name|capitalize}}Base(BaseModel):
    """{{entity_name|capitalize}} 기본 스키마"""
    name: str


class {{entity_name|capitalize}}Create({{entity_name|capitalize}}Base):
    """{{entity_name|capitalize}} 생성 스키마"""
    pass


class {{entity_name|capitalize}}Response({{entity_name|capitalize}}Base):
    """{{entity_name|capitalize}} 응답 스키마"""
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
'''
            ),
            TemplateFile(
                path="models/{{entity_name}}.py",
                content='''"""
{{entity_name|capitalize}} 데이터베이스 모델
"""

from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime

from ..database import Base


class {{entity_name|capitalize}}(Base):
    """{{entity_name|capitalize}} 모델"""
    __tablename__ = "{{entity_name_plural}}"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
'''
            ),
        ],
        tags=["fastapi", "crud", "api", "rest", "backend"],
        created_at=datetime.now(),
        updated_at=datetime.now()
    )


def _get_pytest_template() -> Template:
    """pytest 테스트 템플릿"""
    return Template(
        id="pytest-test",
        name="pytest Test Suite",
        description="pytest를 사용한 테스트 케이스 생성",
        category=TemplateCategory.TESTING,
        variables=[
            TemplateVariable(
                name="module_name",
                description="테스트할 모듈 이름",
                type=VariableType.STRING,
                required=True
            ),
            TemplateVariable(
                name="test_cases",
                description="테스트 케이스 목록",
                type=VariableType.LIST,
                required=False,
                default=["test_basic_functionality", "test_edge_cases", "test_error_handling"]
            ),
        ],
        files=[
            TemplateFile(
                path="test_{{module_name}}.py",
                content='''"""
{{module_name}} 모듈 테스트
"""

import pytest
from {{module_name}} import *


class Test{{module_name|capitalize}}:
    """{{module_name|capitalize}} 테스트 클래스"""

    def setup_method(self):
        """각 테스트 메서드 실행 전 초기화"""
        pass

    def teardown_method(self):
        """각 테스트 메서드 실행 후 정리"""
        pass

    def test_basic_functionality(self):
        """기본 기능 테스트"""
        # Arrange
        # TODO: 테스트 데이터 준비

        # Act
        # TODO: 테스트 실행

        # Assert
        # TODO: 결과 검증
        assert True

    def test_edge_cases(self):
        """경계 조건 테스트"""
        # TODO: 경계 조건 테스트 구현
        pass

    def test_error_handling(self):
        """에러 처리 테스트"""
        # TODO: 예외 상황 테스트 구현
        with pytest.raises(Exception):
            pass


@pytest.fixture
def sample_data():
    """테스트용 샘플 데이터 픽스처"""
    return {}


def test_with_fixture(sample_data):
    """픽스처를 사용한 테스트"""
    # TODO: 픽스처 활용 테스트 구현
    assert sample_data is not None
'''
            ),
        ],
        tags=["pytest", "testing", "unit-test", "tdd"],
        created_at=datetime.now(),
        updated_at=datetime.now()
    )


def _get_django_model_template() -> Template:
    """Django Model 템플릿"""
    return Template(
        id="django-model",
        name="Django Model",
        description="Django ORM 모델 및 관리자 페이지 생성",
        category=TemplateCategory.DATABASE,
        variables=[
            TemplateVariable(
                name="model_name",
                description="모델 이름 (예: Article, Product)",
                type=VariableType.STRING,
                required=True
            ),
            TemplateVariable(
                name="app_name",
                description="Django 앱 이름",
                type=VariableType.STRING,
                required=True
            ),
        ],
        files=[
            TemplateFile(
                path="{{app_name}}/models/{{model_name|lower}}.py",
                content='''"""
{{model_name}} Django 모델
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class {{model_name}}(models.Model):
    """{{model_name}} 모델"""

    title = models.CharField(_("제목"), max_length=200)
    content = models.TextField(_("내용"))
    created_at = models.DateTimeField(_("생성일시"), auto_now_add=True)
    updated_at = models.DateTimeField(_("수정일시"), auto_now=True)
    is_active = models.BooleanField(_("활성화"), default=True)

    class Meta:
        verbose_name = _("{{model_name}}")
        verbose_name_plural = _("{{model_name}}s")
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
'''
            ),
            TemplateFile(
                path="{{app_name}}/admin.py",
                content='''"""
{{app_name}} 관리자 페이지
"""

from django.contrib import admin
from .models.{{model_name|lower}} import {{model_name}}


@admin.register({{model_name}})
class {{model_name}}Admin(admin.ModelAdmin):
    """{{model_name}} 관리자"""

    list_display = ["title", "is_active", "created_at", "updated_at"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["title", "content"]
    date_hierarchy = "created_at"
    ordering = ["-created_at"]

    fieldsets = (
        (None, {
            "fields": ("title", "content")
        }),
        ("상태", {
            "fields": ("is_active",)
        }),
    )

    readonly_fields = ["created_at", "updated_at"]
'''
            ),
        ],
        tags=["django", "model", "orm", "database", "admin"],
        created_at=datetime.now(),
        updated_at=datetime.now()
    )


def _get_react_component_template() -> Template:
    """React Component 템플릿"""
    return Template(
        id="react-component",
        name="React Functional Component",
        description="React 함수형 컴포넌트 및 스타일 생성",
        category=TemplateCategory.FRONTEND,
        variables=[
            TemplateVariable(
                name="component_name",
                description="컴포넌트 이름 (예: UserProfile, ProductCard)",
                type=VariableType.STRING,
                required=True
            ),
            TemplateVariable(
                name="use_typescript",
                description="TypeScript 사용 여부",
                type=VariableType.BOOLEAN,
                required=False,
                default=True
            ),
        ],
        files=[
            TemplateFile(
                path="components/{{component_name}}/{{component_name}}.tsx",
                content='''/* React {{component_name}} 컴포넌트 */
import React from "react";
import "./{{component_name}}.css";

export interface {{component_name}}Props {
  // TODO: Props 타입 정의
}

export const {{component_name}}: React.FC<{{component_name}}Props> = (props) => {
  // TODO: 컴포넌트 로직 구현

  return (
    <div className="{{component_name|lower}}">
      <h2>{{component_name}}</h2>
      {/* TODO: 컴포넌트 UI 구현 */}
    </div>
  );
};

export default {{component_name}};
'''
            ),
            TemplateFile(
                path="components/{{component_name}}/{{component_name}}.css",
                content='''.{{component_name|lower}} {
  /* 컴포넌트 스타일 */
  padding: 1rem;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
}

.{{component_name|lower}} h2 {
  margin: 0 0 1rem 0;
  font-size: 1.5rem;
  color: #333;
}
'''
            ),
            TemplateFile(
                path="components/{{component_name}}/index.ts",
                content='''export { {{component_name}} } from "./{{component_name}}";
export type { {{component_name}}Props } from "./{{component_name}}";
'''
            ),
        ],
        tags=["react", "component", "frontend", "typescript", "ui"],
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
