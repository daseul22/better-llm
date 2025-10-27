# Better-LLM Workflow Canvas (React Frontend)

React + React Flow 기반 워크플로우 캔버스 UI입니다.

## 기능

### ✨ 핵심 기능
- **드래그 앤 드롭 워크플로우**: Worker Agent를 캔버스에 드래그하여 배치
- **노드 간 연결**: 엣지로 Worker 출력을 다음 Worker 입력으로 전달
- **실시간 실행**: 워크플로우 실행 중 각 노드의 상태를 실시간으로 표시
- **워크플로우 저장/불러오기**: 작성한 워크플로우를 파일로 저장하고 재사용

### 🎯 주요 컴포넌트
- **WorkflowCanvas**: React Flow 기반 캔버스 (노드 배치 및 연결)
- **WorkerNode**: 커스텀 노드 (Agent 이름, 작업 템플릿, 실행 상태)
- **NodePanel**: Agent 목록 (클릭하여 캔버스에 추가)
- **ExecutionPanel**: 실행 제어 및 로그 표시

### 🛠️ 기술 스택
- **React 18** + **TypeScript**
- **Vite** (빌드 도구)
- **React Flow** (워크플로우 캔버스)
- **Zustand** (상태 관리)
- **shadcn/ui** (UI 컴포넌트, Radix UI + Tailwind CSS)

## 설치 및 실행

### 1. 의존성 설치

```bash
cd src/presentation/web/frontend
npm install
```

### 2. 개발 서버 실행

```bash
# 프론트엔드 개발 서버 (port 5173)
npm run dev
```

### 3. 백엔드 서버 실행 (별도 터미널)

```bash
# 프로젝트 루트에서 실행
cd ../../../..
./run-web-dev.sh
```

### 4. 브라우저에서 확인

```
http://localhost:5173
```

프론트엔드(5173)가 백엔드(8000)에 자동으로 프록시됩니다 (`vite.config.ts` 참조).

## 빌드 및 배포

### 프로덕션 빌드

```bash
npm run build
```

빌드 결과물은 `../static-react/` 디렉토리에 생성됩니다.

### FastAPI에서 빌드 결과 서빙 (옵션)

FastAPI 앱에서 `static-react` 디렉토리를 서빙하도록 설정:

```python
# src/presentation/web/app.py
app.mount("/", StaticFiles(directory="src/presentation/web/static-react", html=True), name="react-app")
```

## 사용 방법

### 1. 워크플로우 작성

1. **왼쪽 패널**에서 Worker Agent를 클릭하여 캔버스에 추가
2. 노드를 드래그하여 원하는 위치로 이동
3. 노드의 **아래쪽 핸들**(출력)을 드래그하여 다음 노드의 **위쪽 핸들**(입력)에 연결
4. 노드를 클릭하면 작업 템플릿 편집 가능 (추후 구현 예정)

### 2. 워크플로우 실행

1. **오른쪽 패널**의 "초기 입력" 텍스트박스에 입력 데이터 입력
2. "실행" 버튼 클릭
3. 각 노드가 순차적으로 실행되며, 실행 로그가 표시됨
4. 완료되면 "완료" 상태로 표시

### 3. 워크플로우 저장/불러오기

- **저장**: 상단 "저장" 버튼 클릭 (파일로 저장: `~/.better-llm/workflows/`)
- **불러오기**: 상단 "불러오기" 버튼 클릭 → 목록에서 선택

## 디렉토리 구조

```
frontend/
├── src/
│   ├── components/
│   │   ├── ui/                    # shadcn/ui 컴포넌트
│   │   │   ├── button.tsx
│   │   │   └── card.tsx
│   │   ├── WorkflowCanvas.tsx     # 워크플로우 캔버스
│   │   ├── WorkerNode.tsx         # 커스텀 노드
│   │   ├── NodePanel.tsx          # Agent 목록 패널
│   │   └── ExecutionPanel.tsx     # 실행 제어 패널
│   ├── stores/
│   │   └── workflowStore.ts       # Zustand 상태 관리
│   ├── lib/
│   │   ├── api.ts                 # 백엔드 API 클라이언트
│   │   └── utils.ts               # 유틸리티 함수
│   ├── App.tsx                    # 메인 앱
│   ├── main.tsx                   # 엔트리포인트
│   └── index.css                  # Tailwind CSS
├── package.json
├── vite.config.ts
├── tsconfig.json
├── tailwind.config.js
└── README.md
```

## 환경변수

### 백엔드 URL (프록시)

개발 모드에서는 Vite가 `/api` 요청을 `http://127.0.0.1:8000`으로 프록시합니다.

프로덕션에서는 동일 오리진으로 배포하거나, CORS 설정을 추가해야 합니다.

## 트러블슈팅

### 1. 백엔드 연결 실패

```
HTTP 500: Internal Server Error
```

**해결책**:
- 백엔드 서버가 실행 중인지 확인 (`./run-web-dev.sh`)
- 환경변수 `CLAUDE_CODE_OAUTH_TOKEN` 설정 확인
- 백엔드 로그 확인: `~/.better-llm/better-llm/logs/better-llm.log`

### 2. 노드가 캔버스에 표시되지 않음

**해결책**:
- 브라우저 콘솔에서 에러 확인
- React Flow 스타일시트 로드 확인 (`import 'reactflow/dist/style.css'`)

### 3. 실행 로그가 표시되지 않음

**해결책**:
- SSE 스트리밍 응답 확인 (개발자 도구 → Network → `/api/workflows/execute`)
- 백엔드 로그에서 워크플로우 실행 상태 확인

## 향후 개선 계획

- [ ] 노드 속성 편집 다이얼로그 (작업 템플릿 수정)
- [ ] 워크플로우 템플릿 (미리 정의된 워크플로우)
- [ ] 실행 히스토리 (과거 실행 결과 조회)
- [ ] 병렬 실행 지원 (DAG 병렬화)
- [ ] 조건부 분기 (if/else 노드)
- [ ] 루프 노드 (반복 실행)

## 라이센스

MIT License (Better-LLM 프로젝트와 동일)
