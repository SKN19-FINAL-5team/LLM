"""
 SPLADE Retriever
RDB   sparse vector    
"""

import json
import numpy as np
import psycopg2
from typing import List, Dict, Optional
from pathlib import Path
import os
from dotenv import load_dotenv

#   
backend_dir = Path(__file__).parent.parent
env_file = backend_dir / '.env'
if env_file.exists():
    load_dotenv(env_file)
else:
    root_env = backend_dir.parent / '.env'
    if root_env.exists():
        load_dotenv(root_env)
    else:
        load_dotenv()

# SPLADE  import ( )
try:
    from scripts.splade.test_splade_naver import NaverSPLADERetriever
    from scripts.splade.test_splade_remote import RemoteSPLADERetriever
    SPLADE_AVAILABLE = True
except ImportError:
    SPLADE_AVAILABLE = False
    NaverSPLADERetriever = None
    RemoteSPLADERetriever = None


class OptimizedSPLADEDBRetriever:
    """ SPLADE DB Retriever (  sparse vector )"""
    
    def __init__(
        self,
        db_config: Dict,
        use_remote: bool = False,
        api_url: str = None,
        device: str = None
    ):
        """
        Args:
            db_config:   
            use_remote:  API   
            api_url:  API URL
            device:   
        """
        self.db_config = db_config
        self.conn = None
        self.query_encoder = None
        
        #   Retriever 
        if use_remote:
            if api_url is None:
                api_url = os.getenv('SPLADE_API_URL', 'http://localhost:8001')
            try:
                self.query_encoder = RemoteSPLADERetriever(api_url=api_url)
                print(f"  SPLADE API  ( ): {api_url}")
            except Exception as e:
                print(f"   API  : {e}")
                use_remote = False
        
        if not use_remote and SPLADE_AVAILABLE:
            try:
                import torch
                if device is None:
                    device = 'cuda' if torch.cuda.is_available() else 'cpu'
                self.query_encoder = NaverSPLADERetriever(device=device)
                self.query_encoder.load_model()
                print(f"  SPLADE   ( ): device={device}")
            except Exception as e:
                print(f"     : {e}")
                raise RuntimeError("SPLADE     .")
    
    def connect_db(self):
        """DB """
        if self.conn is None or self.conn.closed:
            self.conn = psycopg2.connect(**self.db_config)
    
    def jsonb_to_sparse_vector(self, jsonb_data: Dict[str, float]) -> np.ndarray:
        """
        JSONB  sparse vector numpy array 
        
        Args:
            jsonb_data: {token_id: weight}  
        
        Returns:
            Sparse vector (numpy array, 30522)
        """
        # SPLADE-v3 30522 
        vocab_size = 30522
        sparse_vec = np.zeros(vocab_size, dtype=np.float32)
        
        for token_id_str, weight in jsonb_data.items():
            try:
                token_id = int(token_id_str)
                if 0 <= token_id < vocab_size:
                    sparse_vec[token_id] = float(weight)
            except (ValueError, TypeError):
                continue
        
        return sparse_vec
    
    def compute_similarity_batch(
        self,
        query_vec: np.ndarray,
        doc_vectors: List[Dict[str, float]]
    ) -> List[float]:
        """
          
        
        Args:
            query_vec:  sparse vector
            doc_vectors:  sparse vector  (JSONB )
        
        Returns:
              
        """
        similarities = []
        
        for doc_vec_jsonb in doc_vectors:
            if doc_vec_jsonb is None:
                similarities.append(0.0)
                continue
            
            # JSONB numpy array 
            doc_vec = self.jsonb_to_sparse_vector(doc_vec_jsonb)
            
            # Dot product 
            similarity = np.dot(query_vec, doc_vec)
            similarities.append(float(similarity))
        
        return similarities
    
    def search_law_splade_optimized(
        self,
        query: str,
        top_k: int = 10,
        min_score: float = 0.0
    ) -> List[Dict]:
        """
         SPLADE  ( )
        
        Args:
            query:  
            top_k:    
            min_score:   
        
        Returns:
              
        """
        self.connect_db()
        
        #  
        try:
            query_vec = self.query_encoder.encode_query(query)
            if query_vec is None or query_vec.size == 0:
                return []
        except Exception as e:
            print(f"      : {e}")
            return []
        
        # numpy array 
        if isinstance(query_vec, dict):
            #  JSONB  
            query_vec = self.jsonb_to_sparse_vector(query_vec)
        elif not isinstance(query_vec, np.ndarray):
            import torch
            if isinstance(query_vec, torch.Tensor):
                if query_vec.is_sparse:
                    query_vec = query_vec.to_dense()
                query_vec = query_vec.cpu().numpy()
        
        # DB   sparse vector 
        cur = self.conn.cursor()
        cur.execute("""
            SELECT 
                c.chunk_id,
                c.doc_id,
                c.content,
                c.splade_sparse_vector,
                d.metadata->>'law_name' as law_name
            FROM chunks c
            JOIN documents d ON c.doc_id = d.doc_id
            WHERE 
                d.doc_type = 'law'
                AND c.drop = FALSE
                AND c.splade_encoded = TRUE
                AND c.splade_sparse_vector IS NOT NULL
        """)
        
        chunks = cur.fetchall()
        cur.close()
        
        if not chunks:
            return []
        
        #   
        doc_vectors = [row[3] for row in chunks]  # splade_sparse_vector
        similarities = self.compute_similarity_batch(query_vec, doc_vectors)
        
        #  
        results = []
        for (chunk_id, doc_id, content, _, law_name), score in zip(chunks, similarities):
            if score >= min_score:
                results.append({
                    'chunk_id': chunk_id,
                    'doc_id': doc_id,
                    'content': content,
                    'law_name': law_name if law_name else '',
                    'splade_score': score
                })
        
        #   
        results.sort(key=lambda x: x['splade_score'], reverse=True)
        
        return results[:top_k]
    
    def search_criteria_splade_optimized(
        self,
        query: str,
        top_k: int = 10,
        min_score: float = 0.0
    ) -> List[Dict]:
        """
         SPLADE  ( )
        
        Args:
            query:  
            top_k:    
            min_score:   
        
        Returns:
              
        """
        self.connect_db()
        
        #  
        try:
            query_vec = self.query_encoder.encode_query(query)
            if query_vec is None or query_vec.size == 0:
                return []
        except Exception as e:
            print(f"      : {e}")
            return []
        
        # numpy array 
        if isinstance(query_vec, dict):
            query_vec = self.jsonb_to_sparse_vector(query_vec)
        elif not isinstance(query_vec, np.ndarray):
            import torch
            if isinstance(query_vec, torch.Tensor):
                if query_vec.is_sparse:
                    query_vec = query_vec.to_dense()
                query_vec = query_vec.cpu().numpy()
        
        # DB   sparse vector 
        cur = self.conn.cursor()
        cur.execute("""
            SELECT 
                c.chunk_id,
                c.doc_id,
                c.content,
                c.splade_sparse_vector,
                d.metadata->>'item' as item
            FROM chunks c
            JOIN documents d ON c.doc_id = d.doc_id
            WHERE 
                d.doc_type LIKE 'criteria%%'
                AND c.drop = FALSE
                AND c.splade_encoded = TRUE
                AND c.splade_sparse_vector IS NOT NULL
        """)
        
        chunks = cur.fetchall()
        cur.close()
        
        if not chunks:
            return []
        
        #   
        doc_vectors = [row[3] for row in chunks]
        similarities = self.compute_similarity_batch(query_vec, doc_vectors)
        
        #  
        results = []
        for (chunk_id, doc_id, content, _, item), score in zip(chunks, similarities):
            if score >= min_score:
                results.append({
                    'chunk_id': chunk_id,
                    'doc_id': doc_id,
                    'content': content,
                    'item': item if item else '',
                    'splade_score': score
                })
        
        #   
        results.sort(key=lambda x: x['splade_score'], reverse=True)
        
        return results[:top_k]
    
    def search_hybrid(
        self,
        query: str,
        doc_type: str = None,
        top_k: int = 10,
        splade_weight: float = 0.7,
        dense_weight: float = 0.3
    ) -> List[Dict]:
        """
         : SPLADE + Dense Vector
        
        Args:
            query:  
            doc_type:   
            top_k:    
            splade_weight: SPLADE  
            dense_weight: Dense  
        
        Returns:
              
        """
        # TODO: Dense Retriever 
        #  SPLADE 
        if doc_type == 'law' or doc_type is None:
            return self.search_law_splade_optimized(query, top_k=top_k)
        elif doc_type and doc_type.startswith('criteria'):
            return self.search_criteria_splade_optimized(query, top_k=top_k)
        else:
            return []


