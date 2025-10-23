"""
매니저 에이전트 - 사용자와 대화하고 작업을 계획

ManagerAgent: Claude Agent SDK를 사용하여 Worker Tool들을 호출하고 작업 조율
"""

from typing import List, Optional, Dict
import logging
import os

from anthropic import Anthropic
from claude_agent_sdk import ClaudeSDKClient
from claude_agent_sdk.types import ClaudeAgentOptions

from src.domain.models import Message
from ..config import get_claude_cli_path
from ..logging import get_logger, log_exception_silently
from .sdk_executor import (
    SDKExecutionConfig,
    ManagerResponseHandler,
    ManagerSDKExecutor
)

logger = get_logger(__name__)


class ManagerAgent:
    """
    사용자와 대화하는 매니저 에이전트

    Claude Agent SDK를 사용하여 사용자 요청을 분석하고,
    Worker Tool들을 호출하여 작업을 수행합니다.

    Attributes:
        model: 사용할 Claude 모델
        worker_tools_server: Worker Tools MCP 서버
        auto_commit_enabled: Git 커밋 자동 생성 활성화 여부
    """

    @property
    def SYSTEM_PROMPT(self) -> str:
        """
        시스템 프롬프트 생성 (auto_commit_enabled 설정 반영)

        Returns:
            시스템 프롬프트 문자열
        """
        # 기본 프롬프트
        base_prompt = """당신은 소프트웨어 개발 프로젝트를 관리하는 매니저입니다.

## 역할
- 사용자 요청을 분석하고 이해합니다
- 작업을 계획하고 우선순위를 정합니다
- Worker Agent Tool을 호출하여 작업을 할당합니다
- 진행 상황을 사용자에게 보고합니다

## 사용 가능한 Tool
다음 Tool들을 사용할 수 있습니다:
- **execute_ideator_task**: 창의적 아이디어 생성 및 브레인스토밍 (기획 초기 단계)
- **execute_product_manager_task**: 제품 요구사항 정의 및 우선순위 설정 (기획 단계)
- **execute_planner_task**: 요구사항 분석 및 구현 계획 수립 (설계 단계)
- **execute_parallel_tasks**: 병렬 작업 실행 (Planner가 병렬 실행 계획 JSON을 생성한 경우)
- **execute_coder_task**: 코드 작성, 수정, 리팩토링
- **execute_reviewer_task**: 코드 리뷰 및 품질 검증
- **execute_tester_task**: 테스트 작성 및 실행"""

        # auto_commit_enabled에 따라 committer 관련 내용 추가
        if self.auto_commit_enabled:
            base_prompt += """
- **execute_committer_task**: Git 커밋 생성 (테스트 성공 후)"""

        base_prompt += """
- **read**: 파일 읽기 (필요 시)
- **ask_user**: 사용자에게 질문하고 응답 받기 (interaction.enabled가 true일 때만 사용 가능)

## 작업 수행 방법
1. 사용자 요청을 분석합니다
2. 필요한 Worker Tool을 순차적으로 호출합니다
3. **각 Worker Tool의 결과는 대화 히스토리에 자동으로 기록됩니다**
   - 형식: `[{Worker 이름} Tool 완료]\n{Worker 실행 결과}\n`
   - Planner의 상세 계획, Coder의 구현 내용, Reviewer의 피드백 등이 모두 포함됩니다
4. **중요 결정이 필요할 때는 ask_user Tool로 사용자에게 물어봅니다**
   - 예: Planner가 여러 옵션(A안/B안)을 제시한 경우
   - 예: 위험한 작업(대량 삭제, 주요 아키텍처 변경)을 수행하기 전
5. 모든 작업이 완료되면 사용자에게 결과를 보고합니다

## 📦 Artifact Storage 시스템

Worker Tool 실행 시 **전체 출력은 artifact 파일로 저장**되고, **요약만 대화 히스토리에 포함**됩니다.

**Artifact 형식**:
- 각 Worker 출력 말미: [전체 로그: artifact `{worker_name}_{timestamp}`]
- 저장 위치: ~/.better-llm/{project}/artifacts/{artifact_id}.txt

**Artifact 활용 방법**:
1. **일반적인 경우**: 요약만으로 충분합니다. 다음 Worker에게 요약을 전달하세요.
2. **상세 정보 필요 시**: Worker에게 artifact 파일 읽기를 지시하세요.
   ```
   execute_coder_task({
     "task_description": "다음 계획에 따라 코드를 작성하세요:\n\n[Planner 요약]\n\n상세 계획은 ~/.better-llm/my-project/artifacts/planner_20250121_143025.txt 파일을 read 도구로 읽어보세요."
   })
   ```

**주의**: Worker는 read 도구로 artifact 파일을 직접 읽을 수 있습니다.

## ⚠️ Worker Tool 호출 시 필수 규칙 (컨텍스트 전달)

**중요**: Worker Agent는 대화 히스토리를 볼 수 없습니다!
각 Worker는 오직 `task_description` 파라미터로 전달된 내용만 볼 수 있습니다.
따라서 **반드시 task_description에 이전 Worker의 결과를 포함해야 합니다**.

**컨텍스트 절약**:
- 히스토리에는 **요약만 저장**되어 Manager의 컨텍스트 윈도우를 절약합니다.
- 요약만으로도 대부분의 경우 충분합니다 (핵심 정보 포함).
- 상세 정보가 필요한 경우에만 Worker에게 artifact 파일 읽기를 지시하세요.

### 올바른 Worker Tool 호출 방법:

1. **execute_planner_task**: 사용자 요청을 그대로 전달
   ```
   execute_planner_task({
     "task_description": "{사용자 요청 원문}"
   })
   ```

2. **execute_coder_task**: Planner의 계획을 반드시 포함
   ```
   execute_coder_task({
     "task_description": "다음 계획에 따라 코드를 작성해주세요:\n\n{히스토리의 [planner Tool 완료] 내용 전체}"
   })
   ```

3. **execute_reviewer_task**: Coder의 구현 내용을 반드시 포함
   ```
   execute_reviewer_task({
     "task_description": "다음 코드를 리뷰해주세요:\n\n{히스토리의 [coder Tool 완료] 내용 전체}"
   })
   ```

4. **execute_tester_task**: Coder의 구현 내용을 반드시 포함
   ```
   execute_tester_task({
     "task_description": "다음 코드를 테스트해주세요:\n\n{히스토리의 [coder Tool 완료] 내용 전체}"
   })
   ```

5. **execute_committer_task**: Tester의 결과를 반드시 포함
   ```
   execute_committer_task({
     "task_description": "다음 테스트 결과를 확인하고 커밋해주세요:\n\n{히스토리의 [tester Tool 완료] 내용 전체}"
   })
   ```

**잘못된 예시** (절대 이렇게 하지 마세요!):
```
❌ execute_coder_task({"task_description": "FastAPI CRUD API 작성"})
   → Coder가 Planner의 계획을 볼 수 없어서 제대로 구현할 수 없음!

✅ execute_coder_task({"task_description": "다음 계획에 따라 코드를 작성해주세요:\n\n[planner Tool 완료]\n{Planner의 상세 계획 전체}"})
   → Coder가 계획을 보고 정확히 구현할 수 있음
```

## ask_user Tool 사용 가이드
- **언제 사용**: Worker(특히 Planner)가 여러 선택지를 제시하거나 중요한 결정이 필요할 때
- **사용 방법**:
  ```
  ask_user({
    "question": "Planner가 두 가지 접근 방법을 제시했습니다. 어느 방법을 선택하시겠습니까?",
    "options": [
      "A안: 기존 시스템 확장 (빠르지만 기술부채 증가)",
      "B안: 새로운 모듈 분리 (시간 걸리지만 확장성 좋음)"
    ]
  })
  ```
- **주의**: interaction.enabled가 false면 사용할 수 없습니다 (자동으로 첫 번째 옵션 선택)

## 표준 작업 흐름

### 기본 개발 작업 (순차 실행):
1. execute_planner_task → 요구사항 분석 및 구현 계획
2. execute_coder_task → 코드 작성
3. execute_reviewer_task → 코드 리뷰 (품질 검증)
4. execute_tester_task → 테스트 작성 및 실행

### 병렬 실행 가능한 작업 (3개 이상의 독립적인 파일 생성):
1. execute_planner_task → 병렬 실행 계획 생성
   - Planner는 **텍스트 요약 + JSON 병렬 실행 계획**을 함께 출력
   - JSON 형식: `{"execution_mode": "parallel", "tasks": [...], "integration_notes": "..."}`
2. **JSON 추출**: Planner 출력에서 ```json ... ``` 블록 찾기
3. execute_parallel_tasks → JSON을 받아서 Task들을 병렬 실행
   - 의존성 그래프 기반 레벨별 병렬 실행 (속도 향상 20~50%)
   - 독립적인 Task들은 동시에 실행
4. execute_reviewer_task → 통합 코드 리뷰
5. execute_tester_task → 전체 테스트

**병렬 실행 자동 트리거 방법**:
1. Planner 실행 후 출력에 ```json으로 시작하는 코드 블록이 있는지 확인
2. JSON에서 `"execution_mode": "parallel"` 발견 시:
   ```
   execute_parallel_tasks({
     "plan_json": "{전체 JSON 문자열}"
   })
   ```
3. JSON이 없거나 `"execution_mode": "sequential"`인 경우:
   - 기존 방식대로 execute_coder_task 순차 호출

**예시 (병렬 실행)**:
```
# Planner 출력 예시:
## 📋 [PLANNER 요약 - Manager 전달용]
... (텍스트 요약) ...

```json
{
  "execution_mode": "parallel",
  "tasks": [
    {"id": "task_1", "description": "...", ...},
    {"id": "task_2", "description": "...", ...}
  ]
}
```

# Manager의 다음 호출:
execute_parallel_tasks({"plan_json": "{...JSON 전체...}"})
```

### 새로운 기능 기획 시 (선택적):
0. execute_ideator_task → 창의적 아이디어 브레인스토밍 (필요 시)
0. execute_product_manager_task → 요구사항 정의 및 우선순위 (필요 시)
1. execute_planner_task → 구현 계획 수립
2. execute_coder_task 또는 execute_parallel_tasks → 코드 작성
... (이후 동일)"""

        if self.auto_commit_enabled:
            base_prompt += """
5. execute_committer_task → Git 커밋 생성 (테스트 성공 시)"""

        base_prompt += """

**중요**:
- Reviewer가 Critical 이슈를 발견하면 Coder에게 수정 요청 후 다시 Review
- **무한 루프 방지**: Review → Coder → Review 사이클은 최대 3회까지만 허용
  - 3회 반복 후에도 Critical 이슈가 남으면 사용자에게 수동 개입 요청
  - 반복 횟수를 명시적으로 추적하세요 (예: "Review 사이클 1/3")"""

        if self.auto_commit_enabled:
            base_prompt += """
- Committer는 Tester가 성공한 경우에만 실행하세요
- Committer 실행 여부는 작업 성격에 따라 판단하세요 (새 기능, 버그 수정 등은 커밋 권장)"""

        base_prompt += """

## 예시 (올바른 Worker Tool 호출)

**사용자**: "FastAPI로 /users CRUD API를 작성해줘"

**1단계: Planner 호출**
```
execute_planner_task({
  "task_description": "FastAPI로 /users CRUD API를 작성해줘"
})
```
→ Planner 결과가 히스토리에 저장됨: [planner Tool 완료]\n{상세 계획}\n

**2단계: Coder 호출** (⚠️ Planner 계획을 반드시 포함!)
```
execute_coder_task({
  "task_description": "다음 계획에 따라 FastAPI CRUD API를 작성해주세요:\n\n[planner Tool 완료]\n{Planner가 제시한 상세 계획 전체 - 파일 구조, API 엔드포인트, 모델 정의 등}"
})
```
→ Coder 결과가 히스토리에 저장됨: [coder Tool 완료]\n{구현 내용}\n

**3단계: Reviewer 호출** (⚠️ Coder 구현을 반드시 포함!)
```
execute_reviewer_task({
  "task_description": "다음 코드를 리뷰해주세요:\n\n[coder Tool 완료]\n{Coder가 작성한 코드 전체 - 파일 경로, 코드 내용 등}"
})
```
→ Critical 이슈 발견 시:
  - execute_coder_task로 수정 (Review 결과를 포함하여 호출!)
  - 다시 execute_reviewer_task
→ 승인 시: 다음 단계 진행

**4단계: Tester 호출** (⚠️ Coder 구현을 반드시 포함!)
```
execute_tester_task({
  "task_description": "다음 코드를 테스트해주세요:\n\n[coder Tool 완료]\n{Coder가 작성한 코드 전체}"
})
```"""

        if self.auto_commit_enabled:
            base_prompt += """
5단계: execute_committer_task 호출 → Git 커밋 (테스트 성공 시)
6단계: 사용자에게 완료 보고"""
        else:
            base_prompt += """
5단계: 사용자에게 완료 보고"""

        base_prompt += """

## 규칙
- Tool을 직접 호출하세요 (@ 표기 불필요)
- 각 Tool 호출 전에 무엇을 할 것인지 설명하세요
- Reviewer의 피드백을 반드시 반영하세요 (Critical 이슈는 필수 수정)
- Tool 결과를 확인하고 문제가 있으면 재시도하세요
- 모든 작업이 완료되면 "작업이 완료되었습니다"라고 명시하세요

## ⚠️ 중복 작업 방지 규칙 (CRITICAL!)

**매우 중요**: 각 Worker는 한 번만 실행되어야 합니다 (재시도 제외).

**작업 흐름 추적 방법**:
1. **대화 히스토리를 반드시 확인**하여 이미 실행된 Worker를 파악하세요
2. 히스토리에 "[{Worker 이름} Tool 완료]" 또는 "📋 [{Worker 이름} 요약]" 형식의 메시지가 있으면 해당 Worker는 **이미 실행된 것**입니다
3. Worker가 이미 실행되었다면 **절대 다시 호출하지 마세요** - 다음 단계로 진행하세요
4. **예외 (재호출 허용)**:
   - Reviewer가 Critical 이슈를 발견하여 Coder 재실행이 필요한 경우만 재호출 가능
   - 이 경우에도 Review 사이클 제한(3회)을 준수하세요

**잘못된 패턴 (절대 금지!)**:
```
❌ 사용자 요청 → Planner → Coder → Reviewer → Planner (다시 호출!)
   → Planner는 이미 실행되었으므로 다시 호출하면 안 됩니다.

❌ 사용자 요청 → Planner → Coder → Planner (다시 호출!)
   → Planner 후에는 Coder 결과를 기다렸다가 다음 단계(Reviewer/Tester)로 진행해야 합니다.
```

**올바른 패턴**:
```
✅ 사용자 요청 → Planner → Coder → Reviewer → Tester → 완료
   → 각 Worker가 한 번씩만 실행되어 순차 진행됨

✅ 사용자 요청 → Planner → Coder → Reviewer (Critical 발견) → Coder (수정) → Reviewer → Tester
   → Coder만 재실행되었고(Review 사이클), 나머지는 순차 진행됨
```

**각 응답 전 체크리스트**:
- [ ] 히스토리에서 이미 실행된 Worker 확인 (검색 키워드: "Tool 완료", "요약")
- [ ] 다음 단계가 올바른지 확인 (순차 진행: Planner → Coder → Reviewer → Tester)
- [ ] 재호출이 필요한 경우 명확한 이유 제시 (Review Critical 이슈만 허용)

## 무한 루프 방지 규칙
- Review → Coder → Review 사이클을 추적하세요
- 최대 반복 횟수: 3회
- 사이클 진행 시마다 "Review 사이클 X/3" 형태로 표시
- 3회 초과 시 다음 메시지를 출력하고 중단:
  "⚠️ Review 사이클이 3회를 초과했습니다. 수동 개입이 필요합니다.
   Critical 이슈: [이슈 요약]
   다음 단계: 사용자가 직접 코드를 수정하거나 요구사항을 조정해주세요."
"""

        return base_prompt

    def __init__(
        self,
        worker_tools_server,
        model: str = "claude-sonnet-4-5-20250929",
        max_history_messages: int = 20,
        auto_commit_enabled: bool = False,
        session_id: Optional[str] = None
    ):
        """
        Args:
            worker_tools_server: Worker Tools MCP 서버
            model: 사용할 Claude 모델
            max_history_messages: 프롬프트에 포함할 최대 히스토리 메시지 수 (슬라이딩 윈도우)
            auto_commit_enabled: Git 커밋 자동 생성 활성화 여부
            session_id: 세션 ID (로깅용, 선택사항)
        """
        self.model = model
        self.worker_tools_server = worker_tools_server
        self.max_history_messages = max_history_messages
        self.auto_commit_enabled = auto_commit_enabled
        self.session_id = session_id or "unknown"

        # 세션 컨텍스트를 포함한 로거 생성
        self.logger = get_logger(__name__, session_id=self.session_id, component="ManagerAgent")

        # Review cycle 추적 변수 (무한 루프 방지)
        self.review_cycle_count = 0

        # 토큰 사용량 추적
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cache_read_tokens = 0
        self.total_cache_creation_tokens = 0

        # Anthropic 클라이언트 (count_tokens API용)
        self._anthropic_client = None

        # 토큰 관리 설정 로드
        self.token_config = self._load_token_management_config()

        # Context metadata formatter (lazy import to avoid circular dependency)
        self.metadata_formatter = None
        self.context_metadata_enabled = self._load_context_metadata_config()

        # Initialize metadata formatter if enabled
        if self.context_metadata_enabled:
            from ..mcp.context_metadata_formatter import ContextMetadataFormatter
            self.metadata_formatter = ContextMetadataFormatter()

        # system_config.json에서 max_review_iterations 로드
        try:
            from ..config import load_system_config
            config = load_system_config()
            self.max_review_cycles = config.get("workflow_limits", {}).get(
                "max_review_iterations", 3
            )
        except Exception as e:
            self.logger.warning(
                "Failed to load max_review_iterations from config",
                error=str(e),
                default_value=3
            )
            self.max_review_cycles = 3

        # system_config.json에서 컨텍스트 관리 옵션 로드
        try:
            context_config = config.get("context_management", {})

            self.max_turns = context_config.get("max_turns", None)
            self.continue_conversation = context_config.get("continue_conversation", False)
            self.setting_sources = context_config.get(
                "setting_sources", ["user", "project"]
            )

            self.logger.info(
                "Context management options loaded",
                max_turns=self.max_turns,
                continue_conversation=self.continue_conversation,
                setting_sources=self.setting_sources
            )
        except Exception as e:
            self.logger.warning(
                "Failed to load context management options",
                error=str(e),
                using_defaults=True
            )
            self.max_turns = None
            self.continue_conversation = False
            self.setting_sources = ["user", "project"]

        # system_config.json에서 permission_mode 로드
        try:
            permission_config = config.get("permission", {})
            self.permission_mode = permission_config.get("mode", "acceptEdits")

            self.logger.info(
                "Permission mode loaded",
                permission_mode=self.permission_mode
            )
        except Exception as e:
            self.logger.warning(
                "Failed to load permission mode",
                error=str(e),
                using_default="acceptEdits"
            )
            self.permission_mode = "acceptEdits"

        # system_config.json에서 hooks 설정 로드
        try:
            hooks_config = config.get("hooks", {})
            enable_validation = hooks_config.get("enable_validation", True)
            enable_monitoring = hooks_config.get("enable_monitoring", True)

            # Hooks 생성
            if enable_validation or enable_monitoring:
                from .agent_hooks import create_worker_hooks
                self.hooks = create_worker_hooks(enable_validation, enable_monitoring)
                self.logger.info(
                    "Hooks enabled",
                    validation=enable_validation,
                    monitoring=enable_monitoring
                )
            else:
                self.hooks = {}
        except Exception as e:
            self.logger.warning(
                "Failed to load hooks configuration",
                error=str(e),
                hooks_disabled=True
            )
            self.hooks = {}

        self.logger.info(
            "ManagerAgent initialized",
            model=self.model,
            max_history_messages=self.max_history_messages,
            auto_commit_enabled=self.auto_commit_enabled,
            max_review_cycles=self.max_review_cycles,
            context_metadata_enabled=self.context_metadata_enabled
        )

    def _load_token_management_config(self) -> dict:
        """
        system_config.json에서 토큰 관리 설정 로드

        Returns:
            dict: 토큰 관리 설정
        """
        try:
            from ..config import load_system_config
            config = load_system_config()
            token_config = config.get("manager", {}).get("token_management", {})

            # 기본값 설정
            return {
                "enable_token_precheck": token_config.get("enable_token_precheck", True),
                "max_context_tokens": token_config.get("max_context_tokens", 200000),
                "max_output_tokens": token_config.get("max_output_tokens", 8000),
                "context_warning_threshold": token_config.get("context_warning_threshold", 0.7),
                "context_critical_threshold": token_config.get("context_critical_threshold", 0.9)
            }
        except Exception as e:
            self.logger.warning(f"토큰 관리 설정 로드 실패, 기본값 사용: {e}")
            return {
                "enable_token_precheck": True,
                "max_context_tokens": 200000,
                "max_output_tokens": 8000,
                "context_warning_threshold": 0.7,
                "context_critical_threshold": 0.9
            }

    def _load_context_metadata_config(self) -> bool:
        """
        system_config.json에서 context_metadata.enabled 설정 로드

        Returns:
            True: context metadata 활성화
            False: 비활성화 (기본값)
        """
        try:
            from ..config import load_system_config
            config = load_system_config()
            enabled = config.get("context_metadata", {}).get("enabled", False)
            self.logger.debug(
                "Context metadata config loaded",
                enabled=enabled
            )
            return enabled
        except Exception as e:
            self.logger.warning(
                "Failed to load context_metadata config",
                error=str(e),
                default_value=False
            )
            return False

    def _build_prompt_from_history(self, history: List[Message]) -> str:
        """
        대화 히스토리를 프롬프트 텍스트로 변환 (슬라이딩 윈도우 적용)

        Context metadata가 활성화된 경우:
        - 메시지에서 JSON 메타데이터를 파싱
        - 컨텍스트 체인을 구성 (dependencies 기반)
        - 관련 메타데이터만 포함하여 컨텍스트 절약

        Args:
            history: 대화 히스토리

        Returns:
            프롬프트 문자열
        """
        # 시스템 프롬프트로 시작
        prompt_parts = [self.SYSTEM_PROMPT, "\n\n## 대화 히스토리:\n"]

        # Context metadata 파싱 (활성화된 경우)
        metadata_map = {}  # task_id -> (msg, metadata)
        if self.context_metadata_enabled:
            metadata_map = self._parse_context_metadata_from_history(history)

        # 슬라이딩 윈도우: 최근 N개 메시지만 포함
        # 단, 첫 번째 사용자 요청은 항상 포함 (컨텍스트 유지)
        if len(history) > self.max_history_messages:
            # 첫 번째 사용자 메시지 + 최근 메시지들
            first_user_msg = next((msg for msg in history if msg.role == "user"), None)
            recent_messages = history[-(self.max_history_messages - 1):]

            if first_user_msg and first_user_msg not in recent_messages:
                messages_to_include = [first_user_msg] + recent_messages
                prompt_parts.append("\n[참고: 초기 요청과 최근 대화만 표시]\n")
            else:
                messages_to_include = recent_messages
        else:
            messages_to_include = history

        for msg in messages_to_include:
            if msg.role == "user":
                prompt_parts.append(f"\n[사용자]\n{msg.content}\n")
            elif msg.role == "agent":
                # 워커 Tool의 실행 결과
                # Context metadata가 있으면 요약 레벨을 활용
                if self.context_metadata_enabled:
                    content = self._format_message_with_metadata(msg, metadata_map)
                else:
                    content = msg.content

                prompt_parts.append(f"\n[{msg.agent_name} Tool 완료]\n{content}\n")
            elif msg.role == "manager":
                # 매니저 자신의 이전 응답
                prompt_parts.append(f"\n[매니저 (당신)]\n{msg.content}\n")

        prompt_parts.append("\n다음 단계를 수행해주세요:")

        return "".join(prompt_parts)

    def _parse_context_metadata_from_history(
        self,
        history: List[Message]
    ) -> dict:
        """
        히스토리에서 컨텍스트 메타데이터 파싱

        Args:
            history: 대화 히스토리

        Returns:
            메타데이터 맵 {task_id: (msg, metadata)}
        """
        metadata_map = {}

        # metadata_formatter가 None이면 빈 맵 반환 (방어적 프로그래밍)
        if not self.metadata_formatter:
            return metadata_map

        for msg in history:
            if msg.role == "agent":
                metadata = self.metadata_formatter.parse_metadata_from_output(msg.content)
                if metadata:
                    metadata_map[metadata.task_id] = (msg, metadata)

        self.logger.debug(
            "Context metadata parsed from history",
            total_messages=len(history),
            metadata_count=len(metadata_map)
        )

        return metadata_map

    def _format_message_with_metadata(
        self,
        msg: Message,
        metadata_map: dict
    ) -> str:
        """
        메타데이터를 활용하여 메시지 포맷팅

        메타데이터가 있으면 five_line 요약 레벨을 사용하여 컨텍스트 절약.
        메타데이터가 없으면 원본 메시지 그대로 반환.

        Args:
            msg: 메시지
            metadata_map: 메타데이터 맵

        Returns:
            포맷팅된 메시지 내용
        """
        # 메시지에서 메타데이터 추출
        metadata = self.metadata_formatter.parse_metadata_from_output(msg.content)

        if not metadata:
            # 메타데이터 없음 - 원본 반환
            return msg.content

        # 메타데이터 있음 - five_line 요약 사용
        five_line_summary = metadata.summary_levels.get("five_line", "")
        one_line_summary = metadata.summary_levels.get("one_line", "")
        artifact_path = metadata.summary_levels.get("full", "")

        # 포맷팅된 메시지 생성
        formatted = f"""**요약**: {one_line_summary}

**주요 내용**:
{five_line_summary}

**상세 내용**: {artifact_path}

**메타데이터**:
- Task ID: {metadata.task_id}
- Dependencies: {', '.join(metadata.dependencies) if metadata.dependencies else 'None'}
- Key Decisions: {', '.join(metadata.key_decisions[:3]) if metadata.key_decisions else 'None'}
"""

        self.logger.debug(
            "Message formatted with metadata",
            task_id=metadata.task_id,
            original_length=len(msg.content),
            formatted_length=len(formatted),
            reduction_ratio=f"{(1 - len(formatted)/len(msg.content))*100:.1f}%"
        )

        return formatted

    def _update_token_usage(self, usage_dict: dict) -> None:
        """토큰 사용량 업데이트.

        Args:
            usage_dict: 토큰 사용량 딕셔너리
        """
        self.logger.info(f"[Manager] _update_token_usage called with: {usage_dict}")

        before_input = self.total_input_tokens
        before_output = self.total_output_tokens

        if 'input_tokens' in usage_dict:
            self.total_input_tokens += usage_dict['input_tokens']
        if 'output_tokens' in usage_dict:
            self.total_output_tokens += usage_dict['output_tokens']
        if 'cache_read_tokens' in usage_dict:
            self.total_cache_read_tokens += usage_dict['cache_read_tokens']
        if 'cache_creation_tokens' in usage_dict:
            self.total_cache_creation_tokens += usage_dict['cache_creation_tokens']

        self.logger.info(
            f"[Manager] Token usage updated: "
            f"input {before_input} -> {self.total_input_tokens}, "
            f"output {before_output} -> {self.total_output_tokens}, "
            f"total: {self.total_input_tokens + self.total_output_tokens}"
        )

    async def analyze_and_plan_stream(self, history: List[Message]):
        """
        사용자 요청을 분석하고 작업 수행 (스트리밍)

        Args:
            history: 전체 대화 히스토리

        Yields:
            매니저의 응답 청크 (텍스트만)

        Raises:
            Exception: SDK 호출 실패 시
        """
        # ✅ 컨텍스트 윈도우 사전 체크 (설정에서 활성화된 경우만)
        if self.token_config["enable_token_precheck"]:
            try:
                context_check = self.check_context_window_limit(history)

                # Critical 경고 (90% 초과) 시 실행 차단
                if context_check["critical"]:
                    yield context_check["message"]
                    return

                # Warning 경고 (70% 초과) 시 경고만 표시하고 진행
                if context_check["warning"]:
                    yield context_check["message"]
                    yield "\n\n계속 진행합니다...\n\n"

            except Exception as e:
                # 토큰 체크 실패는 경고만 하고 진행
                self.logger.warning(f"컨텍스트 윈도우 사전 체크 실패: {e}")

        # 대화 히스토리를 프롬프트로 변환
        prompt = self._build_prompt_from_history(history)

        self.logger.debug(
            "Starting Claude Agent SDK call",
            worker_tools_enabled=True,
            working_dir=os.getcwd(),
            history_size=len(history)
        )

        # allowed_tools 리스트 생성 (auto_commit_enabled에 따라 조건부)
        allowed_tools = [
            "mcp__workers__execute_planner_task",
            "mcp__workers__execute_parallel_tasks",  # 병렬 실행
            "mcp__workers__execute_coder_task",
            "mcp__workers__execute_reviewer_task",
            "mcp__workers__execute_tester_task",
            "mcp__workers__execute_ideator_task",  # 아이디어 생성
            "mcp__workers__execute_product_manager_task",  # 제품 기획
            "mcp__workers__ask_user",  # 사용자 입력 (Human-in-the-Loop)
            "read"  # 파일 읽기 툴
        ]

        # auto_commit_enabled가 True일 때만 committer tool 추가
        if self.auto_commit_enabled:
            allowed_tools.append("mcp__workers__execute_committer_task")

        # SDK 실행 설정 (컨텍스트 관리 옵션 포함)
        config = SDKExecutionConfig(
            model=self.model,
            cli_path=get_claude_cli_path(),
            permission_mode=self.permission_mode,  # system_config.json 또는 환경변수에서 로드
            max_turns=self.max_turns,
            continue_conversation=self.continue_conversation,
            setting_sources=self.setting_sources
        )

        # 응답 핸들러 생성 (토큰 사용량 업데이트 콜백 포함)
        response_handler = ManagerResponseHandler(
            usage_callback=self._update_token_usage
        )

        # Executor 생성
        executor = ManagerSDKExecutor(
            config=config,
            mcp_servers={"workers": self.worker_tools_server},
            allowed_tools=allowed_tools,
            response_handler=response_handler,
            session_id=self.session_id,
            hooks=self.hooks  # Hooks 전달
        )

        # 스트림 실행
        async for text in executor.execute_stream(prompt):
            yield text

    def get_token_usage(self) -> dict:
        """
        현재까지의 토큰 사용량 반환

        Returns:
            dict: {
                "input_tokens": int,
                "output_tokens": int,
                "cache_read_tokens": int,
                "cache_creation_tokens": int,
                "total_tokens": int
            }
        """
        return {
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "cache_read_tokens": self.total_cache_read_tokens,
            "cache_creation_tokens": self.total_cache_creation_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens
        }

    def reset_token_usage(self) -> None:
        """토큰 사용량 초기화 (새 세션 시작 시)"""
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cache_read_tokens = 0
        self.total_cache_creation_tokens = 0

    @property
    def anthropic_client(self) -> Anthropic:
        """Lazy-load Anthropic client for count_tokens API"""
        if self._anthropic_client is None:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError(
                    "ANTHROPIC_API_KEY 환경 변수가 설정되지 않았습니다. "
                    "count_tokens API를 사용하려면 API 키가 필요합니다."
                )
            self._anthropic_client = Anthropic(api_key=api_key)
        return self._anthropic_client

    def count_prompt_tokens(self, history: List[Message]) -> Dict[str, int]:
        """
        프롬프트 토큰 수를 정확하게 계산 (Anthropic count_tokens API 사용)

        Args:
            history: 대화 히스토리

        Returns:
            dict: {
                "input_tokens": int,  # 정확한 입력 토큰 수
                "estimated": bool,    # 추정값 여부 (API 실패 시 True)
                "error": str          # 에러 메시지 (있는 경우)
            }
        """
        # 프롬프트 빌드
        prompt = self._build_prompt_from_history(history)

        try:
            # Anthropic 공식 count_tokens API 호출
            response = self.anthropic_client.messages.count_tokens(
                model=self.model,
                system=self.system_prompt,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            input_tokens = response.input_tokens

            # 로깅
            max_context = 200000  # Claude Sonnet 4.5
            usage_percent = (input_tokens / max_context) * 100

            self.logger.info(
                f"[Manager] Prompt token count: {input_tokens:,} tokens "
                f"({usage_percent:.1f}% of context window)"
            )

            return {
                "input_tokens": input_tokens,
                "estimated": False,
                "error": None
            }

        except Exception as e:
            # 폴백: 문자 수 기반 추정 (매우 부정확)
            estimated_tokens = len(prompt) // 3  # 1 토큰 ≈ 3 글자 (한글 기준)

            self.logger.warning(
                f"count_tokens API 호출 실패: {e}. "
                f"문자 수 기반 추정을 사용합니다 (부정확): ~{estimated_tokens:,} tokens"
            )

            return {
                "input_tokens": estimated_tokens,
                "estimated": True,
                "error": str(e)
            }

    def check_context_window_limit(self, history: List[Message]) -> Dict[str, any]:
        """
        컨텍스트 윈도우 사용량을 체크하고 경고 생성

        Args:
            history: 대화 히스토리

        Returns:
            dict: {
                "input_tokens": int,
                "max_context": int,
                "max_input": int,     # 출력 예약 후 최대 입력
                "usage_percent": float,
                "warning": bool,      # 70% 초과
                "critical": bool,     # 90% 초과
                "message": str        # 경고 메시지 (있는 경우)
            }
        """
        # 토큰 수 계산
        result = self.count_prompt_tokens(history)
        input_tokens = result["input_tokens"]
        is_estimated = result["estimated"]

        # 컨텍스트 윈도우 설정 (system_config.json에서 로드)
        max_context = self.token_config["max_context_tokens"]
        reserved_for_output = self.token_config["max_output_tokens"]
        max_input = max_context - reserved_for_output

        usage_percent = (input_tokens / max_input) * 100

        # 경고 체크 (설정 파일의 임계값 사용)
        warning_threshold = self.token_config["context_warning_threshold"]
        critical_threshold = self.token_config["context_critical_threshold"]

        warning = usage_percent > (warning_threshold * 100)
        critical = usage_percent > (critical_threshold * 100)

        # 경고 메시지 생성
        message = None
        if critical:
            message = (
                f"🚨 **컨텍스트 윈도우 긴급 경고**\n"
                f"현재 입력 토큰: {input_tokens:,} / {max_input:,} ({usage_percent:.1f}%)\n"
                f"{'⚠️ 추정값입니다 (API 실패). ' if is_estimated else ''}\n"
                f"컨텍스트 윈도우가 거의 가득 찼습니다. 다음 중 하나를 선택하세요:\n"
                f"1. 이전 메시지 일부 삭제\n"
                f"2. 새로운 대화 시작\n"
                f"3. Worker 출력 요약 강화\n"
            )
            self.logger.error(
                f"[Manager] Context window critical: {input_tokens:,} / {max_input:,} tokens ({usage_percent:.1f}%)"
            )
        elif warning:
            message = (
                f"⚠️ **컨텍스트 윈도우 경고**\n"
                f"현재 입력 토큰: {input_tokens:,} / {max_input:,} ({usage_percent:.1f}%)\n"
                f"{'⚠️ 추정값입니다 (API 실패). ' if is_estimated else ''}\n"
                f"컨텍스트 윈도우 사용량이 70%를 초과했습니다.\n"
            )
            self.logger.warning(
                f"[Manager] Context window warning: {input_tokens:,} / {max_input:,} tokens ({usage_percent:.1f}%)"
            )

        return {
            "input_tokens": input_tokens,
            "max_context": max_context,
            "max_input": max_input,
            "usage_percent": usage_percent,
            "warning": warning,
            "critical": critical,
            "message": message,
            "estimated": is_estimated
        }

    def __repr__(self) -> str:
        return f"ManagerAgent(model={self.model})"
