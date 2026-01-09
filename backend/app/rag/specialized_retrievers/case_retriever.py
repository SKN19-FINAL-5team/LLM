"""
Case Retriever Module
   -   + chunk_type  +  +   
"""

import psycopg2
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime
from ..query_analyzer import QueryAnalysis


@dataclass
class CaseSearchResult:
    """  """
    chunk_id: str
    doc_id: str
    content: str
    chunk_type: str
    case_no: Optional[str]
    decision_date: Optional[str]
    agency: Optional[str]
    category_path: List[str]
    vector_similarity: float     #  
    chunk_type_weight: float     # chunk type 
    recency_score: float         #  
    agency_score: float          #   
    final_score: float           #  
    metadata: Dict


class CaseRetriever:
    """  """
    
    #  
    VECTOR_WEIGHT = 0.4         #  
    CHUNK_TYPE_WEIGHT = 0.3     # chunk type 
    RECENCY_WEIGHT = 0.2        # 
    AGENCY_WEIGHT = 0.1         #  
    
    # Chunk Type 
    # Phase 1 :   (Case  )
    CHUNK_TYPE_IMPORTANCE = {
        'judgment': 1.2,           #  (1.5 → 1.2)
        'decision': 1.2,           #  (1.5 → 1.2)
        'answer': 1.1,             #  (1.4 → 1.1)
        'qa_combined': 1.1,        # Q&A  (1.3 → 1.1)
        'parties_claim': 1.0,      #   (1.1 → 1.0)
        'case_overview': 1.0,      #  
        'question': 0.9,           #  (0.8 → 0.9)
        'default': 1.0             # 
    }
    
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
        query_embedding: List[float],
        agencies: Optional[List[str]] = None,
        top_k: int = 10,
        min_similarity: float = 0.25,
        debug: bool = False
    ) -> List[CaseSearchResult]:
        """
         
        
        Args:
            query:  
            query_analysis:   
            query_embedding:   
            agencies:    ()
            top_k:    
            min_similarity:   
            debug:    
        
        Returns:
               
        """
        self.connect_db()
        
        # DEBUG:   
        if debug:
            print(f"\n[Case Retriever DEBUG]")
            print(f"  Query: {query}")
            print(f"  - Agencies filter: {agencies}")
            print(f"  - Min similarity: {min_similarity}")
            print(f"  - Query type: {query_analysis.query_type}")
            print(f"  - Keywords: {query_analysis.keywords[:5] if len(query_analysis.keywords) > 5 else query_analysis.keywords}")
        
        #    ( )
        vector_results = self._vector_search(
            query_embedding,
            agencies=agencies,
            top_k=top_k * 3,
            min_similarity=min_similarity,
            debug=debug
        )
        
        if debug:
            print(f"  - Vector search results: {len(vector_results)}")
        
        #    
        scored_results = []
        for result in vector_results:
            # Chunk type 
            chunk_type_weight = self.CHUNK_TYPE_IMPORTANCE.get(
                result.chunk_type,
                self.CHUNK_TYPE_IMPORTANCE['default']
            )
            result.chunk_type_weight = chunk_type_weight
            
            #  
            result.recency_score = self._calculate_recency_score(
                result.decision_date
            )
            
            #   
            result.agency_score = self._calculate_agency_score(
                result.agency,
                agencies
            )
            
            #   
            result.final_score = (
                result.vector_similarity * self.VECTOR_WEIGHT +
                chunk_type_weight * self.CHUNK_TYPE_WEIGHT +
                result.recency_score * self.RECENCY_WEIGHT +
                result.agency_score * self.AGENCY_WEIGHT
            )
            
            scored_results.append(result)
            
            if debug and len(scored_results) <= 3:
                print(f"    > Result {len(scored_results)}: sim={result.vector_similarity:.3f}, final={result.final_score:.3f}, chunk_type={result.chunk_type}")
        
        #  K 
        scored_results.sort(key=lambda x: x.final_score, reverse=True)
        
        if debug:
            print(f"  - Final results after scoring: {len(scored_results[:top_k])}")
            if scored_results:
                print(f"  - Top score: {scored_results[0].final_score:.3f}")
            else:
                print(f"  -  NO RESULTS RETURNED")
        
        return scored_results[:top_k]
    
    def _vector_search(
        self,
        query_embedding: List[float],
        agencies: Optional[List[str]] = None,
        top_k: int = 30,
        min_similarity: float = 0.25,
        debug: bool = False
    ) -> List[CaseSearchResult]:
        """
          
        
        Args:
            query_embedding:  
            agencies:   ()
            top_k:    
            min_similarity:  
            debug:    
        
        Returns:
              
        """
        # SQL   -  doc_type 
        sql = """
            SELECT 
                c.chunk_id,
                c.doc_id,
                c.content,
                c.chunk_type,
                d.metadata->>'case_no' AS case_no,
                d.metadata->>'case_sn' AS case_sn,
                d.metadata->>'decision_date' AS decision_date,
                d.source_org AS agency,
                d.category_path,
                d.metadata,
                1 - (c.embedding <=> %s::vector) AS similarity
            FROM chunks c
            JOIN documents d ON c.doc_id = d.doc_id
            WHERE 
                d.doc_type IN ('counsel_case', 'mediation_case')
                AND c.drop = FALSE
                AND c.embedding IS NOT NULL
                AND (1 - (c.embedding <=> %s::vector)) >= %s
        """
        
        params = [query_embedding, query_embedding, min_similarity]
        
        #   ()
        if agencies and len(agencies) > 0:
            placeholders = ','.join(['%s'] * len(agencies))
            sql += f" AND d.source_org IN ({placeholders})"
            params.extend(agencies)
            if debug:
                print(f"    > Applying agency filter: {agencies}")
        
        sql += """
            ORDER BY c.embedding <=> %s::vector
            LIMIT %s
        """
        params.extend([query_embedding, top_k])
        
        if debug:
            print(f"    > Executing vector search (min_similarity={min_similarity}, top_k={top_k})")
        
        self.cur.execute(sql, params)
        rows = self.cur.fetchall()
        
        if debug:
            print(f"    > Found {len(rows)} raw results")
        
        results = []
        for row in rows:
            (chunk_id, doc_id, content, chunk_type, case_no, case_sn,
             decision_date, agency, category_path, metadata, similarity) = row
            
            # case_no ,  case_sn 
            case_number = case_no or case_sn
            
            results.append(CaseSearchResult(
                chunk_id=chunk_id,
                doc_id=doc_id,
                content=content,
                chunk_type=chunk_type or 'default',
                case_no=case_number,
                decision_date=decision_date,
                agency=agency,
                category_path=category_path or [],
                vector_similarity=float(similarity),
                chunk_type_weight=0.0,  #  
                recency_score=0.0,      #  
                agency_score=0.0,       #  
                final_score=0.0,        #  
                metadata=metadata or {}
            ))
        
        return results
    
    def _calculate_recency_score(self, decision_date: Optional[str]) -> float:
        """
          
        
           
        
        Args:
            decision_date:   (YYYY  YYYY-MM-DD)
        
        Returns:
              (0~1)
        """
        if not decision_date:
            return 0.5  #     
        
        try:
            #  
            year_str = str(decision_date)[:4]
            if not year_str.isdigit():
                return 0.5
            
            year = int(year_str)
            current_year = datetime.now().year
            
            #  10   
            years_ago = current_year - year
            
            if years_ago < 0:
                return 0.5  #    
            elif years_ago == 0:
                return 1.0  #  
            elif years_ago <= 2:
                return 0.9  # 2 
            elif years_ago <= 5:
                return 0.7  # 5 
            elif years_ago <= 10:
                return 0.5  # 10 
            else:
                return 0.3  # 10 
        
        except Exception:
            return 0.5
    
    def _calculate_agency_score(
        self,
        result_agency: Optional[str],
        preferred_agencies: Optional[List[str]]
    ) -> float:
        """
           
        
        Args:
            result_agency:   
            preferred_agencies:   
        
        Returns:
               (0~1)
        """
        if not preferred_agencies or not result_agency:
            return 0.5  #  
        
        #   
        result_agency_lower = result_agency.lower()
        preferred_lower = [a.lower() for a in preferred_agencies]
        
        if result_agency_lower in preferred_lower:
            return 1.0  #   
        else:
            return 0.3  #  
