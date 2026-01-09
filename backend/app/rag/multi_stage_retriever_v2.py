"""
Multi-Stage RAG Retriever V2 (Hybrid Version)
하이브리드 검색기를 사용한 개선된 멀티 스테이지 검색 시스템
"""

from typing import List, Dict, Optional
from .hybrid_retriever import HybridRetriever
from .agency_recommender import AgencyRecommender
from .query_analyzer import QueryAnalyzer, QueryType


class MultiStageRetrieverV2:
    """
    하이브리드 검색 기반 멀티 스테이지 RAG 시스템
    
    개선 사항:
    - 질문 유형별 최적화된 검색 전략
    - 데이터 타입별 전문 검색기 활용
    - 메타데이터 기반 재랭킹
    - 중요도 및 최신성 고려
    """
    
    def __init__(self, db_config: Dict, model_name: str = None):
        """
        Args:
            db_config: 데이터베이스 연결 설정
            model_name: 임베딩 모델 이름
        """
        self.hybrid_retriever = HybridRetriever(db_config, model_name)
        self.query_analyzer = QueryAnalyzer()
        self.recommender = AgencyRecommender()
        self.db_config = db_config
    
    def search(
        self,
        query: str,
        top_k: int = 10,
        enable_agency_recommendation: bool = True,
        min_score: float = 0.3,
        debug: bool = False
    ) -> Dict:
        """
        통합 검색 (단일 단계, 하이브리드)
        
        Args:
            query: 사용자 질문
            top_k: 반환할 최대 결과 수
            enable_agency_recommendation: 기관 추천 활성화 여부
            min_score: 최소 점수 임계값
            debug: 디버깅 로그 출력 여부
        
        Returns:
            검색 결과 및 메타 정보
        """
        # 1. 쿼리 분석
        query_analysis = self.query_analyzer.analyze(query)
        
        # 2. 기관 추천 (분쟁조정기관)
        recommended_agencies = None
        if enable_agency_recommendation:
            recommendations = self.recommender.recommend(query, top_n=2)
            recommended_agencies = [rec[0] for rec in recommendations]  # agency codes
        
        # 3. 하이브리드 검색 실행
        results = self.hybrid_retriever.search(
            query=query,
            top_k=top_k,
            agencies=recommended_agencies,
            enable_reranking=True,
            min_score=min_score,
            debug=debug
        )
        
        # 4. 결과 구성
        return {
            'query': query,
            'query_type': query_analysis.query_type.value,
            'recommended_agencies': recommended_agencies,
            'results': self._format_results(results),
            'total_results': len(results),
            'metadata': {
                'extracted_items': query_analysis.extracted_items,
                'extracted_articles': query_analysis.extracted_articles,
                'dispute_types': query_analysis.dispute_types,
                'law_names': query_analysis.law_names
            }
        }
    
    def search_multi_stage(
        self,
        query: str,
        law_top_k: int = 3,
        criteria_top_k: int = 3,
        case_top_k: int = 5,
        enable_agency_recommendation: bool = True
    ) -> Dict:
        """
        멀티 스테이지 검색 (단계별 분리)
        
        기존 호환성을 위한 인터페이스
        
        Args:
            query: 사용자 질문
            law_top_k: 법령 검색 결과 수
            criteria_top_k: 기준 검색 결과 수
            case_top_k: 사례 검색 결과 수
            enable_agency_recommendation: 기관 추천 활성화 여부
        
        Returns:
            단계별 검색 결과
        """
        # 쿼리 분석
        query_analysis = self.query_analyzer.analyze(query)
        
        # 기관 추천
        recommended_agencies = None
        agency_info = {}
        if enable_agency_recommendation:
            recommendations = self.recommender.recommend(query, top_n=2)
            recommended_agencies = [rec[0] for rec in recommendations]
            agency_info = {
                'recommendations': [
                    {'code': rec[0], 'name': rec[2]['name'], 'score': rec[1]}
                    for rec in recommendations
                ]
            }
        
        # 쿼리 임베딩
        query_embedding = self.hybrid_retriever.embed_query(query)
        
        # Stage 1: 법령 검색
        law_results = []
        if law_top_k > 0:
            law_results = self.hybrid_retriever.law_retriever.search(
                query=query,
                query_analysis=query_analysis,
                query_embedding=query_embedding,
                top_k=law_top_k
            )
        
        # Stage 2: 기준 검색
        criteria_results = []
        if criteria_top_k > 0:
            criteria_results = self.hybrid_retriever.criteria_retriever.search(
                query=query,
                query_analysis=query_analysis,
                query_embedding=query_embedding,
                top_k=criteria_top_k
            )
        
        # Stage 3: 사례 검색
        case_results = []
        if case_top_k > 0:
            case_results = self.hybrid_retriever.case_retriever.search(
                query=query,
                query_analysis=query_analysis,
                query_embedding=query_embedding,
                agencies=recommended_agencies,
                top_k=case_top_k
            )
        
        # 재랭킹
        unified_results = self.hybrid_retriever.reranker.rerank(
            law_results=law_results,
            criteria_results=criteria_results,
            case_results=case_results,
            query_analysis=query_analysis,
            query=query
        )
        
        # 결과 구성
        return {
            'query': query,
            'query_type': query_analysis.query_type.value,
            'agencies': agency_info,
            'stage1': {
                'law': self._format_law_results(law_results),
                'criteria': self._format_criteria_results(criteria_results)
            },
            'stage2': {
                'cases': self._format_case_results(case_results)
            },
            'unified': self._format_results(unified_results),
            'metadata': {
                'law_count': len(law_results),
                'criteria_count': len(criteria_results),
                'case_count': len(case_results),
                'total_count': len(unified_results)
            }
        }
    
    def _format_results(self, results: List) -> List[Dict]:
        """통합 검색 결과 포맷팅"""
        formatted = []
        for r in results:
            formatted.append({
                'chunk_id': r.chunk_id,
                'doc_id': r.doc_id,
                'content': r.content,
                'doc_type': r.doc_type,
                'score': round(r.final_score, 4),
                'scores_detail': {
                    'original': round(r.original_score, 4),
                    'metadata_match': round(r.metadata_match_score, 4),
                    'importance': round(r.importance_score, 4),
                    'contextual': round(r.contextual_score, 4)
                },
                'source_info': r.source_info
            })
        return formatted
    
    def _format_law_results(self, results: List) -> List[Dict]:
        """법령 검색 결과 포맷팅"""
        formatted = []
        for r in results:
            formatted.append({
                'chunk_id': r.chunk_id,
                'law_name': r.law_name,
                'article_no': r.article_no,
                'path': r.path,
                'content': r.content,
                'score': round(r.final_score, 4),
                'scores': {
                    'exact_match': round(r.exact_match_score, 4),
                    'keyword_match': round(r.keyword_match_score, 4),
                    'vector_similarity': round(r.vector_similarity, 4)
                }
            })
        return formatted
    
    def _format_criteria_results(self, results: List) -> List[Dict]:
        """기준 검색 결과 포맷팅"""
        formatted = []
        for r in results:
            formatted.append({
                'chunk_id': r.chunk_id,
                'item_name': r.item_name,
                'category': r.category,
                'dispute_type': r.dispute_type,
                'content': r.content,
                'score': round(r.final_score, 4),
                'scores': {
                    'item_match': round(r.item_match_score, 4),
                    'hierarchy_match': round(r.hierarchy_match_score, 4),
                    'dispute_match': round(r.dispute_match_score, 4),
                    'vector_similarity': round(r.vector_similarity, 4)
                }
            })
        return formatted
    
    def _format_case_results(self, results: List) -> List[Dict]:
        """사례 검색 결과 포맷팅"""
        formatted = []
        for r in results:
            formatted.append({
                'chunk_id': r.chunk_id,
                'chunk_type': r.chunk_type,
                'case_no': r.case_no,
                'decision_date': r.decision_date,
                'agency': r.agency,
                'content': r.content,
                'score': round(r.final_score, 4),
                'scores': {
                    'vector_similarity': round(r.vector_similarity, 4),
                    'chunk_type_weight': round(r.chunk_type_weight, 4),
                    'recency_score': round(r.recency_score, 4),
                    'agency_score': round(r.agency_score, 4)
                }
            })
        return formatted
    
    def close(self):
        """리소스 정리"""
        self.hybrid_retriever.close()


# 편의 함수
def create_multi_stage_retriever_v2(db_config: Dict) -> MultiStageRetrieverV2:
    """멀티 스테이지 검색기 V2 생성"""
    return MultiStageRetrieverV2(db_config)
