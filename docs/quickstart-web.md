# Better-LLM 웹 UI 빠른 시작 가이드

5분 안에 워크플로우 캔버스를 시작하는 가이드입니다.

---

## 1단계: 설치 및 환경 설정

### 설치

```bash
# 프로젝트 클론
git clone https://github.com/simdaseul/better-llm.git
cd better-llm

# 자동 설치 (권장)
./setup.sh

# 또는 수동 설치
pipx install -e .
```

### 환경변수 설정

```bash
# Claude API 토큰 설정 (필수)
export CLAUDE_CODE_OAUTH_TOKEN='your-oauth-token-here'

# 또는 .env 파일 생성
echo "CLAUDE_CODE_OAUTH_TOKEN=your-oauth-token-here" > .env
```

토큰 발급: https://console.anthropic.com/settings/keys

---

## 2단계: 웹 서버 실행

### 프로덕션 모드 (권장)

```bash
better-llm-web
```

**접속**: http://127.0.0.1:8000

### 개발 모드 (개발 중일 때만)

```bash
# 프론트엔드 의존성 설치 (최초 1회)
cd src/presentation/web/frontend
npm install
cd -

# 개발 서버 실행
./run-workflow-canvas.sh
```

**접속**: http://localhost:5173

---

## 3단계: 첫 번째 워크플로우 만들기

### 1. Worker 노드 추가

**왼쪽 패널**에서 Worker를 클릭하여 캔버스에 추가:

1. **Planner** 클릭
2. **Coder** 클릭
3. **Reviewer** 클릭

캔버스에 3개의 노드가 생성됩니다.

### 2. 노드 연결

1. **Planner 노드**의 **아래쪽 동그라미**(출력 핸들)를 클릭
2. **Coder 노드**의 **위쪽 동그라미**(입력 핸들)로 드래그
3. 같은 방식으로 **Coder** → **Reviewer** 연결

화살표가 생성되며 데이터 흐름이 정의됩니다.

### 3. 워크플로우 실행

**오른쪽 패널**:

1. **초기 입력** 텍스트박스에 입력:
   ```
   FastAPI로 사용자 인증 API 구현
   ```

2. **실행** 버튼 클릭

3. 각 노드가 순차적으로 실행됩니다:
   - Planner (노란색): 계획 수립 중...
   - Planner (초록색): 완료
   - Coder (노란색): 코드 작성 중...
   - Coder (초록색): 완료
   - Reviewer (노란색): 리뷰 중...
   - Reviewer (초록색): 완료

4. **실행 로그**에서 각 Worker의 출력을 확인:
   ```
   [node-1] planner 실행 시작
   [node-1] 1. API 엔드포인트 설계
   [node-1] 2. JWT 토큰 구현
   ...
   [node-1] planner 완료 (출력: 500자)
   [node-2] coder 실행 시작
   ...
   ```

### 4. 워크플로우 저장

1. 상단 **워크플로우 이름** 입력: "사용자 인증 워크플로우"
2. **저장** 버튼 클릭
3. 저장 완료 메시지 확인

---

## 4단계: 워크플로우 재사용

### 저장된 워크플로우 불러오기

1. 상단 **불러오기** 버튼 클릭
2. 목록에서 워크플로우 선택
3. **불러오기** 버튼 클릭

캔버스에 노드와 연결이 복원됩니다.

### 수정 후 다시 저장

1. 노드를 추가하거나 연결 변경
2. 상단 **저장** 버튼 클릭 (같은 ID로 덮어쓰기)

---

## 5단계: 고급 기능

### 템플릿 변수 사용

노드의 작업 템플릿에 변수를 사용할 수 있습니다:

- `{{input}}`: 초기 입력 데이터
- `{{parent}}`: 이전 노드의 출력
- `{{node_<id>}}`: 특정 노드의 출력

**예시**:
```
Planner 노드: "{{input}}에 대한 구현 계획을 수립해주세요"
Coder 노드: "{{parent}}에 따라 코드를 작성해주세요"
Reviewer 노드: "{{parent}}을(를) 코드 리뷰해주세요"
```

### 복잡한 워크플로우

더 많은 Worker를 추가하여 복잡한 흐름을 만들 수 있습니다:

```
Ideator → Planner → Coder → Tester → Reviewer → Committer
```

1. **Ideator**: 아이디어 생성
2. **Planner**: 구현 계획
3. **Coder**: 코드 작성
4. **Tester**: 테스트 실행
5. **Reviewer**: 코드 리뷰
6. **Committer**: Git 커밋

---

## 트러블슈팅

### "better-llm-web 명령어를 찾을 수 없음"

```bash
# pipx로 재설치
pipx reinstall better-llm

# 또는
pipx install -e .
```

### "CLAUDE_CODE_OAUTH_TOKEN 환경변수가 설정되지 않았습니다"

```bash
# 환경변수 설정
export CLAUDE_CODE_OAUTH_TOKEN='your-oauth-token-here'

# 또는 .env 파일 생성
echo "CLAUDE_CODE_OAUTH_TOKEN=your-oauth-token-here" > .env
```

### 프론트엔드 의존성 설치 실패 (개발 모드)

```bash
cd src/presentation/web/frontend
rm -rf node_modules package-lock.json
npm install
```

### 포트가 이미 사용 중

```bash
# 다른 포트 사용
WEB_PORT=3000 better-llm-web

# 또는 기존 프로세스 종료 (macOS/Linux)
lsof -ti:8000 | xargs kill -9
```

---

## 다음 단계

- [**Workflow Canvas 가이드**](workflow-canvas-guide.md): 상세한 기능 설명
- [**웹 서버 가이드**](web-server-guide.md): 프로덕션 배포 방법
- [**사용 사례**](guides/use_cases.md): 실전 시나리오

---

**최종 업데이트**: 2025-10-27
