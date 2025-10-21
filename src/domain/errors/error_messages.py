"""에러 메시지 템플릿

각 에러 코드에 대한 사용자 친화적인 메시지를 제공합니다.
"""

from typing import Dict, Any
from .error_codes import ErrorCode


# 에러 코드별 메시지 템플릿
ERROR_MESSAGES: Dict[ErrorCode, str] = {
    # Worker 관련
    ErrorCode.WORKER_TIMEOUT: (
        "Worker '{worker_name}'의 실행 시간이 {timeout}초를 초과했습니다. "
        "타임아웃 설정을 늘리거나 작업을 간소화하세요."
    ),
    ErrorCode.WORKER_EXECUTION_FAILED: (
        "Worker '{worker_name}'의 실행 중 오류가 발생했습니다: {error}"
    ),
    ErrorCode.WORKER_NOT_FOUND: (
        "Worker '{worker_name}'을 찾을 수 없습니다. "
        "config/agent_config.json에 정의되어 있는지 확인하세요."
    ),
    ErrorCode.WORKER_INITIALIZATION_FAILED: (
        "Worker '{worker_name}' 초기화에 실패했습니다: {error}"
    ),
    ErrorCode.WORKER_TOOL_NOT_AVAILABLE: (
        "Worker '{worker_name}'에서 필요한 Tool '{tool_name}'을 사용할 수 없습니다."
    ),
    ErrorCode.WORKER_RETRY_EXCEEDED: (
        "Worker '{worker_name}'의 재시도 횟수({max_retries}회)를 초과했습니다."
    ),
    ErrorCode.WORKER_INVALID_INPUT: (
        "Worker '{worker_name}'에 전달된 입력이 유효하지 않습니다: {error}"
    ),
    ErrorCode.WORKER_OUTPUT_PARSING_FAILED: (
        "Worker '{worker_name}'의 출력을 파싱하는 데 실패했습니다: {error}"
    ),
    # Config 관련
    ErrorCode.CONFIG_LOAD_FAILED: (
        "설정 파일 '{file_path}'를 로드하는 데 실패했습니다: {error}"
    ),
    ErrorCode.CONFIG_INVALID: (
        "설정 파일 '{file_path}'의 형식이 올바르지 않습니다: {error}"
    ),
    ErrorCode.CONFIG_MISSING_REQUIRED_FIELD: (
        "설정 파일에 필수 항목 '{field_name}'이 누락되었습니다."
    ),
    ErrorCode.CONFIG_VALIDATION_FAILED: (
        "설정 검증에 실패했습니다: {error}"
    ),
    ErrorCode.CONFIG_FILE_NOT_FOUND: (
        "설정 파일 '{file_path}'을 찾을 수 없습니다."
    ),
    ErrorCode.PROMPT_FILE_NOT_FOUND: (
        "프롬프트 파일 '{file_path}'을 찾을 수 없습니다."
    ),
    ErrorCode.PROMPT_LOAD_FAILED: (
        "프롬프트 파일 '{file_path}' 로드에 실패했습니다: {error}"
    ),
    # Session 관련
    ErrorCode.SESSION_NOT_FOUND: (
        "세션 '{session_id}'를 찾을 수 없습니다."
    ),
    ErrorCode.SESSION_SAVE_FAILED: (
        "세션 '{session_id}' 저장에 실패했습니다: {error}"
    ),
    ErrorCode.SESSION_LOAD_FAILED: (
        "세션 '{session_id}' 로드에 실패했습니다: {error}"
    ),
    ErrorCode.SESSION_INVALID_STATE: (
        "세션 '{session_id}'의 상태가 유효하지 않습니다: {state}"
    ),
    ErrorCode.SESSION_EXCEEDED_MAX_TURNS: (
        "세션 '{session_id}'의 턴 수가 최대값({max_turns})을 초과했습니다."
    ),
    ErrorCode.SESSION_COMPRESSION_FAILED: (
        "세션 '{session_id}' 압축에 실패했습니다: {error}"
    ),
    ErrorCode.SESSION_DECOMPRESSION_FAILED: (
        "세션 '{session_id}' 압축 해제에 실패했습니다: {error}"
    ),
    # API 관련
    ErrorCode.API_KEY_MISSING: (
        "CLAUDE_CODE_OAUTH_TOKEN 환경변수가 설정되지 않았습니다. "
        "OAuth 토큰을 설정한 후 다시 시도하세요."
    ),
    ErrorCode.API_KEY_INVALID: (
        "유효하지 않은 OAuth 토큰입니다. CLAUDE_CODE_OAUTH_TOKEN을 확인하세요."
    ),
    ErrorCode.API_RATE_LIMIT_EXCEEDED: (
        "API 호출 한도를 초과했습니다. {retry_after}초 후 다시 시도하세요."
    ),
    ErrorCode.API_REQUEST_FAILED: (
        "API 요청에 실패했습니다: {error}"
    ),
    ErrorCode.API_RESPONSE_INVALID: (
        "API 응답이 유효하지 않습니다: {error}"
    ),
    ErrorCode.API_TIMEOUT: (
        "API 응답 시간이 {timeout}초를 초과했습니다."
    ),
    ErrorCode.API_NETWORK_ERROR: (
        "네트워크 연결 오류가 발생했습니다: {error}"
    ),
    ErrorCode.API_SERVER_ERROR: (
        "API 서버 에러가 발생했습니다 (HTTP {status_code}): {error}"
    ),
    # Storage 관련
    ErrorCode.STORAGE_WRITE_FAILED: (
        "파일 '{file_path}' 쓰기에 실패했습니다: {error}"
    ),
    ErrorCode.STORAGE_READ_FAILED: (
        "파일 '{file_path}' 읽기에 실패했습니다: {error}"
    ),
    ErrorCode.STORAGE_DELETE_FAILED: (
        "파일 '{file_path}' 삭제에 실패했습니다: {error}"
    ),
    ErrorCode.STORAGE_PERMISSION_DENIED: (
        "파일 '{file_path}'에 접근 권한이 없습니다."
    ),
    ErrorCode.STORAGE_DISK_FULL: (
        "디스크 공간이 부족합니다. 여유 공간을 확보한 후 다시 시도하세요."
    ),
    ErrorCode.STORAGE_INVALID_PATH: (
        "유효하지 않은 파일 경로입니다: {file_path}"
    ),
    # Metrics 관련
    ErrorCode.METRICS_COLLECTION_FAILED: (
        "메트릭 수집에 실패했습니다: {error}"
    ),
    ErrorCode.METRICS_QUEUE_FULL: (
        "메트릭 큐가 가득 찼습니다. 일부 메트릭이 손실될 수 있습니다."
    ),
    ErrorCode.METRICS_FLUSH_FAILED: (
        "메트릭 플러시에 실패했습니다: {error}"
    ),
    ErrorCode.METRICS_INVALID_VALUE: (
        "유효하지 않은 메트릭 값입니다: {value}"
    ),
    # Logging 관련
    ErrorCode.LOGGING_SETUP_FAILED: (
        "로깅 설정에 실패했습니다: {error}"
    ),
    ErrorCode.LOGGING_FILE_WRITE_FAILED: (
        "로그 파일 '{file_path}' 쓰기에 실패했습니다: {error}"
    ),
    ErrorCode.LOGGING_ROTATION_FAILED: (
        "로그 로테이션에 실패했습니다: {error}"
    ),
    # Cache 관련
    ErrorCode.CACHE_SET_FAILED: (
        "캐시 저장에 실패했습니다 (key: '{key}'): {error}"
    ),
    ErrorCode.CACHE_GET_FAILED: (
        "캐시 조회에 실패했습니다 (key: '{key}'): {error}"
    ),
    ErrorCode.CACHE_INVALIDATION_FAILED: (
        "캐시 무효화에 실패했습니다: {error}"
    ),
    ErrorCode.CACHE_SERIALIZATION_FAILED: (
        "캐시 직렬화에 실패했습니다: {error}"
    ),
    # 기타
    ErrorCode.UNKNOWN_ERROR: (
        "알 수 없는 오류가 발생했습니다: {error}"
    ),
    ErrorCode.INVALID_ARGUMENT: (
        "유효하지 않은 인자입니다: {argument}"
    ),
    ErrorCode.OPERATION_NOT_SUPPORTED: (
        "지원하지 않는 작업입니다: {operation}"
    ),
    ErrorCode.RESOURCE_NOT_FOUND: (
        "리소스 '{resource}'를 찾을 수 없습니다."
    ),
    ErrorCode.PERMISSION_DENIED: (
        "권한이 없습니다: {operation}"
    ),
    ErrorCode.TIMEOUT: (
        "작업 시간이 {timeout}초를 초과했습니다."
    ),
    ErrorCode.CANCELLED: (
        "작업이 취소되었습니다."
    ),
}


