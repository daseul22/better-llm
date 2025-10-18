# Circuit Breaker 및 에러 처리 개선

이 문서는 better-llm 프로젝트에 구현된 Circuit Breaker 패턴, Retry 메커니즘, Timeout 관리에 대한 설명입니다.

## 개요

분산 시스템에서 외부 서비스(Claude API 등)와의 통신은 실패할 수 있습니다. 이러한 실패를 효과적으로 처리하기 위해 다음 세 가지 탄력성(Resilience) 메커니즘을 구현했습니다:

1. **Circuit Breaker**: 연속 실패 시 요청 차단 및 자동 복구
2. **Retry Policy**: 일시적 오류에 대한 재시도
3. **Timeout Management**: Worker 실행 시간 제한

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      UseCaseFactory                         │
│  - Circuit Breaker 초기화 (Worker별)                        │
│  - Retry Policy 생성                                        │
│  - Timeout 설정                                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   BaseWorkerUseCase                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  execute()                                           │   │
│  │    1. Validation                                     │   │
│  │    2. Circuit Breaker Check                          │   │
│  │    3. Retry with Exponential Backoff                 │   │
│  │    4. Worker Execution (with Timeout)                │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  WorkerAgentAdapter                         │
│  - asyncio.timeout() 적용                                   │
│  - TimeoutError → WorkerTimeoutError 변환                   │
└─────────────────────────────────────────────────────────────┘
```

## Circuit Breaker 패턴

### 상태 전이도

```
       failure_count >= threshold
CLOSED ────────────────────────────> OPEN
  ↑                                    │
  │                                    │ timeout_seconds 경과
  │                                    ▼
  │                               HALF_OPEN
  └──── success_count >= threshold ────┘
           (또는 실패 시 OPEN으로 복귀)
```

### 상태 설명

- **CLOSED**: 정상 동작 상태. 모든 요청을 허용합니다.
- **OPEN**: 장애 감지 상태. 모든 요청을 차단하고 `CircuitOpenError`를 발생시킵니다.
- **HALF_OPEN**: 복구 시도 상태. 제한된 요청을 허용하여 복구를 확인합니다.

### 설정

`config/system_config.json`:

```json
{
  "resilience": {
    "circuit_breaker": {
      "failure_threshold": 5,      // OPEN으로 전환하기 위한 연속 실패 횟수
      "success_threshold": 2,      // HALF_OPEN에서 CLOSED로 전환하기 위한 성공 횟수
      "timeout_seconds": 60,       // OPEN 상태 유지 시간
      "enable_per_worker": true    // Worker별 Circuit Breaker 활성화
    }
  }
}
```

### 사용 예제

Circuit Breaker는 자동으로 적용됩니다. Worker 호출 시 상태를 확인하여 요청을 제어합니다:

```python
# Circuit이 OPEN 상태일 때
try:
    result = await planner_use_case.execute(task)
except CircuitOpenError as e:
    print(f"Circuit이 열려있습니다: {e}")
    # 대체 로직 수행 또는 사용자에게 알림
