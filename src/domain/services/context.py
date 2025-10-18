"""
프로젝트 컨텍스트 도메인 서비스

ProjectContext: 프로젝트 메타데이터 및 코딩 스타일
CodingStyle: 코딩 스타일 설정
"""

from dataclasses import dataclass, asdict
from typing import Dict, List, Optional


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
    """
    프로젝트 컨텍스트 도메인 모델

    프로젝트의 구조, 코딩 스타일, 아키텍처 정보를 저장합니다.
    Worker들이 이 컨텍스트를 재사용하여 일관성있는 코드를 생성합니다.
    """
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
