"""
Circuit Breaker 모델 정의

Circuit Breaker 패턴의 상태 및 데이터 모델을 정의합니다.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class CircuitState(Enum):
    """Circuit Breaker 상태"""
    CLOSED = "closed"        # 정상 동작
    OPEN = "open"            # 장애 발생, 요청 차단
    HALF_OPEN = "half_open"  # 복구 시도 중


@dataclass
class CircuitBreakerState:
    """
    Circuit Breaker의 현재 상태 정보

    Attributes:
        state: Circuit 상태 (CLOSED, OPEN, HALF_OPEN)
        failure_count: 연속 실패 횟수
        success_count: HALF_OPEN 상태에서의 성공 횟수
        in_flight_requests: 현재 실행 중인 요청 수 (HALF_OPEN 상태에서 동시 실행 제한용)
        last_failure_time: 마지막 실패 시각
        opened_at: Circuit이 OPEN된 시각
    """
    state: CircuitState
    failure_count: int = 0
    success_count: int = 0
    in_flight_requests: int = 0
    last_failure_time: Optional[datetime] = None
    opened_at: Optional[datetime] = None

    def reset(self) -> None:
        """
        카운터 및 타임스탬프를 초기화합니다.

        주의: state 전환은 CircuitBreaker 클래스에서 별도로 관리됩니다.
        """
        self.failure_count = 0
        self.success_count = 0
        self.in_flight_requests = 0
        self.last_failure_time = None
        self.opened_at = None
