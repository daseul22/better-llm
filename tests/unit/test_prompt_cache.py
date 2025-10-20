"""
프롬프트 캐시 단위 테스트
"""

import pytest
import time
from src.infrastructure.cache import PromptCache


def test_prompt_cache_initialization():
    """PromptCache 초기화 테스트"""
    cache = PromptCache(max_size=10, default_ttl=60.0, enabled=True)

    assert cache.max_size == 10
    assert cache.default_ttl == 60.0
    assert cache.enabled is True
    assert len(cache) == 0


def test_cache_set_and_get():
    """캐시 저장 및 조회 테스트"""
    cache = PromptCache()

    prompt = "What is Python?"
    response = "Python is a programming language"

    # 캐시에 저장
    cache.set(prompt, response)

    # 캐시에서 조회
    cached_response = cache.get(prompt)
    assert cached_response == response

    stats = cache.get_stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 0


def test_cache_miss():
    """캐시 미스 테스트"""
    cache = PromptCache()

    # 존재하지 않는 프롬프트 조회
    result = cache.get("Non-existent prompt")
    assert result is None

    stats = cache.get_stats()
    assert stats["hits"] == 0
    assert stats["misses"] == 1


def test_cache_with_context():
    """컨텍스트를 포함한 캐시 테스트"""
    cache = PromptCache()

    prompt = "What is the weather?"
    context1 = {"location": "Seoul"}
    context2 = {"location": "Tokyo"}

    # 동일한 프롬프트, 다른 컨텍스트
    cache.set(prompt, "Sunny in Seoul", context=context1)
    cache.set(prompt, "Rainy in Tokyo", context=context2)

    # 컨텍스트별로 다른 응답 조회
    assert cache.get(prompt, context=context1) == "Sunny in Seoul"
    assert cache.get(prompt, context=context2) == "Rainy in Tokyo"


def test_cache_ttl_expiration():
    """TTL 만료 테스트"""
    cache = PromptCache(default_ttl=0.5)  # 0.5초 TTL

    prompt = "Test prompt"
    response = "Test response"

    # 캐시에 저장
    cache.set(prompt, response)

    # 즉시 조회 성공
    assert cache.get(prompt) == response

    # TTL 대기
    time.sleep(0.6)

    # TTL 만료로 None 반환
    assert cache.get(prompt) is None

    stats = cache.get_stats()
    assert stats["expirations"] >= 1


def test_lru_eviction():
    """LRU 방출 테스트"""
    cache = PromptCache(max_size=3)

    # 캐시에 3개 항목 추가
    cache.set("prompt1", "response1")
    cache.set("prompt2", "response2")
    cache.set("prompt3", "response3")

    # 4번째 항목 추가 시 가장 오래된 항목(prompt1) 제거
    cache.set("prompt4", "response4")

    assert cache.get("prompt1") is None  # LRU로 제거됨
    assert cache.get("prompt2") == "response2"
    assert cache.get("prompt3") == "response3"
    assert cache.get("prompt4") == "response4"

    stats = cache.get_stats()
    assert stats["evictions"] >= 1


def test_lru_access_order():
    """LRU 접근 순서 테스트"""
    cache = PromptCache(max_size=3)

    # 캐시에 3개 항목 추가
    cache.set("prompt1", "response1")
    cache.set("prompt2", "response2")
    cache.set("prompt3", "response3")

    # prompt1 접근 (최근 사용으로 이동)
    cache.get("prompt1")

    # 4번째 항목 추가 시 prompt2가 제거되어야 함 (가장 오래 미사용)
    cache.set("prompt4", "response4")

    assert cache.get("prompt1") == "response1"  # 접근했으므로 유지
    assert cache.get("prompt2") is None  # LRU로 제거됨
    assert cache.get("prompt3") == "response3"
    assert cache.get("prompt4") == "response4"


