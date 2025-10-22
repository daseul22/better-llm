"""
Worker Output Summarizer 테스트
"""

import pytest
from src.infrastructure.mcp.output_summarizer import WorkerOutputSummarizer


class TestWorkerOutputSummarizer:
    """WorkerOutputSummarizer 테스트"""

    def setup_method(self):
        """각 테스트 전 실행"""
        self.summarizer = WorkerOutputSummarizer(max_summary_lines=10)

    def test_extract_one_line_summary_from_summary_section(self):
        """## 요약 섹션에서 1줄 요약 추출"""
        output = """
## 요약

FastAPI CRUD API 구현 완료

## 상세 내용
...
"""
        result = self.summarizer._extract_one_line_summary("planner", output)
        assert "FastAPI CRUD API 구현 완료" in result

    def test_extract_one_line_summary_from_first_header(self):
        """첫 번째 헤더에서 1줄 요약 추출"""
        output = """
## 구현 계획

상세 내용...
"""
        result = self.summarizer._extract_one_line_summary("coder", output)
        assert "구현 계획" in result

    def test_extract_one_line_summary_fallback(self):
        """헤더가 없을 때 첫 단어로 폴백"""
        output = "This is a simple output without headers"
        result = self.summarizer._extract_one_line_summary("reviewer", output)
        assert "reviewer" in result.lower()
        assert "This is a" in result

    def test_extract_key_summary_from_summary_section(self):
        """## 요약 섹션에서 핵심 요약 추출"""
        output = """
## 요약

Line 1
Line 2
Line 3

## 다른 섹션
...
"""
        result = self.summarizer._extract_key_summary(output)
        assert "Line 1" in result
        assert "Line 2" in result
        assert "Line 3" in result

    def test_extract_key_summary_from_headers(self):
        """헤더 목록으로 요약 생성"""
        output = """
## 섹션 1

내용...

## 섹션 2

내용...

## 섹션 3

내용...
"""
        result = self.summarizer._extract_key_summary(output)
        assert "섹션 1" in result
        assert "섹션 2" in result
        assert "섹션 3" in result

    def test_summarize_full_workflow(self):
        """전체 워크플로우 테스트"""
        full_output = """
## 요구사항 분석

사용자는 FastAPI CRUD API를 요청했습니다.

## 구현 계획

1. 모델 정의
2. API 라우터 작성
3. 테스트 작성

## 예상 위험 요소

- DB 연결 필요
- 인증 처리 고려
"""
        summary = self.summarizer.summarize(
            worker_name="planner",
            full_output=full_output,
            artifact_path="/tmp/artifact_test.txt"
        )

        assert "one_line" in summary
        assert "summary" in summary
        assert "full_path" in summary
        assert summary["full_path"] == "/tmp/artifact_test.txt"
        assert len(summary["one_line"]) > 0
        assert len(summary["summary"]) > 0

    def test_format_summary_output(self):
        """요약 포맷팅 테스트"""
        summary = {
            "one_line": "작업 완료",
            "summary": "핵심 내용1\n핵심 내용2",
            "full_path": "/tmp/artifact.txt"
        }
        formatted = self.summarizer.format_summary_output("coder", summary)

        assert "CODER 요약" in formatted
        assert "작업 완료" in formatted
        assert "핵심 내용1" in formatted
        assert "artifact" in formatted.lower()

    def test_max_summary_lines_limit(self):
        """요약 라인 수 제한 테스트"""
        summarizer = WorkerOutputSummarizer(max_summary_lines=3)
        output = "\n".join([f"Line {i}" for i in range(20)])

        result = summarizer._extract_key_summary(output)
        lines = result.strip().split('\n')
        assert len(lines) <= 3

    def test_extract_section(self):
        """특정 섹션 추출 테스트"""
        text = """
## Introduction

This is intro.

## Summary

This is summary content.
Multiple lines here.

## Conclusion

This is conclusion.
"""
        result = self.summarizer._extract_section(text, r"##\s*Summary")
        assert "This is summary content" in result
        assert "Multiple lines here" in result
        assert "Conclusion" not in result

    def test_empty_output(self):
        """빈 출력 처리"""
        summary = self.summarizer.summarize(
            worker_name="tester",
            full_output="",
            artifact_path="/tmp/empty.txt"
        )
        assert summary["one_line"] == "[tester] 작업 완료"
        assert len(summary["summary"]) >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
