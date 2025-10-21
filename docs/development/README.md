# 개발 문서

Better-LLM 프로젝트의 개발 히스토리, 구현 상세, 리팩토링 기록을 담고 있습니다.

## 📜 개발 히스토리

- [**개발 히스토리**](history.md) - 프로젝트 전체 개발 히스토리 및 주요 마일스톤

## 🚀 구현 상세

새로운 기능 및 개선 사항의 구현 상세를 기록합니다.

- [**CLI 출력 개선**](implementations/cli-output.md) - Rich 라이브러리 기반 CLI UI 개선
- [**워크플로우 비주얼라이저**](implementations/workflow-visualizer.md) - TUI 워크플로우 시각화 구현
- [**테스트 보고서 UI**](implementations/test-report-ui.md) - TUI UI/UX 개선 및 테스트 보고서

## 🔧 리팩토링 기록

코드 품질 개선 및 아키텍처 변경 기록입니다.

- [**Import 수정**](refactoring/import-fixes.md) - Import 경로 문제 해결 및 개선
- [**Phase 1 리팩토링**](refactoring/phase1.md) - 초기 리팩토링 작업 요약
- [**구현 요약**](refactoring/implementation-summary.md) - 전체 구현 요약 및 통합

## 관련 문서

- [아키텍처 결정 기록 (ADR)](../adr/0000-template.md) - 주요 설계 결정 배경
- [아키텍처 개요](../architecture.md) - 시스템 아키텍처 설명
- [에러 가이드라인](../ERROR_HANDLING_GUIDELINES.md) - 에러 처리 모범 사례
- [Import 가이드라인](../IMPORT_GUIDELINES.md) - Import 규칙 및 패턴

## 기여하기

개발 문서를 추가하거나 수정하려면:

1. 적절한 디렉토리 선택 (`implementations/` 또는 `refactoring/`)
2. Markdown 파일 작성 (구조화된 포맷 사용)
3. 이 README.md에 링크 추가
4. Pull Request 생성

### 문서 작성 가이드

각 구현 문서는 다음 섹션을 포함해야 합니다:

- **개요**: 무엇을 했는지
- **구현 내용**: 어떻게 구현했는지
- **변경 파일 목록**: 어떤 파일이 변경되었는지
- **테스트 결과**: 어떻게 검증했는지
- **다음 단계**: 향후 개선 사항
