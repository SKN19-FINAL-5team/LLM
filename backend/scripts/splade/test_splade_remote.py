"""
 RunPod SPLADE API   
SSH    (localhost:8002 -> RunPod:8000)
"""

import requests
import numpy as np
from typing import List, Dict, Optional
import psycopg2
from pathlib import Path
import os
from dotenv import load_dotenv

#   
backend_dir = Path(__file__).parent.parent
env_file = backend_dir / '.env'
if env_file.exists():
    load_dotenv(env_file)
else:
    root_env = Path(__file__).parent.parent.parent / '.env'
    if root_env.exists():
        load_dotenv(root_env)
    else:
        load_dotenv()

# API URL (SSH   localhost:8002 )
SPLADE_API_URL = os.getenv('SPLADE_API_URL', 'http://localhost:8002')


class RemoteSPLADERetriever:
    """RunPod SPLADE API  Retriever"""
    
    def __init__(self, api_url: str = None):
        """
        Args:
            api_url: SPLADE API  URL (: http://localhost:8002)
        """
        self.api_url = api_url or SPLADE_API_URL
        self.base_url = self.api_url.rstrip('/')
    
    def _check_connection(self, silent: bool = False):
        """API   """
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                return True
        except Exception as e:
            if not silent:
                print(f"  API   : {e}")
                print(f"   URL: {self.base_url}")
                print(f"   SSH    .")
            return False
        return False
    
    def encode_query(self, query: str) -> np.ndarray:
        """
         Sparse Vector 
        
        Args:
            query:  
        
        Returns:
            Sparse vector (numpy array, 30522)
        """
        #   (    )
        if not self._check_connection():
            raise ConnectionError("SPLADE API    .")
        
        try:
            response = requests.post(
                f"{self.base_url}/encode_query",
                json={"texts": [query]},
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            return np.array(result['embeddings'][0])
        except Exception as e:
            raise RuntimeError(f"Query encoding failed: {e}")
    
    def encode_document(self, document: str) -> np.ndarray:
        """
         Sparse Vector 
        
        Args:
            document:  
        
        Returns:
            Sparse vector (numpy array, 30522)
        """
        #   ( )
        if not self._check_connection(silent=True):
            raise ConnectionError("SPLADE API    .")
        
        try:
            response = requests.post(
                f"{self.base_url}/encode_document",
                json={"texts": [document]},
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            return np.array(result['embeddings'][0])
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"API   : {e}")
        except Exception as e:
            raise RuntimeError(f"Document encoding failed: {e}")
    
    def encode_documents_batch(self, documents: List[str]) -> List[np.ndarray]:
        """
           
        
        Args:
            documents:   
        
        Returns:
            Sparse vector 
        """
        #   ( )
        if not self._check_connection(silent=True):
            raise ConnectionError("SPLADE API    .")
        
        try:
            response = requests.post(
                f"{self.base_url}/encode_document",
                json={"texts": documents},
                timeout=60
            )
            response.raise_for_status()
            result = response.json()
            return [np.array(emb) for emb in result['embeddings']]
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"API   : {e}")
        except Exception as e:
            raise RuntimeError(f"Batch document encoding failed: {e}")
    
    def compute_similarity(
        self,
        query_vec: np.ndarray,
        doc_vec: np.ndarray
    ) -> float:
        """
             (dot product)
        
        Args:
            query_vec:  sparse vector
            doc_vec:  sparse vector
        
        Returns:
             
        """
        try:
            response = requests.post(
                f"{self.base_url}/similarity",
                json={
                    "query_embedding": query_vec.tolist(),
                    "document_embeddings": [doc_vec.tolist()]
                },
                timeout=10
            )
            response.raise_for_status()
            result = response.json()
            return result['similarities'][0]
        except Exception as e:
            raise RuntimeError(f"Similarity computation failed: {e}")


