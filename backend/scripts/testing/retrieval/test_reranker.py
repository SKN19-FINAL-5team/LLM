"""
Reranker 단위 테스트

테스트 항목:
1. Cohere reranker mock 테스트
2. BGE reranker 테스트
3. 타임아웃 fallback 동작
4. top_k 적용
5. 빈 결과 처리
6. _apply_reranking 통합
"""

import asyncio
from dataclasses import dataclass
from unittest.mock import AsyncMock, patch

import pytest

from app.agents.retrieval.reranker.base import RankedDocument
from app.agents.retrieval.reranker.cohere_reranker import CohereReranker


@pytest.fixture
def sample_documents():
    """테스트용 문서 리스트."""
    return [
        {"content": "소비자 분쟁 해결 기준", "title": "기준1", "similarity": 0.8},
        {"content": "전자상거래 환불 규정", "title": "기준2", "similarity": 0.7},
        {"content": "헬스장 계약 해지 기준", "title": "기준3", "similarity": 0.6},
        {"content": "통신사 위약금 관련 법률", "title": "법률1", "similarity": 0.5},
        {"content": "자동차 수리비 분쟁 사례", "title": "사례1", "similarity": 0.4},
    ]


class TestRankedDocument:
    """RankedDocument 데이터클래스 테스트."""

    def test_create_ranked_document(self):
        doc = {"content": "test", "title": "title"}
        ranked = RankedDocument(
            document=doc,
            rerank_score=0.95,
            original_index=0,
            original_similarity=0.8,
        )
        assert ranked.document == doc
        assert ranked.rerank_score == 0.95
        assert ranked.original_index == 0
        assert ranked.original_similarity == 0.8


class TestCohereRerankerEmpty:
    """빈 입력 처리 테스트."""

    def test_empty_documents(self):
        reranker = CohereReranker(api_key="test-key")
        result = asyncio.get_event_loop().run_until_complete(
            reranker.rerank("query", [], top_k=5)
        )
        assert result == []


class TestCohereRerankerNoApiKey:
    """API 키 없을 때 fallback 테스트."""

    @patch.dict("os.environ", {}, clear=False)
    def test_no_api_key_fallback(self, sample_documents):
        reranker = CohereReranker(api_key=None)
        # Force _api_key to None
        reranker._api_key = None
        result = asyncio.get_event_loop().run_until_complete(
            reranker.rerank("query", sample_documents, top_k=3)
        )
        assert len(result) == 3
        # Should return original order
        assert result[0].document == sample_documents[0]
        assert result[1].document == sample_documents[1]
        assert result[2].document == sample_documents[2]


class TestCohereRerankerMock:
    """Cohere API mock 테스트."""

    def test_successful_rerank(self, sample_documents):
        """정상 리랭킹 시 결과 반환."""
        reranker = CohereReranker(api_key="test-key", timeout_ms=500)

        # Mock Cohere response
        @dataclass
        class MockResult:
            index: int
            relevance_score: float

        @dataclass
        class MockResponse:
            results: list

        mock_response = MockResponse(
            results=[
                MockResult(index=2, relevance_score=0.99),
                MockResult(index=0, relevance_score=0.85),
                MockResult(index=4, relevance_score=0.70),
            ]
        )

        mock_client = AsyncMock()
        mock_client.rerank = AsyncMock(return_value=mock_response)
        reranker._client = mock_client

        result = asyncio.get_event_loop().run_until_complete(
            reranker.rerank("헬스장 환불", sample_documents, top_k=3)
        )

        assert len(result) == 3
        # Reranked order: doc[2], doc[0], doc[4]
        assert result[0].document == sample_documents[2]
        assert result[0].rerank_score == 0.99
        assert result[1].document == sample_documents[0]
        assert result[2].document == sample_documents[4]

    def test_top_k_limits_results(self, sample_documents):
        """top_k가 결과 수를 제한하는지 확인."""
        reranker = CohereReranker(api_key="test-key")

        @dataclass
        class MockResult:
            index: int
            relevance_score: float

        @dataclass
        class MockResponse:
            results: list

        mock_response = MockResponse(
            results=[
                MockResult(index=0, relevance_score=0.9),
                MockResult(index=1, relevance_score=0.8),
            ]
        )

        mock_client = AsyncMock()
        mock_client.rerank = AsyncMock(return_value=mock_response)
        reranker._client = mock_client

        result = asyncio.get_event_loop().run_until_complete(
            reranker.rerank("query", sample_documents, top_k=2)
        )

        assert len(result) == 2


class TestCohereRerankerTimeout:
    """타임아웃 fallback 테스트."""

    def test_timeout_returns_original_order(self, sample_documents):
        """타임아웃 시 원본 순서 유지."""
        reranker = CohereReranker(api_key="test-key", timeout_ms=1)

        async def slow_rerank(*args, **kwargs):
            await asyncio.sleep(1)  # 1초 대기 (타임아웃 1ms)

        mock_client = AsyncMock()
        mock_client.rerank = slow_rerank
        reranker._client = mock_client

        result = asyncio.get_event_loop().run_until_complete(
            reranker.rerank("query", sample_documents, top_k=3)
        )

        assert len(result) == 3
        # Should be original order (fallback)
        assert result[0].document == sample_documents[0]
        assert result[1].document == sample_documents[1]
        assert result[2].document == sample_documents[2]


class TestCohereRerankerError:
    """API 에러 시 fallback 테스트."""

    def test_api_error_returns_original_order(self, sample_documents):
        reranker = CohereReranker(api_key="test-key")

        mock_client = AsyncMock()
        mock_client.rerank = AsyncMock(side_effect=Exception("API Error"))
        reranker._client = mock_client

        result = asyncio.get_event_loop().run_until_complete(
            reranker.rerank("query", sample_documents, top_k=3)
        )

        assert len(result) == 3
        assert result[0].document == sample_documents[0]


class TestApplyReranking:
    """_apply_reranking 함수 통합 테스트."""

    @patch.dict("os.environ", {"RETRIEVAL_RERANKING_ENABLED": "false"}, clear=False)
    def test_disabled_returns_original(self):
        """비활성화 시 원본 반환."""
        from app.supervisor.nodes.retrieval_merge import _apply_reranking

        merged = {"laws": [{"content": "test"}], "criteria": []}
        result = _apply_reranking(merged, "query")
        assert result == merged

    @patch.dict("os.environ", {"RETRIEVAL_RERANKING_ENABLED": "true"}, clear=False)
    def test_empty_query_returns_original(self):
        """빈 쿼리 시 원본 반환."""
        from app.supervisor.nodes.retrieval_merge import _apply_reranking

        merged = {"laws": [{"content": "test"}]}
        result = _apply_reranking(merged, "")
        assert result == merged

    @patch.dict("os.environ", {"RETRIEVAL_RERANKING_ENABLED": "true"}, clear=False)
    def test_single_doc_skips_reranking(self):
        """문서 1개 이하면 리랭킹 생략."""
        from app.supervisor.nodes.retrieval_merge import _apply_reranking

        merged = {"laws": [{"content": "single doc"}], "criteria": []}
        result = _apply_reranking(merged, "query")
        # Single doc sections should be unchanged
        assert result["laws"] == merged["laws"]


class TestFallbackRanking:
    """fallback ranking 테스트."""

    def test_fallback_preserves_order(self, sample_documents):
        result = CohereReranker._fallback_ranking(sample_documents, 3)
        assert len(result) == 3
        assert result[0].document == sample_documents[0]
        assert result[0].rerank_score == 0.8
        assert result[0].original_index == 0
