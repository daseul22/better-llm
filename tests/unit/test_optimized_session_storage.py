"""
최적화된 세션 저장소 단위 테스트
"""

import pytest
import tempfile
import shutil
import gzip
import json
from pathlib import Path
from datetime import datetime

from src.infrastructure.storage.optimized_session_storage import OptimizedSessionRepository
from src.domain.models import SessionResult, SessionStatus, SessionSearchCriteria, Message
from src.domain.services import ConversationHistory


@pytest.fixture
def temp_sessions_dir():
    """임시 세션 디렉토리 생성"""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    # 테스트 후 삭제
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_history():
    """샘플 대화 히스토리"""
    history = ConversationHistory(max_length=10)
    history.add_message(Message(
        role="user",
        content="Create a hello world function",
        timestamp=datetime.now()
    ))
    history.add_message(Message(
        role="agent",
        content="I'll create the function",
        agent_name="planner",
        timestamp=datetime.now()
    ))
    return history


@pytest.fixture
def sample_result():
    """샘플 세션 결과"""
    return SessionResult(
        status=SessionStatus.COMPLETED,
        files_modified=["main.py"],
        tests_passed=True
    )


def test_optimized_repository_initialization(temp_sessions_dir):
    """최적화된 저장소 초기화 테스트"""
    repo = OptimizedSessionRepository(
        sessions_dir=temp_sessions_dir,
        enable_compression=True,
        enable_background_save=True
    )

    assert repo.sessions_dir == temp_sessions_dir
    assert repo.enable_compression is True
    assert repo.enable_background_save is True
    assert repo._worker_thread is not None
    assert repo._worker_thread.is_alive()

    repo.stop()


def test_save_with_compression(temp_sessions_dir, sample_history, sample_result):
    """압축 저장 테스트"""
    repo = OptimizedSessionRepository(
        sessions_dir=temp_sessions_dir,
        enable_compression=True,
        enable_background_save=False  # 동기 저장 (테스트 용이성)
    )

    session_id = "test_session_001"
    user_request = "Create hello world"

    # 세션 저장
    filepath = repo.save(session_id, user_request, sample_history, sample_result)

    # 파일이 .json.gz 확장자를 가지는지 확인
    assert filepath.suffix == ".gz"
    assert filepath.exists()

    # gzip으로 압축되었는지 확인
    with gzip.open(filepath, 'rt', encoding='utf-8') as f:
        data = json.load(f)
        assert data["session_id"] == session_id
        assert data["user_request"] == user_request


def test_save_without_compression(temp_sessions_dir, sample_history, sample_result):
    """비압축 저장 테스트"""
    repo = OptimizedSessionRepository(
        sessions_dir=temp_sessions_dir,
        enable_compression=False,
        enable_background_save=False
    )

    session_id = "test_session_002"
    user_request = "Create hello world"

    # 세션 저장
    filepath = repo.save(session_id, user_request, sample_history, sample_result)

    # 파일이 .json 확장자를 가지는지 확인
    assert filepath.suffix == ".json"
    assert filepath.exists()

    # 일반 JSON 파일인지 확인
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
        assert data["session_id"] == session_id


def test_background_save(temp_sessions_dir, sample_history, sample_result):
    """백그라운드 저장 테스트"""
    import time

    repo = OptimizedSessionRepository(
        sessions_dir=temp_sessions_dir,
        enable_compression=False,
        enable_background_save=True
    )

    session_id = "test_session_003"
    user_request = "Create hello world"

    # 세션 저장 (비동기)
    filepath = repo.save(session_id, user_request, sample_history, sample_result)

    # 백그라운드 저장 대기
    time.sleep(1.0)

    # 파일이 저장되었는지 확인
    assert filepath.exists()

    repo.stop()


def test_load_compressed_session(temp_sessions_dir, sample_history, sample_result):
    """압축된 세션 로드 테스트"""
    repo = OptimizedSessionRepository(
        sessions_dir=temp_sessions_dir,
        enable_compression=True,
        enable_background_save=False
    )

    session_id = "test_session_004"
    user_request = "Create hello world"

    # 세션 저장
    repo.save(session_id, user_request, sample_history, sample_result)

    # 세션 로드
    loaded_history = repo.load(session_id)

    assert loaded_history is not None
    assert len(loaded_history.messages) == len(sample_history.messages)
    assert loaded_history.messages[0].content == sample_history.messages[0].content


def test_load_nonexistent_session(temp_sessions_dir):
    """존재하지 않는 세션 로드 테스트"""
    repo = OptimizedSessionRepository(
        sessions_dir=temp_sessions_dir,
        enable_compression=True,
        enable_background_save=False
    )

    # 존재하지 않는 세션 로드
    loaded_history = repo.load("nonexistent_session")

    assert loaded_history is None


