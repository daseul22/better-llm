"""FastAPI 앱 - Better-LLM 워크플로우 캔버스"""
import os
from pathlib import Path
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from src.infrastructure.logging import get_logger
from src.presentation.web.routers import agents_router, health_router, workflows_router

# .env 파일 로드 (프로젝트 루트)
load_dotenv()

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI Lifespan Context Manager (권장 방식)

    startup 및 shutdown 이벤트를 처리합니다.
    """
    # Startup
    logger.info(f"🚀 Better-LLM 시작 (React: {(Path(__file__).parent / 'static-react').exists()})")

    # 환경변수 확인
    if not os.getenv("CLAUDE_CODE_OAUTH_TOKEN"):
        logger.warning("⚠️  CLAUDE_CODE_OAUTH_TOKEN 환경변수가 설정되지 않았습니다")
        logger.warning("   Worker Agent 실행 시 오류가 발생할 수 있습니다")
    else:
        logger.info("✓ CLAUDE_CODE_OAUTH_TOKEN 확인됨")

    yield  # 애플리케이션 실행 중

    # Shutdown
    logger.info("🛑 Better-LLM 종료 중...")
    # 필요한 경우 리소스 정리 작업 추가 (DB 연결 종료, 캐시 정리 등)
    logger.info("✅ Better-LLM 종료 완료")


app = FastAPI(title="Better-LLM", version="4.0.0", lifespan=lifespan)

origins = os.getenv("WEB_ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

app.include_router(health_router)
app.include_router(agents_router)
app.include_router(workflows_router)

REACT_BUILD_DIR = Path(__file__).parent / "static-react"

if REACT_BUILD_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(REACT_BUILD_DIR / "assets")), name="assets")
    @app.get("/")
    async def root():
        return FileResponse(str(REACT_BUILD_DIR / "index.html"))
else:
    @app.get("/")
    async def root():
        return {"error": "React 빌드 필요", "solution": "cd src/presentation/web/frontend && npm run build"}


def main():
    import uvicorn

    # .env 파일 다시 로드 (main 함수에서도)
    load_dotenv()

    host = os.getenv("WEB_HOST", "127.0.0.1")
    port = int(os.getenv("WEB_PORT", "8000"))

    print("╔════════════════════════════════════════════╗")
    print("║   Better-LLM Workflow Canvas               ║")
    print("╚════════════════════════════════════════════╝")
    print()
    print(f"🚀 웹 서버: http://{host}:{port}")

    # 환경변수 확인
    if not os.getenv("CLAUDE_CODE_OAUTH_TOKEN"):
        print()
        print("⚠️  경고: CLAUDE_CODE_OAUTH_TOKEN 환경변수가 설정되지 않았습니다")
        print("   .env 파일을 확인하거나 다음과 같이 설정하세요:")
        print("   export CLAUDE_CODE_OAUTH_TOKEN='your-token'")
    else:
        print("✓ CLAUDE_CODE_OAUTH_TOKEN 확인됨")

    print()
    print("   Ctrl+C로 종료")
    print()

    uvicorn.run("src.presentation.web.app:app", host=host, port=port, log_level="info")

if __name__ == "__main__":
    main()
