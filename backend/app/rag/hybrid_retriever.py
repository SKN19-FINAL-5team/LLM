"""
Hybrid Retriever Module
       
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
    """  -       """
    
    #     
    # Phase 2 : Criteria  
    QUERY_TYPE_WEIGHTS = {
        QueryType.LEGAL: {          #  
            'law': 0.7,             # 0.5 → 0.7 (Phase 1)
            'criteria': 0.2,        # 0.3 → 0.2
            'case': 0.1             # 0.2 → 0.1
        },
        QueryType.PRACTICAL: {       #  
            'case': 0.6,            # 0.5 → 0.6 (Phase 1)
            'criteria': 0.25,       # 0.3 → 0.25
            'law': 0.15             # 0.2 → 0.15
        },
        QueryType.PRODUCT_SPECIFIC: {  #    (Phase 2 )
            'criteria': 0.9,        # 0.8 → 0.9 ( )
            'case': 0.08,           # 0.15 → 0.08 ()
            'law': 0.02             # 0.05 → 0.02 ()
        },
        QueryType.GENERAL: {         #  
            'case': 0.3,            # 0.4 → 0.3 (Phase 1)
            'criteria': 0.35,       # 0.3 → 0.35
            'law': 0.35             # 0.3 → 0.35 (Phase 1, Law )
        }
    }
    
    def __init__(
        self,
        db_config: Dict,
        model_name: str = None
    ):
        """
        Args:
            db_config:   
            model_name:   
        """
        self.db_config = db_config
        self.model_name = model_name or os.getenv('EMBEDDING_MODEL', 'nlpai-lab/KURE-v1')
        
        #  
        self.query_analyzer = QueryAnalyzer()
        self.law_retriever = LawRetriever(db_config)
        self.criteria_retriever = CriteriaRetriever(db_config)
        self.case_retriever = CaseRetriever(db_config)
        self.reranker = Reranker()
        
        #   ( )
        self.model = None
    
    def load_model(self):
        """  """
        if self.model is None:
            print(f"Loading embedding model: {self.model_name}")
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            self.model = SentenceTransformer(self.model_name, device=device)
            print(f"Model loaded on {device}")
    
    def embed_query(self, query: str) -> List[float]:
        """
            
        
        Args:
            query:  
        
        Returns:
              (1024)
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
          
        
        Args:
            query:  
            top_k:    
            agencies:    ( )
            enable_reranking:   
            min_score:   
            debug:    
        
        Returns:
               
        """
        # 1.  
        query_analysis = self.query_analyzer.analyze(query)
        
        if debug:
            print(f"\n[Hybrid Retriever DEBUG]")
            print(f"  Query Type: {query_analysis.query_type}")
        
        # 2.  
        query_embedding = self.embed_query(query)
        
        # 3.    
        weights = self.QUERY_TYPE_WEIGHTS.get(
            query_analysis.query_type,
            self.QUERY_TYPE_WEIGHTS[QueryType.GENERAL]
        )
        
        if debug:
            print(f"  Weights: {weights}")
        
        # 4.     (  top_k )
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
        
        # 5. 
        if enable_reranking:
            unified_results = self.reranker.rerank(
                law_results=law_results,
                criteria_results=criteria_results,
                case_results=case_results,
                query_analysis=query_analysis,
                query=query
            )
        else:
            #    
            from .reranker import UnifiedSearchResult
            unified_results = []
            if law_results:
                unified_results.extend(self.reranker._convert_law_results(law_results))
            if criteria_results:
                unified_results.extend(self.reranker._convert_criteria_results(criteria_results))
            if case_results:
                unified_results.extend(self.reranker._convert_case_results(case_results))
        
        # 6.  
        unique_results = self.reranker.deduplicate(unified_results)
        
        # 7.   
        filtered_results = self.reranker.filter_by_score(unique_results, min_score=min_score)
        
        # 8.  K 
        return filtered_results[:top_k]
    
    def search_with_details(
        self,
        query: str,
        top_k: int = 10,
        agencies: Optional[List[str]] = None
    ) -> Dict:
        """
            (  )
        
        Args:
            query:  
            top_k:    
            agencies:   
        
        Returns:
                
        """
        #  
        query_analysis = self.query_analyzer.analyze(query)
        
        #  
        results = self.search(query, top_k, agencies)
        
        #   
        return {
            'query': query,
            'query_analysis': {
                'query_type': query_analysis.query_type.value,
                'extracted_items': query_analysis.extracted_items,
                'extracted_articles': query_analysis.extracted_articles,
                'keywords': query_analysis.keywords[:10],  #  10
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
        """ """
        self.law_retriever.close_db()
        self.criteria_retriever.close_db()
        self.case_retriever.close_db()


#  
def create_hybrid_retriever(db_config: Dict) -> HybridRetriever:
    """    """
    return HybridRetriever(db_config)
