"""
TUI 메트릭 패널 토글 기능 단위 테스트

테스트 항목:
- action_toggle_metrics_panel() 메서드 테스트
- apply_metrics_panel_visibility() 메서드 테스트
- 설정 저장/로드 통합 테스트
- 에지 케이스: 설정 저장 실패, 위젯 없음
"""

import pytest
from pathlib import Path
import tempfile
import shutil
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from textual.containers import Container

from src.presentation.tui.tui_app import OrchestratorTUI
from src.presentation.tui.utils.tui_config import TUIConfig, TUISettings


class TestMetricsToggle:
    """메트릭 패널 토글 기능 테스트"""

    @pytest.fixture
    def temp_config_path(self):
        """임시 설정 파일 경로"""
        temp_dir = Path(tempfile.mkdtemp())
        config_path = temp_dir / "test_tui_config.json"
        yield config_path
        # 테스트 후 정리
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    @pytest.fixture
    def mock_tui_app(self):
        """모의 TUI 앱 객체"""
        app = Mock(spec=OrchestratorTUI)
        app.show_metrics_panel = True
        app.settings = TUISettings()
        app.notify = Mock()
        return app

    def test_initial_metrics_panel_state(self):
        """초기 메트릭 패널 상태 확인"""
        # 설정 파일이 없을 때는 기본값 사용
        with patch.object(TUIConfig, "load", return_value=TUISettings()):
            app = OrchestratorTUI()

            # 기본 설정에서는 메트릭 패널이 표시됨
            assert app.show_metrics_panel is True

    def test_metrics_panel_state_from_settings(self, temp_config_path):
        """설정 파일에서 메트릭 패널 상태 로드"""
        # 메트릭 패널을 숨긴 설정 저장
        settings = TUISettings(show_metrics_panel=False)
        TUIConfig.save(settings, config_path=temp_config_path)

        # TUIConfig.load가 해당 경로를 사용하도록 패치
        with patch.object(TUIConfig, "load", return_value=settings):
            app = OrchestratorTUI()
            assert app.show_metrics_panel is False

    @pytest.mark.asyncio
    async def test_action_toggle_metrics_panel_show_to_hide(self, mock_tui_app, temp_config_path):
        """메트릭 패널 토글: 표시 → 숨김"""
        # 초기 상태: 표시
        mock_tui_app.show_metrics_panel = True
        mock_tui_app.settings.show_metrics_panel = True
        mock_tui_app.settings.enable_notifications = True

        # apply_metrics_panel_visibility 모의 메서드
        mock_tui_app.apply_metrics_panel_visibility = Mock()

        # TUIConfig.save를 모의하여 성공 반환
        with patch.object(TUIConfig, "save", return_value=True):
            # action_toggle_metrics_panel 실행
            await OrchestratorTUI.action_toggle_metrics_panel(mock_tui_app)

            # 상태가 토글되었는지 확인
            assert mock_tui_app.show_metrics_panel is False
            assert mock_tui_app.settings.show_metrics_panel is False

            # apply_metrics_panel_visibility가 호출되었는지 확인
            mock_tui_app.apply_metrics_panel_visibility.assert_called_once()

            # 알림이 표시되었는지 확인
            mock_tui_app.notify.assert_called_once()
            call_args = mock_tui_app.notify.call_args
            assert "숨김" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_action_toggle_metrics_panel_hide_to_show(self, mock_tui_app, temp_config_path):
        """메트릭 패널 토글: 숨김 → 표시"""
        # 초기 상태: 숨김
        mock_tui_app.show_metrics_panel = False
        mock_tui_app.settings.show_metrics_panel = False
        mock_tui_app.settings.enable_notifications = True

        # apply_metrics_panel_visibility 모의 메서드
        mock_tui_app.apply_metrics_panel_visibility = Mock()

        # TUIConfig.save를 모의하여 성공 반환
        with patch.object(TUIConfig, "save", return_value=True):
            # action_toggle_metrics_panel 실행
            await OrchestratorTUI.action_toggle_metrics_panel(mock_tui_app)

            # 상태가 토글되었는지 확인
            assert mock_tui_app.show_metrics_panel is True
            assert mock_tui_app.settings.show_metrics_panel is True

            # apply_metrics_panel_visibility가 호출되었는지 확인
            mock_tui_app.apply_metrics_panel_visibility.assert_called_once()

            # 알림이 표시되었는지 확인
            mock_tui_app.notify.assert_called_once()
            call_args = mock_tui_app.notify.call_args
            assert "표시" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_action_toggle_metrics_panel_save_failure(self, mock_tui_app):
        """메트릭 패널 토글: 설정 저장 실패 처리"""
        # 초기 상태: 표시
        mock_tui_app.show_metrics_panel = True
        mock_tui_app.settings.show_metrics_panel = True
        mock_tui_app.settings.notify_on_error = True

        # apply_metrics_panel_visibility 모의 메서드
        mock_tui_app.apply_metrics_panel_visibility = Mock()

        # TUIConfig.save를 모의하여 실패 반환
        with patch.object(TUIConfig, "save", return_value=False):
            # action_toggle_metrics_panel 실행
            await OrchestratorTUI.action_toggle_metrics_panel(mock_tui_app)

            # 상태는 토글되어야 함 (UI는 업데이트됨)
            assert mock_tui_app.show_metrics_panel is False
            assert mock_tui_app.settings.show_metrics_panel is False

            # apply_metrics_panel_visibility가 호출되었는지 확인
            mock_tui_app.apply_metrics_panel_visibility.assert_called_once()

            # 에러 알림이 표시되었는지 확인 (2번 호출: 에러 + 토글)
            assert mock_tui_app.notify.call_count >= 1

    @pytest.mark.asyncio
    async def test_action_toggle_metrics_panel_no_notifications(self, mock_tui_app):
        """메트릭 패널 토글: 알림 비활성화 시 동작"""
        # 초기 상태
        mock_tui_app.show_metrics_panel = True
        mock_tui_app.settings.show_metrics_panel = True
        mock_tui_app.settings.enable_notifications = False

        # apply_metrics_panel_visibility 모의 메서드
        mock_tui_app.apply_metrics_panel_visibility = Mock()

        # TUIConfig.save를 모의하여 성공 반환
        with patch.object(TUIConfig, "save", return_value=True):
            # action_toggle_metrics_panel 실행
            await OrchestratorTUI.action_toggle_metrics_panel(mock_tui_app)

            # 상태가 토글되었는지 확인
            assert mock_tui_app.show_metrics_panel is False

            # 알림이 표시되지 않았는지 확인
            mock_tui_app.notify.assert_not_called()

    def test_apply_metrics_panel_visibility_show(self, mock_tui_app):
        """apply_metrics_panel_visibility: 메트릭 패널 표시"""
        # 모의 컨테이너 생성
        mock_container = Mock(spec=Container)
        mock_container.remove_class = Mock()
        mock_container.add_class = Mock()

        # query_one이 모의 컨테이너를 반환하도록 설정
        mock_tui_app.query_one = Mock(return_value=mock_container)

        # show_metrics_panel을 True로 설정
        mock_tui_app.show_metrics_panel = True

        # apply_metrics_panel_visibility 실행
        OrchestratorTUI.apply_metrics_panel_visibility(mock_tui_app)

        # remove_class("hidden")이 호출되었는지 확인
        mock_container.remove_class.assert_called_once_with("hidden")
        mock_container.add_class.assert_not_called()

    def test_apply_metrics_panel_visibility_hide(self, mock_tui_app):
        """apply_metrics_panel_visibility: 메트릭 패널 숨김"""
        # 모의 컨테이너 생성
        mock_container = Mock(spec=Container)
        mock_container.remove_class = Mock()
        mock_container.add_class = Mock()

        # query_one이 모의 컨테이너를 반환하도록 설정
        mock_tui_app.query_one = Mock(return_value=mock_container)

        # show_metrics_panel을 False로 설정
        mock_tui_app.show_metrics_panel = False

        # apply_metrics_panel_visibility 실행
        OrchestratorTUI.apply_metrics_panel_visibility(mock_tui_app)

        # add_class("hidden")이 호출되었는지 확인
        mock_container.add_class.assert_called_once_with("hidden")
        mock_container.remove_class.assert_not_called()

    def test_apply_metrics_panel_visibility_widget_not_found(self, mock_tui_app):
        """apply_metrics_panel_visibility: 위젯이 없을 때 예외 처리"""
        # query_one이 예외를 발생시키도록 설정
        mock_tui_app.query_one = Mock(side_effect=Exception("Widget not found"))

        # show_metrics_panel을 True로 설정
        mock_tui_app.show_metrics_panel = True

        # 예외가 발생하지 않고 정상적으로 처리되어야 함
        try:
            OrchestratorTUI.apply_metrics_panel_visibility(mock_tui_app)
        except Exception:
            pytest.fail("apply_metrics_panel_visibility should handle exceptions gracefully")

    @pytest.mark.asyncio
    async def test_action_toggle_metrics_panel_exception_handling(self, mock_tui_app):
        """메트릭 패널 토글: 예상치 못한 예외 처리"""
        # 초기 상태
        mock_tui_app.show_metrics_panel = True
        mock_tui_app.settings.show_metrics_panel = True

        # apply_metrics_panel_visibility가 예외를 발생시키도록 설정
        mock_tui_app.apply_metrics_panel_visibility = Mock(
            side_effect=Exception("Unexpected error")
        )

        # TUIConfig.save를 모의하여 성공 반환
        with patch.object(TUIConfig, "save", return_value=True):
            # 예외가 로그에 기록되고 애플리케이션은 계속 실행되어야 함
            try:
                await OrchestratorTUI.action_toggle_metrics_panel(mock_tui_app)
            except Exception:
                pytest.fail("action_toggle_metrics_panel should not raise exceptions")