def test_cache_invalidate():
    """캐시 무효화 테스트"""
    cache = PromptCache()

    prompt = "Test prompt"
    cache.set(prompt, "Test response")

    # 무효화 전 조회 성공
    assert cache.get(prompt) == "Test response"

    # 무효화
    result = cache.invalidate(prompt)
    assert result is True

    # 무효화 후 조회 실패
    assert cache.get(prompt) is None


def test_cache_clear():
    """캐시 전체 삭제 테스트"""
    cache = PromptCache()

    cache.set("prompt1", "response1")
    cache.set("prompt2", "response2")
    cache.set("prompt3", "response3")

    assert len(cache) == 3

    # 전체 삭제
    cache.clear()

    assert len(cache) == 0
    assert cache.get("prompt1") is None


def test_cleanup_expired():
    """만료된 엔트리 정리 테스트"""
    cache = PromptCache(default_ttl=0.5)

    # 여러 항목 추가
    cache.set("prompt1", "response1")
    cache.set("prompt2", "response2")
    time.sleep(0.3)
    cache.set("prompt3", "response3")  # 나중에 추가

    # TTL 대기 (prompt1, prompt2 만료)
    time.sleep(0.3)

    # 만료된 항목 정리
    cleaned = cache.cleanup_expired()

    # prompt1, prompt2는 만료되었고, prompt3는 아직 유효
    assert cleaned >= 2
    assert cache.get("prompt3") == "response3"


def test_cache_stats():
    """캐시 통계 테스트"""
    cache = PromptCache(max_size=10)

    # 캐시 저장
    cache.set("prompt1", "response1")
    cache.set("prompt2", "response2")

    # 히트
    cache.get("prompt1")
    cache.get("prompt2")

    # 미스
    cache.get("prompt3")

    stats = cache.get_stats()

    assert stats["hits"] == 2
    assert stats["misses"] == 1
    assert stats["inserts"] == 2
    assert stats["cache_size"] == 2
    assert stats["max_size"] == 10
    assert stats["hit_rate"] == 66.67  # 2/3 * 100


def test_cache_disabled():
    """비활성화된 캐시 테스트"""
    cache = PromptCache(enabled=False)

    # 저장 시도
    cache.set("prompt", "response")

    # 비활성화 상태에서는 항상 None 반환
    assert cache.get("prompt") is None
    assert len(cache) == 0


def test_cache_info():
    """캐시 정보 조회 테스트"""
    cache = PromptCache(default_ttl=60.0)

    cache.set("prompt1", "response1")
    cache.set("prompt2", "response2")

    # 캐시 정보 조회
    info = cache.get_cache_info()

    assert len(info) == 2
    assert all("key_prefix" in item for item in info)
    assert all("created_at" in item for item in info)
    assert all("access_count" in item for item in info)
    assert all("ttl" in item for item in info)


def test_custom_ttl():
    """커스텀 TTL 테스트"""
    cache = PromptCache(default_ttl=10.0)

    # 커스텀 TTL로 저장
    cache.set("prompt1", "response1", ttl=0.5)
    cache.set("prompt2", "response2", ttl=5.0)

    # 즉시 조회 성공
    assert cache.get("prompt1") == "response1"
    assert cache.get("prompt2") == "response2"

    # 0.6초 대기 (prompt1 만료)
    time.sleep(0.6)

    assert cache.get("prompt1") is None  # TTL 만료
    assert cache.get("prompt2") == "response2"  # 아직 유효


def test_cache_thread_safety():
    """캐시 스레드 안전성 간단 테스트"""
    import threading

    cache = PromptCache(max_size=100)
    errors = []

    def worker(i):
        try:
            prompt = f"prompt_{i}"
            response = f"response_{i}"
            cache.set(prompt, response)
            result = cache.get(prompt)
            assert result == response
        except Exception as e:
            errors.append(e)

    # 여러 스레드에서 동시 접근
    threads = [threading.Thread(target=worker, args=(i,)) for i in range(50)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # 에러 없이 완료되어야 함
    assert len(errors) == 0
    assert len(cache) <= cache.max_size
