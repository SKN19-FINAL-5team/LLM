"""
Reranker Module
     
"""

from typing import List, Dict, Any, Union
from dataclasses import dataclass, asdict
from .query_analyzer import QueryAnalysis
from .specialized_retrievers.law_retriever import LawSearchResult
from .specialized_retrievers.criteria_retriever import CriteriaSearchResult
from .specialized_retrievers.case_retriever import CaseSearchResult


@dataclass
class UnifiedSearchResult:
    """  """
    chunk_id: str
    doc_id: str
    content: str
    doc_type: str                  # 'law', 'criteria', 'case'
    original_score: float          #   
    metadata_match_score: float    #   
    importance_score: float        #   
    contextual_score: float        #   (,  )
    final_score: float             #   
    source_info: Dict              #    
    metadata: Dict


class Reranker:
    """ """
    
    #  
    ORIGINAL_SCORE_WEIGHT = 0.4      #   
    METADATA_MATCH_WEIGHT = 0.3      #  
    IMPORTANCE_WEIGHT = 0.2          # 
    CONTEXTUAL_WEIGHT = 0.1          #  
    
    def __init__(self):
        """"""
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
          
        
        Args:
            law_results:   
            criteria_results:   
            case_results:   
            query_analysis:   
            query:  
        
        Returns:
                
        """
        unified_results = []
        
        # 1.      
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
        
        # 2.    
        if query_analysis:
            for result in unified_results:
                result.metadata_match_score = self._calculate_metadata_match_score(
                    result, query_analysis
                )
        
        # 3.    (Phase 2  : Law/Criteria )
        TYPE_MULTIPLIERS = {
            'law': 1.8,       # Law   (1.5 → 1.8, )
            'criteria': 2.0,  # Criteria   (2.5 → 2.0, )
            'case': 1.0       # Case 
        }
        
        for result in unified_results:
            base_score = (
                result.original_score * self.ORIGINAL_SCORE_WEIGHT +
                result.metadata_match_score * self.METADATA_MATCH_WEIGHT +
                result.importance_score * self.IMPORTANCE_WEIGHT +
                result.contextual_score * self.CONTEXTUAL_WEIGHT
            )
            
            #   
            type_multiplier = TYPE_MULTIPLIERS.get(result.doc_type, 1.0)
            result.final_score = base_score * type_multiplier
        
        # 4.   
        unified_results.sort(key=lambda x: x.final_score, reverse=True)
        
        return unified_results
    
    def _convert_law_results(
        self,
        law_results: List[LawSearchResult]
    ) -> List[UnifiedSearchResult]:
        """     """
        unified = []
        
        for result in law_results:
            unified.append(UnifiedSearchResult(
                chunk_id=result.chunk_id,
                doc_id=result.doc_id,
                content=result.content,
                doc_type='law',
                original_score=result.final_score,
                metadata_match_score=0.0,  #  
                importance_score=0.8,  #   
                contextual_score=0.5,  #   
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
        """     """
        unified = []
        
        for result in criteria_results:
            unified.append(UnifiedSearchResult(
                chunk_id=result.chunk_id,
                doc_id=result.doc_id,
                content=result.content,
                doc_type='criteria',
                original_score=result.final_score,
                metadata_match_score=0.0,  #  
                importance_score=0.9,  #   
                contextual_score=0.5,  #   
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
        """     """
        unified = []
        
        for result in case_results:
            unified.append(UnifiedSearchResult(
                chunk_id=result.chunk_id,
                doc_id=result.doc_id,
                content=result.content,
                doc_type='case',
                original_score=result.final_score,
                metadata_match_score=0.0,  #  
                importance_score=result.chunk_type_weight / 1.5,  # 
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
           
        
              
        
        Args:
            result:  
            query_analysis:   
        
        Returns:
               (0~1)
        """
        score = 0.0
        match_count = 0
        total_checks = 0
        
        source_info = result.source_info
        
        # 1.  
        if result.doc_type == 'law':
            total_checks += 2
            
            #  
            if query_analysis.extracted_articles:
                for article_info in query_analysis.extracted_articles:
                    if article_info.get('article_no') == source_info.get('article_no'):
                        match_count += 1
                        break
            
            #  
            if query_analysis.law_names and source_info.get('law_name'):
                if any(law in source_info['law_name'] for law in query_analysis.law_names):
                    match_count += 1
        
        # 2.  
        elif result.doc_type == 'criteria':
            total_checks += 2
            
            #  
            if query_analysis.extracted_items and source_info.get('item_name'):
                if any(item.lower() in source_info['item_name'].lower() 
                       for item in query_analysis.extracted_items):
                    match_count += 1
            
            #  
            if query_analysis.dispute_types and source_info.get('dispute_type'):
                if any(dt in source_info['dispute_type'] 
                       for dt in query_analysis.dispute_types):
                    match_count += 1
        
        # 3.  
        elif result.doc_type == 'case':
            total_checks += 1
            
            #  
            if source_info.get('category_path'):
                category_match = False
                for cat in source_info['category_path']:
                    if any(kw in cat for kw in query_analysis.keywords):
                        category_match = True
                        break
                if category_match:
                    match_count += 1
        
        #  
        if total_checks > 0:
            score = match_count / total_checks
        
        return score
    
    def deduplicate(
        self,
        results: List[UnifiedSearchResult],
        similarity_threshold: float = 0.95
    ) -> List[UnifiedSearchResult]:
        """
           
        
        Args:
            results:   
            similarity_threshold:  
        
        Returns:
               
        """
        if not results:
            return []
        
        unique_results = []
        seen_content = set()
        
        for result in results:
            #     ( )
            content_hash = hash(result.content[:200])  #  200 
            
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
            
        
        Args:
            results:   
            min_score:  
        
        Returns:
              
        """
        return [r for r in results if r.final_score >= min_score]
