"""
Hybrid Retriever Module
질문 유형별로 적절한 전문 검색기를 조합하는 하이브리드 검색기
"""

from typing import List, Dict, Optional
from sentence_transformers import SentenceTransformer
import torch
import os

from .query_analyzer import QueryAnalyzer, QueryAnalysis, QueryType
from .specialized_retrievers.law_retriever import LawRetriever
from .specialized_retrievers.criteria_retriever import CriteriaRetriever
from .specialized_retrievers.case_retriever import CaseRetriever
from .reranker import Reranker, UnifiedSearchResult


class HybridRetriever:
    """하이브리드 검색기 - 질문 유형에 따라 적절한 검색 전략 적용"""
    
    # 질문 유형별 데이터 소스 가중치
    # Phase 2 개선: Criteria 우선순위 강화
    QUERY_TYPE_WEIGHTS = {
        QueryType.LEGAL: {          # 법률 질문
            'law': 0.7,             # 0.5 → 0.7 (Phase 1)
            'criteria': 0.2,        # 0.3 → 0.2
            'case': 0.1             # 0.2 → 0.1
        },
        QueryType.PRACTICAL: {       # 실무 질문
            'case': 0.6,            # 0.5 → 0.6 (Phase 1)
            'criteria': 0.25,       # 0.3 → 0.25
            'law': 0.15             # 0.2 → 0.15
        },
        QueryType.PRODUCT_SPECIFIC: {  # 품목별 기준 질문 (Phase 2 최우선)
            'criteria': 0.9,        # 0.8 → 0.9 (대폭 증가)
            'case': 0.08,           # 0.15 → 0.08 (감소)
            'law': 0.02             # 0.05 → 0.02 (감소)
        },
        QueryType.GENERAL: {         # 일반 질문
            'case': 0.3,            # 0.4 → 0.3 (Phase 1)
            'criteria': 0.35,       # 0.3 → 0.35
            'law': 0.35             # 0.3 → 0.35 (Phase 1, Law 향상)
        }
    }
    
    def __init__(
        self,
        db_config: Dict,
        model_name: str = None
    ):
        """
        Args:
            db_config: 데이터베이스 연결 설정
            model_name: 임베딩 모델 이름
        """
        self.db_config = db_config
        self.model_name = model_name or os.getenv('EMBEDDING_MODEL', 'nlpai-lab/KURE-v1')
        
        # 컴포넌트 초기화
        self.query_analyzer = QueryAnalyzer()
        self.law_retriever = LawRetriever(db_config)
        self.criteria_retriever = CriteriaRetriever(db_config)
        self.case_retriever = CaseRetriever(db_config)
        self.reranker = Reranker()
        
        # 임베딩 모델 (지연 로딩)
        self.model = None
    
    def load_model(self):
        """임베딩 모델 로드"""
        if self.model is None:
            print(f"Loading embedding model: {self.model_name}")
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            self.model = SentenceTransformer(self.model_name, device=device)
            print(f"Model loaded on {device}")
    
    def embed_query(self, query: str) -> List[float]:
        """
        쿼리 텍스트를 임베딩 벡터로 변환
        
        Args:
            query: 사용자 질문
        
        Returns:
            임베딩 벡터 (1024차원)
        """
        self.load_model()
        embedding = self.model.encode(query, convert_to_numpy=True)
        return embedding.tolist()
    
    def search(
        self,
        query: str,
        top_k: int = 10,
        agencies: Optional[List[str]] = None,
        enable_reranking: bool = True,
        min_score: float = 0.3,
        debug: bool = False
    ) -> List[UnifiedSearchResult]:
        """
        하이브리드 검색 실행
        
        Args:
            query: 사용자 질문
            top_k: 반환할 최대 결과 수
            agencies: 선호 기관 리스트 (사례 검색용)
            enable_reranking: 재랭킹 활성화 여부
            min_score: 최소 점수 임계값
            debug: 디버깅 로그 출력 여부
        
        Returns:
            통합 검색 결과 리스트
        """
        # 1. 쿼리 분석
        query_analysis = self.query_analyzer.analyze(query)
        
        if debug:
            print(f"\n[Hybrid Retriever DEBUG]")
            print(f"  Query Type: {query_analysis.query_type}")
        
        # 2. 쿼리 임베딩
        query_embedding = self.embed_query(query)
        
        # 3. 질문 유형별 가중치 결정
        weights = self.QUERY_TYPE_WEIGHTS.get(
            query_analysis.query_type,
            self.QUERY_TYPE_WEIGHTS[QueryType.GENERAL]
        )
        
        if debug:
            print(f"  Weights: {weights}")
        
        # 4. 각 데이터 소스별 검색 (가중치에 따라 top_k 조정)
        law_results = None
        criteria_results = None
        case_results = None
        
        if weights.get('law', 0) > 0:
            law_top_k = max(int(top_k * weights['law'] * 2), 3)
            law_results = self.law_retriever.search(
                query=query,
                query_analysis=query_analysis,
                query_embedding=query_embedding,
                top_k=law_top_k,
                debug=debug
            )
        
        if weights.get('criteria', 0) > 0:
            criteria_top_k = max(int(top_k * weights['criteria'] * 2), 3)
            criteria_results = self.criteria_retriever.search(
                query=query,
                query_analysis=query_analysis,
                query_embedding=query_embedding,
                top_k=criteria_top_k
            )
        
        if weights.get('case', 0) > 0:
            case_top_k = max(int(top_k * weights['case'] * 2), 5)
            case_results = self.case_retriever.search(
                query=query,
                query_analysis=query_analysis,
                query_embedding=query_embedding,
                agencies=agencies,
                top_k=case_top_k,
                debug=debug
            )
        
        # 5. 재랭킹
        if enable_reranking:
            unified_results = self.reranker.rerank(
                law_results=law_results,
                criteria_results=criteria_results,
                case_results=case_results,
                query_analysis=query_analysis,
                query=query
            )
        else:
            # 재랭킹 없이 단순 결합
            from .reranker import UnifiedSearchResult
            unified_results = []
            if law_results:
                unified_results.extend(self.reranker._convert_law_results(law_results))
            if criteria_results:
                unified_results.extend(self.reranker._convert_criteria_results(criteria_results))
            if case_results:
                unified_results.extend(self.reranker._convert_case_results(case_results))
        
        # 6. 중복 제거
        unique_results = self.reranker.deduplicate(unified_results)
        
        # 7. 최소 점수 필터링
        filtered_results = self.reranker.filter_by_score(unique_results, min_score=min_score)
        
        # 8. 상위 K개 반환
        return filtered_results[:top_k]
    
    def search_with_details(
        self,
        query: str,
        top_k: int = 10,
        agencies: Optional[List[str]] = None
    ) -> Dict:
        """
        상세 정보와 함께 검색 (디버깅 및 분석용)
        
        Args:
            query: 사용자 질문
            top_k: 반환할 최대 결과 수
            agencies: 선호 기관 리스트
        
        Returns:
            검색 결과 및 상세 정보
        """
        # 쿼리 분석
        query_analysis = self.query_analyzer.analyze(query)
        
        # 검색 실행
        results = self.search(query, top_k, agencies)
        
        # 상세 정보 구성
        return {
            'query': query,
            'query_analysis': {
                'query_type': query_analysis.query_type.value,
                'extracted_items': query_analysis.extracted_items,
                'extracted_articles': query_analysis.extracted_articles,
                'keywords': query_analysis.keywords[:10],  # 상위 10개만
                'dispute_types': query_analysis.dispute_types,
                'law_names': query_analysis.law_names,
                'has_amount': query_analysis.has_amount,
                'has_date': query_analysis.has_date
            },
            'weights': self.QUERY_TYPE_WEIGHTS[query_analysis.query_type],
            'results': [
                {
                    'chunk_id': r.chunk_id,
                    'doc_id': r.doc_id,
                    'content': r.content[:200] + '...' if len(r.content) > 200 else r.content,
                    'doc_type': r.doc_type,
                    'scores': {
                        'original': r.original_score,
                        'metadata_match': r.metadata_match_score,
                        'importance': r.importance_score,
                        'contextual': r.contextual_score,
                        'final': r.final_score
                    },
                    'source_info': r.source_info
                }
                for r in results
            ],
            'total_results': len(results)
        }
    
    def close(self):
        """리소스 정리"""
        self.law_retriever.close_db()
        self.criteria_retriever.close_db()
        self.case_retriever.close_db()


# 편의 함수
def create_hybrid_retriever(db_config: Dict) -> HybridRetriever:
    """하이브리드 검색기 생성 편의 함수"""
    return HybridRetriever(db_config)
