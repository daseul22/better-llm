"""
자동 완성 엔진 모듈

슬래시 커맨드 및 파일 경로 자동 완성 기능 제공
"""

import os
from pathlib import Path
from typing import List, Optional, Tuple


class FilePathCompleter:
    """
    파일 경로 자동 완성 클래스

    현재 디렉토리 기준으로 파일 및 디렉토리 경로를 자동 완성합니다.
    """

    @staticmethod
    def get_completions(partial_path: str, working_dir: Optional[Path] = None) -> List[str]:
        """
        부분 경로에 대한 자동 완성 후보 반환

        Args:
            partial_path: 부분 입력 경로 문자열
            working_dir: 작업 디렉토리 (None이면 현재 디렉토리)

        Returns:
            자동 완성 후보 리스트 (정렬됨: 디렉토리 우선)
        """
        if not partial_path:
            return []

        try:
            # 작업 디렉토리 설정
            base_dir = working_dir or Path.cwd()

            # 경로 분리 (디렉토리 부분과 파일명 부분)
            path_obj = Path(partial_path)
            if partial_path.endswith(os.sep):
                # 경로가 '/'로 끝나면 해당 디렉토리 내 모든 항목 검색
                search_dir = base_dir / path_obj
                prefix = ""
            else:
                # 마지막 부분을 파일명으로 간주
                search_dir = base_dir / path_obj.parent
                prefix = path_obj.name

            # 디렉토리가 존재하지 않으면 빈 리스트 반환
            if not search_dir.exists() or not search_dir.is_dir():
                return []

            # 매칭되는 항목 찾기
            matches = []
            for item in search_dir.iterdir():
                if item.name.startswith(prefix):
                    # 상대 경로로 변환
                    rel_path = item.relative_to(base_dir)
                    path_str = str(rel_path)

                    # 디렉토리면 '/' 추가
                    if item.is_dir():
                        path_str += os.sep
                        matches.append((path_str, True))  # (경로, 디렉토리 여부)
                    else:
                        matches.append((path_str, False))

            # 정렬: 디렉토리 우선, 그 다음 알파벳 순
            matches.sort(key=lambda x: (not x[1], x[0].lower()))

            return [m[0] for m in matches]

        except (OSError, ValueError) as e:
            # 경로 접근 오류 시 빈 리스트 반환
            return []

    @staticmethod
    def needs_quotes(path: str) -> bool:
        """
        공백이 포함된 경로인지 확인

        Args:
            path: 경로 문자열

        Returns:
            따옴표가 필요한지 여부
        """
        return " " in path


class CommandCompleter:
    """
    슬래시 커맨드 자동 완성 클래스
    """

    # 사용 가능한 슬래시 커맨드 목록
    SLASH_COMMANDS = [
        "/help",
        "/init",
        "/load",
        "/clear",
        "/metrics",
        "/search",
    ]

    @staticmethod
    def get_completions(partial_command: str) -> List[str]:
        """
        부분 입력에 대한 자동 완성 후보 반환

        Args:
            partial_command: 부분 입력 커맨드 문자열

        Returns:
            자동 완성 후보 리스트
        """
        if not partial_command or not partial_command.startswith("/"):
            return []

        # 부분 입력과 일치하는 커맨드 찾기
        matches = [
            cmd for cmd in CommandCompleter.SLASH_COMMANDS
            if cmd.startswith(partial_command.lower())
        ]

        return sorted(matches)


