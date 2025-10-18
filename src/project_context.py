"""
프로젝트 컨텍스트 관리

프로젝트의 구조, 코딩 스타일, 아키텍처 정보를 저장하고 관리합니다.
Worker들이 이 컨텍스트를 재사용하여 일관성있는 코드를 생성합니다.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class CodingStyle:
    """코딩 스타일 설정"""
    docstring_style: str = "google"  # google, numpy, sphinx
    type_hints: bool = True
    line_length: int = 100
    quote_style: str = "double"  # single, double
    import_style: str = "absolute"  # absolute, relative


@dataclass
class ProjectContext:
    """프로젝트 컨텍스트"""
    project_name: str
    language: str
    framework: Optional[str] = None
    architecture: Optional[str] = None
    key_files: Dict[str, str] = None
    coding_style: CodingStyle = None
    dependencies: List[str] = None
    description: Optional[str] = None

    def __post_init__(self):
        if self.key_files is None:
            self.key_files = {}
        if self.coding_style is None:
            self.coding_style = CodingStyle()
        if self.dependencies is None:
            self.dependencies = []

    def to_dict(self) -> Dict:
        """딕셔너리로 변환"""
        data = asdict(self)
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> "ProjectContext":
        """딕셔너리에서 생성"""
        # CodingStyle 변환
        if "coding_style" in data and isinstance(data["coding_style"], dict):
            data["coding_style"] = CodingStyle(**data["coding_style"])
        return cls(**data)

    def to_prompt_context(self) -> str:
        """
        Worker Agent 프롬프트에 포함할 컨텍스트 생성

        Returns:
            프롬프트용 컨텍스트 문자열
        """
        lines = [
            "\n## 프로젝트 컨텍스트\n",
            f"**프로젝트명**: {self.project_name}",
            f"**언어**: {self.language}",
        ]

        if self.framework:
            lines.append(f"**프레임워크**: {self.framework}")

        if self.architecture:
            lines.append(f"**아키텍처**: {self.architecture}")

        if self.description:
            lines.append(f"**설명**: {self.description}")

        # 주요 파일
        if self.key_files:
            lines.append("\n**주요 파일**:")
            for key, path in self.key_files.items():
                lines.append(f"  - {key}: `{path}`")

        # 코딩 스타일
        lines.append("\n**코딩 스타일**:")
        lines.append(f"  - Docstring: {self.coding_style.docstring_style}")
        lines.append(f"  - Type Hints: {'사용' if self.coding_style.type_hints else '미사용'}")
        lines.append(f"  - Line Length: {self.coding_style.line_length}")
        lines.append(f"  - Quote Style: {self.coding_style.quote_style}")

        # 의존성
        if self.dependencies:
            lines.append("\n**주요 의존성**:")
            for dep in self.dependencies[:10]:  # 최대 10개
                lines.append(f"  - {dep}")

        lines.append("\n**중요**: 위 프로젝트 컨텍스트를 준수하여 일관성있는 코드를 작성하세요.\n")

        return "\n".join(lines)


class ProjectContextManager:
    """프로젝트 컨텍스트 관리자"""

    def __init__(self, context_file: Path = Path(".context.json")):
        """
        Args:
            context_file: 컨텍스트 파일 경로
        """
        self.context_file = context_file
        self._context: Optional[ProjectContext] = None

    def load(self) -> Optional[ProjectContext]:
        """
        컨텍스트 파일 로드

        Returns:
            ProjectContext 또는 None (파일 없을 경우)
        """
        if not self.context_file.exists():
            logger.warning(f"⚠️  프로젝트 컨텍스트 파일이 없습니다: {self.context_file}")
            return None

        try:
            with open(self.context_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self._context = ProjectContext.from_dict(data)
            logger.info(f"✅ 프로젝트 컨텍스트 로드: {self._context.project_name}")
            return self._context

        except Exception as e:
            logger.error(f"❌ 컨텍스트 로드 실패: {e}")
            return None

    def save(self, context: ProjectContext):
        """
        컨텍스트 저장

        Args:
            context: 저장할 컨텍스트
        """
        try:
            with open(self.context_file, 'w', encoding='utf-8') as f:
                json.dump(context.to_dict(), f, indent=2, ensure_ascii=False)

            logger.info(f"✅ 프로젝트 컨텍스트 저장: {self.context_file}")
            self._context = context

        except Exception as e:
            logger.error(f"❌ 컨텍스트 저장 실패: {e}")
            raise

    def get(self) -> Optional[ProjectContext]:
        """
        현재 컨텍스트 반환 (캐시됨)

        Returns:
            ProjectContext 또는 None
        """
        if self._context is None:
            self._context = self.load()
        return self._context

    def create_default(self, project_name: str, language: str = "python") -> ProjectContext:
        """
        기본 컨텍스트 생성

        Args:
            project_name: 프로젝트명
            language: 언어

        Returns:
            생성된 ProjectContext
        """
        context = ProjectContext(
            project_name=project_name,
            language=language,
            framework=None,
            architecture=None,
            key_files={},
            coding_style=CodingStyle(),
            dependencies=[],
            description=f"{project_name} 프로젝트"
        )

        self.save(context)
        return context


def create_better_llm_context() -> ProjectContext:
    """
    better-llm 프로젝트의 컨텍스트 생성

    Returns:
        ProjectContext
    """
    return ProjectContext(
        project_name="better-llm",
        language="python",
        framework="claude-agent-sdk",
        architecture="Worker Tools Architecture",
        key_files={
            "main": "orchestrator.py",
            "tui": "tui.py",
            "manager": "src/manager_agent.py",
            "workers": "src/worker_tools.py",
            "worker_agent": "src/worker_agent.py",
            "models": "src/models.py",
            "config": "config/agent_config.json"
        },
        coding_style=CodingStyle(
            docstring_style="google",
            type_hints=True,
            line_length=100,
            quote_style="double",
            import_style="absolute"
        ),
        dependencies=[
            "claude-agent-sdk",
            "textual",
            "click",
            "python-dotenv"
        ],
        description="그룹 챗 오케스트레이션 시스템 - Manager Agent가 Worker Tools를 호출하여 소프트웨어 개발 작업 자동화"
    )
