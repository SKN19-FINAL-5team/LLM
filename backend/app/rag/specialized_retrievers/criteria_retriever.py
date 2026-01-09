"""
Criteria Retriever Module
   -   +   +  +   
"""

import psycopg2
from typing import List, Dict, Optional
from dataclasses import dataclass
from ..query_analyzer import QueryAnalysis


@dataclass
class CriteriaSearchResult:
    """  """
    chunk_id: str
    doc_id: str
    content: str
    item_name: Optional[str]
    category: Optional[str]
    industry: Optional[str]
    item_group: Optional[str]
    dispute_type: Optional[str]
    item_match_score: float       #   
    hierarchy_match_score: float  #    
    dispute_match_score: float    #   
    vector_similarity: float      #  
    final_score: float            #  
    metadata: Dict


class CriteriaRetriever:
    """   (Phase 2 )"""
    
    #   (Phase 2:  )
    ITEM_MATCH_WEIGHT = 0.6      #   (0.4 → 0.6, )
    KEYWORD_WEIGHT = 0.2         #   ()
    HIERARCHY_WEIGHT = 0.1       #    (0.3 → 0.1)
    DISPUTE_WEIGHT = 0.1         #   (0.2 → 0.1)
    VECTOR_WEIGHT = 0.0          #   (0.1 → 0.0, )
    
    #     (Phase 2  )
    EXACT_ITEM_MATCH_BONUS = 2.0  #    +2.0   (3.0 → 2.0)
    
    def __init__(self, db_config: Dict):
        """
        Args:
            db_config:   
        """
        self.db_config = db_config
        self.conn = None
        self.cur = None
    
    def connect_db(self):
        """DB """
        if self.conn is None or self.conn.closed:
            self.conn = psycopg2.connect(**self.db_config)
            self.cur = self.conn.cursor()
    
    def close_db(self):
        """DB  """
        if self.cur:
            self.cur.close()
        if self.conn:
            self.conn.close()
    
    def search(
        self,
        query: str,
        query_analysis: QueryAnalysis,
        query_embedding: Optional[List[float]] = None,
        top_k: int = 10
    ) -> List[CriteriaSearchResult]:
        """
         
        
        Args:
            query:  
            query_analysis:   
            query_embedding:    ()
            top_k:    
        
        Returns:
               
        """
        self.connect_db()
        
        results = []
        
        # 1.   
        if query_analysis.extracted_items:
            item_results = self._item_name_search(
                query_analysis.extracted_items,
                query_analysis.dispute_types
            )
            results.extend(item_results)
        
        # 2.  +  
        if query_analysis.dispute_types:
            dispute_results = self._dispute_type_search(
                query_analysis.dispute_types,
                query_analysis.keywords,
                top_k=top_k * 2
            )
            results.extend(dispute_results)
        
        # 3.    ()
        if query_embedding:
            vector_results = self._vector_search(
                query_embedding,
                top_k=top_k
            )
            results.extend(vector_results)
        
        # 4.     
        unique_results = self._deduplicate_and_score(results, query_analysis)
        
        # 5.  K 
        unique_results.sort(key=lambda x: x.final_score, reverse=True)
        return unique_results[:top_k]
    
    def _item_name_search(
        self,
        item_names: List[str],
        dispute_types: List[str]
    ) -> List[CriteriaSearchResult]:
        """
           
        
        Args:
            item_names:   
            dispute_types:   
        
        Returns:
              
        """
        results = []
        
        for item_name in item_names:
            #   (aliases) 
            sql = """
                SELECT 
                    c.chunk_id,
                    c.doc_id,
                    c.content,
                    d.metadata
                FROM chunks c
                JOIN documents d ON c.doc_id = d.doc_id
                WHERE 
                    (d.doc_type LIKE 'criteria%%' OR d.doc_type LIKE 'guideline%%')
                    AND c.drop = FALSE
                    AND (
                        d.metadata->>'item_name' ILIKE %s
                        OR jsonb_exists(d.metadata->'aliases', %s)
                        OR c.content ILIKE %s
                    )
                ORDER BY c.chunk_index
                LIMIT 10
            """
            
            search_pattern = f'%{item_name}%'
            
            self.cur.execute(sql, (search_pattern, item_name, search_pattern))
            rows = self.cur.fetchall()
            
            for row in rows:
                chunk_id, doc_id, content, metadata = row
                metadata = metadata or {}
                
                #     
                item_match_score = 1.0 if metadata.get('item_name', '').lower() == item_name.lower() else 0.8
                
                #   
                dispute_match_score = 0.0
                if dispute_types and metadata.get('dispute_type'):
                    if any(dt in metadata.get('dispute_type', '') for dt in dispute_types):
                        dispute_match_score = 1.0
                
                results.append(CriteriaSearchResult(
                    chunk_id=chunk_id,
                    doc_id=doc_id,
                    content=content,
                    item_name=metadata.get('item_name'),
                    category=metadata.get('category'),
                    industry=metadata.get('industry'),
                    item_group=metadata.get('item_group'),
                    dispute_type=metadata.get('dispute_type'),
                    item_match_score=item_match_score,
                    hierarchy_match_score=0.0,  #  
                    dispute_match_score=dispute_match_score,
                    vector_similarity=0.0,
                    final_score=0.0,
                    metadata=metadata
                ))
        
        return results
    
    def _dispute_type_search(
        self,
        dispute_types: List[str],
        keywords: List[str],
        top_k: int = 20
    ) -> List[CriteriaSearchResult]:
        """
         +  
        
        Args:
            dispute_types:   
            keywords:  
            top_k:    
        
        Returns:
              
        """
        results = []
        
        #    
        for dispute_type in dispute_types:
            sql = """
                SELECT 
                    c.chunk_id,
                    c.doc_id,
                    c.content,
                    d.metadata
                FROM chunks c
                JOIN documents d ON c.doc_id = d.doc_id
                WHERE 
                    (d.doc_type LIKE 'criteria%%' OR d.doc_type LIKE 'guideline%%')
                    AND c.drop = FALSE
                    AND (
                        d.metadata->>'dispute_type' ILIKE %s
                        OR c.content ILIKE %s
                    )
                ORDER BY c.importance_score DESC
                LIMIT %s
            """
            
            search_pattern = f'%{dispute_type}%'
            
            self.cur.execute(sql, (search_pattern, search_pattern, top_k))
            rows = self.cur.fetchall()
            
            for row in rows:
                chunk_id, doc_id, content, metadata = row
                metadata = metadata or {}
                
                results.append(CriteriaSearchResult(
                    chunk_id=chunk_id,
                    doc_id=doc_id,
                    content=content,
                    item_name=metadata.get('item_name'),
                    category=metadata.get('category'),
                    industry=metadata.get('industry'),
                    item_group=metadata.get('item_group'),
                    dispute_type=metadata.get('dispute_type'),
                    item_match_score=0.0,
                    hierarchy_match_score=0.0,
                    dispute_match_score=1.0,
                    vector_similarity=0.0,
                    final_score=0.0,
                    metadata=metadata
                ))
        
        return results
    
    def _vector_search(
        self,
        query_embedding: List[float],
        top_k: int = 10
    ) -> List[CriteriaSearchResult]:
        """
          
        
        Args:
            query_embedding:  
            top_k:    
        
        Returns:
              
        """
        sql = """
            SELECT 
                c.chunk_id,
                c.doc_id,
                c.content,
                d.metadata,
                1 - (c.embedding <=> %s::vector) AS similarity
            FROM chunks c
            JOIN documents d ON c.doc_id = d.doc_id
            WHERE 
                (d.doc_type LIKE 'criteria%%%%' OR d.doc_type LIKE 'guideline%%%%')
                AND c.drop = FALSE
                AND c.embedding IS NOT NULL
            ORDER BY c.embedding <=> %s::vector
            LIMIT %s
        """
        
        self.cur.execute(sql, (query_embedding, query_embedding, top_k))
        rows = self.cur.fetchall()
        
        results = []
        for row in rows:
            chunk_id, doc_id, content, metadata, similarity = row
            metadata = metadata or {}
            
            results.append(CriteriaSearchResult(
                chunk_id=chunk_id,
                doc_id=doc_id,
                content=content,
                item_name=metadata.get('item_name'),
                category=metadata.get('category'),
                industry=metadata.get('industry'),
                item_group=metadata.get('item_group'),
                dispute_type=metadata.get('dispute_type'),
                item_match_score=0.0,
                hierarchy_match_score=0.0,
                dispute_match_score=0.0,
                vector_similarity=float(similarity),
                final_score=0.0,
                metadata=metadata
            ))
        
        return results
    
    def _calculate_keyword_bonus(
        self,
        content: str,
        keywords: List[str]
    ) -> float:
        """
            (Phase 2 )
        
        Criteria     
        
        Args:
            content:  
            keywords:   
        
        Returns:
              (0~1)
        """
        # Criteria   ( )
        criteria_specific_keywords = [
            '', '', '', '',
            '', '', '',
            '', '', '',
            '', '', '',
            'A/S', '', '',
            '', '', '',
            '', '', '', ''
        ]
        
        score = 0.0
        content_lower = content.lower()
        
        #    (0.5)
        for keyword in criteria_specific_keywords:
            if keyword.lower() in content_lower:
                score += 0.5
        
        #    (0.2)
        for keyword in keywords:
            if len(keyword) >= 2 and keyword.lower() in content_lower:
                score += 0.2
        
        return min(score, 1.0)  #  1.0
    
    def _calculate_hierarchy_score(
        self,
        result: CriteriaSearchResult,
        query_analysis: QueryAnalysis
    ) -> float:
        """
            
        
         >  >    
        
        Args:
            result:  
            query_analysis:   
        
        Returns:
               (0~1)
        """
        score = 0.0
        keywords_lower = [k.lower() for k in query_analysis.keywords]
        
        #   ( )
        if result.category:
            # category   
            category_str = ' '.join(result.category) if isinstance(result.category, list) else result.category
            if any(k in category_str.lower() for k in keywords_lower):
                score += 0.5
        
        #   ()
        if result.industry:
            industry_str = ' '.join(result.industry) if isinstance(result.industry, list) else result.industry
            if any(k in industry_str.lower() for k in keywords_lower):
                score += 0.3
        
        #   ()
        if result.item_group:
            item_group_str = ' '.join(result.item_group) if isinstance(result.item_group, list) else result.item_group
            if any(k in item_group_str.lower() for k in keywords_lower):
                score += 0.2
        
        return min(score, 1.0)
    
    def _deduplicate_and_score(
        self,
        results: List[CriteriaSearchResult],
        query_analysis: QueryAnalysis
    ) -> List[CriteriaSearchResult]:
        """
             
        
        Args:
            results:   
            query_analysis:   
        
        Returns:
                  
        """
        # chunk_id 
        chunk_map = {}
        
        for result in results:
            chunk_id = result.chunk_id
            
            if chunk_id not in chunk_map:
                chunk_map[chunk_id] = result
            else:
                #     ( )
                existing = chunk_map[chunk_id]
                existing.item_match_score = max(
                    existing.item_match_score,
                    result.item_match_score
                )
                existing.dispute_match_score = max(
                    existing.dispute_match_score,
                    result.dispute_match_score
                )
                existing.vector_similarity = max(
                    existing.vector_similarity,
                    result.vector_similarity
                )
        
        #  ,        (Phase 2 )
        unique_results = []
        for result in chunk_map.values():
            # 1.   
            result.hierarchy_match_score = self._calculate_hierarchy_score(
                result, query_analysis
            )
            
            # 2.    (Phase 2 )
            keyword_bonus = self._calculate_keyword_bonus(
                result.content,
                query_analysis.keywords
            )
            
            # 3.   
            base_score = (
                result.item_match_score * self.ITEM_MATCH_WEIGHT +
                keyword_bonus * self.KEYWORD_WEIGHT +
                result.hierarchy_match_score * self.HIERARCHY_WEIGHT +
                result.dispute_match_score * self.DISPUTE_WEIGHT +
                result.vector_similarity * self.VECTOR_WEIGHT
            )
            
            # 4.       +3.0 (Phase 2 )
            if result.item_match_score >= 0.8:  #    
                base_score += self.EXACT_ITEM_MATCH_BONUS
            
            result.final_score = base_score
            unique_results.append(result)
        
        return unique_results
