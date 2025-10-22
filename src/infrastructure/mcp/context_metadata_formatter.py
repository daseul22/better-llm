"""
Context Metadata Formatter - Worker 출력에 메타데이터 추가

Worker 출력을 분석하여 구조화된 메타데이터를 생성하고,
Worker 출력 말미에 JSON 메타데이터 블록을 추가합니다.
"""

import re
import json
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

from src.domain.models.context_metadata import WorkerContextMetadata
from ..logging import get_logger

logger = get_logger(__name__, component="ContextMetadataFormatter")


class ContextMetadataFormatter:
    """
    Worker 출력에 메타데이터를 추가하는 포맷터

    Worker의 raw 출력을 분석하여:
    1. key_decisions 추출 (중요 결정 사항)
    2. 3단계 요약 생성 (one_line, five_line, full)
    3. JSON 메타데이터 블록 생성 및 추가

    Example:
        >>> formatter = ContextMetadataFormatter()
        >>> enhanced_output = formatter.format_worker_output(
        ...     worker_name="planner",
        ...     output="Planner의 상세 계획...",
        ...     artifact_path="/path/to/artifact.txt",
        ...     dependencies=[]
        ... )
        >>> print(enhanced_output)
        (원본 출력)
        ---
        **Context Metadata** (JSON):
        ```json
        {
          "task_id": "planner_20251022_143025",
          ...
        }
        ```
    """

    def __init__(self):
        """ContextMetadataFormatter 초기화"""
        pass

    def format_worker_output(
        self,
        worker_name: str,
        output: str,
        artifact_path: Optional[str] = None,
        dependencies: Optional[List[str]] = None
    ) -> str:
        """
        Worker 출력에 메타데이터 블록 추가

        Args:
            worker_name: Worker 이름 (planner, coder, reviewer, tester, committer)
            output: Worker의 raw 출력
            artifact_path: Artifact 파일 경로 (선택적)
            dependencies: 이전 task_id 목록 (컨텍스트 체인, 선택적)

        Returns:
            메타데이터가 추가된 Worker 출력

        Example:
            >>> formatter = ContextMetadataFormatter()
            >>> enhanced = formatter.format_worker_output(
            ...     worker_name="planner",
            ...     output="## 계획\\n...",
            ...     artifact_path="~/.better-llm/project/artifacts/planner_20251022_001.txt"
            ... )
        """
        # 1. Task ID 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        task_id = f"{worker_name}_{timestamp}"

        # 2. Key decisions 추출
        key_decisions = self._extract_key_decisions(output)

        # 3. 3단계 요약 생성
        summary_levels = self._generate_summary_levels(output, artifact_path)

        # 4. WorkerContextMetadata 생성
        metadata = WorkerContextMetadata(
            task_id=task_id,
            worker_name=worker_name,
            timestamp=datetime.now(),
            dependencies=dependencies or [],
            key_decisions=key_decisions,
            artifacts=[artifact_path] if artifact_path else [],
            summary_levels=summary_levels
        )

        # 5. 메타데이터 블록 생성 및 추가
        metadata_block = metadata.to_json_block()
        enhanced_output = f"{output}\n\n{metadata_block}"

        logger.debug(
            "Context metadata added to worker output",
            worker_name=worker_name,
            task_id=task_id,
            key_decisions_count=len(key_decisions),
            dependencies_count=len(dependencies or [])
        )

        return enhanced_output

    def _extract_key_decisions(self, output: str) -> List[str]:
        """
        Worker 출력에서 중요 결정 사항 추출

        다음 패턴을 찾습니다:
        - "결정:", "Decision:", "선택:", "Choice:"
        - "중요:", "Important:", "주의:", "Note:"
        - "권장:", "Recommendation:", "제안:", "Suggestion:"

        Args:
            output: Worker 출력 텍스트

        Returns:
            중요 결정 사항 목록 (최대 10개)

        Example:
            >>> formatter = ContextMetadataFormatter()
            >>> decisions = formatter._extract_key_decisions(
            ...     "결정: A안 선택\\n권장: REST API 사용"
            ... )
            >>> print(decisions)
            ["A안 선택", "REST API 사용"]
        """
        decision_patterns = [
            r"(?:결정|Decision):\s*(.+?)(?:\n|$)",
            r"(?:선택|Choice):\s*(.+?)(?:\n|$)",
            r"(?:중요|Important):\s*(.+?)(?:\n|$)",
            r"(?:주의|Note):\s*(.+?)(?:\n|$)",
            r"(?:권장|Recommendation):\s*(.+?)(?:\n|$)",
            r"(?:제안|Suggestion):\s*(.+?)(?:\n|$)",
        ]

        decisions = []
        for pattern in decision_patterns:
            matches = re.findall(pattern, output, re.MULTILINE | re.IGNORECASE)
            for match in matches:
                decision = match.strip()[:200]  # 최대 200자
                if decision and decision not in decisions:
                    decisions.append(decision)

        return decisions[:10]  # 최대 10개

    def _generate_summary_levels(
        self,
        output: str,
        artifact_path: Optional[str]
    ) -> Dict[str, str]:
        """
        3단계 요약 생성 (one_line, five_line, full)

        Args:
            output: Worker 출력 텍스트
            artifact_path: Artifact 파일 경로 (full 요약에 사용)

        Returns:
            요약 딕셔너리 {"one_line": "...", "five_line": "...", "full": "..."}

        Example:
            >>> formatter = ContextMetadataFormatter()
            >>> summaries = formatter._generate_summary_levels(
            ...     "## 계획\\n...",
            ...     "/path/to/artifact.txt"
            ... )
            >>> print(summaries["one_line"])
        """
        # 1. one_line: 첫 줄 또는 제목 추출
        one_line = self._extract_one_line_summary(output)

        # 2. five_line: 요약 섹션이 있으면 추출, 없으면 첫 5줄
        five_line = self._extract_five_line_summary(output)

        # 3. full: Artifact 경로 (전체 출력은 artifact 파일에 저장됨)
        full = artifact_path or "(no artifact)"

        return {
            "one_line": one_line,
            "five_line": five_line,
            "full": full
        }

    def _extract_one_line_summary(self, output: str) -> str:
        """
        1줄 요약 추출

        다음 우선순위로 추출:
        1. "## 📋 [XXX 요약 - Manager 전달용]" 다음의 첫 줄
        2. "상태: 구현 완료" 같은 상태 라인
        3. 첫 번째 마크다운 제목 (# 또는 ##)
        4. 첫 100자

        Args:
            output: Worker 출력 텍스트

        Returns:
            1줄 요약 (최대 200자)

        Example:
            >>> formatter = ContextMetadataFormatter()
            >>> summary = formatter._extract_one_line_summary(
            ...     "## 📋 요약\\n\\n**상태**: 구현 완료\\n..."
            ... )
            >>> print(summary)
            상태: 구현 완료
        """
        lines = output.split("\n")

        # 1. "상태:" 라인 찾기
        for line in lines:
            if re.search(r"^\*?\*?상태\*?\*?:\s*(.+)", line, re.IGNORECASE):
                match = re.search(r"^\*?\*?상태\*?\*?:\s*(.+)", line, re.IGNORECASE)
                return match.group(1).strip()[:200]

        # 2. 첫 번째 마크다운 제목 찾기
        for line in lines:
            if line.strip().startswith("#"):
                title = re.sub(r"^#+\s*", "", line.strip())
                # 이모지 제거
                title = re.sub(r"[\U0001F000-\U0001F9FF]", "", title)
                return title.strip()[:200]

        # 3. 첫 100자
        first_line = output[:200].replace("\n", " ").strip()
        return first_line

    def _extract_five_line_summary(self, output: str) -> str:
        """
        5줄 요약 추출

        다음 우선순위로 추출:
        1. "핵심 구현 내용" 섹션 (3-5줄)
        2. "변경 파일" 섹션 (파일 목록)
        3. 전체 출력의 첫 5줄

        Args:
            output: Worker 출력 텍스트

        Returns:
            5줄 요약 (최대 500자)

        Example:
            >>> formatter = ContextMetadataFormatter()
            >>> summary = formatter._extract_five_line_summary(
            ...     "## 요약\\n\\n**핵심 구현 내용**:\\n- API 엔드포인트\\n- 모델 정의\\n..."
            ... )
        """
        # 1. "핵심 구현 내용" 섹션 찾기
        core_pattern = r"\*?\*?핵심\s*구현\s*내용\*?\*?:?\s*\n((?:[-*]\s*.+\n?)+)"
        match = re.search(core_pattern, output, re.MULTILINE | re.IGNORECASE)
        if match:
            core_section = match.group(1).strip()[:500]
            return core_section

        # 2. "변경 파일" 섹션 찾기
        files_pattern = r"\*?\*?변경\s*파일\*?\*?:?\s*\n((?:[-*]\s*.+\n?)+)"
        match = re.search(files_pattern, output, re.MULTILINE | re.IGNORECASE)
        if match:
            files_section = match.group(1).strip()[:500]
            return files_section

        # 3. 첫 5줄 (비어있지 않은 줄만)
        lines = [line for line in output.split("\n") if line.strip()]
        first_five = "\n".join(lines[:5])[:500]
        return first_five

    def parse_metadata_from_output(self, output: str) -> Optional[WorkerContextMetadata]:
        """
        Worker 출력에서 JSON 메타데이터 블록 파싱

        Args:
            output: 메타데이터가 포함된 Worker 출력

        Returns:
            WorkerContextMetadata 인스턴스 또는 None (파싱 실패 시)

        Example:
            >>> formatter = ContextMetadataFormatter()
            >>> output_with_metadata = "...\\n```json\\n{...}\\n```"
            >>> metadata = formatter.parse_metadata_from_output(output_with_metadata)
            >>> print(metadata.task_id if metadata else "None")
        """
        # JSON 코드 블록 찾기 (```json ... ```)
        json_pattern = r"```json\s*\n(\{.+?\})\s*\n```"
        match = re.search(json_pattern, output, re.DOTALL)

        if not match:
            logger.debug("No JSON metadata block found in worker output")
            return None

        try:
            json_str = match.group(1)
            data = json.loads(json_str)
            metadata = WorkerContextMetadata.from_dict(data)

            logger.debug(
                "Context metadata parsed successfully",
                task_id=metadata.task_id,
                worker_name=metadata.worker_name
            )

            return metadata

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(
                "Failed to parse context metadata",
                error=str(e),
                json_preview=json_str[:200] if match else "N/A"
            )
            return None
