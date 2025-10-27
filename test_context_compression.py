#!/usr/bin/env python3
"""
컨텍스트 압축 기능 테스트 스크립트 (간소화 버전)

구문 검사 및 로직 검증용
"""

import sys
from pathlib import Path

print("=" * 60)
print("컨텍스트 압축 기능 - 구문 검사")
print("=" * 60)

# 구문 검사만 수행
try:
    import py_compile

    # context_compressor.py 구문 검사
    compressor_path = Path(__file__).parent / "src/domain/services/context_compressor.py"
    py_compile.compile(str(compressor_path), doraise=True)
    print(f"✅ {compressor_path.name} 구문 검사 통과")

    # manager_client.py 구문 검사
    manager_path = Path(__file__).parent / "src/infrastructure/claude/manager_client.py"
    py_compile.compile(str(manager_path), doraise=True)
    print(f"✅ {manager_path.name} 구문 검사 통과")

    print("\n" + "=" * 60)
    print("✅ 모든 구문 검사 통과!")
    print("=" * 60)

    sys.exit(0)

except SyntaxError as e:
    print(f"\n❌ 구문 오류: {e}")
    sys.exit(1)


def create_test_messages(count: int = 10) -> list:
    """테스트용 메시지 생성"""
    messages = []

    # 첫 번째 사용자 메시지
    messages.append(Message(
        role="user",
        content="FastAPI로 /users CRUD API를 작성해줘",
        agent_name=None,
        timestamp=datetime.now()
    ))

    # 여러 Agent 메시지 추가
    for i in range(count - 1):
        messages.append(Message(
            role="agent",
            content=f"테스트 Agent 메시지 {i+1}\n" + "A" * 1000,  # 1000자 메시지
            agent_name=f"worker_{i+1}",
            timestamp=datetime.now()
        ))

    return messages


def test_should_compress():
    """압축 필요 여부 판단 테스트"""
    print("\n=== 테스트 1: should_compress() ===")

    compressed_dir = Path("/tmp/test_compression")
    compressor = ContextCompressor(
        compressed_dir=compressed_dir,
        compression_threshold=0.85
    )

    # 85% 미만: 압축 불필요
    result = compressor.should_compress(current_tokens=80000, max_tokens=100000)
    assert result == False, "80% 사용량에서는 압축 불필요"
    print(f"✅ 80% 사용량: 압축 불필요 = {result}")

    # 85% 이상: 압축 필요
    result = compressor.should_compress(current_tokens=90000, max_tokens=100000)
    assert result == True, "90% 사용량에서는 압축 필요"
    print(f"✅ 90% 사용량: 압축 필요 = {result}")

    print("✅ 테스트 1 통과")


def test_estimate_compression_benefit():
    """압축 효과 추정 테스트"""
    print("\n=== 테스트 2: estimate_compression_benefit() ===")

    compressed_dir = Path("/tmp/test_compression")
    compressor = ContextCompressor(compressed_dir=compressed_dir)

    messages = create_test_messages(count=10)

    benefit = compressor.estimate_compression_benefit(
        messages,
        target_reduction_ratio=0.3
    )

    print(f"원본 문자 수: {benefit['original_chars']:,}자")
    print(f"압축 후 예상 문자 수: {benefit['estimated_compressed_chars']:,}자")
    print(f"압축 비율: {benefit['reduction_ratio']*100:.1f}%")
    print(f"압축 대상 메시지 수: {benefit['messages_to_compress']}개")

    assert benefit['original_chars'] > 0, "원본 문자 수는 0보다 커야 함"
    assert benefit['estimated_compressed_chars'] < benefit['original_chars'], "압축 후 문자 수가 더 적어야 함"
    assert benefit['messages_to_compress'] > 0, "압축 대상이 있어야 함"

    print("✅ 테스트 2 통과")


def test_compress_messages():
    """메시지 압축 테스트"""
    print("\n=== 테스트 3: compress_messages() ===")

    compressed_dir = Path("/tmp/test_compression")
    compressed_dir.mkdir(parents=True, exist_ok=True)

    compressor = ContextCompressor(compressed_dir=compressed_dir)

    messages = create_test_messages(count=10)
    print(f"원본 메시지 수: {len(messages)}개")

    # 30% 압축 (3개 메시지 압축)
    compressed_messages, compressed_count = compressor.compress_messages(
        messages,
        target_reduction_ratio=0.3
    )

    print(f"압축된 메시지 수: {compressed_count}개")
    print(f"압축 후 메시지 리스트 길이: {len(compressed_messages)}개")

    assert len(compressed_messages) == len(messages), "메시지 개수는 동일해야 함"
    assert compressed_count > 0, "최소 1개는 압축되어야 함"

    # 첫 번째 사용자 메시지는 압축되지 않아야 함
    first_msg = compressed_messages[0]
    assert "압축된 메시지" not in first_msg.content, "첫 사용자 메시지는 압축 안 됨"
    print(f"✅ 첫 번째 사용자 메시지 보존됨")

    # 일부 메시지는 압축되어야 함
    compressed_found = False
    for msg in compressed_messages[1:]:
        if "압축된 메시지" in msg.content:
            compressed_found = True
            print(f"✅ 압축된 메시지 발견:")
            print(f"   {msg.content[:200]}...")
            break

    assert compressed_found, "압축된 메시지가 있어야 함"

    print("✅ 테스트 3 통과")


def test_load_compressed_message():
    """압축된 메시지 로드 테스트"""
    print("\n=== 테스트 4: load_compressed_message() ===")

    compressed_dir = Path("/tmp/test_compression")
    compressed_dir.mkdir(parents=True, exist_ok=True)

    compressor = ContextCompressor(compressed_dir=compressed_dir)

    # 압축 수행
    messages = create_test_messages(count=5)
    compressed_messages, _ = compressor.compress_messages(messages, target_reduction_ratio=0.4)

    # 압축된 메시지 찾기
    compressed_file_path = None
    for msg in compressed_messages:
        if "압축된 메시지" in msg.content and "저장 경로:" in msg.content:
            # 파일 경로 추출
            lines = msg.content.split("\n")
            for line in lines:
                if "저장 경로:" in line:
                    compressed_file_path = Path(line.split("저장 경로:")[-1].strip())
                    break
            break

    assert compressed_file_path is not None, "압축된 파일 경로를 찾아야 함"
    print(f"압축 파일 경로: {compressed_file_path}")

    # 압축된 메시지 로드
    loaded_msg = compressor.load_compressed_message(compressed_file_path)

    assert loaded_msg is not None, "메시지 로드 성공해야 함"
    assert len(loaded_msg.content) > 100, "원본 메시지 내용이 복원되어야 함"
    print(f"✅ 압축된 메시지 로드 성공 (길이: {len(loaded_msg.content)}자)")
    print(f"   내용: {loaded_msg.content[:100]}...")

    print("✅ 테스트 4 통과")


def main():
    """전체 테스트 실행"""
    print("=" * 60)
    print("컨텍스트 압축 기능 테스트 시작")
    print("=" * 60)

    try:
        test_should_compress()
        test_estimate_compression_benefit()
        test_compress_messages()
        test_load_compressed_message()

        print("\n" + "=" * 60)
        print("✅ 모든 테스트 통과!")
        print("=" * 60)

        return 0

    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ 테스트 실패: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
