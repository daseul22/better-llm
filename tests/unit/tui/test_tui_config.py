"""
TUIConfig 및 TUISettings 클래스 단위 테스트

테스트 항목:
- 기본 설정 로드
- 설정 파일 저장 및 로드
- 설정 리셋
- JSON 직렬화/역직렬화
- 잘못된 설정 처리
"""

import pytest
from pathlib import Path
import tempfile
import shutil
import json
from src.presentation.tui.utils.tui_config import TUIConfig, TUISettings


class TestTUISettings:
    """TUISettings 데이터 클래스 테스트"""

    def test_default_initialization(self):
        """기본 초기화 테스트"""
        settings = TUISettings()

        # 테마 설정
        assert settings.theme == "dark"

        # 타임아웃 설정
        assert settings.worker_timeout == 300
        assert settings.max_worker_timeout == 1800

        # 버퍼 크기
        assert settings.max_log_lines == 1000
        assert settings.max_history_size == 100

        # 키 바인딩
        assert settings.key_interrupt == "ctrl+c"
        assert settings.key_new_session == "ctrl+n"
        assert settings.key_save_log == "ctrl+s"
        assert settings.key_search == "ctrl+f"
        assert settings.key_help == "f1"
        assert settings.key_settings == "f2"

        # 알림 설정
        assert settings.enable_notifications is True
        assert settings.notify_on_completion is True
        assert settings.notify_on_error is True

        # 검색 설정
        assert settings.search_case_sensitive is False
        assert settings.search_context_lines == 2

        # 자동 완성 설정
        assert settings.enable_autocomplete is True

        # 로그 저장 설정
        assert settings.log_export_format == "text"
        assert settings.log_export_dir == "logs"

        # UI 패널 표시 설정
        assert settings.show_metrics_panel is True

    def test_custom_initialization(self):
        """커스텀 값으로 초기화 테스트"""
        settings = TUISettings(
            theme="light",
            worker_timeout=600,
            max_log_lines=2000,
            enable_notifications=False,
            show_metrics_panel=False,
        )

        assert settings.theme == "light"
        assert settings.worker_timeout == 600
        assert settings.max_log_lines == 2000
        assert settings.enable_notifications is False
        assert settings.show_metrics_panel is False


