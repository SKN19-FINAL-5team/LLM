"""
  - RAG  
: 2026-01-05
 ,  ,    
"""

import psycopg2
from typing import List, Dict, Optional, Tuple
import requests
from dataclasses import dataclass
import re


@dataclass
class SearchResult:
    """   """
    chunk_id: str
    doc_id: str
    chunk_type: str
    content: str
    doc_title: str
    doc_type: str
    category_path: List[str]
    similarity: float
    metadata: Optional[Dict] = None


class RAGRetriever:
    """RAG  """
    
    def __init__(self, db_config: Dict[str, str], embed_api_url: str = "http://localhost:8001/embed"):
        self.db_config = db_config
        self.embed_api_url = embed_api_url
        self.conn = None
        
        #     
        self.QUERY_TYPE_WEIGHTS = {
            'legal_interpretation': {  #   
                'law': 0.6,
                'mediation_case': 0.3,
                'counsel_case': 0.1
            },
            'similar_case': {  #   
                'mediation_case': 0.5,
                'counsel_case': 0.4,
                'law': 0.1
            },
            'general_inquiry': {  #  
                'counsel_case': 0.5,
                'mediation_case': 0.3,
                'law': 0.2
            }
        }
    
    def connect(self):
        """ """
        self.conn = psycopg2.connect(**self.db_config)
    
    def close(self):
        """  """
        if self.conn:
            self.conn.close()
    
    def embed_query(self, query: str) -> List[float]:
        """  """
        try:
            response = requests.post(
                self.embed_api_url,
                json={"texts": [query]},
                timeout=10
            )
            response.raise_for_status()
            embeddings = response.json()['embeddings']
            return embeddings[0]
        except requests.exceptions.RequestException as e:
            raise Exception(f" API : {e}")
    
    def vector_search(
        self,
        query: str,
        top_k: int = 10,
        doc_type_filter: Optional[str] = None,
        chunk_type_filter: Optional[str] = None
    ) -> List[SearchResult]:
        """  """
        #   
        query_embedding = self.embed_query(query)
        
        #  
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT 
                    c.chunk_id,
                    c.doc_id,
                    c.chunk_type,
                    c.content,
                    d.title AS doc_title,
                    d.doc_type,
                    d.category_path,
                    1 - (c.embedding <=> %s::vector) AS similarity
                FROM chunks c
                JOIN documents d ON c.doc_id = d.doc_id
                WHERE 
                    c.embedding IS NOT NULL
                    AND (%s IS NULL OR d.doc_type = %s)
                    AND (%s IS NULL OR c.chunk_type = %s)
                ORDER BY c.embedding <=> %s::vector
                LIMIT %s
                """,
                (
                    query_embedding,
                    doc_type_filter, doc_type_filter,
                    chunk_type_filter, chunk_type_filter,
                    query_embedding,
                    top_k
                )
            )
            
            results = []
            for row in cur.fetchall():
                results.append(SearchResult(
                    chunk_id=row[0],
                    doc_id=row[1],
                    chunk_type=row[2],
                    content=row[3],
                    doc_title=row[4],
                    doc_type=row[5],
                    category_path=row[6] or [],
                    similarity=float(row[7])
                ))
            
            return results
    
    def keyword_search(
        self,
        query: str,
        top_k: int = 10,
        doc_type_filter: Optional[str] = None
    ) -> List[SearchResult]:
        """   (PostgreSQL  )"""
        #    ( )
        keywords = self._extract_keywords(query)
        
        with self.conn.cursor() as cur:
            # LIKE  ( )
            search_pattern = f"%{query}%"
            
            cur.execute(
                """
                SELECT 
                    c.chunk_id,
                    c.doc_id,
                    c.chunk_type,
                    c.content,
                    d.title AS doc_title,
                    d.doc_type,
                    d.category_path,
                    0.5 AS similarity
                FROM chunks c
                JOIN documents d ON c.doc_id = d.doc_id
                WHERE 
                    (c.content LIKE %s OR d.title LIKE %s)
                    AND (%s IS NULL OR d.doc_type = %s)
                LIMIT %s
                """,
                (
                    search_pattern, search_pattern,
                    doc_type_filter, doc_type_filter,
                    top_k
                )
            )
            
            results = []
            for row in cur.fetchall():
                results.append(SearchResult(
                    chunk_id=row[0],
                    doc_id=row[1],
                    chunk_type=row[2],
                    content=row[3],
                    doc_title=row[4],
                    doc_type=row[5],
                    category_path=row[6] or [],
                    similarity=float(row[7])
                ))
            
            return results
    
    def hybrid_search(
        self,
        query: str,
        top_k: int = 10,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3,
        doc_type_filter: Optional[str] = None
    ) -> List[SearchResult]:
        """  ( + )"""
        #  
        vector_results = self.vector_search(
            query,
            top_k=top_k * 2,
            doc_type_filter=doc_type_filter
        )
        
        #  
        keyword_results = self.keyword_search(
            query,
            top_k=top_k * 2,
            doc_type_filter=doc_type_filter
        )
        
        #     
        merged_results = {}
        
        for result in vector_results:
            merged_results[result.chunk_id] = {
                'result': result,
                'score': result.similarity * vector_weight
            }
        
        for result in keyword_results:
            if result.chunk_id in merged_results:
                merged_results[result.chunk_id]['score'] += result.similarity * keyword_weight
            else:
                merged_results[result.chunk_id] = {
                    'result': result,
                    'score': result.similarity * keyword_weight
                }
        
        #   
        sorted_results = sorted(
            merged_results.values(),
            key=lambda x: x['score'],
            reverse=True
        )
        
        #    
        final_results = []
        for item in sorted_results[:top_k]:
            result = item['result']
            result.similarity = item['score']
            final_results.append(result)
        
        return final_results
    
    def multi_source_search(
        self,
        query: str,
        query_type: str = 'general_inquiry',
        top_k: int = 10
    ) -> List[SearchResult]:
        """   (   )"""
        weights = self.QUERY_TYPE_WEIGHTS.get(query_type, self.QUERY_TYPE_WEIGHTS['general_inquiry'])
        
        all_results = []
        
        for doc_type, weight in weights.items():
            #    
            results = self.vector_search(
                query,
                top_k=int(top_k * weight * 2),
                doc_type_filter=doc_type
            )
            
            #  
            for result in results:
                result.similarity *= weight
                all_results.append(result)
        
        #   
        all_results.sort(key=lambda x: x.similarity, reverse=True)
        
        return all_results[:top_k]
    
    def get_chunk_with_context(
        self,
        chunk_id: str,
        window_size: int = 1
    ) -> List[SearchResult]:
        """   """
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT * FROM get_chunk_with_context(%s, %s)
                """,
                (chunk_id, window_size)
            )
            
            results = []
            for row in cur.fetchall():
                #   
                cur.execute(
                    """
                    SELECT d.title, d.doc_type, d.category_path
                    FROM documents d
                    WHERE d.doc_id = %s
                    """,
                    (row[1],)
                )
                doc_info = cur.fetchone()
                
                results.append(SearchResult(
                    chunk_id=row[0],
                    doc_id=row[1],
                    chunk_type=row[3],
                    content=row[4],
                    doc_title=doc_info[0] if doc_info else "",
                    doc_type=doc_info[1] if doc_info else "",
                    category_path=doc_info[2] if doc_info else [],
                    similarity=1.0 if row[5] else 0.8,  # is_target
                    metadata={'is_target': row[5]}
                ))
            
            return results
    
    def expand_context_for_results(
        self,
        results: List[SearchResult],
        window_size: int = 1
    ) -> List[SearchResult]:
        """    """
        expanded_results = []
        seen_chunk_ids = set()
        
        for result in results:
            #   
            context_chunks = self.get_chunk_with_context(result.chunk_id, window_size)
            
            for chunk in context_chunks:
                if chunk.chunk_id not in seen_chunk_ids:
                    expanded_results.append(chunk)
                    seen_chunk_ids.add(chunk.chunk_id)
        
        return expanded_results
    
    def _extract_keywords(self, query: str) -> List[str]:
        """   ( )"""
        #    ( )
        #  KoNLPy    
        keywords = re.findall(r'[-]+', query)
        return [kw for kw in keywords if len(kw) >= 2]
    
    def format_results_for_llm(self, results: List[SearchResult]) -> str:
        """  LLM   """
        formatted = []
        
        for i, result in enumerate(results, 1):
            formatted.append(f"[  {i}]")
            formatted.append(f" : {result.doc_type}")
            formatted.append(f": {result.doc_title}")
            formatted.append(f" : {result.chunk_type}")
            formatted.append(f": {result.similarity:.4f}")
            formatted.append(f"\n:\n{result.content}")
            formatted.append("\n" + "=" * 60 + "\n")
        
        return "\n".join(formatted)


def main():
    """  """
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': os.getenv('DB_PORT', '5432'),
        'database': os.getenv('DB_NAME', 'ddoksori'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres')
    }
    
    embed_api_url = os.getenv('EMBED_API_URL', 'http://localhost:8001/embed')
    
    retriever = RAGRetriever(db_config, embed_api_url)
    retriever.connect()
    
    try:
        #  
        query = "   ?"
        print(f": {query}\n")
        
        #  
        print("===   ===")
        results = retriever.vector_search(query, top_k=3)
        for i, result in enumerate(results, 1):
            print(f"{i}. {result.doc_title} ({result.doc_type}) - : {result.similarity:.4f}")
        
        print("\n===   ===")
        results = retriever.hybrid_search(query, top_k=3)
        for i, result in enumerate(results, 1):
            print(f"{i}. {result.doc_title} ({result.doc_type}) - : {result.similarity:.4f}")
        
    finally:
        retriever.close()


if __name__ == "__main__":
    main()
