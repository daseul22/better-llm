"""
Worker 출력 자동 요약 시스템

Worker의 긴 출력을 자동으로 요약하여 MCP 도구 제한(25,000 토큰)을 우회합니다.

2가지 요약 방식:
1. LLM 기반 요약 (기본): Claude Haiku를 사용하여 지능적으로 요약
2. 패턴 매칭 요약 (fallback): 정규식 기반 휴리스틱 요약
"""

import re
import os
from typing import Dict, Tuple, Optional
from pathlib import Path

from ..logging import get_logger
from ..config.env_utils import parse_bool_env

logger = get_logger(__name__, component="OutputSummarizer")

# 환경변수로 LLM 요약 on/off (기본값: true)
ENABLE_LLM_SUMMARIZATION = parse_bool_env("ENABLE_LLM_SUMMARIZATION", default=True)


class WorkerOutputSummarizer:
    """
    Worker 출력을 3단계로 요약하는 시스템

    - Level 1 (1줄): 작업 상태
    - Level 2 (5-10줄): 핵심 내용
    - Level 3 (전체): Artifact 파일로 저장

    Attributes:
        max_summary_lines: Level 2 요약 최대 라인 수
    """

    def __init__(self, max_summary_lines: int = 10, use_llm: bool = ENABLE_LLM_SUMMARIZATION):
        """
        Args:
            max_summary_lines: Level 2 요약 최대 라인 수
            use_llm: LLM 기반 요약 사용 여부 (기본값: 환경변수)
        """
        self.max_summary_lines = max_summary_lines
        self.use_llm = use_llm

        # LLM 사용 시 Anthropic 클라이언트 초기화
        if self.use_llm:
            try:
                import anthropic
                api_key = os.getenv("ANTHROPIC_API_KEY")
                if api_key:
                    self.anthropic_client = anthropic.Anthropic(api_key=api_key)
                    logger.info("LLM-based summarization enabled (Claude Haiku)")
                else:
                    logger.warning("ANTHROPIC_API_KEY not found, falling back to pattern matching")
                    self.use_llm = False
                    self.anthropic_client = None
            except ImportError:
                logger.warning("anthropic package not installed, falling back to pattern matching")
                self.use_llm = False
                self.anthropic_client = None
        else:
            self.anthropic_client = None
            logger.info("Pattern-matching summarization enabled (LLM disabled)")

    def summarize(
        self,
        worker_name: str,
        full_output: str,
        artifact_path: str
    ) -> Dict[str, str]:
        """
        Worker 출력을 3단계로 요약

        Args:
            worker_name: Worker 이름
            full_output: 전체 출력
            artifact_path: Artifact 파일 경로

        Returns:
            {
                "one_line": "1줄 요약",
                "summary": "5-10줄 요약",
                "full_path": "artifact 경로"
            }
        """
        # LLM 기반 요약 시도
        if self.use_llm and self.anthropic_client:
            try:
                llm_summary = self._summarize_with_llm(worker_name, full_output)
                if llm_summary:
                    logger.debug(
                        "LLM summarization successful",
                        worker_name=worker_name,
                        output_length=len(full_output)
                    )
                    return {
                        "one_line": llm_summary["one_line"],
                        "summary": llm_summary["summary"],
                        "full_path": artifact_path
                    }
            except Exception as e:
                logger.warning(
                    "LLM summarization failed, falling back to pattern matching",
                    worker_name=worker_name,
                    error=str(e)
                )

        # Fallback: 패턴 매칭 기반 요약
        logger.debug(
            "Using pattern-matching summarization",
            worker_name=worker_name
        )
        one_line = self._extract_one_line_summary(worker_name, full_output)
        summary = self._extract_key_summary(full_output)

        return {
            "one_line": one_line,
            "summary": summary,
            "full_path": artifact_path
        }

    def _summarize_with_llm(self, worker_name: str, full_output: str) -> Optional[Dict[str, str]]:
        """
        LLM을 사용하여 Worker 출력 요약

        Claude Haiku를 사용하여 빠르고 저렴하게 요약합니다.
        - 1줄 요약: 핵심 작업 상태
        - 5-10줄 요약: 중요 내용 및 결정 사항

        Args:
            worker_name: Worker 이름
            full_output: 전체 출력

        Returns:
            {"one_line": "...", "summary": "..."} 또는 None (실패 시)
        """
        if not self.anthropic_client:
            return None

        # 출력이 너무 길면 앞부분만 사용 (토큰 제한)
        max_chars = 15000  # 약 5000 토큰
        truncated_output = full_output[:max_chars]
        if len(full_output) > max_chars:
            truncated_output += "\n\n... (출력 생략) ..."

        # LLM 요약 프롬프트
        prompt = f"""다음은 {worker_name} Worker의 출력입니다. 이를 2가지 형식으로 요약해주세요:

1. **1줄 요약** (최대 200자): 핵심 작업 상태 및 결과
2. **5-10줄 요약** (최대 500자): 중요 내용, 변경 파일, 주요 결정 사항

출력 형식:
```
ONE_LINE: (1줄 요약)
SUMMARY:
(5-10줄 요약)
```

Worker 출력:
---
{truncated_output}
---

요약을 시작하세요:"""

        try:
            # Claude Haiku 호출 (빠르고 저렴)
            response = self.anthropic_client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=1024,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )

            # 응답 파싱 (안전한 접근)
            if not response.content or len(response.content) == 0:
                logger.warning(
                    "LLM response content is empty",
                    worker_name=worker_name
                )
                return None

            # content[0].text가 None일 수 있으므로 안전하게 접근
            content_block = response.content[0]
            if not hasattr(content_block, 'text') or not content_block.text:
                logger.warning(
                    "LLM response content[0].text is None or missing",
                    worker_name=worker_name,
                    content_block_type=type(content_block).__name__
                )
                return None

            summary_text = content_block.text.strip()

            # ONE_LINE 추출
            one_line_match = re.search(r"ONE_LINE:\s*(.+?)(?:\n|$)", summary_text, re.DOTALL)
            one_line = one_line_match.group(1).strip() if one_line_match else ""

            # SUMMARY 추출
            summary_match = re.search(r"SUMMARY:\s*(.+)", summary_text, re.DOTALL)
            summary = summary_match.group(1).strip() if summary_match else ""

            # 검증
            if not one_line or not summary:
                logger.warning(
                    "LLM summary parsing failed",
                    worker_name=worker_name,
                    response_preview=summary_text[:200]
                )
                return None

            return {
                "one_line": one_line[:200],  # 최대 200자
                "summary": summary[:500]  # 최대 500자
            }

        except Exception as e:
            logger.warning(
                "LLM API call failed",
                worker_name=worker_name,
                error=str(e)
            )
            return None

    def _extract_one_line_summary(self, worker_name: str, output: str) -> str:
        """
        1줄 요약 추출

        전략:
        1. "## 요약" 섹션의 첫 줄 찾기
        2. 없으면 첫 번째 헤더(##) 찾기
        3. 없으면 첫 5단어 + "..."

        Args:
            worker_name: Worker 이름
            output: 전체 출력

        Returns:
            1줄 요약
        """
        # 전략 1: "## 요약" 또는 "## Summary" 섹션 찾기
        summary_match = re.search(
            r'##\s*(요약|Summary|결론|Conclusion)\s*\n(.+?)(?:\n|$)',
            output,
            re.IGNORECASE
        )
        if summary_match:
            return summary_match.group(2).strip()[:200]  # 최대 200자

        # 전략 2: 첫 번째 ## 헤더 찾기
        header_match = re.search(r'##\s*(.+?)(?:\n|$)', output)
        if header_match:
            return header_match.group(1).strip()[:200]

        # 전략 3: 첫 5단어
        words = output.split()[:10]
        if words:
            truncated = ' '.join(words)
            return f"[{worker_name}] {truncated[:150]}..."

        return f"[{worker_name}] 작업 완료"

    def _extract_key_summary(self, output: str) -> str:
        """
        핵심 요약 추출 (5-10줄)

        전략:
        1. "## 요약" 섹션 전체 추출
        2. 없으면 주요 헤더(##) 목록 추출
        3. 없으면 첫 10줄 추출

        Args:
            output: 전체 출력

        Returns:
            5-10줄 요약
        """
        lines = output.split('\n')

        # 전략 1: "## 요약" 섹션 추출
        summary_section = self._extract_section(output, r'##\s*(요약|Summary|결론|Conclusion)')
        if summary_section:
            summary_lines = summary_section.split('\n')[:self.max_summary_lines]
            return '\n'.join(summary_lines)

        # 전략 2: 주요 헤더(##) 목록 추출
        headers = re.findall(r'##\s*(.+?)(?:\n|$)', output)
        if headers:
            header_list = '\n'.join(f"- {h.strip()}" for h in headers[:self.max_summary_lines])
            return f"**주요 섹션:**\n{header_list}"

        # 전략 3: 첫 N줄 추출 (공백/구분선 제외)
        meaningful_lines = [
            line for line in lines
            if line.strip() and not line.strip().startswith('=') and not line.strip().startswith('-')
        ]
        truncated_lines = meaningful_lines[:self.max_summary_lines]
        return '\n'.join(truncated_lines)

    def _extract_section(self, text: str, section_header_pattern: str) -> str:
        """
        특정 섹션 추출

        Args:
            text: 전체 텍스트
            section_header_pattern: 섹션 헤더 정규식 패턴

        Returns:
            섹션 내용 (헤더 제외)
        """
        # 섹션 시작 찾기
        match = re.search(section_header_pattern, text, re.IGNORECASE)
        if not match:
            return ""

        start = match.end()

        # 다음 ## 헤더까지 또는 끝까지
        next_header = re.search(r'\n##\s', text[start:])
        if next_header:
            end = start + next_header.start()
        else:
            end = len(text)

        return text[start:end].strip()

    def format_summary_output(
        self,
        worker_name: str,
        summary: Dict[str, str]
    ) -> str:
        """
        요약을 포맷팅된 문자열로 변환

        Args:
            worker_name: Worker 이름
            summary: summarize() 반환값

        Returns:
            포맷팅된 요약 문자열
        """
        return f"""## 📋 [{worker_name.upper()} 요약 - Manager 전달용]

**✅ 상태: 작업 완료**

**핵심 내용**:
{summary['summary']}

**요약**: {summary['one_line']}

---
**[전체 로그: artifact `{Path(summary['full_path']).stem}`]**

⚠️ **중요**: 이 Worker는 이미 실행되었습니다. 동일한 Worker를 다시 호출하지 마세요.
"""


def test_summarizer():
    """간단한 테스트"""
    summarizer = WorkerOutputSummarizer()

    # 테스트 출력
    test_output = """## 요구사항 분석

사용자는 FastAPI CRUD API를 원합니다.

## 구현 계획

1. 모델 정의
2. API 라우터 작성
3. 테스트 작성

## 예상 위험 요소

- DB 연결 설정 필요
- 인증 처리 고려
"""

    summary = summarizer.summarize(
        worker_name="planner",
        full_output=test_output,
        artifact_path="/path/to/artifact/planner_20251022_001.txt"
    )

    formatted = summarizer.format_summary_output("planner", summary)
    print(formatted)
    print("\n✅ Summarizer 테스트 완료")


if __name__ == "__main__":
    test_summarizer()
