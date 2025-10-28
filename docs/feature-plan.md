# Better-LLM Web UI 기능 개발 계획

## 개요

이 문서는 Better-LLM Web UI의 고도화 기능 개발 계획을 담고 있습니다. 각 기능은 독립적으로 구현 가능하도록 설계되었으며, 우선순위와 난이도가 명시되어 있습니다.

---

## ✅ 완료된 기능

### 기능 1: 실시간 실행 모니터링 강화 (완료)

**구현 내용**:
- 백엔드: `WorkflowNodeExecutionEvent`에 `timestamp`, `elapsed_time`, `token_usage` 필드 추가
- 백엔드: `WorkflowExecutor`에서 노드별 실행 시간 자동 추적
- 백엔드: `WorkerAgent`에서 토큰 사용량 수집 (usage_callback)
- 프론트엔드: Zustand store에 노드 실행 상태 관리 (`nodeMeta`, `totalTokenUsage`)
- 프론트엔드: WorkerNode에 실행 시간 및 토큰 사용량 UI 표시
- 프론트엔드: SSE 이벤트 핸들러에서 메타데이터 처리

**파일 변경**:
- `src/presentation/web/schemas/workflow.py`
- `src/presentation/web/services/workflow_executor.py`
- `src/presentation/web/frontend/src/stores/workflowStore.ts`
- `src/presentation/web/frontend/src/components/WorkerNode.tsx`
- `src/presentation/web/frontend/src/components/InputNode.tsx`
- `src/presentation/web/frontend/src/lib/api.ts`

### 기능 2: 워크플로우 템플릿 갤러리 (완료)

**구현 내용**:

**백엔드**:
- 템플릿 스키마 정의 (`schemas/template.py`)
  - `Template`, `TemplateMetadata`, `TemplateSaveRequest` 등
- TemplateManager 클래스 구현 (`services/template_manager.py`)
  - 템플릿 CRUD 기능 (목록 조회, 상세 조회, 저장, 삭제)
  - 내장 템플릿과 사용자 템플릿 분리 관리 (builtin vs user)
  - 템플릿 검증 로직 (필수 필드, 노드 연결 유효성)
- 템플릿 API 라우터 (`routers/templates.py`)
  - `GET /api/templates` - 템플릿 목록 조회
  - `GET /api/templates/{id}` - 템플릿 상세 조회
  - `POST /api/templates` - 템플릿 저장
  - `DELETE /api/templates/{id}` - 템플릿 삭제
  - `POST /api/templates/validate` - 템플릿 검증
- 기본 템플릿 4개 제공 (`templates/`)
  - `code_review.json`: Planner → Coder → Reviewer
  - `test_automation.json`: Coder → Tester → Committer
  - `bug_fix.json`: Planner → Coder → Tester
  - `ideation.json`: Ideator → Product Manager → Planner

**프론트엔드**:
- 템플릿 API 클라이언트 (`lib/api.ts`)
  - `getTemplates()`, `getTemplate()`, `saveTemplate()`, `deleteTemplate()`, `validateTemplate()`
- TemplateGallery 컴포넌트 (`components/TemplateGallery.tsx`)
  - 템플릿 카드 UI (이름, 설명, 카테고리, 노드/엣지 수, 태그)
  - 검색 기능 (템플릿 이름, 설명)
  - 카테고리 필터 (code_review, testing, bug_fix, planning 등)
  - 템플릿 선택 시 워크플로우 자동 로드
  - Import 기능 (JSON 파일에서 워크플로우 가져오기)
  - 템플릿 삭제 (내장 템플릿 제외)
- App.tsx에 템플릿 갤러리 통합
  - 헤더에 "템플릿" 버튼 추가
  - 템플릿 갤러리 모달 렌더링
  - 템플릿 로드 시 토스트 알림

**파일 변경**:
- `src/presentation/web/schemas/template.py` (신규)
- `src/presentation/web/services/template_manager.py` (신규)
- `src/presentation/web/routers/templates.py` (신규)
- `src/presentation/web/routers/__init__.py`
- `src/presentation/web/app.py`
- `src/presentation/web/frontend/src/lib/api.ts`
- `src/presentation/web/frontend/src/components/TemplateGallery.tsx` (신규)
- `src/presentation/web/frontend/src/App.tsx`
- `templates/code_review.json` (신규)
- `templates/test_automation.json` (신규)
- `templates/bug_fix.json` (신규)
- `templates/ideation.json` (신규)

