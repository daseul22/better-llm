"""
TUI UI/UX 개선 사항 테스트

검증 항목:
1. 설정 기본값 (show_worker_status = True)
2. Help 모달 F5 키 바인딩 정보
3. 설정 모달 ScrollableContainer
4. TUI 앱 키 바인딩 (F5 토글)
"""

import pytest
from pathlib import Path
import tempfile
import shutil
from textual.app import App
from textual.containers import ScrollableContainer

from src.presentation.tui.utils.tui_config import TUIConfig, TUISettings
from src.presentation.tui.widgets.help_modal import HelpModal
from src.presentation.tui.widgets.settings_modal import SettingsModal


class TestTUIConfigDefaults:
    """TUISettings 기본값 테스트 - UI/UX 개선 사항"""

    def test_show_worker_status_default_is_true(self):
        """Worker 상태 패널이 기본으로 표시되어야 함 (수정됨)"""
        settings = TUISettings()
        assert settings.show_worker_status is True

    def test_show_metrics_panel_default_is_false(self):
        """메트릭 패널이 기본으로 숨겨져 있어야 함"""
        settings = TUISettings()
        assert settings.show_metrics_panel is False

    def test_show_workflow_panel_default_is_false(self):
        """워크플로우 패널이 기본으로 숨겨져 있어야 함"""
        settings = TUISettings()
        assert settings.show_workflow_panel is False

    def test_all_panel_defaults(self):
        """모든 패널 기본값 종합 검증"""
        settings = TUISettings()

        # Worker 상태만 기본 표시
        assert settings.show_worker_status is True

        # 나머지는 숨김
        assert settings.show_metrics_panel is False
        assert settings.show_workflow_panel is False

    @pytest.fixture
    def temp_config_path(self):
        """임시 설정 파일 경로"""
        temp_dir = Path(tempfile.mkdtemp())
        config_path = temp_dir / "test_tui_config.json"
        yield config_path
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    def test_worker_status_persistence(self, temp_config_path):
        """Worker 상태 설정 저장/로드 테스트"""
        # 기본값으로 저장
        settings = TUISettings()
        assert settings.show_worker_status is True

        TUIConfig.save(settings, config_path=temp_config_path)
        loaded = TUIConfig.load(config_path=temp_config_path)

        assert loaded.show_worker_status is True

    def test_toggle_worker_status_persistence(self, temp_config_path):
        """Worker 상태 토글 후 저장/로드 테스트"""
        # False로 설정
        settings = TUISettings(show_worker_status=False)
        TUIConfig.save(settings, config_path=temp_config_path)

        loaded = TUIConfig.load(config_path=temp_config_path)
        assert loaded.show_worker_status is False

        # 다시 True로 설정
        settings.show_worker_status = True
        TUIConfig.save(settings, config_path=temp_config_path)

        loaded = TUIConfig.load(config_path=temp_config_path)
        assert loaded.show_worker_status is True


class TestHelpModalF5KeyBinding:
    """Help 모달 F5 키 바인딩 정보 테스트"""

    def test_help_modal_contains_f5_binding(self):
        """Help 모달에 F5 키 바인딩 정보가 포함되어 있는지 확인"""
        # 소스 코드에서 직접 확인
        from src.presentation.tui.widgets.help_modal import HelpModal
        import inspect

        source = inspect.getsource(HelpModal._generate_help_content)

        # F5 키 바인딩 정보 확인
        assert '"F5"' in source or "'F5'" in source
        assert "Worker" in source

    def test_help_modal_key_bindings_complete(self):
        """Help 모달에 모든 키 바인딩이 포함되어 있는지 확인"""
        from src.presentation.tui.widgets.help_modal import HelpModal
        import inspect

        source = inspect.getsource(HelpModal._generate_help_content)

        # 주요 키 바인딩 확인
        expected_keys = [
            "Enter",
            "Shift+Enter",
            "Ctrl+C",
            "Ctrl+N",
            "Ctrl+S",
            "Ctrl+L",
            "Ctrl+F",
            "F1",
            "F2",
            "F3",
            "F4",
            "F5",  # 새로 추가된 키 바인딩
            "ESC",
        ]

        for key in expected_keys:
            assert key in source, f"키 바인딩 '{key}'가 Help 모달 소스에 없습니다"


