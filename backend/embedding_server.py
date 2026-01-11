import os
import torch
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
from contextlib import asynccontextmanager

from typing import List, Optional, Union

# Global model variable
model = None

class EmbeddingRequest(BaseModel):
    text: Optional[str] = None
    texts: Optional[List[str]] = None

class EmbeddingResponse(BaseModel):
    embedding: Optional[List[float]] = None
    embeddings: Optional[List[List[float]]] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global model
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Initializing Embedding Server on {device}...")
    
    # Model configuration
    model_name = os.getenv("EMBEDDING_MODEL_NAME", "nlpai-lab/KURE-v1")
    
    try:
        print(f"Loading model: {model_name}...")
        model = SentenceTransformer(model_name, device=device)
        print(f"✅ Model {model_name} loaded successfully on {device}")
    except Exception as e:
        print(f"⚠️ Failed to load {model_name}: {e}")
        fallback_model = "jhgan/ko-sroberta-multitask"
        print(f"🔄 Falling back to {fallback_model}...")
        try:
            model = SentenceTransformer(fallback_model, device=device)
            print(f"✅ Fallback model {fallback_model} loaded successfully on {device}")
        except Exception as e2:
            print(f"❌ Failed to load fallback model: {e2}")
            # Do not raise here, allow server to start but fail requests
            pass
            
    yield
    print("Shutting down model...")

app = FastAPI(title="Ddoksori Embedding API", lifespan=lifespan)

@app.post("/embed", response_model=EmbeddingResponse)
async def create_embedding(request: EmbeddingRequest):
    global model
    if model is None:
        raise HTTPException(status_code=503, detail="Model not initialized")
    
    try:
        if request.texts:
            # Batch mode
            embeddings = model.encode(request.texts, convert_to_numpy=True).tolist()
            return {"embeddings": embeddings}
        elif request.text:
            # Single mode
            embedding = model.encode(request.text, convert_to_numpy=True).tolist()
            return {"embedding": embedding}
        else:
            raise HTTPException(status_code=422, detail="Either 'text' or 'texts' field is required")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding generation failed: {str(e)}")

@app.get("/health")
async def health():
    if model is None:
        raise HTTPException(status_code=503, detail="Model not initialized")
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    # model.modules() is a generator
    model_name_or_path = "unknown"
    try:
        if hasattr(model, 'modules'):
            modules = list(model.modules())
            if modules and hasattr(modules[0], 'auto_model'):
                 model_name_or_path = modules[0].auto_model.config.name_or_path
    except:
        pass
        
    return {
        "status": "healthy", 
        "device": device,
        "model": model_name_or_path
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)