class TestTUIConfig:
    """TUIConfig 클래스 테스트"""

    @pytest.fixture
    def temp_config_path(self):
        """임시 설정 파일 경로"""
        temp_dir = Path(tempfile.mkdtemp())
        config_path = temp_dir / "test_tui_config.json"
        yield config_path
        # 테스트 후 정리
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    def test_load_default_settings(self, temp_config_path):
        """설정 파일이 없을 때 기본 설정 로드"""
        settings = TUIConfig.load(config_path=temp_config_path)

        assert isinstance(settings, TUISettings)
        assert settings.theme == "dark"
        assert settings.worker_timeout == 300

    def test_save_and_load(self, temp_config_path):
        """설정 저장 및 로드 테스트"""
        # 커스텀 설정 생성
        original_settings = TUISettings(
            theme="light",
            worker_timeout=600,
            max_log_lines=2000,
            enable_notifications=False,
            search_case_sensitive=True,
        )

        # 저장
        success = TUIConfig.save(original_settings, config_path=temp_config_path)
        assert success is True
        assert temp_config_path.exists()

        # 로드
        loaded_settings = TUIConfig.load(config_path=temp_config_path)

        # 값 검증
        assert loaded_settings.theme == "light"
        assert loaded_settings.worker_timeout == 600
        assert loaded_settings.max_log_lines == 2000
        assert loaded_settings.enable_notifications is False
        assert loaded_settings.search_case_sensitive is True

    def test_save_creates_directory(self, temp_config_path):
        """저장 시 디렉토리 자동 생성 테스트"""
        # 중첩된 디렉토리 경로
        nested_path = temp_config_path.parent / "nested" / "config" / "tui_config.json"

        settings = TUISettings()
        success = TUIConfig.save(settings, config_path=nested_path)

        assert success is True
        assert nested_path.exists()
        assert nested_path.parent.exists()

    def test_load_corrupted_file(self, temp_config_path):
        """손상된 설정 파일 로드 시 기본값 반환"""
        # 잘못된 JSON 파일 생성
        temp_config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(temp_config_path, "w") as f:
            f.write("{ invalid json }")

        # 로드 시 기본 설정 반환되어야 함
        settings = TUIConfig.load(config_path=temp_config_path)
        assert isinstance(settings, TUISettings)
        assert settings.theme == "dark"

    def test_reset_to_default(self, temp_config_path):
        """기본값으로 리셋 테스트"""
        # 커스텀 설정 저장
        custom_settings = TUISettings(theme="light", worker_timeout=999)
        TUIConfig.save(custom_settings, config_path=temp_config_path)

        # 리셋
        reset_settings = TUIConfig.reset_to_default(config_path=temp_config_path)

        # 기본값으로 리셋되었는지 확인
        assert reset_settings.theme == "dark"
        assert reset_settings.worker_timeout == 300

        # 파일도 업데이트되었는지 확인
        loaded_settings = TUIConfig.load(config_path=temp_config_path)
        assert loaded_settings.theme == "dark"

    def test_json_format(self, temp_config_path):
        """JSON 파일 포맷 검증"""
        settings = TUISettings(theme="light")
        TUIConfig.save(settings, config_path=temp_config_path)

        # JSON 파일 읽기
        with open(temp_config_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 필드 확인
        assert "theme" in data
        assert data["theme"] == "light"
        assert "worker_timeout" in data
        assert "max_log_lines" in data
        assert "key_interrupt" in data

    def test_partial_settings_file(self, temp_config_path):
        """일부 필드만 있는 설정 파일 로드"""
        # 일부 필드만 있는 JSON 파일 생성
        partial_data = {
            "theme": "light",
            "worker_timeout": 500,
        }

        temp_config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(temp_config_path, "w") as f:
            json.dump(partial_data, f)

        # 로드 시 나머지는 기본값으로 채워져야 함
        # dataclass의 **data 언패킹은 명시된 필드만 설정하고
        # 나머지는 기본값을 사용함
        settings = TUIConfig.load(config_path=temp_config_path)

        # 파일에 명시된 값
        assert settings.theme == "light"
        assert settings.worker_timeout == 500

        # 나머지는 기본값
        assert settings.max_log_lines == 1000  # 기본값
        assert settings.enable_notifications is True  # 기본값

    def test_unicode_in_config(self, temp_config_path):
        """유니코드 설정값 테스트"""
        settings = TUISettings(log_export_dir="로그디렉토리")
        success = TUIConfig.save(settings, config_path=temp_config_path)
        assert success is True

        loaded_settings = TUIConfig.load(config_path=temp_config_path)
        assert loaded_settings.log_export_dir == "로그디렉토리"

    def test_save_read_only_location(self):
        """읽기 전용 위치에 저장 시도"""
        # 쓰기 권한이 없는 경로
        read_only_path = Path("/root/config.json")

        settings = TUISettings()
        success = TUIConfig.save(settings, config_path=read_only_path)

        # 실패해야 함
        assert success is False

    def test_multiple_save_load_cycles(self, temp_config_path):
        """여러 번 저장/로드 사이클 테스트"""
        for i in range(5):
            settings = TUISettings(worker_timeout=100 + i * 100)
            TUIConfig.save(settings, config_path=temp_config_path)

            loaded = TUIConfig.load(config_path=temp_config_path)
            assert loaded.worker_timeout == 100 + i * 100

    def test_default_config_path_location(self):
        """기본 설정 파일 경로 확인"""
        expected_path = Path.home() / ".better-llm" / "tui_config.json"
        assert TUIConfig.DEFAULT_CONFIG_PATH == expected_path

    def test_show_metrics_panel_field(self, temp_config_path):
        """show_metrics_panel 필드 저장 및 로드 테스트"""
        # 메트릭 패널을 숨긴 설정 생성
        settings_hidden = TUISettings(show_metrics_panel=False)
        TUIConfig.save(settings_hidden, config_path=temp_config_path)

        # 로드 및 검증
        loaded_hidden = TUIConfig.load(config_path=temp_config_path)
        assert loaded_hidden.show_metrics_panel is False

        # 메트릭 패널을 표시하는 설정으로 변경
        settings_visible = TUISettings(show_metrics_panel=True)
        TUIConfig.save(settings_visible, config_path=temp_config_path)

        # 로드 및 검증
        loaded_visible = TUIConfig.load(config_path=temp_config_path)
        assert loaded_visible.show_metrics_panel is True

    def test_show_metrics_panel_in_json(self, temp_config_path):
        """show_metrics_panel이 JSON 파일에 올바르게 저장되는지 검증"""
        settings = TUISettings(show_metrics_panel=False)
        TUIConfig.save(settings, config_path=temp_config_path)

        # JSON 파일 읽기
        with open(temp_config_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # show_metrics_panel 필드 확인
        assert "show_metrics_panel" in data
        assert data["show_metrics_panel"] is False