class AutocompleteEngine:
    """
    통합 자동 완성 엔진

    슬래시 커맨드와 파일 경로를 자동 완성하며, Tab 키로 여러 후보를 순환합니다.

    Features:
        - 슬래시 커맨드 자동 완성 (입력이 '/'로 시작)
        - 파일 경로 자동 완성 (입력에 '/' 또는 './' 포함)
        - Tab 키 반복으로 후보 순환
        - 공백 있는 경로 자동 따옴표 처리
    """

    def __init__(self, working_dir: Optional[Path] = None):
        """
        AutocompleteEngine 초기화

        Args:
            working_dir: 작업 디렉토리 (None이면 현재 디렉토리)
        """
        self.working_dir = working_dir or Path.cwd()
        self.current_candidates: List[str] = []
        self.current_index: int = -1
        self.last_input: str = ""

    def get_completions(self, input_text: str) -> List[str]:
        """
        입력 텍스트에 대한 자동 완성 후보 반환

        Args:
            input_text: 입력 텍스트

        Returns:
            자동 완성 후보 리스트
        """
        if not input_text:
            return []

        # 슬래시 커맨드 자동 완성
        if input_text.startswith("/") and " " not in input_text:
            return CommandCompleter.get_completions(input_text)

        # 파일 경로 자동 완성 (/, ./, ../ 포함 시)
        if "/" in input_text or input_text.startswith("."):
            # 마지막 단어 추출 (공백으로 분리된 경우)
            words = input_text.split()
            if words:
                last_word = words[-1]
                # 경로로 보이는 경우에만 자동 완성
                if "/" in last_word or last_word.startswith("."):
                    return FilePathCompleter.get_completions(last_word, self.working_dir)

        return []

    def complete(self, input_text: str, cycle: bool = False) -> Optional[str]:
        """
        입력 텍스트를 자동 완성

        Args:
            input_text: 입력 텍스트
            cycle: True면 후보 순환, False면 첫 번째 후보 반환

        Returns:
            자동 완성된 텍스트, 후보가 없으면 None
        """
        # 입력이 변경되면 후보 목록 갱신
        if input_text != self.last_input:
            self.current_candidates = self.get_completions(input_text)
            self.current_index = -1
            self.last_input = input_text

        if not self.current_candidates:
            return None

        # 순환 모드
        if cycle:
            self.current_index = (self.current_index + 1) % len(self.current_candidates)
            candidate = self.current_candidates[self.current_index]
        else:
            # 첫 번째 후보 반환
            candidate = self.current_candidates[0]

        # 자동 완성 결과 생성
        return self._apply_completion(input_text, candidate)

    def _apply_completion(self, input_text: str, candidate: str) -> str:
        """
        자동 완성을 입력 텍스트에 적용

        Args:
            input_text: 원본 입력 텍스트
            candidate: 자동 완성 후보

        Returns:
            자동 완성된 텍스트
        """
        # 슬래시 커맨드인 경우
        if input_text.startswith("/") and " " not in input_text:
            return candidate

        # 파일 경로인 경우
        if "/" in input_text or input_text.startswith("."):
            words = input_text.split()
            if words:
                # 마지막 단어를 후보로 교체
                words[-1] = candidate

                # 공백 있는 경로는 따옴표로 감싸기
                if FilePathCompleter.needs_quotes(candidate):
                    words[-1] = f'"{candidate}"'

                return " ".join(words)

        return input_text

    def get_preview(self) -> str:
        """
        현재 자동 완성 후보 미리보기 텍스트 반환

        Returns:
            미리보기 텍스트 (예: "1/3: /help")
        """
        if not self.current_candidates:
            return ""

        if self.current_index == -1:
            return f"Tab: {len(self.current_candidates)}개 후보"

        current = self.current_index + 1
        total = len(self.current_candidates)
        candidate = self.current_candidates[self.current_index]

        return f"{current}/{total}: {candidate}"

    def reset(self) -> None:
        """자동 완성 상태 초기화"""
        self.current_candidates = []
        self.current_index = -1
        self.last_input = ""

    @staticmethod
    def _get_common_prefix(strings: List[str]) -> str:
        """
        문자열 리스트의 공통 접두사 찾기

        Args:
            strings: 문자열 리스트

        Returns:
            공통 접두사
        """
        if not strings:
            return ""

        # 첫 번째 문자열을 기준으로 비교
        prefix = strings[0]

        for s in strings[1:]:
            # 공통 접두사 길이 찾기
            i = 0
            while i < len(prefix) and i < len(s) and prefix[i] == s[i]:
                i += 1
            prefix = prefix[:i]

            if not prefix:
                break

        return prefix
