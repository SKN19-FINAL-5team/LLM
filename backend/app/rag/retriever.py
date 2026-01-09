"""
RAG Retriever Module
Vector DB    
"""

import os
import psycopg2
from typing import List, Dict, Optional
from sentence_transformers import SentenceTransformer
import torch


class VectorRetriever:
    """Vector DB    """
    
    def __init__(self, db_config: Dict, model_name: str = None):
        """
        Args:
            db_config:   
            model_name:    (:  )
        """
        self.db_config = db_config
        self.model_name = model_name or os.getenv('EMBEDDING_MODEL', 'nlpai-lab/KURE-v1')
        self.model = None
        self.conn = None
        
    def load_model(self):
        """  """
        if self.model is None:
            print(f"Loading embedding model: {self.model_name}")
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            self.model = SentenceTransformer(self.model_name, device=device)
            print(f"Model loaded on {device}")
    
    def connect_db(self):
        """ """
        if self.conn is None or self.conn.closed:
            self.conn = psycopg2.connect(**self.db_config)
    
    def close(self):
        """ """
        if self.conn and not self.conn.closed:
            self.conn.close()
    
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
        top_k: int = 5,
        chunk_types: Optional[List[str]] = None,
        agencies: Optional[List[str]] = None
    ) -> List[Dict]:
        """
          
        
        Args:
            query:  
            top_k:    
            chunk_types:     (: ['decision', 'reasoning'])
            agencies:    (: ['kca', 'ecmc'])
            
        Returns:
               ( )
        """
        self.connect_db()
        
        #  
        query_embedding = self.embed_query(query)
        
        # SQL  
        sql = """
            SELECT 
                c.chunk_id,
                c.doc_id,
                c.chunk_type,
                c.content,
                c.content_length,
                d.title,
                d.metadata->>'decision_date' AS decision_date,
                d.source_org AS agency,
                d.doc_type AS source,
                1 - (c.embedding <=> %s::vector) AS similarity
            FROM chunks c
            JOIN documents d ON c.doc_id = d.doc_id
            WHERE c.drop = FALSE
        """
        
        params = [query_embedding]
        
        #   
        if chunk_types:
            placeholders = ','.join(['%s'] * len(chunk_types))
            sql += f" AND c.chunk_type IN ({placeholders})"
            params.extend(chunk_types)
        
        #  
        if agencies:
            placeholders = ','.join(['%s'] * len(agencies))
            sql += f" AND d.source_org IN ({placeholders})"
            params.extend(agencies)
        
        sql += """
            ORDER BY c.embedding <=> %s::vector
            LIMIT %s
        """
        params.append(query_embedding)
        params.append(top_k)
        
        #  
        with self.conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
        
        #  
        results = []
        for row in rows:
            results.append({
                'chunk_uid': row[0],  # chunk_id ( )
                'case_uid': row[1],   # doc_id ( )
                'chunk_type': row[2],
                'text': row[3],       # content
                'text_len': row[4],   # content_length
                'case_no': row[5],    # title ( )
                'decision_date': row[6],
                'agency': row[7],     # source_org
                'source': row[8],     # doc_type
                'similarity': float(row[9])
            })
        
        return results
    
    def get_case_chunks(self, case_uid: str) -> List[Dict]:
        """
            
        
        Args:
            case_uid:   ID (doc_id)
            
        Returns:
                
        """
        self.connect_db()
        
        sql = """
            SELECT 
                c.chunk_id,
                c.doc_id,
                c.chunk_type,
                c.content,
                c.chunk_index,
                d.title,
                d.metadata->>'decision_date' AS decision_date,
                d.source_org
            FROM chunks c
            JOIN documents d ON c.doc_id = d.doc_id
            WHERE c.doc_id = %s AND c.drop = FALSE
            ORDER BY c.chunk_index
        """
        
        with self.conn.cursor() as cur:
            cur.execute(sql, (case_uid,))
            rows = cur.fetchall()
        
        results = []
        for row in rows:
            results.append({
                'chunk_uid': row[0],
                'case_uid': row[1],
                'chunk_type': row[2],
                'text': row[3],
                'seq': row[4],
                'case_no': row[5],
                'decision_date': row[6],
                'agency': row[7]
            })
        
        return results
