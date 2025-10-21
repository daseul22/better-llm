"""
Worker 출력 파서 - Claude SDK Message 객체를 사람이 읽기 쉽게 정제

Worker 출력은 Claude SDK의 raw Message 객체 형태로 전달되는데,
이를 파싱하여 의미 있는 내용만 추출하고 포맷팅합니다.
"""

import re
from typing import Optional
from rich.text import Text
from rich.panel import Panel
from rich.syntax import Syntax


class WorkerOutputParser:
    """Worker 출력 파서 - Message 객체를 정제하여 표시"""

    # Message 객체 패턴
    ASSISTANT_MESSAGE_PATTERN = re.compile(
        r"AssistantMessage\(content=\[(.*?)\], model='([^']+)'.*?\)",
        re.DOTALL
    )
    USER_MESSAGE_PATTERN = re.compile(
        r"UserMessage\(content=\[(.*?)\]\)",
        re.DOTALL
    )

    # Block 패턴
    TOOL_USE_BLOCK_PATTERN = re.compile(
        r"ToolUseBlock\(id='([^']+)', name='([^']+)', input=(\{.*?\})\)",
        re.DOTALL
    )
    TOOL_RESULT_BLOCK_PATTERN = re.compile(
        r"ToolResultBlock\(tool_use_id='([^']+)', content='(.*?)'\)",
        re.DOTALL
    )
    TEXT_BLOCK_PATTERN = re.compile(
        r"TextBlock\(text='(.*?)'\)",
        re.DOTALL
    )

    @classmethod
    def parse(cls, raw_output: str) -> Optional[str]:
        """
        Worker 출력 파싱 및 정제

        Args:
            raw_output: Worker의 raw 출력 (Message 객체 문자열)

        Returns:
            정제된 출력 문자열 (None이면 파싱 실패)
        """
        # AssistantMessage 파싱
        assistant_match = cls.ASSISTANT_MESSAGE_PATTERN.search(raw_output)
        if assistant_match:
            return cls._parse_assistant_message(assistant_match)

        # UserMessage 파싱
        user_match = cls.USER_MESSAGE_PATTERN.search(raw_output)
        if user_match:
            return cls._parse_user_message(user_match)

        # 일반 텍스트는 그대로 반환
        # (Message 객체가 아닌 경우)
        if not raw_output.startswith(("AssistantMessage", "UserMessage")):
            return raw_output

        # 파싱 실패 시 None
        return None

    @classmethod
    def _parse_assistant_message(cls, match: re.Match) -> str:
        """AssistantMessage 파싱"""
        content = match.group(1)
        model = match.group(2)

        # ToolUseBlock 파싱
        tool_use_match = cls.TOOL_USE_BLOCK_PATTERN.search(content)
        if tool_use_match:
            tool_id = tool_use_match.group(1)
            tool_name = tool_use_match.group(2)
            tool_input = tool_use_match.group(3)

            # Tool 입력 파라미터 정제 (이스케이프 포함)
            tool_input_clean = cls._format_tool_input(tool_input)

            return (
                f"[bold cyan]🔧 Tool 호출[/bold cyan]\n"
                f"  Tool: [yellow]{tool_name}[/yellow]\n"
                f"  Input: {tool_input_clean}\n"
                f"  [dim]ID: {tool_id[:16]}...[/dim]"
            )

        # TextBlock 파싱
        text_match = cls.TEXT_BLOCK_PATTERN.search(content)
        if text_match:
            text = text_match.group(1)
            # 이스케이프 문자 처리
            text = text.replace("\\n", "\n").replace("\\'", "'").replace('\\"', '"')
            # Rich 마크업 이스케이프
            text = cls._escape_markup(text)
            return f"[dim cyan]💬[/dim cyan] {text}"

        # 파싱 실패 시 원본 반환
        return f"[dim]AssistantMessage (파싱 실패)[/dim]"

    @classmethod
    def _parse_user_message(cls, match: re.Match) -> str:
        """UserMessage 파싱"""
        content = match.group(1)

        # ToolResultBlock 파싱
        tool_result_match = cls.TOOL_RESULT_BLOCK_PATTERN.search(content)
        if tool_result_match:
            tool_use_id = tool_result_match.group(1)
            result_content = tool_result_match.group(2)

            # 결과 내용 정제 (너무 길면 자르기)
            MAX_RESULT_LENGTH = 500
            if len(result_content) > MAX_RESULT_LENGTH:
                result_preview = result_content[:MAX_RESULT_LENGTH] + "..."
            else:
                result_preview = result_content

            # 이스케이프 문자 처리
            result_preview = result_preview.replace("\\n", "\n").replace("\\'", "'").replace('\\"', '"')
            # Rich 마크업 이스케이프
            result_preview = cls._escape_markup(result_preview)

            return (
                f"[bold green]✅ Tool 결과[/bold green]\n"
                f"{result_preview}\n"
                f"  [dim]Tool ID: {tool_use_id[:16]}...[/dim]"
            )

        # 파싱 실패 시 원본 반환
        return f"[dim]UserMessage (파싱 실패)[/dim]"

    @classmethod
    def _format_tool_input(cls, tool_input: str) -> str:
        """
        Tool 입력 파라미터 포맷팅

        Args:
            tool_input: Tool 입력 딕셔너리 문자열

        Returns:
            포맷팅된 문자열
        """
        # Rich 마크업 이스케이프 ([, ] 문자)
        tool_input = cls._escape_markup(tool_input)

        # 간단한 파라미터는 한 줄로
        if len(tool_input) < 100:
            return tool_input

        # 복잡한 파라미터는 줄바꿈
        # {'file_path': '...', 'content': '...'} 형태를 여러 줄로
        formatted = tool_input.replace("', '", "',\n    '")
        formatted = formatted.replace("{", "{\n    ")
        formatted = formatted.replace("}", "\n  }")

        return formatted

    @classmethod
    def _escape_markup(cls, text: str) -> str:
        """
        Rich 마크업 이스케이프 처리

        Args:
            text: 원본 텍스트

        Returns:
            이스케이프된 텍스트
        """
        # [ 와 ] 문자를 이스케이프
        # \[ 로 이스케이프하면 Rich가 리터럴로 처리
        return text.replace("[", r"\[").replace("]", r"\]")

    @classmethod
    def format_for_display(cls, raw_output: str, worker_name: str) -> str:
        """
        Worker 출력을 화면에 표시하기 위해 최종 포맷팅

        Args:
            raw_output: Worker의 raw 출력
            worker_name: Worker 이름 (planner, coder 등)

        Returns:
            최종 포맷팅된 출력
        """
        # 파싱 시도
        parsed = cls.parse(raw_output)

        if parsed:
            return parsed
        else:
            # 파싱 실패 시 원본 반환 (디버그용)
            # Rich 마크업 이스케이프 (파싱 에러 방지)
            escaped = cls._escape_markup(raw_output)
            # 너무 길면 자르기
            if len(escaped) > 1000:
                return f"[dim]{escaped[:1000]}...[/dim]"
            else:
                return f"[dim]{escaped}[/dim]"
