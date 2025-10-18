"""
챗 매니저 - 에이전트 라우팅 및 종료 조건 관리

ChatManager: 다음 응답할 에이전트를 결정하는 중앙 조정자
"""

from typing import List, Tuple, Optional, Dict
import re
import logging

from .models import Message
from .agents import Agent

logger = logging.getLogger(__name__)


class ChatManager:
    """
    대화 흐름을 관리하고 다음 에이전트를 선택하는 매니저

    규칙 기반 라우팅을 사용하여 키워드 매칭, 에이전트 명시 요청,
    순차 진행 등을 처리합니다.

    Attributes:
        agents: 사용 가능한 에이전트 딕셔너리 (name -> Agent)
        max_turns: 최대 턴 수 (무한 루프 방지)
        max_consecutive: 동일 에이전트 최대 연속 실행 횟수
    """

    # 키워드 기반 라우팅 규칙
    KEYWORD_RULES = {
        "planner": ["plan", "design", "계획", "설계", "분석"],
        "coder": ["code", "implement", "구현", "작성", "개발", "코딩"],
        "tester": ["test", "verify", "테스트", "검증", "확인"],
    }

    # 순차 진행 규칙
    SEQUENCE_RULES = {
        "planner": "coder",
        "coder": "tester",
        "tester": "TERMINATE"
    }

    def __init__(
        self,
        agents: Dict[str, Agent],
        max_turns: int = 50,
        max_consecutive: int = 5
    ):
        """
        Args:
            agents: 에이전트 딕셔너리 (name -> Agent)
            max_turns: 최대 턴 수 (기본값: 50)
            max_consecutive: 동일 에이전트 최대 연속 실행 횟수 (기본값: 5)
        """
        self.agents = agents
        self.max_turns = max_turns
        self.max_consecutive = max_consecutive

    def select_next_agent(self, history: List[Message]) -> str:
        """
        대화 히스토리를 기반으로 다음 에이전트 선택

        우선순위:
        1. 종료 조건 확인
        2. 명시적 에이전트 요청 (@agent_name)
        3. TERMINATE 키워드 확인
        4. 키워드 기반 라우팅
        5. 순차 진행 규칙
        6. 기본값 (planner)

        Args:
            history: 전체 대화 히스토리

        Returns:
            다음 에이전트 이름, "TERMINATE", 또는 "USER_INPUT"
        """
        # 1. 종료 조건 확인
        should_terminate, reason = self.should_terminate(history)
        if should_terminate:
            logger.info(f"🛑 종료 조건 충족: {reason}")
            return "TERMINATE"

        # 2. 마지막 메시지 확인
        last_message = history[-1] if history else None
        if not last_message:
            # 첫 시작: planner로 시작
            return "planner"

        # 3. 명시적 에이전트 요청 확인 (@agent_name)
        explicit_agent = self._extract_explicit_agent(last_message.content)
        if explicit_agent:
            if explicit_agent in self.agents:
                logger.info(f"👉 명시적 요청: {explicit_agent}")
                return explicit_agent
            else:
                logger.warning(f"⚠️  알 수 없는 에이전트: {explicit_agent}")

        # 4. TERMINATE 키워드 확인
        if self._contains_terminate_keyword(last_message.content):
            logger.info("🛑 TERMINATE 키워드 감지")
            return "TERMINATE"

        # 5. 키워드 기반 라우팅
        keyword_agent = self._match_keywords(last_message.content)
        if keyword_agent:
            logger.info(f"🔍 키워드 매칭: {keyword_agent}")
            return keyword_agent

        # 6. 순차 진행 규칙
        last_agent = self._get_last_agent_name(history)
        if last_agent and last_agent in self.SEQUENCE_RULES:
            next_agent = self.SEQUENCE_RULES[last_agent]
            logger.info(f"➡️  순차 진행: {last_agent} → {next_agent}")
            return next_agent

        # 7. 기본값: planner
        logger.info("🔄 기본값: planner")
        return "planner"

    def should_terminate(self, history: List[Message]) -> Tuple[bool, str]:
        """
        종료 조건 확인

        종료 조건:
        1. 최대 턴 수 도달
        2. 동일 에이전트 연속 실행 제한 초과
        3. 마지막 메시지에 TERMINATE 포함

        Args:
            history: 대화 히스토리

        Returns:
            (종료 여부, 종료 이유)
        """
        if not history:
            return False, ""

        # 1. 최대 턴 수 확인
        agent_turns = sum(1 for msg in history if msg.role == "agent")
        if agent_turns >= self.max_turns:
            return True, f"최대 턴 수 도달 ({self.max_turns}턴)"

        # 2. 동일 에이전트 연속 실행 확인
        consecutive_count = self._count_consecutive_agents(history)
        if consecutive_count >= self.max_consecutive:
            last_agent = self._get_last_agent_name(history)
            return True, f"동일 에이전트({last_agent}) 연속 {consecutive_count}회 실행"

        # 3. TERMINATE 키워드 확인
        last_message = history[-1]
        if self._contains_terminate_keyword(last_message.content):
            return True, "TERMINATE 키워드 감지"

        return False, ""

    def _extract_explicit_agent(self, content: str) -> Optional[str]:
        """
        메시지에서 명시적 에이전트 요청 추출 (@agent_name)

        Args:
            content: 메시지 내용

        Returns:
            에이전트 이름 또는 None
        """
        # @planner, @coder, @tester 패턴 찾기
        pattern = r'@(\w+)'
        matches = re.findall(pattern, content.lower())

        if matches:
            # 첫 번째 매칭된 에이전트 이름 반환
            agent_name = matches[0]
            if agent_name in self.agents:
                return agent_name

        return None

    def _contains_terminate_keyword(self, content: str) -> bool:
        """
        TERMINATE 키워드 포함 여부 확인

        Args:
            content: 메시지 내용

        Returns:
            TERMINATE 포함 여부
        """
        terminate_keywords = ["TERMINATE", "terminate", "작업 완료", "완료됨"]
        content_lower = content.lower()

        return any(keyword.lower() in content_lower for keyword in terminate_keywords)

    def _match_keywords(self, content: str) -> Optional[str]:
        """
        키워드 매칭으로 에이전트 선택

        Args:
            content: 메시지 내용

        Returns:
            매칭된 에이전트 이름 또는 None
        """
        content_lower = content.lower()

        for agent_name, keywords in self.KEYWORD_RULES.items():
            for keyword in keywords:
                if keyword.lower() in content_lower:
                    return agent_name

        return None

    def _get_last_agent_name(self, history: List[Message]) -> Optional[str]:
        """
        마지막 에이전트 이름 조회

        Args:
            history: 대화 히스토리

        Returns:
            마지막 에이전트 이름 또는 None
        """
        for msg in reversed(history):
            if msg.role == "agent" and msg.agent_name:
                return msg.agent_name
        return None

    def _count_consecutive_agents(self, history: List[Message]) -> int:
        """
        동일 에이전트 연속 실행 횟수 계산

        Args:
            history: 대화 히스토리

        Returns:
            연속 실행 횟수
        """
        if not history:
            return 0

        last_agent = self._get_last_agent_name(history)
        if not last_agent:
            return 0

        count = 0
        for msg in reversed(history):
            if msg.role == "agent" and msg.agent_name == last_agent:
                count += 1
            elif msg.role == "agent":
                # 다른 에이전트 발견 시 중단
                break

        return count

    def __repr__(self) -> str:
        return (
            f"ChatManager(agents={len(self.agents)}, "
            f"max_turns={self.max_turns}, "
            f"max_consecutive={self.max_consecutive})"
        )
