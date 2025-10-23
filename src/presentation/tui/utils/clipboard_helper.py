"""
클립보드 이미지 처리 모듈

클립보드에서 이미지를 가져와 파일로 저장하는 기능 제공
"""

from pathlib import Path
from datetime import datetime
from typing import Optional
import logging
import platform

try:
    from PIL import Image, ImageGrab
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

from src.utils.paths import get_data_dir

logger = logging.getLogger(__name__)


class ClipboardHelper:
    """
    클립보드 이미지 처리 클래스

    클립보드에서 이미지를 가져와 임시 파일로 저장하는 기능 제공
    """

    @staticmethod
    def get_clipboard_image() -> Optional[Image.Image]:
        """
        클립보드에서 이미지 가져오기

        Returns:
            클립보드에 이미지가 있으면 PIL.Image 객체 반환, 없으면 None

        Raises:
            RuntimeError: Pillow 라이브러리가 설치되지 않은 경우
            NotImplementedError: 지원되지 않는 플랫폼인 경우

        Examples:
            >>> image = ClipboardHelper.get_clipboard_image()
            >>> if image:
            ...     print(f"이미지 크기: {image.size}")
        """
        if not PILLOW_AVAILABLE:
            raise RuntimeError(
                "Pillow 라이브러리가 필요합니다. 'pip install pillow'로 설치하세요."
            )

        # 플랫폼 확인
        system = platform.system()
        if system not in ["Darwin", "Windows"]:
            raise NotImplementedError(
                f"클립보드 이미지 가져오기는 macOS와 Windows만 지원됩니다. "
                f"현재 플랫폼: {system}"
            )

        # 클립보드에서 이미지 가져오기 (예외는 호출자가 처리)
        image = ImageGrab.grabclipboard()

        if image is None:
            logger.debug("클립보드에 이미지가 없습니다")
            return None

        # PIL.Image 객체인지 확인
        if not isinstance(image, Image.Image):
            logger.debug(f"클립보드 내용이 이미지가 아닙니다: {type(image)}")
            return None

        logger.debug(
            f"클립보드에서 이미지 가져오기 성공: {image.size}, {image.mode}"
        )
        return image

    @staticmethod
    def save_image_to_temp(image: Image.Image) -> str:
        """
        이미지를 임시 파일로 저장

        이미지를 PNG 형식으로 프로젝트별 임시 디렉토리에 저장합니다.
        저장 경로: ~/.better-llm/{project-name}/images/paste_{timestamp}.png

        Args:
            image: 저장할 PIL.Image 객체

        Returns:
            저장된 파일의 절대 경로 (문자열)

        Raises:
            ValueError: image가 None이거나 잘못된 형식인 경우
            OSError: 파일 저장 실패 시

        Examples:
            >>> image = Image.new("RGB", (100, 100), color="red")
            >>> path = ClipboardHelper.save_image_to_temp(image)
            >>> print(path)
            '/Users/username/.better-llm/my-project/images/paste_20250123_143025.png'
        """
        if image is None:
            raise ValueError("image가 None입니다")

        if not isinstance(image, Image.Image):
            raise ValueError(f"image는 PIL.Image 객체여야 합니다. 현재: {type(image)}")

        try:
            # 이미지 저장 디렉토리 생성
            images_dir = get_data_dir("images")

            # 타임스탬프 기반 파일명 생성 (기존 코드 스타일과 일관성 유지)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"paste_{timestamp}.png"
            filepath = images_dir / filename

            # PNG 형식으로 저장
            image.save(filepath, format="PNG")

            logger.info(f"이미지 저장 성공: {filepath} ({image.size})")
            return str(filepath)

        except Exception as e:
            logger.error(f"이미지 저장 실패: {e}")
            raise OSError(f"이미지 저장 중 오류 발생: {e}") from e

    @staticmethod
    def get_and_save_clipboard_image() -> Optional[str]:
        """
        클립보드에서 이미지를 가져와 바로 저장하는 헬퍼 메서드

        Returns:
            저장된 파일 경로 (문자열), 클립보드에 이미지가 없으면 None

        Raises:
            RuntimeError: Pillow 라이브러리가 설치되지 않은 경우
            NotImplementedError: 지원되지 않는 플랫폼인 경우
            OSError: 이미지 저장 실패 시

        Examples:
            >>> try:
            ...     path = ClipboardHelper.get_and_save_clipboard_image()
            ...     if path:
            ...         print(f"이미지가 {path}에 저장되었습니다")
            ... except (RuntimeError, NotImplementedError) as e:
            ...     print(f"클립보드 이미지 미지원: {e}")
        """
        image = ClipboardHelper.get_clipboard_image()
        if image is None:
            return None

        try:
            return ClipboardHelper.save_image_to_temp(image)
        finally:
            # PIL Image 리소스 정리
            image.close()
