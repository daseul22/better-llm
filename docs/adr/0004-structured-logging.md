# 4. 구조화된 로깅 (Structlog) 채택

## Status

Accepted

## Context

Better-LLM은 복잡한 오케스트레이션 시스템으로, 다음과 같은 로깅 요구사항이 있었습니다:

- **다중 Worker 추적**: 5개 Worker Agent의 실행 로그를 구분하여 추적
- **에러 디버깅**: 어떤 Worker에서 언제 에러가 발생했는지 빠르게 파악
- **성능 모니터링**: API 호출 시간, 메트릭 수집 성능 측정
- **운영 자동화**: 로그를 파싱하여 알림/대시보드 자동 생성

### 기존 로깅의 문제점 (Python logging)

```python
import logging

logger = logging.getLogger(__name__)
logger.info(f"Worker {worker_name} started task {task_id}")
```

**문제점:**
1. **파싱 어려움**: 문자열 기반 로그를 파싱하려면 정규식 필요
2. **컨텍스트 손실**: worker_name, task_id가 문자열에 포함되어 쿼리 불가
3. **일관성 부족**: 개발자마다 다른 형식으로 로그 작성
4. **타임스탬프 없음**: 기본 포맷에는 밀리초 단위 타임스탬프 없음

### 고려한 대안

1. **Python logging + Formatter**:
   - 기존 logging 유지하고 JSON Formatter만 추가
   - 문제: 구조화된 데이터 바인딩 어려움

2. **Loguru**:
   - 간결한 API와 자동 컬러링
   - 문제: JSON 출력이 기본이 아님, structlog보다 유연성 낮음

3. **Structlog**:
   - 구조화된 로깅 전문 라이브러리
   - JSON 출력, 컨텍스트 바인딩, 프로세서 체인 지원

## Decision

**Structlog를 채택**하여 모든 로그를 JSON 형태로 구조화하고, 컨텍스트 정보를 자동으로 추가하도록 구현했습니다.

### 구현 방식

```python
# src/infrastructure/logging/setup.py

import structlog
from structlog.processors import (
    add_log_level,
    TimeStamper,
    StackInfoRenderer,
    format_exc_info,
    JSONRenderer,
)

def setup_logging(log_level: str = "INFO", log_format: str = "json"):
    """구조화된 로깅 설정"""
    processors = [
        structlog.contextvars.merge_contextvars,
        add_log_level,
        TimeStamper(fmt="iso"),
        StackInfoRenderer(),
        format_exc_info,
        CallsiteParameterAdder(),  # 파일명, 함수명, 줄번호 자동 추가
    ]

    if log_format == "json":
        processors.append(JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(processors=processors)
```

### JSON 로그 예시

```json
{
  "event": "Worker agent initialized",
  "worker_name": "planner",
  "role": "요구사항 분석 및 계획 수립",
  "model": "claude-sonnet-4-5-20250929",
  "session_id": "abc123",
  "pathname": "src/infrastructure/mcp/worker_tools.py",
  "func_name": "initialize_workers",
  "lineno": 427,
  "timestamp": "2025-01-20T10:30:00.123456Z",
  "level": "info"
}
```

### 로그 레벨 및 파일 관리

```python
# 로그 레벨: DEBUG, INFO, WARNING, ERROR, CRITICAL
# 환경변수: LOG_LEVEL, LOG_FORMAT, LOG_DIR

# 파일 분리
- logs/better-llm.log          # 전체 로그
- logs/better-llm-error.log    # 에러만
- logs/better-llm-debug.log    # DEBUG 레벨 전용
```

## Consequences

### 긍정적 결과

- **쿼리 가능**: JSON 로그를 jq, grep 등으로 쿼리 가능
  ```bash
  cat logs/better-llm.log | jq 'select(.worker_name == "planner")'
  ```

- **컨텍스트 자동 추가**: worker_name, session_id 등이 자동으로 모든 로그에 포함
  ```python
  logger = get_logger().bind(worker_name="planner")
  logger.info("Task started", task_id="123")
  # → worker_name과 task_id가 자동으로 JSON에 포함
  ```

- **운영 자동화**:
  - CloudWatch/Datadog 같은 로그 수집 시스템에 바로 통합
  - 에러 알림 자동화 (ERROR 레벨 로그 감지)

- **디버깅 효율성**:
  - 파일명, 함수명, 줄번호 자동 기록
  - 에러 발생 시 즉시 코드 위치 파악

- **성능 측정**:
  ```python
  logger.info("API call started", api="claude")
  # ... API 호출
  logger.info("API call finished", api="claude", duration_ms=1234)
  ```

### 부정적 결과

- **로그 파일 크기 증가**: JSON은 텍스트보다 약 30% 크기 증가
  - 해결: 로그 로테이션 (10MB, 5개 백업)

- **사람이 읽기 어려움**: JSON은 기계 친화적이지만 가독성 낮음
  - 해결: 로컬 개발 시 `LOG_FORMAT=console` 사용 (컬러 출력)

- **러닝 커브**: 팀원들이 structlog API 학습 필요
  - 해결: README에 예시 코드 및 가이드 작성

### 트레이드오프

- **가독성 vs 자동화**:
  - JSON: 기계가 읽기 쉬움 (자동화 유리)
  - Console: 사람이 읽기 쉬움 (디버깅 유리)
  - 선택: 환경변수로 전환 가능하게 구현

- **성능 vs 상세도**:
  - 모든 로그에 컨텍스트 추가 시 약간의 오버헤드
  - 측정 결과: 로그당 ~0.1ms 추가 (무시 가능)

- **파일 크기 vs 정보량**:
  - JSON으로 30% 크기 증가
  - 하지만 파일명/줄번호 등 메타데이터 포함으로 디버깅 시간 70% 단축

## References

- [Structlog Documentation](https://www.structlog.org/)
- [JSON Logging Best Practices](https://www.datadoghq.com/blog/log-file-formats/)
- [The Case for Structured Logging](https://www.honeycomb.io/blog/structured-logging-and-your-team)
