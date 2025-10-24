"""
ImageHandler 모듈

이미지 붙여넣기 이벤트 처리 로직을 캡슐화합니다.
"""

from pathlib import Path
from typing import TYPE_CHECKING, Optional
from rich.panel import Panel
from src.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from ..tui_app import OrchestratorTUI

logger = get_logger(__name__, component="ImageHandler")


class ImageHandler:
    """
    이미지 붙여넣기 처리를 담당하는 클래스

    tui_app.py의 on_multiline_input_image_pasted 메서드에서
    분리된 로직을 통합합니다.

    책임:
        - 이미지 파일 정보 추출 (크기, 해상도)
        - Rich Panel 형식으로 정보 포맷팅
        - 입력창에 이미지 경로 삽입
        - 알림 표시

    Example:
        >>> handler = ImageHandler(tui_app)
        >>> await handler.handle_image_paste("/tmp/screenshot.png")
    """

    def __init__(self, tui_app: "OrchestratorTUI"):
        """
        ImageHandler 초기화

        Args:
            tui_app: TUI 애플리케이션 인스턴스
        """
        self.tui = tui_app

    def format_file_size(self, size_bytes: int) -> str:
        """
        파일 크기를 사람이 읽기 쉬운 형식으로 변환

        Args:
            size_bytes: 바이트 단위 파일 크기

        Returns:
            포맷팅된 크기 문자열 (예: "2.5 MB", "512 KB", "128 bytes")
        """
        if size_bytes < 1024:
            return f"{size_bytes} bytes"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.2f} MB"

    def extract_image_dimensions(self, file_path: Path) -> str:
        """
        이미지 해상도 정보 추출 (PIL 사용)

        Args:
            file_path: 이미지 파일 경로

        Returns:
            "1920x1080 (RGB)" 형식의 문자열, 실패 시 "N/A"
        """
        try:
            from PIL import Image
            with Image.open(file_path) as img:
                return f"{img.size[0]}x{img.size[1]} ({img.mode})"
        except Exception as img_error:
            logger.debug(f"이미지 메타데이터 읽기 실패: {img_error}")
            return "N/A"

    def create_image_info_panel(
        self,
        file_path: Path,
        file_size_str: str,
        dimensions: str
    ) -> Panel:
        """
        이미지 정보를 Rich Panel로 생성

        Args:
            file_path: 이미지 파일 경로
            file_size_str: 포맷팅된 파일 크기
            dimensions: 이미지 해상도 문자열

        Returns:
            Rich Panel 객체
        """
        info_text = (
            f"[bold cyan]🖼️ 이미지 붙여넣기 완료[/bold cyan]\n\n"
            f"**파일명**: {file_path.name}\n"
            f"**경로**: {file_path}\n"
            f"**크기**: {file_size_str}\n"
            f"**해상도**: {dimensions}"
        )
        return Panel(info_text, border_style="cyan")

    def create_minimal_image_panel(self, file_path: str) -> Panel:
        """
        최소 이미지 정보 Panel 생성 (에러 시 대체용)

        Args:
            file_path: 이미지 파일 경로

        Returns:
            간소화된 Rich Panel 객체
        """
        return Panel(
            f"[bold cyan]🖼️ 이미지 붙여넣기 완료[/bold cyan]\n\n"
            f"**경로**: {file_path}",
            border_style="cyan"
        )

    def notify_image_paste(self, file_path: Path) -> None:
        """
        이미지 붙여넣기 알림 표시

        Args:
            file_path: 이미지 파일 경로
        """
        if self.tui.settings.enable_notifications:
            self.tui.notify(
                f"이미지 붙여넣기: {file_path.name}",
                severity="information"
            )

    def insert_image_path_to_input(self, file_path: str) -> None:
        """
        입력창에 이미지 경로 삽입

        Args:
            file_path: 이미지 파일 경로
        """
        from textual.widgets import TextArea as MultilineInput
        task_input = self.tui.query_one("#task-input", MultilineInput)
        task_input.insert(f"[Image: {file_path}]")
        logger.info(f"📝 [TUI] 입력창에 이미지 경로 삽입: {file_path}")

    def write_image_info_to_log(
        self,
        file_path: Path,
        original_path: str
    ) -> None:
        """
        이미지 정보를 로그 패널에 출력

        Args:
            file_path: 이미지 파일 Path 객체
            original_path: 원본 경로 문자열 (에러 시 사용)
        """
        try:
            file_size = file_path.stat().st_size
            file_size_str = self.format_file_size(file_size)
            dimensions = self.extract_image_dimensions(file_path)

            # 로그 패널 생성 및 출력
            panel = self.create_image_info_panel(file_path, file_size_str, dimensions)
            self.tui.write_log("")
            self.tui.write_log(panel)
            self.tui.write_log("")

        except Exception as info_error:
            logger.error(
                f"이미지 정보 추출 실패: {info_error}",
                exc_info=True
            )
            # 최소한의 정보라도 표시
            panel = self.create_minimal_image_panel(original_path)
            self.tui.write_log("")
            self.tui.write_log(panel)
            self.tui.write_log("")

    async def handle_image_paste(self, file_path: str) -> None:
        """
        이미지 붙여넣기 처리 메인 로직

        Args:
            file_path: 이미지 파일 경로 문자열
        """
        try:
            logger.info(f"🖼️ [TUI] 이미지 붙여넣기 이벤트 수신: {file_path}")

            # 1. 알림 표시
            path_obj = Path(file_path)
            self.notify_image_paste(path_obj)

            # 2. 입력창에 경로 삽입
            self.insert_image_path_to_input(file_path)

            # 3. 로그에 이미지 정보 출력
            self.write_image_info_to_log(path_obj, file_path)

        except Exception as e:
            logger.error(
                f"이미지 붙여넣기 처리 실패: {e}",
                exc_info=True
            )
            if self.tui.settings.enable_notifications and self.tui.settings.notify_on_error:
                self.tui.notify(
                    f"이미지 처리 실패: {e}",
                    severity="error"
                )
