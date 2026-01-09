"""
Multi-Method Retriever Module
모든 검색 방법(cosine, BM25, SPLADE, hybrid)을 통합하여 실행하는 모듈
"""

import os
import time
from typing import List, Dict, Optional
from pathlib import Path
import sys

# 프로젝트 경로 추가
backend_dir = Path(__file__).parent.parent
project_root = backend_dir.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_dir))

from app.rag.retriever import VectorRetriever
from app.rag.hybrid_retriever import HybridRetriever

# BM25 및 SPLADE import (선택적)
try:
    from scripts.splade.test_splade_bm25 import BM25SparseRetriever
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False
    BM25SparseRetriever = None

try:
    from scripts.splade.test_splade_optimized import OptimizedSPLADEDBRetriever
    SPLADE_AVAILABLE = True
except ImportError:
    SPLADE_AVAILABLE = False
    OptimizedSPLADEDBRetriever = None


class MultiMethodRetriever:
    """모든 검색 방법을 통합하여 실행하는 클래스"""
    
    def __init__(self, db_config: Dict):
        """
        Args:
            db_config: 데이터베이스 연결 설정
        """
        self.db_config = db_config
        
        # 기본 retriever 초기화
        self.vector_retriever = VectorRetriever(db_config)
        self.hybrid_retriever = HybridRetriever(db_config)
        
        # 선택적 retriever 초기화
        self.bm25_retriever = None
        self.splade_retriever = None
        
        if BM25_AVAILABLE:
            try:
                self.bm25_retriever = BM25SparseRetriever(db_config)
                print("✅ BM25 Retriever 초기화 완료")
            except Exception as e:
                print(f"⚠️  BM25 Retriever 초기화 실패: {e}")
        
        if SPLADE_AVAILABLE:
            try:
                self.splade_retriever = OptimizedSPLADEDBRetriever(db_config)
                print("✅ SPLADE Retriever 초기화 완료")
            except Exception as e:
                print(f"⚠️  SPLADE Retriever 초기화 실패: {e}")
    
    def _normalize_result(self, result: Dict, method_name: str, score_key: str = 'similarity') -> Dict:
        """
        검색 결과를 일관된 형식으로 정규화
        
        Args:
            result: 검색 결과 딕셔너리
            method_name: 검색 방법 이름
            score_key: 점수 필드 이름
        
        Returns:
            정규화된 결과 딕셔너리
        """
        # 공통 필드 매핑
        normalized = {
            'chunk_id': result.get('chunk_id') or result.get('chunk_uid'),
            'doc_id': result.get('doc_id') or result.get('case_uid'),
            'text': result.get('text') or result.get('content'),
            'chunk_type': result.get('chunk_type'),
            'source': result.get('source') or result.get('doc_type'),
            'agency': result.get('agency') or result.get('source_org'),
            'case_no': result.get('case_no') or result.get('title'),
            'decision_date': result.get('decision_date'),
            'method': method_name,
            'score': result.get(score_key, result.get('similarity', 0.0))
        }
        
        # 메타데이터 추가
        if 'metadata' in result:
            normalized['metadata'] = result['metadata']
        
        return normalized
    
    def search_cosine(self, query: str, top_k: int = 10) -> Dict:
        """
        Cosine Similarity 검색
        
        Args:
            query: 검색 쿼리
            top_k: 반환할 최대 결과 수
        
        Returns:
            검색 결과 딕셔너리 (results, count, elapsed_time)
        """
        start_time = time.time()
        try:
            results = self.vector_retriever.search(query=query, top_k=top_k)
            normalized_results = [
                self._normalize_result(r, 'cosine', 'similarity')
                for r in results
            ]
            elapsed = time.time() - start_time
            
            return {
                'method': 'cosine',
                'results': normalized_results,
                'count': len(normalized_results),
                'elapsed_time': elapsed,
                'success': True
            }
        except Exception as e:
            elapsed = time.time() - start_time
            return {
                'method': 'cosine',
                'results': [],
                'count': 0,
                'elapsed_time': elapsed,
                'success': False,
                'error': str(e)
            }
    
    def search_bm25(self, query: str, top_k: int = 10) -> Dict:
        """
        BM25 검색
        
        Args:
            query: 검색 쿼리
            top_k: 반환할 최대 결과 수
        
        Returns:
            검색 결과 딕셔너리
        """
        if not self.bm25_retriever:
            return {
                'method': 'bm25',
                'results': [],
                'count': 0,
                'elapsed_time': 0.0,
                'success': False,
                'error': 'BM25 Retriever not available'
            }
        
        start_time = time.time()
        try:
            # BM25는 법령, 기준, 사례 검색을 지원
            law_results = self.bm25_retriever.search_law_bm25(query, top_k=top_k)
            criteria_results = self.bm25_retriever.search_criteria_bm25(query, top_k=top_k)
            
            # 사례 검색 (분쟁조정 + 피해구제)
            mediation_results = []
            counsel_results = []
            if hasattr(self.bm25_retriever, 'search_mediation_bm25'):
                try:
                    mediation_results = self.bm25_retriever.search_mediation_bm25(query, top_k=top_k)
                except Exception as e:
                    print(f"⚠️  Mediation BM25 검색 실패: {e}")
            
            if hasattr(self.bm25_retriever, 'search_counsel_bm25'):
                try:
                    counsel_results = self.bm25_retriever.search_counsel_bm25(query, top_k=top_k)
                except Exception as e:
                    print(f"⚠️  Counsel BM25 검색 실패: {e}")
            
            # 결과 통합 및 정규화
            all_results = []
            
            # 법령 결과
            for r in law_results:
                normalized = self._normalize_result(r, 'bm25', 'bm25_score')
                normalized['source'] = 'law'
                all_results.append(normalized)
            
            # 기준 결과
            for r in criteria_results:
                normalized = self._normalize_result(r, 'bm25', 'bm25_score')
                normalized['source'] = 'criteria'
                all_results.append(normalized)
            
            # 분쟁조정 사례 결과
            for r in mediation_results:
                normalized = self._normalize_result(r, 'bm25', 'bm25_score')
                normalized['source'] = 'mediation_case'
                normalized['case_no'] = r.get('case_no', '')
                normalized['decision_date'] = r.get('decision_date', '')
                normalized['agency'] = r.get('agency', '')
                all_results.append(normalized)
            
            # 피해구제 사례 결과
            for r in counsel_results:
                normalized = self._normalize_result(r, 'bm25', 'bm25_score')
                normalized['source'] = 'counsel_case'
                normalized['case_no'] = r.get('case_no', '')
                normalized['decision_date'] = r.get('decision_date', '')
                normalized['agency'] = r.get('agency', '')
                all_results.append(normalized)
            
            # 점수 기준 정렬
            all_results.sort(key=lambda x: x['score'], reverse=True)
            all_results = all_results[:top_k]
            
            elapsed = time.time() - start_time
            
            return {
                'method': 'bm25',
                'results': all_results,
                'count': len(all_results),
                'elapsed_time': elapsed,
                'success': True
            }
        except Exception as e:
            elapsed = time.time() - start_time
            return {
                'method': 'bm25',
                'results': [],
                'count': 0,
                'elapsed_time': elapsed,
                'success': False,
                'error': str(e)
            }
    
    def search_splade(self, query: str, top_k: int = 10) -> Dict:
        """
        SPLADE 검색
        
        Args:
            query: 검색 쿼리
            top_k: 반환할 최대 결과 수
        
        Returns:
            검색 결과 딕셔너리
        """
        if not self.splade_retriever:
            return {
                'method': 'splade',
                'results': [],
                'count': 0,
                'elapsed_time': 0.0,
                'success': False,
                'error': 'SPLADE Retriever not available'
            }
        
        start_time = time.time()
        try:
            # SPLADE는 법령과 기준 검색을 지원
            law_results = self.splade_retriever.search_law_splade_optimized(query, top_k=top_k)
            criteria_results = self.splade_retriever.search_criteria_splade_optimized(query, top_k=top_k)
            
            # 결과 통합 및 정규화
            all_results = []
            for r in law_results:
                normalized = self._normalize_result(r, 'splade', 'splade_score')
                normalized['source'] = 'law'
                all_results.append(normalized)
            
            for r in criteria_results:
                normalized = self._normalize_result(r, 'splade', 'splade_score')
                normalized['source'] = 'criteria'
                all_results.append(normalized)
            
            # 점수 기준 정렬
            all_results.sort(key=lambda x: x['score'], reverse=True)
            all_results = all_results[:top_k]
            
            elapsed = time.time() - start_time
            
            return {
                'method': 'splade',
                'results': all_results,
                'count': len(all_results),
                'elapsed_time': elapsed,
                'success': True
            }
        except Exception as e:
            elapsed = time.time() - start_time
            return {
                'method': 'splade',
                'results': [],
                'count': 0,
                'elapsed_time': elapsed,
                'success': False,
                'error': str(e)
            }
    
    def search_hybrid(self, query: str, top_k: int = 10) -> Dict:
        """
        Hybrid Search 검색
        
        Args:
            query: 검색 쿼리
            top_k: 반환할 최대 결과 수
        
        Returns:
            검색 결과 딕셔너리
        """
        start_time = time.time()
        try:
            results = self.hybrid_retriever.search(
                query=query,
                top_k=top_k,
                enable_reranking=True
            )
            
            # UnifiedSearchResult를 딕셔너리로 변환
            normalized_results = []
            for r in results:
                # UnifiedSearchResult는 dataclass이므로 속성 직접 접근
                metadata = r.metadata if hasattr(r, 'metadata') else {}
                
                result_dict = {
                    'chunk_id': r.chunk_id,
                    'doc_id': r.doc_id,
                    'text': r.content,
                    'chunk_type': metadata.get('chunk_type', ''),
                    'source': r.doc_type,
                    'agency': metadata.get('agency', ''),
                    'case_no': metadata.get('case_no', ''),
                    'decision_date': metadata.get('decision_date', ''),
                    'similarity': r.final_score,
                    'metadata': metadata
                }
                normalized = self._normalize_result(result_dict, 'hybrid', 'similarity')
                normalized_results.append(normalized)
            
            elapsed = time.time() - start_time
            
            return {
                'method': 'hybrid',
                'results': normalized_results,
                'count': len(normalized_results),
                'elapsed_time': elapsed,
                'success': True
            }
        except Exception as e:
            elapsed = time.time() - start_time
            return {
                'method': 'hybrid',
                'results': [],
                'count': 0,
                'elapsed_time': elapsed,
                'success': False,
                'error': str(e)
            }
    
    def search_all_methods(
        self,
        query: str,
        top_k: int = 10,
        methods: Optional[List[str]] = None
    ) -> Dict:
        """
        모든 검색 방법을 실행하고 결과를 통합
        
        Args:
            query: 검색 쿼리
            top_k: 각 방법별 반환할 최대 결과 수
            methods: 실행할 검색 방법 리스트 (None이면 모두 실행)
                    가능한 값: ['cosine', 'bm25', 'splade', 'hybrid']
        
        Returns:
            모든 검색 방법의 결과를 포함한 딕셔너리
        """
        if methods is None:
            methods = ['cosine', 'bm25', 'splade', 'hybrid']
        
        all_results = {}
        
        if 'cosine' in methods:
            all_results['cosine'] = self.search_cosine(query, top_k)
        
        if 'bm25' in methods:
            all_results['bm25'] = self.search_bm25(query, top_k)
        
        if 'splade' in methods:
            all_results['splade'] = self.search_splade(query, top_k)
        
        if 'hybrid' in methods:
            all_results['hybrid'] = self.search_hybrid(query, top_k)
        
        return {
            'query': query,
            'methods': all_results,
            'total_methods': len(all_results),
            'successful_methods': sum(1 for m in all_results.values() if m.get('success', False))
        }
    
    def close(self):
        """리소스 정리"""
        if self.vector_retriever:
            self.vector_retriever.close()
        if self.hybrid_retriever:
            # HybridRetriever는 close 메서드가 없을 수 있음
            pass
        if self.bm25_retriever and hasattr(self.bm25_retriever, 'conn'):
            if self.bm25_retriever.conn:
                self.bm25_retriever.conn.close()
        if self.splade_retriever and hasattr(self.splade_retriever, 'conn'):
            if self.splade_retriever.conn:
                self.splade_retriever.conn.close()