def test_search_sessions(temp_sessions_dir, sample_history, sample_result):
    """세션 검색 테스트"""
    repo = OptimizedSessionRepository(
        sessions_dir=temp_sessions_dir,
        enable_compression=False,
        enable_background_save=False
    )

    # 여러 세션 저장
    repo.save("session_001", "Create hello world", sample_history, sample_result)
    repo.save("session_002", "Create goodbye function", sample_history, sample_result)
    repo.save("session_003", "Create test cases", sample_history, sample_result)

    # 키워드 검색
    criteria = SessionSearchCriteria(keyword="hello", limit=10)
    results = repo.search_sessions(criteria)

    assert len(results) >= 1
    assert any("hello" in r.user_request.lower() for r in results)


def test_get_session_detail(temp_sessions_dir, sample_history, sample_result):
    """세션 상세 정보 조회 테스트"""
    repo = OptimizedSessionRepository(
        sessions_dir=temp_sessions_dir,
        enable_compression=True,
        enable_background_save=False
    )

    session_id = "test_session_005"
    user_request = "Create hello world"

    # 세션 저장
    repo.save(session_id, user_request, sample_history, sample_result)

    # 세션 상세 조회
    detail = repo.get_session_detail(session_id)

    assert detail is not None
    assert detail.metadata.session_id == session_id
    assert detail.metadata.user_request == user_request
    assert len(detail.messages) == len(sample_history.messages)


def test_list_sessions(temp_sessions_dir, sample_history, sample_result):
    """세션 목록 조회 테스트"""
    repo = OptimizedSessionRepository(
        sessions_dir=temp_sessions_dir,
        enable_compression=False,
        enable_background_save=False
    )

    # 여러 세션 저장
    for i in range(5):
        repo.save(f"session_{i:03d}", f"Task {i}", sample_history, sample_result)

    # 세션 목록 조회
    sessions = repo.list_sessions(limit=10)

    assert len(sessions) == 5


def test_delete_session(temp_sessions_dir, sample_history, sample_result):
    """세션 삭제 테스트"""
    repo = OptimizedSessionRepository(
        sessions_dir=temp_sessions_dir,
        enable_compression=False,
        enable_background_save=False
    )

    session_id = "test_session_006"
    user_request = "Create hello world"

    # 세션 저장
    repo.save(session_id, user_request, sample_history, sample_result)

    # 삭제 전 존재 확인
    assert repo.load(session_id) is not None

    # 세션 삭제
    result = repo.delete_session(session_id)
    assert result is True

    # 삭제 후 존재하지 않음 확인
    assert repo.load(session_id) is None


def test_compression_ratio(temp_sessions_dir, sample_result):
    """압축 비율 테스트"""
    repo_compressed = OptimizedSessionRepository(
        sessions_dir=temp_sessions_dir / "compressed",
        enable_compression=True,
        enable_background_save=False
    )

    repo_uncompressed = OptimizedSessionRepository(
        sessions_dir=temp_sessions_dir / "uncompressed",
        enable_compression=False,
        enable_background_save=False
    )

    # 큰 히스토리 생성
    large_history = ConversationHistory(max_length=100)
    for i in range(50):
        large_history.add_message(Message(
            role="user",
            content=f"This is message {i} with some content to compress",
            timestamp=datetime.now()
        ))

    session_id = "large_session"
    user_request = "Large session test"

    # 압축/비압축 저장
    filepath_compressed = repo_compressed.save(
        session_id, user_request, large_history, sample_result
    )
    filepath_uncompressed = repo_uncompressed.save(
        session_id, user_request, large_history, sample_result
    )

    # 파일 크기 비교 (압축 파일이 더 작아야 함)
    size_compressed = filepath_compressed.stat().st_size
    size_uncompressed = filepath_uncompressed.stat().st_size

    assert size_compressed < size_uncompressed

    # 압축률 계산
    compression_ratio = (1 - size_compressed / size_uncompressed) * 100
    print(f"Compression ratio: {compression_ratio:.1f}%")

    # 최소 30% 압축 기대
    assert compression_ratio > 30


def test_context_manager(temp_sessions_dir, sample_history, sample_result):
    """Context manager 테스트"""
    import time

    session_id = "test_session_007"
    user_request = "Create hello world"

    with OptimizedSessionRepository(
        sessions_dir=temp_sessions_dir,
        enable_compression=False,
        enable_background_save=True
    ) as repo:
        repo.save(session_id, user_request, sample_history, sample_result)
        time.sleep(0.5)

    # Context manager 종료 후 백그라운드 워커도 종료되어야 함
    time.sleep(1.0)

    # 파일이 저장되었는지 확인
    files = list(temp_sessions_dir.glob(f"session_{session_id}_*.json"))
    assert len(files) >= 1


def test_stop_with_pending_saves(temp_sessions_dir, sample_history, sample_result):
    """대기 중인 저장 작업이 있을 때 종료 테스트"""
    repo = OptimizedSessionRepository(
        sessions_dir=temp_sessions_dir,
        enable_compression=False,
        enable_background_save=True
    )

    # 여러 세션 빠르게 저장
    for i in range(10):
        repo.save(f"session_{i:03d}", f"Task {i}", sample_history, sample_result)

    # 즉시 종료 (대기 중인 작업 처리)
    repo.stop(timeout=5.0)

    # 모든 파일이 저장되었는지 확인
    files = list(temp_sessions_dir.glob("session_*.json"))
    assert len(files) == 10
