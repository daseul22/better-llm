"""
Worker Agent Tools - Worker Agent들을 Custom Tool로 래핑

각 Worker Agent를 Claude Agent SDK의 Custom Tool로 만들어,
Manager Agent가 필요할 때 호출할 수 있도록 합니다.
"""

from typing import Any, Dict, Callable, Optional, Tuple
from pathlib import Path
import logging
import asyncio
import re
from functools import wraps
from datetime import datetime

from claude_agent_sdk import tool, create_sdk_mcp_server
from claude_agent_sdk.types import ClaudeAgentOptions

from ..claude import WorkerAgent
from ...domain.models import AgentConfig
from ...domain.services import MetricsCollector
from ..config import JsonConfigLoader, get_project_root

logger = logging.getLogger(__name__)


# 민감 정보 검증을 위한 패턴 정의
SENSITIVE_FILE_PATTERNS = [
    r"\.env.*",                     # .env, .env.local, .env.production 등
    r".*credentials.*",             # credentials.json, aws-credentials 등
    r".*secret.*",                  # secret.txt, secrets.yaml 등
    r".*\.pem$",                    # SSL 인증서
    r".*\.p12$",                    # PKCS#12 인증서
    r".*api[_-]?keys?.*",           # api_key.txt, api-keys.json 등
    r".*\.key$",                    # 개인 키 파일
    r".*private[_-]?key.*",         # private-key.pem 등
]

SENSITIVE_CONTENT_PATTERNS = [
    r"api[_-]?key\s*[:=]\s*['\"]?[\w-]{20,}",              # API 키
    r"password\s*[:=]\s*['\"][\w@#$%^&*]+['\"]",          # 비밀번호
    r"secret[_-]?key\s*[:=]",                             # Secret 키
    r"aws[_-]?access[_-]?key",                            # AWS Access Key
    r"anthropic[_-]?api[_-]?key",                         # Anthropic API Key
    r"openai[_-]?api[_-]?key",                            # OpenAI API Key
    r"private[_-]?key\s*[:=]",                            # Private Key
    r"bearer\s+[a-zA-Z0-9\-._~+/]+=*",                    # Bearer 토큰
    r"token\s*[:=]\s*['\"]?[\w-]{20,}",                   # 일반 토큰
]


# 에러 통계
_ERROR_STATS = {
    "planner": {"attempts": 0, "failures": 0},
    "coder": {"attempts": 0, "failures": 0},
    "reviewer": {"attempts": 0, "failures": 0},
    "tester": {"attempts": 0, "failures": 0},
    "committer": {"attempts": 0, "failures": 0}
}


async def retry_with_backoff(
    func: Callable,
    worker_name: str,
    max_retries: int = 3,
    base_delay: float = 1.0
) -> Dict[str, Any]:
    """
    재시도 로직이 포함된 래퍼

    Args:
        func: 실행할 비동기 함수
        worker_name: Worker 이름 (로깅용)
        max_retries: 최대 재시도 횟수
        base_delay: 기본 대기 시간 (초)

    Returns:
        함수 실행 결과
    """
    _ERROR_STATS[worker_name]["attempts"] += 1

    for attempt in range(max_retries):
        try:
            result = await func()
            return result

        except Exception as e:
            _ERROR_STATS[worker_name]["failures"] += 1

            if attempt < max_retries - 1:
                # Exponential backoff
                wait_time = base_delay * (2 ** attempt)
                logger.warning(
                    f"⚠️  [{worker_name}] 시도 {attempt + 1}/{max_retries} 실패: {e}. "
                    f"{wait_time}초 후 재시도..."
                )
                await asyncio.sleep(wait_time)
            else:
                # 최종 실패 - 예외를 다시 던져서 호출자가 처리하도록 함
                logger.error(
                    f"❌ [{worker_name}] {max_retries}회 시도 후 최종 실패: {e}"
                )
                raise

    # 여기 도달하면 안 됨
    raise RuntimeError("Unexpected error in retry_with_backoff")


# 전역 변수로 Worker Agent 인스턴스들을 저장
_WORKER_AGENTS: Dict[str, WorkerAgent] = {}

# 메트릭 수집기 (선택적)
_METRICS_COLLECTOR: Optional[MetricsCollector] = None
_CURRENT_SESSION_ID: Optional[str] = None

# 워크플로우 콜백 (TUI에서 설정)
_WORKFLOW_CALLBACK: Optional[Callable] = None


