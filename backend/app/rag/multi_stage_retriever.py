"""
  RAG  
3        
"""

from typing import List, Dict, Optional
from .retriever import VectorRetriever
from .agency_recommender import AgencyRecommender


class MultiStageRetriever:
    """
      RAG  
    
    Stage 1:  +    ( )
    Stage 2:   ( )
    Stage 3:   (Fallback)
    """
    
    #    (   )
    CHUNK_TYPE_MAPPING = {
        'law': ['article', 'paragraph'],  # : , 
        'criteria': ['item_classification', 'resolution_row'],  # : , 
        'mediation': ['decision', 'parties_claim', 'judgment'],  # : , , 
        'counsel': ['qa_combined']  # : 
    }
    
    #    
    DOC_TYPE_MAPPING = {
        'law': ['law'],
        'criteria': ['criteria_item', 'criteria_resolution', 'criteria_warranty', 'criteria_lifespan'],
        'mediation': ['mediation_case'],
        'counsel': ['counsel_case']
    }
    
    def __init__(self, db_config: Dict, model_name: str = None):
        """
        Args:
            db_config:   
            model_name:   
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
         (//) 
        
        Args:
            query:  
            category: 'law', 'criteria', 'mediation', 'counsel'
            top_k:    
            agencies:   
            
        Returns:
              
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
        Stage 1:  +   
        
        Args:
            query:  
            law_top_k:    
            criteria_top_k:    
            
        Returns:
            {'law': [...], 'criteria': [...]}  
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
        Stage 2:   (Stage 1  )
        
        Args:
            query:  
            stage1_results: Stage 1  
            top_k:    
            agencies:   
            
        Returns:
               
        """
        # Stage 1    
        #       
        enhanced_query = query
        
        #      ( :  100)
        law_context = ""
        if stage1_results.get('law'):
            law_texts = [chunk['text'][:100] for chunk in stage1_results['law'][:2]]
            law_context = " ".join(law_texts)
        
        #     
        criteria_context = ""
        if stage1_results.get('criteria'):
            criteria_texts = [chunk['text'][:100] for chunk in stage1_results['criteria'][:2]]
            criteria_context = " ".join(criteria_texts)
        
        #     (,    )
        if law_context or criteria_context:
            enhanced_query = f"{query} {law_context} {criteria_context}"[:500]
        
        #  
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
        Stage 3:   (Fallback)
        
        Args:
            query:  
            top_k:    
            agencies:   
            
        Returns:
               
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
            
        
        Args:
            query:  
            law_top_k: Stage 1   
            criteria_top_k: Stage 1   
            mediation_top_k: Stage 2   
            counsel_top_k: Stage 3   
            mediation_threshold:    ( Fallback)
            agencies:   
            enable_agency_recommendation:    
            
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
        
        # Stage 1:  +  
        print(f"[Stage 1]     ...")
        stage1_results = self.search_stage1_legal(
            query=query,
            law_top_k=law_top_k,
            criteria_top_k=criteria_top_k
        )
        results['stage1'] = stage1_results
        print(f"  - : {len(stage1_results['law'])}")
        print(f"  - : {len(stage1_results['criteria'])}")
        
        # Stage 2:  
        print(f"[Stage 2]   ...")
        stage2_results = self.search_stage2_mediation(
            query=query,
            stage1_results=stage1_results,
            top_k=mediation_top_k,
            agencies=agencies
        )
        results['stage2'] = stage2_results
        print(f"  - : {len(stage2_results)}")
        
        # Stage 3: Fallback (  )
        used_fallback = False
        if len(stage2_results) < mediation_threshold:
            print(f"[Stage 3]   ({len(stage2_results)} < {mediation_threshold}),   ...")
            stage3_results = self.search_stage3_fallback(
                query=query,
                top_k=counsel_top_k,
                agencies=agencies
            )
            results['stage3'] = stage3_results
            print(f"  - : {len(stage3_results)}")
            used_fallback = True
        else:
            results['stage3'] = []
            print(f"[Stage 3]  , Fallback ")
        
        results['used_fallback'] = used_fallback
        
        #   
        all_chunks = []
        all_chunks.extend(stage1_results['law'])
        all_chunks.extend(stage1_results['criteria'])
        all_chunks.extend(stage2_results)
        all_chunks.extend(results['stage3'])
        
        results['all_chunks'] = all_chunks
        
        #  
        if enable_agency_recommendation:
            print(f"[Agency Recommendation]   ...")
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
                print(f"  -  : {top_info['name']} (: {top_score:.2f})")
        else:
            results['agency_recommendation'] = None
        
        #  
        results['stats'] = {
            'total_chunks': len(all_chunks),
            'law_chunks': len(stage1_results['law']),
            'criteria_chunks': len(stage1_results['criteria']),
            'mediation_chunks': len(stage2_results),
            'counsel_chunks': len(results['stage3']),
            'used_fallback': used_fallback
        }
        
        print(f"\n[]  {len(all_chunks)}  ")
        
        return results
    
    def close(self):
        """ """
        self.retriever.close()
