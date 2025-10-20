# Worker 디버그 모드 사용 가이드

## 개요

각 Worker 실행 시 시스템 프롬프트와 컨텍스트 정보를 표시하여 디버깅을 용이하게 합니다.

## 활성화 방법

### 환경변수 설정

```bash
export WORKER_DEBUG_INFO=true
```

또는 실행 시 직접 설정:

```bash
# CLI
WORKER_DEBUG_INFO=true python orchestrator.py "작업 설명"

# TUI
WORKER_DEBUG_INFO=true python tui.py
```

## 표시되는 정보

각 Worker 실행 시 다음 정보가 아웃풋 패널에 표시됩니다:

```
======================================================================
🔍 [PLANNER] 실행 정보
======================================================================

📋 Worker: planner (계획 수립)
🤖 Model: claude-sonnet-4-5-20250929
🛠️  Tools: read, glob

📄 System Prompt File: prompts/planner.txt
   Length: 1794 characters

🏗️  Project Context:
   - Project: better-llm
   - Description: 그룹 챗 오케스트레이션 시스템 v4.0 - Manager Agent가...
   - Coding Style: Python, indentation=4
   - Testing: pytest

📝 Task Description:
   프로젝트 README 파일을 개선하기 위한 계획을 수립하세요.
   간단히 3단계만 작성해주세요.

======================================================================
⚡ Starting execution...
```

### 표시 정보 상세

1. **Worker 기본 정보**
   - Worker 이름 및 역할
   - 사용 모델
   - 허용된 도구 목록

2. **시스템 프롬프트**
   - 프롬프트 파일 경로
   - 프롬프트 길이 (문자 수)

3. **프로젝트 컨텍스트**
   - 프로젝트 이름
   - 프로젝트 설명
   - 코딩 스타일 (언어, 들여쓰기)
   - 테스팅 프레임워크

4. **작업 설명**
   - Worker에 전달된 Task Description
   - 최대 5줄까지 표시 (긴 경우 생략)

## 사용 예시

### CLI에서 디버그 모드로 실행

```bash
export WORKER_DEBUG_INFO=true
python orchestrator.py "FastAPI로 사용자 인증 API를 구현해줘"
```

각 Worker (Planner → Coder → Reviewer → Tester) 실행 시
위의 디버그 정보가 순차적으로 표시됩니다.

### TUI에서 디버그 모드로 실행

```bash
export WORKER_DEBUG_INFO=true
python tui.py
```

TUI 실행 중:
1. Worker 아웃풋 패널에서 `Ctrl+Tab`으로 각 Worker 탭 이동
2. 각 Worker 실행 정보를 상단에서 확인
3. `?` 키를 눌러 도움말에서 자세한 사용법 확인

## 비활성화

디버그 정보를 숨기려면:

```bash
unset WORKER_DEBUG_INFO
# 또는
export WORKER_DEBUG_INFO=false
```

## 활용 팁

### 1. Worker 프롬프트 검증
시스템 프롬프트 파일을 수정한 후 제대로 로드되었는지 확인:

```bash
WORKER_DEBUG_INFO=true python orchestrator.py "간단한 테스트"
# 프롬프트 파일 경로와 길이 확인
```

### 2. 프로젝트 컨텍스트 확인
`.context.json` 파일이 제대로 로드되는지 확인:

```bash
WORKER_DEBUG_INFO=true python orchestrator.py "README 개선"
# Project Context 섹션 확인
```

### 3. Worker별 도구 권한 확인
각 Worker가 어떤 도구를 사용할 수 있는지 확인:

```bash
WORKER_DEBUG_INFO=true python orchestrator.py "파일 생성"
# Coder의 Tools 목록: read, write, edit, glob, grep
```

### 4. 작업 설명 전달 확인
Manager가 Worker에게 전달하는 Task Description 확인:

```bash
WORKER_DEBUG_INFO=true python orchestrator.py "복잡한 요청..."
# Task Description 섹션에서 실제 전달된 내용 확인
```

## 주의사항

1. **출력량 증가**: 디버그 모드 활성화 시 아웃풋이 많아집니다
2. **성능 영향**: 미미하지만 약간의 오버헤드 존재
3. **민감 정보**: 시스템 프롬프트 내용이 표시되므로 주의

## 관련 문서

- [TUI 사용 가이드](use_cases_guide.md)
- [Worker Agent 설정](../config/agent_config.json)
- [시스템 프롬프트](../prompts/)