```

## Retry Policy (Exponential Backoff)

### 동작 방식

1. 재시도 가능한 예외 발생 시 자동으로 재시도
2. 재시도 간격은 지수적으로 증가 (1초 → 2초 → 4초 → ...)
3. Jitter를 추가하여 Thundering Herd 문제 방지

### 재시도 가능한 예외

- `WorkerTimeoutError`: Worker 실행 타임아웃
- `RetryableError`: 재시도 가능한 일반 예외

**재시도 불가능한 예외**:
- `ValidationError`: 입력 검증 실패
- `PreconditionFailedError`: 사전 조건 미충족
- `CircuitOpenError`: Circuit Breaker가 OPEN 상태

### 설정

`config/system_config.json`:

```json
{
  "performance": {
    "worker_retry_enabled": true,
    "worker_retry_max_attempts": 3,
    "worker_retry_base_delay": 1.0,
    "worker_retry_max_delay": 30.0,
    "worker_retry_jitter": 0.1,
    "worker_retry_exponential": true
  }
}
```

### 재시도 간격 계산

```
delay = min(base_delay * 2^(attempt-1), max_delay)
jitter = delay * jitter_ratio * random()
final_delay = delay + jitter
```

**예시** (base_delay=1.0, max_delay=30.0, jitter=0.1):
- 1차 재시도: ~1.0초 (1.0 + 0.1*random)
- 2차 재시도: ~2.0초 (2.0 + 0.2*random)
- 3차 재시도: ~4.0초 (4.0 + 0.4*random)

## Timeout 관리

### Worker별 Timeout

각 Worker는 실행 시간 제한을 가집니다. 제한 시간 초과 시 `WorkerTimeoutError`가 발생합니다.

### 설정

`config/system_config.json`:

```json
{
  "timeouts": {
    "default_worker_timeout": 300,  // 기본 타임아웃: 5분
    "max_worker_timeout": 1800      // 최대 타임아웃: 30분
  }
}
```

### Python 버전 호환성

- **Python 3.11+**: `asyncio.timeout()` 사용
- **Python 3.10 이하**: `async_timeout` 라이브러리 필요

Python 3.10 환경에서는 다음 패키지를 설치하세요:

```bash
pip install async-timeout
```

### 사용 예제

```python
# Timeout은 자동으로 적용됩니다
try:
    result = await coder_use_case.execute(task)
except WorkerTimeoutError as e:
    print(f"Worker 타임아웃: {e.worker_name}, {e.timeout}초")
```

## 통합 예제

### 정상 실행

```python
from application.use_cases import UseCaseFactory

# Factory 초기화 (Circuit Breaker, Retry Policy 자동 생성)
factory = UseCaseFactory(worker_client_factory=create_worker_client)

# Use Case 생성 (탄력성 메커니즘 주입됨)
planner = factory.create_planner_use_case()

# 실행 (Circuit Breaker + Retry + Timeout 적용)
task = Task(agent_name="planner", description="새로운 기능 계획")
result = await planner.execute(task)
```

### 에러 처리

```python
from domain.exceptions import (
    CircuitOpenError,
    WorkerTimeoutError,
    WorkerExecutionError
)

try:
    result = await planner.execute(task)
except CircuitOpenError:
    # Circuit이 열려있음 - 잠시 후 재시도 필요
    print("시스템이 일시적으로 과부하 상태입니다. 잠시 후 다시 시도하세요.")
except WorkerTimeoutError as e:
    # Timeout 발생
    print(f"작업이 {e.timeout}초를 초과했습니다.")
except WorkerExecutionError as e:
    # 기타 Worker 실행 오류
    print(f"Worker 실행 실패: {e}")
```

## 로깅

각 메커니즘은 상세한 로그를 남깁니다:

### Circuit Breaker 로그

```
[CircuitBreaker:planner] 실패 감지 (3/5): TimeoutError
[CircuitBreaker:planner] CLOSED -> OPEN (장애 감지, 60초간 차단)
[CircuitBreaker:planner] OPEN -> HALF_OPEN (복구 시도)
[CircuitBreaker:planner] HALF_OPEN 성공 (1/2)
[CircuitBreaker:planner] HALF_OPEN -> CLOSED (복구 완료)
```

### Retry Policy 로그

```
[RetryPolicy] 재시도 대기 (시도 1/3, 1.05초 후): TimeoutError
[RetryPolicy] 재시도 대기 (시도 2/3, 2.18초 후): TimeoutError
[RetryPolicy] ✅ 재시도 성공 (시도 3/3)
```

### Timeout 로그

```
[planner] ❌ 작업 실행 실패: Worker 'planner' 실행 타임아웃 (300초)
```

## 모니터링

Circuit Breaker 상태는 실시간으로 조회할 수 있습니다:

```python
factory = UseCaseFactory(...)

