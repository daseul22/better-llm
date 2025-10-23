"""
Artifact Storage - Worker 전체 출력을 외부 파일로 저장

Manager Agent의 컨텍스트 윈도우 절약을 위해
Worker의 전체 출력을 파일로 저장하고,
요약만 Manager에게 전달합니다.

저장 위치: ~/.better-llm/{project-name}/artifacts/
"""

from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta
import re

from ..config import get_data_dir
from ..logging import get_logger

logger = get_logger(__name__, component="ArtifactStorage")


class ArtifactStorage:
    """
    Worker 출력 Artifact 저장소

    Worker의 전체 출력을 파일로 저장하고,
    요약 섹션만 추출하여 Manager에게 전달합니다.

    Attributes:
        artifacts_dir: Artifact 저장 디렉토리
    """

    def __init__(self, artifacts_dir: Optional[Path] = None):
        """
        Args:
            artifacts_dir: Artifact 저장 디렉토리 (기본값: ~/.better-llm/{project}/artifacts)
        """
        if artifacts_dir is None:
            artifacts_dir = get_data_dir("artifacts")

        self.artifacts_dir = Path(artifacts_dir)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            "ArtifactStorage initialized",
            artifacts_dir=str(self.artifacts_dir)
        )

    def save_artifact(
        self,
        worker_name: str,
        full_output: str,
        session_id: Optional[str] = None
    ) -> str:
        """
        Worker 전체 출력을 artifact 파일로 저장

        Args:
            worker_name: Worker 이름 (planner, coder, reviewer, tester 등)
            full_output: Worker 전체 출력
            session_id: 세션 ID (선택적)

        Returns:
            artifact_id (파일 경로 참조용)

        Example:
            >>> storage = ArtifactStorage()
            >>> artifact_id = storage.save_artifact("planner", "...long output...")
            >>> print(artifact_id)
            planner_20250121_143025
        """
        # Artifact ID 생성: {worker_name}_{timestamp}
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        artifact_id = f"{worker_name}_{timestamp}"

        # 세션 ID가 있으면 서브디렉토리에 저장
        if session_id:
            artifact_dir = self.artifacts_dir / session_id
            artifact_dir.mkdir(parents=True, exist_ok=True)
        else:
            artifact_dir = self.artifacts_dir

        # 파일 저장
        artifact_path = artifact_dir / f"{artifact_id}.txt"
        try:
            with open(artifact_path, 'w', encoding='utf-8') as f:
                f.write(full_output)
        except IOError as e:
            logger.error(
                "Artifact 저장 실패 (IOError)",
                artifact_id=artifact_id,
                worker_name=worker_name,
                path=str(artifact_path),
                error=str(e)
            )
            raise
        except Exception as e:
            logger.error(
                "Artifact 저장 실패",
                artifact_id=artifact_id,
                worker_name=worker_name,
                path=str(artifact_path),
                error=str(e)
            )
            raise

        logger.info(
            "Artifact saved",
            artifact_id=artifact_id,
            worker_name=worker_name,
            size_bytes=len(full_output),
            path=str(artifact_path)
        )

        return artifact_id

    def load_artifact(
        self,
        artifact_id: str,
        session_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Artifact 파일 로드

        Args:
            artifact_id: Artifact ID
            session_id: 세션 ID (선택적)

        Returns:
            Artifact 전체 내용 또는 None (파일 없음)

        Example:
            >>> storage = ArtifactStorage()
            >>> content = storage.load_artifact("planner_20250121_143025")
        """
        # 세션 ID가 있으면 서브디렉토리에서 검색
        if session_id:
            artifact_path = self.artifacts_dir / session_id / f"{artifact_id}.txt"
        else:
            artifact_path = self.artifacts_dir / f"{artifact_id}.txt"

        if not artifact_path.exists():
            logger.warning(
                "Artifact not found",
                artifact_id=artifact_id,
                path=str(artifact_path)
            )
            return None

        with open(artifact_path, 'r', encoding='utf-8') as f:
            content = f.read()

        logger.info(
            "Artifact loaded",
            artifact_id=artifact_id,
            size_bytes=len(content)
        )

        return content

    def extract_summary(self, full_output: str) -> Optional[str]:
        """
        Worker 출력에서 요약 섹션만 추출

        "## 📋 [XXX 요약 - Manager 전달용]" 섹션을 찾아서 반환합니다.
        요약 섹션이 없으면 처음 1000자만 반환합니다.

        Args:
            full_output: Worker 전체 출력

        Returns:
            요약 섹션 또는 잘린 출력 + 경고

        Example:
            >>> storage = ArtifactStorage()
            >>> summary = storage.extract_summary(worker_output)
            >>> if summary:
            ...     print(summary)
            ... else:
            ...     print("요약 실패")
        """
        # 여러 패턴 시도 (견고성 향상)
        patterns = [
            # 패턴 1: 이모지 포함 (원본)
            r'##\s*📋\s*\[.+?요약\s*-\s*Manager\s*전달용\]',
            # 패턴 2: 이모지 없이 (폴백)
            r'##\s*\[.+?요약\s*-\s*Manager\s*전달용\]',
            # 패턴 3: 대괄호 없이
            r'##\s*📋.*?요약.*?Manager.*?전달용',
            # 패턴 4: 영문 대체 (PLANNER 요약, CODER 요약 등)
            r'##\s*📋\s*\[[A-Z]+\s*요약\s*-\s*Manager\s*전달용\]',
        ]

        # 디버깅: 출력 샘플 로그
        sample = full_output[:500].replace('\n', '\\n')
        logger.debug(
            "Attempting to extract summary",
            output_size=len(full_output),
            output_sample=sample
        )

        # 각 패턴 시도
        for i, pattern in enumerate(patterns, 1):
            match = re.search(pattern, full_output, re.MULTILINE | re.IGNORECASE)

            if match:
                # 요약 섹션 시작 위치부터 끝까지
                summary_start = match.start()
                summary = full_output[summary_start:].strip()

                logger.info(
                    "Summary extracted successfully",
                    pattern_index=i,
                    matched_text=match.group()[:100],
                    original_size=len(full_output),
                    summary_size=len(summary),
                    reduction_ratio=f"{(1 - len(summary)/len(full_output))*100:.1f}%"
                )

                return summary

        # 모든 패턴 실패 시 - None 반환하여 재요청 트리거
        logger.warning(
            "Summary section not found with any pattern, returning None to trigger re-request",
            output_size=len(full_output),
            tried_patterns=len(patterns)
        )

        # None 반환 → worker_tools.py에서 재요청 트리거
        # 재요청도 실패하면 worker_tools.py의 폴백 로직이 2000자로 제한
        return None

    def cleanup_old_artifacts(self, days: int = 7) -> int:
        """
        오래된 artifact 파일 삭제

        Args:
            days: 보관 기간 (일 단위, 기본값: 7일)

        Returns:
            삭제된 파일 개수

        Example:
            >>> storage = ArtifactStorage()
            >>> deleted = storage.cleanup_old_artifacts(days=7)
            >>> print(f"{deleted} files deleted")
        """
        cutoff_time = datetime.now() - timedelta(days=days)
        deleted_count = 0

        # artifacts 디렉토리의 모든 .txt 파일 검색
        for artifact_file in self.artifacts_dir.rglob("*.txt"):
            # 파일 수정 시간 확인
            mtime = datetime.fromtimestamp(artifact_file.stat().st_mtime)

            if mtime < cutoff_time:
                artifact_file.unlink()
                deleted_count += 1
                logger.debug(
                    "Old artifact deleted",
                    file=str(artifact_file),
                    age_days=(datetime.now() - mtime).days
                )

        if deleted_count > 0:
            logger.info(
                "Old artifacts cleaned up",
                deleted_count=deleted_count,
                cutoff_days=days
            )

        return deleted_count

    def get_artifact_path(
        self,
        artifact_id: str,
        session_id: Optional[str] = None
    ) -> Path:
        """
        Artifact 파일 경로 반환 (Worker가 직접 읽을 때 사용)

        Args:
            artifact_id: Artifact ID
            session_id: 세션 ID (선택적)

        Returns:
            Artifact 파일 절대 경로

        Example:
            >>> storage = ArtifactStorage()
            >>> path = storage.get_artifact_path("planner_20250121_143025")
            >>> print(path)
            /Users/user/.better-llm/my-project/artifacts/planner_20250121_143025.txt
        """
        if session_id:
            return self.artifacts_dir / session_id / f"{artifact_id}.txt"
        else:
            return self.artifacts_dir / f"{artifact_id}.txt"


# 싱글톤 인스턴스 (worker_tools.py에서 사용)
_artifact_storage: Optional[ArtifactStorage] = None


def get_artifact_storage() -> ArtifactStorage:
    """
    ArtifactStorage 싱글톤 인스턴스 반환

    Returns:
        ArtifactStorage 인스턴스
    """
    global _artifact_storage

    if _artifact_storage is None:
        _artifact_storage = ArtifactStorage()

    return _artifact_storage
