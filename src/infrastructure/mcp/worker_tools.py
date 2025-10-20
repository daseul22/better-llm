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
import os
from functools import wraps
from datetime import datetime

from claude_agent_sdk import tool, create_sdk_mcp_server
from claude_agent_sdk.types import ClaudeAgentOptions

from ..claude import WorkerAgent
from domain.models import AgentConfig
from domain.services import MetricsCollector
from ..config import JsonConfigLoader, get_project_root
from ..logging import get_logger, log_exception_silently

logger = get_logger(__name__, component="WorkerTools")


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
    "committer": {"attempts": 0, "failures": 0},
    "ideator": {"attempts": 0, "failures": 0},
    "product_manager": {"attempts": 0, "failures": 0},
    "parallel_executor": {"attempts": 0, "failures": 0}
}

def _get_timeout_from_env(worker_name: str, default: int) -> int:
    """
    환경변수에서 타임아웃 값 가져오기 (안전한 int 변환)

    Args:
        worker_name: Worker 이름 (예: "planner", "coder")
        default: 기본값

    Returns:
        타임아웃 값 (초)
    """
    env_var = f"WORKER_TIMEOUT_{worker_name.upper()}"
    value = os.getenv(env_var)

    if value is None:
        return default

    try:
        return int(value)
    except ValueError:
        logger.warning(
            f"환경변수 {env_var}의 값 '{value}'을(를) 정수로 변환할 수 없습니다. "
            f"기본값 {default}초를 사용합니다."
        )
        return default


