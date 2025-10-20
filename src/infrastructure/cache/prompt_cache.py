"""
프롬프트 캐싱 시스템

LRU 캐시 기반으로 프롬프트와 응답을 캐싱하여 중복 API 호출을 방지합니다.
"""

import hashlib
import time
from typing import Optional, Dict, Any, Tuple
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime
import threading

from ..logging import get_logger

logger = get_logger(__name__, component="PromptCache")


@dataclass
class CacheEntry:
    """
    캐시 엔트리 데이터 클래스

    Attributes:
        key: 캐시 키
        value: 캐시 값
        created_at: 생성 시각
        last_accessed: 마지막 접근 시각
        access_count: 접근 횟수
        ttl: TTL (초)
    """
    key: str
    value: Any
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    ttl: float = 3600.0

    def is_expired(self) -> bool:
        """
        TTL 만료 여부 확인

        Returns:
            만료 여부
        """
        return (time.time() - self.created_at) > self.ttl

    def touch(self) -> None:
        """마지막 접근 시각 업데이트 및 접근 횟수 증가"""
        self.last_accessed = time.time()
        self.access_count += 1


class PromptCache:
    """
    LRU 캐시 기반 프롬프트 캐싱

    프롬프트 해시를 키로 사용하여 응답을 캐싱하고,
    TTL(Time-To-Live) 및 LRU(Least Recently Used) 정책을 적용합니다.

    Attributes:
        max_size: 최대 캐시 크기
        default_ttl: 기본 TTL (초)
        enabled: 캐싱 활성화 여부
    """

    def __init__(
        self,
        max_size: int = 100,
        default_ttl: float = 3600.0,
        enabled: bool = True
    ):
        """
        Args:
            max_size: 최대 캐시 크기 (기본: 100)
            default_ttl: 기본 TTL (초, 기본: 3600 = 1시간)
            enabled: 캐싱 활성화 여부 (기본: True)
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.enabled = enabled

        # LRU 캐시 (OrderedDict 사용)
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()

        # 스레드 세이프를 위한 락
        self._lock = threading.RLock()

        # 통계
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "expirations": 0,
            "inserts": 0,
        }

        logger.info(
            "PromptCache initialized",
            max_size=max_size,
            default_ttl=default_ttl,
            enabled=enabled
        )

    def get(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """
        캐시에서 프롬프트 응답 조회

        Args:
            prompt: 프롬프트 텍스트
            context: 추가 컨텍스트 (선택적, 해시에 포함됨)

        Returns:
            캐시된 응답 또는 None
        """
        if not self.enabled:
            return None

        cache_key = self._generate_key(prompt, context)

        with self._lock:
            if cache_key not in self._cache:
                self._stats["misses"] += 1
                logger.debug("Cache miss", key_prefix=cache_key[:16])
                return None

            entry = self._cache[cache_key]

            # TTL 만료 체크
            if entry.is_expired():
                self._stats["expirations"] += 1
                self._stats["misses"] += 1
                logger.debug(
                    "Cache expired",
                    key_prefix=cache_key[:16],
                    age_seconds=time.time() - entry.created_at
                )
                del self._cache[cache_key]
                return None

            # 히트 처리
            entry.touch()
            self._cache.move_to_end(cache_key)  # LRU: 최근 사용으로 이동
            self._stats["hits"] += 1

            logger.debug(
                "Cache hit",
                key_prefix=cache_key[:16],
                access_count=entry.access_count
            )

            return entry.value

    def set(
        self,
        prompt: str,
        value: Any,
        context: Optional[Dict[str, Any]] = None,
        ttl: Optional[float] = None
    ) -> None:
        """
        캐시에 프롬프트 응답 저장

        Args:
            prompt: 프롬프트 텍스트
            value: 응답 값
            context: 추가 컨텍스트 (선택적)
            ttl: TTL (초, 기본값은 default_ttl 사용)
        """
        if not self.enabled:
            return

        cache_key = self._generate_key(prompt, context)
        ttl = ttl or self.default_ttl

        with self._lock:
            # 기존 항목이 있으면 제거 (새로 추가하기 위해)
            if cache_key in self._cache:
                del self._cache[cache_key]

            # 캐시 크기 제한 확인
            if len(self._cache) >= self.max_size:
                # LRU: 가장 오래된 항목 제거
                evicted_key, _ = self._cache.popitem(last=False)
                self._stats["evictions"] += 1
                logger.debug(
                    "Cache eviction (LRU)",
                    evicted_key_prefix=evicted_key[:16],
                    cache_size=len(self._cache)
                )

            # 새 엔트리 추가
            entry = CacheEntry(
                key=cache_key,
                value=value,
                ttl=ttl
            )
            self._cache[cache_key] = entry
            self._stats["inserts"] += 1

            logger.debug(
                "Cache set",
                key_prefix=cache_key[:16],
                ttl=ttl,
                cache_size=len(self._cache)
            )

    def invalidate(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        특정 프롬프트의 캐시 무효화

        Args:
            prompt: 프롬프트 텍스트
            context: 추가 컨텍스트 (선택적)

        Returns:
            무효화 성공 여부
        """
        cache_key = self._generate_key(prompt, context)

        with self._lock:
            if cache_key in self._cache:
                del self._cache[cache_key]
                logger.debug("Cache invalidated", key_prefix=cache_key[:16])
                return True
            return False

    def clear(self) -> None:
        """모든 캐시 삭제"""
        with self._lock:
            cache_size = len(self._cache)
            self._cache.clear()
            logger.info("Cache cleared", previous_size=cache_size)

    def cleanup_expired(self) -> int:
        """
        만료된 캐시 엔트리 정리

        Returns:
            정리된 엔트리 수
        """
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired()
            ]

            for key in expired_keys:
                del self._cache[key]
                self._stats["expirations"] += 1

            if expired_keys:
                logger.debug(
                    "Expired entries cleaned up",
                    count=len(expired_keys)
                )

            return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        """
        캐시 통계 조회

        Returns:
            통계 딕셔너리
        """
        with self._lock:
            total_requests = self._stats["hits"] + self._stats["misses"]
            hit_rate = (
                (self._stats["hits"] / total_requests * 100)
                if total_requests > 0 else 0.0
            )

            return {
                **self._stats,
                "cache_size": len(self._cache),
                "max_size": self.max_size,
                "hit_rate": round(hit_rate, 2),
                "total_requests": total_requests,
            }

    def get_cache_info(self) -> list[Dict[str, Any]]:
        """
        캐시 항목 상세 정보 조회 (디버깅용)

        Returns:
            캐시 항목 정보 리스트
        """
        with self._lock:
            return [
                {
                    "key_prefix": entry.key[:16],
                    "created_at": datetime.fromtimestamp(entry.created_at).isoformat(),
                    "last_accessed": datetime.fromtimestamp(entry.last_accessed).isoformat(),
                    "access_count": entry.access_count,
                    "ttl": entry.ttl,
                    "age_seconds": round(time.time() - entry.created_at, 2),
                    "is_expired": entry.is_expired(),
                }
                for entry in self._cache.values()
            ]

    def _generate_key(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        프롬프트와 컨텍스트에서 캐시 키 생성

        Args:
            prompt: 프롬프트 텍스트
            context: 추가 컨텍스트

        Returns:
            SHA256 해시 문자열
        """
        # 프롬프트와 컨텍스트를 결합하여 해시 생성
        hash_input = prompt

        if context:
            # 컨텍스트를 정렬된 문자열로 변환 (순서 보장)
            context_str = str(sorted(context.items()))
            hash_input += context_str

        # SHA256 해시 생성
        return hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

    def __repr__(self) -> str:
        return (
            f"PromptCache(max_size={self.max_size}, "
            f"default_ttl={self.default_ttl}, "
            f"enabled={self.enabled}, "
            f"size={len(self._cache)})"
        )

    def __len__(self) -> int:
        """현재 캐시 크기 반환"""
        with self._lock:
            return len(self._cache)
