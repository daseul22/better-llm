# 문제 해결

Better-LLM 사용 중 발생할 수 있는 일반적인 문제와 해결 방법을 안내합니다.

## 설치 문제

### Python 버전 오류

**증상**:
```
ERROR: This package requires Python 3.10 or higher
```

**해결**:
```bash
# Python 버전 확인
python --version

# Python 3.10+ 설치
# macOS (Homebrew)
brew install python@3.11

# Ubuntu/Debian
sudo apt install python3.11

# pyenv 사용
pyenv install 3.11.0
pyenv global 3.11.0
```

### pipx 설치 실패

**증상**:
```
command not found: pipx
```

**해결**:
```bash
# macOS
brew install pipx
pipx ensurepath

# Ubuntu/Debian
sudo apt install pipx

# pip로 설치
python -m pip install --user pipx
python -m pipx ensurepath

# 셸 재시작
exec $SHELL
```

### 의존성 설치 실패

**증상**:
```
ERROR: Could not find a version that satisfies the requirement anthropic
```

**해결**:
```bash
# pip 업그레이드
pip install --upgrade pip

# 캐시 삭제 후 재설치
pip cache purge
pip install -e .

# 특정 의존성 버전 지정
pip install anthropic==0.40.0
```

## API 키 문제

### API 키 미설정

**증상**:
```
APIError: ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다.
```

**해결**:
```bash
# 환경 변수 확인
echo $ANTHROPIC_API_KEY

# 비어있으면 설정
export ANTHROPIC_API_KEY='your-api-key-here'

# 영구 설정 (bash)
echo "export ANTHROPIC_API_KEY='your-api-key-here'" >> ~/.bashrc
source ~/.bashrc

# 영구 설정 (zsh)
echo "export ANTHROPIC_API_KEY='your-api-key-here'" >> ~/.zshrc
source ~/.zshrc

# .env 파일 사용
echo "ANTHROPIC_API_KEY=your-api-key-here" > .env
```

### API 키 유효하지 않음

**증상**:
```
APIError: 유효하지 않은 API 키입니다.
```