# Worker별 타임아웃 설정 (초 단위, 환경변수 > system_config.json > 기본값 순)
# 나중에 _load_worker_timeouts()로 초기화됨
_WORKER_TIMEOUTS = {
    "planner": _get_timeout_from_env("planner", 300),
    "coder": _get_timeout_from_env("coder", 600),
    "reviewer": _get_timeout_from_env("reviewer", 300),
    "tester": _get_timeout_from_env("tester", 600),
    "committer": _get_timeout_from_env("committer", 180),
    "ideator": _get_timeout_from_env("ideator", 300),
    "product_manager": _get_timeout_from_env("product_manager", 300),
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


# 전역 변수로 Worker Agent 인스턴스들을 저장
_WORKER_AGENTS: Dict[str, WorkerAgent] = {}

# 메트릭 수집기 (선택적)
_METRICS_COLLECTOR: Optional[MetricsCollector] = None
_CURRENT_SESSION_ID: Optional[str] = None

# 워크플로우 콜백 (TUI에서 설정)
_WORKFLOW_CALLBACK: Optional[Callable] = None

# Worker 출력 스트리밍 콜백 (TUI에서 설정)
_WORKER_OUTPUT_CALLBACK: Optional[Callable] = None

# Review cycle 추적 (무한 루프 방지)
_REVIEW_CYCLE_STATE = {
    "count": 0,
    "max_cycles": 3,
    "last_reviewer_call_time": None,
    "coder_called_after_reviewer": False
}


def reset_review_cycle() -> None:
    """
    Review cycle을 초기화합니다.

    새 작업 시작 시 호출하여 이전 작업의 review count가 누적되지 않도록 합니다.
    """
    global _REVIEW_CYCLE_STATE
    _REVIEW_CYCLE_STATE["count"] = 0
    _REVIEW_CYCLE_STATE["last_reviewer_call_time"] = None
    _REVIEW_CYCLE_STATE["coder_called_after_reviewer"] = False
    logger.info("🔄 Review cycle has been reset")


def _increment_review_cycle() -> tuple[int, bool]:
    """
    Review cycle을 증가시키고 현재 값을 반환합니다.

    Returns:
        tuple[int, bool]: (현재 cycle 수, 최대치 초과 여부)
    """
    global _REVIEW_CYCLE_STATE

    _REVIEW_CYCLE_STATE["count"] += 1
    current_cycle = _REVIEW_CYCLE_STATE["count"]
    max_cycles = _REVIEW_CYCLE_STATE["max_cycles"]
    exceeded = current_cycle > max_cycles

    logger.info(
        f"🔄 Review cycle incremented: {current_cycle}/{max_cycles} "
        f"({'EXCEEDED' if exceeded else 'OK'})"
    )

    return current_cycle, exceeded


def _load_worker_timeouts_from_config():
    """
    system_config.json에서 Worker 타임아웃 로드

    환경변수가 설정되어 있으면 우선 사용,
    없으면 system_config.json 값 사용,
    둘 다 없으면 기본값 사용
    """
    global _WORKER_TIMEOUTS

    try:
        from ..config import load_system_config

        config = load_system_config()
        timeouts = config.get("timeouts", {})

        # 환경변수 > system_config.json > 기본값 순으로 우선순위
        _WORKER_TIMEOUTS["planner"] = _get_timeout_from_env(
            "planner", timeouts.get("planner_timeout", 300)
        )
        _WORKER_TIMEOUTS["coder"] = _get_timeout_from_env(
            "coder", timeouts.get("coder_timeout", 600)
        )
        _WORKER_TIMEOUTS["reviewer"] = _get_timeout_from_env(
            "reviewer", timeouts.get("reviewer_timeout", 300)
        )
        _WORKER_TIMEOUTS["tester"] = _get_timeout_from_env(
            "tester", timeouts.get("tester_timeout", 600)
        )
        _WORKER_TIMEOUTS["committer"] = _get_timeout_from_env(
            "committer", timeouts.get("committer_timeout", 180)
        )
        _WORKER_TIMEOUTS["ideator"] = _get_timeout_from_env(
            "ideator", timeouts.get("ideator_timeout", 300)
        )
        _WORKER_TIMEOUTS["product_manager"] = _get_timeout_from_env(
            "product_manager", timeouts.get("product_manager_timeout", 300)
        )

        logger.debug(f"Worker 타임아웃 설정 로드 완료: {_WORKER_TIMEOUTS}")

    except Exception as e:
        logger.warning(f"system_config.json에서 타임아웃 로드 실패: {e}. 기본값 사용.")


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
    global _WORKER_AGENTS, _REVIEW_CYCLE_STATE

    # system_config.json에서 타임아웃 설정 로드
    _load_worker_timeouts_from_config()

    # system_config.json에서 max_review_iterations 로드
    try:
        from ..config import load_system_config
        config = load_system_config()
        _REVIEW_CYCLE_STATE["max_cycles"] = config.get("workflow_limits", {}).get(
            "max_review_iterations", 3
        )
        logger.info(
            f"✅ Review cycle 최대 횟수: {_REVIEW_CYCLE_STATE['max_cycles']}회"
        )
    except Exception as e:
        logger.warning(f"max_review_iterations 로드 실패: {e}. 기본값 3 사용.")
        _REVIEW_CYCLE_STATE["max_cycles"] = 3

    loader = JsonConfigLoader(get_project_root())
    worker_configs = loader.load_agent_configs()

    for config in worker_configs:
        worker = WorkerAgent(config)
        _WORKER_AGENTS[config.name] = worker
        logger.info(
            "Worker agent initialized",
            worker_name=config.name,
            role=config.role,
            model=config.model
        )


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
    logger.info("Metrics collector configured", session_id=session_id)


def update_session_id(session_id: str) -> None:
    """
    현재 세션 ID 업데이트

    Args:
        session_id: 새 세션 ID
    """
    global _CURRENT_SESSION_ID
    _CURRENT_SESSION_ID = session_id
    logger.info("Session ID updated", session_id=session_id)


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


def set_worker_output_callback(callback: Optional[Callable]) -> None:
    """
    Worker 출력 스트리밍 콜백 설정

    Args:
        callback: Worker 출력 스트리밍 함수
                  시그니처: callback(worker_name: str, chunk: str)
    """
    global _WORKER_OUTPUT_CALLBACK
    _WORKER_OUTPUT_CALLBACK = callback
    logger.info("✅ Worker 출력 스트리밍 콜백 설정 완료")


def worker_tool(
    worker_name: str,
    description: str,
    retry: bool = False,
    security_check: bool = False
) -> Callable:
    """
    Worker Tool 데코레이터 팩토리

    공통 로직을 데코레이터로 추출하여 코드 중복을 제거합니다.

    Args:
        worker_name: Worker 이름 (예: "planner", "coder")
        description: Tool 설명
        retry: 재시도 로직 사용 여부
        security_check: 보안 검증 수행 여부 (Committer 전용)

    Returns:
        데코레이터 함수

    Example:
        @worker_tool("planner", "요구사항 분석 및 계획 수립", retry=True)
        async def execute_planner_task(args: Dict[str, Any]) -> Dict[str, Any]:
            pass
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(args: Dict[str, Any]) -> Dict[str, Any]:
            """
            Worker Tool 래퍼 함수

            Args:
                args: {"task_description": "작업 설명"}

            Returns:
                Agent 실행 결과
            """
            # Committer의 경우 보안 검증 수행
            if security_check:
                logger.debug(
                    f"[{worker_name.capitalize()} Tool] 작업 실행 시작: "
                    f"{args['task_description'][:50]}..."
                )

                # 1단계: Git 환경 검증
                is_valid, error_msg = await _verify_git_environment()
                if not is_valid:
                    logger.error(f"[{worker_name.capitalize()} Tool] Git 환경 오류: {error_msg}")
                    return {
                        "content": [
                            {"type": "text", "text": f"❌ Git 환경 오류: {error_msg}"}
                        ]
                    }

                # 2단계: 민감 정보 검증
                is_safe, error_msg = await _validate_commit_safety()
                if not is_safe:
                    logger.warning(
                        f"[{worker_name.capitalize()} Tool] 커밋 거부 (민감 정보 감지): {error_msg}"
                    )
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": f"❌ 커밋 거부 (보안 검증 실패):\n\n{error_msg}"
                            }
                        ]
                    }

                logger.info(
                    f"[{worker_name.capitalize()} Tool] 보안 검증 통과 - "
                    f"{worker_name.capitalize()} Agent 실행"
                )

            # 공통 실행 로직
            return await _execute_worker_task(
                worker_name,
                args["task_description"],
                use_retry=retry
            )

        # @tool 데코레이터 적용
        return tool(
            f"execute_{worker_name}_task",
            f"{worker_name.capitalize()} Agent에게 작업을 할당합니다. {description}",
            {
                "task_description": {
                    "type": "string",
                    "description": "작업 설명"
                }
            }
        )(wrapper)

    return decorator


async def _execute_worker_task(
    worker_name: str,
    task_description: str,
    use_retry: bool = False
) -> Dict[str, Any]:
    """
    Worker Agent 실행 공통 로직 (타임아웃 적용 + Review cycle 추적)

    Args:
        worker_name: Worker 이름 (예: "planner", "coder")
        task_description: 작업 설명
        use_retry: 재시도 로직 사용 여부

    Returns:
        Agent 실행 결과
    """
    global _REVIEW_CYCLE_STATE

    # Worker 전용 로거 생성 (컨텍스트 포함)
    worker_logger = get_logger(__name__, worker_name=worker_name, component="WorkerExecution")
    worker_logger.debug(
        "Task execution started",
        task_description=task_description[:100]
    )

    worker = _WORKER_AGENTS.get(worker_name)
    if not worker:
        worker_logger.error("Worker agent not found")
        return {
            "content": [
                {"type": "text", "text": f"❌ {worker_name.capitalize()} Agent를 찾을 수 없습니다."}
            ]
        }

    # 새 작업 시작 시 Review cycle 초기화 (Planner 또는 Coder 시작 시)
    if worker_name in ["planner", "coder"]:
        # Planner는 항상 새 작업의 시작이므로 무조건 초기화
        # Coder는 Reviewer 호출 이후가 아니면 새 작업의 시작으로 간주
        if worker_name == "planner" or not _REVIEW_CYCLE_STATE["coder_called_after_reviewer"]:
            reset_review_cycle()

    # Review cycle 추적 로직 (무한 루프 방지)

    if worker_name == "reviewer":
        # Reviewer 호출 시 cycle count 증가 (Coder 호출 후인 경우)
        if _REVIEW_CYCLE_STATE["coder_called_after_reviewer"]:
            _REVIEW_CYCLE_STATE["coder_called_after_reviewer"] = False
            # Cycle count 증가 및 최대치 체크
            current_cycle, exceeded = _increment_review_cycle()

            # 최대 횟수 초과 체크
            if exceeded:
                error_msg = (
                    f"⚠️  Review Cycle이 최대 횟수 "
                    f"({_REVIEW_CYCLE_STATE['max_cycles']}회)를 초과했습니다.\n\n"
                    f"무한 루프를 방지하기 위해 Reviewer 실행을 중단합니다.\n"
                    f"수동으로 코드를 검토하고 수정하거나, 요구사항을 조정해주세요.\n\n"
                    f"(Tip: system_config.json의 'workflow_limits.max_review_iterations'로 "
                    f"최대 횟수를 조정할 수 있습니다.)"
                )
                logger.error(error_msg)

                # Review cycle 초기화
                reset_review_cycle()

                return {
                    "content": [{"type": "text", "text": error_msg}]
                }

        _REVIEW_CYCLE_STATE["last_reviewer_call_time"] = datetime.now()

    elif worker_name == "coder":
        # Reviewer 호출 후 Coder가 호출되면 플래그 설정
        if _REVIEW_CYCLE_STATE["last_reviewer_call_time"] is not None:
            _REVIEW_CYCLE_STATE["coder_called_after_reviewer"] = True
            logger.debug("Reviewer 호출 후 Coder 실행 감지 (다음 Reviewer 호출 시 cycle count 증가)")

    # 타임아웃 설정 가져오기
    timeout = _WORKER_TIMEOUTS.get(worker_name, 300)
    worker_logger.debug("Timeout configured", timeout_seconds=timeout)

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
            # Worker 출력 스트리밍 콜백 호출
            if _WORKER_OUTPUT_CALLBACK:
                try:
                    _WORKER_OUTPUT_CALLBACK(worker_name, chunk)
                except Exception as e:
                    logger.warning(f"Worker 출력 콜백 실행 실패: {e}")
        return {"content": [{"type": "text", "text": result}]}

    try:
        # 타임아웃 적용
        if use_retry:
            result = await asyncio.wait_for(
                retry_with_backoff(execute, worker_name),
                timeout=timeout
            )
        else:
            _ERROR_STATS[worker_name]["attempts"] += 1
            result = await asyncio.wait_for(execute(), timeout=timeout)

        success = True

        # 워크플로우 콜백: COMPLETED 상태
        if _WORKFLOW_CALLBACK:
            try:
                _WORKFLOW_CALLBACK(worker_name, "completed", None)
            except Exception as e:
                logger.warning(f"워크플로우 콜백 실행 실패 (completed): {e}")

        return result

    except asyncio.TimeoutError:
        _ERROR_STATS[worker_name]["failures"] += 1
        error_message = f"타임아웃 ({timeout}초 초과)"
        worker_logger.error(
            "Task execution timeout",
            timeout_seconds=timeout,
            exc_info=True
        )

        # 워크플로우 콜백: FAILED 상태
        if _WORKFLOW_CALLBACK:
            try:
                _WORKFLOW_CALLBACK(worker_name, "failed", error_message)
            except Exception as callback_error:
                logger.warning(f"워크플로우 콜백 실행 실패 (failed): {callback_error}")

        return {
            "content": [
                {
                    "type": "text",
                    "text": (
                        f"❌ {worker_name.capitalize()} 실행 타임아웃\n\n"
                        f"작업이 {timeout}초 내에 완료되지 않았습니다.\n"
                        f"환경변수 WORKER_TIMEOUT_{worker_name.upper()}를 "
                        f"조정하여 타임아웃을 늘릴 수 있습니다."
                    )
                }
            ]
        }

    except Exception as e:
        _ERROR_STATS[worker_name]["failures"] += 1
        error_message = str(e)

        # 런타임 에러를 조용히 로그에 기록 (프로그램 종료하지 않음)
        log_exception_silently(
            worker_logger,
            e,
            f"Worker Tool ({worker_name}) execution failed",
            worker_name=worker_name,
            task_description=task_description[:100]
        )

        # 워크플로우 콜백: FAILED 상태
        if _WORKFLOW_CALLBACK:
            try:
                _WORKFLOW_CALLBACK(worker_name, "failed", str(e))
            except Exception as callback_error:
                logger.warning(f"워크플로우 콜백 실행 실패 (failed): {callback_error}")

        return {
            "content": [
                {
                    "type": "text",
                    "text": (
                        f"❌ {worker_name.capitalize()} 실행 실패\n\n"
                        f"에러: {e}\n\n"
                        f"스택 트레이스는 에러 로그 (~/.better-llm/{{project}}/logs/better-llm-error.log)를 확인하세요."
                    )
                }
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


@worker_tool("planner", "요구사항 분석 및 계획 수립을 담당합니다.", retry=True)
async def execute_planner_task(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Planner Agent 실행 (재시도 로직 포함)

    Args:
        args: {"task_description": "작업 설명"}

    Returns:
        Agent 실행 결과
    """
    pass  # 데코레이터가 모든 로직을 처리


@worker_tool("coder", "코드 작성, 수정, 리팩토링을 담당합니다.", retry=False)
async def execute_coder_task(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Coder Agent 실행

    Args:
        args: {"task_description": "작업 설명"}

    Returns:
        Agent 실행 결과
    """
    pass  # 데코레이터가 모든 로직을 처리


@worker_tool("tester", "테스트 작성 및 실행을 담당합니다.", retry=False)
async def execute_tester_task(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tester Agent 실행

    Args:
        args: {"task_description": "작업 설명"}

    Returns:
        Agent 실행 결과
    """
    pass  # 데코레이터가 모든 로직을 처리


@worker_tool("reviewer", "코드 리뷰 및 품질 검증을 담당합니다.", retry=False)
async def execute_reviewer_task(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Reviewer Agent에게 작업을 할당합니다. 코드 리뷰 및 품질 검증을 담당합니다.

    Review cycle은 무한 루프 방지를 위해 최대 횟수가 제한됩니다.
    (기본값: 3회, system_config.json의 'workflow_limits.max_review_iterations'로 조정 가능)

    Args:
        args: {"task_description": "리뷰 요청 내용"}
              - task_description: 리뷰 대상 및 요청 사항
              - (향후 확장 가능) context: 추가 컨텍스트 정보
              - (향후 확장 가능) severity_threshold: 최소 보고 심각도

    Returns:
        Dict[str, Any]: Agent 실행 결과
            - content: [{"type": "text", "text": "리뷰 결과"}]

    Raises:
        Exception: Review cycle이 최대치를 초과한 경우

    Note:
        - Review cycle은 Reviewer → Coder → Reviewer 패턴을 감지하여 증가합니다.
        - 최대 횟수 초과 시 자동으로 실행이 중단되며, 수동 검토가 필요합니다.
        - 새 작업 시작 시(Planner 또는 Coder 호출) Review cycle이 자동 초기화됩니다.
    """
    pass  # 데코레이터가 모든 로직을 처리


@worker_tool("committer", "Git 커밋 생성을 담당합니다.", retry=False, security_check=True)
async def execute_committer_task(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Committer Agent 실행 (보안 검증 포함)

    Args:
        args: {"task_description": "작업 설명"}

    Returns:
        Agent 실행 결과
    """
    pass  # 데코레이터가 모든 로직을 처리 (보안 검증 포함)


@worker_tool("ideator", "창의적 아이디어 생성 및 브레인스토밍을 담당합니다.", retry=True)
async def execute_ideator_task(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ideator Agent 실행 (재시도 로직 포함)

    Args:
        args: {"task_description": "작업 설명"}

    Returns:
        Agent 실행 결과
    """
    pass  # 데코레이터가 모든 로직을 처리


@worker_tool("product_manager", "제품 기획 및 요구사항 정의를 담당합니다.", retry=True)
async def execute_product_manager_task(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Product Manager Agent 실행 (재시도 로직 포함)

    Args:
        args: {"task_description": "작업 설명"}

    Returns:
        Agent 실행 결과
    """
    pass  # 데코레이터가 모든 로직을 처리


@tool(
    "execute_parallel_tasks",
    "병렬 작업 실행을 수행합니다. Planner가 생성한 병렬 실행 계획 JSON을 받아서 Task들을 병렬로 실행합니다.",
    {
        "plan_json": {
            "type": "string",
            "description": "Planner가 생성한 병렬 실행 계획 JSON 문자열"
        }
    }
)
async def execute_parallel_tasks(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    병렬 작업 실행 Tool

    Planner가 생성한 병렬 실행 계획 JSON을 받아서
    ParallelTaskExecutor를 사용하여 Task들을 병렬 실행합니다.

    Args:
        args: {
            "plan_json": "Planner가 생성한 병렬 실행 계획 JSON 문자열"
        }

    Returns:
        {
            "content": [{"type": "text", "text": "실행 결과"}],
            "success": True/False,
            "metadata": {
                "completed_tasks": int,
                "failed_tasks": int,
                "total_duration": float,
                "speedup_factor": float
            }
        }
    """
    from domain.models.parallel_task import TaskExecutionPlan, ParallelTask
    from domain.services.parallel_executor import ParallelTaskExecutor
    import json
    import re

    worker_name = "parallel_executor"
    _record_attempt(worker_name)

    try:
        # 인자 검증
        if "plan_json" not in args:
            raise ValueError("plan_json 인자가 필요합니다")

        plan_json_raw = args["plan_json"]

        # JSON 추출 (```json ... ``` 마크다운 코드 블록 제거)
        json_match = re.search(r'```json\s*(.*?)\s*```', plan_json_raw, re.DOTALL)
        if json_match:
            plan_json = json_match.group(1).strip()
        else:
            plan_json = plan_json_raw.strip()

        logger.info(f"[{worker_name}] 병렬 실행 계획 파싱 시작")

        # TaskExecutionPlan 생성
        try:
            plan = TaskExecutionPlan.from_json(plan_json)
        except ValueError as e:
            raise ValueError(f"병렬 실행 계획 파싱 실패: {e}")

        logger.info(
            f"[{worker_name}] {len(plan.tasks)}개 Task 병렬 실행 시작",
            task_ids=[task.id for task in plan.tasks]
        )

        # Coder Worker를 task_executor로 래핑
        async def coder_task_executor(task: ParallelTask) -> str:
            """단일 Task 실행 (Coder Worker 호출)"""
            coder_agent = _WORKER_AGENTS.get("coder")
            if not coder_agent:
                raise RuntimeError("Coder Agent를 찾을 수 없습니다")

            # Coder에게 전달할 작업 설명
            # Task description에 target_files 정보 추가
            task_description = task.description
            if task.target_files:
                task_description += f"\n\n**Target Files**: {', '.join(task.target_files)}"

            result = ""
            async for chunk in coder_agent.execute_task(task_description):
                result += chunk

            return result

        # ParallelTaskExecutor 생성 및 실행
        executor = ParallelTaskExecutor(
            task_executor=coder_task_executor,
            max_concurrent_tasks=5  # 동시 실행 최대 5개
        )

        execution_result = await executor.execute(plan)

        # 결과 포맷팅
        result_lines = []
        result_lines.append(f"🚀 병렬 실행 완료\n")
        result_lines.append(f"📊 실행 결과:")
        result_lines.append(f"   - 성공: {len(execution_result.completed_tasks)}개")
        result_lines.append(f"   - 실패: {len(execution_result.failed_tasks)}개")
        result_lines.append(f"   - 실행 시간: {execution_result.total_duration:.1f}초")
        result_lines.append(f"   - 속도 향상: {execution_result.speedup_factor:.2f}x")
        result_lines.append(f"   - 성공률: {execution_result.success_rate * 100:.0f}%\n")

        # 완료된 Task 상세
        if execution_result.completed_tasks:
            result_lines.append("✅ 완료된 Task:")
            for task in execution_result.completed_tasks:
                result_lines.append(f"   - [{task.id}] {task.description}")
                result_lines.append(f"     파일: {', '.join(task.target_files)}")
                if task.duration_seconds():
                    result_lines.append(f"     실행 시간: {task.duration_seconds():.1f}초")
                result_lines.append("")

        # 실패한 Task 상세
        if execution_result.failed_tasks:
            result_lines.append("❌ 실패한 Task:")
            for task in execution_result.failed_tasks:
                result_lines.append(f"   - [{task.id}] {task.description}")
                result_lines.append(f"     에러: {task.error}")
                result_lines.append("")

        # 통합 주의사항
        if plan.integration_notes:
            result_lines.append(f"📝 통합 시 주의사항:")
            result_lines.append(f"   {plan.integration_notes}\n")

        result_text = "\n".join(result_lines)

        logger.info(
            f"[{worker_name}] 병렬 실행 완료",
            completed=len(execution_result.completed_tasks),
            failed=len(execution_result.failed_tasks),
            duration=execution_result.total_duration
        )

        return {
            "content": [{"type": "text", "text": result_text}],
            "success": execution_result.all_succeeded,
            "metadata": {
                "completed_tasks": len(execution_result.completed_tasks),
                "failed_tasks": len(execution_result.failed_tasks),
                "total_duration": execution_result.total_duration,
                "speedup_factor": execution_result.speedup_factor,
                "success_rate": execution_result.success_rate
            }
        }

    except Exception as e:
        _record_failure(worker_name)
        logger.error(f"[{worker_name}] 병렬 실행 실패: {e}", exc_info=True)
        return {
            "content": [{"type": "text", "text": f"❌ 병렬 실행 실패: {e}"}],
            "success": False,
            "error": str(e)
        }


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
            execute_committer_task,
            execute_ideator_task,
            execute_product_manager_task,
            execute_parallel_tasks  # 병렬 실행 Tool
        ]
    )

    logger.info("✅ Worker Tools MCP Server 생성 완료 (병렬 실행 포함)")

    return server
