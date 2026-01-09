# backend/runpod_splade_server.py
"""
RunPod에서 실행할 SPLADE API 서버
로컬에서 SSH 터널을 통해 접근하여 SPLADE 검색 수행
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import torch
import numpy as np
from typing import List, Dict, Optional
import os
from dotenv import load_dotenv

# transformers 라이브러리 확인
try:
    import transformers
    print(f"✅ transformers {transformers.__version__} 로드 성공")
except ImportError as e:
    print(f"❌ transformers 라이브러리를 찾을 수 없습니다: {e}")
    print("\n해결 방법:")
    print("  pip install --upgrade transformers>=4.41.0")
    raise

# PreTrainedModel import 테스트
try:
    from transformers import PreTrainedModel
    print(f"✅ PreTrainedModel import 성공")
except (ImportError, ModuleNotFoundError) as e:
    print(f"❌ PreTrainedModel import 실패: {e}")
    print("\n💡 transformers 라이브러리가 손상되었을 수 있습니다.")
    print("\n해결 방법 (RunPod에서 실행):")
    print("  1. transformers 완전 재설치:")
    print("     pip uninstall transformers -y")
    print("     pip install transformers>=4.41.0")
    print("")
    print("  2. 또는 캐시 클리어 후 재설치:")
    print("     pip cache purge")
    print("     pip install --force-reinstall transformers>=4.41.0")
    print("")
    print("  3. 의존성과 함께 재설치:")
    print("     pip install --upgrade transformers>=4.41.0 torch>=2.6")
    raise

# sentence-transformers 버전 확인 및 SparseEncoder import
try:
    import sentence_transformers
    version = sentence_transformers.__version__
    major_version = int(version.split('.')[0])
    
    if major_version < 5:
        raise ImportError(
            f"sentence-transformers 버전이 5.0.0 이상이어야 합니다. "
            f"현재 버전: {version}. "
            f"업그레이드: pip install --upgrade sentence-transformers>=5.0.0"
        )
    
    from sentence_transformers import SparseEncoder
    print(f"✅ sentence-transformers {version} - SparseEncoder 사용 가능")
except ImportError as e:
    print(f"❌ SparseEncoder import 실패: {e}")
    print("\n해결 방법:")
    print("  1. transformers 업그레이드: pip install --upgrade transformers>=4.41.0")
    print("  2. sentence-transformers 업그레이드: pip install --upgrade sentence-transformers>=5.0.0")
    raise

# 환경 변수 로드
load_dotenv()

# hf_transfer가 없으면 비활성화 (모델 다운로드 오류 방지)
try:
    import hf_transfer
except ImportError:
    os.environ['HF_HUB_ENABLE_HF_TRANSFER'] = '0'
    print("⚠️  hf_transfer가 설치되지 않아 기본 다운로드 방식 사용")
    print("   빠른 다운로드를 원하면: pip install hf_transfer")

# HuggingFace 토큰 확인
HF_TOKEN = os.getenv('HF_TOKEN') or os.getenv('HUGGINGFACE_TOKEN')

# 1. 모델 로드 (GPU 사용)
device = 'cuda' if torch.cuda.is_available() else 'cpu'
print(f"🔧 Loading SPLADE model on {device}...")

# torch 버전 확인
torch_version = torch.__version__
print(f"  PyTorch version: {torch_version}")

# torch 2.6 미만인 경우 경고
try:
    major, minor = map(int, torch_version.split('.')[:2])
    if major < 2 or (major == 2 and minor < 6):
        print(f"  ⚠️  PyTorch 버전이 2.6 미만입니다 (현재: {torch_version})")
        print(f"  💡 safetensors 형식으로 모델을 로드하려고 시도합니다...")
        # safetensors 사용 강제
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
    print(f"✅ SPLADE model loaded successfully on {device}!")
except Exception as e:
    error_str = str(e)
    if "torch.load" in error_str or "CVE-2025-32434" in error_str or "torch>=2.6" in error_str:
        print(f"❌ Error loading SPLADE model: {error_str}")
        print(f"\n💡 해결 방법:")
        print(f"   RunPod에서 torch를 업그레이드하세요:")
        print(f"   pip install --upgrade torch>=2.6")
        print(f"   또는 CUDA 버전에 맞게:")
        print(f"   pip install torch>=2.6 --index-url https://download.pytorch.org/whl/cu121")
        raise RuntimeError("torch 버전이 2.6 미만입니다. 업그레이드가 필요합니다.")
    else:
        print(f"❌ Error loading SPLADE model: {e}")
        raise

# 2. FastAPI 앱 생성
app = FastAPI(title="SPLADE Sparse Encoder API")

# 3. 요청/응답 모델 정의
class EncodeRequest(BaseModel):
    texts: List[str]

class EncodeResponse(BaseModel):
    embeddings: List[List[float]]  # Sparse vector를 dense로 변환
    shapes: List[List[int]]  # 각 embedding의 shape

class SimilarityRequest(BaseModel):
    query_embedding: List[float]
    document_embeddings: List[List[float]]

class SimilarityResponse(BaseModel):
    similarities: List[float]

# 4. 유틸리티 함수
def sparse_to_dense(sparse_vec, vocab_size=30522):
    """
    Sparse tensor를 dense numpy array로 변환
    
    Args:
        sparse_vec: torch.Tensor (sparse 또는 dense)
        vocab_size: vocabulary size (SPLADE-v3는 30522)
    
    Returns:
        numpy array
    """
    if isinstance(sparse_vec, torch.Tensor):
        if sparse_vec.is_sparse:
            sparse_vec = sparse_vec.to_dense()
        sparse_vec = sparse_vec.cpu().numpy()
    
    # 배치인 경우 첫 번째만 반환
    if len(sparse_vec.shape) > 1:
        return sparse_vec[0]
    return sparse_vec

# 5. 인코딩 엔드포인트
@app.post("/encode_query", response_model=EncodeResponse)
def encode_query(request: EncodeRequest):
    """
    쿼리 텍스트를 Sparse Vector로 인코딩
    """
    try:
        query_embeddings = model.encode_query(request.texts)
        
        # Sparse tensor를 dense numpy array로 변환
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
    문서 텍스트를 Sparse Vector로 인코딩
    """
    try:
        doc_embeddings = model.encode_document(request.texts)
        
        # Sparse tensor를 dense numpy array로 변환
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
    쿼리와 문서 간 유사도 계산 (dot product)
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
    """헬스 체크 엔드포인트"""
    return {
        "status": "healthy",
        "device": device,
        "cuda_available": torch.cuda.is_available()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
