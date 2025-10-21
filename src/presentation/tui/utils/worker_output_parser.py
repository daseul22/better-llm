"""
Worker 출력 파서 - Claude SDK Message 객체를 사람이 읽기 쉽게 정제

Worker 출력은 Claude SDK의 raw Message 객체 형태로 전달되는데,
이를 파싱하여 의미 있는 내용만 추출하고 포맷팅합니다.

v2.0: JSON 파싱 지원, Rich Panel을 사용한 UI 개선
"""

import re
import json
from typing import Optional, Dict, Any, List
from rich.text import Text
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.console import RenderableType


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
    def format_for_display(cls, raw_output: str, worker_name: str) -> RenderableType:
        """
        Worker 출력을 화면에 표시하기 위해 최종 포맷팅 (v2.0)

        Args:
            raw_output: Worker의 raw 출력
            worker_name: Worker 이름 (planner, coder 등)

        Returns:
            최종 포맷팅된 출력 (str 또는 Rich Renderable)
        """
        # 1단계: JSON 파싱 시도 (v2.0 새로운 기능)
        json_result = cls._try_parse_json(raw_output)
        if json_result:
            return json_result

        # 2단계: 정규식 파싱 시도 (기존 로직)
        parsed = cls.parse(raw_output)
        if parsed:
            return parsed

        # 3단계: 일반 텍스트 처리
        # Rich 마크업 이스케이프 (파싱 에러 방지)
        escaped = cls._escape_markup(raw_output)
        # 너무 길면 자르기
        if len(escaped) > 1000:
            return f"[dim]{escaped[:1000]}...[/dim]"
        else:
            return f"[dim]{escaped}[/dim]"

    @classmethod
    def _try_parse_json(cls, raw_output: str) -> Optional[RenderableType]:
        """
        JSON 형태의 출력을 파싱하여 Rich UI로 변환 (v2.0)

        Args:
            raw_output: 원본 출력

        Returns:
            Rich Renderable 또는 None (파싱 실패 시)
        """
        # JSON 객체/배열로 시작하는지 확인
        stripped = raw_output.strip()
        if not (stripped.startswith('{') or stripped.startswith('[')):
            return None

        try:
            # JSON 파싱 시도
            data = json.loads(stripped)

            # Message 객체인 경우
            if isinstance(data, dict):
                return cls._render_message_object(data)

            # 배열인 경우
            elif isinstance(data, list):
                # 여러 메시지가 있는 경우
                results = []
                for item in data:
                    if isinstance(item, dict):
                        results.append(cls._render_message_object(item))
                # 결과가 있으면 첫 번째 반환
                return results[0] if results else None

        except json.JSONDecodeError:
            # JSON 파싱 실패 시 None 반환
            return None

        return None

    @classmethod
    def _render_message_object(cls, message: Dict[str, Any]) -> RenderableType:
        """
        Message 객체를 Rich UI로 렌더링 (v2.0)

        Args:
            message: Message 객체 (dict)

        Returns:
            Rich Renderable
        """
        # AssistantMessage 처리
        if 'content' in message and isinstance(message['content'], list):
            contents = message['content']

            # TextBlock 찾기
            for content in contents:
                if isinstance(content, dict):
                    # TextBlock
                    if content.get('type') == 'text' and 'text' in content:
                        text = content['text']
                        return Panel(
                            Text(text, style="cyan"),
                            title="[bold cyan]💬 사고 과정[/bold cyan]",
                            border_style="cyan",
                            padding=(1, 2)
                        )

                    # ToolUseBlock
                    elif content.get('type') == 'tool_use':
                        return cls._render_tool_use(content)

        # ToolResultBlock 처리 (UserMessage의 content)
        elif 'tool_use_id' in message:
            return cls._render_tool_result(message)

        # 파싱 실패 시 기본 표시
        return f"[dim]{json.dumps(message, indent=2, ensure_ascii=False)}[/dim]"

    @classmethod
    def _render_tool_use(cls, tool_use: Dict[str, Any]) -> RenderableType:
        """
        Tool 호출을 Rich Panel로 렌더링 (v2.0)

        Args:
            tool_use: ToolUseBlock (dict)

        Returns:
            Rich Panel
        """
        tool_name = tool_use.get('name', 'Unknown')
        tool_input = tool_use.get('input', {})
        tool_id = tool_use.get('id', 'N/A')

        # Tool Input을 예쁘게 포맷팅
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Key", style="yellow", width=15)
        table.add_column("Value", style="white")

        for key, value in tool_input.items():
            # 값이 너무 길면 자르기
            value_str = str(value)
            if len(value_str) > 100:
                value_str = value_str[:100] + "..."
            table.add_row(key, value_str)

        return Panel(
            table,
            title=f"[bold yellow]🔧 도구 호출: {tool_name}[/bold yellow]",
            subtitle=f"[dim]ID: {tool_id[:16]}...[/dim]",
            border_style="yellow",
            padding=(1, 2)
        )

    @classmethod
    def _render_tool_result(cls, tool_result: Dict[str, Any]) -> RenderableType:
        """
        Tool 결과를 Rich Panel로 렌더링 (v2.0)

        Args:
            tool_result: ToolResultBlock (dict)

        Returns:
            Rich Panel
        """
        tool_use_id = tool_result.get('tool_use_id', 'N/A')
        content = tool_result.get('content', '')

        # 결과가 너무 길면 자르기
        if isinstance(content, str):
            display_content = content if len(content) <= 500 else content[:500] + "\n..."
        else:
            display_content = str(content)

        return Panel(
            Text(display_content, style="green"),
            title="[bold green]✅ 도구 결과[/bold green]",
            subtitle=f"[dim]Tool ID: {tool_use_id[:16]}...[/dim]",
            border_style="green",
            padding=(1, 2)
        )
