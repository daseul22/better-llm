"""
컨텍스트 압축 서비스

ContextCompressor: 대화 히스토리를 압축하여 컨텍스트 윈도우 효율성 향상

핵심 아이디어:
1. 오래된 메시지를 파일로 저장
2. 메시지를 메타데이터(파일 참조)로 대체
3. 필요 시 Worker가 read 도구로 원본 읽기
"""

from typing import List, Optional, Tuple
from datetime import datetime
from pathlib import Path
import json

from ..models import Message
from ...infrastructure.logging import get_logger

logger = get_logger(__name__, component="ContextCompressor")


class ContextCompressor:
    """
    컨텍스트 압축 관리 서비스

    대화 히스토리에서 오래된 메시지를 파일로 저장하고,
    메타데이터 참조로 대체하여 컨텍스트 윈도우 효율성을 향상시킵니다.

    압축 전략:
    - 첫 번째 사용자 메시지는 항상 보존 (컨텍스트 유지)
    - 오래된 메시지부터 압축
    - 압축된 메시지: 파일 저장 + 메타데이터 참조로 대체

    Attributes:
        compressed_dir: 압축된 메시지 저장 디렉토리
        compression_threshold: 압축 시작 임계값 (토큰 비율, 0.0-1.0)
    """

    def __init__(
        self,
        compressed_dir: Path,
        compression_threshold: float = 0.85
    ):
        """
        Args:
            compressed_dir: 압축된 메시지 저장 디렉토리
            compression_threshold: 압축 시작 임계값 (기본값: 85%)
        """
        self.compressed_dir = Path(compressed_dir)
        self.compression_threshold = compression_threshold

        # 디렉토리 생성
        self.compressed_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            "ContextCompressor initialized",
            compressed_dir=str(self.compressed_dir),
            compression_threshold=f"{compression_threshold*100:.0f}%"
        )

    def should_compress(
        self,
        current_tokens: int,
        max_tokens: int
    ) -> bool:
        """
        압축이 필요한지 판단

        Args:
            current_tokens: 현재 토큰 수
            max_tokens: 최대 토큰 수

        Returns:
            True: 압축 필요, False: 압축 불필요
        """
        usage_ratio = current_tokens / max_tokens
        should_compress = usage_ratio >= self.compression_threshold

        if should_compress:
            logger.info(
                "Context compression triggered",
                current_tokens=current_tokens,
                max_tokens=max_tokens,
                usage_ratio=f"{usage_ratio*100:.1f}%",
                threshold=f"{self.compression_threshold*100:.0f}%"
            )

        return should_compress

    def compress_messages(
        self,
        messages: List[Message],
        target_reduction_ratio: float = 0.3
    ) -> Tuple[List[Message], int]:
        """
        메시지 리스트를 압축

        압축 전략:
        1. 첫 번째 사용자 메시지는 항상 보존
        2. 오래된 메시지부터 압축 (target_reduction_ratio만큼)
        3. 압축된 메시지: 파일 저장 + 메타데이터 참조로 대체

        Args:
            messages: 압축할 메시지 리스트
            target_reduction_ratio: 목표 압축 비율 (기본값: 30% 압축)

        Returns:
            (압축된 메시지 리스트, 압축된 메시지 개수)

        Example:
            >>> compressor = ContextCompressor(compressed_dir=Path("~/.better-llm/project/compressed"))
            >>> compressed_messages, count = compressor.compress_messages(history)
            >>> print(f"{count} messages compressed")
        """
        if not messages:
            return messages, 0

        # 첫 번째 사용자 메시지 찾기
        first_user_msg_idx = next(
            (i for i, msg in enumerate(messages) if msg.role == "user"),
            None
        )

        # 압축 대상 계산
        total_messages = len(messages)
        target_compressed_count = int(total_messages * target_reduction_ratio)

        # 최소 1개는 압축, 첫 메시지는 제외
        if first_user_msg_idx is not None:
            # 첫 사용자 메시지 이후부터 압축 대상 선택
            compressible_start = first_user_msg_idx + 1
        else:
            compressible_start = 0

        # 압축 대상: 오래된 메시지부터 (첫 메시지 제외)
        messages_to_compress_indices = list(range(
            compressible_start,
            min(compressible_start + target_compressed_count, total_messages)
        ))

        logger.info(
            "Starting message compression",
            total_messages=total_messages,
            target_compressed_count=target_compressed_count,
            first_user_msg_idx=first_user_msg_idx,
            compressible_range=f"{compressible_start} to {compressible_start + target_compressed_count}"
        )

        # 압축 수행
        compressed_messages = []
        compressed_count = 0

        for i, msg in enumerate(messages):
            if i in messages_to_compress_indices:
                # 압축 대상: 파일 저장 + 메타데이터 참조로 대체
                compressed_msg = self._compress_message(msg)
                compressed_messages.append(compressed_msg)
                compressed_count += 1
            else:
                # 압축 대상 아님: 그대로 유지
                compressed_messages.append(msg)

        logger.info(
            "Message compression completed",
            compressed_count=compressed_count,
            original_messages=total_messages,
            compressed_messages=len(compressed_messages)
        )

        return compressed_messages, compressed_count

    def _compress_message(self, msg: Message) -> Message:
        """
        단일 메시지 압축

        Args:
            msg: 압축할 메시지

        Returns:
            압축된 메시지 (메타데이터 참조로 대체)
        """
        # 1. 파일명 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        role_prefix = msg.role
        if msg.agent_name:
            role_prefix = f"{msg.role}_{msg.agent_name}"

        filename = f"{role_prefix}_{timestamp}.txt"
        file_path = self.compressed_dir / filename

        # 2. 원본 메시지를 파일로 저장
        self._save_message_to_file(msg, file_path)

        # 3. 메타데이터 참조 생성
        compressed_content = self._create_compressed_reference(msg, file_path)

        # 4. 새 메시지 생성 (압축된 내용)
        compressed_msg = Message(
            role=msg.role,
            content=compressed_content,
            agent_name=msg.agent_name,
            timestamp=msg.timestamp
        )

        logger.debug(
            "Message compressed",
            original_length=len(msg.content),
            compressed_length=len(compressed_content),
            reduction_ratio=f"{(1 - len(compressed_content)/len(msg.content))*100:.1f}%",
            file_path=str(file_path)
        )

        return compressed_msg

    def _save_message_to_file(self, msg: Message, file_path: Path) -> None:
        """
        메시지를 파일로 저장

        Args:
            msg: 저장할 메시지
            file_path: 저장 경로
        """
        try:
            # JSON 형식으로 저장 (메타데이터 포함)
            data = {
                "role": msg.role,
                "content": msg.content,
                "agent_name": msg.agent_name,
                "timestamp": msg.timestamp.isoformat() if msg.timestamp else None,
                "compressed_at": datetime.now().isoformat()
            }

            file_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

            logger.debug(
                "Message saved to file",
                file_path=str(file_path),
                content_length=len(msg.content)
            )

        except Exception as e:
            logger.error(
                "Failed to save message to file",
                file_path=str(file_path),
                error=str(e)
            )
            raise

    def _create_compressed_reference(self, msg: Message, file_path: Path) -> str:
        """
        압축된 메시지 참조 메타데이터 생성

        Args:
            msg: 원본 메시지
            file_path: 저장된 파일 경로

        Returns:
            메타데이터 참조 문자열

        Example:
            >>> ref = compressor._create_compressed_reference(msg, Path("..."))
            >>> print(ref)
            [압축된 메시지]
            - 역할: planner
            - 원본 길이: 15,234자
            - 저장 경로: ~/.better-llm/project/compressed/agent_planner_20251027_001.txt
            - 요약: 요구사항 분석 및 구현 계획 수립 완료

            상세 내용이 필요하면 read 도구로 위 경로의 파일을 읽어주세요.
        """
        # 요약 추출 (첫 200자)
        summary = msg.content[:200].replace("\n", " ").strip()
        if len(msg.content) > 200:
            summary += "..."

        # 역할 표시
        role_display = msg.agent_name if msg.agent_name else msg.role

        # 메타데이터 참조 생성
        reference = f"""[압축된 메시지]
- 역할: {role_display}
- 원본 길이: {len(msg.content):,}자
- 저장 경로: {file_path}
- 요약: {summary}

상세 내용이 필요하면 read 도구로 위 경로의 파일을 읽어주세요."""

        return reference

    def load_compressed_message(self, file_path: Path) -> Optional[Message]:
        """
        압축된 메시지 파일 읽기

        Args:
            file_path: 압축된 메시지 파일 경로

        Returns:
            원본 메시지 또는 None (실패 시)
        """
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))

            msg = Message(
                role=data["role"],
                content=data["content"],
                agent_name=data.get("agent_name"),
                timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else None
            )

            logger.debug(
                "Compressed message loaded",
                file_path=str(file_path),
                content_length=len(msg.content)
            )

            return msg

        except Exception as e:
            logger.error(
                "Failed to load compressed message",
                file_path=str(file_path),
                error=str(e)
            )
            return None

    def estimate_compression_benefit(
        self,
        messages: List[Message],
        target_reduction_ratio: float = 0.3
    ) -> dict:
        """
        압축 효과 추정

        Args:
            messages: 메시지 리스트
            target_reduction_ratio: 목표 압축 비율

        Returns:
            dict: {
                "original_chars": int,        # 원본 문자 수
                "estimated_compressed_chars": int,  # 압축 후 문자 수
                "reduction_ratio": float,     # 실제 압축 비율
                "messages_to_compress": int   # 압축 대상 메시지 수
            }
        """
        if not messages:
            return {
                "original_chars": 0,
                "estimated_compressed_chars": 0,
                "reduction_ratio": 0.0,
                "messages_to_compress": 0
            }

        # 첫 번째 사용자 메시지 찾기
        first_user_msg_idx = next(
            (i for i, msg in enumerate(messages) if msg.role == "user"),
            None
        )

        # 압축 대상 계산
        total_messages = len(messages)
        target_compressed_count = int(total_messages * target_reduction_ratio)

        if first_user_msg_idx is not None:
            compressible_start = first_user_msg_idx + 1
        else:
            compressible_start = 0

        messages_to_compress_indices = list(range(
            compressible_start,
            min(compressible_start + target_compressed_count, total_messages)
        ))

        # 원본 문자 수 계산
        original_chars = sum(len(msg.content) for msg in messages)

        # 압축 후 문자 수 추정
        estimated_compressed_chars = 0
        for i, msg in enumerate(messages):
            if i in messages_to_compress_indices:
                # 압축 참조 문자 수 (대략 200자)
                estimated_compressed_chars += 200
            else:
                # 원본 그대로
                estimated_compressed_chars += len(msg.content)

        reduction_ratio = (original_chars - estimated_compressed_chars) / original_chars if original_chars > 0 else 0.0

        return {
            "original_chars": original_chars,
            "estimated_compressed_chars": estimated_compressed_chars,
            "reduction_ratio": reduction_ratio,
            "messages_to_compress": len(messages_to_compress_indices)
        }