**해결**:
1. [Anthropic Console](https://console.anthropic.com/)에서 새 키 발급
2. 키 복사 (한 번만 표시됨!)
3. 환경 변수 재설정:
   ```bash
   export ANTHROPIC_API_KEY='sk-ant-api...'
   ```

### API 호출 한도 초과

**증상**:
```
APIError: API 호출 한도를 초과했습니다. 60초 후 다시 시도하세요.
```

**해결**:
1. 대기 후 재시도
2. 프롬프트 캐싱 활성화:
   ```json
   {
     "performance": {
       "enable_caching": true,
       "cache_ttl_seconds": 3600
     }
   }
   ```
3. API 플랜 업그레이드 고려

## 설정 파일 문제

### 설정 파일을 찾을 수 없음

**증상**:
```
ConfigError: 설정 파일 'config/agent_config.json'을 찾을 수 없습니다.
```

**해결**:
```bash
# 파일 존재 확인
ls -la config/

# 없으면 git에서 복원
git checkout config/agent_config.json

# 또는 샘플 파일 복사
cp config/agent_config.json.example config/agent_config.json
```

### 설정 파일 형식 오류

**증상**:
```
ConfigError: 설정 파일 형식이 올바르지 않습니다: Expecting ',' delimiter
```

**해결**:
```bash
# JSON 형식 검증
cat config/agent_config.json | jq .

# 에러 위치 확인
python -m json.tool config/agent_config.json

# 일반적인 오류:
# 1. 마지막 항목 뒤 쉼표
# 2. 따옴표 누락
# 3. 중괄호/대괄호 불일치
```

### 프롬프트 파일 없음

**증상**:
```
ConfigError: 프롬프트 파일 'prompts/planner.txt'을 찾을 수 없습니다.
```

**해결**:
```bash
# 파일 존재 확인
ls -la prompts/

# git에서 복원
git checkout prompts/planner.txt

# 또는 빈 파일 생성 (임시)
touch prompts/planner.txt
```

## Worker 실행 문제

### Worker 타임아웃

**증상**:
```
WorkerError: Worker 'coder'의 실행 시간이 600초를 초과했습니다.
```

**해결**:
1. 타임아웃 증가:
   ```bash
   # 환경 변수로
   export WORKER_TIMEOUT_CODER=1200

   # 설정 파일로
   # config/agent_config.json
   {
     "agents": [
       {
         "name": "coder",
         "timeout": 1200
       }
     ]
   }
   ```

2. 작업 분할:
   ```bash
   # 한 번에 하지 말고 단계별로
   better-llm-cli "@planner 계획 수립"
   better-llm-cli "@coder 1단계만 구현"
   ```

### Worker 실행 실패

**증상**:
```
WorkerError: Worker 'planner' 실행 중 오류가 발생했습니다
```

**해결**:
1. 로그 확인:
   ```bash
   tail -n 50 logs/better-llm-error.log
   ```

2. 상세 로깅 활성화:
   ```bash
   export LOG_LEVEL=DEBUG
   better-llm-cli -v "작업 설명"
   ```

3. Worker 재시도:
   ```json
   {
     "performance": {
       "worker_retry_enabled": true,
       "worker_retry_max_attempts": 3
     }
   }
   ```

### Worker를 찾을 수 없음

**증상**:
```
WorkerError: Worker 'planer'을 찾을 수 없습니다.
```

**해결**:
1. 이름 확인 (오타):
   - ❌ `planer`
   - ✅ `planner`

2. 설정 파일 확인:
   ```bash
   cat config/agent_config.json | jq '.agents[].name'
   ```

3. 사용 가능한 Worker:
   - `planner`
   - `coder`
   - `tester`
   - `reviewer`
   - `committer`

## 세션 관리 문제

### 세션 저장 실패

**증상**:
```
SessionError: 세션 'abc123' 저장에 실패했습니다: Permission denied
```

**해결**:
```bash
# 디렉토리 권한 확인
ls -la sessions/

# 권한 수정
chmod 755 sessions/

# 디스크 공간 확인
df -h

# 공간 확보 (오래된 세션 삭제)
find sessions/ -mtime +30 -delete
```

### 세션 로드 실패

**증상**:
```
SessionError: 세션 'abc123' 로드에 실패했습니다: File is corrupted
```

**해결**:
1. 압축 파일 확인:
   ```bash
   # .json.gz 파일이 손상되었는지 확인
   gzip -t sessions/abc123.json.gz

   # 손상되었으면 백업에서 복원
   cp sessions/.backup/abc123.json sessions/
   ```

2. 압축 비활성화:
   ```json
   {
     "performance": {
       "enable_session_compression": false
     }
   }
   ```

### 최대 턴 수 초과

**증상**:
```
SessionError: 세션의 턴 수가 최대값(50)을 초과했습니다.
```

**해결**:
1. 새 세션 시작:
   ```bash
   # TUI에서 Ctrl+N
   # CLI에서
   better-llm-cli -s new-session "작업 설명"
   ```

2. 최대 턴 수 증가:
   ```json
   {
     "workflow_limits": {
       "max_turns": 100
     }
   }
   ```

## 성능 문제

### 응답 속도가 느림

**해결**:
1. 프롬프트 캐싱 활성화:
   ```json
   {
     "performance": {
       "enable_caching": true,
       "cache_ttl_seconds": 3600
     }
   }
   ```

2. 로그 레벨 낮추기:
   ```bash
   export LOG_LEVEL=WARNING
   ```

3. 메트릭 플러시 주기 증가:
   ```json
   {
     "performance": {
       "metrics_flush_interval": 10.0
     }
   }
   ```

### 메모리 사용량이 높음

**해결**:
1. 세션 압축 활성화:
   ```json
   {
     "performance": {
       "enable_session_compression": true
     }
   }
   ```

2. 캐시 크기 제한:
   ```json
   {
     "performance": {
       "cache_max_size": 50
     }
   }
   ```

3. 메트릭 큐 크기 감소:
   ```json
   {
     "performance": {
       "metrics_buffer_size": 500
     }
   }
   ```

### 디스크 공간 부족

**해결**:
```bash
# 오래된 세션 삭제
find sessions/ -mtime +30 -delete

# 오래된 로그 삭제
find logs/ -mtime +7 -delete

# 세션 압축
cd sessions/
for f in *.json; do gzip "$f"; done
```

## 로깅 문제

### 로그 파일이 생성되지 않음

**해결**:
```bash
# 로그 디렉토리 생성
mkdir -p logs

# 권한 확인
chmod 755 logs/

# 로깅 설정 확인
export LOG_DIR=logs
export LOG_LEVEL=INFO
```

### 로그 파일이 너무 큼

**해결**:
1. 로그 로테이션 자동 설정됨:
   - `better-llm.log`: 10MB 로테이션, 5개 백업
   - `better-llm-error.log`: 5MB 로테이션, 3개 백업

2. 수동 로테이션:
   ```bash
   mv logs/better-llm.log logs/better-llm.log.1
   mv logs/better-llm.log.1.gz logs/better-llm.log.2.gz
   gzip logs/better-llm.log.1
   ```

3. 로그 레벨 조정:
   ```bash
   # DEBUG는 매우 상세함
   export LOG_LEVEL=WARNING
   ```

## TUI 문제

### TUI가 시작되지 않음

**증상**:
```
ImportError: No module named 'textual'
```

**해결**:
```bash
# textual 재설치
pip install --upgrade textual

# 또는 전체 재설치
pip install -e .
```

### TUI 레이아웃 깨짐

**해결**:
```bash
# 터미널 크기 확인 (최소 80x24)
echo $COLUMNS x $LINES

# 터미널 크기 조정
# macOS: Cmd + + (확대)
# Linux: Ctrl + Shift + + (확대)

# 또는 풀스크린 모드
```

### TUI에서 한글 깨짐

**해결**:
```bash
# 로케일 확인
locale

# UTF-8 설정
export LANG=ko_KR.UTF-8
export LC_ALL=ko_KR.UTF-8

# 터미널 폰트를 UTF-8 지원 폰트로 변경
# 추천: D2Coding, Noto Sans Mono CJK
```

## 네트워크 문제

### API 연결 실패

**증상**:
```
APIError: 네트워크 연결 오류가 발생했습니다
```

**해결**:
1. 인터넷 연결 확인:
   ```bash
   ping api.anthropic.com
   ```

2. 프록시 설정 (회사 네트워크):
   ```bash
   export HTTP_PROXY=http://proxy.company.com:8080
   export HTTPS_PROXY=http://proxy.company.com:8080
   ```

3. 방화벽 확인:
   - 443 포트 허용 확인

### API 응답 타임아웃

**해결**:
```json
{
  "api_timeout": 120
}
```

## 기타 문제

### Unicode 인코딩 에러

**증상**:
```
UnicodeEncodeError: 'ascii' codec can't encode characters
```

**해결**:
```bash
export PYTHONIOENCODING=utf-8
```

### 프로세스 좀비화

**해결**:
```bash
# 좀비 프로세스 찾기
ps aux | grep better-llm

# 종료
pkill -9 -f better-llm

# 또는
kill -9 <PID>
```

### 캐시 손상

**해결**:
```bash
# 캐시 디렉토리 삭제 (재생성됨)
rm -rf ~/.cache/better-llm/
```

## 디버깅 팁

### 상세 로그 확인

```bash
# DEBUG 레벨로 실행
export LOG_LEVEL=DEBUG
better-llm-cli -v "작업 설명"

# 실시간 로그 모니터링
tail -f logs/better-llm.log
```

### JSON 로그 파싱

```bash
# 에러만 필터링
cat logs/better-llm.log | jq 'select(.level == "error")'

# 특정 Worker 로그만
cat logs/better-llm.log | jq 'select(.worker_name == "planner")'

# 에러 통계
cat logs/better-llm-error.log | jq -r '.error_code' | sort | uniq -c
```

### 메트릭 분석

```bash
# Worker 평균 실행 시간
cat metrics.jsonl | jq -r 'select(.metric_name == "worker_duration") | [.worker_name, .value] | @tsv'

# API 호출 횟수
cat metrics.jsonl | jq -r 'select(.metric_name == "api_call") | .value' | wc -l
```

## 도움 받기

문제가 해결되지 않으면:

1. **GitHub Issues**: [https://github.com/simdaseul/better-llm/issues](https://github.com/simdaseul/better-llm/issues)
2. **Discussions**: [https://github.com/simdaseul/better-llm/discussions](https://github.com/simdaseul/better-llm/discussions)

이슈 등록 시 포함할 정보:
- 에러 메시지 전문
- 로그 파일 스니펫 (`logs/better-llm-error.log`)
- 재현 방법
- 환경 정보 (OS, Python 버전, Better-LLM 버전)
- 설정 파일 (`config/agent_config.json`, `config/system_config.json`)
