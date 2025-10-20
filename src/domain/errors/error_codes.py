"""에러 코드 정의

Better-LLM의 모든 에러를 카테고리별로 분류하여 관리합니다.
"""

from enum import Enum


class ErrorCode(Enum):
    """Better-LLM 에러 코드

    에러 코드는 4자리 숫자로 구성되며, 앞 두 자리는 카테고리를 나타냅니다.

    Categories:
        10xx: Worker 관련 에러
        20xx: Config 관련 에러
        30xx: Session 관련 에러
        40xx: API 관련 에러
        50xx: Storage 관련 에러
        60xx: Metrics 관련 에러
        70xx: Logging 관련 에러
        80xx: Cache 관련 에러
        90xx: 기타 에러
    """

    # ==================== Worker 관련 (1000-1999) ====================
    WORKER_TIMEOUT = 1001
    """Worker 실행 타임아웃"""

    WORKER_EXECUTION_FAILED = 1002
    """Worker 실행 실패"""

    WORKER_NOT_FOUND = 1003
    """존재하지 않는 Worker"""

    WORKER_INITIALIZATION_FAILED = 1004
    """Worker 초기화 실패"""

    WORKER_TOOL_NOT_AVAILABLE = 1005
    """Worker Tool이 사용 불가능"""

    WORKER_RETRY_EXCEEDED = 1006
    """Worker 재시도 횟수 초과"""

    WORKER_INVALID_INPUT = 1007
    """Worker 입력 파라미터 오류"""

    WORKER_OUTPUT_PARSING_FAILED = 1008
    """Worker 출력 파싱 실패"""

    # ==================== Config 관련 (2000-2999) ====================
    CONFIG_LOAD_FAILED = 2001
    """설정 파일 로드 실패"""

    CONFIG_INVALID = 2002
    """설정 파일 형식 오류"""

    CONFIG_MISSING_REQUIRED_FIELD = 2003
    """필수 설정 항목 누락"""

    CONFIG_VALIDATION_FAILED = 2004
    """설정 검증 실패"""

    CONFIG_FILE_NOT_FOUND = 2005
    """설정 파일을 찾을 수 없음"""

    PROMPT_FILE_NOT_FOUND = 2101
    """프롬프트 파일을 찾을 수 없음"""

    PROMPT_LOAD_FAILED = 2102
    """프롬프트 파일 로드 실패"""

    # ==================== Session 관련 (3000-3999) ====================
    SESSION_NOT_FOUND = 3001
    """세션을 찾을 수 없음"""

    SESSION_SAVE_FAILED = 3002
    """세션 저장 실패"""

    SESSION_LOAD_FAILED = 3003
    """세션 로드 실패"""

    SESSION_INVALID_STATE = 3004
    """잘못된 세션 상태"""

    SESSION_EXCEEDED_MAX_TURNS = 3005
    """최대 턴 수 초과"""

    SESSION_COMPRESSION_FAILED = 3006
    """세션 압축 실패"""

    SESSION_DECOMPRESSION_FAILED = 3007
    """세션 압축 해제 실패"""

    # ==================== API 관련 (4000-4999) ====================
    API_KEY_MISSING = 4001
    """API 키가 설정되지 않음"""

    API_KEY_INVALID = 4002
    """유효하지 않은 API 키"""

    API_RATE_LIMIT_EXCEEDED = 4003
    """API 호출 한도 초과"""

    API_REQUEST_FAILED = 4004
    """API 요청 실패"""

    API_RESPONSE_INVALID = 4005
    """유효하지 않은 API 응답"""

    API_TIMEOUT = 4006
    """API 응답 타임아웃"""

    API_NETWORK_ERROR = 4007
    """네트워크 연결 오류"""

    API_SERVER_ERROR = 4008
    """API 서버 에러 (5xx)"""

    # ==================== Storage 관련 (5000-5999) ====================
    STORAGE_WRITE_FAILED = 5001
    """저장소 쓰기 실패"""

    STORAGE_READ_FAILED = 5002
    """저장소 읽기 실패"""

    STORAGE_DELETE_FAILED = 5003
    """저장소 삭제 실패"""

    STORAGE_PERMISSION_DENIED = 5004
    """저장소 접근 권한 없음"""

    STORAGE_DISK_FULL = 5005
    """디스크 공간 부족"""

    STORAGE_INVALID_PATH = 5006
    """유효하지 않은 저장소 경로"""

    # ==================== Metrics 관련 (6000-6999) ====================
    METRICS_COLLECTION_FAILED = 6001
    """메트릭 수집 실패"""

    METRICS_QUEUE_FULL = 6002
    """메트릭 큐가 가득 찼음"""

    METRICS_FLUSH_FAILED = 6003
    """메트릭 플러시 실패"""

    METRICS_INVALID_VALUE = 6004
    """유효하지 않은 메트릭 값"""

    # ==================== Logging 관련 (7000-7999) ====================
    LOGGING_SETUP_FAILED = 7001
    """로깅 설정 실패"""

    LOGGING_FILE_WRITE_FAILED = 7002
    """로그 파일 쓰기 실패"""

    LOGGING_ROTATION_FAILED = 7003
    """로그 로테이션 실패"""

    # ==================== Cache 관련 (8000-8999) ====================
    CACHE_SET_FAILED = 8001
    """캐시 저장 실패"""

    CACHE_GET_FAILED = 8002
    """캐시 조회 실패"""

    CACHE_INVALIDATION_FAILED = 8003
    """캐시 무효화 실패"""

    CACHE_SERIALIZATION_FAILED = 8004
    """캐시 직렬화 실패"""

    # ==================== 기타 (9000-9999) ====================
    UNKNOWN_ERROR = 9001
    """알 수 없는 에러"""

    INVALID_ARGUMENT = 9002
    """유효하지 않은 인자"""

    OPERATION_NOT_SUPPORTED = 9003
    """지원하지 않는 작업"""

    RESOURCE_NOT_FOUND = 9004
    """리소스를 찾을 수 없음"""

    PERMISSION_DENIED = 9005
    """권한 없음"""

    TIMEOUT = 9006
    """작업 타임아웃"""

    CANCELLED = 9007
    """작업이 취소됨"""

    def __str__(self) -> str:
        """에러 코드를 문자열로 반환 (예: 'WORKER_TIMEOUT (1001)')"""
        return f"{self.name} ({self.value})"

    @property
    def code(self) -> int:
        """에러 코드 숫자 반환"""
        return self.value

    @property
    def category(self) -> str:
        """에러 카테고리 반환"""
        code = self.value
        if 1000 <= code < 2000:
            return "Worker"
        elif 2000 <= code < 3000:
            return "Config"
        elif 3000 <= code < 4000:
            return "Session"
        elif 4000 <= code < 5000:
            return "API"
        elif 5000 <= code < 6000:
            return "Storage"
        elif 6000 <= code < 7000:
            return "Metrics"
        elif 7000 <= code < 8000:
            return "Logging"
        elif 8000 <= code < 9000:
            return "Cache"
        else:
            return "Other"
