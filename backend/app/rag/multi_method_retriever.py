"""
Multi-Method Retriever Module
  (cosine, BM25, SPLADE, hybrid)   
"""

import os
import time
from typing import List, Dict, Optional
from pathlib import Path
import sys

#   
backend_dir = Path(__file__).parent.parent
project_root = backend_dir.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_dir))

from app.rag.retriever import VectorRetriever
from app.rag.hybrid_retriever import HybridRetriever

# BM25  SPLADE import ()
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
    """     """
    
    def __init__(self, db_config: Dict):
        """
        Args:
            db_config:   
        """
        self.db_config = db_config
        
        #  retriever 
        self.vector_retriever = VectorRetriever(db_config)
        self.hybrid_retriever = HybridRetriever(db_config)
        
        #  retriever 
        self.bm25_retriever = None
        self.splade_retriever = None
        
        if BM25_AVAILABLE:
            try:
                self.bm25_retriever = BM25SparseRetriever(db_config)
                print("BM25 Retriever 초기화 완료")
            except Exception as e:
                print(f"BM25 Retriever 초기화 실패: {e}")
        
        if SPLADE_AVAILABLE:
            try:
                self.splade_retriever = OptimizedSPLADEDBRetriever(db_config)
                print("SPLADE Retriever 초기화 완료")
            except Exception as e:
                print(f"SPLADE Retriever 초기화 실패: {e}")
    
    def _normalize_result(self, result: Dict, method_name: str, score_key: str = 'similarity') -> Dict:
        """
            
        
        Args:
            result:   
            method_name:   
            score_key:   
        
        Returns:
              
        """
        #   
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
        
        #  
        if 'metadata' in result:
            normalized['metadata'] = result['metadata']
        
        return normalized
    
    def search_cosine(self, query: str, top_k: int = 10) -> Dict:
        """
        Cosine Similarity 
        
        Args:
            query:  
            top_k:    
        
        Returns:
               (results, count, elapsed_time)
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
        BM25 
        
        Args:
            query:  
            top_k:    
        
        Returns:
              
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
            # BM25 , ,   
            law_results = self.bm25_retriever.search_law_bm25(query, top_k=top_k)
            criteria_results = self.bm25_retriever.search_criteria_bm25(query, top_k=top_k)
            
            #   ( + )
            mediation_results = []
            counsel_results = []
            if hasattr(self.bm25_retriever, 'search_mediation_bm25'):
                try:
                    mediation_results = self.bm25_retriever.search_mediation_bm25(query, top_k=top_k)
                except Exception as e:
                    print(f"Mediation BM25 검색 실패: {e}")
            
            if hasattr(self.bm25_retriever, 'search_counsel_bm25'):
                try:
                    counsel_results = self.bm25_retriever.search_counsel_bm25(query, top_k=top_k)
                except Exception as e:
                    print(f"Counsel BM25 검색 실패: {e}")
            
            #    
            all_results = []
            
            #  
            for r in law_results:
                normalized = self._normalize_result(r, 'bm25', 'bm25_score')
                normalized['source'] = 'law'
                all_results.append(normalized)
            
            #  
            for r in criteria_results:
                normalized = self._normalize_result(r, 'bm25', 'bm25_score')
                normalized['source'] = 'criteria'
                all_results.append(normalized)
            
            #   
            for r in mediation_results:
                normalized = self._normalize_result(r, 'bm25', 'bm25_score')
                normalized['source'] = 'mediation_case'
                normalized['case_no'] = r.get('case_no', '')
                normalized['decision_date'] = r.get('decision_date', '')
                normalized['agency'] = r.get('agency', '')
                all_results.append(normalized)
            
            #   
            for r in counsel_results:
                normalized = self._normalize_result(r, 'bm25', 'bm25_score')
                normalized['source'] = 'counsel_case'
                normalized['case_no'] = r.get('case_no', '')
                normalized['decision_date'] = r.get('decision_date', '')
                normalized['agency'] = r.get('agency', '')
                all_results.append(normalized)
            
            #   
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
        SPLADE 
        
        Args:
            query:  
            top_k:    
        
        Returns:
              
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
            # SPLADE    
            law_results = self.splade_retriever.search_law_splade_optimized(query, top_k=top_k)
            criteria_results = self.splade_retriever.search_criteria_splade_optimized(query, top_k=top_k)
            
            #    
            all_results = []
            for r in law_results:
                normalized = self._normalize_result(r, 'splade', 'splade_score')
                normalized['source'] = 'law'
                all_results.append(normalized)
            
            for r in criteria_results:
                normalized = self._normalize_result(r, 'splade', 'splade_score')
                normalized['source'] = 'criteria'
                all_results.append(normalized)
            
            #   
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
        Hybrid Search 
        
        Args:
            query:  
            top_k:    
        
        Returns:
              
        """
        start_time = time.time()
        try:
            results = self.hybrid_retriever.search(
                query=query,
                top_k=top_k,
                enable_reranking=True
            )
            
            # UnifiedSearchResult  
            normalized_results = []
            for r in results:
                # UnifiedSearchResult dataclass   
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
             
        
        Args:
            query:  
            top_k:      
            methods:     (None  )
                     : ['cosine', 'bm25', 'splade', 'hybrid']
        
        Returns:
                 
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
        """ """
        if self.vector_retriever:
            self.vector_retriever.close()
        if self.hybrid_retriever:
            # HybridRetriever close    
            pass
        if self.bm25_retriever and hasattr(self.bm25_retriever, 'conn'):
            if self.bm25_retriever.conn:
                self.bm25_retriever.conn.close()
        if self.splade_retriever and hasattr(self.splade_retriever, 'conn'):
            if self.splade_retriever.conn:
                self.splade_retriever.conn.close()
