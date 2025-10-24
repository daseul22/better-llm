#!/usr/bin/env python3
"""
Manager Agent의 Worker Tool 실패 시 자동 복구 기능 테스트

테스트 시나리오:
1. 프롬프트에 복구 규칙이 포함되는지 확인
2. Committer 실패 시나리오 시뮬레이션
3. Tester 실패 시나리오 시뮬레이션
"""

import sys
import os

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.infrastructure.claude.manager_client import ManagerAgent
from src.domain.models import Message


def test_prompt_contains_recovery_rules():
    """프롬프트에 Worker Tool 실패 시 자동 복구 규칙이 포함되는지 확인"""
    print("=" * 80)
    print("테스트 1: 프롬프트에 복구 규칙 포함 여부 확인")
    print("=" * 80)

    # ManagerAgent 생성 (worker_tools_server는 None으로 - 프롬프트만 확인)
    manager = ManagerAgent(
        worker_tools_server=None,
        model="claude-sonnet-4-5-20250929",
        auto_commit_enabled=True
    )

    # 시스템 프롬프트 확인
    prompt = manager.SYSTEM_PROMPT

    # 필수 키워드 체크
    required_keywords = [
        "Worker Tool 실패 시 자동 복구 규칙",
        "Committer 실패 시 복구 규칙",
        "Tester 실패 시 복구 규칙",
        "Coder 실패 시 복구 규칙",
        "병합 충돌",
        "즉시 Tool을 호출하세요",
        "텍스트만 출력하고 끝내면 안 됩니다"
    ]

    print("\n✅ 필수 키워드 확인:")
    all_found = True
    for keyword in required_keywords:
        found = keyword in prompt
        status = "✅" if found else "❌"
        print(f"  {status} '{keyword}': {'포함됨' if found else '누락!'}")
        if not found:
            all_found = False

    # Committer 예시 확인
    print("\n✅ Committer 복구 패턴 확인:")
    committer_patterns = [
        "execute_coder_task",
        "병합 충돌을 해결해주세요",
        "잘못된 패턴 (절대 금지!)",
        "올바른 패턴"
    ]

    for pattern in committer_patterns:
        found = pattern in prompt
        status = "✅" if found else "❌"
        print(f"  {status} '{pattern}': {'포함됨' if found else '누락!'}")
        if not found:
            all_found = False

    # Tester 예시 확인
    print("\n✅ Tester 복구 패턴 확인:")
    tester_patterns = [
        "테스트가 실패했습니다",
        "최대 재시도: 2회",
        "2회 재시도 후에도 실패"
    ]

    for pattern in tester_patterns:
        found = pattern in prompt
        status = "✅" if found else "❌"
        print(f"  {status} '{pattern}': {'포함됨' if found else '누락!'}")
        if not found:
            all_found = False

    # 프롬프트 길이 확인
    print(f"\n📊 프롬프트 통계:")
    print(f"  - 전체 길이: {len(prompt):,} 문자")
    print(f"  - 라인 수: {len(prompt.splitlines())} 줄")

    # 복구 규칙 섹션 추출
    if "Worker Tool 실패 시 자동 복구 규칙" in prompt:
        start_idx = prompt.index("## ⚠️ Worker Tool 실패 시 자동 복구 규칙")
        recovery_section = prompt[start_idx:start_idx+2000]  # 앞 2000자만
        print(f"\n📋 복구 규칙 섹션 미리보기 (앞 500자):")
        print("-" * 80)
        print(recovery_section[:500])
        print("-" * 80)

    print(f"\n{'='*80}")
    print(f"테스트 1 결과: {'✅ 통과' if all_found else '❌ 실패'}")
    print(f"{'='*80}\n")

    return all_found


def test_history_with_committer_failure():
    """Committer 실패 시나리오 시뮬레이션"""
    print("=" * 80)
    print("테스트 2: Committer 실패 시나리오 - 프롬프트 생성 확인")
    print("=" * 80)

    # ManagerAgent 생성
    manager = ManagerAgent(
        worker_tools_server=None,
        model="claude-sonnet-4-5-20250929",
        auto_commit_enabled=True
    )

    # 대화 히스토리 시뮬레이션
    history = [
        Message(role="user", content="프로젝트를 커밋해줘"),
        Message(
            role="agent",
            agent_name="planner",
            content="""## 📋 [PLANNER 요약 - Manager 전달용]

**✅ 상태: 작업 완료**

**핵심 내용**:
현재 변경사항을 확인하고 커밋 계획 수립

**요약**: Git 상태 확인 후 커밋 진행"""
        ),
        Message(
            role="agent",
            agent_name="committer",
            content="""❌ 커밋 거부 (보안 검증 실패):

병합 충돌 마커가 감지되었습니다:
  - src/infrastructure/mcp/commit_validator.py
  - src/infrastructure/mcp/worker_tools.py

충돌을 해결한 후 커밋해주세요."""
        )
    ]

    # 프롬프트 빌드
    prompt = manager._build_prompt_from_history(history)

    print("\n✅ 생성된 프롬프트 확인:")
    print(f"  - 전체 길이: {len(prompt):,} 문자")

    # Committer 실패 내용이 포함되었는지 확인
    assert "병합 충돌 마커가 감지되었습니다" in prompt, "Committer 실패 내용이 누락됨!"
    print("  ✅ Committer 실패 내용 포함됨")

    # 복구 규칙이 포함되었는지 확인
    assert "병합 충돌을 해결해주세요" in prompt or "Committer 실패 시 복구 규칙" in prompt
    print("  ✅ 복구 규칙 포함됨")

    # 대화 히스토리 확인
    assert "[planner Tool 완료]" in prompt, "Planner 결과가 누락됨!"
    assert "[committer Tool 완료]" in prompt, "Committer 결과가 누락됨!"
    print("  ✅ 대화 히스토리 정상 포함")

    print(f"\n📋 프롬프트 마지막 500자 미리보기:")
    print("-" * 80)
    print(prompt[-500:])
    print("-" * 80)

    print(f"\n{'='*80}")
    print("테스트 2 결과: ✅ 통과")
    print(f"{'='*80}\n")

    return True