**사용 방법**:
1. 웹 서버 실행: `better-llm-web` 또는 `python -m src.presentation.web.app`
2. 브라우저에서 http://localhost:8000 접속
3. 헤더의 "템플릿" 버튼 클릭
4. 원하는 템플릿 선택하거나 JSON 파일에서 가져오기

**커밋**: `2383af5` - feat(web): 워크플로우 템플릿 갤러리 기능 추가

---

## 📋 진행 예정 기능

### 기능 3: 노드 검증 및 에러 힌트

**우선순위**: 중
**난이도**: 중

#### 목표
- 워크플로우 실행 전 검증
- 실시간 에러 힌트 표시
- 템플릿 변수 유효성 검사

#### 구현 계획

##### 3-1. 백엔드: 워크플로우 검증기
**파일**: `src/presentation/web/services/workflow_validator.py` (신규)

```python
from typing import List, Dict, Any
from dataclasses import dataclass

@dataclass
class ValidationError:
    """검증 에러"""
    severity: str  # 'error', 'warning', 'info'
    node_id: str
    message: str
    suggestion: str

class WorkflowValidator:
    """워크플로우 검증기"""

    def validate(self, workflow: Workflow) -> List[ValidationError]:
        """워크플로우 검증"""
        errors = []

        # 1. 순환 참조 검사
        errors.extend(self._check_cycles(workflow))

        # 2. 고아 노드 검사 (연결되지 않은 노드)
        errors.extend(self._check_orphan_nodes(workflow))

        # 3. 템플릿 변수 검증
        errors.extend(self._validate_template_variables(workflow))

        # 4. Worker별 필수 도구 권한 검사
        errors.extend(self._check_worker_tools(workflow))

        return errors

    def _check_cycles(self, workflow: Workflow) -> List[ValidationError]:
        """순환 참조 검사 (DFS)"""
        pass

    def _check_orphan_nodes(self, workflow: Workflow) -> List[ValidationError]:
        """고아 노드 검사"""
        pass

    def _validate_template_variables(self, workflow: Workflow) -> List[ValidationError]:
        """템플릿 변수 유효성 검사 ({{input}}, {{node_X}} 등)"""
        pass

    def _check_worker_tools(self, workflow: Workflow) -> List[ValidationError]:
        """Worker별 필수 도구 확인"""
        pass
```

**태스크**:
- [ ] WorkflowValidator 클래스 구현
- [ ] 각 검증 로직 구현
- [ ] 단위 테스트 작성

##### 3-2. 백엔드: API 엔드포인트
**파일**: `src/presentation/web/routers/workflows.py`

```python
@router.post("/validate")
async def validate_workflow(workflow: Workflow):
    """워크플로우 검증"""
    validator = WorkflowValidator()
    errors = validator.validate(workflow)

    return {
        "valid": len([e for e in errors if e.severity == 'error']) == 0,
        "errors": [e.__dict__ for e in errors]
    }
```

**태스크**:
- [ ] `/api/workflows/validate` 엔드포인트 추가
- [ ] 응답 스키마 정의

##### 3-3. 프론트엔드: 실시간 검증 UI
**파일**: `src/presentation/web/frontend/src/components/WorkflowCanvas.tsx`

```tsx
import { useEffect, useState } from 'react'
import { validateWorkflow } from '@/lib/api'

export function WorkflowCanvas() {
  const [validationErrors, setValidationErrors] = useState([])

  // 노드/엣지 변경 시 자동 검증 (debounce)
  useEffect(() => {
    const timer = setTimeout(() => {
      const workflow = getWorkflow()
      validateWorkflow(workflow).then(setValidationErrors)
    }, 1000)

    return () => clearTimeout(timer)
  }, [nodes, edges])

  // 에러가 있는 노드에 빨간 테두리 표시
  // ...
}
```

**태스크**:
- [ ] 실시간 검증 로직 추가 (debounce 1초)
- [ ] 에러가 있는 노드 시각적 표시 (빨간 테두리, 경고 아이콘)
- [ ] 에러 목록 패널 추가 (하단 또는 우측)
- [ ] 에러 클릭 → 해당 노드로 포커스

