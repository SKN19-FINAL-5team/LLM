"""
Multi-Stage RAG Retriever V2 (Hybrid Version)
       
"""

from typing import List, Dict, Optional
from .hybrid_retriever import HybridRetriever
from .agency_recommender import AgencyRecommender
from .query_analyzer import QueryAnalyzer, QueryType


class MultiStageRetrieverV2:
    """
         RAG 
    
     :
    -     
    -     
    -   
    -    
    """
    
    def __init__(self, db_config: Dict, model_name: str = None):
        """
        Args:
            db_config:   
            model_name:   
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
          ( , )
        
        Args:
            query:  
            top_k:    
            enable_agency_recommendation:    
            min_score:   
            debug:    
        
        Returns:
                
        """
        # 1.  
        query_analysis = self.query_analyzer.analyze(query)
        
        # 2.   ()
        recommended_agencies = None
        if enable_agency_recommendation:
            recommendations = self.recommender.recommend(query, top_n=2)
            recommended_agencies = [rec[0] for rec in recommendations]  # agency codes
        
        # 3.   
        results = self.hybrid_retriever.search(
            query=query,
            top_k=top_k,
            agencies=recommended_agencies,
            enable_reranking=True,
            min_score=min_score,
            debug=debug
        )
        
        # 4.  
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
           ( )
        
           
        
        Args:
            query:  
            law_top_k:    
            criteria_top_k:    
            case_top_k:    
            enable_agency_recommendation:    
        
        Returns:
              
        """
        #  
        query_analysis = self.query_analyzer.analyze(query)
        
        #  
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
        
        #  
        query_embedding = self.hybrid_retriever.embed_query(query)
        
        # Stage 1:  
        law_results = []
        if law_top_k > 0:
            law_results = self.hybrid_retriever.law_retriever.search(
                query=query,
                query_analysis=query_analysis,
                query_embedding=query_embedding,
                top_k=law_top_k
            )
        
        # Stage 2:  
        criteria_results = []
        if criteria_top_k > 0:
            criteria_results = self.hybrid_retriever.criteria_retriever.search(
                query=query,
                query_analysis=query_analysis,
                query_embedding=query_embedding,
                top_k=criteria_top_k
            )
        
        # Stage 3:  
        case_results = []
        if case_top_k > 0:
            case_results = self.hybrid_retriever.case_retriever.search(
                query=query,
                query_analysis=query_analysis,
                query_embedding=query_embedding,
                agencies=recommended_agencies,
                top_k=case_top_k
            )
        
        # 
        unified_results = self.hybrid_retriever.reranker.rerank(
            law_results=law_results,
            criteria_results=criteria_results,
            case_results=case_results,
            query_analysis=query_analysis,
            query=query
        )
        
        #  
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
        """   """
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
        """   """
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
        """   """
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
        """   """
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
        """ """
        self.hybrid_retriever.close()


#  
def create_multi_stage_retriever_v2(db_config: Dict) -> MultiStageRetrieverV2:
    """   V2 """
    return MultiStageRetrieverV2(db_config)
