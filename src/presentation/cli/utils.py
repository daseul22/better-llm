"""
CLI Presentation Utilities

Helper functions for CLI interface (logging, session management, validation)
"""

import json
import logging
import uuid
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple


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
        파일명 (예: session_abc123_20250118_143022_결제시스템구현.json)
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
    history,  # ConversationHistory object
    result: dict,
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


def print_footer(
    session_id: str,
    total_turns: int,
    duration: float,
    files_modified: int,
    filepath: Path
) -> None:
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


def validate_user_input(user_input: str, max_length: int = 5000) -> Tuple[bool, Optional[str]]:
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
        return False, "입력에 허용되지 않는 제어 문자가 포함되어 있습니다."

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
    sanitized = re.sub(r'[ \t]+', ' ', sanitized)

    # 3. 연속된 줄바꿈을 최대 2개로 제한
    sanitized = re.sub(r'\n{3,}', '\n\n', sanitized)

    return sanitized


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
        "reviewer": "🔍",
        "tester": "🧪",
        "user": "👤",
        "manager": "👔"
    }
    return emoji_map.get(agent_name, "🤖")


def load_system_config(config_path: Optional[Path] = None):
    """
    시스템 설정 로드 (하위호환성 함수)

    Args:
        config_path: 설정 파일 경로

    Returns:
        SystemConfig 객체
    """
    from ...infrastructure.config import JsonConfigLoader, get_project_root

    project_root = get_project_root()
    loader = JsonConfigLoader(project_root)
    return loader.load_system_config()


def save_metrics_report(
    session_id: str,
    metrics_collector,  # MetricsCollector object
    output_dir: Path,
    format: str = "text"
) -> Optional[Path]:
    """
    세션 메트릭 리포트를 파일로 저장

    Args:
        session_id: 세션 ID
        metrics_collector: 메트릭 수집기 (MetricsCollector 객체)
        output_dir: 출력 디렉토리
        format: 리포트 형식 ("text", "json", "markdown")

    Returns:
        저장된 파일 경로 또는 None (메트릭이 없는 경우)
    """
    from ...domain.services import MetricsReporter

    # 세션 메트릭 조회
    session_metrics = metrics_collector.get_session_summary(session_id)

    if not session_metrics or not session_metrics.workers_metrics:
        # 메트릭이 없으면 저장하지 않음
        return None

    # 리포트 저장
    filepath = MetricsReporter.save_report(
        session_metrics=session_metrics,
        output_path=output_dir,
        format=format
    )

    return filepath
