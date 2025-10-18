"""
프로젝트 컨텍스트 자동 분석

작업공간의 코드 구조를 분석하여 ProjectContext를 생성합니다.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Set
from collections import Counter

from .context import ProjectContext, CodingStyle


class ProjectContextAnalyzer:
    """
    프로젝트 구조를 분석하여 컨텍스트를 자동 생성

    분석 항목:
    - 언어 감지 (파일 확장자 기반)
    - 프레임워크 감지 (의존성 파일)
    - 아키텍처 패턴 감지 (디렉토리 구조)
    - 주요 파일 식별
    - 의존성 파싱
    - 코딩 스타일 추론
    """

    # 언어별 확장자 매핑
    LANGUAGE_EXTENSIONS = {
        'python': {'.py', '.pyw', '.pyx'},
        'javascript': {'.js', '.mjs', '.cjs'},
        'typescript': {'.ts', '.tsx'},
        'go': {'.go'},
        'rust': {'.rs'},
        'java': {'.java'},
        'kotlin': {'.kt', '.kts'},
        'c': {'.c', '.h'},
        'cpp': {'.cpp', '.hpp', '.cc', '.hh', '.cxx'},
        'ruby': {'.rb'},
        'php': {'.php'},
    }

    # 프레임워크 감지 패턴 (의존성 파일 기반)
    FRAMEWORK_PATTERNS = {
        'requirements.txt': {
            'django': 'Django',
            'flask': 'Flask',
            'fastapi': 'FastAPI',
            'claude-agent-sdk': 'Claude Agent SDK',
            'anthropic': 'Anthropic API',
            'textual': 'Textual TUI',
        },
        'package.json': {
            'react': 'React',
            'vue': 'Vue.js',
            'next': 'Next.js',
            'express': 'Express',
            'nestjs': 'NestJS',
        },
        'go.mod': {
            'gin': 'Gin',
            'fiber': 'Fiber',
            'echo': 'Echo',
        }
    }

    # 아키텍처 패턴 (디렉토리 구조 기반)
    ARCHITECTURE_PATTERNS = {
        ('domain', 'application', 'infrastructure', 'presentation'): 'Clean Architecture (4-Layer)',
        ('domain', 'application', 'infrastructure'): 'Clean Architecture (3-Layer)',
        ('models', 'views', 'controllers'): 'MVC',
        ('components', 'pages', 'app'): 'Next.js App Router',
        ('src', 'tests', 'docs'): 'Standard Layout',
    }

    def __init__(self, project_root: Path):
        """
        Args:
            project_root: 프로젝트 루트 디렉토리
        """
        self.project_root = project_root
        self.ignore_dirs = {
            '.git', '.venv', 'venv', 'env', '__pycache__',
            'node_modules', '.pytest_cache', '.mypy_cache',
            'dist', 'build', '.idea', '.vscode', 'sessions'
        }

    def analyze(self) -> ProjectContext:
        """
        프로젝트를 분석하여 컨텍스트 생성

        Returns:
            ProjectContext 객체
        """
        # 1. 기본 정보
        project_name = self.project_root.name

        # 2. 언어 감지
        language = self._detect_language()

        # 3. 프레임워크 감지
        framework = self._detect_framework()

        # 4. 아키텍처 감지
        architecture = self._detect_architecture()

        # 5. 주요 파일 식별
        key_files = self._identify_key_files()

        # 6. 의존성 파싱
        dependencies = self._parse_dependencies()

        # 7. 코딩 스타일 추론
        coding_style = self._infer_coding_style()

        # 8. 설명 생성
        description = self._generate_description(language, framework, architecture)

        # ProjectContext 생성
        coding_style_dict = {}
        if coding_style:
            coding_style_dict = {
                'docstring_style': coding_style.docstring_style,
                'type_hints': coding_style.type_hints,
                'line_length': coding_style.line_length,
                'quote_style': coding_style.quote_style,
                'import_style': coding_style.import_style
            }

        context_dict = {
            'project_name': project_name,
            'language': language,
            'framework': framework,
            'architecture': architecture,
            'key_files': key_files,
            'coding_style': coding_style_dict,
            'dependencies': dependencies,
            'description': description
        }

        # testing 정보 추가 (pytest 있으면)
        if 'pytest' in dependencies:
            test_files = list(self.project_root.glob('test_*.py'))
            if test_files:
                context_dict['testing'] = {
                    'framework': 'pytest',
                    'integration_tests': test_files[0].name
                }

        return ProjectContext.from_dict(context_dict)

    def _detect_language(self) -> str:
        """
        파일 확장자를 기반으로 주 언어 감지

        Returns:
            언어 이름 (예: "python", "javascript")
        """
        extension_counts = Counter()

        for file_path in self.project_root.rglob('*'):
            if file_path.is_file() and not self._should_ignore(file_path):
                ext = file_path.suffix.lower()
                for lang, extensions in self.LANGUAGE_EXTENSIONS.items():
                    if ext in extensions:
                        extension_counts[lang] += 1
                        break

        if not extension_counts:
            return 'unknown'

        # 가장 많은 파일 수를 가진 언어
        return extension_counts.most_common(1)[0][0]

    def _detect_framework(self) -> str:
        """
        의존성 파일을 기반으로 프레임워크 감지

        Returns:
            프레임워크 이름 (예: "Django", "FastAPI")
        """
        frameworks = []

        for dep_file, patterns in self.FRAMEWORK_PATTERNS.items():
            dep_path = self.project_root / dep_file
            if dep_path.exists():
                try:
                    content = dep_path.read_text(encoding='utf-8').lower()
                    for pattern, framework in patterns.items():
                        if pattern in content:
                            frameworks.append(framework)
                except Exception:
                    continue

        # 중복 제거 및 정렬
        frameworks = sorted(set(frameworks))

        if not frameworks:
            return 'unknown'

        # 여러 프레임워크가 감지되면 콤마로 구분
        return ', '.join(frameworks)

    def _detect_architecture(self) -> str:
        """
        디렉토리 구조를 기반으로 아키텍처 패턴 감지

        Returns:
            아키텍처 이름 (예: "Clean Architecture (4-Layer)")
        """
        # src 디렉토리 우선 확인
        src_dir = self.project_root / 'src'
        search_dir = src_dir if src_dir.exists() else self.project_root

        # 서브디렉토리 이름 수집
        subdirs = {
            d.name for d in search_dir.iterdir()
            if d.is_dir() and not self._should_ignore(d)
        }

        # 패턴 매칭
        for pattern_dirs, architecture in self.ARCHITECTURE_PATTERNS.items():
            if all(d in subdirs for d in pattern_dirs):
                return architecture

        return 'Custom'

    def _identify_key_files(self) -> Dict:
        """
        주요 파일 식별

        Returns:
            주요 파일 경로 딕셔너리
        """
        key_files = {}

        # Entry points
        entry_points = {}
        for name in ['main.py', 'app.py', 'server.py', 'orchestrator.py', 'tui.py']:
            path = self.project_root / name
            if path.exists():
                entry_points[path.stem] = name

        if entry_points:
            key_files['entry_points'] = entry_points

        # Clean Architecture 레이어
        src_dir = self.project_root / 'src'
        if src_dir.exists():
            layers = ['domain', 'application', 'infrastructure', 'presentation']
            for layer in layers:
                layer_dir = src_dir / layer
                if layer_dir.exists():
                    key_files[layer] = f'src/{layer}/'

        # Config 파일
        config_dir = self.project_root / 'config'
        if config_dir.exists():
            config_files = list(config_dir.glob('*.json'))
            if config_files:
                if len(config_files) == 1:
                    key_files['config'] = f'config/{config_files[0].name}'
                else:
                    key_files['config'] = {f.stem: f'config/{f.name}' for f in config_files}

        return key_files

    def _parse_dependencies(self) -> List[str]:
        """
        의존성 파일 파싱

        Returns:
            의존성 패키지 리스트
        """
        dependencies = set()

        # requirements.txt
        req_file = self.project_root / 'requirements.txt'
        if req_file.exists():
            try:
                content = req_file.read_text(encoding='utf-8')
                for line in content.splitlines():
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # 패키지명만 추출 (>= 제거)
                        pkg = line.split('>=')[0].split('==')[0].split('<')[0].strip()
                        dependencies.add(pkg)
            except Exception:
                pass

        # package.json
        pkg_file = self.project_root / 'package.json'
        if pkg_file.exists():
            try:
                data = json.loads(pkg_file.read_text(encoding='utf-8'))
                if 'dependencies' in data:
                    dependencies.update(data['dependencies'].keys())
                if 'devDependencies' in data:
                    dependencies.update(data['devDependencies'].keys())
            except Exception:
                pass

        return sorted(dependencies)

    def _infer_coding_style(self) -> Optional[CodingStyle]:
        """
        코드 샘플을 분석하여 코딩 스타일 추론

        Returns:
            CodingStyle 객체 또는 None
        """
        # Python 프로젝트인 경우
        python_files = list(self.project_root.glob('**/*.py'))
        if not python_files:
            return None

        # 샘플 파일 읽기 (최대 5개)
        samples = []
        for py_file in python_files[:5]:
            if self._should_ignore(py_file):
                continue
            try:
                samples.append(py_file.read_text(encoding='utf-8'))
            except Exception:
                continue

        if not samples:
            return CodingStyle()

        # Quote style 감지
        single_quotes = sum(s.count("'") for s in samples)
        double_quotes = sum(s.count('"') for s in samples)
        quote_style = 'double' if double_quotes > single_quotes else 'single'

        # Type hints 감지
        type_hints = any('def ' in s and '->' in s for s in samples)

        # Docstring style 감지 (간단히 Google/NumPy 감지)
        has_args_section = any('Args:' in s or 'Arguments:' in s for s in samples)
        docstring_style = 'google' if has_args_section else 'numpy'

        return CodingStyle(
            docstring_style=docstring_style,
            type_hints=type_hints,
            line_length=100,  # 기본값
            quote_style=quote_style,
            import_style='absolute'  # 기본값
        )

    def _generate_description(self, language: str, framework: str, architecture: str) -> str:
        """
        프로젝트 설명 생성

        Returns:
            프로젝트 설명 문자열
        """
        parts = [self.project_root.name]

        if language != 'unknown':
            parts.append(f'{language.capitalize()} 프로젝트')

        if framework != 'unknown':
            parts.append(f'{framework} 기반')

        if architecture != 'Custom':
            parts.append(f'{architecture} 아키텍처')

        return ' - '.join(parts)

    def _should_ignore(self, path: Path) -> bool:
        """
        경로를 무시해야 하는지 확인

        Args:
            path: 확인할 경로

        Returns:
            무시해야 하면 True
        """
        # 절대 경로로 변환
        try:
            rel_path = path.relative_to(self.project_root)
        except ValueError:
            return True

        # ignore_dirs에 포함된 디렉토리인지 확인
        for part in rel_path.parts:
            if part in self.ignore_dirs:
                return True

        return False
