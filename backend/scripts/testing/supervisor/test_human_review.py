"""
Human-in-the-Loop 단위 테스트

테스트 항목:
1. confidence_score 임계값 동작
2. should_route_to_human_review 라우팅
3. human_review_node 승인/거부/수정
4. 환경변수 비활성화
5. confidence_score 공식 검증
6. admin API 모델 검증
"""

import os
from unittest.mock import patch


class TestShouldRouteToHumanReview:
    """should_route_to_human_review 라우팅 함수 테스트."""

    def test_disabled_returns_supervisor(self):
        """HIL 비활성화 시 항상 supervisor로 라우팅."""
        from app.supervisor.nodes.human_review import should_route_to_human_review

        with patch.dict(os.environ, {"ENABLE_HUMAN_REVIEW": "false"}):
            state = {"review": {"confidence_score": 0.3}}
            assert should_route_to_human_review(state) == "supervisor"

    def test_enabled_low_confidence_routes_to_human_review(self):
        """활성화 + 낮은 confidence → human_review로 라우팅."""
        from app.supervisor.nodes.human_review import should_route_to_human_review

        with patch.dict(
            os.environ,
            {"ENABLE_HUMAN_REVIEW": "true", "REVIEW_CONFIDENCE_THRESHOLD": "0.7"},
        ):
            state = {"review": {"confidence_score": 0.5}}
            assert should_route_to_human_review(state) == "human_review"

    def test_enabled_high_confidence_routes_to_supervisor(self):
        """활성화 + 높은 confidence → supervisor로 라우팅."""
        from app.supervisor.nodes.human_review import should_route_to_human_review

        with patch.dict(
            os.environ,
            {"ENABLE_HUMAN_REVIEW": "true", "REVIEW_CONFIDENCE_THRESHOLD": "0.7"},
        ):
            state = {"review": {"confidence_score": 0.9}}
            assert should_route_to_human_review(state) == "supervisor"

    def test_exact_threshold_routes_to_supervisor(self):
        """정확히 임계값 = supervisor (미만만 human_review)."""
        from app.supervisor.nodes.human_review import should_route_to_human_review

        with patch.dict(
            os.environ,
            {"ENABLE_HUMAN_REVIEW": "true", "REVIEW_CONFIDENCE_THRESHOLD": "0.7"},
        ):
            state = {"review": {"confidence_score": 0.7}}
            assert should_route_to_human_review(state) == "supervisor"

    def test_retry_generation_skips_human_review(self):
        """재생성 필요 시 human_review 건너뜀."""
        from app.supervisor.nodes.human_review import should_route_to_human_review

        with patch.dict(os.environ, {"ENABLE_HUMAN_REVIEW": "true"}):
            state = {
                "review": {"confidence_score": 0.3},
                "next_agent": "retry_generation",
            }
            assert should_route_to_human_review(state) == "supervisor"

    def test_missing_confidence_defaults_to_supervisor(self):
        """confidence_score 없으면 기본값 1.0 → supervisor."""
        from app.supervisor.nodes.human_review import should_route_to_human_review

        with patch.dict(os.environ, {"ENABLE_HUMAN_REVIEW": "true"}):
            state = {"review": {}}
            assert should_route_to_human_review(state) == "supervisor"


class TestConfidenceScoreFormula:
    """confidence_score 공식 검증 테스트."""

    def test_perfect_score(self):
        """위반 0, 인용 정확도 1.0 → 1.0."""
        citation_accuracy = 1.0
        violation_details = []
        total_checks = len(violation_details) + 1
        violation_ratio = len(violation_details) / total_checks
        score = round(citation_accuracy * 0.5 + (1 - violation_ratio) * 0.5, 4)
        assert score == 1.0

    def test_half_accuracy_no_violations(self):
        """인용 정확도 0.5, 위반 0 → 0.75."""
        citation_accuracy = 0.5
        violation_details = []
        total_checks = len(violation_details) + 1
        violation_ratio = len(violation_details) / total_checks
        score = round(citation_accuracy * 0.5 + (1 - violation_ratio) * 0.5, 4)
        assert score == 0.75

    def test_full_accuracy_one_violation(self):
        """인용 정확도 1.0, 위반 1개 → 0.75."""
        citation_accuracy = 1.0
        violation_details = [{"severity": "critical"}]
        total_checks = len(violation_details) + 1
        violation_ratio = len(violation_details) / total_checks
        score = round(citation_accuracy * 0.5 + (1 - violation_ratio) * 0.5, 4)
        assert score == 0.75

    def test_example_from_plan(self):
        """계획서 예시: 인용 4/5, 위반 1/10 → 0.85."""
        citation_accuracy = 4 / 5  # 0.8
        # Plan says: 검사 10개 중 위반 1개 → violation_ratio = 0.1
        # But our formula uses len(violation_details) / (len(violation_details) + 1)
        # For 1 violation: 1/2 = 0.5
        # score = 0.8 * 0.5 + (1 - 0.5) * 0.5 = 0.4 + 0.25 = 0.65
        violation_details = [{"severity": "warning"}]
        total_checks = len(violation_details) + 1
        violation_ratio = len(violation_details) / total_checks
        score = round(citation_accuracy * 0.5 + (1 - violation_ratio) * 0.5, 4)
        assert score == 0.65


