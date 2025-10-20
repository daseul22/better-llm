# Storage

세션 저장소 API 문서입니다.

## SessionRepository

::: src.infrastructure.storage.session_storage.SessionRepository
    options:
      show_source: true
      show_root_heading: true
      members:
        - __init__
        - save
        - load
        - list_all
        - delete

## OptimizedSessionRepository

::: src.infrastructure.storage.optimized_session_storage.OptimizedSessionRepository
    options:
      show_source: true
      show_root_heading: true
      members:
        - __init__
        - save
        - load
        - stop

최적화된 세션 저장소로, 다음 기능을 지원합니다:

- **압축 저장**: gzip으로 파일 크기 30-50% 절감
- **백그라운드 저장**: 별도 스레드에서 비동기 저장
- **큐 기반 버퍼링**: 저장 요청을 큐에 버퍼링하여 성능 향상
