# backend/runpod_embed_server.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
import torch
from typing import List

# 1. 모델 로드 (GPU 사용)
device = 'cuda' if torch.cuda.is_available() else 'cpu'
model = SentenceTransformer('nlpai-lab/KURE-v1', device=device)
print(f"Model loaded on {device}")

# 2. FastAPI 앱 생성
app = FastAPI()

# 3. 요청/응답 모델 정의
class EmbedRequest(BaseModel):
    texts: List[str]

class EmbedResponse(BaseModel):
    embeddings: List[List[float]]

# 4. 임베딩 엔드포인트
@app.post("/embed", response_model=EmbedResponse)
def embed_texts(request: EmbedRequest):
    try:
        embeddings = model.encode(request.texts, convert_to_tensor=False).tolist()
        return EmbedResponse(embeddings=embeddings)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def root():
    return {"message": "Embedding server is running", "device": device}