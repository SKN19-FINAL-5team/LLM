"""
멀티 스테이지 RAG 검색 모듈
3단계 계층적 검색을 통해 더 정확하고 풍부한 컨텍스트 제공
"""

from typing import List, Dict, Optional
from .retriever import VectorRetriever
from .agency_recommender import AgencyRecommender


class MultiStageRetriever:
    """
    멀티 스테이지 RAG 검색 시스템
    
    Stage 1: 법령 + 소비자분쟁기준 병렬 검색 (기반 규칙)
    Stage 2: 분쟁조정사례 검색 (유사 사례)
    Stage 3: 피해구제사례 검색 (Fallback)
    """
    
    # 청크 타입 매핑 (현재 데이터베이스 스키마에 맞춤)
    CHUNK_TYPE_MAPPING = {
        'law': ['article', 'paragraph'],  # 법령: 조문, 항
        'criteria': ['item_classification', 'resolution_row'],  # 분쟁조정기준: 품목분류, 해결기준
        'mediation': ['decision', 'parties_claim', 'judgment'],  # 분쟁조정사례: 결정, 당사자주장, 판단
        'counsel': ['qa_combined']  # 피해구제사례: 질의응답
    }
    
    # 문서 타입별 소스 매핑
    DOC_TYPE_MAPPING = {
        'law': ['law'],
        'criteria': ['criteria_item', 'criteria_resolution', 'criteria_warranty', 'criteria_lifespan'],
        'mediation': ['mediation_case'],
        'counsel': ['counsel_case']
    }
    
    def __init__(self, db_config: Dict, model_name: str = None):
        """
        Args:
            db_config: 데이터베이스 연결 설정
            model_name: 임베딩 모델 이름
        """
        self.retriever = VectorRetriever(db_config, model_name)
        self.recommender = AgencyRecommender()
        
    def _search_by_category(
        self,
        query: str,
        category: str,
        top_k: int,
        agencies: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        특정 카테고리(법령/기준/사례)로 검색
        
        Args:
            query: 검색 쿼리
            category: 'law', 'criteria', 'mediation', 'counsel'
            top_k: 반환할 최대 결과 수
            agencies: 필터링할 기관 리스트
            
        Returns:
            검색된 청크 리스트
        """
        chunk_types = self.CHUNK_TYPE_MAPPING.get(category, [])
        if not chunk_types:
            return []
        
        return self.retriever.search(
            query=query,
            top_k=top_k,
            chunk_types=chunk_types,
            agencies=agencies
        )
    
    def search_stage1_legal(
        self,
        query: str,
        law_top_k: int = 3,
        criteria_top_k: int = 3
    ) -> Dict[str, List[Dict]]:
        """
        Stage 1: 법령 + 분쟁조정기준 병렬 검색
        
        Args:
            query: 사용자 질문
            law_top_k: 법령 검색 결과 수
            criteria_top_k: 기준 검색 결과 수
            
        Returns:
            {'law': [...], 'criteria': [...]} 형태의 딕셔너리
        """
        law_chunks = self._search_by_category(
            query=query,
            category='law',
            top_k=law_top_k
        )
        
        criteria_chunks = self._search_by_category(
            query=query,
            category='criteria',
            top_k=criteria_top_k
        )
        
        return {
            'law': law_chunks,
            'criteria': criteria_chunks
        }
    
    def search_stage2_mediation(
        self,
        query: str,
        stage1_results: Dict[str, List[Dict]],
        top_k: int = 5,
        agencies: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Stage 2: 분쟁조정사례 검색 (Stage 1 컨텍스트 활용)
        
        Args:
            query: 사용자 질문
            stage1_results: Stage 1 검색 결과
            top_k: 반환할 최대 결과 수
            agencies: 필터링할 기관 리스트
            
        Returns:
            검색된 분쟁조정사례 청크 리스트
        """
        # Stage 1 결과를 컨텍스트로 쿼리 확장
        # 법령과 기준에서 핵심 키워드 추출하여 쿼리에 추가
        enhanced_query = query
        
        # 법령 텍스트에서 중요 키워드 추출 (간단한 방법: 처음 100자)
        law_context = ""
        if stage1_results.get('law'):
            law_texts = [chunk['text'][:100] for chunk in stage1_results['law'][:2]]
            law_context = " ".join(law_texts)
        
        # 기준 텍스트에서 중요 키워드 추출
        criteria_context = ""
        if stage1_results.get('criteria'):
            criteria_texts = [chunk['text'][:100] for chunk in stage1_results['criteria'][:2]]
            criteria_context = " ".join(criteria_texts)
        
        # 컨텍스트가 있으면 쿼리 확장 (단, 너무 길어지지 않도록 제한)
        if law_context or criteria_context:
            enhanced_query = f"{query} {law_context} {criteria_context}"[:500]
        
        # 분쟁조정사례 검색
        mediation_chunks = self._search_by_category(
            query=enhanced_query,
            category='mediation',
            top_k=top_k,
            agencies=agencies
        )
        
        return mediation_chunks
    
    def search_stage3_fallback(
        self,
        query: str,
        top_k: int = 3,
        agencies: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Stage 3: 피해구제사례 검색 (Fallback)
        
        Args:
            query: 사용자 질문
            top_k: 반환할 최대 결과 수
            agencies: 필터링할 기관 리스트
            
        Returns:
            검색된 피해구제사례 청크 리스트
        """
        counsel_chunks = self._search_by_category(
            query=query,
            category='counsel',
            top_k=top_k,
            agencies=agencies
        )
        
        return counsel_chunks
    
    def search_multi_stage(
        self,
        query: str,
        law_top_k: int = 3,
        criteria_top_k: int = 3,
        mediation_top_k: int = 5,
        counsel_top_k: int = 3,
        mediation_threshold: int = 2,
        agencies: Optional[List[str]] = None,
        enable_agency_recommendation: bool = True
    ) -> Dict:
        """
        전체 멀티 스테이지 검색 실행
        
        Args:
            query: 사용자 질문
            law_top_k: Stage 1 법령 검색 수
            criteria_top_k: Stage 1 기준 검색 수
            mediation_top_k: Stage 2 분쟁조정사례 검색 수
            counsel_top_k: Stage 3 피해구제사례 검색 수
            mediation_threshold: 분쟁조정사례 최소 개수 (이하면 Fallback)
            agencies: 필터링할 기관 리스트
            enable_agency_recommendation: 기관 추천 활성화 여부
            
        Returns:
            {
                'stage1': {'law': [...], 'criteria': [...]},
                'stage2': [...],
                'stage3': [...],
                'all_chunks': [...],
                'used_fallback': bool,
                'agency_recommendation': {...}
            }
        """
        results = {}
        
        # Stage 1: 법령 + 기준 검색
        print(f"[Stage 1] 법령 및 분쟁조정기준 검색 중...")
        stage1_results = self.search_stage1_legal(
            query=query,
            law_top_k=law_top_k,
            criteria_top_k=criteria_top_k
        )
        results['stage1'] = stage1_results
        print(f"  - 법령: {len(stage1_results['law'])}건")
        print(f"  - 기준: {len(stage1_results['criteria'])}건")
        
        # Stage 2: 분쟁조정사례 검색
        print(f"[Stage 2] 분쟁조정사례 검색 중...")
        stage2_results = self.search_stage2_mediation(
            query=query,
            stage1_results=stage1_results,
            top_k=mediation_top_k,
            agencies=agencies
        )
        results['stage2'] = stage2_results
        print(f"  - 분쟁조정사례: {len(stage2_results)}건")
        
        # Stage 3: Fallback (분쟁조정사례가 부족한 경우)
        used_fallback = False
        if len(stage2_results) < mediation_threshold:
            print(f"[Stage 3] 분쟁조정사례 부족 ({len(stage2_results)}건 < {mediation_threshold}건), 피해구제사례 검색 중...")
            stage3_results = self.search_stage3_fallback(
                query=query,
                top_k=counsel_top_k,
                agencies=agencies
            )
            results['stage3'] = stage3_results
            print(f"  - 피해구제사례: {len(stage3_results)}건")
            used_fallback = True
        else:
            results['stage3'] = []
            print(f"[Stage 3] 분쟁조정사례 충분, Fallback 건너뜀")
        
        results['used_fallback'] = used_fallback
        
        # 모든 청크 통합
        all_chunks = []
        all_chunks.extend(stage1_results['law'])
        all_chunks.extend(stage1_results['criteria'])
        all_chunks.extend(stage2_results)
        all_chunks.extend(results['stage3'])
        
        results['all_chunks'] = all_chunks
        
        # 기관 추천
        if enable_agency_recommendation:
            print(f"[Agency Recommendation] 기관 추천 중...")
            recommendations = self.recommender.recommend(
                query=query,
                search_results=all_chunks
            )
            results['agency_recommendation'] = {
                'recommendations': recommendations,
                'top_agency': recommendations[0] if recommendations else None,
                'formatted': self.recommender.format_recommendation_text(query, all_chunks)
            }
            if recommendations:
                top_agency_code, top_score, top_info = recommendations[0]
                print(f"  - 추천 기관: {top_info['name']} (점수: {top_score:.2f})")
        else:
            results['agency_recommendation'] = None
        
        # 통계 정보
        results['stats'] = {
            'total_chunks': len(all_chunks),
            'law_chunks': len(stage1_results['law']),
            'criteria_chunks': len(stage1_results['criteria']),
            'mediation_chunks': len(stage2_results),
            'counsel_chunks': len(results['stage3']),
            'used_fallback': used_fallback
        }
        
        print(f"\n[완료] 총 {len(all_chunks)}개 청크 검색")
        
        return results
    
    def close(self):
        """리소스 정리"""
        self.retriever.close()
