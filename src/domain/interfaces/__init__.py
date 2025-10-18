"""
Domain 인터페이스 패키지

Use Case 인터페이스, Circuit Breaker, Retry Policy 등을 포함합니다.
"""

from .circuit_breaker import ICircuitBreaker
from .retry_policy import IRetryPolicy

__all__ = [
    "ICircuitBreaker",
    "IRetryPolicy",
]
