"""
Memory Bank Repository - FAISS 기반 벡터 검색

세션 메모리를 벡터로 저장하고 유사도 기반 검색을 수행합니다.
"""

import faiss
import numpy as np
import json
from pathlib import Path
from typing import List, Dict

from src.application.ports import IMemoryBankRepository
from src.domain.models import Memory, MemoryQuery, MemorySearchResult
from .embedding_service import EmbeddingService
from ..config import get_data_dir
from ..logging import get_logger

logger = get_logger(__name__, component="MemoryBankRepository")


class FAISSMemoryBankRepository(IMemoryBankRepository):
    """
    FAISS 기반 메모리 뱅크 저장소

    벡터 검색을 위해 FAISS를 사용하고, 메타데이터는 JSON 파일로 저장합니다.

    Attributes:
        embedding_service: 임베딩 생성 서비스
        index: FAISS 인덱스
        memories: 메모리 ID → Memory 매핑 (메타데이터)
        id_to_index: 메모리 ID → FAISS 인덱스 위치 매핑
    """

    def __init__(
        self,
        embedding_service: EmbeddingService | None = None,
        storage_dir: Path | None = None
    ):
        """
        Memory Bank Repository 초기화

        Args:
            embedding_service: 임베딩 서비스 (None이면 기본 생성)
            storage_dir: 저장 디렉토리 (None이면 ~/.better-llm/{project}/memory)
        """
        self.embedding_service = embedding_service or EmbeddingService()
        self.storage_dir = storage_dir or get_data_dir("memory")
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # FAISS 인덱스 초기화 (코사인 유사도를 위해 정규화된 벡터 사용)
        dimension = self.embedding_service.dimension
        self.index = faiss.IndexFlatIP(dimension)  # Inner Product (정규화 시 코사인 유사도)

        # 메타데이터 저장
        self.memories: Dict[str, Memory] = {}
        self.id_to_index: Dict[str, int] = {}

        # 기존 데이터 로드
        self._load()
        logger.info(f"MemoryBankRepository initialized (count: {self.count()})")

    def save_memory(self, memory: Memory) -> None:
        """메모리 저장"""
        # 1. 임베딩 생성
        text = memory.to_text()
        embedding = self.embedding_service.encode(text)

        # 2. FAISS 인덱스에 추가
        embedding_2d = embedding.reshape(1, -1).astype('float32')
        index_position = self.index.ntotal
        self.index.add(embedding_2d)

        # 3. 메타데이터 저장
        self.memories[memory.id] = memory
        self.id_to_index[memory.id] = index_position

        # 4. 영속화
        self._save()
        logger.debug(f"Memory saved: {memory.id}")

    def search(self, query: MemoryQuery) -> List[MemorySearchResult]:
        """유사도 기반 메모리 검색"""
        if self.index.ntotal == 0:
            return []

        # 1. 쿼리 임베딩 생성
        query_embedding = self.embedding_service.encode(query.query_text)
        query_2d = query_embedding.reshape(1, -1).astype('float32')

        # 2. FAISS 검색 (top-k)
        k = min(query.top_k, self.index.ntotal)
        distances, indices = self.index.search(query_2d, k)

        # 3. 결과 변환 (인덱스 → 메모리)
        results: List[MemorySearchResult] = []
        index_to_id = {v: k for k, v in self.id_to_index.items()}

        for dist, idx in zip(distances[0], indices[0]):
            memory_id = index_to_id.get(int(idx))
            if memory_id is None:
                continue

            memory = self.memories.get(memory_id)
            if memory is None:
                continue

            similarity = float(dist)  # Inner product (정규화 시 코사인 유사도)

            if similarity >= query.threshold:
                results.append(MemorySearchResult(
                    memory=memory,
                    similarity_score=similarity
                ))

        return results

    def get_by_id(self, memory_id: str) -> Memory | None:
        """ID로 메모리 조회"""
        return self.memories.get(memory_id)

    def delete(self, memory_id: str) -> bool:
        """메모리 삭제"""
        if memory_id not in self.memories:
            return False

        # FAISS는 개별 삭제를 지원하지 않으므로, 메타데이터만 삭제하고 재구축 필요
        del self.memories[memory_id]
        del self.id_to_index[memory_id]

        # 인덱스 재구축
        self._rebuild_index()
        self._save()
        logger.debug(f"Memory deleted: {memory_id}")
        return True

    def count(self) -> int:
        """저장된 메모리 개수"""
        return len(self.memories)

    def clear(self) -> None:
        """모든 메모리 삭제 (테스트용)"""
        dimension = self.embedding_service.dimension
        self.index = faiss.IndexFlatIP(dimension)
        self.memories.clear()
        self.id_to_index.clear()
        self._save()
        logger.warning("All memories cleared")

    def _rebuild_index(self) -> None:
        """인덱스 재구축 (삭제 후 필요)"""
        dimension = self.embedding_service.dimension
        self.index = faiss.IndexFlatIP(dimension)
        self.id_to_index.clear()

        if not self.memories:
            return

        # 모든 메모리 재삽입
        texts = [m.to_text() for m in self.memories.values()]
        embeddings = self.embedding_service.encode_batch(texts)

        self.index.add(embeddings.astype('float32'))

        for i, memory_id in enumerate(self.memories.keys()):
            self.id_to_index[memory_id] = i

    def _save(self) -> None:
        """FAISS 인덱스 및 메타데이터 저장"""
        # FAISS 인덱스 저장
        index_path = self.storage_dir / "faiss_index.bin"
        faiss.write_index(self.index, str(index_path))

        # 메타데이터 저장
        metadata_path = self.storage_dir / "metadata.json"
        metadata = {
            memory_id: memory.to_dict()
            for memory_id, memory in self.memories.items()
        }
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        # ID 매핑 저장
        mapping_path = self.storage_dir / "id_mapping.json"
        with open(mapping_path, 'w', encoding='utf-8') as f:
            json.dump(self.id_to_index, f, indent=2)

    def _load(self) -> None:
        """FAISS 인덱스 및 메타데이터 로드"""
        index_path = self.storage_dir / "faiss_index.bin"
        metadata_path = self.storage_dir / "metadata.json"
        mapping_path = self.storage_dir / "id_mapping.json"

        if not index_path.exists():
            return

        try:
            # FAISS 인덱스 로드
            self.index = faiss.read_index(str(index_path))

            # 메타데이터 로드
            if metadata_path.exists():
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    self.memories = {
                        memory_id: Memory.from_dict(data)
                        for memory_id, data in metadata.items()
                    }

            # ID 매핑 로드
            if mapping_path.exists():
                with open(mapping_path, 'r', encoding='utf-8') as f:
                    self.id_to_index = json.load(f)

            logger.info(f"Loaded {len(self.memories)} memories from storage")
        except Exception as e:
            logger.error(f"Failed to load memory bank: {e}")
            # 로드 실패 시 빈 상태로 시작
            dimension = self.embedding_service.dimension
            self.index = faiss.IndexFlatIP(dimension)
            self.memories.clear()
            self.id_to_index.clear()
