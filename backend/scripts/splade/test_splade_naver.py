"""
Naver SPLADE   
HuggingFace: naver/splade-v3
HuggingFace  : SparseEncoder 
"""

import torch
from typing import List, Dict, Optional
import numpy as np
import psycopg2
import os
from dotenv import load_dotenv
from pathlib import Path

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

# HuggingFace  
HF_TOKEN = os.getenv('HF_TOKEN') or os.getenv('HUGGINGFACE_TOKEN')


class NaverSPLADERetriever:
    """Naver SPLADE   Retriever (SparseEncoder )"""
    
    def __init__(self, model_name: str = "naver/splade-v3", device: str = None):
        """
        Args:
            model_name: Naver SPLADE   (: naver/splade-v3)
            device:   ('cuda'  'cpu', None  )
                    'cuda'  GPU , None  
        """
        self.model_name = model_name
        self.model = None
        # device     
        if device is None:
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        else:
            self.device = device
        self.use_sparse_encoder = True
        print(f" SPLADE Retriever : device={self.device}, CUDA available={torch.cuda.is_available()}")
    
    def load_model(self):
        """  (SparseEncoder ,   SentenceTransformer )"""
        if self.model is None:
            print(f"Loading SPLADE model: {self.model_name}")
            print(f"Device: {self.device}")
            
            # safetensors   (torch   )
            os.environ['SAFETENSORS_FAST_GPU'] = '1'
            # transformers safetensors  
            os.environ['TRANSFORMERS_SAFE_LOADING'] = '1'
            
            # SparseEncoder  (HuggingFace )
            try:
                from sentence_transformers import SparseEncoder
                print("  : SparseEncoder (safetensors )...")
                self.model = SparseEncoder(
                    self.model_name,
                    token=HF_TOKEN if HF_TOKEN else None,
                    trust_remote_code=True
                )
                self.use_sparse_encoder = True
                print(" SparseEncoder   !")
                return
            except ImportError:
                print("    SparseEncoder    (sentence-transformers   )")
            except Exception as e:
                error_str = str(e)
                print(f"    SparseEncoder  : {error_str}")
                
                # torch   
                if "torch.load" in error_str or "CVE-2025-32434" in error_str or "torch>=2.6" in error_str:
                    print("   torch    (: 2.5.1, : 2.6+)")
                    print("    :")
                    print("     1. torch : pip install torch>=2.6")
                    print("     2.   safetensors   ")
                    print("     SPLADE    .")
                    raise RuntimeError("torch  2.6 . torch>=2.6  safetensors   .")
            
            # SentenceTransformer   ( SPLADE sparse vector  )
            print("    SentenceTransformer SPLADE sparse vector  .")
            raise RuntimeError("SPLADE    . SparseEncoder .")
    
    def encode_query(self, query: str):
        """
         Sparse Vector 
        
        Args:
            query:  
        
        Returns:
            Sparse vector (torch tensor  numpy array, 30522)
        """
        self.load_model()
        
        if self.use_sparse_encoder:
            # SparseEncoder 
            query_emb = self.model.encode_query([query])
            # torch tensor  
            import torch
            if isinstance(query_emb, torch.Tensor):
                # sparse tensor  dense 
                if query_emb.is_sparse:
                    query_emb = query_emb.to_dense()
                # numpy 
                query_emb = query_emb.cpu().numpy()
            #     ( 1)
            if len(query_emb.shape) > 1:
                return query_emb[0]
            return query_emb
        else:
            # SentenceTransformer  ( )
            # SPLADE sparse vector      
            raise NotImplementedError("SentenceTransformer SPLADE sparse vector  . SparseEncoder .")
    
    def encode_document(self, document: str):
        """
         Sparse Vector 
        
        Args:
            document:  
        
        Returns:
            Sparse vector (torch tensor  numpy array, 30522)
        """
        self.load_model()
        
        if self.use_sparse_encoder:
            # SparseEncoder 
            doc_emb = self.model.encode_document([document])
            # torch tensor  
            import torch
            if isinstance(doc_emb, torch.Tensor):
                # sparse tensor  dense 
                if doc_emb.is_sparse:
                    doc_emb = doc_emb.to_dense()
                # numpy 
                doc_emb = doc_emb.cpu().numpy()
            #    
            if len(doc_emb.shape) > 1:
                return doc_emb[0]
            return doc_emb
        else:
            raise NotImplementedError("SentenceTransformer SPLADE sparse vector  .")
    
    def compute_similarity(
        self,
        query_vec,
        doc_vec
    ) -> float:
        """
             (dot product)
        
        Args:
            query_vec:  sparse vector (torch tensor  numpy array)
            doc_vec:  sparse vector (torch tensor  numpy array)
        
        Returns:
             
        """
        # torch tensor  numpy 
        import torch
        if isinstance(query_vec, torch.Tensor):
            if query_vec.is_sparse:
                query_vec = query_vec.to_dense()
            query_vec = query_vec.cpu().numpy()
        if isinstance(doc_vec, torch.Tensor):
            if doc_vec.is_sparse:
                doc_vec = doc_vec.to_dense()
            doc_vec = doc_vec.cpu().numpy()
        
        # Sparse vector dot product
        similarity = np.dot(query_vec, doc_vec)
        return float(similarity)
    
    def search(
        self,
        query: str,
        documents: List[str],
        top_k: int = 10
    ) -> List[tuple]:
        """
         
        
        Args:
            query:  
            documents:    
            top_k:    
        
        Returns:
            (, )  
        """
        query_vec = self.encode_query(query)
        
        #   
        scores = []
        for doc in documents:
            doc_vec = self.encode_document(doc)
            score = self.compute_similarity(query_vec, doc_vec)
            scores.append((doc, score))
        
        #   
        scores.sort(key=lambda x: x[1], reverse=True)
        
        return scores[:top_k]


