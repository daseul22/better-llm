#!/usr/bin/env python3
"""
그룹 챗 오케스트레이션 시스템 - Streamlit 웹 UI

실시간 스트리밍, 세션 히스토리 조회 등의 기능을 제공하는 웹 인터페이스
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import streamlit as st

from src.models import SessionResult
from src.manager_agent import ManagerAgent
from src.worker_agent import WorkerAgent
from src.conversation import ConversationHistory
from src.chat_manager import ChatManager
from src.utils import (
    load_agent_config,
    generate_session_id,
    save_session_history,
    validate_environment
)


# 페이지 설정
st.set_page_config(
    page_title="Group Chat Orchestration",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)


def init_session_state():
    """세션 상태 초기화"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "session_id" not in st.session_state:
        st.session_state.session_id = generate_session_id()
    if "orchestrator_ready" not in st.session_state:
        st.session_state.orchestrator_ready = False


def load_session_files():
    """저장된 세션 파일 목록 로드"""
    sessions_dir = Path("sessions")
    if not sessions_dir.exists():
        return []

    session_files = list(sessions_dir.glob("session_*.json"))
    session_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    return session_files[:10]  # 최근 10개만


async def run_orchestration(user_request: str):
    """오케스트레이션 실행"""
    try:
        # 환경 검증
        validate_environment()

        # 매니저 에이전트 초기화
        manager = ManagerAgent()

        # 워커 에이전트 설정 로드
        config_path = Path("config/agent_config.json")
        worker_configs = load_agent_config(config_path)

        # 워커 에이전트 초기화
        workers = {}
        for config in worker_configs:
            worker = WorkerAgent(config)
            workers[config.name] = worker

        # 챗 매니저
        chat_manager = ChatManager(workers)

        # 대화 히스토리
        history = ConversationHistory()

        # 세션 ID
        session_id = st.session_state.session_id

        # 헤더 정보
        st.info(f"🆔 세션: {session_id} | 👔 매니저: ManagerAgent | 👷 워커: {', '.join(workers.keys())}")

        # 사용자 요청을 히스토리에 추가
        history.add_message("user", user_request)

        # 메시지 표시 영역
        status_placeholder = st.empty()
        output_placeholder = st.empty()

        turn = 0
        max_turns = 20

        while turn < max_turns:
            turn += 1

            status_placeholder.info(f"🔄 Turn {turn} 진행 중...")

            # 1. 매니저가 작업 분석 및 계획
            with output_placeholder.container():
                st.markdown(f"### [Turn {turn}] 👔 ManagerAgent")
                manager_container = st.empty()

                manager_response = await manager.analyze_and_plan(history.get_history())
                manager_container.markdown(manager_response)

                # 히스토리에 추가
                history.add_message("manager", manager_response)

            # 2. 종료 조건 확인
            if "TERMINATE" in manager_response.upper() or "작업 완료" in manager_response:
                status_placeholder.success("✅ 작업이 완료되었습니다!")
                break

            # 3. 다음 워커 선택
            next_worker = extract_worker_assignment(manager_response, workers)

            if not next_worker:
                status_placeholder.warning("⚠️ 워커를 지정하지 않았습니다. 계속 진행합니다.")
                continue

            if next_worker not in workers:
                status_placeholder.warning(f"⚠️ 알 수 없는 워커: {next_worker}")
                continue

            # 4. 워커 실행
            worker = workers[next_worker]
            emoji = get_agent_emoji(next_worker)

            with output_placeholder.container():
                st.markdown(f"### [Turn {turn}] {emoji} {worker.config.role} ({next_worker})")
                worker_container = st.empty()

                task_description = extract_task_for_worker(manager_response, next_worker)

                try:
                    worker_response = ""
                    async for chunk in worker.execute_task(task_description):
                        worker_response += chunk
                        worker_container.markdown(worker_response)

                    # 히스토리에 추가
                    history.add_message("agent", worker_response, next_worker)

                except Exception as e:
                    error_msg = f"❌ 워커 실행 실패: {e}"
                    worker_container.error(error_msg)
                    history.add_message("agent", error_msg, next_worker)

        # 최대 턴 수 도달
        if turn >= max_turns:
            status_placeholder.warning(f"⚠️ 최대 턴 수({max_turns})에 도달했습니다.")

        # 세션 저장
        result = SessionResult(status="completed")
        sessions_dir = Path("sessions")
        filepath = save_session_history(
            session_id,
            user_request,
            history,
            result.to_dict(),
            sessions_dir
        )

        st.success(f"💾 세션이 저장되었습니다: {filepath.name}")

        return history

    except Exception as e:
        st.error(f"❌ 오류 발생: {e}")
        return None


def extract_worker_assignment(manager_response: str, workers: dict) -> Optional[str]:
    """매니저 응답에서 @worker_name 추출"""
    import re
    pattern = r'@(\w+)'
    matches = re.findall(pattern, manager_response.lower())

    if matches:
        for match in matches:
            if match in workers:
                return match
    return None


def extract_task_for_worker(manager_response: str, worker_name: str) -> str:
    """매니저 응답에서 워커에게 전달할 작업 추출"""
    import re
    pattern = rf'@{worker_name}\s+(.+?)(?=@\w+|$)'
    match = re.search(pattern, manager_response, re.DOTALL | re.IGNORECASE)

    if match:
        return match.group(1).strip()
    return manager_response


def get_agent_emoji(agent_name: str) -> str:
    """에이전트별 이모지 반환"""
    emoji_map = {
        "planner": "📋",
        "coder": "💻",
        "tester": "🧪"
    }
    return emoji_map.get(agent_name, "🤖")


def main():
    """메인 함수"""
    init_session_state()

    # 사이드바
    with st.sidebar:
        st.title("🤖 Group Chat Orchestration")
        st.markdown("---")

        # 새 세션 버튼
        if st.button("🔄 새 세션 시작"):
            st.session_state.session_id = generate_session_id()
            st.session_state.messages = []
            st.rerun()

        st.markdown("---")
        st.subheader("📜 최근 세션")

        # 최근 세션 파일 표시
        session_files = load_session_files()
        if session_files:
            for session_file in session_files:
                with st.expander(f"📄 {session_file.stem}"):
                    try:
                        with open(session_file, 'r', encoding='utf-8') as f:
                            session_data = json.load(f)
                            st.json(session_data)
                    except Exception as e:
                        st.error(f"로드 실패: {e}")
        else:
            st.info("저장된 세션이 없습니다.")

        st.markdown("---")
        st.caption(f"세션 ID: {st.session_state.session_id}")

    # 메인 영역
    st.title("🤖 Multi-Agent Orchestration System")
    st.markdown("여러 AI 에이전트가 협업하여 복잡한 소프트웨어 개발 작업을 자동화합니다.")

    # 사용자 입력
    user_request = st.text_area(
        "작업 요청을 입력하세요:",
        placeholder="예: 'FastAPI로 간단한 CRUD API를 작성해줘. 파일명은 api.py로 해줘.'",
        height=100
    )

    col1, col2 = st.columns([1, 5])
    with col1:
        run_button = st.button("🚀 실행", type="primary", use_container_width=True)
    with col2:
        st.caption("💡 팁: @planner, @coder, @tester 에이전트가 자동으로 협업합니다.")

    # 실행
    if run_button and user_request:
        with st.spinner("오케스트레이션 실행 중..."):
            asyncio.run(run_orchestration(user_request))


if __name__ == "__main__":
    main()
