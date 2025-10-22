"""
메모리 저장소 포트 (인터페이스)

IMemoryBankRepository: 메모리 뱅크 저장소 인터페이스
"""

from abc import ABC, abstractmethod
from typing import List

from src.domain.models import Memory, MemoryQuery, MemorySearchResult


class IMemoryBankRepository(ABC):
    """
    메모리 뱅크 저장소 인터페이스

    Infrastructure 계층에서 구현됨 (FAISS 기반)
    """

    @abstractmethod
    def save_memory(self, memory: Memory) -> None:
        """
        메모리 저장

        Args:
            memory: 저장할 메모리

        Raises:
            Exception: 저장 실패 시
        """
        pass

    @abstractmethod
    def search(self, query: MemoryQuery) -> List[MemorySearchResult]:
        """
        유사도 기반 메모리 검색

        Args:
            query: 검색 쿼리

        Returns:
            검색 결과 리스트 (유사도 순으로 정렬)

        Raises:
            Exception: 검색 실패 시
        """
        pass

    @abstractmethod
    def get_by_id(self, memory_id: str) -> Memory | None:
        """
        ID로 메모리 조회

        Args:
            memory_id: 메모리 ID

        Returns:
            메모리 (없으면 None)
        """
        pass

    @abstractmethod
    def delete(self, memory_id: str) -> bool:
        """
        메모리 삭제

        Args:
            memory_id: 메모리 ID

        Returns:
            삭제 성공 여부
        """
        pass

    @abstractmethod
    def count(self) -> int:
        """
        저장된 메모리 개수

        Returns:
            메모리 개수
        """
        pass

    @abstractmethod
    def clear(self) -> None:
        """모든 메모리 삭제 (테스트용)"""
        pass
