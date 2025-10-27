# Better-LLM Workflow Canvas 가이드

**캔버스 기반 워크플로우 에디터** - Worker Agent를 드래그 앤 드롭으로 연결하여 복잡한 작업 흐름을 시각적으로 구성합니다.

---

## 빠른 시작

### 1. 설치

```bash
# 프론트엔드 의존성 설치
cd src/presentation/web/frontend
npm install
cd -
```

### 2. 실행

```bash
# 통합 실행 스크립트 (백엔드 + 프론트엔드)
./run-workflow-canvas.sh
```

또는 개별 실행:

```bash
# 터미널 1: 백엔드 (FastAPI)
./run-web-dev.sh

# 터미널 2: 프론트엔드 (Vite)
cd src/presentation/web/frontend
npm run dev
```

### 3. 접속

```
http://localhost:5173
```

---

## 핵심 기능

### 1. 드래그 앤 드롭 워크플로우

**기존 방식** (단일 Worker 실행):
```
사용자 → Worker 선택 → 작업 입력 → 실행 → 결과 확인
```

**Workflow Canvas** (복합 Worker 연결):
```
사용자 → 캔버스에 Worker 배치 → Worker 간 연결 → 실행 → 각 Worker 결과 확인
```

### 2. 노드 간 데이터 전달

**작업 템플릿 변수**:
- `{{input}}`: 초기 입력 데이터
- `{{node_<id>}}`: 특정 노드의 출력
- `{{parent}}`: 부모 노드의 출력 (부모가 1개인 경우)

**예시**:
```
[Planner 노드]
작업: "{{input}} 프로젝트의 구현 계획을 수립해주세요"
출력: "1. 요구사항 분석\n2. 코드 작성\n3. 테스트"

↓ (연결)

[Coder 노드]
작업: "{{parent}}에 따라 코드를 작성해주세요"
입력: "1. 요구사항 분석\n2. 코드 작성\n3. 테스트"
```

### 3. 실시간 실행 상태

각 노드는 실행 상태에 따라 시각적으로 표시됩니다:

- **대기 중** (회색 테두리): 실행 전
- **실행 중** (노란색 테두리 + 배경): 현재 실행 중
- **완료** (초록색 테두리 + 배경): 실행 완료
- **에러** (빨간색 테두리 + 배경): 실행 실패

### 4. 워크플로우 저장/불러오기

- **저장**: 상단 "저장" 버튼 → `~/.better-llm/workflows/{workflow_id}.json`
- **불러오기**: 상단 "불러오기" 버튼 → 목록에서 선택
- **삭제**: 불러오기 다이얼로그에서 휴지통 아이콘 클릭

---

## 사용 예시

### 예시 1: 코드 리뷰 워크플로우

```
[초기 입력] "main.py 파일 리뷰"
    ↓
[Planner] "{{input}}에 대한 리뷰 계획 수립"
    ↓
[Coder] "{{parent}}에 따라 코드를 수정"
    ↓
[Reviewer] "{{parent}}을(를) 코드 리뷰"
    ↓
[Committer] "{{parent}} 결과를 커밋"
```

**실행 흐름**:
1. Planner: 리뷰 항목 도출 (보안, 성능, 가독성 등)
2. Coder: 리뷰 항목에 따라 코드 수정
3. Reviewer: 수정된 코드 검증 (Critical 이슈 확인)
4. Committer: Git 커밋

### 예시 2: 신규 기능 개발 워크플로우

```
[초기 입력] "사용자 인증 기능 추가"
    ↓
[Ideator] "{{input}} 아이디어 도출"
    ↓
[Planner] "{{parent}}을(를) 바탕으로 구현 계획 수립"
    ↓
[Coder] "{{parent}}에 따라 코드 작성"
    ↓
[Tester] "{{parent}}을(를) 테스트"
    ↓
[Reviewer] "{{parent}} 검증"
```

### 예시 3: 병렬 작업 (향후 지원 예정)

```
[초기 입력] "API 서버 구축"
         ↓
    [Planner]
    ↙        ↘
[Coder]    [Tester]
(병렬 실행)
    ↘        ↙
    [Reviewer]
```

---

## UI 구성

### 레이아웃

```
┌─────────────────────────────────────────────────────┐
│  Header: 워크플로우 이름 | 저장 | 불러오기          │
├──────────┬──────────────────────────┬───────────────┤
│          │                          │               │
│  Node    │    Workflow Canvas       │  Execution    │
│  Panel   │    (React Flow)          │  Panel        │
│          │                          │               │
│  - Worker│    [드래그 앤 드롭]       │  - 초기 입력  │
│    목록  │    [노드 연결]            │  - 실행 버튼  │
│          │                          │  - 로그       │
│          │                          │               │
└──────────┴──────────────────────────┴───────────────┘
```