##### 3-4. 프론트엔드: 템플릿 변수 프리뷰
**파일**: `src/presentation/web/frontend/src/components/NodeConfigPanel.tsx`

```tsx
function TemplatePreview({ template, nodes }: Props) {
  // {{input}}, {{node_X}} 등을 실제 값으로 치환하여 미리보기
  const preview = renderTemplate(template, { input: "예시 입력", nodes })

  return (
    <div className="bg-gray-100 p-2 rounded">
      <pre className="text-xs">{preview}</pre>
    </div>
  )
}
```

**태스크**:
- [ ] 템플릿 렌더링 함수 구현
- [ ] NodeConfigPanel에 프리뷰 섹션 추가
- [ ] 유효하지 않은 변수 하이라이트

**예상 작업 시간**: 2-3일

---

### 기능 4: 조건부 분기 및 반복 노드

**우선순위**: 중
**난이도**: 상

#### 목표
- Condition 노드: 출력 기반 조건 분기
- Loop 노드: 조건 만족 시까지 반복
- Merge 노드: 여러 분기 결과 통합

#### 구현 계획

##### 4-1. 백엔드: 새로운 노드 타입 추가
**파일**: `src/presentation/web/schemas/workflow.py`

```python
class ConditionNodeData(BaseModel):
    """조건 분기 노드"""
    condition_type: str  # 'contains', 'regex', 'length', 'custom'
    condition_value: str  # 조건 값
    true_path: str  # True 경로 노드 ID
    false_path: str  # False 경로 노드 ID

class LoopNodeData(BaseModel):
    """반복 노드"""
    max_iterations: int = 5  # 최대 반복 횟수
    loop_condition: str  # 반복 조건 (예: "output contains 'success'")
    loop_body_nodes: List[str]  # 반복할 노드 ID 목록

class MergeNodeData(BaseModel):
    """병합 노드"""
    merge_strategy: str  # 'concatenate', 'first', 'last', 'custom'
```

**태스크**:
- [ ] 새로운 노드 데이터 스키마 정의
- [ ] `WorkflowNodeData` Union 타입에 추가

##### 4-2. 백엔드: WorkflowExecutor 확장
**파일**: `src/presentation/web/services/workflow_executor.py`

```python
async def _execute_condition_node(
    self, node: WorkflowNode, node_outputs: Dict[str, str], ...
) -> AsyncIterator[WorkflowNodeExecutionEvent]:
    """조건 노드 실행"""
    node_data: ConditionNodeData = node.data

    # 부모 노드 출력 가져오기
    parent_output = node_outputs.get(parent_id, "")

    # 조건 평가
    result = self._evaluate_condition(node_data, parent_output)

    # 분기 결정
    next_node_id = node_data.true_path if result else node_data.false_path

    # 다음 노드 실행 (재귀적으로)
    # ...

async def _execute_loop_node(
    self, node: WorkflowNode, node_outputs: Dict[str, str], ...
) -> AsyncIterator[WorkflowNodeExecutionEvent]:
    """반복 노드 실행"""
    node_data: LoopNodeData = node.data

    iteration = 0
    while iteration < node_data.max_iterations:
        # 루프 본문 실행
        for body_node_id in node_data.loop_body_nodes:
            # 노드 실행
            pass

        # 조건 평가
        if self._evaluate_condition(node_data.loop_condition, output):
            break

        iteration += 1

    # ...
```

**태스크**:
- [ ] `_execute_condition_node` 메서드 구현
- [ ] `_execute_loop_node` 메서드 구현
- [ ] `_execute_merge_node` 메서드 구현
- [ ] 조건 평가 로직 (`_evaluate_condition`)
- [ ] 무한 루프 방지 로직

##### 4-3. 프론트엔드: 새로운 노드 컴포넌트
**파일**:
- `src/presentation/web/frontend/src/components/ConditionNode.tsx` (신규)
- `src/presentation/web/frontend/src/components/LoopNode.tsx` (신규)
- `src/presentation/web/frontend/src/components/MergeNode.tsx` (신규)

