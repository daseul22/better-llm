# Better-LLM 웹 UI 사용 가이드

Better-LLM은 두 가지 웹 인터페이스를 제공합니다.

---

## 1. Workflow Canvas (워크플로우 캔버스) - 권장 ✨

**드래그 앤 드롭으로 Worker Agent를 연결하여 복잡한 작업 흐름을 구성하는 시각적 에디터입니다.**

### 실행 방법

```bash
# 하나의 명령어로 모든 것 실행 (백엔드 + 프론트엔드)
better-llm-web
```

**접속**:
- 프론트엔드: http://localhost:5173 (자동 리다이렉트)
- 백엔드: http://127.0.0.1:8000

### 특징

- 🎯 **드래그 앤 드롭**: Worker를 캔버스에 배치하고 자유롭게 연결
- 🔗 **시각적 데이터 흐름**: 화살표로 Worker 간 연결 표시
- ⚡ **실시간 실행 상태**: 각 노드의 실행 상태를 색상으로 표시
  - 노란색: 실행 중
  - 초록색: 완료
  - 빨간색: 에러
- 💾 **저장/불러오기**: 워크플로우를 파일로 저장하고 재사용
- 📝 **템플릿 변수**: `{{input}}`, `{{parent}}` 등으로 데이터 전달

### 사용 예시

**코드 리뷰 워크플로우**:
```
Planner → Coder → Reviewer → Committer
```

1. Planner: 리뷰 계획 수립
2. Coder: 계획에 따라 코드 수정
3. Reviewer: 수정된 코드 검증
4. Committer: Git 커밋

**상세 가이드**: [workflow-canvas-guide.md](workflow-canvas-guide.md)

---

## 2. Legacy UI (레거시 UI)

**단일 Worker Agent를 선택하여 실행하는 간단한 UI입니다.**

### 접속 방법

```bash
# better-llm-web 실행 후
http://127.0.0.1:8000/legacy
```

### 특징

- ✅ **간단함**: 단일 Worker 선택 후 작업 입력
- ✅ **빠른 테스트**: 개별 Worker 동작 확인용
- ⚠️ **제한적**: Worker 간 연결 불가

### 사용 시기

- 개별 Worker 테스트
- 간단한 작업 (단일 Worker로 해결 가능)
- 레거시 워크플로우 유지

---

## 명령어 옵션

### 환경변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `WEB_HOST` | `127.0.0.1` | 백엔드 호스트 |
| `WEB_PORT` | `8000` | 백엔드 포트 |
| `WEB_FRONTEND` | `true` | 프론트엔드 개발 서버 실행 |
| `WEB_RELOAD` | `true` | 백엔드 자동 리로드 |
| `WEB_LOG_LEVEL` | `info` | 로그 레벨 |

### 사용 예시

```bash
# 기본 실행 (백엔드 + 프론트엔드)
better-llm-web

# 백엔드만 실행 (프론트엔드 빌드 결과물 서빙)
WEB_FRONTEND=false better-llm-web

# 포트 변경
WEB_PORT=3000 better-llm-web

# 로그 레벨 변경
WEB_LOG_LEVEL=debug better-llm-web
```

---

## 자동 기능

### 1. 프론트엔드 의존성 자동 설치

`better-llm-web` 실행 시 `node_modules`가 없으면 자동으로 `npm install`을 실행합니다.

```
📦 프론트엔드 의존성을 설치합니다...
   디렉토리: src/presentation/web/frontend

✓ 프론트엔드 의존성 설치 완료
```

### 2. 프론트엔드 개발 서버 자동 실행

`better-llm-web` 실행 시 백엔드와 프론트엔드 개발 서버를 모두 자동으로 실행합니다.

```
🚀 모드: 풀스택 개발 모드 (백엔드 + 프론트엔드)
   백엔드:     http://127.0.0.1:8000
   프론트엔드: http://localhost:5173
```

### 3. React 빌드 결과물 자동 감지

프론트엔드 개발 서버가 실행되지 않으면, React 빌드 결과물(`static-react/`)을 자동으로 서빙합니다.

```
   ✓ React 빌드 결과물 발견 (프로덕션 모드)
     접속: http://127.0.0.1:8000
```

---

## 트러블슈팅

### 프론트엔드가 실행되지 않음

**증상**:
```
❌ 프론트엔드 디렉토리를 찾을 수 없습니다
```

**해결책**: 프로젝트 루트에서 실행하거나 백엔드만 실행
```bash
# 프로젝트 루트로 이동
cd /path/to/better-llm

# 또는 백엔드만 실행
WEB_FRONTEND=false better-llm-web
```

### npm 의존성 설치 실패

**증상**:
```
❌ 프론트엔드 의존성 설치 실패
```

**해결책**: 수동 설치
```bash
cd src/presentation/web/frontend
npm install
```

### Node.js가 설치되지 않음

**증상**:
```
❌ npm을 찾을 수 없습니다. Node.js를 설치해주세요
```

**해결책**: Node.js 설치
- macOS: `brew install node`
- 공식 사이트: https://nodejs.org/

### 포트가 이미 사용 중

**증상**:
```
ERROR: [Errno 48] Address already in use
```

**해결책**: 다른 포트 사용 또는 기존 프로세스 종료
```bash
# 다른 포트 사용
WEB_PORT=3000 better-llm-web

# 기존 프로세스 종료 (macOS/Linux)
lsof -ti:8000 | xargs kill -9
lsof -ti:5173 | xargs kill -9
```

---

## 개발 모드 vs 프로덕션 모드

### 개발 모드 (권장)

```bash
better-llm-web
```

**특징**:
- ✅ 백엔드 + 프론트엔드 동시 실행
- ✅ 코드 변경 시 자동 리로드
- ✅ HMR (Hot Module Replacement)
- ✅ 상세한 로그

### 프로덕션 모드

```bash
# 프론트엔드 빌드
cd src/presentation/web/frontend
npm run build
cd -

# 백엔드만 실행
WEB_FRONTEND=false better-llm-web
```

**특징**:
- ✅ 빌드된 React 앱 서빙
- ✅ 빠른 로딩 속도
- ✅ 최적화된 번들
- ⚠️ 코드 변경 시 재빌드 필요

---

## 다음 단계

- [**Workflow Canvas 가이드**](workflow-canvas-guide.md) - 상세한 사용법
- [**빠른 시작 가이드**](quickstart-web.md) - 5분 튜토리얼
- [**웹 서버 가이드**](web-server-guide.md) - 고급 설정

---

**최종 업데이트**: 2025-10-27
