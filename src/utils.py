"""
유틸리티 함수

설정 로드, 세션 관리, 로깅 등의 헬퍼 함수들
"""

import json
import logging
import uuid
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

from .models import AgentConfig
from dataclasses import dataclass


# 프로젝트 루트 디렉토리 (better-llm)
# orchestrator.py, tui.py가 있는 디렉토리
_PROJECT_ROOT = None


def get_project_root() -> Path:
    """
    프로젝트 루트 디렉토리 반환

    orchestrator.py 또는 tui.py가 있는 디렉토리를 프로젝트 루트로 간주

    Returns:
        프로젝트 루트 디렉토리 (절대 경로)
    """
    global _PROJECT_ROOT

    if _PROJECT_ROOT is not None:
        return _PROJECT_ROOT

    # 현재 파일(utils.py)의 부모의 부모 = better-llm
    # better-llm/src/utils.py -> better-llm
    _PROJECT_ROOT = Path(__file__).parent.parent.resolve()

    return _PROJECT_ROOT


def set_project_root(path: Path) -> None:
    """
    프로젝트 루트 디렉토리 수동 설정

    Args:
        path: 프로젝트 루트 디렉토리 경로
    """
    global _PROJECT_ROOT
    _PROJECT_ROOT = path.resolve()


@dataclass
class SystemConfig:
    """시스템 설정"""
    # Manager 설정
    manager_model: str = "claude-sonnet-4-5-20250929"
    max_history_messages: int = 20
    max_turns: int = 10

    # 성능 설정
    enable_caching: bool = True
    worker_retry_enabled: bool = True
    worker_retry_max_attempts: int = 3
    worker_retry_base_delay: float = 1.0

    # 보안 설정
    max_input_length: int = 5000
    enable_input_validation: bool = True

    # 로깅 설정
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    enable_structured_logging: bool = False

    @classmethod
    def from_dict(cls, data: Dict) -> "SystemConfig":
        """딕셔너리에서 SystemConfig 생성"""
        manager = data.get("manager", {})
        performance = data.get("performance", {})
        security = data.get("security", {})
        logging_config = data.get("logging", {})

        return cls(
            manager_model=manager.get("model", "claude-sonnet-4-5-20250929"),
            max_history_messages=manager.get("max_history_messages", 20),
            max_turns=manager.get("max_turns", 10),
            enable_caching=performance.get("enable_caching", True),
            worker_retry_enabled=performance.get("worker_retry_enabled", True),
            worker_retry_max_attempts=performance.get("worker_retry_max_attempts", 3),
            worker_retry_base_delay=performance.get("worker_retry_base_delay", 1.0),
            max_input_length=security.get("max_input_length", 5000),
            enable_input_validation=security.get("enable_input_validation", True),
            log_level=logging_config.get("level", "INFO"),
            log_format=logging_config.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
            enable_structured_logging=logging_config.get("enable_structured_logging", False)
        )


def load_system_config(config_path: Optional[Path] = None) -> SystemConfig:
    """
    시스템 설정 파일 로드 (프로젝트 루트 기준)

    Args:
        config_path: 설정 파일 경로 (기본: config/system_config.json, 프로젝트 루트 기준)

    Returns:
        SystemConfig 객체
    """
    if config_path is None:
        # 프로젝트 루트 기준
        config_path = get_project_root() / "config" / "system_config.json"
    elif not config_path.is_absolute():
        # 상대 경로면 프로젝트 루트 기준으로 변환
        config_path = get_project_root() / config_path

    if not config_path.exists():
        logging.warning(f"시스템 설정 파일이 없습니다: {config_path}. 기본값 사용.")
        return SystemConfig()

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return SystemConfig.from_dict(data)
    except Exception as e:
        logging.error(f"시스템 설정 로드 실패: {e}. 기본값 사용.")
        return SystemConfig()


def setup_logging(verbose: bool = False) -> None:
    """
    로깅 설정

    Args:
        verbose: 상세 로깅 활성화 여부
    """
    level = logging.DEBUG if verbose else logging.INFO
    format_str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    logging.basicConfig(
        level=level,
        format=format_str,
        datefmt="%Y-%m-%d %H:%M:%S"
    )


def load_agent_config(config_path: Path) -> List[AgentConfig]:
    """
    에이전트 설정 파일 로드

    Args:
        config_path: 설정 파일 경로 (agent_config.json)

    Returns:
        AgentConfig 리스트

    Raises:
        FileNotFoundError: 설정 파일이 없을 경우
        ValueError: 설정 파일 형식이 잘못된 경우
    """
    if not config_path.exists():
        raise FileNotFoundError(f"설정 파일을 찾을 수 없습니다: {config_path}")

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 유효성 검증
        if "agents" not in data:
            raise ValueError("설정 파일에 'agents' 필드가 없습니다")

        agents_data = data["agents"]
        if not isinstance(agents_data, list):
            raise ValueError("'agents'는 리스트여야 합니다")

        # AgentConfig 객체 생성
        agent_configs = []
        for agent_data in agents_data:
            # 필수 필드 검증
            required_fields = ["name", "role", "system_prompt_file", "tools", "model"]
            for field in required_fields:
                if field not in agent_data:
                    raise ValueError(f"에이전트 설정에 필수 필드 '{field}'가 없습니다: {agent_data}")

            # system_prompt_file을 system_prompt로 변환
            agent_data_copy = agent_data.copy()
            agent_data_copy["system_prompt"] = agent_data_copy.pop("system_prompt_file")

            config = AgentConfig.from_dict(agent_data_copy)
            agent_configs.append(config)

        return agent_configs

    except json.JSONDecodeError as e:
        raise ValueError(f"JSON 파싱 실패: {e}")
    except Exception as e:
        raise ValueError(f"설정 파일 로드 실패: {e}")