```tsx
// ConditionNode.tsx
export const ConditionNode = memo(({ data }: NodeProps) => {
  return (
    <Card className="min-w-[250px] border-amber-400 bg-amber-50">
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          <GitBranch className="h-4 w-4" />
          조건 분기
        </CardTitle>
      </CardHeader>
      <CardContent>
        {/* 조건 타입 선택 */}
        {/* True/False 경로 표시 */}
      </CardContent>

      {/* 입력 핸들 (위) */}
      <Handle type="target" position={Position.Top} />

      {/* 출력 핸들 (왼쪽: True, 오른쪽: False) */}
      <Handle type="source" position={Position.Left} id="true" />
      <Handle type="source" position={Position.Right} id="false" />
    </Card>
  )
})
```

**태스크**:
- [ ] ConditionNode 컴포넌트 구현
- [ ] LoopNode 컴포넌트 구현
- [ ] MergeNode 컴포넌트 구현
- [ ] WorkflowCanvas에 nodeTypes 등록

##### 4-4. 프론트엔드: 노드 설정 패널
**파일**: `src/presentation/web/frontend/src/components/NodeConfigPanel.tsx`

```tsx
function ConditionNodeConfig({ nodeId }: Props) {
  return (
    <div>
      <Select label="조건 타입">
        <option value="contains">텍스트 포함</option>
        <option value="regex">정규표현식</option>
        <option value="length">길이 비교</option>
      </Select>

      <Input label="조건 값" />

      <Select label="True 경로">
        {/* 다음 노드 선택 */}
      </Select>

      <Select label="False 경로">
        {/* 다음 노드 선택 */}
      </Select>
    </div>
  )
}
```

**태스크**:
- [ ] 각 노드 타입별 설정 UI 구현
- [ ] NodeConfigPanel에 통합

**예상 작업 시간**: 5-7일 (복잡도 높음)

---

### 기능 5: 변수 및 컨텍스트 관리

**우선순위**: 중
**난이도**: 상

#### 목표
- 워크플로우 전역 변수 시스템
- 노드 간 구조화된 데이터 전달
- 파일 첨부 기능

#### 구현 계획

##### 5-1. 백엔드: 변수 시스템
**파일**: `src/presentation/web/services/workflow_executor.py`

```python
class WorkflowContext:
    """워크플로우 실행 컨텍스트"""

    def __init__(self):
        self.variables: Dict[str, Any] = {}
        self.files: Dict[str, Path] = {}

    def set_variable(self, key: str, value: Any):
        """변수 설정"""
        self.variables[key] = value

    def get_variable(self, key: str, default: Any = None) -> Any:
        """변수 조회"""
        return self.variables.get(key, default)

    def attach_file(self, key: str, file_path: Path):
        """파일 첨부"""
        self.files[key] = file_path

class WorkflowExecutor:
    async def execute_workflow(self, workflow, initial_input, session_id):
        # 컨텍스트 초기화
        context = WorkflowContext()
        context.set_variable("input", initial_input)

        # 노드 실행 시 컨텍스트 전달
        for node in sorted_nodes:
            # 변수 치환
            task_description = self._render_task_with_context(
                node.data.task_template,
                context
            )
            # ...

    def _render_task_with_context(self, template: str, context: WorkflowContext) -> str:
        """변수 치환 ({{var:key}} 형식)"""
        import re

        def replace_var(match):
            var_name = match.group(1)
            return str(context.get_variable(var_name, f"{{UNDEFINED:{var_name}}}"))

        return re.sub(r'\{\{var:(\w+)\}\}', replace_var, template)
```

**태스크**:
- [ ] WorkflowContext 클래스 구현
- [ ] WorkflowExecutor에 컨텍스트 통합
- [ ] 변수 설정 구문 파싱 (`{{set:key=value}}`)
- [ ] 변수 참조 구문 파싱 (`{{var:key}}`)
- [ ] 파일 첨부 API

##### 5-2. 프론트엔드: 변수 관리 UI
**파일**: `src/presentation/web/frontend/src/components/VariablePanel.tsx` (신규)

```tsx
export function VariablePanel() {
  const [variables, setVariables] = useState<Record<string, string>>({})

  return (
    <Card>
      <CardHeader>
        <CardTitle>전역 변수</CardTitle>
      </CardHeader>
      <CardContent>
        {Object.entries(variables).map(([key, value]) => (
          <div key={key} className="flex gap-2">
            <Input value={key} readOnly />
            <Input value={value} onChange={/* ... */} />
            <Button variant="ghost" size="sm">
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        ))}

        <Button onClick={/* 변수 추가 */}>
          + 변수 추가
        </Button>
      </CardContent>
    </Card>
  )
}
```

