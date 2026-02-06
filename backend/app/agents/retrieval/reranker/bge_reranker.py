"""
BGEReranker - 로컬 BGE Reranker 모델 기반 리랭커

BAAI/bge-reranker-v2-m3 모델을 사용한 로컬 리랭킹.
주의: torch ~1-2GB 의존성으로 Docker 이미지 크기 급증 리스크.
로컬 개발/GPU 서버 전용 권장.
"""

import logging
import time
from typing import Any, Dict, List

from app.agents.retrieval.reranker.base import BaseReranker, RankedDocument

logger = logging.getLogger(__name__)


class BGEReranker(BaseReranker):
    """로컬 BGE Reranker 모델 기반 리랭커."""

    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3"):
        self._model_name = model_name
        self._model = None

    def _get_model(self):
        """모델 lazy loading."""
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder

                self._model = CrossEncoder(self._model_name)
                logger.info(f"[BGEReranker] Loaded model: {self._model_name}")
            except ImportError:
                logger.warning(
                    "[BGEReranker] sentence-transformers package not installed. "
                    "Install with: pip install sentence-transformers"
                )
                return None
        return self._model

    async def rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int = 5,
        text_field: str = "content",
    ) -> List[RankedDocument]:
        """
        로컬 BGE 모델로 문서 리랭킹.

        CPU에서도 동작하지만 GPU 권장.
        """
        if not documents:
            return []

        model = self._get_model()
        if model is None:
            return self._fallback_ranking(documents, top_k)

        # 문서 텍스트 추출
        doc_texts = []
        for doc in documents:
            text = doc.get(text_field, "")
            if not text:
                text = doc.get("title", "") + " " + doc.get("chunk_text", "")
            doc_texts.append(text.strip() or "(empty)")

        start_time = time.time()

        try:
            pairs = [(query, text) for text in doc_texts]
            scores = model.predict(pairs)

            # 점수 기준 정렬
            scored_docs = list(zip(range(len(documents)), scores, documents))
            scored_docs.sort(key=lambda x: x[1], reverse=True)

            elapsed_ms = (time.time() - start_time) * 1000
            logger.info(
                f"[BGEReranker] Reranked {len(documents)} docs "
                f"→ top {top_k} in {elapsed_ms:.0f}ms"
            )

            return [
                RankedDocument(
                    document=doc,
                    rerank_score=float(score),
                    original_index=idx,
                    original_similarity=doc.get("similarity", 0.0),
                )
                for idx, score, doc in scored_docs[:top_k]
            ]

        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            logger.warning(
                f"[BGEReranker] Error after {elapsed_ms:.0f}ms: {e}, "
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