#  
if __name__ == "__main__":
    import sys
    
    # DB 
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'database': os.getenv('DB_NAME', 'ddoksori'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres')
    }
    
    # Retriever 
    try:
        retriever = OptimizedSPLADEDBRetriever(db_config)
    except Exception as e:
        print(f" Retriever  : {e}")
        sys.exit(1)
    
    #  
    test_queries = [
        " 750 ",
        "  "
    ]
    
    for query in test_queries:
        print(f"\n{'='*80}")
        print(f"Query: {query}")
        print(f"{'='*80}")
        
        #  
        if "" in query or "" in query:
            results = retriever.search_law_splade_optimized(query, top_k=5)
            print(f"\n  : {len(results)}")
            for i, r in enumerate(results[:3], 1):
                print(f"\n{i}. Score: {r['splade_score']:.4f}")
                print(f"   Law: {r.get('law_name', 'N/A')}")
                print(f"   Content: {r['content'][:100]}...")
        
        #  
        else:
            results = retriever.search_criteria_splade_optimized(query, top_k=5)
            print(f"\n  : {len(results)}")
            for i, r in enumerate(results[:3], 1):
                print(f"\n{i}. Score: {r['splade_score']:.4f}")
                print(f"   Item: {r.get('item', 'N/A')}")
                print(f"   Content: {r['content'][:100]}...")
    
    #  
    if retriever.conn:
        retriever.conn.close()