**태스크**:
- [ ] VariablePanel 컴포넌트 구현
- [ ] WorkflowCanvas에 통합
- [ ] 변수 자동 완성 (템플릿 입력 시)

**예상 작업 시간**: 4-5일

---

### 기능 6: Human-in-the-Loop 통합

**우선순위**: 중
**난이도**: 중

#### 목표
- Worker의 ask_user 호출 시 Web UI에 모달 표시
- 사용자 응답을 SSE로 Worker에게 전달
- 승인/거부 플로우 (예: Committer 실행 전)

#### 구현 계획

##### 6-1. 백엔드: 양방향 통신 메커니즘
**파일**: `src/presentation/web/services/workflow_executor.py`

```python
import asyncio
from asyncio import Queue

class WorkflowExecutor:
    def __init__(self, config_loader):
        self.config_loader = config_loader
        self.user_response_queue: Dict[str, Queue] = {}  # session_id → Queue

    async def wait_for_user_response(
        self, session_id: str, question: str, timeout: int = 300
    ) -> str:
        """사용자 응답 대기"""
        queue = Queue()
        self.user_response_queue[session_id] = queue

        # ask_user 이벤트 전송
        yield WorkflowNodeExecutionEvent(
            event_type="ask_user",
            node_id="",
            data={"question": question}
        )

        try:
            response = await asyncio.wait_for(queue.get(), timeout=timeout)
            return response
        except asyncio.TimeoutError:
            return ""  # 타임아웃 시 빈 문자열 반환

    async def submit_user_response(self, session_id: str, response: str):
        """사용자 응답 제출"""
        if session_id in self.user_response_queue:
            await self.user_response_queue[session_id].put(response)
```

**파일**: `src/presentation/web/routers/workflows.py`

```python
@router.post("/execute/{session_id}/respond")
async def submit_user_response(session_id: str, response: str):
    """사용자 응답 제출"""
    # WorkflowExecutor 인스턴스에 접근 (전역 저장소 필요)
    await executor.submit_user_response(session_id, response)
    return {"status": "ok"}
```

**태스크**:
- [ ] 양방향 통신 메커니즘 구현 (Queue 기반)
- [ ] ask_user 이벤트 타입 추가
- [ ] 사용자 응답 제출 API

##### 6-2. 프론트엔드: ask_user 모달
**파일**: `src/presentation/web/frontend/src/components/AskUserModal.tsx` (신규)

```tsx
export function AskUserModal({ question, onSubmit, onCancel }: Props) {
  const [response, setResponse] = useState("")

  return (
    <Dialog open>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Worker가 질문합니다</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <p>{question}</p>

          <Textarea
            value={response}
            onChange={(e) => setResponse(e.target.value)}
            placeholder="응답을 입력하세요..."
          />
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onCancel}>
            취소
          </Button>
          <Button onClick={() => onSubmit(response)}>
            제출
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
```

**태스크**:
- [ ] AskUserModal 컴포넌트 구현
- [ ] SSE 이벤트 핸들러에 ask_user 처리 추가
- [ ] 사용자 응답 제출 API 호출

**예상 작업 시간**: 2-3일

---

### 기능 7: 워크플로우 버전 관리

**우선순위**: 낮
**난이도**: 중

#### 목표
- Git 스타일 버전 관리
- 워크플로우 변경 이력 시각화
- 특정 버전으로 롤백

#### 구현 계획

##### 7-1. 백엔드: 버전 저장소
**파일**: `src/presentation/web/services/version_control.py` (신규)

```python
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

@dataclass
class WorkflowVersion:
    """워크플로우 버전"""
    version_id: str
    workflow: Workflow
    message: str  # 커밋 메시지
    author: str
    created_at: datetime
    parent_version_id: Optional[str]

class VersionControl:
    """워크플로우 버전 관리"""

    def __init__(self, storage_dir: Path):
        self.storage_dir = storage_dir

    def commit(self, workflow: Workflow, message: str, author: str) -> str:
        """새 버전 생성"""
        pass

    def get_history(self, workflow_id: str) -> List[WorkflowVersion]:
        """변경 이력 조회"""
        pass

    def diff(self, version_id_1: str, version_id_2: str) -> Dict[str, Any]:
        """두 버전 비교"""
        pass

    def rollback(self, version_id: str) -> Workflow:
        """특정 버전으로 롤백"""
        pass
```

