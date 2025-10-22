# 🚀 Advanced Features (고급 기능)

Better-LLM의 수직적 고도화 기능들을 소개합니다.

## 📋 목차

1. [LLM 기반 Intelligent Summarizer](#1-llm-기반-intelligent-summarizer)
2. [Context Metadata 시스템](#2-context-metadata-시스템)
3. [Performance Metrics 수집](#3-performance-metrics-수집)

---

## 1. LLM 기반 Intelligent Summarizer

Worker의 긴 출력을 Claude Haiku를 사용하여 지능적으로 요약합니다.

### 특징
- **지능형 요약**: 패턴 매칭 대신 LLM이 문맥을 이해하여 요약
- **자동 Fallback**: LLM 실패 시 패턴 매칭으로 자동 전환
- **컨텍스트 절약**: Manager 컨텍스트 윈도우 **90% 절감**
- **빠른 응답**: Claude Haiku 사용으로 저렴하고 빠른 요약

### 활성화 방법

```bash
# 환경변수 설정 (기본값: true)
export ENABLE_LLM_SUMMARIZATION=true

# ANTHROPIC_API_KEY 필수
export ANTHROPIC_API_KEY='your-api-key-here'

# Better-LLM 실행
python orchestrator.py "작업 설명"
```

### 비활성화 방법

```bash
# LLM 요약 비활성화 (패턴 매칭 사용)
export ENABLE_LLM_SUMMARIZATION=false
```

### 작동 방식

1. **Worker 실행 완료** → 전체 출력 (수천~수만 자)
2. **LLM 요약** → Claude Haiku가 1줄 + 5-10줄 요약 생성
3. **Artifact 저장** → 전체 로그는 `~/.better-llm/{project}/artifacts/`에 보관
4. **Manager 전달** → 요약만 전달 (컨텍스트 절약)

### 예시

**Before (패턴 매칭):**
```
Planner 출력: 15,000자 → Manager 히스토리에 전부 포함
```

**After (LLM 요약):**
```
Planner 출력: 15,000자
  ↓ Claude Haiku 요약
요약: 1,500자 → Manager 히스토리 (90% 절감)
전체 로그: ~/.better-llm/my-project/artifacts/planner_20251022_143025.txt
```

---

## 2. Context Metadata 시스템

Worker 출력에 구조화된 메타데이터를 자동으로 추가하여 Manager가 컨텍스트를 추적합니다.

### 특징
- **자동 추적**: task_id, dependencies, key_decisions 자동 생성
- **3단계 요약**: one_line, five_line, full (artifact 경로)
- **JSON 직렬화**: Manager가 파싱하여 다음 Worker에게 전달
- **컨텍스트 체인**: 이전 작업과의 연결 관계 추적

### 활성화 방법

```json
// config/system_config.json
{
  "context_metadata": {
    "enabled": true  // 활성화
  }
}
```

### 작동 방식

1. **Worker 실행 완료**
2. **메타데이터 자동 생성**:
   - `task_id`: `planner_20251022_143025`
   - `dependencies`: 이전 task_id 목록
   - `key_decisions`: "결정:", "중요:" 등 키워드에서 자동 추출
   - `artifacts`: Artifact 파일 경로 목록
3. **JSON 블록 추가**:
   ```
   Worker 출력...

   ---
   **Context Metadata** (JSON):
   ```json
   {
     "task_id": "planner_20251022_143025",
     "worker_name": "planner",
     "dependencies": [],
     "key_decisions": ["A안 선택: REST API 방식"],
     "artifacts": ["~/.better-llm/project/artifacts/planner_20251022_143025.txt"]
   }
   ```
   ```
   ```

### 예시

**워크플로우:**
```
Planner (task_id: p1)
  ↓ dependencies: []
Coder (task_id: c1)
  ↓ dependencies: ["p1"]
Reviewer (task_id: r1)
  ↓ dependencies: ["c1"]
Coder (task_id: c2) - 재작업
  ↓ dependencies: ["r1"]
```

Manager는 dependencies를 보고 작업 흐름을 자동으로 파악합니다.

---

## 3. Performance Metrics 수집

Worker별 성과를 자동으로 추적하고 분석합니다.

### 특징
- **토큰 사용량 추적**: input_tokens, output_tokens, cache tokens 자동 수집
- **실행 시간 측정**: Worker별 평균 실행 시간
- **성공률 추적**: Worker별 성공/실패율
- **세션별 분석**: 각 세션의 총 토큰 사용량 및 비용

### 자동 수집 메트릭

```python
{
  "worker_name": "coder",
  "session_id": "session_20251022_143025",
  "start_time": "2025-10-22T14:30:25",
  "end_time": "2025-10-22T14:35:42",
  "duration_seconds": 317,
  "success": True,
  "tokens_used": {
    "input_tokens": 15234,
    "output_tokens": 4521,
    "cache_read_tokens": 8912,
    "cache_creation_tokens": 0,
    "total_tokens": 19755
  },
  "error_message": None
}
```

### 메트릭 확인 방법

```python
# orchestrator.py 실행 후 자동 출력됨
"""
📊 Performance Metrics:
  Planner: 1회, 평균 45초, 성공률 100%, 평균 토큰 12,345
  Coder:   2회, 평균 120초, 성공률 100%, 평균 토큰 23,456
  Reviewer: 1회, 평균 30초, 성공률 100%, 평균 토큰 8,901
  Total tokens: 44,702 (약 $0.67)
"""
```

### 로그에서 확인

```bash
# 로그 파일에 구조화된 메트릭 기록됨
tail -f ~/.better-llm/{project}/logs/better-llm.log | grep "Token usage recorded"
```

---

## 🎯 모든 기능 통합 사용

```bash
# 1. 환경변수 설정
export ANTHROPIC_API_KEY='your-api-key-here'
export ENABLE_LLM_SUMMARIZATION=true  # LLM 요약 활성화

# 2. system_config.json 확인
# "context_metadata": {"enabled": true}

# 3. Better-LLM 실행
python orchestrator.py "새로운 인증 시스템 추가"

# 결과:
# ✅ LLM 기반 요약: Planner 출력 15,000자 → 1,500자 (90% 절감)
# ✅ Context Metadata: task_id, dependencies, key_decisions 자동 추출
# ✅ Performance Metrics: 토큰 사용량, 실행 시간, 성공률 자동 수집
```

---

## 📊 성능 비교

| 기능 | Before | After | 개선율 |
|------|--------|-------|--------|
| **Manager 컨텍스트** | 15,000 토큰 | 1,500 토큰 | **90% 절감** |
| **토큰 추적** | ❌ 미지원 | ✅ 자동 수집 | - |
| **컨텍스트 체인** | ❌ 수동 추적 | ✅ 자동 추적 | - |
| **요약 품질** | 패턴 매칭 | LLM 기반 | **품질 향상** |

---

## 🔧 문제 해결

### LLM 요약 실패 시

```bash
# 에러 로그 확인
tail ~/.better-llm/{project}/logs/better-llm-error.log

# 원인:
# 1. ANTHROPIC_API_KEY 미설정
# 2. anthropic 패키지 미설치 (pip install anthropic)
# 3. API 할당량 초과

# 해결:
# - 자동으로 패턴 매칭으로 fallback됨 (정상 동작)
# - API 키 확인 또는 LLM 요약 비활성화
```

### Context Metadata 비활성화 시

```json
// config/system_config.json
{
  "context_metadata": {
    "enabled": false  // 비활성화
  }
}
```

---

## 📖 추가 문서

- [CLAUDE.md](./CLAUDE.md) - 전체 프로젝트 구조 및 아키텍처
- [CHANGELOG.md](./CHANGELOG.md) - 변경 이력
- [README.md](./README.md) - 시작 가이드

---

**최종 업데이트**: 2025-10-22
