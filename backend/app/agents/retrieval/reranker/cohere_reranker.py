"""
CohereReranker - Cohere Rerank API 기반 리랭커

Cohere rerank-v3.5 모델을 사용하여 검색 결과를 리랭킹.
500ms 타임아웃 설정, 초과 시 원본 순서 유지 (graceful fallback).
"""

import asyncio
import logging
import os
import time
from typing import Any, Dict, List, Optional

from app.agents.retrieval.reranker.base import BaseReranker, RankedDocument

logger = logging.getLogger(__name__)


class CohereReranker(BaseReranker):
    """Cohere Rerank API 기반 리랭커."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "rerank-v3.5",
        timeout_ms: int = 500,
    ):
        self._api_key = api_key or os.getenv("COHERE_API_KEY")
        self._model = model
        self._timeout_ms = timeout_ms
        self._client = None

    def _get_client(self):
        """Cohere 클라이언트 lazy initialization."""
        if self._client is None:
            try:
                import cohere

                self._client = cohere.AsyncClientV2(api_key=self._api_key)
            except ImportError:
                logger.warning(
                    "[CohereReranker] cohere package not installed. "
                    "Install with: pip install cohere"
                )
                return None
        return self._client

    async def rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int = 5,
        text_field: str = "content",
    ) -> List[RankedDocument]:
        """
        Cohere Rerank API로 문서 리랭킹.

        500ms 타임아웃 초과 또는 에러 시 원본 순서 유지.
        """
        if not documents:
            return []

        if not self._api_key:
            logger.warning("[CohereReranker] COHERE_API_KEY not set, skipping rerank")
            return self._fallback_ranking(documents, top_k)

        client = self._get_client()
        if client is None:
            return self._fallback_ranking(documents, top_k)

        # 문서 텍스트 추출
        doc_texts = []
        for doc in documents:
            text = doc.get(text_field, "")
            if not text:
                text = doc.get("title", "") + " " + doc.get("chunk_text", "")
            doc_texts.append(text.strip() or "(empty)")

        start_time = time.time()
        timeout_sec = self._timeout_ms / 1000.0

        try:
            response = await asyncio.wait_for(
                client.rerank(
                    model=self._model,
                    query=query,
                    documents=doc_texts,
                    top_n=min(top_k, len(documents)),
                ),
                timeout=timeout_sec,
            )

            elapsed_ms = (time.time() - start_time) * 1000
            logger.info(
                f"[CohereReranker] Reranked {len(documents)} docs "
                f"→ top {top_k} in {elapsed_ms:.0f}ms"
            )

            ranked = []
            for result in response.results:
                idx = result.index
                ranked.append(
                    RankedDocument(
                        document=documents[idx],
                        rerank_score=result.relevance_score,
                        original_index=idx,
                        original_similarity=documents[idx].get("similarity", 0.0),
                    )
                )

            return ranked

        except asyncio.TimeoutError:
            elapsed_ms = (time.time() - start_time) * 1000
            logger.warning(
                f"[CohereReranker] Timeout ({elapsed_ms:.0f}ms > {self._timeout_ms}ms), "
                f"falling back to original order"
            )
            return self._fallback_ranking(documents, top_k)

        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            logger.warning(
                f"[CohereReranker] Error after {elapsed_ms:.0f}ms: {e}, "
                f"falling back to original order"
            )
            return self._fallback_ranking(documents, top_k)

    @staticmethod
    def _fallback_ranking(
        documents: List[Dict[str, Any]], top_k: int
    ) -> List[RankedDocument]:
        """원본 순서 유지 fallback."""
        return [
            RankedDocument(
                document=doc,
                rerank_score=doc.get("similarity", 0.0),
                original_index=i,
                original_similarity=doc.get("similarity", 0.0),
            )
            for i, doc in enumerate(documents[:top_k])
        ]
