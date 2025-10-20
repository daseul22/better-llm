# Logging

구조화된 로깅 API 문서입니다.

## setup_logging

::: src.infrastructure.logging.setup.setup_logging
    options:
      show_source: true
      show_root_heading: true

## get_logger

::: src.infrastructure.logging.setup.get_logger
    options:
      show_source: true
      show_root_heading: true

## ErrorTracker

::: src.infrastructure.logging.error_tracker.ErrorTracker
    options:
      show_source: true
      show_root_heading: true
      members:
        - track_error
        - get_stats
        - clear

## 사용 예시

### 기본 로깅

```python
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)

logger.info("Worker started", worker_name="planner")
logger.error("Worker failed", worker_name="coder", error="timeout")
```

### 에러 추적

```python
from src.infrastructure.logging import track_error, get_error_stats

try:
    worker.run(task)
except Exception as e:
    track_error(e, "worker_execution", worker_name="planner")

# 에러 통계 조회
stats = get_error_stats()
print(stats["total_errors"])
print(stats["error_counts"])
```