### Node Panel (왼쪽)

Worker Agent 목록을 표시합니다:
- **Planner**: 계획 수립 전문가
- **Coder**: 코드 작성 전문가
- **Reviewer**: 코드 리뷰 전문가
- **Tester**: 테스트 및 검증 전문가
- **Committer**: Git 커밋 전문가
- **Ideator**: 아이디어 생성 전문가
- **Product Manager**: 제품 기획 전문가

클릭하여 캔버스에 추가합니다.

### Workflow Canvas (중앙)

React Flow 기반 캔버스:
- **드래그**: 노드 이동
- **연결**: 노드의 아래쪽 핸들을 드래그하여 다음 노드의 위쪽 핸들에 연결
- **삭제**: 노드 선택 후 `Delete` 키 (또는 노드 클릭 → 휴지통 아이콘)
- **줌**: 마우스 휠 또는 Controls 패널 사용
- **미니맵**: 우측 하단에 전체 워크플로우 미리보기

### Execution Panel (오른쪽)

실행 제어 및 로그:
- **초기 입력**: 첫 번째 노드에 전달할 입력 데이터
- **실행 버튼**: 워크플로우 실행 시작
- **중단 버튼**: 실행 중단 (UI만 제공, 백엔드 미지원)
- **실행 로그**: 각 노드의 실행 상태 및 출력 표시

---

## 백엔드 API

### 워크플로우 실행

```http
POST /api/workflows/execute
Content-Type: application/json

{
  "workflow": {
    "name": "코드 리뷰 워크플로우",
    "nodes": [
      {
        "id": "node-1",
        "type": "worker",
        "position": { "x": 100, "y": 100 },
        "data": {
          "agent_name": "planner",
          "task_template": "{{input}}에 대한 계획 수립"
        }
      },
      {
        "id": "node-2",
        "type": "worker",
        "position": { "x": 100, "y": 250 },
        "data": {
          "agent_name": "coder",
          "task_template": "{{parent}}에 따라 코드 작성"
        }
      }
    ],
    "edges": [
      {
        "id": "edge-1",
        "source": "node-1",
        "target": "node-2"
      }
    ]
  },
  "initial_input": "웹 UI 추가"
}
```

**응답 (Server-Sent Events)**:
```
data: {"event_type": "node_start", "node_id": "node-1", "data": {"agent_name": "planner"}}

data: {"event_type": "node_output", "node_id": "node-1", "data": {"chunk": "계획 수립 중..."}}

data: {"event_type": "node_complete", "node_id": "node-1", "data": {"output_length": 500}}

data: {"event_type": "node_start", "node_id": "node-2", "data": {"agent_name": "coder"}}

data: {"event_type": "node_output", "node_id": "node-2", "data": {"chunk": "코드 작성 중..."}}

data: {"event_type": "node_complete", "node_id": "node-2", "data": {"output_length": 1500}}

data: {"event_type": "workflow_complete", "node_id": "", "data": {"message": "완료"}}

data: [DONE]
```

### 워크플로우 저장

```http
POST /api/workflows
Content-Type: application/json

{
  "workflow": {
    "name": "코드 리뷰 워크플로우",
    "description": "계획 → 코드 작성 → 리뷰",
    "nodes": [...],
    "edges": [...]
  }
}
```

**응답**:
```json
{
  "workflow_id": "uuid-v4",
  "message": "워크플로우가 저장되었습니다"
}
```

### 워크플로우 목록 조회

```http
GET /api/workflows
```

**응답**:
```json
{
  "workflows": [
    {
      "id": "uuid-v4",
      "name": "코드 리뷰 워크플로우",
      "description": "계획 → 코드 작성 → 리뷰",
      "node_count": 3,
      "edge_count": 2
    }
  ]
}
```

### 워크플로우 조회 (단일)

```http
GET /api/workflows/{workflow_id}
```

### 워크플로우 삭제

```http
DELETE /api/workflows/{workflow_id}
```

---

## 아키텍처

### 프론트엔드 (React + TypeScript)

```
src/presentation/web/frontend/
├── src/
│   ├── components/
│   │   ├── ui/                    # shadcn/ui 컴포넌트
│   │   ├── WorkflowCanvas.tsx     # React Flow 캔버스
│   │   ├── WorkerNode.tsx         # 커스텀 노드 (Worker)
│   │   ├── NodePanel.tsx          # Agent 목록
│   │   └── ExecutionPanel.tsx     # 실행 제어
│   ├── stores/
│   │   └── workflowStore.ts       # Zustand 상태 관리
│   ├── lib/
│   │   ├── api.ts                 # 백엔드 API 클라이언트
│   │   └── utils.ts               # 유틸리티
│   └── App.tsx                    # 메인 앱
```