class NaverSPLADEDBRetriever:
    """Naver SPLADE   DB """
    
    def __init__(
        self,
        db_config: Dict,
        model_name: str = "naver/splade-v3",
        device: str = None
    ):
        """
        Args:
            db_config:   
            model_name: SPLADE  
            device:   ('cuda'  'cpu', None  )
        """
        self.db_config = db_config
        # device None  , 'cuda'  GPU  
        if device is None:
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.splade_retriever = NaverSPLADERetriever(model_name, device=device)
        self.conn = None
        print(f" SPLADE DB Retriever : device={device}")
    
    def connect_db(self):
        """DB """
        if self.conn is None or self.conn.closed:
            self.conn = psycopg2.connect(**self.db_config)
    
    def search_law_splade(
        self,
        query: str,
        top_k: int = 10
    ) -> List[Dict]:
        """ SPLADE """
        self.connect_db()
        
        try:
            #  
            query_vec = self.splade_retriever.encode_query(query)
            
            if query_vec is None or query_vec.size == 0:
                return []
        except Exception as e:
            print(f"      : {e}")
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
        
        #  chunk   
        results = []
        for chunk_id, doc_id, content, law_name in chunks:
            try:
                doc_vec = self.splade_retriever.encode_document(content)
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
                #      
                continue
        
        #   
        results.sort(key=lambda x: x['splade_score'], reverse=True)
        
        return results[:top_k]
    
    def search_criteria_splade(
        self,
        query: str,
        top_k: int = 10
    ) -> List[Dict]:
        """ SPLADE """
        self.connect_db()
        
        try:
            #  
            query_vec = self.splade_retriever.encode_query(query)
            
            if query_vec is None or query_vec.size == 0:
                return []
        except Exception as e:
            print(f"      : {e}")
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
        
        #  chunk   
        results = []
        for chunk_id, doc_id, content, item in chunks:
            try:
                doc_vec = self.splade_retriever.encode_document(content)
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
                #      
                continue
        
        #   
        results.sort(key=lambda x: x['splade_score'], reverse=True)
        
        return results[:top_k]


#  
if __name__ == "__main__":
    #  
    print("=== Naver SPLADE   ===")
    retriever = NaverSPLADERetriever()
    
    query = " 750 "
    print(f"\nQuery: {query}")
    print("Encoding query...")
    
    try:
        query_vec = retriever.encode_query(query)
        print(f" Encoded sparse vector (shape: {query_vec.shape})")
        
        # numpy array  ( )
        import torch
        if isinstance(query_vec, torch.Tensor):
            if query_vec.is_sparse:
                query_vec = query_vec.to_dense()
            query_vec = query_vec.cpu().numpy()
        
        # 0   
        non_zero_count = np.count_nonzero(query_vec)
        print(f"  Non-zero values: {non_zero_count}")
        
        # Top-10 
        top_indices = np.argsort(query_vec)[-10:][::-1]
        print("\nTop 10 token indices ():")
        for idx in top_indices:
            if query_vec[idx] > 0:
                print(f"  Token {idx}: {query_vec[idx]:.4f}")
        
        #   
        test_doc = " 750   "
        print(f"\nDocument: {test_doc}")
        doc_vec = retriever.encode_document(test_doc)
        similarity = retriever.compute_similarity(query_vec, doc_vec)
        print(f" Similarity: {similarity:.4f}")
        
    except Exception as e:
        print(f" Error: {e}")
        import traceback
        traceback.print_exc()
        print("\nNote:    :")
        print("  1. HuggingFace      ")
        print("  2. sentence-transformers : pip install sentence-transformers")
        print("  3. HF_TOKEN   ")
