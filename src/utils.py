"""
유틸리티 함수

설정 로드, 세션 관리, 로깅 등의 헬퍼 함수들
"""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

from .models import AgentConfig


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


def validate_environment() -> None:
    """
    환경 변수 검증 (ANTHROPIC_API_KEY)

    .env 파일이 있으면 자동으로 로드합니다.

    Raises:
        ValueError: API 키가 설정되지 않은 경우
    """
    import os
    from dotenv import load_dotenv

    # .env 파일 로드 (있을 경우)
    load_dotenv()

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다.\n"
            "다음 명령으로 설정하세요:\n"
            "  export ANTHROPIC_API_KEY='your-api-key'\n"
            "또는 .env 파일에 추가하세요."
        )
