"""전체 프로젝트 Import 경로 자동 수정 스크립트

src 디렉토리 전체를 대상으로 import 경로를 수정합니다.

잘못된 형식:
    from domain.models import ...
    from application.ports import ...
    import infrastructure.logging

올바른 형식:
    from src.domain.models import ...
    from src.application.ports import ...
    import src.infrastructure.logging
"""

import re
from pathlib import Path
from typing import Tuple


def fix_imports(file_path: Path) -> Tuple[bool, int]:
    """파일의 import 경로를 수정합니다.

    Args:
        file_path: 수정할 파일 경로

    Returns:
        Tuple[수정 여부, 수정된 라인 수]
    """
    try:
        content = file_path.read_text(encoding="utf-8")
        original = content
        modified_lines = 0

        # from domain|application|infrastructure|presentation.* 패턴 수정
        content, count1 = re.subn(
            r"^from (domain|application|infrastructure|presentation)\.",
            r"from src.\1.",
            content,
            flags=re.MULTILINE
        )
        modified_lines += count1

        # import domain|application|infrastructure|presentation.* 패턴 수정
        content, count2 = re.subn(
            r"^import (domain|application|infrastructure|presentation)\b",
            r"import src.\1",
            content,
            flags=re.MULTILINE
        )
        modified_lines += count2

        if content != original:
            file_path.write_text(content, encoding="utf-8")
            return True, modified_lines
        return False, 0
    except Exception as e:
        print(f"❌ Error fixing {file_path}: {e}")
        return False, 0


def main():
    """메인 실행 함수."""
    print("=" * 80)
    print("전체 프로젝트 Import 경로 자동 수정")
    print("=" * 80)
    print()

    # src 디렉토리의 모든 .py 파일 찾기
    src_path = Path("src")
    if not src_path.exists():
        print("❌ src 디렉토리를 찾을 수 없습니다.")
        return

    python_files = list(src_path.rglob("*.py"))
    print(f"📋 총 검색된 파일: {len(python_files)}개\n")

    fixed_count = 0
    skipped_count = 0
    total_lines_modified = 0
    fixed_files = []

    for file_path in sorted(python_files):
        was_fixed, lines_modified = fix_imports(file_path)

        if was_fixed:
            print(f"✅ Fixed: {file_path} ({lines_modified} imports)")
            fixed_count += 1
            total_lines_modified += lines_modified
            fixed_files.append((file_path, lines_modified))
        else:
            skipped_count += 1

    print()
    print("=" * 80)
    print("📊 수정 결과 요약")
    print("=" * 80)
    print(f"✅ 수정됨: {fixed_count}개 파일")
    print(f"📝 총 수정된 import 라인: {total_lines_modified}개")
    print(f"⏭️  건너뜀 (이미 올바름): {skipped_count}개")
    print(f"📁 총 처리: {fixed_count + skipped_count}/{len(python_files)}개")
    print()

    if fixed_files:
        print("=" * 80)
        print("📝 수정된 파일 목록")
        print("=" * 80)
        for file_path, lines_modified in fixed_files:
            print(f"  {file_path} ({lines_modified} imports)")
        print()

    print("=" * 80)
    print("🎉 Import 경로 수정 완료!")
    print("=" * 80)


if __name__ == "__main__":
    main()
