"""
Project Memory Bank 통합 테스트

간단한 저장 및 검색 테스트
"""

from datetime import datetime
from src.domain.models import Memory, MemoryQuery
from src.infrastructure.memory import EmbeddingService, FAISSMemoryBankRepository


def test_memory_bank():
    """메모리 뱅크 기본 기능 테스트"""
    print("=" * 60)
    print("Project Memory Bank 테스트 시작")
    print("=" * 60)

    # 1. Repository 초기화
    print("\n[1] Repository 초기화...")
    embedding_service = EmbeddingService()
    repo = FAISSMemoryBankRepository(embedding_service=embedding_service)
    repo.clear()  # 테스트용 초기화
    print(f"✅ Repository 초기화 완료 (dimension: {embedding_service.dimension})")

    # 2. 메모리 저장
    print("\n[2] 메모리 저장...")
    memories = [
        Memory(
            id="session-001",
            task_description="FastAPI로 CRUD API 구현해줘",
            session_summary="FastAPI를 사용하여 /users 엔드포인트를 구현했습니다. GET, POST, PUT, DELETE를 지원합니다.",
            files_modified=["src/api/users.py", "src/models/user.py"],
            tags=["FastAPI", "CRUD", "REST API"],
        ),
        Memory(
            id="session-002",
            task_description="SQLAlchemy 모델을 작성해줘",
            session_summary="SQLAlchemy ORM을 사용하여 User 모델을 정의했습니다. PostgreSQL과 호환됩니다.",
            files_modified=["src/models/user.py", "src/db/base.py"],
            tags=["SQLAlchemy", "ORM", "Database"],
        ),
        Memory(
            id="session-003",
            task_description="React 컴포넌트를 만들어줘",
            session_summary="React 함수형 컴포넌트로 UserList를 구현했습니다. useState와 useEffect를 활용합니다.",
            files_modified=["src/components/UserList.tsx"],
            tags=["React", "TypeScript", "Frontend"],
        ),
    ]

    for memory in memories:
        repo.save_memory(memory)
        print(f"  ✅ 저장: {memory.id} - {memory.task_description}")

    print(f"\n총 {repo.count()}개 메모리 저장 완료")

    # 3. 유사도 검색 테스트
    print("\n[3] 유사도 검색 테스트...")
    queries = [
        "FastAPI API 만들기",
        "데이터베이스 ORM",
        "프론트엔드 컴포넌트",
    ]

    for query_text in queries:
        print(f"\n[검색] '{query_text}'")
        query = MemoryQuery(query_text=query_text, top_k=2, threshold=0.3)
        results = repo.search(query)

        if results:
            for i, result in enumerate(results, 1):
                print(f"  {i}. [{result.similarity_score:.3f}] {result.memory.task_description}")
                print(f"     파일: {', '.join(result.memory.files_modified)}")
        else:
            print("  (검색 결과 없음)")

    # 4. ID로 조회 테스트
    print("\n[4] ID로 조회 테스트...")
    memory = repo.get_by_id("session-001")
    if memory:
        print(f"✅ 조회 성공: {memory.task_description}")
    else:
        print("❌ 조회 실패")

    # 5. 삭제 테스트
    print("\n[5] 삭제 테스트...")
    success = repo.delete("session-003")
    print(f"{'✅ 삭제 성공' if success else '❌ 삭제 실패'}: session-003")
    print(f"남은 메모리: {repo.count()}개")

    print("\n" + "=" * 60)
    print("테스트 완료!")
    print("=" * 60)


if __name__ == "__main__":
    test_memory_bank()
