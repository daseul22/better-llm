# 5. 비동기 메트릭 수집

## Status

Accepted

## Context

Better-LLM은 다음과 같은 메트릭을 수집해야 했습니다:

- **Worker 실행 시간**: 각 Worker가 작업을 완료하는 데 걸린 시간
- **API 호출 횟수**: Claude API 호출 빈도 (비용 추적)
- **에러 발생 빈도**: Worker별 에러율
- **캐시 히트율**: 프롬프트 캐시 효율성
- **세션 통계**: 전체 세션 수, 평균 턴 수 등

### 동기 메트릭 수집의 문제점

초기 구현에서는 메트릭을 동기적으로 수집했습니다:

```python
# 문제가 있는 코드
def execute_worker(worker_name: str, task: str):
    start_time = time.time()
    result = worker.run(task)
    duration = time.time() - start_time

    # 동기적으로 메트릭 저장 (메인 워크플로우 블로킹!)
    metrics_collector.record_duration(worker_name, duration)
    metrics_collector.save_to_file()  # 파일 I/O 블로킹

    return result
```

**문제점:**

1. **메인 워크플로우 블로킹**: 메트릭 저장 시 파일 I/O로 인해 Worker 실행이 지연됨
2. **성능 저하**: 메트릭 1개당 ~5-10ms 지연 발생, 50개 메트릭 수집 시 최대 500ms 낭비
3. **에러 전파**: 메트릭 저장 실패 시 Worker 실행도 실패 처리됨
4. **확장성 제약**: 메트릭 수가 늘어날수록 성능 저하

### 고려한 대안

1. **메트릭 수집 비활성화**:
   - 메트릭을 아예 수집하지 않음
   - 문제: 성능 모니터링 불가, 비용 추적 어려움

2. **주기적 배치 저장**:
   - 메모리에 메트릭 누적 후 5초마다 한 번에 저장
   - 문제: 프로세스 종료 시 메트릭 손실 가능

3. **비동기 메트릭 수집 (큐 기반)**:
   - 메트릭을 큐에 추가하고, 별도 스레드에서 처리
   - 장점: 메인 워크플로우 블로킹 없음, 안정성 높음

4. **외부 메트릭 시스템 (Prometheus/StatsD)**:
   - 전문 메트릭 수집 시스템 사용
   - 문제: 추가 인프라 필요, 로컬 개발 복잡도 증가

## Decision

**큐 기반 비동기 메트릭 수집**을 구현하여 메인 워크플로우와 독립적으로 메트릭을 처리하도록 했습니다.

### 구현 방식

```python
# src/infrastructure/metrics/async_collector.py

import queue
import threading
import time
from typing import Dict, Any

class AsyncMetricsCollector:
    """비동기 메트릭 수집기 (큐 기반)"""

    def __init__(self, buffer_size: int = 1000, flush_interval: float = 5.0):
        self._queue = queue.Queue(maxsize=buffer_size)
        self._flush_interval = flush_interval
        self._worker_thread = threading.Thread(target=self._process_metrics, daemon=True)
        self._worker_thread.start()

    def record(self, metric_name: str, value: Any, **context):
        """메트릭 기록 (논블로킹)"""
        try:
            self._queue.put_nowait({
                "metric_name": metric_name,
                "value": value,
                "timestamp": time.time(),
                **context
            })
        except queue.Full:
            # 큐가 가득 차면 가장 오래된 메트릭 무시 (메인 워크플로우 보호)
            pass

    def _process_metrics(self):
        """백그라운드 스레드에서 메트릭 처리"""
        batch = []
        last_flush = time.time()

        while True:
            try:
                # 0.1초마다 큐 확인
                metric = self._queue.get(timeout=0.1)
                batch.append(metric)
            except queue.Empty:
                pass

            # 주기적 플러시 또는 배치가 100개 이상일 때
            if time.time() - last_flush >= self._flush_interval or len(batch) >= 100:
                if batch:
                    self._flush_batch(batch)
                    batch = []
                    last_flush = time.time()

    def _flush_batch(self, batch: list):
        """메트릭 배치를 파일에 저장"""
        try:
            # 파일 I/O (메인 스레드에 영향 없음)
            with open("metrics.jsonl", "a") as f:
                for metric in batch:
                    f.write(json.dumps(metric) + "\n")
        except Exception as e:
            # 메트릭 저장 실패해도 메인 워크플로우에 영향 없음
            logger.error("Failed to flush metrics", error=str(e))
```

### 사용 예시

```python
# Worker 실행 시
metrics = AsyncMetricsCollector()

start_time = time.time()
result = worker.run(task)
duration = time.time() - start_time

# 논블로킹 메트릭 기록 (~0.01ms)
metrics.record("worker_duration", duration, worker_name="planner")

# 메인 워크플로우는 즉시 계속 실행됨
return result
```

### 설정 옵션

```json
{
  "performance": {
    "enable_async_metrics": true,
    "metrics_buffer_size": 1000,      // 큐 최대 크기
    "metrics_flush_interval": 5.0     // 플러시 주기 (초)
  }
}
```

## Consequences

### 긍정적 결과

- **성능 향상**: 메트릭 기록이 메인 워크플로우를 블로킹하지 않음
  - Before: Worker 실행 + 메트릭 저장 = 1020ms
  - After: Worker 실행 = 1000ms, 메트릭 저장 = 백그라운드

- **안정성 향상**:
  - 메트릭 저장 실패해도 Worker 실행은 성공
  - 큐가 가득 차도 메인 워크플로우 보호 (오래된 메트릭 드롭)

- **확장성**:
  - 메트릭 수가 늘어나도 성능 영향 없음
  - 배치 처리로 파일 I/O 횟수 감소 (100개 → 1회)

- **메모리 효율성**:
  - 큐 크기 제한으로 메모리 사용량 제한 (1000개 = ~100KB)
  - 주기적 플러시로 메모리 누수 방지

### 부정적 결과

- **메트릭 손실 가능성**:
  - 프로세스 비정상 종료 시 큐에 있는 메트릭 손실
  - 해결: `stop()` 메서드에서 남은 메트릭 강제 플러시

- **실시간성 부족**:
  - 최대 5초 지연 후 메트릭 저장
  - 실시간 대시보드에는 적합하지 않음

- **디버깅 어려움**:
  - 멀티스레드 환경으로 인한 디버깅 복잡도
  - 해결: 상세한 로깅 및 통계 API 제공

### 트레이드오프

- **실시간성 vs 성능**:
  - 동기: 즉시 저장되지만 느림
  - 비동기: 최대 5초 지연되지만 빠름
  - 선택: Better-LLM은 실시간 대시보드가 아니므로 비동기 선택

- **안정성 vs 완전성**:
  - 큐 가득 찰 때 메트릭 드롭 (안정성 우선)
  - 대안: 큐가 가득 차면 블로킹 (완전성 우선)
  - 선택: 메인 워크플로우 보호가 더 중요

- **메모리 vs 디스크 I/O**:
  - 큐에 메트릭 버퍼링 (메모리 사용)
  - 배치로 파일 I/O 최소화
  - 밸런스: 1000개 큐 크기, 5초 플러시

## References

- [Python Queue - Thread-safe Queue](https://docs.python.org/3/library/queue.html)
- [Asynchronous Metrics Collection Patterns](https://www.datadoghq.com/blog/engineering/introducing-glommio/)
- [StatsD - Simple Daemon for Stats Aggregation](https://github.com/statsd/statsd)
