"""
BaseReranker - 리랭커 추상 인터페이스

모든 리랭커 구현이 상속하는 ABC.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class RankedDocument:
    """리랭킹된 문서."""

    document: Dict[str, Any]
    rerank_score: float
    original_index: int = 0
    original_similarity: float = 0.0


class BaseReranker(ABC):
    """리랭커 추상 기본 클래스."""

    @abstractmethod
    async def rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int = 5,
        text_field: str = "content",
    ) -> List[RankedDocument]:
        """
        문서 리랭킹.

        Args:
            query: 사용자 쿼리
            documents: 리랭킹할 문서 리스트 (각 문서는 dict)
            top_k: 반환할 상위 문서 수
            text_field: 문서에서 텍스트를 추출할 필드명

        Returns:
            리랭킹된 상위 K개 문서 (RankedDocument 리스트)
        """
        ...