async def _verify_git_environment() -> Tuple[bool, Optional[str]]:
    """
    Git 설치 및 저장소 확인

    Returns:
        (성공 여부, 에러 메시지)
    """
    try:
        # Git이 설치되어 있는지 확인
        proc = await asyncio.create_subprocess_shell(
            "git --version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            return False, "Git이 설치되어 있지 않습니다."

        # Git 저장소인지 확인
        proc = await asyncio.create_subprocess_shell(
            "git rev-parse --is-inside-work-tree",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            return False, "현재 디렉토리가 Git 저장소가 아닙니다."

        return True, None

    except Exception as e:
        logger.error(f"Git 환경 검증 실패: {e}")
        return False, f"Git 환경 검증 중 오류 발생: {str(e)}"


async def _validate_commit_safety() -> Tuple[bool, Optional[str]]:
    """
    커밋 안전성 검증 (민감 정보 포함 여부)

    Returns:
        (안전 여부, 에러 메시지)
    """
    try:
        # git status --porcelain으로 변경된 파일 목록 가져오기
        proc = await asyncio.create_subprocess_shell(
            "git status --porcelain",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            return False, f"Git status 실행 실패: {stderr.decode('utf-8', errors='ignore')}"

        # 변경된 파일 목록 파싱
        status_output = stdout.decode("utf-8", errors="ignore")
        changed_files = []

        for line in status_output.splitlines():
            if len(line) < 4:
                continue
            # 상태 코드(2자) + 공백 + 파일명
            file_path = line[3:].strip()
            # -> 로 리네임된 경우 처리
            if " -> " in file_path:
                file_path = file_path.split(" -> ")[1]
            changed_files.append(file_path)

        if not changed_files:
            return False, "커밋할 변경 사항이 없습니다."

        # 1단계: 파일명 패턴 검증
        sensitive_files = []
        for file_path in changed_files:
            file_name = Path(file_path).name
            for pattern in SENSITIVE_FILE_PATTERNS:
                if re.match(pattern, file_name, re.IGNORECASE):
                    sensitive_files.append(file_path)
                    break

        if sensitive_files:
            files_str = "\n  - ".join(sensitive_files)
            return False, (
                f"민감한 파일명이 감지되었습니다:\n  - {files_str}\n\n"
                "이러한 파일은 일반적으로 커밋하지 않아야 합니다. "
                "정말 커밋하려면 .gitignore에 추가하거나 수동으로 커밋하세요."
            )

        # 2단계: 파일 내용 스캔 (정규식)
        sensitive_content = []
        for file_path in changed_files:
            # 바이너리 파일이나 큰 파일은 스킵
            try:
                path_obj = Path(file_path)
                if not path_obj.exists():
                    continue

                # 파일 크기 체크 (10MB 이상은 스킵)
                if path_obj.stat().st_size > 10 * 1024 * 1024:
                    logger.debug(f"파일이 너무 큼, 스캔 스킵: {file_path}")
                    continue

                # 텍스트 파일인지 확인
                with open(path_obj, "rb") as f:
                    chunk = f.read(8192)
                    if b"\x00" in chunk:
                        # 바이너리 파일은 스킵
                        logger.debug(f"바이너리 파일, 스캔 스킵: {file_path}")
                        continue

                # 파일 내용 읽기
                with open(path_obj, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                # 민감 패턴 검색
                for pattern in SENSITIVE_CONTENT_PATTERNS:
                    matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
                    for match in matches:
                        sensitive_content.append({
                            "file": file_path,
                            "pattern": pattern,
                            "match": match.group()[:50] + "..." if len(match.group()) > 50 else match.group()
                        })
                        break  # 파일당 한 번만 경고

            except Exception as e:
                logger.warning(f"파일 스캔 중 오류 (무시하고 계속): {file_path} - {e}")
                continue

        if sensitive_content:
            findings = []
            for item in sensitive_content[:5]:  # 최대 5개만 표시
                findings.append(f"  - {item['file']}: {item['match']}")
            findings_str = "\n".join(findings)

            if len(sensitive_content) > 5:
                findings_str += f"\n  ... 외 {len(sensitive_content) - 5}개"

            return False, (
                f"민감한 정보가 파일 내용에서 감지되었습니다:\n{findings_str}\n\n"
                "API 키, 비밀번호, 토큰 등은 커밋하지 않아야 합니다. "
                "환경 변수나 설정 파일(.env)을 사용하고 .gitignore에 추가하세요."
            )

        # 모든 검증 통과
        return True, None

    except Exception as e:
        logger.error(f"커밋 안전성 검증 실패: {e}")
        # 검증 실패 시 False Positive 방지를 위해 경고만 표시
        return True, None


def initialize_workers(config_path: Path):
    """
    Worker Agent들을 초기화합니다.

    Args:
        config_path: Agent 설정 파일 경로
    """
    global _WORKER_AGENTS

    loader = JsonConfigLoader(get_project_root())
    worker_configs = loader.load_agent_configs()

    for config in worker_configs:
        worker = WorkerAgent(config)
        _WORKER_AGENTS[config.name] = worker
        logger.info(f"✅ Worker Agent 초기화: {config.name} ({config.role})")


def set_metrics_collector(collector: MetricsCollector, session_id: str) -> None:
    """
    메트릭 컬렉터 설정 (TUI/CLI에서 호출)

    Args:
        collector: 메트릭 수집기
        session_id: 현재 세션 ID
    """
    global _METRICS_COLLECTOR, _CURRENT_SESSION_ID
    _METRICS_COLLECTOR = collector
    _CURRENT_SESSION_ID = session_id
    logger.info(f"✅ 메트릭 컬렉터 설정 완료 (Session: {session_id})")


def update_session_id(session_id: str) -> None:
    """
    현재 세션 ID 업데이트

    Args:
        session_id: 새 세션 ID
    """
    global _CURRENT_SESSION_ID
    _CURRENT_SESSION_ID = session_id
    logger.info(f"✅ 세션 ID 업데이트: {session_id}")


def set_workflow_callback(callback: Optional[Callable]) -> None:
    """
    워크플로우 상태 업데이트 콜백 설정

    Args:
        callback: 워크플로우 상태 업데이트 함수
                  시그니처: callback(worker_name: str, status: str, error: Optional[str])
    """
    global _WORKFLOW_CALLBACK
    _WORKFLOW_CALLBACK = callback
    logger.info("✅ 워크플로우 콜백 설정 완료")


async def _execute_worker_task(
    worker_name: str,
    task_description: str,
    use_retry: bool = False
) -> Dict[str, Any]:
    """
    Worker Agent 실행 공통 로직

    Args:
        worker_name: Worker 이름 (예: "planner", "coder")
        task_description: 작업 설명
        use_retry: 재시도 로직 사용 여부

    Returns:
        Agent 실행 결과
    """
    logger.debug(f"[{worker_name.capitalize()} Tool] 작업 실행: {task_description[:50]}...")

    worker = _WORKER_AGENTS.get(worker_name)
    if not worker:
        return {
            "content": [
                {"type": "text", "text": f"❌ {worker_name.capitalize()} Agent를 찾을 수 없습니다."}
            ]
        }

    # 메트릭 수집 시작
    start_time = datetime.now()
    success = False
    error_message = None

    # 워크플로우 콜백: RUNNING 상태
    if _WORKFLOW_CALLBACK:
        try:
            _WORKFLOW_CALLBACK(worker_name, "running", None)
        except Exception as e:
            logger.warning(f"워크플로우 콜백 실행 실패 (running): {e}")

    async def execute():
        result = ""
        async for chunk in worker.execute_task(task_description):
            result += chunk
        return {"content": [{"type": "text", "text": result}]}

    try:
        if use_retry:
            result = await retry_with_backoff(execute, worker_name)
        else:
            _ERROR_STATS[worker_name]["attempts"] += 1
            result = await execute()

        success = True

        # 워크플로우 콜백: COMPLETED 상태
        if _WORKFLOW_CALLBACK:
            try:
                _WORKFLOW_CALLBACK(worker_name, "completed", None)
            except Exception as e:
                logger.warning(f"워크플로우 콜백 실행 실패 (completed): {e}")

        return result

    except Exception as e:
        _ERROR_STATS[worker_name]["failures"] += 1
        error_message = str(e)
        logger.error(f"[{worker_name.capitalize()} Tool] 실행 실패: {e}")

        # 워크플로우 콜백: FAILED 상태
        if _WORKFLOW_CALLBACK:
            try:
                _WORKFLOW_CALLBACK(worker_name, "failed", str(e))
            except Exception as callback_error:
                logger.warning(f"워크플로우 콜백 실행 실패 (failed): {callback_error}")

        return {
            "content": [
                {"type": "text", "text": f"❌ {worker_name.capitalize()} 실행 실패: {e}"}
            ]
        }

    finally:
        # 메트릭 기록 (컬렉터가 설정되어 있으면)
        if _METRICS_COLLECTOR and _CURRENT_SESSION_ID:
            end_time = datetime.now()
            try:
                _METRICS_COLLECTOR.record_worker_execution(
                    session_id=_CURRENT_SESSION_ID,
                    worker_name=worker_name,
                    task_description=task_description[:100],  # 너무 길면 잘라냄
                    start_time=start_time,
                    end_time=end_time,
                    success=success,
                    tokens_used=None,  # 추후 Claude SDK에서 토큰 정보 가져오면 추가
                    error_message=error_message,
                )
            except Exception as metrics_error:
                # 메트릭 기록 실패는 로그만 남기고 무시
                logger.warning(f"메트릭 기록 실패: {metrics_error}")


@tool(
    "execute_planner_task",
    "Planner Agent에게 작업을 할당합니다. 요구사항 분석 및 계획 수립을 담당합니다.",
    {"task_description": str}
)
async def execute_planner_task(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Planner Agent 실행 (재시도 로직 포함)

    Args:
        args: {"task_description": "작업 설명"}

    Returns:
        Agent 실행 결과
    """
    return await _execute_worker_task("planner", args["task_description"], use_retry=True)


@tool(
    "execute_coder_task",
    "Coder Agent에게 작업을 할당합니다. 코드 작성, 수정, 리팩토링을 담당합니다.",
    {"task_description": str}
)
async def execute_coder_task(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Coder Agent 실행

    Args:
        args: {"task_description": "작업 설명"}

    Returns:
        Agent 실행 결과
    """
    return await _execute_worker_task("coder", args["task_description"], use_retry=False)


@tool(
    "execute_tester_task",
    "Tester Agent에게 작업을 할당합니다. 테스트 작성 및 실행을 담당합니다.",
    {"task_description": str}
)
async def execute_tester_task(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tester Agent 실행

    Args:
        args: {"task_description": "작업 설명"}

    Returns:
        Agent 실행 결과
    """
    return await _execute_worker_task("tester", args["task_description"], use_retry=False)


@tool(
    "execute_reviewer_task",
    "Reviewer Agent에게 작업을 할당합니다. 코드 리뷰 및 품질 검증을 담당합니다.",
    {"task_description": str}
)
async def execute_reviewer_task(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Reviewer Agent 실행

    Args:
        args: {"task_description": "작업 설명"}

    Returns:
        Agent 실행 결과
    """
    return await _execute_worker_task("reviewer", args["task_description"], use_retry=False)


@tool(
    "execute_committer_task",
    "Committer Agent에게 작업을 할당합니다. Git 커밋 생성을 담당합니다.",
    {"task_description": str}
)
async def execute_committer_task(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Committer Agent 실행 (보안 검증 포함)

    Args:
        args: {"task_description": "작업 설명"}

    Returns:
        Agent 실행 결과
    """
    logger.debug(f"[Committer Tool] 작업 실행 시작: {args['task_description'][:50]}...")

    # 1단계: Git 환경 검증
    is_valid, error_msg = await _verify_git_environment()
    if not is_valid:
        logger.error(f"[Committer Tool] Git 환경 오류: {error_msg}")
        return {
            "content": [
                {"type": "text", "text": f"❌ Git 환경 오류: {error_msg}"}
            ]
        }

    # 2단계: 민감 정보 검증
    is_safe, error_msg = await _validate_commit_safety()
    if not is_safe:
        logger.warning(f"[Committer Tool] 커밋 거부 (민감 정보 감지): {error_msg}")
        return {
            "content": [
                {"type": "text", "text": f"❌ 커밋 거부 (보안 검증 실패):\n\n{error_msg}"}
            ]
        }

    # 3단계: 모든 검증 통과 - Committer Agent 실행
    logger.info("[Committer Tool] 보안 검증 통과 - Committer Agent 실행")
    return await _execute_worker_task("committer", args["task_description"], use_retry=False)


def get_error_statistics() -> Dict[str, Any]:
    """
    에러 통계 조회

    Returns:
        각 Worker의 시도/실패 통계 및 에러율
    """
    stats = {}
    for worker_name, data in _ERROR_STATS.items():
        attempts = data["attempts"]
        failures = data["failures"]
        error_rate = (failures / attempts * 100) if attempts > 0 else 0.0

        stats[worker_name] = {
            "attempts": attempts,
            "failures": failures,
            "successes": attempts - failures,
            "error_rate": round(error_rate, 2)
        }

    return stats


def reset_error_statistics():
    """
    에러 통계 초기화
    """
    global _ERROR_STATS
    for worker_name in _ERROR_STATS:
        _ERROR_STATS[worker_name]["attempts"] = 0
        _ERROR_STATS[worker_name]["failures"] = 0
    logger.info("✅ 에러 통계 초기화 완료")


def log_error_summary():
    """
    에러 통계 요약 로그 출력
    """
    stats = get_error_statistics()
    logger.info("=" * 60)
    logger.info("📊 Worker Tools 에러 통계")
    logger.info("=" * 60)

    for worker_name, data in stats.items():
        logger.info(
            f"[{worker_name.upper()}] "
            f"시도: {data['attempts']}, "
            f"성공: {data['successes']}, "
            f"실패: {data['failures']}, "
            f"에러율: {data['error_rate']}%"
        )

    logger.info("=" * 60)


def create_worker_tools_server():
    """
    Worker Tool들을 포함하는 MCP 서버 생성

    Returns:
        MCP 서버 인스턴스
    """
    server = create_sdk_mcp_server(
        name="workers",
        version="1.0.0",
        tools=[
            execute_planner_task,
            execute_coder_task,
            execute_reviewer_task,
            execute_tester_task,
            execute_committer_task
        ]
    )

    logger.info("✅ Worker Tools MCP Server 생성 완료")

    return server
