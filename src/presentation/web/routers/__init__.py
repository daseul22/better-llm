"""
웹 API 라우터

FastAPI 라우터를 정의합니다.
"""

from src.presentation.web.routers.agents import router as agents_router
from src.presentation.web.routers.health import router as health_router
from src.presentation.web.routers.workflows import router as workflows_router

__all__ = ["agents_router", "health_router", "workflows_router"]
