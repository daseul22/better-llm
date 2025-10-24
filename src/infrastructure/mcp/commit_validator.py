"""
Commit Safety Validator - 커밋 안전성 검증 모듈

Git 커밋 전 민감 정보, 대용량 파일, 병합 충돌 등을 검증하여
안전하지 않은 커밋을 방지합니다.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Any
from abc import ABC, abstractmethod
import re
import asyncio

from src.infrastructure.logging import get_logger

logger = get_logger(__name__, component="CommitValidator")


# 기본 민감 정보 패턴 정의
DEFAULT_SENSITIVE_FILE_PATTERNS = [
    r"\.env.*",                     # .env, .env.local, .env.production 등
    r".*credentials.*",             # credentials.json, aws-credentials 등
    r".*secret.*",                  # secret.txt, secrets.yaml 등
    r".*\.pem$",                    # SSL 인증서
    r".*\.p12$",                    # PKCS#12 인증서
    r".*api[_-]?keys?.*",           # api_key.txt, api-keys.json 등
    r".*\.key$",                    # 개인 키 파일
    r".*private[_-]?key.*",         # private-key.pem 등
]

DEFAULT_SENSITIVE_CONTENT_PATTERNS = [
    r"api[_-]?key\s*[:=]\s*['\"]?[\w-]{20,}",              # API 키
    r"password\s*[:=]\s*['\"][\w@#$%^&*]+['\"]",          # 비밀번호
    r"secret[_-]?key\s*[:=]",                             # Secret 키
    r"aws[_-]?access[_-]?key",                            # AWS Access Key
    # Anthropic API Key 하드코딩 탐지 (sk-ant-로 시작하는 실제 값만)
    r"anthropic[_-]?api[_-]?key\s*[:=]\s*['\"]sk-ant-[\w-]+['\"]",
    # OpenAI API Key 하드코딩 탐지 (sk-로 시작하는 실제 값만)
    r"openai[_-]?api[_-]?key\s*[:=]\s*['\"]sk-[\w-]+['\"]",
    r"private[_-]?key\s*[:=]",                            # Private Key
    r"bearer\s+[a-zA-Z0-9\-._~+/]+=*",                    # Bearer 토큰
    r"token\s*[:=]\s*['\"]?[\w-]{20,}",                   # 일반 토큰
]


@dataclass
class SafetyCheckResult:
    """개별 안전성 검사 결과"""
    passed: bool
    check_name: str
    error_message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


@dataclass
class ValidationResult:
    """전체 검증 결과"""
    is_safe: bool
    error_message: Optional[str] = None
    check_results: List[SafetyCheckResult] = None

    def __post_init__(self):
        if self.check_results is None:
            self.check_results = []


class SafetyChecker(ABC):
    """안전성 검사 추상 클래스 (Strategy Pattern)"""

    @abstractmethod
    async def check(self, changed_files: List[str]) -> SafetyCheckResult:
        """
        안전성 검사 수행

        Args:
            changed_files: 변경된 파일 목록

        Returns:
            SafetyCheckResult: 검사 결과
        """
        pass


class SecretPatternChecker(SafetyChecker):
    """민감 정보 패턴 검사"""

    def __init__(
        self,
        file_patterns: Optional[List[str]] = None,
        content_patterns: Optional[List[str]] = None
    ):
        """
        SecretPatternChecker 초기화

        Args:
            file_patterns: 민감한 파일명 패턴 (정규식)
            content_patterns: 민감한 내용 패턴 (정규식)
        """
        self.file_patterns = file_patterns or DEFAULT_SENSITIVE_FILE_PATTERNS
        self.content_patterns = content_patterns or DEFAULT_SENSITIVE_CONTENT_PATTERNS

    async def check(self, changed_files: List[str]) -> SafetyCheckResult:
        """민감 정보 패턴 검사"""
        # 1단계: 파일명 패턴 검증
        sensitive_files = []
        for file_path in changed_files:
            file_name = Path(file_path).name
            for pattern in self.file_patterns:
                if re.match(pattern, file_name, re.IGNORECASE):
                    sensitive_files.append(file_path)
                    break

        if sensitive_files:
            files_str = "\n  - ".join(sensitive_files)
            return SafetyCheckResult(
                passed=False,
                check_name="SecretPatternChecker",
                error_message=(
                    f"민감한 파일명이 감지되었습니다:\n  - {files_str}\n\n"
                    "이러한 파일은 일반적으로 커밋하지 않아야 합니다. "
                    "정말 커밋하려면 .gitignore에 추가하거나 수동으로 커밋하세요."
                ),
                details={"sensitive_files": sensitive_files}
            )

        # 2단계: 파일 내용 스캔
        sensitive_content = []
        for file_path in changed_files:
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
                        logger.debug(f"바이너리 파일, 스캔 스킵: {file_path}")
                        continue

                # 파일 내용 읽기
                with open(path_obj, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                # 민감 패턴 검색
                for pattern in self.content_patterns:
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

            return SafetyCheckResult(
                passed=False,
                check_name="SecretPatternChecker",
                error_message=(
                    f"민감한 정보가 파일 내용에서 감지되었습니다:\n{findings_str}\n\n"
                    "API 키, 비밀번호, 토큰 등은 커밋하지 않아야 합니다. "
                    "환경 변수나 설정 파일(.env)을 사용하고 .gitignore에 추가하세요."
                ),
                details={"sensitive_content": sensitive_content}
            )

        return SafetyCheckResult(
            passed=True,
            check_name="SecretPatternChecker"
        )


class GitConflictChecker(SafetyChecker):
    """Git 병합 충돌 검사"""

    async def check(self, changed_files: List[str]) -> SafetyCheckResult:
        """병합 충돌 마커 검사"""
        conflict_markers = ["<<<<<<<", "=======", ">>>>>>>"]
        conflicted_files = []

        for file_path in changed_files:
            try:
                path_obj = Path(file_path)
                if not path_obj.exists():
                    continue

                # 텍스트 파일만 검사
                with open(path_obj, "rb") as f:
                    chunk = f.read(8192)
                    if b"\x00" in chunk:
                        continue

                with open(path_obj, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                # 충돌 마커 검색
                for marker in conflict_markers:
                    if marker in content:
                        conflicted_files.append(file_path)
                        break

            except Exception as e:
                logger.warning(f"병합 충돌 검사 중 오류: {file_path} - {e}")
                continue

        if conflicted_files:
            files_str = "\n  - ".join(conflicted_files)
            return SafetyCheckResult(
                passed=False,
                check_name="GitConflictChecker",
                error_message=(
                    f"병합 충돌 마커가 감지되었습니다:\n  - {files_str}\n\n"
                    "충돌을 해결한 후 커밋해주세요."
                ),
                details={"conflicted_files": conflicted_files}
            )

        return SafetyCheckResult(
            passed=True,
            check_name="GitConflictChecker"
        )


class LargeFileChecker(SafetyChecker):
    """대용량 파일 검사"""

    def __init__(self, max_size_mb: int = 50):
        """
        LargeFileChecker 초기화

        Args:
            max_size_mb: 최대 파일 크기 (MB)
        """
        self.max_size_bytes = max_size_mb * 1024 * 1024

    async def check(self, changed_files: List[str]) -> SafetyCheckResult:
        """대용량 파일 검사"""
        large_files = []

        for file_path in changed_files:
            try:
                path_obj = Path(file_path)
                if not path_obj.exists():
                    continue

                file_size = path_obj.stat().st_size
                if file_size > self.max_size_bytes:
                    large_files.append({
                        "file": file_path,
                        "size_mb": round(file_size / (1024 * 1024), 2)
                    })

            except Exception as e:
                logger.warning(f"파일 크기 검사 중 오류: {file_path} - {e}")
                continue

        if large_files:
            files_str = "\n  - ".join([
                f"{item['file']} ({item['size_mb']} MB)"
                for item in large_files
            ])
            return SafetyCheckResult(
                passed=False,
                check_name="LargeFileChecker",
                error_message=(
                    f"대용량 파일이 감지되었습니다:\n  - {files_str}\n\n"
                    "Git LFS를 사용하거나, .gitignore에 추가하는 것을 권장합니다."
                ),
                details={"large_files": large_files}
            )

        return SafetyCheckResult(
            passed=True,
            check_name="LargeFileChecker"
        )


class CommitSafetyValidator:
    """
    커밋 안전성 검증기

    Git 커밋 전 다양한 안전성 검사를 수행합니다:
    - 민감 정보 패턴 검사 (API 키, 비밀번호 등)
    - 병합 충돌 마커 검사
    - 대용량 파일 검사
    - Git 환경 검증

    Example:
        >>> validator = CommitSafetyValidator()
        >>> result = await validator.validate_all()
        >>> if result.is_safe:
        ...     # 커밋 진행
        ... else:
        ...     print(result.error_message)
    """

    def __init__(
        self,
        checkers: Optional[List[SafetyChecker]] = None,
        allowed_paths: Optional[List[str]] = None
    ):
        """
        CommitSafetyValidator 초기화

        Args:
            checkers: 사용할 SafetyChecker 목록 (기본값: 모든 체커)
            allowed_paths: 화이트리스트 경로 (검사 제외)
        """
        self.checkers = checkers or [
            SecretPatternChecker(),
            GitConflictChecker(),
            LargeFileChecker()
        ]
        self.allowed_paths = allowed_paths or []

    async def verify_git_environment(self) -> ValidationResult:
        """
        Git 설치 및 저장소 확인

        Returns:
            ValidationResult: Git 환경 검증 결과
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
                return ValidationResult(
                    is_safe=False,
                    error_message="Git이 설치되어 있지 않습니다."
                )

            # Git 저장소인지 확인
            proc = await asyncio.create_subprocess_shell(
                "git rev-parse --is-inside-work-tree",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                return ValidationResult(
                    is_safe=False,
                    error_message="현재 디렉토리가 Git 저장소가 아닙니다."
                )

            return ValidationResult(is_safe=True)

        except Exception as e:
            logger.error(f"Git 환경 검증 실패: {e}")
            return ValidationResult(
                is_safe=False,
                error_message=f"Git 환경 검증 중 오류 발생: {str(e)}"
            )

    async def get_changed_files(self) -> tuple[bool, List[str], Optional[str]]:
        """
        변경된 파일 목록 가져오기

        Returns:
            tuple[bool, List[str], Optional[str]]:
                (성공 여부, 파일 목록, 에러 메시지)
        """
        try:
            proc = await asyncio.create_subprocess_shell(
                "git status --porcelain",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                return False, [], f"Git status 실행 실패: {stderr.decode('utf-8', errors='ignore')}"

            status_output = stdout.decode("utf-8", errors="ignore")
            changed_files = []

            for line in status_output.splitlines():
                if len(line) < 4:
                    continue
                file_path = line[3:].strip()
                # -> 로 리네임된 경우 처리
                if " -> " in file_path:
                    file_path = file_path.split(" -> ")[1]
                changed_files.append(file_path)

            if not changed_files:
                return False, [], "커밋할 변경 사항이 없습니다."

            # 화이트리스트 필터링
            filtered_files = [
                f for f in changed_files
                if not any(f.startswith(allowed) for allowed in self.allowed_paths)
            ]

            return True, filtered_files, None

        except Exception as e:
            logger.error(f"변경된 파일 조회 실패: {e}")
            return False, [], f"변경된 파일 조회 중 오류: {str(e)}"

    async def validate_all(self) -> ValidationResult:
        """
        전체 안전성 검증 수행

        Returns:
            ValidationResult: 종합 검증 결과
        """
        # 1단계: Git 환경 검증
        git_result = await self.verify_git_environment()
        if not git_result.is_safe:
            return git_result

        # 2단계: 변경된 파일 조회
        success, changed_files, error_msg = await self.get_changed_files()
        if not success:
            return ValidationResult(
                is_safe=False,
                error_message=error_msg
            )

        # 3단계: 모든 체커 실행
        check_results = []
        for checker in self.checkers:
            try:
                result = await checker.check(changed_files)
                check_results.append(result)

                if not result.passed:
                    # 하나라도 실패하면 즉시 반환
                    return ValidationResult(
                        is_safe=False,
                        error_message=result.error_message,
                        check_results=check_results
                    )

            except Exception as e:
                logger.error(f"Safety checker failed: {checker.__class__.__name__} - {e}")
                # 체커 실패는 경고만 로그 (False Positive 방지)
                continue

        # 모든 검증 통과
        return ValidationResult(
            is_safe=True,
            check_results=check_results
        )

    def add_checker(self, checker: SafetyChecker) -> None:
        """SafetyChecker 추가"""
        self.checkers.append(checker)
        logger.info(f"Added checker: {checker.__class__.__name__}")

    def update_allowed_paths(self, paths: List[str]) -> None:
        """화이트리스트 경로 업데이트"""
        self.allowed_paths = paths
        logger.info(f"Updated allowed paths: {paths}")
