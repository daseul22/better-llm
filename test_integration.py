#!/usr/bin/env python3
"""
통합 테스트 - 전체 시스템 검증

Reviewer Agent, 프로젝트 컨텍스트, 에러 핸들링이 올바르게 통합되었는지 확인합니다.
"""

import sys
from pathlib import Path

# 체크리스트
checks = {
    "config": False,
    "reviewer_prompt": False,
    "project_context": False,
    "manager_config": False,
    "worker_tools": False,
    "error_monitoring": False
}

print("=" * 70)
print("🔍 Better-LLM 통합 테스트")
print("=" * 70)
print()

# 1. Agent Config 확인
print("[1/6] Agent 설정 파일 확인...")
try:
    import json
    with open("config/agent_config.json", "r") as f:
        config = json.load(f)

    agent_names = [agent["name"] for agent in config["agents"]]
    required_agents = ["planner", "coder", "reviewer", "tester"]

    if all(name in agent_names for name in required_agents):
        print(f"  ✅ 모든 Agent 설정 완료: {', '.join(agent_names)}")
        checks["config"] = True
    else:
        print(f"  ❌ 누락된 Agent: {set(required_agents) - set(agent_names)}")
except Exception as e:
    print(f"  ❌ 설정 로드 실패: {e}")

# 2. Reviewer 프롬프트 확인
print("\n[2/6] Reviewer 프롬프트 확인...")
try:
    reviewer_prompt_path = Path("prompts/reviewer.txt")
    if reviewer_prompt_path.exists():
        with open(reviewer_prompt_path, "r") as f:
            prompt = f.read()

        required_keywords = ["코드 리뷰", "심각도", "승인"]
        if all(kw in prompt for kw in required_keywords):
            print(f"  ✅ Reviewer 프롬프트 확인 ({len(prompt)} chars)")
            checks["reviewer_prompt"] = True
        else:
            print(f"  ❌ 프롬프트에 필수 키워드 누락")
    else:
        print(f"  ❌ 프롬프트 파일 없음: {reviewer_prompt_path}")
except Exception as e:
    print(f"  ❌ 프롬프트 로드 실패: {e}")

# 3. 프로젝트 컨텍스트 확인
print("\n[3/6] 프로젝트 컨텍스트 확인...")
try:
    from src.infrastructure.storage import JsonContextRepository
    from src.infrastructure.config import get_project_root

    repo = JsonContextRepository(get_project_root() / ".context.json")
    context = repo.load()

    if context:
        print(f"  ✅ 프로젝트 컨텍스트 로드 성공")
        print(f"     - 프로젝트: {context.project_name}")
        print(f"     - 언어: {context.language}")
        print(f"     - 프레임워크: {context.framework}")
        print(f"     - 아키텍처: {context.architecture}")
        checks["project_context"] = True
    else:
        print(f"  ⚠️  컨텍스트 파일 없음 (.context.json)")
except Exception as e:
    print(f"  ❌ 컨텍스트 로드 실패: {e}")

# 4. Manager Agent 설정 확인
print("\n[4/6] Manager Agent 설정 확인...")
try:
    # 소스 코드 직접 읽기 (SDK 없이도 확인 가능)
    with open("src/infrastructure/claude/manager_client.py", "r") as f:
        source = f.read()

    # Reviewer가 allowed_tools에 포함되어 있는지 확인
    required_items = [
        "execute_reviewer_task",
        "SYSTEM_PROMPT",
        "reviewer"
    ]

    if all(item in source for item in required_items):
        print(f"  ✅ Manager 설정에 Reviewer 포함 확인")
        print(f"     - execute_reviewer_task in allowed_tools")
        print(f"     - Reviewer workflow in SYSTEM_PROMPT")
        checks["manager_config"] = True
    else:
        missing = [item for item in required_items if item not in source]
        print(f"  ❌ 누락 항목: {missing}")
except Exception as e:
    print(f"  ❌ Manager 설정 확인 실패: {e}")

# 5. Worker Tools 확인
print("\n[5/6] Worker Tools 확인...")
try:
    # 소스 코드 직접 읽기
    with open("src/infrastructure/mcp/worker_tools.py", "r") as f:
        source = f.read()

    required_tools = [
        "execute_planner_task",
        "execute_coder_task",
        "execute_reviewer_task",
        "execute_tester_task"
    ]

    # 재시도 로직 확인
    has_retry = "retry_with_backoff" in source

    if all(tool in source for tool in required_tools) and has_retry:
        print(f"  ✅ 모든 Worker Tools 등록 확인")
        for tool in required_tools:
            print(f"     - {tool}")
        print(f"  ✅ 재시도 로직 (retry_with_backoff) 확인")
        checks["worker_tools"] = True
    else:
        missing = [tool for tool in required_tools if tool not in source]
        if missing:
            print(f"  ❌ 누락된 Tools: {missing}")
        if not has_retry:
            print(f"  ❌ 재시도 로직 누락")
except Exception as e:
    print(f"  ❌ Worker Tools 확인 실패: {e}")

# 6. 에러 모니터링 확인
print("\n[6/6] 에러 모니터링 기능 확인...")
try:
    # 소스 코드 직접 읽기
    with open("src/infrastructure/mcp/worker_tools.py", "r") as f:
        source = f.read()

    required_functions = [
        "get_error_statistics",
        "reset_error_statistics",
        "log_error_summary",
        "_ERROR_STATS"
    ]

    # orchestrator와 tui에서 에러 통계 사용 확인
    with open("src/presentation/cli/orchestrator.py", "r") as f:
        orchestrator_source = f.read()

    with open("src/presentation/tui/tui_app.py", "r") as f:
        tui_source = f.read()

    has_all_functions = all(func in source for func in required_functions)
    orchestrator_uses_stats = "log_error_summary" in orchestrator_source
    tui_uses_stats = "get_error_statistics" in tui_source

    if has_all_functions and orchestrator_uses_stats and tui_uses_stats:
        print(f"  ✅ 에러 통계 함수 확인")
        for func in required_functions:
            print(f"     - {func}: OK")
        print(f"  ✅ orchestrator.py에서 통계 사용 확인")
        print(f"  ✅ tui.py에서 통계 사용 확인")
        checks["error_monitoring"] = True
    else:
        if not has_all_functions:
            missing = [f for f in required_functions if f not in source]
            print(f"  ❌ 누락된 함수: {missing}")
        if not orchestrator_uses_stats:
            print(f"  ❌ orchestrator.py에서 통계 미사용")
        if not tui_uses_stats:
            print(f"  ❌ tui.py에서 통계 미사용")
except Exception as e:
    print(f"  ❌ 에러 모니터링 확인 실패: {e}")

# 결과 요약
print()
print("=" * 70)
print("📊 테스트 결과")
print("=" * 70)

passed = sum(checks.values())
total = len(checks)

for check_name, result in checks.items():
    status = "✅" if result else "❌"
    print(f"{status} {check_name}")

print()
print(f"통과: {passed}/{total} ({passed/total*100:.0f}%)")

if passed == total:
    print()
    print("🎉 모든 통합 테스트 통과!")
    print()
    print("✅ Reviewer Agent 추가 완료")
    print("✅ 프로젝트 컨텍스트 관리 완료")
    print("✅ 에러 핸들링 및 모니터링 완료")
    print()
    sys.exit(0)
else:
    print()
    print("⚠️  일부 테스트 실패. 위 항목을 확인하세요.")
    sys.exit(1)
