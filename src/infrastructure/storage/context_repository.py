"""
프로젝트 컨텍스트 저장소 구현

JsonContextRepository: JSON 파일 기반 컨텍스트 저장소
"""

import json
import logging
from pathlib import Path
from typing import Optional

from ...application.ports import IContextRepository
from ...domain.services import ProjectContext

logger = logging.getLogger(__name__)


class JsonContextRepository(IContextRepository):
    """
    JSON 파일 기반 프로젝트 컨텍스트 저장소

    .context.json 파일 사용
    """

    def __init__(self, context_file: Path = Path(".context.json")):
        """
        Args:
            context_file: 컨텍스트 파일 경로
        """
        self.context_file = context_file

    def load(self) -> Optional[ProjectContext]:
        """
        프로젝트 컨텍스트 로드

        Returns:
            ProjectContext 또는 None (파일 없을 경우)
        """
        if not self.context_file.exists():
            logger.warning(f"⚠️  프로젝트 컨텍스트 파일이 없습니다: {self.context_file}")
            return None

        try:
            with open(self.context_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            context = ProjectContext.from_dict(data)
            logger.info(f"✅ 프로젝트 컨텍스트 로드: {context.project_name}")
            return context

        except Exception as e:
            logger.error(f"❌ 컨텍스트 로드 실패: {e}")
            return None

    def save(self, context: ProjectContext) -> None:
        """
        프로젝트 컨텍스트 저장

        Args:
            context: 저장할 컨텍스트
        """
        try:
            with open(self.context_file, 'w', encoding='utf-8') as f:
                json.dump(context.to_dict(), f, indent=2, ensure_ascii=False)

            logger.info(f"✅ 프로젝트 컨텍스트 저장: {self.context_file}")

        except Exception as e:
            logger.error(f"❌ 컨텍스트 저장 실패: {e}")
            raise
