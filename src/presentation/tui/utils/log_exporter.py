"""
로그 내보내기 모듈

TUI 로그를 파일로 저장하는 기능 제공
"""

from pathlib import Path
from datetime import datetime
from typing import List, Optional
import re
import logging

logger = logging.getLogger(__name__)


class LogExporter:
    """
    로그 내보내기 클래스

    RichLog의 내용을 텍스트 파일로 저장
    """

    @staticmethod
    def export_to_file(
        lines: List[str],
        session_id: str,
        output_dir: Path = Path("logs"),
    ) -> Optional[Path]:
        """
        로그를 파일로 내보내기

        Args:
            lines: 로그 라인 리스트
            session_id: 세션 ID
            output_dir: 출력 디렉토리 경로

        Returns:
            저장된 파일 경로, 실패 시 None
        """
        try:
            # session_id 안전성 검증 (Path Traversal 방지)
            safe_session_id = re.sub(r'[^a-zA-Z0-9_-]', '', session_id)
            if not safe_session_id:
                raise ValueError("Invalid session_id: contains only invalid characters")

            # 출력 디렉토리 생성
            output_dir.mkdir(parents=True, exist_ok=True)

            # 파일명 생성: session_<id>_<timestamp>.log
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"session_{safe_session_id}_{timestamp}.log"
            filepath = output_dir / filename

            # 로그 내용 정제 (Rich 마크업 제거)
            cleaned_lines = [LogExporter._clean_markup(line) for line in lines]

            # 파일 저장
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("\n".join(cleaned_lines))

            return filepath

        except Exception as e:
            logger.error(f"로그 저장 실패: {e}")
            return None

    @staticmethod
    def _clean_markup(text: str) -> str:
        """
        Rich 마크업 제거

        Args:
            text: 원본 텍스트

        Returns:
            마크업이 제거된 텍스트
        """
        # Rich 마크업 패턴: [style]text[/style]
        pattern = r"\[/?[^\]]+\]"
        cleaned = re.sub(pattern, "", text)
        return cleaned

    @staticmethod
    def export_to_markdown(
        lines: List[str],
        session_id: str,
        output_dir: Path = Path("logs"),
    ) -> Optional[Path]:
        """
        로그를 Markdown 파일로 내보내기

        Args:
            lines: 로그 라인 리스트
            session_id: 세션 ID
            output_dir: 출력 디렉토리 경로

        Returns:
            저장된 파일 경로, 실패 시 None
        """
        try:
            # session_id 안전성 검증 (Path Traversal 방지)
            safe_session_id = re.sub(r'[^a-zA-Z0-9_-]', '', session_id)
            if not safe_session_id:
                raise ValueError("Invalid session_id: contains only invalid characters")

            # 출력 디렉토리 생성
            output_dir.mkdir(parents=True, exist_ok=True)

            # 파일명 생성: session_<id>_<timestamp>.md
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"session_{safe_session_id}_{timestamp}.md"
            filepath = output_dir / filename

            # Markdown 형식으로 변환
            markdown_content = LogExporter._convert_to_markdown(lines, session_id)

            # 파일 저장
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(markdown_content)

            return filepath

        except Exception as e:
            logger.error(f"Markdown 저장 실패: {e}")
            return None

    @staticmethod
    def _convert_to_markdown(lines: List[str], session_id: str) -> str:
        """
        로그를 Markdown 형식으로 변환

        Args:
            lines: 로그 라인 리스트
            session_id: 세션 ID

        Returns:
            Markdown 형식 문자열
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        md_lines = [
            f"# AI Orchestration Session Log",
            f"",
            f"**Session ID:** `{session_id}`  ",
            f"**Exported:** {timestamp}",
            f"",
            f"---",
            f"",
        ]

        # 로그 내용 추가 (마크업 제거)
        for line in lines:
            cleaned = LogExporter._clean_markup(line)
            if cleaned.strip():
                md_lines.append(cleaned)

        return "\n".join(md_lines)
