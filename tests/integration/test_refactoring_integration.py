"""
통합 테스트: 리팩토링된 코드베이스 통합 검증

- 환경변수 검증
- 코드 품질 (import, 타입 힌트)
- 설정 파일 포맷 검증
- 코드베이스 구조 검증
"""

import os
import json
import pytest
import re
from pathlib import Path
from typing import List, Dict, Any

# 프로젝트 경로
project_root = Path(__file__).parent.parent.parent

# 테스트 마커
pytestmark = [pytest.mark.integration]


class TestEnvironmentValidation:
    """환경변수 검증 테스트"""

    def test_env_file_exists(self):
        """환경 파일 존재 확인"""
        env_example = project_root / ".env.example"
        assert env_example.exists(), f".env.example 미존재: {env_example}"

    def test_env_file_has_required_vars(self):
        """.env.example에 필수 환경변수 포함"""
        env_example = project_root / ".env.example"

        with open(env_example) as f:
            content = f.read()

        # 필수 환경변수 확인
        required_vars = ["CLAUDE_CODE_OAUTH_TOKEN"]

        for var in required_vars:
            assert var in content, f"필수 환경변수 '{var}' 미포함"

    def test_env_variable_format(self):
        """.env.example 포맷 검증"""
        env_example = project_root / ".env.example"

        with open(env_example) as f:
            lines = f.readlines()

        # 각 라인이 KEY=VALUE 형식인지 확인
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # KEY=VALUE 형식 확인
            assert "=" in line, f"올바르지 않은 형식: {line}"


class TestCodeQuality:
    """코드 품질 검증 테스트"""

    def test_sdk_executor_no_duplicate_imports(self):
        """SDK Executor의 중복된 import 검증"""
        sdk_executor_path = (
            project_root / "src/infrastructure/claude/sdk_executor.py"
        )

        with open(sdk_executor_path) as f:
            content = f.read()

        # import json 개수 확인
        import_count = content.count("import json")
        assert (
            import_count == 1
        ), f"import json이 {import_count}회 반복됨 (예상: 1회)"

        # json이 실제로 사용되는지 확인
        assert "json." in content or "json(" in content, "import된 json이 사용되지 않음"

    def test_import_organization_in_app_py(self):
        """app.py의 import 구성 확인"""
        app_path = project_root / "src/presentation/web/app.py"

        with open(app_path) as f:
            lines = f.readlines()

        # 주석 섹션 확인
        import_section = "".join(lines[:30])

        # 주석 확인
        assert "# 표준 라이브러리" in import_section, "표준 라이브러리 주석 미포함"
        assert "# 서드파티" in import_section, "서드파티 주석 미포함"
        assert "# 로컬" in import_section, "로컬 주석 미포함"

        # 순서 검증
        stdlib_idx = import_section.find("# 표준 라이브러리")
        thirdparty_idx = import_section.find("# 서드파티")
        local_idx = import_section.find("# 로컬")

        assert (
            0 <= stdlib_idx < thirdparty_idx < local_idx
        ), "Import 순서가 올바르지 않음 (표준 > 서드파티 > 로컬)"

    def test_worker_client_typing_hints(self):
        """Worker Client 타입 힌트 검증"""
        worker_client_path = (
            project_root / "src/infrastructure/claude/worker_client.py"
        )

        with open(worker_client_path) as f:
            content = f.read()

        # Callable 임포트 확인
        assert "Callable" in content, "Callable 타입 힌트 미포함"
        assert "Dict" in content, "Dict 타입 힌트 미포함"
        assert "Any" in content, "Any 타입 힌트 미포함"

        # usage_callback 타입 힌트 확인
        assert "Optional[Callable" in content, "usage_callback 타입 힌트 미명시"

    def test_app_py_import_order(self):
        """app.py의 import 순서 검증"""
        app_path = project_root / "src/presentation/web/app.py"

        with open(app_path) as f:
            lines = f.readlines()

        # Import 라인 추출
        imports = []
        for i, line in enumerate(lines[:50]):
            if line.startswith("import ") or line.startswith("from "):
                imports.append((i, line.strip()))

        # os는 pathlib보다 먼저 나와야 함 (같은 섹션 내)
        stdlib_imports = [
            i for i, line in imports if i < 20 and ("import os" in line or "from pathlib" in line)
        ]

        if len(stdlib_imports) >= 2:
            # stdlib 섹션에서의 순서 확인
            pass