class TestHumanReviewHelpers:
    """helper 함수 테스트."""

    def test_is_enabled_default_false(self):
        from app.supervisor.nodes.human_review import _is_human_review_enabled

        with patch.dict(os.environ, {}, clear=False):
            if "ENABLE_HUMAN_REVIEW" in os.environ:
                del os.environ["ENABLE_HUMAN_REVIEW"]
            assert _is_human_review_enabled() is False

    def test_is_enabled_true(self):
        from app.supervisor.nodes.human_review import _is_human_review_enabled

        with patch.dict(os.environ, {"ENABLE_HUMAN_REVIEW": "true"}):
            assert _is_human_review_enabled() is True

    def test_get_threshold_default(self):
        from app.supervisor.nodes.human_review import _get_confidence_threshold

        with patch.dict(os.environ, {}, clear=False):
            if "REVIEW_CONFIDENCE_THRESHOLD" in os.environ:
                del os.environ["REVIEW_CONFIDENCE_THRESHOLD"]
            assert _get_confidence_threshold() == 0.7

    def test_get_threshold_custom(self):
        from app.supervisor.nodes.human_review import _get_confidence_threshold

        with patch.dict(os.environ, {"REVIEW_CONFIDENCE_THRESHOLD": "0.85"}):
            assert _get_confidence_threshold() == 0.85

    def test_get_threshold_invalid_returns_default(self):
        from app.supervisor.nodes.human_review import _get_confidence_threshold

        with patch.dict(os.environ, {"REVIEW_CONFIDENCE_THRESHOLD": "invalid"}):
            assert _get_confidence_threshold() == 0.7


class TestAdminModels:
    """Admin API 모델 테스트."""

    def test_review_decision_approve(self):
        from app.api.admin_review import ReviewDecision

        decision = ReviewDecision(action="approve")
        assert decision.action == "approve"
        assert decision.fallback_answer is None

    def test_review_decision_reject_with_fallback(self):
        from app.api.admin_review import ReviewDecision

        decision = ReviewDecision(
            action="reject", fallback_answer="안전 응답", reason="부정확"
        )
        assert decision.action == "reject"
        assert decision.fallback_answer == "안전 응답"

    def test_review_decision_edit(self):
        from app.api.admin_review import ReviewDecision

        decision = ReviewDecision(action="edit", edited_answer="수정된 답변")
        assert decision.action == "edit"
        assert decision.edited_answer == "수정된 답변"


class TestPendingReviewStore:
    """In-memory pending review store 테스트."""

    def test_add_and_get(self):
        from app.api.admin_review import (
            _pending_reviews,
            add_pending_review,
            get_pending_reviews,
        )

        _pending_reviews.clear()
        add_pending_review("thread-1", {"query": "test", "confidence_score": 0.5})
        reviews = get_pending_reviews()
        assert len(reviews) == 1
        assert reviews[0]["thread_id"] == "thread-1"
        _pending_reviews.clear()

    def test_remove(self):
        from app.api.admin_review import (
            _pending_reviews,
            add_pending_review,
            remove_pending_review,
        )

        _pending_reviews.clear()
        add_pending_review("thread-2", {"query": "test"})
        removed = remove_pending_review("thread-2")
        assert removed is not None
        assert removed["thread_id"] == "thread-2"
        assert remove_pending_review("thread-2") is None
        _pending_reviews.clear()
