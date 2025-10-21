"""
매니저 에이전트 - 사용자와 대화하고 작업을 계획

ManagerAgent: Claude Agent SDK를 사용하여 Worker Tool들을 호출하고 작업 조율
"""

from typing import List, Optional
import logging
import os

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

## ⚠️ Worker Tool 호출 시 필수 규칙 (컨텍스트 전달)

**중요**: Worker Agent는 대화 히스토리를 볼 수 없습니다!
각 Worker는 오직 `task_description` 파라미터로 전달된 내용만 볼 수 있습니다.
따라서 **반드시 task_description에 이전 Worker의 결과를 포함해야 합니다**.

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
1. execute_planner_task → 병렬 실행 계획 JSON 생성 (execution_mode: "parallel")
2. execute_parallel_tasks → Planner의 JSON을 받아서 Task들을 병렬 실행
   - 의존성 그래프 기반으로 레벨별 병렬 실행
   - 독립적인 Task들은 동시에 실행되어 속도 향상
3. execute_reviewer_task → 통합 코드 리뷰
4. execute_tester_task → 전체 테스트

**병렬 실행 판단 기준**:
- Planner가 JSON 형식으로 "execution_mode": "parallel"을 출력하면 병렬 실행
- 그렇지 않으면 기존 방식대로 순차 실행

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

        self.logger.info(
            "ManagerAgent initialized",
            model=self.model,
            max_history_messages=self.max_history_messages,
            auto_commit_enabled=self.auto_commit_enabled,
            max_review_cycles=self.max_review_cycles
        )

    def _build_prompt_from_history(self, history: List[Message]) -> str:
        """
        대화 히스토리를 프롬프트 텍스트로 변환 (슬라이딩 윈도우 적용)

        Args:
            history: 대화 히스토리

        Returns:
            프롬프트 문자열
        """
        # 시스템 프롬프트로 시작
        prompt_parts = [self.SYSTEM_PROMPT, "\n\n## 대화 히스토리:\n"]

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
                prompt_parts.append(f"\n[{msg.agent_name} Tool 완료]\n{msg.content}\n")
            elif msg.role == "manager":
                # 매니저 자신의 이전 응답
                prompt_parts.append(f"\n[매니저 (당신)]\n{msg.content}\n")

        prompt_parts.append("\n다음 단계를 수행해주세요:")

        return "".join(prompt_parts)

    def _update_token_usage(self, usage_dict: dict) -> None:
        """토큰 사용량 업데이트.

        Args:
            usage_dict: 토큰 사용량 딕셔너리
        """
        if 'input_tokens' in usage_dict:
            self.total_input_tokens += usage_dict['input_tokens']
        if 'output_tokens' in usage_dict:
            self.total_output_tokens += usage_dict['output_tokens']
        if 'cache_read_tokens' in usage_dict:
            self.total_cache_read_tokens += usage_dict['cache_read_tokens']
        if 'cache_creation_tokens' in usage_dict:
            self.total_cache_creation_tokens += usage_dict['cache_creation_tokens']

        self.logger.debug(
            "Token usage updated",
            input_tokens=self.total_input_tokens,
            output_tokens=self.total_output_tokens,
            cache_read_tokens=self.total_cache_read_tokens,
            cache_creation_tokens=self.total_cache_creation_tokens
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

        # SDK 실행 설정
        config = SDKExecutionConfig(
            model=self.model,
            cli_path=get_claude_cli_path(),
            permission_mode="bypassPermissions"
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
            session_id=self.session_id
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

    def __repr__(self) -> str:
        return f"ManagerAgent(model={self.model})"