class RemoteSPLADEDBRetriever:
    """RunPod SPLADE API  DB """
    
    def __init__(
        self,
        db_config: Dict,
        api_url: str = None
    ):
        """
        Args:
            db_config:   
            api_url: SPLADE API  URL
        """
        self.db_config = db_config
        self.splade_retriever = RemoteSPLADERetriever(api_url)
        self.conn = None
        self.api_available = False
        
        #     
        try:
            if self.splade_retriever._check_connection():
                self.api_available = True
            else:
                self.api_available = False
                raise ConnectionError("API    .")
        except Exception as e:
            self.api_available = False
            raise ConnectionError(f"API   : {e}")
    
    def connect_db(self):
        """DB """
        if self.conn is None or self.conn.closed:
            self.conn = psycopg2.connect(**self.db_config)
    
    def search_law_splade(
        self,
        query: str,
        top_k: int = 10
    ) -> List[Dict]:
        """ SPLADE  (  )"""
        # API       
        if not self.api_available:
            return []
        
        self.connect_db()
        
        try:
            #   (   )
            query_vec = self.splade_retriever.encode_query(query)
            
            if query_vec is None or query_vec.size == 0:
                return []
        except ConnectionError:
            #       
            self.api_available = False
            return []
        except Exception as e:
            #     
            return []
        
        #   chunk 
        cur = self.conn.cursor()
        cur.execute("""
            SELECT 
                c.chunk_id,
                c.doc_id,
                c.content,
                d.metadata->>'law_name' as law_name
            FROM chunks c
            JOIN documents d ON c.doc_id = d.doc_id
            WHERE d.doc_type = 'law'
            LIMIT 1000
        """)
        
        chunks = cur.fetchall()
        
        #   (32)
        batch_size = 32
        results = []
        
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i+batch_size]
            contents = [c[2] for c in batch]  # content 
            
            try:
                #  
                doc_vecs = self.splade_retriever.encode_documents_batch(contents)
                
                #     
                for (chunk_id, doc_id, content, law_name), doc_vec in zip(batch, doc_vecs):
                    score = self.splade_retriever.compute_similarity(query_vec, doc_vec)
                    
                    if score > 0:
                        results.append({
                            'chunk_id': chunk_id,
                            'doc_id': doc_id,
                            'content': content,
                            'law_name': law_name,
                            'splade_score': float(score)
                        })
            except Exception as e:
                print(f"       (batch {i//batch_size + 1}): {e}")
                continue
        
        #   
        results.sort(key=lambda x: x['splade_score'], reverse=True)
        
        return results[:top_k]
    
    def search_criteria_splade(
        self,
        query: str,
        top_k: int = 10
    ) -> List[Dict]:
        """ SPLADE  (  )"""
        # API       
        if not self.api_available:
            return []
        
        self.connect_db()
        
        try:
            #   (   )
            query_vec = self.splade_retriever.encode_query(query)
            
            if query_vec is None or query_vec.size == 0:
                return []
        except ConnectionError:
            #       
            self.api_available = False
            return []
        except Exception as e:
            #     
            return []
        
        #   chunk 
        cur = self.conn.cursor()
        cur.execute("""
            SELECT 
                c.chunk_id,
                c.doc_id,
                c.content,
                d.metadata->>'item' as item
            FROM chunks c
            JOIN documents d ON c.doc_id = d.doc_id
            WHERE d.doc_type LIKE 'criteria%%'
            LIMIT 1000
        """)
        
        chunks = cur.fetchall()
        
        #   (32)
        batch_size = 32
        results = []
        
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i+batch_size]
            contents = [c[2] for c in batch]  # content 
            
            try:
                #  
                doc_vecs = self.splade_retriever.encode_documents_batch(contents)
                
                #     
                for (chunk_id, doc_id, content, item), doc_vec in zip(batch, doc_vecs):
                    score = self.splade_retriever.compute_similarity(query_vec, doc_vec)
                    
                    if score > 0:
                        results.append({
                            'chunk_id': chunk_id,
                            'doc_id': doc_id,
                            'content': content,
                            'item': item,
                            'splade_score': float(score)
                        })
            except Exception as e:
                print(f"       (batch {i//batch_size + 1}): {e}")
                continue
        
        #   
        results.sort(key=lambda x: x['splade_score'], reverse=True)
        
        return results[:top_k]


#  
if __name__ == "__main__":
    # API   
    retriever = RemoteSPLADERetriever()
    
    if retriever._check_connection():
        print(" SPLADE API   !")
        
        # 
        query = " 750 "
        print(f"\nQuery: {query}")
        query_vec = retriever.encode_query(query)
        print(f" Encoded (shape: {query_vec.shape}, non-zero: {np.count_nonzero(query_vec)})")
    else:
        print(" SPLADE API   ")
        print("   SSH  : ssh -L 8002:localhost:8000 [user]@[host] -p [port]")