**주요 라이브러리**:
- **React Flow**: 워크플로우 캔버스 (노드 배치, 연결, 줌 등)
- **Zustand**: 상태 관리 (노드/엣지, 실행 상태)
- **shadcn/ui**: UI 컴포넌트 (Radix UI + Tailwind CSS)
- **Lucide React**: 아이콘

### 백엔드 (FastAPI + Python)

```
src/presentation/web/
├── routers/
│   └── workflows.py               # 워크플로우 API 라우터
├── schemas/
│   └── workflow.py                # Workflow, WorkflowNode, WorkflowEdge 스키마
├── services/
│   └── workflow_executor.py       # 워크플로우 실행 엔진
└── app.py                         # FastAPI 앱
```

**주요 기능**:
- **위상 정렬 (Topological Sort)**: 노드 실행 순서 결정 (DAG)
- **템플릿 렌더링**: `{{input}}`, `{{parent}}` 등 변수 치환
- **스트리밍 실행**: SSE로 실시간 이벤트 전송
- **워크플로우 저장소**: `~/.better-llm/workflows/` (JSON 파일)

---

## 제약사항 및 알려진 이슈

### 현재 제약사항

1. **순차 실행만 지원**: 병렬 실행 미지원 (DAG 병렬화 향후 구현 예정)
2. **단순 템플릿 변수**: 조건부 분기, 루프 미지원
3. **중단 기능 미지원**: UI만 제공, 백엔드에서 실행 중단 불가
4. **노드 속성 편집**: 캔버스에서 직접 편집 불가 (템플릿 수정 시 Zustand 직접 수정 필요)

### 알려진 이슈

- **워크플로우 순환 참조**: 순환 참조 시 실행 실패 (에러 메시지 표시)
- **긴 작업 타임아웃**: 각 Worker는 최대 10분 실행 (system_config.json에서 변경 가능)

---

## 트러블슈팅

### 1. 프론트엔드 의존성 설치 실패

```bash
npm ERR! code ERESOLVE
npm ERR! ERESOLVE unable to resolve dependency tree
```

**해결책**:
```bash
cd src/presentation/web/frontend
rm -rf node_modules package-lock.json
npm install --legacy-peer-deps
```

### 2. 백엔드 연결 실패 (CORS)

```
Access to fetch at 'http://127.0.0.1:8000/api/agents' from origin 'http://localhost:5173' has been blocked by CORS policy
```

**해결책**: Vite 프록시 설정 확인 (`vite.config.ts`):
```typescript
server: {
  proxy: {
    '/api': {
      target: 'http://127.0.0.1:8000',
      changeOrigin: true,
    },
  },
}
```

### 3. 워크플로우 실행 실패 (환경변수)

```
CLAUDE_CODE_OAUTH_TOKEN 환경변수가 설정되지 않았습니다
```

**해결책**:
```bash
export CLAUDE_CODE_OAUTH_TOKEN='your-oauth-token-here'
./run-workflow-canvas.sh
```

### 4. 노드가 캔버스에 표시되지 않음

**해결책**:
- 브라우저 콘솔에서 에러 확인
- React Flow 스타일시트 로드 확인 (`import 'reactflow/dist/style.css'`)
- Zustand 상태 확인 (React DevTools)

---

## 향후 개선 계획

### 단기 (우선순위 1)
- [ ] 노드 속성 편집 다이얼로그 (작업 템플릿 수정)
- [ ] 워크플로우 템플릿 (미리 정의된 워크플로우)
- [ ] 실행 히스토리 (과거 실행 결과 조회)
- [ ] 실행 중단 기능 (백엔드 지원)

### 중기 (우선순위 2)
- [ ] 병렬 실행 지원 (DAG 병렬화)
- [ ] 조건부 분기 노드 (if/else)
- [ ] 루프 노드 (반복 실행)
- [ ] 워크플로우 공유 (JSON 내보내기/가져오기)

### 장기 (우선순위 3)
- [ ] 협업 기능 (다중 사용자)
- [ ] 워크플로우 버전 관리
- [ ] 성능 최적화 (큰 워크플로우 처리)
- [ ] 클라우드 배포 (Docker + Kubernetes)

---

## 참고 자료

- [React Flow 공식 문서](https://reactflow.dev/)
- [shadcn/ui 컴포넌트](https://ui.shadcn.com/)
- [FastAPI Server-Sent Events](https://fastapi.tiangolo.com/advanced/custom-response/#using-streamingresponse-with-file-like-objects)
- [Better-LLM CLAUDE.md](../CLAUDE.md)

---

**최종 업데이트**: 2025-10-27
