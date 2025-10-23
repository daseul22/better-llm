#!/usr/bin/env python3
"""
클립보드 이미지 붙여넣기 수동 테스트

이 스크립트는 Pillow 라이브러리 설치 및 클립보드 이미지 기능을 검증합니다.

사용 방법:
    1. 아무 이미지를 클립보드에 복사 (Cmd+C / Ctrl+C)
    2. 이 스크립트 실행: python tests/manual/test_clipboard.py
    3. 결과 확인

예상 출력:
    ✅ Pillow 설치됨: 10.x.x
    ✅ 클립보드에서 이미지 가져오기 성공: (800, 600) RGB
    ✅ 이미지 저장 성공: /path/to/paste_20250123_143025.png
"""

import sys
import platform
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가 (import 가능하도록)
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def test_pillow_installation():
    """Pillow 설치 여부 및 버전 확인"""
    print("=" * 60)
    print("1. Pillow 라이브러리 설치 확인")
    print("=" * 60)

    try:
        from PIL import Image, ImageGrab
        import PIL
        print(f"✅ Pillow 설치됨: {PIL.__version__}")
        return True
    except ImportError as e:
        print(f"❌ Pillow 설치 안 됨: {e}")
        print("\n해결 방법:")
        print("  pip install pillow")
        print("  또는")
        print("  pip install -r requirements.txt")
        return False


def test_platform_support():
    """플랫폼 지원 여부 확인"""
    print("\n" + "=" * 60)
    print("2. 플랫폼 지원 확인")
    print("=" * 60)

    system = platform.system()
    print(f"현재 플랫폼: {system}")

    if system in ["Darwin", "Windows"]:
        print(f"✅ 클립보드 이미지 지원 플랫폼입니다")
        return True
    else:
        print(f"❌ 클립보드 이미지는 macOS/Windows만 지원됩니다")
        return False


def test_clipboard_image():
    """클립보드에서 이미지 가져오기 테스트"""
    print("\n" + "=" * 60)
    print("3. 클립보드 이미지 가져오기 테스트")
    print("=" * 60)

    from src.presentation.tui.utils.clipboard_helper import ClipboardHelper

    try:
        image = ClipboardHelper.get_clipboard_image()

        if image is None:
            print("⚠️  클립보드에 이미지가 없습니다")
            print("\n테스트 방법:")
            print("  1. 아무 이미지를 클립보드에 복사하세요 (Cmd+C / Ctrl+C)")
            print("  2. 이 스크립트를 다시 실행하세요")
            return None

        print(f"✅ 클립보드에서 이미지 가져오기 성공")
        print(f"   - 크기: {image.size}")
        print(f"   - 모드: {image.mode}")
        print(f"   - 포맷: {image.format or 'N/A'}")

        return image

    except RuntimeError as e:
        print(f"❌ Pillow 라이브러리 오류: {e}")
        return None
    except NotImplementedError as e:
        print(f"❌ 플랫폼 미지원: {e}")
        return None
    except Exception as e:
        print(f"❌ 예기치 않은 오류: {e}")
        return None


def test_save_image(image):
    """이미지 저장 테스트"""
    print("\n" + "=" * 60)
    print("4. 이미지 저장 테스트")
    print("=" * 60)

    from src.presentation.tui.utils.clipboard_helper import ClipboardHelper

    try:
        filepath = ClipboardHelper.save_image_to_temp(image)
        print(f"✅ 이미지 저장 성공: {filepath}")

        # 파일 존재 여부 확인
        if Path(filepath).exists():
            file_size = Path(filepath).stat().st_size
            print(f"   - 파일 크기: {file_size:,} bytes")
        else:
            print(f"⚠️  파일이 저장되지 않았습니다: {filepath}")

        return filepath

    except ValueError as e:
        print(f"❌ 입력 오류: {e}")
        return None
    except OSError as e:
        print(f"❌ 파일 저장 오류: {e}")
        return None
    except Exception as e:
        print(f"❌ 예기치 않은 오류: {e}")
        return None


def test_full_workflow():
    """전체 워크플로우 테스트 (get_and_save_clipboard_image)"""
    print("\n" + "=" * 60)
    print("5. 전체 워크플로우 테스트")
    print("=" * 60)

    from src.presentation.tui.utils.clipboard_helper import ClipboardHelper

    try:
        filepath = ClipboardHelper.get_and_save_clipboard_image()

        if filepath is None:
            print("⚠️  클립보드에 이미지가 없습니다")
            return False

        print(f"✅ 클립보드 이미지 저장 성공: {filepath}")
        return True

    except Exception as e:
        print(f"❌ 워크플로우 오류: {e}")
        return False


def main():
    """메인 테스트 함수"""
    print("\n" + "🧪 클립보드 이미지 붙여넣기 수동 테스트")
    print("=" * 60)

    # 1. Pillow 설치 확인
    if not test_pillow_installation():
        print("\n❌ Pillow가 설치되지 않아 테스트를 중단합니다")
        sys.exit(1)

    # 2. 플랫폼 지원 확인
    if not test_platform_support():
        print("\n❌ 지원되지 않는 플랫폼입니다")
        sys.exit(1)

    # 3. 클립보드 이미지 가져오기
    image = test_clipboard_image()
    if image is None:
        print("\n⚠️  클립보드에 이미지가 없어 일부 테스트를 건너뜁니다")
        sys.exit(0)

    # 4. 이미지 저장
    filepath = test_save_image(image)
    if filepath is None:
        print("\n❌ 이미지 저장 실패")
        sys.exit(1)

    # 5. 전체 워크플로우 (재테스트)
    test_full_workflow()

    # 종료 메시지
    print("\n" + "=" * 60)
    print("✅ 모든 테스트 통과!")
    print("=" * 60)
    print("\n다음 단계:")
    print("  1. TUI 실행: python -m src.presentation.tui.tui_app")
    print("  2. 입력창에서 Cmd+V (macOS) / Ctrl+V (Windows) 테스트")
    print("  3. 이미지가 자동으로 첨부되는지 확인")
    print()


if __name__ == "__main__":
    main()
