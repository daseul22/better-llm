# Cache

프롬프트 캐싱 API 문서입니다.

## PromptCache

::: src.infrastructure.cache.prompt_cache.PromptCache
    options:
      show_source: true
      show_root_heading: true
      members:
        - __init__
        - get
        - set
        - clear
        - get_stats

프롬프트 캐시로, 다음 기능을 지원합니다:

- **LRU (Least Recently Used)**: 최근 사용되지 않은 항목 제거
- **TTL (Time-To-Live)**: 시간 기반 만료
- **스레드 세이프**: 멀티스레드 환경에서 안전
- **통계 API**: 캐시 히트율 등 조회

## 사용 예시

### 캐시 사용

```python
from src.infrastructure.cache import PromptCache

cache = PromptCache(
    max_size=100,
    default_ttl=3600.0  # 1시간
)

# 캐시에 저장
cache.set("What is Python?", "Python is a programming language")

# 캐시에서 조회
response = cache.get("What is Python?")
if response:
    print("Cache hit!")
else:
    print("Cache miss!")

# 통계 확인
stats = cache.get_stats()
print(f"Hit rate: {stats['hit_rate']}%")
print(f"Cache size: {stats['cache_size']}/{stats['max_size']}")
print(f"Hits: {stats['hits']}, Misses: {stats['misses']}")

# 캐시 초기화
cache.clear()
```

### 설정

```json
{
  "performance": {
    "enable_caching": true,
    "cache_ttl_seconds": 3600,
    "cache_max_size": 100
  }
}
```

## 성능 효과

| 지표 | 개선 효과 |
|------|----------|
| API 호출 횟수 | 30-50% 절감 |
| 응답 시간 | 50-70% 단축 (캐시 히트 시) |
| 비용 | 30-50% 절감 |
