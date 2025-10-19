"""
TUI 설정 관리 모듈

사용자 설정 로드 및 저장 기능 제공
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class TUISettings:
    """TUI 설정 데이터 클래스"""

    # 테마 설정
    theme: str = "dark"  # "dark" 또는 "light"

    # 타임아웃 설정 (초)
    worker_timeout: int = 300
    max_worker_timeout: int = 1800

    # 버퍼 크기
    max_log_lines: int = 1000
    max_history_size: int = 100

    # 키 바인딩
    key_interrupt: str = "ctrl+c"
    key_new_session: str = "ctrl+n"
    key_save_log: str = "ctrl+s"
    key_search: str = "ctrl+f"
    key_help: str = "f1"
    key_settings: str = "f2"

    # 알림 설정
    enable_notifications: bool = True
    notify_on_completion: bool = True
    notify_on_error: bool = True

    # 검색 설정
    search_case_sensitive: bool = False
    search_context_lines: int = 2

    # 자동 완성 설정
    enable_autocomplete: bool = True

    # 로그 저장 설정
    log_export_format: str = "text"  # "text" 또는 "markdown"
    log_export_dir: str = "logs"

    # UI 패널 표시 설정
    show_metrics_panel: bool = True


class TUIConfig:
    """
    TUI 설정 관리 클래스

    설정 파일을 로드하고 저장하는 기능 제공
    """

    DEFAULT_CONFIG_PATH = Path.home() / ".better-llm" / "tui_config.json"

    @staticmethod
    def load(config_path: Optional[Path] = None) -> TUISettings:
        """
        설정 파일 로드

        Args:
            config_path: 설정 파일 경로 (기본값: ~/.better-llm/tui_config.json)

        Returns:
            TUISettings 객체
        """
        if config_path is None:
            config_path = TUIConfig.DEFAULT_CONFIG_PATH

        try:
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return TUISettings(**data)
            else:
                # 기본 설정 반환
                return TUISettings()

        except Exception as e:
            print(f"설정 로드 실패 (기본값 사용): {e}")
            return TUISettings()

    @staticmethod
    def save(settings: TUISettings, config_path: Optional[Path] = None) -> bool:
        """
        설정 파일 저장

        Args:
            settings: TUISettings 객체
            config_path: 설정 파일 경로 (기본값: ~/.better-llm/tui_config.json)

        Returns:
            저장 성공 여부
        """
        if config_path is None:
            config_path = TUIConfig.DEFAULT_CONFIG_PATH

        try:
            # 디렉토리 생성
            config_path.parent.mkdir(parents=True, exist_ok=True)

            # JSON으로 저장
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(asdict(settings), f, indent=2, ensure_ascii=False)

            return True

        except Exception as e:
            print(f"설정 저장 실패: {e}")
            return False

    @staticmethod
    def reset_to_default(config_path: Optional[Path] = None) -> TUISettings:
        """
        설정을 기본값으로 리셋

        Args:
            config_path: 설정 파일 경로

        Returns:
            기본 TUISettings 객체
        """
        settings = TUISettings()
        TUIConfig.save(settings, config_path)
        return settings
