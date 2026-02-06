"""
똑소리 프로젝트 - Human-in-the-Loop 관리자 검토 노드

LangGraph interrupt() 함수를 사용하여 confidence_score가 임계값 이하일 때
파이프라인을 일시 중단하고 관리자 검토를 대기합니다.

환경변수:
    ENABLE_HUMAN_REVIEW: 'true' (기본 false) - HIL 활성화
    REVIEW_CONFIDENCE_THRESHOLD: 0.7 (기본) - 검토 임계값
"""

import logging
import os
from typing import Any, Dict

from langgraph.types import interrupt

logger = logging.getLogger(__name__)

# 기본 설정
DEFAULT_CONFIDENCE_THRESHOLD = 0.7


def _is_human_review_enabled() -> bool:
    """Human review 활성화 여부 확인."""
    return os.getenv("ENABLE_HUMAN_REVIEW", "false").lower() == "true"


def _get_confidence_threshold() -> float:
    """Confidence 임계값 조회."""
    try:
        return float(
            os.getenv("REVIEW_CONFIDENCE_THRESHOLD", str(DEFAULT_CONFIDENCE_THRESHOLD))
        )
    except ValueError:
        return DEFAULT_CONFIDENCE_THRESHOLD


def human_review_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Human-in-the-Loop 관리자 검토 노드.

    review 노드의 결과에서 confidence_score를 확인하고,
    임계값 미만이면 interrupt()로 파이프라인을 일시 중단합니다.

    관리자가 Command(resume={"action": "approve"/"reject"/"edit", ...}) 호출 시 재개됩니다.

    Args:
        state: ChatState dict containing review results

    Returns:
        Updated state dict
    """
    review_data = state.get("review", {})
    confidence_score = review_data.get("confidence_score", 1.0)
    threshold = _get_confidence_threshold()

    logger.info(
        f"[HumanReview] confidence_score={confidence_score}, threshold={threshold}"
    )

    # interrupt()로 관리자 검토 요청
    # 이 호출은 그래프 실행을 일시 중단하고, Command(resume=...) 호출까지 대기
    review_payload = {
        "confidence_score": confidence_score,
        "threshold": threshold,
        "query": state.get("query", ""),
        "final_answer": state.get("final_answer", review_data.get("final_answer", "")),
        "violations": review_data.get("violations", []),
        "review_passed": review_data.get("passed", False),
    }

    logger.info("[HumanReview] Interrupting for admin review...")
    admin_decision = interrupt(review_payload)

    # 관리자 응답 처리
    action = (
        admin_decision.get("action", "approve")
        if isinstance(admin_decision, dict)
        else "approve"
    )

    if action == "approve":
        logger.info("[HumanReview] Admin approved the response")
        return {
            "human_review_status": "approved",
            "human_review_decision": admin_decision,
        }
    elif action == "reject":
        logger.info("[HumanReview] Admin rejected the response")
        fallback_answer = (
            "죄송합니다. 해당 질문에 대한 정확한 답변을 제공하기 어렵습니다. "
            "소비자 분쟁과 관련된 보다 정확한 상담을 위해 "
            "한국소비자원(1372) 또는 가까운 법률구조공단에 문의해 주시기 바랍니다."
        )
        return {
            "human_review_status": "rejected",
            "human_review_decision": admin_decision,
            "final_answer": admin_decision.get("fallback_answer", fallback_answer),
        }
    elif action == "edit":
        logger.info("[HumanReview] Admin edited the response")
        edited_answer = admin_decision.get(
            "edited_answer", state.get("final_answer", "")
        )
        return {
            "human_review_status": "edited",
            "human_review_decision": admin_decision,
            "final_answer": edited_answer,
        }
    else:
        logger.warning(f"[HumanReview] Unknown action: {action}, defaulting to approve")
        return {
            "human_review_status": "approved",
            "human_review_decision": admin_decision,
        }


def should_route_to_human_review(state: Dict[str, Any]) -> str:
    """
    review 노드 이후 human_review로 분기할지 결정하는 조건부 라우팅 함수.

    Returns:
        "human_review": confidence_score < threshold이고 HIL 활성화됨
        "supervisor": 그 외 (기존 동작 유지)
    """
    if not _is_human_review_enabled():
        return "supervisor"

    review_data = state.get("review", {})
    confidence_score = review_data.get("confidence_score", 1.0)
    threshold = _get_confidence_threshold()

    # 재생성이 필요한 경우(retry)는 human_review 건너뜀
    next_agent = state.get("next_agent", "")
    if next_agent == "retry_generation":
        return "supervisor"

    if confidence_score < threshold:
        logger.info(
            f"[HumanReview] Routing to human_review: "
            f"confidence={confidence_score} < threshold={threshold}"
        )
        return "human_review"

    return "supervisor"


__all__ = ["human_review_node", "should_route_to_human_review"]