def generate_session_id() -> str:
    """
    고유한 세션 ID 생성

    Returns:
        UUID 기반 세션 ID
    """
    return str(uuid.uuid4())[:8]


def create_session_filename(session_id: str, user_request: str) -> str:
    """
    세션 히스토리 파일명 생성

    Args:
        session_id: 세션 ID
        user_request: 사용자 요청 (요약용)

    Returns:
        파일명 (예: session_abc123_결제시스템구현.json)
    """
    # 사용자 요청을 파일명으로 사용 가능한 형태로 변환
    # 공백 제거, 특수문자 제거, 최대 20자
    safe_request = "".join(c for c in user_request if c.isalnum() or c.isspace())
    safe_request = safe_request.replace(" ", "")[:20]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"session_{session_id}_{timestamp}_{safe_request}.json"


def save_session_history(
    session_id: str,
    user_request: str,
    history: List,
    result: Dict,
    output_dir: Path
) -> Path:
    """
    세션 히스토리를 JSON 파일로 저장

    Args:
        session_id: 세션 ID
        user_request: 사용자 요청
        history: 대화 히스토리 (ConversationHistory 객체)
        result: 작업 결과 (SessionResult 객체의 dict)
        output_dir: 출력 디렉토리

    Returns:
        저장된 파일 경로
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = create_session_filename(session_id, user_request)
    filepath = output_dir / filename

    # 대화 히스토리에서 에이전트 사용 목록 추출
    agents_used = list(set(
        msg.agent_name for msg in history.messages
        if msg.role == "agent" and msg.agent_name
    ))

    session_data = {
        "session_id": session_id,
        "created_at": history.messages[0].timestamp.isoformat() if history.messages else datetime.now().isoformat(),
        "completed_at": datetime.now().isoformat(),
        "user_request": user_request,
        "total_turns": sum(1 for msg in history.messages if msg.role == "agent"),
        "agents_used": sorted(agents_used),
        "messages": [msg.to_dict() for msg in history.messages],
        "result": result
    }

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(session_data, f, ensure_ascii=False, indent=2)

    return filepath


def print_header(title: str, width: int = 60) -> None:
    """
    CLI 헤더 출력

    Args:
        title: 헤더 제목
        width: 전체 너비
    """
    print()
    print("┌" + "─" * (width - 2) + "┐")
    print(f"│ {title:<{width - 4}} │")
    print("└" + "─" * (width - 2) + "┘")
    print()


def print_footer(session_id: str, total_turns: int, duration: float, files_modified: int, filepath: Path) -> None:
    """
    CLI 푸터 (완료 요약) 출력

    Args:
        session_id: 세션 ID
        total_turns: 총 턴 수
        duration: 소요 시간 (초)
        files_modified: 수정된 파일 수
        filepath: 저장된 히스토리 파일 경로
    """
    print()
    print("┌" + "─" * 58 + "┐")
    print("│ " + "작업 완료".ljust(56) + " │")
    print("├" + "─" * 58 + "┤")
    print(f"│ 세션 ID: {session_id:<45} │")
    print(f"│ 총 턴: {total_turns:<48} │")
    print(f"│ 소요 시간: {duration:.1f}초{' ' * (48 - len(f'{duration:.1f}'))}│")
    print(f"│ 수정된 파일: {files_modified}개{' ' * (45 - len(str(files_modified)))}│")
    print(f"│ 히스토리: {filepath.name:<44} │")
    print("└" + "─" * 58 + "┘")
    print()


def get_agent_emoji(agent_name: str) -> str:
    """
    에이전트별 이모지 반환

    Args:
        agent_name: 에이전트 이름

    Returns:
        이모지 문자열
    """
    emoji_map = {
        "planner": "🧠",
        "coder": "💻",
        "tester": "🧪",
        "user": "👤"
    }
    return emoji_map.get(agent_name, "🤖")


def validate_user_input(user_input: str, max_length: int = 5000) -> tuple[bool, Optional[str]]:
    """
    사용자 입력을 검증합니다.

    Args:
        user_input: 사용자 입력 문자열
        max_length: 최대 길이 (기본 5000자)

    Returns:
        (is_valid, error_message) 튜플
        - is_valid: 입력이 유효하면 True
        - error_message: 유효하지 않을 경우 에러 메시지
    """
    # 1. 빈 입력 체크
    if not user_input or not user_input.strip():
        return False, "입력이 비어있습니다."

    # 2. 길이 체크
    if len(user_input) > max_length:
        return False, f"입력이 너무 깁니다. (최대 {max_length}자, 현재 {len(user_input)}자)"

    # 3. 위험한 패턴 감지 (프롬프트 인젝션 방지)
    dangerous_patterns = [
        "system:",
        "assistant:",
        "<|im_start|>",
        "<|im_end|>",
        "###instruction",
        "###system",
    ]

    user_input_lower = user_input.lower()
    for pattern in dangerous_patterns:
        if pattern in user_input_lower:
            return False, f"입력에 허용되지 않는 패턴이 포함되어 있습니다: {pattern}"

    # 4. 제어 문자 체크 (일부 허용: \n, \t)
    for char in user_input:
        if char.isprintable() or char in ['\n', '\t']:
            continue
        # 비정상적인 제어 문자
        return False, f"입력에 허용되지 않는 제어 문자가 포함되어 있습니다."

    return True, None


def sanitize_user_input(user_input: str) -> str:
    """
    사용자 입력을 정제합니다.

    Args:
        user_input: 사용자 입력 문자열

    Returns:
        정제된 입력 문자열
    """
    # 1. 앞뒤 공백 제거
    sanitized = user_input.strip()

    # 2. 연속된 공백을 하나로 축약 (줄바꿈은 유지)
    import re
    sanitized = re.sub(r'[ \t]+', ' ', sanitized)

    # 3. 연속된 줄바꿈을 최대 2개로 제한
    sanitized = re.sub(r'\n{3,}', '\n\n', sanitized)

    return sanitized


def get_claude_cli_path() -> str:
    """
    Claude CLI 실행 파일 경로를 반환합니다.

    우선순위:
    1. 환경변수 CLAUDE_CLI_PATH (명시적 오버라이드)
    2. 자동 탐지 (~/.claude/local/claude)

    Returns:
        Claude CLI 실행 파일 경로

    Raises:
        FileNotFoundError: CLI를 찾을 수 없을 경우
    """
    import os
    import platform
    from dotenv import load_dotenv

    # .env 파일 로드
    load_dotenv()

    # 1. 환경변수 확인
    env_path = os.getenv("CLAUDE_CLI_PATH")
    if env_path:
        cli_path = Path(env_path).expanduser()
        if cli_path.exists():
            return str(cli_path)
        else:
            logging.warning(f"환경변수 CLAUDE_CLI_PATH가 유효하지 않습니다: {env_path}")

    # 2. 자동 탐지
    home_dir = Path.home()
    system = platform.system()

    if system == "Windows":
        default_path = home_dir / ".claude" / "local" / "claude.exe"
    else:  # macOS, Linux
        default_path = home_dir / ".claude" / "local" / "claude"

    if default_path.exists():
        return str(default_path)

    # 찾을 수 없음
    raise FileNotFoundError(
        f"Claude CLI를 찾을 수 없습니다.\n"
        f"다음 중 하나의 방법으로 설정하세요:\n\n"
        f"방법 1 - 환경변수 설정:\n"
        f"  export CLAUDE_CLI_PATH='/path/to/claude'\n\n"
        f"방법 2 - 기본 경로에 설치:\n"
        f"  {default_path}\n\n"
        f"Claude CLI 설치 방법: https://docs.anthropic.com/en/docs/claude-code"
    )


def validate_environment() -> None:
    """
    환경 변수 검증 (ANTHROPIC_API_KEY 또는 CLAUDE_CODE_OAUTH_TOKEN)

    .env 파일이 있으면 자동으로 로드합니다.

    Claude Agent SDK는 두 가지 인증 방식을 지원합니다:
    - ANTHROPIC_API_KEY: API 키 기반 (pay-as-you-go)
    - CLAUDE_CODE_OAUTH_TOKEN: OAuth 토큰 기반 (구독 사용자)

    Raises:
        ValueError: 인증 정보가 설정되지 않은 경우
    """
    import os
    from dotenv import load_dotenv

    # .env 파일 로드 (있을 경우)
    load_dotenv()

    api_key = os.getenv("ANTHROPIC_API_KEY")
    oauth_token = os.getenv("CLAUDE_CODE_OAUTH_TOKEN")

    if not api_key and not oauth_token:
        raise ValueError(
            "인증 정보가 설정되지 않았습니다.\n"
            "다음 중 하나의 방법으로 설정하세요:\n\n"
            "방법 1 - API 키 (pay-as-you-go):\n"
            "  export ANTHROPIC_API_KEY='sk-ant-...'\n\n"
            "방법 2 - OAuth 토큰 (Claude 구독 사용자):\n"
            "  export CLAUDE_CODE_OAUTH_TOKEN='your-oauth-token'\n\n"
            "또는 .env 파일에 추가하세요."
        )
