"""
Embedding Service - 텍스트를 벡터로 변환

Sentence Transformers를 사용하여 텍스트 임베딩 생성
"""

import numpy as np
from typing import List
from sentence_transformers import SentenceTransformer

from ..logging import get_logger

logger = get_logger(__name__, component="EmbeddingService")


class EmbeddingService:
    """
    텍스트 임베딩 서비스

    Sentence Transformers를 사용하여 텍스트를 벡터로 변환합니다.
    기본 모델: all-MiniLM-L6-v2 (384차원, 빠르고 효율적)

    Attributes:
        model: Sentence Transformer 모델
        dimension: 임베딩 벡터 차원

    Example:
        >>> service = EmbeddingService()
        >>> embedding = service.encode("FastAPI로 CRUD API 구현")
        >>> len(embedding)
        384
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Embedding Service 초기화

        Args:
            model_name: Sentence Transformer 모델 이름
        """
        logger.info(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
        logger.info(f"Embedding model loaded (dimension: {self.dimension})")

    def encode(self, text: str) -> np.ndarray:
        """
        단일 텍스트를 임베딩 벡터로 변환

        Args:
            text: 입력 텍스트

        Returns:
            임베딩 벡터 (numpy array)
        """
        embedding = self.model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
        return embedding

    def encode_batch(self, texts: List[str]) -> np.ndarray:
        """
        여러 텍스트를 배치로 임베딩 변환 (성능 최적화)

        Args:
            texts: 입력 텍스트 리스트

        Returns:
            임베딩 벡터 배열 (shape: [len(texts), dimension])
        """
        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            batch_size=32,
            show_progress_bar=False
        )
        return embeddings

    def similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        두 임베딩 벡터 간의 코사인 유사도 계산

        Args:
            embedding1: 첫 번째 임베딩 벡터
            embedding2: 두 번째 임베딩 벡터

        Returns:
            코사인 유사도 (0.0 ~ 1.0, 높을수록 유사)
        """
        # 정규화된 벡터의 내적 = 코사인 유사도
        return float(np.dot(embedding1, embedding2))
