#!/usr/bin/env python3
"""
로깅 시스템 테스트

웹 워크플로우에서 에러 로그가 제대로 기록되는지 테스트합니다.
"""
import os
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).parent))

from src.infrastructure.logging import configure_structlog, get_logger, add_session_file_handlers, remove_session_file_handlers

def test_logging():
    """로깅 시스템 테스트"""
    print("=" * 70)
    print("로깅 시스템 테스트 시작")
    print("=" * 70)

    # 1. 로그 시스템 초기화
    log_dir = Path.home() / ".better-llm" / "test-logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    configure_structlog(
        log_dir=str(log_dir),
        log_level="DEBUG",
        enable_json=False  # 읽기 쉬운 콘솔 형식
    )

    # 2. 세션별 핸들러 추가 (project_path는 .better-llm의 부모 디렉토리)
    session_id = "test-session-12345"
    project_path = str(log_dir.parent.parent)  # ~/.better-llm의 부모 → ~
    add_session_file_handlers(session_id, project_path=project_path)

    # 세션별 로그 디렉토리 확인
    session_log_dir = Path(project_path) / ".better-llm" / "logs"
    print(f"📁 세션별 로그 디렉토리: {session_log_dir}")

    logger = get_logger(__name__, test_id="logging-test", session_id=session_id)

    print(f"\n📁 로그 디렉토리: {log_dir}")
    print(f"🔑 세션 ID: {session_id}")
    print("\n테스트 로그 출력 중...\n")

    # 3. 다양한 레벨의 로그 출력
    logger.debug("디버그 메시지", detail="상세 정보")
    logger.info("정보 메시지", user="test_user")
    logger.warning("경고 메시지", warning_type="test")
    logger.error("에러 메시지", error_code=500)

    # 4. 예외 로그 출력
    try:
        raise TypeError("테스트 TypeError 발생")
    except TypeError as e:
        logger.error(
            "예외가 발생했습니다",
            error_type=type(e).__name__,
            error_message=str(e),
            exc_info=True
        )

    # 5. 세션별 핸들러 제거
    remove_session_file_handlers(session_id)

    print("\n" + "=" * 70)
    print("로그 파일 확인:")
    print("=" * 70)

    # 기본 로그 파일들
    basic_files = [
        "better-llm.log",
        "better-llm-error.log",
        "better-llm-debug.log",
    ]

    for filename in basic_files:
        log_file = log_dir / filename
        if log_file.exists():
            file_size = log_file.stat().st_size
            status = "✅" if file_size > 0 else "⚠️ (empty)"
            print(f"  {status} {filename}: {file_size} bytes")

            if file_size > 0:
                with open(log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    line_count = len(lines)
                    print(f"       ({line_count} lines)")
        else:
            print(f"  ❌ {filename}: 파일 없음")

    # 세션별 로그 파일들
    print(f"\n세션별 로그 ({session_log_dir}):")
    session_files = [
        "system.log",
        f"{session_id}-debug.log",
        f"{session_id}-info.log",
        f"{session_id}-error.log",
    ]

    for filename in session_files:
        log_file = session_log_dir / filename
        if log_file.exists():
            file_size = log_file.stat().st_size
            status = "✅" if file_size > 0 else "⚠️ (empty)"
            print(f"  {status} {filename}: {file_size} bytes")

            if file_size > 0:
                with open(log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    line_count = len(lines)
                    print(f"       ({line_count} lines)")
        else:
            print(f"  ❌ {filename}: 파일 없음")

    print("\n" + "=" * 70)
    print("레벨별 로그 분리 확인:")
    print("=" * 70)

    # debug.log에 debug만 있는지 확인
    debug_log = session_log_dir / f"{session_id}-debug.log"
    if debug_log.exists():
        with open(debug_log, 'r', encoding='utf-8') as f:
            content = f.read()
            has_debug = "디버그 메시지" in content
            has_info = "정보 메시지" in content
            has_error = "에러 메시지" in content
            print(f"  {session_id}-debug.log:")
            print(f"    DEBUG 포함: {'✅' if has_debug else '❌'}")
            print(f"    INFO 제외: {'✅' if not has_info else '❌ (잘못됨)'}")
            print(f"    ERROR 제외: {'✅' if not has_error else '❌ (잘못됨)'}")

    # info.log에 info/warning만 있는지 확인
    info_log = session_log_dir / f"{session_id}-info.log"
    if info_log.exists():
        with open(info_log, 'r', encoding='utf-8') as f:
            content = f.read()
            has_debug = "디버그 메시지" in content
            has_info = "정보 메시지" in content
            has_warning = "경고 메시지" in content
            has_error = "에러 메시지" in content
            print(f"  {session_id}-info.log:")
            print(f"    DEBUG 제외: {'✅' if not has_debug else '❌ (잘못됨)'}")
            print(f"    INFO 포함: {'✅' if has_info else '❌'}")
            print(f"    WARNING 포함: {'✅' if has_warning else '❌'}")
            print(f"    ERROR 제외: {'✅' if not has_error else '❌ (잘못됨)'}")

    # error.log에 error만 있는지 확인
    error_log = log_dir / f"{session_id}-error.log"
    if error_log.exists():
        with open(error_log, 'r', encoding='utf-8') as f:
            content = f.read()
            has_debug = "디버그 메시지" in content
            has_info = "정보 메시지" in content
            has_error = "에러 메시지" in content
            print(f"  {session_id}-error.log:")
            print(f"    DEBUG 제외: {'✅' if not has_debug else '❌ (잘못됨)'}")
            print(f"    INFO 제외: {'✅' if not has_info else '❌ (잘못됨)'}")
            print(f"    ERROR 포함: {'✅' if has_error else '❌'}")

    print("\n" + "=" * 70)
    print("✅ 테스트 완료")
    print("=" * 70)

if __name__ == "__main__":
    test_logging()