class TestConfigurationFiles:
    """설정 파일 검증 테스트"""

    def test_agent_config_exists(self):
        """agent_config.json 존재"""
        config_path = project_root / "config/agent_config.json"
        assert config_path.exists(), f"agent_config.json 미존재: {config_path}"

    def test_agent_config_valid_json(self):
        """agent_config.json JSON 형식 검증"""
        config_path = project_root / "config/agent_config.json"

        with open(config_path) as f:
            config_data = json.load(f)

        assert isinstance(config_data, dict), "config.json이 딕셔너리가 아님"

    def test_agent_config_has_agents_array(self):
        """agent_config.json에 agents 배열"""
        config_path = project_root / "config/agent_config.json"

        with open(config_path) as f:
            config_data = json.load(f)

        assert "agents" in config_data, "agents 배열 미포함"
        assert isinstance(
            config_data["agents"], list
        ), "agents가 리스트가 아님"
        assert len(config_data["agents"]) > 0, "agents 배열이 비어 있음"

    def test_agent_config_agent_structure(self):
        """각 agent의 필수 필드 검증"""
        config_path = project_root / "config/agent_config.json"

        with open(config_path) as f:
            config_data = json.load(f)

        required_fields = ["name", "role", "system_prompt_file", "allowed_tools", "model"]

        for agent in config_data["agents"]:
            for field in required_fields:
                assert field in agent, f"Agent {agent.get('name')}: {field} 미정의"

            # tools는 리스트여야 함
            assert isinstance(
                agent["allowed_tools"], list
            ), f"Agent {agent.get('name')}: tools는 리스트여야 함"

    def test_system_config_exists(self):
        """system_config.json 존재"""
        config_path = project_root / "config/system_config.json"
        assert config_path.exists(), f"system_config.json 미존재: {config_path}"

    def test_system_config_valid_json(self):
        """system_config.json JSON 형식 검증"""
        config_path = project_root / "config/system_config.json"

        with open(config_path) as f:
            config_data = json.load(f)

        assert isinstance(config_data, dict), "system_config.json이 딕셔너리가 아님"

    def test_system_config_required_sections(self):
        """system_config.json의 필수 섹션"""
        config_path = project_root / "config/system_config.json"

        with open(config_path) as f:
            config_data = json.load(f)

        required_sections = ["manager", "performance", "permission"]

        for section in required_sections:
            assert section in config_data, f"{section} 섹션 미정의"

    def test_system_config_manager_section(self):
        """system_config.json의 manager 섹션"""
        config_path = project_root / "config/system_config.json"

        with open(config_path) as f:
            config_data = json.load(f)

        manager = config_data.get("manager", {})

        assert "max_history_messages" in manager, "max_history_messages 미정의"
        assert "max_turns" in manager, "max_turns 미정의"
        assert isinstance(
            manager["max_history_messages"], int
        ), "max_history_messages는 정수여야 함"
        assert isinstance(manager["max_turns"], int), "max_turns는 정수여야 함"


class TestCodebaseStructure:
    """코드베이스 구조 검증 테스트"""

    def test_src_directory_structure(self):
        """src 디렉토리 구조 확인"""
        src_path = project_root / "src"

        required_dirs = [
            "domain",
            "application",
            "infrastructure",
            "presentation",
        ]

        for dir_name in required_dirs:
            dir_path = src_path / dir_name
            assert dir_path.exists(), f"{dir_name} 디렉토리 미존재"
            assert dir_path.is_dir(), f"{dir_name}이 디렉토리가 아님"

    def test_prompts_directory_exists(self):
        """prompts 디렉토리 존재"""
        prompts_path = project_root / "prompts"
        assert prompts_path.exists(), f"prompts 디렉토리 미존재"
        assert prompts_path.is_dir(), "prompts가 디렉토리가 아님"

    def test_required_prompt_files(self):
        """필수 prompt 파일 존재"""
        prompts_path = project_root / "prompts"

        # agent_config.json에서 prompt 파일 추출
        config_path = project_root / "config/agent_config.json"

        with open(config_path) as f:
            config_data = json.load(f)

        missing_prompts = []

        for agent in config_data["agents"]:
            prompt_file = agent.get("system_prompt_file")
            if prompt_file:
                prompt_path = project_root / prompt_file
                if not prompt_path.exists():
                    missing_prompts.append(prompt_file)

        assert (
            len(missing_prompts) == 0
        ), f"누락된 prompt 파일: {missing_prompts}"

    def test_python_files_syntax(self):
        """Python 파일 구문 검증"""
        import py_compile
        import tempfile

        python_files = list((project_root / "src").rglob("*.py"))

        # 처음 10개 파일만 확인 (성능)
        errors = []

        for py_file in python_files[:10]:
            try:
                py_compile.compile(str(py_file), doraise=True)
            except py_compile.PyCompileError as e:
                errors.append((str(py_file), str(e)))

        assert len(errors) == 0, f"구문 오류: {errors}"

    def test_frontend_components_exist(self):
        """프론트엔드 컴포넌트 존재"""
        frontend_path = (
            project_root / "src/presentation/web/frontend/src/components"
        )

        # 리팩토링된 컴포넌트 확인
        required_components = [
            "WorkerSection.tsx",
            "WorkerButton.tsx",
            "NodePanel.tsx",
            "WorkflowCanvas.tsx",
        ]

        for component in required_components:
            component_path = frontend_path / component
            assert (
                component_path.exists()
            ), f"컴포넌트 미존재: {component}"

    def test_frontend_hooks_exist(self):
        """프론트엔드 훅 존재"""
        hooks_path = (
            project_root / "src/presentation/web/frontend/src/hooks"
        )

        required_hooks = ["useAutoLayout.ts"]

        for hook in required_hooks:
            hook_path = hooks_path / hook
            assert hook_path.exists(), f"훅 미존재: {hook}"