class TestSettingsModalScrollable:
    """설정 모달 스크롤 기능 테스트"""

    def test_settings_modal_has_scrollable_container(self):
        """설정 모달에 ScrollableContainer가 있는지 확인"""
        # 소스 코드에서 직접 확인
        from src.presentation.tui.widgets.settings_modal import SettingsModal
        import inspect

        source = inspect.getsource(SettingsModal.compose)

        # ScrollableContainer 사용 확인
        assert "ScrollableContainer" in source, \
            "SettingsModal.compose()에 ScrollableContainer가 없습니다"
        assert "settings-content" in source, \
            "ScrollableContainer의 ID가 설정되지 않았습니다"

    def test_settings_modal_css_height(self):
        """설정 모달 CSS에 height 설정이 있는지 확인"""
        modal = SettingsModal(TUISettings())

        # CSS에 height가 설정되어 있는지 확인
        assert "#settings-content" in modal.CSS
        assert "height:" in modal.CSS

        # settings-content에 height가 있는지 확인
        css_lines = modal.CSS.split('\n')
        in_settings_content = False
        has_height = False

        for line in css_lines:
            if "#settings-content" in line:
                in_settings_content = True
            if in_settings_content and "height:" in line:
                has_height = True
                break
            if in_settings_content and "}" in line:
                break

        assert has_height, "#settings-content에 height 설정이 없습니다"

    def test_settings_modal_scrollable_id(self):
        """ScrollableContainer의 ID가 settings-content인지 확인"""
        # 소스 코드에서 직접 확인
        from src.presentation.tui.widgets.settings_modal import SettingsModal
        import inspect

        source = inspect.getsource(SettingsModal.compose)

        # ID가 settings-content인 ScrollableContainer 확인
        assert 'ScrollableContainer(id="settings-content")' in source or \
               "ScrollableContainer(id='settings-content')" in source, \
            "ID가 'settings-content'인 ScrollableContainer가 없습니다"


class TestSettingsModalWorkerStatusSwitch:
    """설정 모달 Worker 상태 스위치 테스트"""

    def test_settings_modal_has_worker_status_switch(self):
        """설정 모달에 Worker 상태 스위치가 있는지 확인"""
        # 소스 코드에서 직접 확인
        from src.presentation.tui.widgets import settings_modal
        import inspect

        source = inspect.getsource(settings_modal.SettingsModal.compose)
        assert "show-worker-status" in source
        assert 'Switch' in source

    def test_worker_status_switch_default_value(self):
        """Worker 상태 스위치의 기본값이 True인지 확인"""
        settings = TUISettings(show_worker_status=True)
        modal = SettingsModal(settings)

        # settings 객체의 값 확인
        assert modal.settings.show_worker_status is True

    def test_worker_status_switch_false_value(self):
        """Worker 상태 스위치가 False 값을 올바르게 반영하는지 확인"""
        settings = TUISettings(show_worker_status=False)
        modal = SettingsModal(settings)

        assert modal.settings.show_worker_status is False


class TestTUIAppKeyBindings:
    """TUI 앱 키 바인딩 테스트"""

    def test_f5_key_binding_exists(self):
        """F5 키 바인딩이 존재하는지 확인"""
        from src.presentation.tui.tui_app import OrchestratorTUI
        import inspect

        # BINDINGS 속성 확인
        assert hasattr(OrchestratorTUI, 'BINDINGS')

        # F5 키 바인딩 확인
        bindings = OrchestratorTUI.BINDINGS
        f5_binding = None

        for binding in bindings:
            if binding.key == "f5":
                f5_binding = binding
                break

        assert f5_binding is not None, "F5 키 바인딩이 없습니다"
        assert f5_binding.action == "toggle_worker_status"

    def test_toggle_worker_status_action_exists(self):
        """toggle_worker_status 액션이 존재하는지 확인"""
        from src.presentation.tui.tui_app import OrchestratorTUI

        assert hasattr(OrchestratorTUI, 'action_toggle_worker_status')

        # 메서드가 async인지 확인
        import inspect
        assert inspect.iscoroutinefunction(OrchestratorTUI.action_toggle_worker_status)

    def test_all_panel_toggle_actions_exist(self):
        """모든 패널 토글 액션이 존재하는지 확인"""
        from src.presentation.tui.tui_app import OrchestratorTUI

        required_actions = [
            'action_toggle_metrics_panel',
            'action_toggle_workflow_panel',
            'action_toggle_worker_status',
        ]

        for action_name in required_actions:
            assert hasattr(OrchestratorTUI, action_name), \
                f"{action_name} 액션이 없습니다"


