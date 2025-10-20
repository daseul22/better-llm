"""
InputHandler 모듈

사용자 입력 처리 책임:
- 사용자 입력 처리
- 명령 라우팅
- 명령 히스토리 관리
"""

from typing import Callable, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
from collections import deque

from infrastructure.logging import get_logger

logger = get_logger(__name__, component="InputHandler")


class CommandStatus(str, Enum):
    """명령 실행 상태"""
    SUCCESS = "success"
    ERROR = "error"
    NOT_FOUND = "not_found"
    INVALID_ARGS = "invalid_args"


@dataclass
class CommandResult:
    """
    명령 실행 결과

    Attributes:
        status: 실행 상태
        output: 출력 메시지
        error: 에러 메시지 (옵셔널)
    """
    status: CommandStatus
    output: str
    error: Optional[str] = None

    def __str__(self) -> str:
        if self.error:
            return f"[{self.status.value}] {self.output}: {self.error}"
        return f"[{self.status.value}] {self.output}"


class InputHandler:
    """
    사용자 입력 처리기

    사용자 입력을 파싱하고 등록된 명령 핸들러로 라우팅합니다.

    Example:
        >>> handler = InputHandler()
        >>> def hello_handler(args):
        ...     return CommandResult(
        ...         status=CommandStatus.SUCCESS,
        ...         output=f"Hello {args[0] if args else 'World'}!"
        ...     )
        >>> handler.register_command("hello", hello_handler)
        >>> result = handler.handle_input("hello Claude")
        >>> print(result.output)
        Hello Claude!
    """

    def __init__(self, max_history_size: int = 100) -> None:
        """
        InputHandler 초기화

        Args:
            max_history_size: 최대 명령 히스토리 크기 (기본값: 100)
        """
        self._command_handlers: Dict[str, Callable] = {}
        self._command_history: deque[str] = deque(maxlen=max_history_size)
        self._max_history_size = max_history_size
        self._command_aliases: Dict[str, str] = {}
        self._command_descriptions: Dict[str, str] = {}
        logger.info(f"InputHandler initialized (max_history: {max_history_size})")

    def handle_input(self, input_str: str) -> CommandResult:
        """
        사용자 입력을 처리합니다.

        Args:
            input_str: 사용자 입력 문자열

        Returns:
            명령 실행 결과

        Example:
            >>> handler = InputHandler()
            >>> def echo_handler(args):
            ...     return CommandResult(
            ...         status=CommandStatus.SUCCESS,
            ...         output=" ".join(args)
            ...     )
            >>> handler.register_command("echo", echo_handler)
            >>> result = handler.handle_input("echo hello world")
            >>> print(result.output)
            hello world
        """
        # 빈 입력 처리
        if not input_str or not input_str.strip():
            return CommandResult(
                status=CommandStatus.INVALID_ARGS,
                output="Empty input",
                error="No command provided"
            )

        # 히스토리에 추가
        self._command_history.append(input_str)

        # 입력 파싱
        parts = input_str.strip().split()
        command = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []

        # 별칭 처리
        if command in self._command_aliases:
            command = self._command_aliases[command]

        # 명령 핸들러 조회
        if command not in self._command_handlers:
            logger.warning(f"Command not found: {command}")
            return CommandResult(
                status=CommandStatus.NOT_FOUND,
                output=f"Command '{command}' not found",
                error=f"Use 'help' to see available commands"
            )

        # 명령 실행
        try:
            handler = self._command_handlers[command]
            result = handler(args)
            logger.debug(f"Command executed: {command} (status: {result.status})")
            return result
        except Exception as e:
            logger.error(f"Error executing command '{command}': {e}", exc_info=True)
            return CommandResult(
                status=CommandStatus.ERROR,
                output=f"Error executing command '{command}'",
                error=str(e)
            )

    def register_command(
        self,
        command: str,
        handler: Callable[[List[str]], CommandResult],
        description: str = ""
    ) -> None:
        """
        명령 핸들러를 등록합니다.

        Args:
            command: 명령 이름
            handler: 명령 핸들러 함수 (args를 받아 CommandResult를 반환)
            description: 명령 설명 (옵셔널)

        Example:
            >>> handler = InputHandler()
            >>> def quit_handler(args):
            ...     return CommandResult(
            ...         status=CommandStatus.SUCCESS,
            ...         output="Goodbye!"
            ...     )
            >>> handler.register_command("quit", quit_handler, "Exit the application")
        """
        command_lower = command.lower()
        self._command_handlers[command_lower] = handler

        if description:
            self._command_descriptions[command_lower] = description

        logger.info(f"Command registered: {command_lower}")

    def unregister_command(self, command: str) -> None:
        """
        명령 핸들러를 제거합니다.

        Args:
            command: 명령 이름

        Raises:
            KeyError: 존재하지 않는 명령

        Example:
            >>> handler = InputHandler()
            >>> def test_handler(args):
            ...     return CommandResult(CommandStatus.SUCCESS, "Test")
            >>> handler.register_command("test", test_handler)
            >>> handler.unregister_command("test")
        """
        command_lower = command.lower()

        if command_lower not in self._command_handlers:
            logger.error(f"Command not found: {command_lower}")
            raise KeyError(f"Command '{command_lower}' not found")

        del self._command_handlers[command_lower]

        if command_lower in self._command_descriptions:
            del self._command_descriptions[command_lower]

        logger.info(f"Command unregistered: {command_lower}")

    def get_command_history(self, limit: int = 100) -> List[str]:
        """
        명령 히스토리를 조회합니다.

        Args:
            limit: 최대 반환 개수 (기본값: 100)

        Returns:
            명령 히스토리 리스트 (최신순)

        Example:
            >>> handler = InputHandler()
            >>> handler.handle_input("command1")
            >>> handler.handle_input("command2")
            >>> history = handler.get_command_history()
            >>> print(len(history))
            2
        """
        history = list(self._command_history)
        # 최신 순으로 반환
        history.reverse()
        result = history[:limit]

        logger.debug(f"Retrieved command history ({len(result)} entries)")

        return result

    def clear_command_history(self) -> None:
        """
        명령 히스토리를 삭제합니다.

        Example:
            >>> handler = InputHandler()
            >>> handler.handle_input("test")
            >>> handler.clear_command_history()
            >>> history = handler.get_command_history()
            >>> print(len(history))
            0
        """
        self._command_history.clear()
        logger.info("Command history cleared")

    def list_commands(self) -> List[str]:
        """
        등록된 모든 명령 목록을 반환합니다.

        Returns:
            명령 이름 리스트

        Example:
            >>> handler = InputHandler()
            >>> def test_handler(args):
            ...     return CommandResult(CommandStatus.SUCCESS, "Test")
            >>> handler.register_command("test1", test_handler)
            >>> handler.register_command("test2", test_handler)
            >>> commands = handler.list_commands()
            >>> print(sorted(commands))
            ['test1', 'test2']
        """
        return list(self._command_handlers.keys())

    def get_command_description(self, command: str) -> Optional[str]:
        """
        명령 설명을 조회합니다.

        Args:
            command: 명령 이름

        Returns:
            명령 설명 (없으면 None)

        Example:
            >>> handler = InputHandler()
            >>> def test_handler(args):
            ...     return CommandResult(CommandStatus.SUCCESS, "Test")
            >>> handler.register_command("test", test_handler, "Test command")
            >>> desc = handler.get_command_description("test")
            >>> print(desc)
            Test command
        """
        return self._command_descriptions.get(command.lower())

    def add_command_alias(self, alias: str, command: str) -> None:
        """
        명령 별칭을 추가합니다.

        Args:
            alias: 별칭
            command: 실제 명령 이름

        Example:
            >>> handler = InputHandler()
            >>> def quit_handler(args):
            ...     return CommandResult(CommandStatus.SUCCESS, "Bye")
            >>> handler.register_command("quit", quit_handler)
            >>> handler.add_command_alias("q", "quit")
            >>> result = handler.handle_input("q")
            >>> print(result.output)
            Bye
        """
        alias_lower = alias.lower()
        command_lower = command.lower()

        self._command_aliases[alias_lower] = command_lower
        logger.info(f"Command alias added: {alias_lower} -> {command_lower}")

    def remove_command_alias(self, alias: str) -> None:
        """
        명령 별칭을 제거합니다.

        Args:
            alias: 별칭

        Raises:
            KeyError: 존재하지 않는 별칭

        Example:
            >>> handler = InputHandler()
            >>> handler.add_command_alias("q", "quit")
            >>> handler.remove_command_alias("q")
        """
        alias_lower = alias.lower()

        if alias_lower not in self._command_aliases:
            logger.error(f"Alias not found: {alias_lower}")
            raise KeyError(f"Alias '{alias_lower}' not found")

        del self._command_aliases[alias_lower]
        logger.info(f"Command alias removed: {alias_lower}")

    def get_command_aliases(self) -> Dict[str, str]:
        """
        모든 명령 별칭을 조회합니다.

        Returns:
            별칭 딕셔너리 (alias -> command)

        Example:
            >>> handler = InputHandler()
            >>> handler.add_command_alias("q", "quit")
            >>> handler.add_command_alias("h", "help")
            >>> aliases = handler.get_command_aliases()
            >>> print(len(aliases))
            2
        """
        return self._command_aliases.copy()

    def has_command(self, command: str) -> bool:
        """
        명령이 등록되어 있는지 확인합니다.

        Args:
            command: 명령 이름

        Returns:
            등록 여부

        Example:
            >>> handler = InputHandler()
            >>> def test_handler(args):
            ...     return CommandResult(CommandStatus.SUCCESS, "Test")
            >>> handler.register_command("test", test_handler)
            >>> print(handler.has_command("test"))
            True
            >>> print(handler.has_command("nonexistent"))
            False
        """
        return command.lower() in self._command_handlers

    def get_last_command(self) -> Optional[str]:
        """
        마지막으로 실행한 명령을 반환합니다.

        Returns:
            마지막 명령 (없으면 None)

        Example:
            >>> handler = InputHandler()
            >>> handler.handle_input("test command")
            >>> last = handler.get_last_command()
            >>> print(last)
            test command
        """
        if self._command_history:
            return self._command_history[-1]
        return None

    def search_history(self, keyword: str) -> List[str]:
        """
        명령 히스토리를 키워드로 검색합니다.

        Args:
            keyword: 검색 키워드

        Returns:
            검색 결과 리스트

        Example:
            >>> handler = InputHandler()
            >>> handler.handle_input("echo hello")
            >>> handler.handle_input("echo world")
            >>> handler.handle_input("quit")
            >>> results = handler.search_history("echo")
            >>> print(len(results))
            2
        """
        keyword_lower = keyword.lower()
        results = [
            cmd for cmd in self._command_history
            if keyword_lower in cmd.lower()
        ]

        logger.debug(f"History search: '{keyword}' -> {len(results)} results")

        return results

    def get_help_text(self) -> str:
        """
        사용 가능한 명령 목록을 도움말 형식으로 반환합니다.

        Returns:
            도움말 문자열

        Example:
            >>> handler = InputHandler()
            >>> def test_handler(args):
            ...     return CommandResult(CommandStatus.SUCCESS, "Test")
            >>> handler.register_command("test", test_handler, "Test command")
            >>> help_text = handler.get_help_text()
            >>> print("test" in help_text)
            True
        """
        lines = ["=== Available Commands ===", ""]

        if not self._command_handlers:
            lines.append("No commands registered")
        else:
            for command in sorted(self._command_handlers.keys()):
                description = self._command_descriptions.get(command, "No description")
                lines.append(f"  {command}: {description}")

        lines.append("")

        # 별칭 표시
        if self._command_aliases:
            lines.append("=== Aliases ===")
            lines.append("")
            for alias, command in sorted(self._command_aliases.items()):
                lines.append(f"  {alias} -> {command}")
            lines.append("")

        return "\n".join(lines)

    def validate_command_args(
        self,
        command: str,
        args: List[str],
        min_args: int = 0,
        max_args: Optional[int] = None
    ) -> Optional[str]:
        """
        명령 인자의 유효성을 검증합니다.

        Args:
            command: 명령 이름
            args: 인자 리스트
            min_args: 최소 인자 개수
            max_args: 최대 인자 개수 (None이면 무제한)

        Returns:
            에러 메시지 (유효하면 None)

        Example:
            >>> handler = InputHandler()
            >>> error = handler.validate_command_args("test", ["arg1"], min_args=1)
            >>> print(error)
            None
            >>> error = handler.validate_command_args("test", [], min_args=1)
            >>> print(error is not None)
            True
        """
        args_count = len(args)

        if args_count < min_args:
            return f"Command '{command}' requires at least {min_args} argument(s), got {args_count}"

        if max_args is not None and args_count > max_args:
            return f"Command '{command}' accepts at most {max_args} argument(s), got {args_count}"

        return None

    def get_history_count(self) -> int:
        """
        명령 히스토리 개수를 반환합니다.

        Returns:
            히스토리 개수

        Example:
            >>> handler = InputHandler()
            >>> handler.handle_input("test1")
            >>> handler.handle_input("test2")
            >>> count = handler.get_history_count()
            >>> print(count)
            2
        """
        return len(self._command_history)