def get_error_message(error_code: ErrorCode) -> str:
    """에러 코드에 해당하는 메시지 템플릿 반환

    Args:
        error_code: 에러 코드

    Returns:
        에러 메시지 템플릿

    Examples:
        >>> get_error_message(ErrorCode.WORKER_TIMEOUT)
        "Worker '{worker_name}'의 실행 시간이 {timeout}초를 초과했습니다..."
    """
    return ERROR_MESSAGES.get(
        error_code,
        "알 수 없는 에러 코드입니다: {error_code}"
    )


def format_error_message(error_code: ErrorCode, **context: Any) -> str:
    """에러 메시지를 컨텍스트 정보로 포맷팅

    Args:
        error_code: 에러 코드
        **context: 메시지 템플릿에 삽입할 컨텍스트 정보

    Returns:
        포맷팅된 에러 메시지

    Examples:
        >>> format_error_message(
        ...     ErrorCode.WORKER_TIMEOUT,
        ...     worker_name="planner",
        ...     timeout=300
        ... )
        "Worker 'planner'의 실행 시간이 300초를 초과했습니다..."
    """
    template = get_error_message(error_code)

    # 컨텍스트에 error_code도 추가 (템플릿에서 사용 가능)
    context["error_code"] = error_code

    try:
        return template.format(**context)
    except KeyError as e:
        # 템플릿에 필요한 변수가 context에 없는 경우
        return (
            f"{template} [포맷 오류: 필수 변수 '{e.args[0]}'가 누락되었습니다. "
            f"제공된 변수: {list(context.keys())}]"
        )
