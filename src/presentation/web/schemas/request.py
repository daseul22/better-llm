"""
웹 API 요청/응답 스키마 정의

이 모듈은 FastAPI 엔드포인트에서 사용하는 Pydantic 모델을 정의합니다.
"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator


class AgentExecuteRequest(BaseModel):
    """Worker Agent 실행 요청 스키마"""

    agent_name: str = Field(
        ...,
        description="실행할 Worker Agent 이름 (예: planner, coder, reviewer)",
        min_length=1,
        max_length=50,
    )
    task_description: str = Field(
        ...,
        description="Agent에게 전달할 작업 설명",
        min_length=1,
        max_length=5000,  # 프롬프트 인젝션 방어
    )
    session_id: Optional[str] = Field(
        None,
        description="세션 ID (선택적, 미제공 시 자동 생성)",
        min_length=1,
        max_length=100,
    )

    @field_validator("agent_name")
    @classmethod
    def validate_agent_name(cls, v: str) -> str:
        """Agent 이름 검증 (알파벳, 숫자, 언더스코어만 허용)"""
        if not v.replace("_", "").isalnum():
            raise ValueError(
                "Agent 이름은 알파벳, 숫자, 언더스코어만 포함해야 합니다"
            )
        return v.lower()

    @field_validator("task_description")
    @classmethod
    def validate_task_description(cls, v: str) -> str:
        """작업 설명 검증 (공백만 있는 경우 거부)"""
        if not v.strip():
            raise ValueError("작업 설명은 비어있을 수 없습니다")
        return v.strip()


class AgentListResponse(BaseModel):
    """사용 가능한 Agent 목록 응답 스키마"""

    agents: list[dict[str, str]] = Field(
        ...,
        description="Agent 목록 (name, role, description 포함)",
    )


class HealthCheckResponse(BaseModel):
    """Health check 응답 스키마"""

    status: str = Field(..., description="서비스 상태 (ok/error)")
    message: str = Field(..., description="상태 메시지")


class ErrorResponse(BaseModel):
    """에러 응답 스키마"""

    error: str = Field(..., description="에러 메시지")
    detail: Optional[str] = Field(None, description="상세 에러 정보")