class TestLayoutAndCSS:
    """레이아웃 및 CSS 테스트"""

    def test_worker_status_container_css(self):
        """Worker 상태 컨테이너 CSS가 정의되어 있는지 확인"""
        from src.presentation.tui.tui_app import OrchestratorTUI

        css = OrchestratorTUI.CSS

        # worker-status-container CSS 확인
        assert "#worker-status-container" in css
        assert "#worker-status" in css

    def test_hidden_class_exists(self):
        """hidden 클래스가 CSS에 정의되어 있는지 확인"""
        from src.presentation.tui.tui_app import OrchestratorTUI

        css = OrchestratorTUI.CSS

        # .hidden 클래스 확인
        assert ".hidden" in css
        assert "display: none" in css

    def test_metrics_container_css(self):
        """메트릭 컨테이너 CSS가 정의되어 있는지 확인"""
        from src.presentation.tui.tui_app import OrchestratorTUI

        css = OrchestratorTUI.CSS

        assert "#metrics-container" in css
        assert "#metrics-panel" in css

    def test_workflow_container_css(self):
        """워크플로우 컨테이너 CSS가 정의되어 있는지 확인"""
        from src.presentation.tui.tui_app import OrchestratorTUI

        css = OrchestratorTUI.CSS

        assert "#workflow-container" in css


class TestApplyVisibilityMethods:
    """패널 가시성 적용 메서드 테스트"""

    def test_apply_worker_status_visibility_method_exists(self):
        """apply_worker_status_visibility 메서드가 존재하는지 확인"""
        from src.presentation.tui.tui_app import OrchestratorTUI

        assert hasattr(OrchestratorTUI, 'apply_worker_status_visibility')

    def test_apply_metrics_panel_visibility_method_exists(self):
        """apply_metrics_panel_visibility 메서드가 존재하는지 확인"""
        from src.presentation.tui.tui_app import OrchestratorTUI

        assert hasattr(OrchestratorTUI, 'apply_metrics_panel_visibility')

    def test_apply_workflow_panel_visibility_method_exists(self):
        """apply_workflow_panel_visibility 메서드가 존재하는지 확인"""
        from src.presentation.tui.tui_app import OrchestratorTUI

        assert hasattr(OrchestratorTUI, 'apply_workflow_panel_visibility')


class TestIntegration:
    """통합 테스트"""

    @pytest.fixture
    def temp_config_path(self):
        """임시 설정 파일 경로"""
        temp_dir = Path(tempfile.mkdtemp())
        config_path = temp_dir / "test_tui_config.json"
        yield config_path
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    def test_config_to_settings_modal_integration(self, temp_config_path):
        """설정 파일 -> 설정 모달 통합 테스트"""
        # 설정 저장
        original = TUISettings(
            show_worker_status=True,
            show_metrics_panel=False,
            show_workflow_panel=False,
        )
        TUIConfig.save(original, config_path=temp_config_path)

        # 설정 로드
        loaded = TUIConfig.load(config_path=temp_config_path)

        # 설정 모달 생성
        modal = SettingsModal(loaded)

        # 모달의 설정 확인
        assert modal.settings.show_worker_status is True
        assert modal.settings.show_metrics_panel is False
        assert modal.settings.show_workflow_panel is False

    def test_default_workflow(self, temp_config_path):
        """기본 워크플로우: 설정 로드 -> 앱 초기화"""
        # 기본 설정 로드
        settings = TUIConfig.load(config_path=temp_config_path)

        # 기본값 확인
        assert settings.show_worker_status is True
        assert settings.show_metrics_panel is False
        assert settings.show_workflow_panel is False

        # 이 설정으로 앱이 초기화될 때 올바른 상태를 가져야 함
        # (실제 앱 테스트는 통합 테스트에서 수행)