**태스크**:
- [ ] VersionControl 클래스 구현
- [ ] 버전 저장 형식 설계 (JSON + 메타데이터)
- [ ] diff 알고리즘 구현 (노드/엣지 비교)

##### 7-2. 프론트엔드: 버전 이력 UI
**파일**: `src/presentation/web/frontend/src/components/VersionHistory.tsx` (신규)

```tsx
export function VersionHistory({ workflowId }: Props) {
  const [versions, setVersions] = useState([])

  return (
    <div className="space-y-2">
      {versions.map((version) => (
        <Card key={version.version_id}>
          <CardHeader>
            <div className="flex justify-between">
              <span className="font-mono text-sm">
                {version.version_id.substring(0, 7)}
              </span>
              <span className="text-xs text-gray-500">
                {new Date(version.created_at).toLocaleString()}
              </span>
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-sm">{version.message}</p>
            <p className="text-xs text-gray-500">by {version.author}</p>

            <div className="flex gap-2 mt-2">
              <Button size="sm" variant="outline">
                Diff
              </Button>
              <Button size="sm" variant="outline">
                Rollback
              </Button>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
```

**태스크**:
- [ ] VersionHistory 컴포넌트 구현
- [ ] 버전 diff 시각화 (노드 추가/수정/삭제)
- [ ] 롤백 확인 모달

**예상 작업 시간**: 3-4일

---

### 기능 10: AI 기반 워크플로우 최적화

**우선순위**: 낮 (혁신적이지만 복잡도 높음)
**난이도**: 최상

#### 목표
- 자연어 → 워크플로우 자동 생성
- 병목 노드 탐지 및 최적화 제안
- A/B 테스트

#### 구현 계획

##### 10-1. 백엔드: LLM 기반 워크플로우 생성기
**파일**: `src/presentation/web/services/workflow_generator.py` (신규)

```python
from claude_agent_sdk import query
from src.domain.models import AgentConfig

class WorkflowGenerator:
    """LLM 기반 워크플로우 생성기"""

    async def generate_from_text(self, description: str) -> Workflow:
        """자연어 설명에서 워크플로우 생성"""

        prompt = f"""
다음 작업 설명을 읽고, Better-LLM 워크플로우 JSON을 생성하세요.

사용 가능한 Worker:
- planner: 계획 수립
- coder: 코드 작성
- reviewer: 코드 리뷰
- tester: 테스트 실행
- committer: Git 커밋
- ideator: 아이디어 생성
- product_manager: 요구사항 분석

작업 설명:
{description}

워크플로우 JSON을 생성하세요:
"""

        # LLM 호출
        response = await query(prompt=prompt, model="claude-sonnet-4-5")

        # JSON 파싱 및 검증
        workflow_json = self._extract_json(response)
        workflow = Workflow(**workflow_json)

        return workflow

    def _extract_json(self, text: str) -> dict:
        """LLM 응답에서 JSON 추출"""
        import json
        import re

        # ```json ... ``` 블록 추출
        match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if match:
            return json.loads(match.group(1))

        return json.loads(text)
```

**태스크**:
- [ ] WorkflowGenerator 클래스 구현
- [ ] 프롬프트 엔지니어링 (Few-shot examples)
- [ ] JSON 추출 및 검증 로직

##### 10-2. 백엔드: 병목 분석기
**파일**: `src/presentation/web/services/workflow_analyzer.py` (신규)

