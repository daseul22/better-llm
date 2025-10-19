"""
Domain Layer Ports

Domain Layer의 인터페이스 정의 (의존성 역전 원칙)
"""

from .metrics_repository import IMetricsRepository

__all__ = ["IMetricsRepository"]
