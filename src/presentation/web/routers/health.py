"""
Health Check API 라우터

서비스 상태 확인을 위한 엔드포인트를 제공합니다.
"""

from fastapi import APIRouter

from src.presentation.web.schemas.request import HealthCheckResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthCheckResponse)
async def health_check() -> HealthCheckResponse:
    """
    서비스 상태 확인

    Returns:
        HealthCheckResponse: 서비스 상태 정보

    Example:
        GET /health
        Response: {"status": "ok", "message": "Service is running"}
    """
    return HealthCheckResponse(status="ok", message="Service is running")