# Circuit Breaker 상태 조회
planner_cb = factory._circuit_breakers.get("planner")
if planner_cb:
    state = planner_cb.state
    print(f"State: {state.state.value}")
    print(f"Failure Count: {state.failure_count}")
    print(f"Last Failure: {state.last_failure_time}")
```

## 테스트

### Circuit Breaker 테스트

```python
import pytest
from application.resilience import CircuitBreaker
from domain.exceptions import CircuitOpenError

@pytest.mark.asyncio
async def test_circuit_breaker_opens_on_failures():
    cb = CircuitBreaker(name="test", failure_threshold=3, timeout_seconds=1)

    # 3번 실패
    for _ in range(3):
        try:
            await cb.call(failing_function)
        except Exception:
            pass

    # Circuit이 OPEN 상태여야 함
    with pytest.raises(CircuitOpenError):
        await cb.call(succeeding_function)
```

### Retry Policy 테스트

```python
from application.resilience import ExponentialBackoffRetryPolicy

@pytest.mark.asyncio
async def test_retry_policy_retries_on_retryable_errors():
    policy = ExponentialBackoffRetryPolicy(max_attempts=3)

    call_count = 0
    async def flaky_function():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise WorkerTimeoutError("test", message="timeout")
        return "success"

    result = await policy.execute(flaky_function)
    assert result == "success"
    assert call_count == 3
```

## 성능 고려사항

### Circuit Breaker

- **메모리**: Worker당 ~200 bytes (상태 정보)
- **CPU**: 거의 영향 없음 (Lock 사용, 비동기 안전)

### Retry Policy

- **지연 시간**: 재시도 시 지연 발생 (최대 max_delay)
- **리소스**: 재시도 횟수만큼 추가 API 호출

### Timeout

- **메모리**: Context Manager 오버헤드 (~100 bytes)
- **CPU**: 타이머 관리 오버헤드 (무시 가능)

## 권장 설정

### 개발 환경

```json
{
  "resilience": {
    "circuit_breaker": {
      "failure_threshold": 3,
      "success_threshold": 1,
      "timeout_seconds": 30
    }
  },
  "performance": {
    "worker_retry_max_attempts": 2,
    "worker_retry_base_delay": 0.5
  },
  "timeouts": {
    "default_worker_timeout": 120
  }
}
```

### 프로덕션 환경

```json
{
  "resilience": {
    "circuit_breaker": {
      "failure_threshold": 5,
      "success_threshold": 2,
      "timeout_seconds": 60
    }
  },
  "performance": {
    "worker_retry_max_attempts": 3,
    "worker_retry_base_delay": 1.0,
    "worker_retry_max_delay": 30.0
  },
  "timeouts": {
    "default_worker_timeout": 300
  }
}
```

## 문제 해결

### Circuit이 계속 OPEN 상태

**원인**: Worker가 반복적으로 실패
**해결**:
1. Worker 로그 확인
2. Claude API 상태 확인
3. Timeout 설정 증가
4. Circuit Breaker threshold 조정

### 재시도가 너무 많음

**원인**: Retry Policy가 너무 공격적
**해결**:
1. `worker_retry_max_attempts` 감소
2. `worker_retry_base_delay` 증가
3. 특정 예외를 재시도 불가능으로 설정

### Timeout이 너무 짧음

**원인**: Worker 작업이 복잡함
**해결**:
1. `default_worker_timeout` 증가
2. Worker별 timeout 개별 설정

## 참고 자료

- [Circuit Breaker Pattern - Martin Fowler](https://martinfowler.com/bliki/CircuitBreaker.html)
- [Exponential Backoff - AWS Architecture Blog](https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/)
- [asyncio.timeout() - Python Docs](https://docs.python.org/3/library/asyncio-task.html#asyncio.timeout)
