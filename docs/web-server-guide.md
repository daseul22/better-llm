# Better-LLM 웹 서버 가이드

Better-LLM의 웹 인터페이스는 두 가지 모드로 실행할 수 있습니다:

1. **프로덕션 모드**: `better-llm-web` 명령어 (안정적, 빠름)
2. **개발 모드**: `./run-workflow-canvas.sh` 스크립트 (자동 리로드)

---

## 프로덕션 모드 (권장)

### 설치

```bash
# pipx로 설치 (권장)
pipx install -e .

# 또는 pip로 설치
pip install -e .
```

### 실행

```bash
# 기본 실행 (http://127.0.0.1:8000)
better-llm-web

# 포트 변경
WEB_PORT=3000 better-llm-web

# 외부 접근 허용
WEB_HOST=0.0.0.0 WEB_PORT=8000 better-llm-web

# 멀티 워커 (CPU 코어 수만큼)
WEB_WORKERS=4 better-llm-web

# 로그 레벨 변경
WEB_LOG_LEVEL=debug better-llm-web
```

### 환경변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `WEB_HOST` | `127.0.0.1` | 호스트 주소 |
| `WEB_PORT` | `8000` | 포트 번호 |
| `WEB_RELOAD` | `false` | 자동 리로드 (개발 모드) |
| `WEB_WORKERS` | `1` | 워커 수 (reload 모드에서는 강제로 1) |
| `WEB_LOG_LEVEL` | `info` | 로그 레벨 (debug, info, warning, error) |

### 특징

- ✅ **안정적**: 코드 변경이 즉시 반영되지 않아 안정적
- ✅ **빠름**: 리로드 오버헤드 없음
- ✅ **멀티 워커 지원**: 여러 요청을 동시에 처리
- ⚠️ **코드 변경 시 재시작 필요**: 코드 수정 후 수동으로 재시작

---

## 개발 모드 (개발 시에만 사용)

### 실행

```bash
# 백엔드(FastAPI) + 프론트엔드(Vite) 동시 실행
./run-workflow-canvas.sh
```

### 특징

- ✅ **자동 리로드**: 백엔드/프론트엔드 코드 변경 시 즉시 반영
- ✅ **HMR (Hot Module Replacement)**: React 컴포넌트 수정 시 전체 새로고침 없이 반영
- ✅ **캐시 무효화**: 정적 파일(CSS, JS) 변경 시 브라우저 새로고침만으로 반영
- ⚠️ **느림**: 리로드 오버헤드로 인해 느릴 수 있음
- ⚠️ **단일 워커**: 멀티 워커 미지원

### 포트

- **백엔드**: http://127.0.0.1:8000 (FastAPI)
- **프론트엔드**: http://localhost:5173 (Vite)

프론트엔드가 백엔드에 자동으로 프록시됩니다 (`vite.config.ts` 참조).

---

## 프로덕션 배포

### 1. 프론트엔드 빌드

```bash
cd src/presentation/web/frontend
npm run build
cd -
```

빌드 결과물: `src/presentation/web/static-react/`

### 2. FastAPI에서 정적 파일 서빙

`src/presentation/web/app.py`에 추가:

```python
from fastapi.staticfiles import StaticFiles

# React 빌드 결과물 서빙
REACT_BUILD_DIR = Path(__file__).parent / "static-react"
if REACT_BUILD_DIR.exists():
    app.mount("/", StaticFiles(directory=str(REACT_BUILD_DIR), html=True), name="react-app")
```

### 3. 프로덕션 서버 실행

```bash
# 기본 실행
better-llm-web

# 멀티 워커 (CPU 코어 수: 4)
WEB_WORKERS=4 better-llm-web

# 외부 접근 허용
WEB_HOST=0.0.0.0 WEB_PORT=80 better-llm-web
```

### 4. Docker 배포 (선택)

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Python 의존성 설치
COPY pyproject.toml .
RUN pip install -e .

# 소스 복사
COPY src/ src/
COPY config/ config/
COPY prompts/ prompts/

# 프론트엔드 빌드 복사
COPY src/presentation/web/static-react/ src/presentation/web/static-react/

# 포트 노출
EXPOSE 8000

# 서버 실행
CMD ["better-llm-web"]
```

빌드 및 실행:

```bash
docker build -t better-llm-web .
docker run -p 8000:8000 \
  -e CLAUDE_CODE_OAUTH_TOKEN='your-token' \
  -e WEB_HOST=0.0.0.0 \
  -e WEB_WORKERS=4 \
  better-llm-web
```

---

## 프로덕션 vs 개발 모드 비교

| 항목 | 프로덕션 (`better-llm-web`) | 개발 (`./run-workflow-canvas.sh`) |
|------|----------------------------|-----------------------------------|
| **실행 방법** | 명령어 1개 | 스크립트 실행 |
| **자동 리로드** | ❌ (수동 재시작) | ✅ (코드 변경 시 자동) |
| **HMR** | ❌ | ✅ (React 컴포넌트) |
| **멀티 워커** | ✅ | ❌ (단일 워커) |
| **성능** | 빠름 | 느림 (리로드 오버헤드) |
| **안정성** | 높음 | 낮음 (코드 변경 중 불안정) |
| **프론트엔드** | 빌드 결과 서빙 | Vite 개발 서버 (별도 포트) |
| **사용 시기** | 프로덕션, 테스트 | 개발 중 |

---

## 트러블슈팅

### 1. `better-llm-web` 명령어를 찾을 수 없음

```bash
bash: better-llm-web: command not found
```

**해결책**: pipx로 재설치

```bash
pipx reinstall better-llm
```

또는

```bash
pipx install -e .
```

### 2. 포트가 이미 사용 중

```
ERROR: [Errno 48] Address already in use
```

**해결책**: 다른 포트 사용 또는 기존 프로세스 종료

```bash
# 다른 포트 사용
WEB_PORT=3000 better-llm-web

# 기존 프로세스 종료 (macOS/Linux)
lsof -ti:8000 | xargs kill -9
```

### 3. 프론트엔드 빌드 실패

```
npm ERR! code ELIFECYCLE
```

**해결책**: 의존성 재설치

```bash
cd src/presentation/web/frontend
rm -rf node_modules package-lock.json
npm install
npm run build
```

### 4. CORS 오류 (프로덕션 배포 시)

```
Access-Control-Allow-Origin 헤더가 없음
```

**해결책**: `src/presentation/web/app.py`에서 CORS 설정 확인

```python
# CORS 설정
origins = os.getenv("WEB_ALLOWED_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

프로덕션 도메인 추가:

```bash
WEB_ALLOWED_ORIGINS="https://your-domain.com,http://localhost:8000" better-llm-web
```

---

## 참고 자료

- [FastAPI 배포 가이드](https://fastapi.tiangolo.com/deployment/)
- [Uvicorn 설정](https://www.uvicorn.org/settings/)
- [Vite 프로덕션 빌드](https://vitejs.dev/guide/build.html)

---

**최종 업데이트**: 2025-10-27