def test_history_with_tester_failure():
    """Tester 실패 시나리오 시뮬레이션"""
    print("=" * 80)
    print("테스트 3: Tester 실패 시나리오 - 프롬프트 생성 확인")
    print("=" * 80)

    # ManagerAgent 생성
    manager = ManagerAgent(
        worker_tools_server=None,
        model="claude-sonnet-4-5-20250929",
        auto_commit_enabled=False
    )

    # 대화 히스토리 시뮬레이션
    history = [
        Message(role="user", content="FastAPI CRUD API를 작성해줘"),
        Message(
            role="agent",
            agent_name="planner",
            content="## 📋 [PLANNER 요약]\n계획 완료"
        ),
        Message(
            role="agent",
            agent_name="coder",
            content="## 📋 [CODER 요약]\nFastAPI CRUD 코드 작성 완료"
        ),
        Message(
            role="agent",
            agent_name="reviewer",
            content="## 📋 [REVIEWER 요약]\n✅ 승인"
        ),
        Message(
            role="agent",
            agent_name="tester",
            content="""## 📋 [TESTER 요약]

❌ 테스트 실패 (2/5 실패):
- test_create_user: AssertionError (예상: 201, 실제: 500)
- test_delete_user: KeyError 'user_id'

나머지 테스트는 통과했습니다."""
        )
    ]

    # 프롬프트 빌드
    prompt = manager._build_prompt_from_history(history)

    print("\n✅ 생성된 프롬프트 확인:")
    print(f"  - 전체 길이: {len(prompt):,} 문자")

    # Tester 실패 내용이 포함되었는지 확인
    assert "테스트 실패" in prompt, "Tester 실패 내용이 누락됨!"
    print("  ✅ Tester 실패 내용 포함됨")

    # 복구 규칙이 포함되었는지 확인
    assert "Tester 실패 시 복구 규칙" in prompt
    print("  ✅ Tester 복구 규칙 포함됨")

    # 모든 Worker 결과가 포함되었는지 확인
    for worker in ["planner", "coder", "reviewer", "tester"]:
        assert f"[{worker} Tool 완료]" in prompt, f"{worker} 결과가 누락됨!"
    print("  ✅ 모든 Worker 결과 포함됨")

    print(f"\n{'='*80}")
    print("테스트 3 결과: ✅ 통과")
    print(f"{'='*80}\n")

    return True


def main():
    """전체 테스트 실행"""
    print("\n" + "=" * 80)
    print("Manager Agent Worker Tool 실패 복구 기능 테스트")
    print("=" * 80 + "\n")

    results = []

    try:
        # 테스트 1: 프롬프트 키워드 확인
        results.append(("프롬프트 복구 규칙 포함 확인", test_prompt_contains_recovery_rules()))
    except Exception as e:
        print(f"❌ 테스트 1 실패: {e}")
        results.append(("프롬프트 복구 규칙 포함 확인", False))

    try:
        # 테스트 2: Committer 실패 시나리오
        results.append(("Committer 실패 시나리오", test_history_with_committer_failure()))
    except Exception as e:
        print(f"❌ 테스트 2 실패: {e}")
        results.append(("Committer 실패 시나리오", False))

    try:
        # 테스트 3: Tester 실패 시나리오
        results.append(("Tester 실패 시나리오", test_history_with_tester_failure()))
    except Exception as e:
        print(f"❌ 테스트 3 실패: {e}")
        results.append(("Tester 실패 시나리오", False))

    # 최종 결과
    print("\n" + "=" * 80)
    print("테스트 결과 요약")
    print("=" * 80)

    for test_name, passed in results:
        status = "✅ 통과" if passed else "❌ 실패"
        print(f"{status}: {test_name}")

    total = len(results)
    passed = sum(1 for _, p in results if p)

    print(f"\n총 {total}개 테스트 중 {passed}개 통과 ({passed/total*100:.0f}%)")

    if passed == total:
        print("\n🎉 모든 테스트가 통과했습니다!")
        return 0
    else:
        print(f"\n⚠️ {total - passed}개 테스트가 실패했습니다.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