```python
@dataclass
class BottleneckAnalysis:
    """병목 분석 결과"""
    node_id: str
    node_name: str
    avg_execution_time: float
    token_usage: int
    recommendation: str

class WorkflowAnalyzer:
    """워크플로우 분석기"""

    def analyze_bottlenecks(self, execution_history: List[Dict]) -> List[BottleneckAnalysis]:
        """병목 노드 분석"""

        # 노드별 평균 실행 시간 계산
        node_stats = {}
        for execution in execution_history:
            for node_id, meta in execution['node_meta'].items():
                if node_id not in node_stats:
                    node_stats[node_id] = []
                node_stats[node_id].append(meta['elapsed_time'])

        # 병목 노드 식별 (평균 실행 시간 상위 20%)
        bottlenecks = []
        for node_id, times in node_stats.items():
            avg_time = sum(times) / len(times)
            if avg_time > threshold:
                bottlenecks.append(BottleneckAnalysis(
                    node_id=node_id,
                    avg_execution_time=avg_time,
                    recommendation=self._generate_recommendation(node_id, avg_time)
                ))

        return bottlenecks

    def _generate_recommendation(self, node_id: str, avg_time: float) -> str:
        """최적화 제안 생성"""
        # LLM 호출하여 최적화 제안 생성
        pass
```

**태스크**:
- [ ] WorkflowAnalyzer 클래스 구현
- [ ] 실행 이력 저장 로직
- [ ] LLM 기반 최적화 제안 생성

##### 10-3. 프론트엔드: 워크플로우 생성 UI
**파일**: `src/presentation/web/frontend/src/components/WorkflowGeneratorModal.tsx` (신규)

```tsx
export function WorkflowGeneratorModal({ onGenerate }: Props) {
  const [description, setDescription] = useState("")
  const [isGenerating, setIsGenerating] = useState(false)

  const handleGenerate = async () => {
    setIsGenerating(true)
    try {
      const workflow = await generateWorkflowFromText(description)
      onGenerate(workflow)
    } finally {
      setIsGenerating(false)
    }
  }

  return (
    <Dialog>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>AI 워크플로우 생성</DialogTitle>
        </DialogHeader>

        <Textarea
          placeholder="작업 설명을 입력하세요. 예: '버그를 수정하고 테스트 후 커밋해줘'"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={5}
        />

        <Button onClick={handleGenerate} disabled={isGenerating}>
          {isGenerating ? <Loader2 className="animate-spin" /> : null}
          생성
        </Button>
      </DialogContent>
    </Dialog>
  )
}
```

**태스크**:
- [ ] WorkflowGeneratorModal 컴포넌트 구현
- [ ] 생성 중 로딩 상태 표시
- [ ] 생성된 워크플로우 미리보기

**예상 작업 시간**: 7-10일 (LLM 통합 복잡도)

---

## 🗓️ 권장 구현 순서

### Phase 1: 사용성 개선 (1-2주)
1. **기능 2**: 워크플로우 템플릿 갤러리
2. **기능 3**: 노드 검증 및 에러 힌트

### Phase 2: 고급 기능 (2-4주)
3. **기능 6**: Human-in-the-Loop 통합
4. **기능 5**: 변수 및 컨텍스트 관리
5. **기능 4**: 조건부 분기 및 반복 노드

### Phase 3: 엔터프라이즈 기능 (4주+)
6. **기능 7**: 워크플로우 버전 관리
7. **기능 10**: AI 기반 워크플로우 최적화

---

## 📝 개발 가이드라인

### 파일 구조 규칙
- 백엔드 서비스: `src/presentation/web/services/`
- 백엔드 라우터: `src/presentation/web/routers/`
- 백엔드 스키마: `src/presentation/web/schemas/`
- 프론트엔드 컴포넌트: `src/presentation/web/frontend/src/components/`
- 프론트엔드 API: `src/presentation/web/frontend/src/lib/api.ts`

### 테스트 요구사항
- 백엔드: 각 서비스 클래스에 단위 테스트 작성 (`tests/unit/`)
- 프론트엔드: TypeScript 타입 검사 (`npx tsc --noEmit`)
- 통합 테스트: 워크플로우 실행 전체 플로우 검증

### 코드 스타일
- 백엔드: Black + Ruff (자동 포맷팅)
- 프론트엔드: Prettier + ESLint
- 커밋 메시지: Conventional Commits 형식

---

## 🔗 참고 자료

- [ReactFlow 문서](https://reactflow.dev/)
- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [Zustand 문서](https://github.com/pmndrs/zustand)
- [Claude Agent SDK](https://docs.anthropic.com/en/docs/agent-sdk/python)

---

**마지막 업데이트**: 2025-10-28
**작성자**: Claude Code Assistant