class TestMetricsToggleIntegration:
    """메트릭 패널 토글 통합 테스트"""

    @pytest.fixture
    def temp_config_path(self):
        """임시 설정 파일 경로"""
        temp_dir = Path(tempfile.mkdtemp())
        config_path = temp_dir / "test_tui_config.json"
        yield config_path
        # 테스트 후 정리
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    @pytest.mark.asyncio
    async def test_toggle_and_reload_settings(self, temp_config_path):
        """토글 후 설정 재로드 통합 테스트"""
        # 초기 설정 생성 (메트릭 패널 표시)
        initial_settings = TUISettings(show_metrics_panel=True)
        TUIConfig.save(initial_settings, config_path=temp_config_path)

        # 설정 로드
        loaded_settings = TUIConfig.load(config_path=temp_config_path)
        assert loaded_settings.show_metrics_panel is True

        # 메트릭 패널을 숨긴 설정으로 변경 및 저장
        loaded_settings.show_metrics_panel = False
        TUIConfig.save(loaded_settings, config_path=temp_config_path)

        # 재로드 및 검증
        reloaded_settings = TUIConfig.load(config_path=temp_config_path)
        assert reloaded_settings.show_metrics_panel is False

        # 다시 표시로 변경
        reloaded_settings.show_metrics_panel = True
        TUIConfig.save(reloaded_settings, config_path=temp_config_path)

        # 최종 검증
        final_settings = TUIConfig.load(config_path=temp_config_path)
        assert final_settings.show_metrics_panel is True

    def test_multiple_toggles(self, temp_config_path):
        """여러 번 토글 후 설정 유지 테스트"""
        settings = TUISettings(show_metrics_panel=True)

        # 10번 토글
        for i in range(10):
            expected_state = i % 2 == 0  # 짝수: False, 홀수: True
            settings.show_metrics_panel = not settings.show_metrics_panel
            TUIConfig.save(settings, config_path=temp_config_path)

            loaded = TUIConfig.load(config_path=temp_config_path)
            assert loaded.show_metrics_panel == settings.show_metrics_panel

    @pytest.mark.asyncio
    async def test_concurrent_setting_changes(self, temp_config_path):
        """다른 설정과 함께 메트릭 패널 설정 변경"""
        # 여러 설정을 함께 변경
        settings = TUISettings(
            theme="light",
            worker_timeout=600,
            show_metrics_panel=False,
            enable_notifications=False,
        )
        TUIConfig.save(settings, config_path=temp_config_path)

        # 로드 및 검증
        loaded = TUIConfig.load(config_path=temp_config_path)
        assert loaded.theme == "light"
        assert loaded.worker_timeout == 600
        assert loaded.show_metrics_panel is False
        assert loaded.enable_notifications is False

        # 메트릭 패널만 변경
        loaded.show_metrics_panel = True
        TUIConfig.save(loaded, config_path=temp_config_path)

        # 재로드 및 검증 (다른 설정은 유지되어야 함)
        reloaded = TUIConfig.load(config_path=temp_config_path)
        assert reloaded.theme == "light"
        assert reloaded.worker_timeout == 600
        assert reloaded.show_metrics_panel is True
        assert reloaded.enable_notifications is False


