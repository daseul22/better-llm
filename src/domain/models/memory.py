"""
메모리 도메인 모델 (Project Memory Bank)

Memory: 벡터 DB에 저장될 세션 메모리
MemoryQuery: 유사도 검색 쿼리
MemorySearchResult: 검색 결과
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Any


@dataclass
class Memory:
    """
    세션 메모리 도메인 모델

    Attributes:
        id: 메모리 고유 ID (세션 ID)
        task_description: 작업 설명 (사용자 입력)
        session_summary: 세션 요약 (Manager의 최종 응답)
        files_modified: 수정된 파일 목록
        tags: 태그 목록 (예: ["FastAPI", "CRUD", "SQLAlchemy"])
        created_at: 생성 시각
        metadata: 추가 메타데이터
    """
    id: str
    task_description: str
    session_summary: str
    files_modified: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_text(self) -> str:
        """
        임베딩을 위한 텍스트 표현 생성

        Returns:
            작업 설명, 요약, 태그를 결합한 텍스트
        """
        tags_str = ", ".join(self.tags) if self.tags else ""
        files_str = ", ".join(self.files_modified) if self.files_modified else ""

        parts = [
            f"Task: {self.task_description}",
            f"Summary: {self.session_summary}",
        ]

        if tags_str:
            parts.append(f"Tags: {tags_str}")
        if files_str:
            parts.append(f"Files: {files_str}")

        return "\n".join(parts)

    def to_dict(self) -> dict:
        """JSON 직렬화용 딕셔너리 변환"""
        return {
            "id": self.id,
            "task_description": self.task_description,
            "session_summary": self.session_summary,
            "files_modified": self.files_modified,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Memory":
        """딕셔너리에서 Memory 인스턴스 생성"""
        return cls(
            id=data["id"],
            task_description=data["task_description"],
            session_summary=data["session_summary"],
            files_modified=data.get("files_modified", []),
            tags=data.get("tags", []),
            created_at=datetime.fromisoformat(data["created_at"]),
            metadata=data.get("metadata", {}),
        )


@dataclass
class MemoryQuery:
    """
    메모리 검색 쿼리

    Attributes:
        query_text: 검색 쿼리 텍스트
        top_k: 반환할 결과 개수 (기본값: 5)
        threshold: 유사도 임계값 (0.0 ~ 1.0, 기본값: 0.0 = 임계값 없음)
    """
    query_text: str
    top_k: int = 5
    threshold: float = 0.0


@dataclass
class MemorySearchResult:
    """
    메모리 검색 결과

    Attributes:
        memory: 검색된 메모리
        similarity_score: 유사도 점수 (0.0 ~ 1.0, 높을수록 유사)
    """
    memory: Memory
    similarity_score: float

    def to_dict(self) -> dict:
        """JSON 직렬화용 딕셔너리 변환"""
        return {
            "memory": self.memory.to_dict(),
            "similarity_score": self.similarity_score,
        }
