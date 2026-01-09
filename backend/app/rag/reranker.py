"""
Reranker Module
검색 결과를 다양한 시그널을 기반으로 재랭킹
"""

from typing import List, Dict, Any, Union
from dataclasses import dataclass, asdict
from .query_analyzer import QueryAnalysis
from .specialized_retrievers.law_retriever import LawSearchResult
from .specialized_retrievers.criteria_retriever import CriteriaSearchResult
from .specialized_retrievers.case_retriever import CaseSearchResult


@dataclass
class UnifiedSearchResult:
    """통합 검색 결과"""
    chunk_id: str
    doc_id: str
    content: str
    doc_type: str                  # 'law', 'criteria', 'case'
    original_score: float          # 원본 검색 점수
    metadata_match_score: float    # 메타데이터 매칭 점수
    importance_score: float        # 청크 중요도 점수
    contextual_score: float        # 맥락 점수 (최신성, 기관 등)
    final_score: float             # 최종 재랭킹 점수
    source_info: Dict              # 원본 검색 결과 정보
    metadata: Dict


class Reranker:
    """재랭킹 시스템"""
    
    # 가중치 설정
    ORIGINAL_SCORE_WEIGHT = 0.4      # 원본 검색 점수
    METADATA_MATCH_WEIGHT = 0.3      # 메타데이터 매칭
    IMPORTANCE_WEIGHT = 0.2          # 중요도
    CONTEXTUAL_WEIGHT = 0.1          # 맥락 점수
    
    def __init__(self):
        """초기화"""
        pass
    
    def rerank(
        self,
        law_results: List[LawSearchResult] = None,
        criteria_results: List[CriteriaSearchResult] = None,
        case_results: List[CaseSearchResult] = None,
        query_analysis: QueryAnalysis = None,
        query: str = ""
    ) -> List[UnifiedSearchResult]:
        """
        검색 결과 재랭킹
        
        Args:
            law_results: 법령 검색 결과
            criteria_results: 기준 검색 결과
            case_results: 사례 검색 결과
            query_analysis: 쿼리 분석 정보
            query: 원본 쿼리
        
        Returns:
            통합 및 재랭킹된 검색 결과
        """
        unified_results = []
        
        # 1. 각 검색 결과를 통합 형식으로 변환
        if law_results:
            unified_results.extend(
                self._convert_law_results(law_results)
            )
        
        if criteria_results:
            unified_results.extend(
                self._convert_criteria_results(criteria_results)
            )
        
        if case_results:
            unified_results.extend(
                self._convert_case_results(case_results)
            )
        
        # 2. 메타데이터 매칭 점수 계산
        if query_analysis:
            for result in unified_results:
                result.metadata_match_score = self._calculate_metadata_match_score(
                    result, query_analysis
                )
        
        # 3. 최종 점수 계산 (Phase 2 최종 조정: Law/Criteria 균형)
        TYPE_MULTIPLIERS = {
            'law': 1.8,       # Law 결과 우대 (1.5 → 1.8, 증가)
            'criteria': 2.0,  # Criteria 결과 우대 (2.5 → 2.0, 감소)
            'case': 1.0       # Case는 기본값
        }
        
        for result in unified_results:
            base_score = (
                result.original_score * self.ORIGINAL_SCORE_WEIGHT +
                result.metadata_match_score * self.METADATA_MATCH_WEIGHT +
                result.importance_score * self.IMPORTANCE_WEIGHT +
                result.contextual_score * self.CONTEXTUAL_WEIGHT
            )
            
            # 타입별 가중치 적용
            type_multiplier = TYPE_MULTIPLIERS.get(result.doc_type, 1.0)
            result.final_score = base_score * type_multiplier
        
        # 4. 점수 기준 정렬
        unified_results.sort(key=lambda x: x.final_score, reverse=True)
        
        return unified_results
    
    def _convert_law_results(
        self,
        law_results: List[LawSearchResult]
    ) -> List[UnifiedSearchResult]:
        """법령 검색 결과를 통합 형식으로 변환"""
        unified = []
        
        for result in law_results:
            unified.append(UnifiedSearchResult(
                chunk_id=result.chunk_id,
                doc_id=result.doc_id,
                content=result.content,
                doc_type='law',
                original_score=result.final_score,
                metadata_match_score=0.0,  # 나중에 계산
                importance_score=0.8,  # 법령은 중요도 높음
                contextual_score=0.5,  # 법령은 시간성 낮음
                final_score=0.0,
                source_info={
                    'law_name': result.law_name,
                    'article_no': result.article_no,
                    'path': result.path,
                    'exact_match_score': result.exact_match_score,
                    'keyword_match_score': result.keyword_match_score,
                    'vector_similarity': result.vector_similarity
                },
                metadata=result.metadata
            ))
        
        return unified
    
    def _convert_criteria_results(
        self,
        criteria_results: List[CriteriaSearchResult]
    ) -> List[UnifiedSearchResult]:
        """기준 검색 결과를 통합 형식으로 변환"""
        unified = []
        
        for result in criteria_results:
            unified.append(UnifiedSearchResult(
                chunk_id=result.chunk_id,
                doc_id=result.doc_id,
                content=result.content,
                doc_type='criteria',
                original_score=result.final_score,
                metadata_match_score=0.0,  # 나중에 계산
                importance_score=0.9,  # 기준은 매우 중요
                contextual_score=0.5,  # 기준은 시간성 낮음
                final_score=0.0,
                source_info={
                    'item_name': result.item_name,
                    'category': result.category,
                    'industry': result.industry,
                    'item_group': result.item_group,
                    'dispute_type': result.dispute_type,
                    'item_match_score': result.item_match_score,
                    'hierarchy_match_score': result.hierarchy_match_score,
                    'dispute_match_score': result.dispute_match_score,
                    'vector_similarity': result.vector_similarity
                },
                metadata=result.metadata
            ))
        
        return unified
    
    def _convert_case_results(
        self,
        case_results: List[CaseSearchResult]
    ) -> List[UnifiedSearchResult]:
        """사례 검색 결과를 통합 형식으로 변환"""
        unified = []
        
        for result in case_results:
            unified.append(UnifiedSearchResult(
                chunk_id=result.chunk_id,
                doc_id=result.doc_id,
                content=result.content,
                doc_type='case',
                original_score=result.final_score,
                metadata_match_score=0.0,  # 나중에 계산
                importance_score=result.chunk_type_weight / 1.5,  # 정규화
                contextual_score=result.recency_score * 0.7 + result.agency_score * 0.3,
                final_score=0.0,
                source_info={
                    'chunk_type': result.chunk_type,
                    'case_no': result.case_no,
                    'decision_date': result.decision_date,
                    'agency': result.agency,
                    'category_path': result.category_path,
                    'vector_similarity': result.vector_similarity,
                    'chunk_type_weight': result.chunk_type_weight,
                    'recency_score': result.recency_score,
                    'agency_score': result.agency_score
                },
                metadata=result.metadata
            ))
        
        return unified
    
    def _calculate_metadata_match_score(
        self,
        result: UnifiedSearchResult,
        query_analysis: QueryAnalysis
    ) -> float:
        """
        메타데이터 매칭 점수 계산
        
        쿼리 분석 결과와 검색 결과의 메타데이터를 비교
        
        Args:
            result: 검색 결과
            query_analysis: 쿼리 분석 정보
        
        Returns:
            메타데이터 매칭 점수 (0~1)
        """
        score = 0.0
        match_count = 0
        total_checks = 0
        
        source_info = result.source_info
        
        # 1. 법령 매칭
        if result.doc_type == 'law':
            total_checks += 2
            
            # 조문 매칭
            if query_analysis.extracted_articles:
                for article_info in query_analysis.extracted_articles:
                    if article_info.get('article_no') == source_info.get('article_no'):
                        match_count += 1
                        break
            
            # 법령명 매칭
            if query_analysis.law_names and source_info.get('law_name'):
                if any(law in source_info['law_name'] for law in query_analysis.law_names):
                    match_count += 1
        
        # 2. 기준 매칭
        elif result.doc_type == 'criteria':
            total_checks += 2
            
            # 품목명 매칭
            if query_analysis.extracted_items and source_info.get('item_name'):
                if any(item.lower() in source_info['item_name'].lower() 
                       for item in query_analysis.extracted_items):
                    match_count += 1
            
            # 분쟁유형 매칭
            if query_analysis.dispute_types and source_info.get('dispute_type'):
                if any(dt in source_info['dispute_type'] 
                       for dt in query_analysis.dispute_types):
                    match_count += 1
        
        # 3. 사례 매칭
        elif result.doc_type == 'case':
            total_checks += 1
            
            # 카테고리 매칭
            if source_info.get('category_path'):
                category_match = False
                for cat in source_info['category_path']:
                    if any(kw in cat for kw in query_analysis.keywords):
                        category_match = True
                        break
                if category_match:
                    match_count += 1
        
        # 점수 계산
        if total_checks > 0:
            score = match_count / total_checks
        
        return score
    
    def deduplicate(
        self,
        results: List[UnifiedSearchResult],
        similarity_threshold: float = 0.95
    ) -> List[UnifiedSearchResult]:
        """
        유사한 결과 중복 제거
        
        Args:
            results: 검색 결과 리스트
            similarity_threshold: 유사도 임계값
        
        Returns:
            중복 제거된 결과 리스트
        """
        if not results:
            return []
        
        unique_results = []
        seen_content = set()
        
        for result in results:
            # 내용 기반 중복 체크 (간단한 버전)
            content_hash = hash(result.content[:200])  # 앞 200자로 판단
            
            if content_hash not in seen_content:
                seen_content.add(content_hash)
                unique_results.append(result)
        
        return unique_results
    
    def filter_by_score(
        self,
        results: List[UnifiedSearchResult],
        min_score: float = 0.3
    ) -> List[UnifiedSearchResult]:
        """
        최소 점수 이하 결과 필터링
        
        Args:
            results: 검색 결과 리스트
            min_score: 최소 점수
        
        Returns:
            필터링된 결과 리스트
        """
        return [r for r in results if r.final_score >= min_score]
