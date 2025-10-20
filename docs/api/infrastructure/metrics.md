# Metrics

비동기 메트릭 수집 API 문서입니다.

## AsyncMetricsCollector

::: src.infrastructure.metrics.async_collector.AsyncMetricsCollector
    options:
      show_source: true
      show_root_heading: true
      members:
        - __init__
        - record
        - get_stats
        - stop

비동기 메트릭 수집기로, 다음 기능을 지원합니다:

- **큐 기반 버퍼링**: 메트릭을 큐에 추가 (논블로킹)
- **주기적 플러시**: 설정된 주기마다 파일에 저장
- **백그라운드 스레드**: 메인 워크플로우에 영향 없음
- **통계 API**: 수집 통계 조회 가능

## 사용 예시

### 메트릭 기록

```python
from src.infrastructure.metrics import AsyncMetricsCollector

collector = AsyncMetricsCollector(
    buffer_size=1000,
    flush_interval=5.0
)

# 메트릭 기록 (논블로킹, ~0.01ms)
collector.record(
    "worker_duration",
    value=123.45,
    worker_name="planner",
    task_id="abc123"
)

# 통계 확인
stats = collector.get_stats()
print(f"Total queued: {stats['total_queued']}")
print(f"Total processed: {stats['total_processed']}")
print(f"Queue size: {stats['queue_size']}")

# 종료 시 남은 메트릭 플러시
collector.stop()
```

### 설정

```json
{
  "performance": {
    "enable_async_metrics": true,
    "metrics_buffer_size": 1000,
    "metrics_flush_interval": 5.0
  }
}
```
