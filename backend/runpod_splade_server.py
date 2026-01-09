# backend/runpod_splade_server.py
"""
RunPod  SPLADE API 
 SSH    SPLADE  
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import torch
import numpy as np
from typing import List, Dict, Optional
import os
from dotenv import load_dotenv

# transformers  
try:
    import transformers
    print(f" transformers {transformers.__version__}  ")
except ImportError as e:
    print(f" transformers    : {e}")
    print("\n :")
    print("  pip install --upgrade transformers>=4.41.0")
    raise

# PreTrainedModel import 
try:
    from transformers import PreTrainedModel
    print(f" PreTrainedModel import ")
except (ImportError, ModuleNotFoundError) as e:
    print(f" PreTrainedModel import : {e}")
    print("\n transformers    .")
    print("\n  (RunPod ):")
    print("  1. transformers  :")
    print("     pip uninstall transformers -y")
    print("     pip install transformers>=4.41.0")
    print("")
    print("  2.     :")
    print("     pip cache purge")
    print("     pip install --force-reinstall transformers>=4.41.0")
    print("")
    print("  3.   :")
    print("     pip install --upgrade transformers>=4.41.0 torch>=2.6")
    raise

# sentence-transformers    SparseEncoder import
try:
    import sentence_transformers
    version = sentence_transformers.__version__
    major_version = int(version.split('.')[0])
    
    if major_version < 5:
        raise ImportError(
            f"sentence-transformers  5.0.0  . "
            f" : {version}. "
            f": pip install --upgrade sentence-transformers>=5.0.0"
        )
    
    from sentence_transformers import SparseEncoder
    print(f" sentence-transformers {version} - SparseEncoder  ")
except ImportError as e:
    print(f" SparseEncoder import : {e}")
    print("\n :")
    print("  1. transformers : pip install --upgrade transformers>=4.41.0")
    print("  2. sentence-transformers : pip install --upgrade sentence-transformers>=5.0.0")
    raise

#   
load_dotenv()

# hf_transfer   (   )
try:
    import hf_transfer
except ImportError:
    os.environ['HF_HUB_ENABLE_HF_TRANSFER'] = '0'
    print("  hf_transfer      ")
    print("     : pip install hf_transfer")

# HuggingFace  
HF_TOKEN = os.getenv('HF_TOKEN') or os.getenv('HUGGINGFACE_TOKEN')

# 1.   (GPU )
device = 'cuda' if torch.cuda.is_available() else 'cpu'
print(f" Loading SPLADE model on {device}...")

# torch  
torch_version = torch.__version__
print(f"  PyTorch version: {torch_version}")

# torch 2.6   
try:
    major, minor = map(int, torch_version.split('.')[:2])
    if major < 2 or (major == 2 and minor < 6):
        print(f"    PyTorch  2.6  (: {torch_version})")
        print(f"   safetensors    ...")
        # safetensors  
        import os
        os.environ['SAFETENSORS_FAST_GPU'] = '1'
        os.environ['TRANSFORMERS_SAFE_LOADING'] = '1'
except:
    pass

try:
    model = SparseEncoder(
        "naver/splade-v3",
        token=HF_TOKEN if HF_TOKEN else None,
        trust_remote_code=True
    )
    print(f" SPLADE model loaded successfully on {device}!")
except Exception as e:
    error_str = str(e)
    if "torch.load" in error_str or "CVE-2025-32434" in error_str or "torch>=2.6" in error_str:
        print(f" Error loading SPLADE model: {error_str}")
        print(f"\n  :")
        print(f"   RunPod torch :")
        print(f"   pip install --upgrade torch>=2.6")
        print(f"    CUDA  :")
        print(f"   pip install torch>=2.6 --index-url https://download.pytorch.org/whl/cu121")
        raise RuntimeError("torch  2.6 .  .")
    else:
        print(f" Error loading SPLADE model: {e}")
        raise

# 2. FastAPI  
app = FastAPI(title="SPLADE Sparse Encoder API")

# 3. /  
class EncodeRequest(BaseModel):
    texts: List[str]

class EncodeResponse(BaseModel):
    embeddings: List[List[float]]  # Sparse vector dense 
    shapes: List[List[int]]  #  embedding shape

class SimilarityRequest(BaseModel):
    query_embedding: List[float]
    document_embeddings: List[List[float]]

class SimilarityResponse(BaseModel):
    similarities: List[float]

# 4.  
def sparse_to_dense(sparse_vec, vocab_size=30522):
    """
    Sparse tensor dense numpy array 
    
    Args:
        sparse_vec: torch.Tensor (sparse  dense)
        vocab_size: vocabulary size (SPLADE-v3 30522)
    
    Returns:
        numpy array
    """
    if isinstance(sparse_vec, torch.Tensor):
        if sparse_vec.is_sparse:
            sparse_vec = sparse_vec.to_dense()
        sparse_vec = sparse_vec.cpu().numpy()
    
    #     
    if len(sparse_vec.shape) > 1:
        return sparse_vec[0]
    return sparse_vec

# 5.  
@app.post("/encode_query", response_model=EncodeResponse)
def encode_query(request: EncodeRequest):
    """
      Sparse Vector 
    """
    try:
        query_embeddings = model.encode_query(request.texts)
        
        # Sparse tensor dense numpy array 
        dense_embeddings = []
        for emb in query_embeddings:
            dense_emb = sparse_to_dense(emb)
            dense_embeddings.append(dense_emb.tolist())
        
        return EncodeResponse(
            embeddings=dense_embeddings,
            shapes=[list(emb.shape) for emb in query_embeddings]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query encoding error: {str(e)}")

@app.post("/encode_document", response_model=EncodeResponse)
def encode_document(request: EncodeRequest):
    """
      Sparse Vector 
    """
    try:
        doc_embeddings = model.encode_document(request.texts)
        
        # Sparse tensor dense numpy array 
        dense_embeddings = []
        for emb in doc_embeddings:
            dense_emb = sparse_to_dense(emb)
            dense_embeddings.append(dense_emb.tolist())
        
        return EncodeResponse(
            embeddings=dense_embeddings,
            shapes=[list(emb.shape) for emb in doc_embeddings]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document encoding error: {str(e)}")

@app.post("/similarity", response_model=SimilarityResponse)
def compute_similarity(request: SimilarityRequest):
    """
         (dot product)
    """
    try:
        query_vec = np.array(request.query_embedding)
        similarities = []
        
        for doc_vec in request.document_embeddings:
            doc_vec = np.array(doc_vec)
            similarity = float(np.dot(query_vec, doc_vec))
            similarities.append(similarity)
        
        return SimilarityResponse(similarities=similarities)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Similarity computation error: {str(e)}")

@app.get("/")
def root():
    return {
        "message": "SPLADE Sparse Encoder API is running",
        "device": device,
        "model": "naver/splade-v3",
        "cuda_available": torch.cuda.is_available()
    }

@app.get("/health")
def health():
    """  """
    return {
        "status": "healthy",
        "device": device,
        "cuda_available": torch.cuda.is_available()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