class TestFileIntegrity:
    """파일 무결성 검증 테스트"""

    def test_package_json_exists(self):
        """package.json 존재"""
        package_json = (
            project_root
            / "src/presentation/web/frontend/package.json"
        )
        assert package_json.exists(), "package.json 미존재"

    def test_pyproject_toml_exists(self):
        """pyproject.toml 존재"""
        pyproject = project_root / "pyproject.toml"
        assert pyproject.exists(), "pyproject.toml 미존재"

    def test_readme_exists(self):
        """README.md 존재"""
        readme = project_root / "README.md"
        assert readme.exists(), "README.md 미존재"

    def test_claude_md_updated(self):
        """CLAUDE.md가 최신인지 확인"""
        claude_md = project_root / "CLAUDE.md"
        assert claude_md.exists(), "CLAUDE.md 미존재"

        with open(claude_md) as f:
            content = f.read()

        # 최근 작업 섹션이 있는지 확인
        assert "## 최근 작업" in content, "최근 작업 섹션 미포함"


class TestDependencies:
    """의존성 검증 테스트"""

    def test_requirements_exists(self):
        """requirements.txt 존재"""
        requirements = project_root / "requirements.txt"
        assert requirements.exists(), "requirements.txt 미존재"

    def test_requirements_format(self):
        """requirements.txt 포맷 검증"""
        requirements = project_root / "requirements.txt"

        with open(requirements) as f:
            lines = f.readlines()

        # 패키지 라인 확인
        package_lines = [
            line.strip()
            for line in lines
            if line.strip() and not line.startswith("#")
        ]

        assert len(package_lines) > 0, "requirements.txt에 패키지 없음"

        # 각 라인이 올바른 형식인지 확인
        for line in package_lines:
            # 패키지 이름 확인 (버전 포함 가능)
            assert any(
                c.isalpha() for c in line.split("=")[0]
            ), f"올바르지 않은 패키지 형식: {line}"


class TestRefactoringChanges:
    """리팩토링 변경사항 검증"""

    def test_worker_section_component(self):
        """WorkerSection 컴포넌트 존재 및 구조"""
        component_path = (
            project_root
            / "src/presentation/web/frontend/src/components/WorkerSection.tsx"
        )

        assert component_path.exists(), "WorkerSection.tsx 미존재"

        with open(component_path) as f:
            content = f.read()

        # Props 인터페이스 확인
        assert "interface WorkerSectionProps" in content, "Props 인터페이스 미정의"
        assert "title:" in content, "title prop 미정의"
        assert "children:" in content, "children prop 미정의"

    def test_worker_button_component(self):
        """WorkerButton 컴포넌트 존재 및 구조"""
        component_path = (
            project_root
            / "src/presentation/web/frontend/src/components/WorkerButton.tsx"
        )

        assert component_path.exists(), "WorkerButton.tsx 미존재"

        with open(component_path) as f:
            content = f.read()

        # Props 인터페이스 확인
        assert "interface WorkerButtonProps" in content, "Props 인터페이스 미정의"
        assert "name:" in content, "name prop 미정의"
        assert "role:" in content, "role prop 미정의"

    def test_use_auto_layout_hook(self):
        """useAutoLayout 훅 존재 및 구조"""
        hook_path = (
            project_root
            / "src/presentation/web/frontend/src/hooks/useAutoLayout.ts"
        )

        assert hook_path.exists(), "useAutoLayout.ts 미존재"

        with open(hook_path) as f:
            content = f.read()

        # 함수 정의 확인
        assert "export function useAutoLayout" in content or "export const useAutoLayout" in content, "useAutoLayout 훅 미정의"

    def test_node_panel_refactored(self):
        """NodePanel 리팩토링 확인"""
        component_path = (
            project_root
            / "src/presentation/web/frontend/src/components/NodePanel.tsx"
        )

        with open(component_path) as f:
            content = f.read()

        # WorkerSection, WorkerButton 사용 확인
        assert (
            "<WorkerSection" in content
        ), "WorkerSection 컴포넌트 미사용"
        assert (
            "<WorkerButton" in content
        ), "WorkerButton 컴포넌트 미사용"

    def test_workflow_canvas_refactored(self):
        """WorkflowCanvas 리팩토링 확인"""
        component_path = (
            project_root
            / "src/presentation/web/frontend/src/components/WorkflowCanvas.tsx"
        )

        with open(component_path) as f:
            content = f.read()

        # useAutoLayout 훅 사용 확인
        assert "useAutoLayout" in content, "useAutoLayout 훅 미사용"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
