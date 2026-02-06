"""
똑소리 프로젝트 - LangGraph Checkpointer 팩토리

Checkpointer는 LangGraph에서 thread_id별 상태를 저장/복원하는 역할.
- InMemory: 개발/테스트용 (서버 재시작 시 상태 소실)
- Postgres: 프로덕션용 (영구 저장, interrupt/resume 지원)

환경변수:
    CHECKPOINTER_MODE: 'memory' (기본) | 'postgres'
"""

import logging
import os
from typing import Literal, Optional

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver

logger = logging.getLogger(__name__)

# 지원하는 Checkpointer 모드
CheckpointerMode = Literal["memory", "postgres"]

# 기본 모드
DEFAULT_MODE: CheckpointerMode = "memory"


def get_checkpointer_mode() -> CheckpointerMode:
    """
    환경변수에서 Checkpointer 모드 읽기

    Returns:
        'memory' 또는 'postgres'

    Raises:
        ValueError: 지원하지 않는 모드인 경우
    """
    mode = os.getenv("CHECKPOINTER_MODE", DEFAULT_MODE).lower()

    if mode not in ("memory", "postgres"):
        raise ValueError(
            f"지원하지 않는 CHECKPOINTER_MODE: '{mode}'. "
            f"'memory' 또는 'postgres'를 사용하세요."
        )

    return mode  # type: ignore


def get_checkpointer(mode: Optional[CheckpointerMode] = None) -> BaseCheckpointSaver:
    """
    Checkpointer 인스턴스 생성 팩토리

    Args:
        mode: 'memory' | 'postgres' | None (환경변수에서 읽음)

    Returns:
        BaseCheckpointSaver 구현체

    Example:
        >>> checkpointer = get_checkpointer()
        >>> graph = builder.compile(checkpointer=checkpointer)
    """
    if mode is None:
        mode = get_checkpointer_mode()

    if mode == "memory":
        return _create_memory_checkpointer()

    if mode == "postgres":
        return _create_postgres_checkpointer()

    raise ValueError(f"지원하지 않는 모드: {mode}")


def _create_memory_checkpointer() -> MemorySaver:
    """InMemory Checkpointer 생성 (개발/테스트용)."""
    return MemorySaver()


def _create_postgres_checkpointer() -> BaseCheckpointSaver:
    """
    PostgreSQL Checkpointer 생성 (프로덕션용).

    langgraph-checkpoint-postgres의 PostgresSaver를 사용.
    기존 RDS 연결 정보를 활용하여 DSN을 구성.
    """
    try:
        from langgraph.checkpoint.postgres import PostgresSaver
    except ImportError:
        logger.error(
            "[Checkpointer] langgraph-checkpoint-postgres not installed. "
            "Install with: pip install langgraph-checkpoint-postgres psycopg[binary]"
        )
        logger.warning("[Checkpointer] Falling back to MemorySaver")
        return _create_memory_checkpointer()

    try:
        from app.common.config import get_config

        config = get_config()
        db = config.database
        dsn = f"postgresql://{db.user}:{db.password}@{db.host}:{db.port}/{db.name}"

        # Sync PostgresSaver (LangGraph graph.compile uses sync checkpointer)
        import psycopg

        conn = psycopg.connect(dsn, autocommit=True)
        checkpointer = PostgresSaver(conn)
        checkpointer.setup()

        logger.info("[Checkpointer] PostgresSaver initialized successfully")
        return checkpointer

    except Exception as e:
        logger.error(f"[Checkpointer] PostgresSaver init failed: {e}")
        logger.warning("[Checkpointer] Falling back to MemorySaver")
        return _create_memory_checkpointer()
