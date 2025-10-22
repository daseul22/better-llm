"""
Worker Context Metadata - Worker 출력의 구조화된 메타데이터

Manager가 컨텍스트를 자동으로 추적하고 전달할 수 있도록
각 Worker 출력에 포함되는 메타데이터를 정의합니다.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional


@dataclass
class WorkerContextMetadata:
    """
    Worker 출력에 포함되는 구조화된 메타데이터

    Manager가 컨텍스트를 자동으로 추적하고 다음 Worker에게 전달할 수 있도록
    각 Worker 실행 결과에 메타데이터를 포함합니다.

    Attributes:
        task_id: 작업 고유 ID (예: "p1_20251022_001")
        worker_name: Worker 이름 (planner, coder, reviewer, tester, committer)
        timestamp: 작업 완료 시각
        dependencies: 이전 task_id 목록 (컨텍스트 체인 추적)
        key_decisions: 중요 결정 사항 목록 (Manager가 추적)
        artifacts: Artifact 파일 경로 목록 (전체 출력 저장 위치)
        summary_levels: 3단계 요약 (one_line, five_line, full)

    Example:
        >>> metadata = WorkerContextMetadata(
        ...     task_id="p1_20251022_001",
        ...     worker_name="planner",
        ...     timestamp=datetime.now(),
        ...     dependencies=[],
        ...     key_decisions=["A안 선택: REST API 방식"],
        ...     artifacts=["~/.better-llm/project/artifacts/planner_20251022_001.txt"],
        ...     summary_levels={
        ...         "one_line": "FastAPI CRUD 엔드포인트 설계 완료",
        ...         "five_line": "...",
        ...         "full": "artifact 경로"
        ...     }
        ... )
        >>> print(metadata.to_dict())
    """
    task_id: str
    worker_name: str
    timestamp: datetime
    dependencies: List[str] = field(default_factory=list)
    key_decisions: List[str] = field(default_factory=list)
    artifacts: List[str] = field(default_factory=list)
    summary_levels: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, any]:
        """
        JSON 직렬화를 위한 딕셔너리 변환

        Returns:
            직렬화 가능한 딕셔너리

        Example:
            >>> metadata = WorkerContextMetadata(
            ...     task_id="p1_20251022_001",
            ...     worker_name="planner",
            ...     timestamp=datetime.now()
            ... )
            >>> data = metadata.to_dict()
            >>> print(data["task_id"])
            p1_20251022_001
        """
        return {
            "task_id": self.task_id,
            "worker_name": self.worker_name,
            "timestamp": self.timestamp.isoformat(),
            "dependencies": self.dependencies,
            "key_decisions": self.key_decisions,
            "artifacts": self.artifacts,
            "summary_levels": self.summary_levels
        }

    @classmethod
    def from_dict(cls, data: Dict[str, any]) -> "WorkerContextMetadata":
        """
        딕셔너리에서 WorkerContextMetadata 객체 생성

        Args:
            data: 직렬화된 메타데이터 딕셔너리

        Returns:
            WorkerContextMetadata 인스턴스

        Example:
            >>> data = {
            ...     "task_id": "p1_20251022_001",
            ...     "worker_name": "planner",
            ...     "timestamp": "2025-10-22T14:30:00",
            ...     "dependencies": [],
            ...     "key_decisions": ["A안 선택"],
            ...     "artifacts": ["~/.better-llm/project/artifacts/planner_20251022_001.txt"],
            ...     "summary_levels": {"one_line": "..."}
            ... }
            >>> metadata = WorkerContextMetadata.from_dict(data)
            >>> print(metadata.worker_name)
            planner
        """
        data = data.copy()
        if "timestamp" in data and isinstance(data["timestamp"], str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)

    def to_json_block(self) -> str:
        """
        Worker 출력 말미에 삽입할 JSON 메타데이터 블록 생성

        Returns:
            Markdown 형식의 JSON 블록 문자열

        Example:
            >>> metadata = WorkerContextMetadata(
            ...     task_id="p1_20251022_001",
            ...     worker_name="planner",
            ...     timestamp=datetime.now()
            ... )
            >>> print(metadata.to_json_block())
            ---
            **Context Metadata** (JSON):
            ```json
            {
              "task_id": "p1_20251022_001",
              ...
            }
            ```
        """
        import json
        json_str = json.dumps(self.to_dict(), indent=2, ensure_ascii=False)
        return f"""---
**Context Metadata** (JSON):
```json
{json_str}
```"""