class TestEdgeCases:
    """에지 케이스 테스트"""

    @pytest.fixture
    def temp_config_path(self):
        """임시 설정 파일 경로"""
        temp_dir = Path(tempfile.mkdtemp())
        config_path = temp_dir / "test_tui_config.json"
        yield config_path
        # 테스트 후 정리
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    def test_missing_show_metrics_panel_field_in_json(self, temp_config_path):
        """JSON 파일에 show_metrics_panel 필드가 없을 때 기본값 사용"""
        # show_metrics_panel 필드 없이 JSON 파일 생성
        import json

        partial_config = {
            "theme": "dark",
            "worker_timeout": 300,
        }

        temp_config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(temp_config_path, "w") as f:
            json.dump(partial_config, f)

        # 로드 시 기본값 사용되어야 함
        settings = TUIConfig.load(config_path=temp_config_path)
        assert settings.show_metrics_panel is True  # 기본값

    @pytest.mark.asyncio
    async def test_toggle_with_corrupted_config(self, temp_config_path):
        """손상된 설정 파일이 있을 때 토글 동작"""
        # 손상된 JSON 파일 생성
        temp_config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(temp_config_path, "w") as f:
            f.write("{ invalid json }")

        # 설정 로드 시 기본값 반환됨
        settings = TUIConfig.load(config_path=temp_config_path)
        assert settings.show_metrics_panel is True

        # 토글 및 저장 (이제 올바른 JSON 파일이 생성됨)
        settings.show_metrics_panel = False
        success = TUIConfig.save(settings, config_path=temp_config_path)
        assert success is True

        # 재로드 및 검증
        reloaded = TUIConfig.load(config_path=temp_config_path)
        assert reloaded.show_metrics_panel is False

    def test_read_only_config_file(self):
        """읽기 전용 설정 파일에 저장 시도"""
        # 쓰기 권한이 없는 경로
        read_only_path = Path("/root/tui_config.json")

        settings = TUISettings(show_metrics_panel=False)
        success = TUIConfig.save(settings, config_path=read_only_path)

        # 실패해야 함
        assert success is False

    @pytest.mark.asyncio
    async def test_toggle_without_initialized_widgets(self):
        """위젯이 초기화되지 않은 상태에서 토글"""
        mock_app = Mock(spec=OrchestratorTUI)
        mock_app.show_metrics_panel = True
        mock_app.settings = TUISettings()
        mock_app.notify = Mock()

        # query_one이 예외를 발생시키도록 설정
        mock_app.query_one = Mock(side_effect=Exception("Widget not initialized"))

        # apply_metrics_panel_visibility 메서드 적용
        mock_app.apply_metrics_panel_visibility = Mock(
            side_effect=OrchestratorTUI.apply_metrics_panel_visibility.__get__(
                mock_app, OrchestratorTUI
            )
        )

        # TUIConfig.save를 모의하여 성공 반환
        with patch.object(TUIConfig, "save", return_value=True):
            # 예외가 발생하지 않아야 함 (graceful handling)
            try:
                await OrchestratorTUI.action_toggle_metrics_panel(mock_app)
            except Exception:
                pytest.fail(
                    "action_toggle_metrics_panel should handle missing widgets gracefully"
                )

            # 상태는 변경되어야 함
            assert mock_app.show_metrics_panel is False
