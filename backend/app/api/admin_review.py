"""
똑소리 프로젝트 - 관리자 검토 API

Human-in-the-Loop 관리자 검토 엔드포인트.
관리자가 검토 대기 중인 응답을 조회하고 승인/거부/수정할 수 있습니다.
"""

import datetime
import logging
import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from langgraph.types import Command
from pydantic import BaseModel, Field

from app.supervisor import get_graph_for_chat_type

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin/reviews", tags=["Admin Review"])


# Admin API Key Authentication
async def verify_admin_key(x_admin_key: str = Header(..., alias="X-Admin-Key")) -> str:
    """Verify admin API key."""
    expected = os.getenv("ADMIN_API_KEY", "")
    if not expected or x_admin_key != expected:
        raise HTTPException(status_code=403, detail="Invalid admin API key")
    return x_admin_key


# Request/Response Models
class ReviewDecision(BaseModel):
    """관리자 검토 결정 모델."""

    action: str = Field(..., description="approve | reject | edit")
    fallback_answer: Optional[str] = Field(None, description="거부 시 대체 응답")
    edited_answer: Optional[str] = Field(None, description="수정 시 편집된 응답")
    reason: Optional[str] = Field(None, description="결정 사유")


class PendingReview(BaseModel):
    """대기 중인 검토 정보."""

    thread_id: str
    query: str = ""
    final_answer: str = ""
    confidence_score: float = 0.0
    violations: List[Dict[str, Any]] = []
    created_at: Optional[str] = None


class ReviewResponse(BaseModel):
    """검토 처리 응답."""

    thread_id: str
    action: str
    status: str
    message: str


# In-memory pending reviews store (프로덕션에서는 Redis/DB로 대체)
_pending_reviews: Dict[str, Dict[str, Any]] = {}


def add_pending_review(thread_id: str, review_data: Dict[str, Any]) -> None:
    """검토 대기열에 추가."""
    _pending_reviews[thread_id] = {
        **review_data,
        "thread_id": thread_id,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    logger.info(f"[Admin] Added pending review for thread_id={thread_id}")


def remove_pending_review(thread_id: str) -> Optional[Dict[str, Any]]:
    """검토 대기열에서 제거."""
    return _pending_reviews.pop(thread_id, None)


def get_pending_reviews() -> List[Dict[str, Any]]:
    """대기 중인 검토 목록 조회."""
    return list(_pending_reviews.values())


@router.get(
    "", response_model=List[PendingReview], dependencies=[Depends(verify_admin_key)]
)
async def list_pending_reviews():
    """대기 중인 관리자 검토 목록 조회."""
    return get_pending_reviews()


@router.get(
    "/{thread_id}",
    response_model=PendingReview,
    dependencies=[Depends(verify_admin_key)],
)
async def get_review(thread_id: str):
    """특정 검토 상세 조회."""
    if thread_id not in _pending_reviews:
        raise HTTPException(status_code=404, detail=f"Review not found: {thread_id}")
    return _pending_reviews[thread_id]


@router.post(
    "/{thread_id}/decide",
    response_model=ReviewResponse,
    dependencies=[Depends(verify_admin_key)],
)
async def decide_review(thread_id: str, decision: ReviewDecision):
    """
    관리자 검토 결정 처리.

    approve: 원본 응답 승인 → 그래프 재개
    reject: 거부 → fallback 응답으로 대체 후 재개
    edit: 수정 → 편집된 응답으로 대체 후 재개
    """
    if thread_id not in _pending_reviews:
        raise HTTPException(status_code=404, detail=f"Review not found: {thread_id}")

    if decision.action not in ("approve", "reject", "edit"):
        raise HTTPException(
            status_code=400, detail=f"Invalid action: {decision.action}"
        )

    if decision.action == "edit" and not decision.edited_answer:
        raise HTTPException(
            status_code=400, detail="edited_answer required for edit action"
        )

    try:
        graph = get_graph_for_chat_type("mas")
        resume_value = decision.model_dump(exclude_none=True)
        config = {"configurable": {"thread_id": thread_id}}
        await graph.ainvoke(Command(resume=resume_value), config=config)

        remove_pending_review(thread_id)

        return ReviewResponse(
            thread_id=thread_id,
            action=decision.action,
            status="completed",
            message=f"Review {decision.action}d successfully",
        )
    except Exception as e:
        logger.error(f"[Admin] Failed to process review for {thread_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to process review: {str(e)}"
        )


@router.post(
    "/{thread_id}/approve",
    response_model=ReviewResponse,
    dependencies=[Depends(verify_admin_key)],
)
async def approve_review(thread_id: str, reason: Optional[str] = None):
    """검토 승인 (간편 엔드포인트)."""
    decision = ReviewDecision(action="approve", reason=reason)
    return await decide_review(thread_id, decision)


@router.post(
    "/{thread_id}/reject",
    response_model=ReviewResponse,
    dependencies=[Depends(verify_admin_key)],
)
async def reject_review(
    thread_id: str,
    fallback_answer: Optional[str] = None,
    reason: Optional[str] = None,
):
    """검토 거부 (간편 엔드포인트)."""
    decision = ReviewDecision(
        action="reject", fallback_answer=fallback_answer, reason=reason
    )
    return await decide_review(thread_id, decision)


__all__ = [
    "router",
    "add_pending_review",
    "remove_pending_review",
    "get_pending_reviews",
    "ReviewDecision",
    "PendingReview",
    "ReviewResponse",
    "_pending_reviews",
]
