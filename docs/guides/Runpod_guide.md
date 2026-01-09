# RunPod GPU   RAG   

## 1. SSH    RunPod 

### 1.1. SSH  
- ** ** Google Drive  .ssh  
- 1.1.1.   SSH     

### 1.1.1  SSH   

SSH       `.ssh`  .     :

- #    (!)
chmod 600 ~/.ssh/runpod_key
chmod 644 ~/.ssh/runpod_key.pub

|  |   | SSH    |    |
|------|------------|-----------------|---------------|
| **WSL2** | `~`  `$HOME` | `~/.ssh/runpod_key` | `/home/user/.ssh/runpod_key` |
| **Mac OS** | `~`  `$HOME` | `~/.ssh/runpod_key` | `/Users/user/.ssh/runpod_key` |
| **Windows 11 (Git Bash)** | `~` | `~/.ssh/runpod_key` | `/c/Users/user/.ssh/runpod_key` |
| **Windows 11 (PowerShell)** | `$env:USERPROFILE` | `$env:USERPROFILE\.ssh\runpod_key` | `C:\Users\user\.ssh\runpod_key` |

### 1.2. Runpod  

1. Runpod 
2. Pod 
    -  GPU : A40 (VRAM 48gb )
3.  
    - `Runpod PyTorch 2.8`   
    - `SPLADE`  `PyTorch 2.6`   
4. `SSH terminal access`  ! (  )

### 1.3. SSH  

- powershell, bash, zsh, Git Bash 
- `SSH over exposed TCP`    

```bash
ssh root@[IP ADDRESS] -p [PORT] -i ~/.ssh/runpod_key
```

### 1.4.  
```bash
pip install fastapi uvicorn sentence-transformers hf_transfer
```

### 1.5.   API   
- cat...  EOF    enter

```bash
# RunPod  
cat > runpod_embed_server.py << 'EOF'
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
import torch
from typing import List
import traceback

# GPU    
device = 'cuda' if torch.cuda.is_available() else 'cpu'
print(f"Loading model on {device}...")

model = SentenceTransformer('nlpai-lab/KURE-v1', device=device)
print(f" Model loaded successfully on {device}!")

app = FastAPI(title="KURE-v1 Embedding API")

class EmbedRequest(BaseModel):
    texts: List[str]

class EmbedResponse(BaseModel):
    embeddings: List[List[float]]

@app.post("/embed", response_model=EmbedResponse)
def embed_texts(request: EmbedRequest):
    try:
        embeddings = model.encode(
            request.texts,
            convert_to_tensor=False,
            show_progress_bar=False
        ).tolist()
        return EmbedResponse(embeddings=embeddings)
    except Exception as e:
        print(f" Embedding error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def root():
    return {"message": "Embedding server is running", "device": device}
EOF
```

### 1.6. KURE-v1   
```bash
# RunPod  
#      
uvicorn runpod_embed_server:app --host 0.0.0.0 --port 8000
```

### 1.7. SSH  
-  powershell, Git Bash, bash, zsh   

```bash
#  PC    
#     SPLADE   
#   [], [IP], []   
ssh -L 8001:localhost:8000 []@[IP] -p []

# :
# ssh -L 8002:localhost:8002 root@xxx-xxx-xxx-xxx.runpod.io -p 12345

#      
```

### 1.8.   
-   powershell, git bash, bash, zsh  
```bash
#  PC   
curl http://localhost:8001/

#  : {"message":"Embedding server is running","device":"cuda"}
```

## 2. SPLADE  
### 2.1. SSH 

- powershell, bash, zsh, Git Bash 
- `SSH over exposed TCP`    
- **### 1.3    **

```bash
ssh root@[IP ADDRESS] -p [PORT] -i ~/.ssh/runpod_key
```

### 2.2.   
```bash
# RunPod  
# sentence-transformers 5.0.0  
pip install sentence-transformers fastapi uvicorn hf_transfer python-dotenv
```

- **SPLADE    HF_TOKEN 
```bash
# HuggingFace    (gated  )
export HF_TOKEN=your_token_here
```

### 2.3. SPLADE    
- cat...  EOF    enter

```bash
# RunPod  
#     ,    
cat > runpod_splade_server.py << 'EOF'
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import torch
import numpy as np
from typing import List
import os
from dotenv import load_dotenv

#   
load_dotenv()

# transformers  
try:
    from sentence_transformers import SparseEncoder
    print(f" SparseEncoder  ")
except ImportError as e:
    print(f" SparseEncoder import : {e}")
    print("   pip install --upgrade sentence-transformers>=5.0.0")
    raise

# HuggingFace  
HF_TOKEN = os.getenv('HF_TOKEN') or os.getenv('HUGGINGFACE_TOKEN')

#   (GPU )
device = 'cuda' if torch.cuda.is_available() else 'cpu'
print(f" Loading SPLADE model on {device}...")

try:
    model = SparseEncoder(
        "naver/splade-v3",
        token=HF_TOKEN if HF_TOKEN else None,
        trust_remote_code=True
    )
    print(f" SPLADE model loaded successfully on {device}!")
except Exception as e:
    print(f" Error loading SPLADE model: {e}")
    raise

# FastAPI  
app = FastAPI(title="SPLADE Sparse Encoder API")

# /  
class EncodeRequest(BaseModel):
    texts: List[str]

class EncodeResponse(BaseModel):
    embeddings: List[List[float]]
    shapes: List[List[int]]

#  
def sparse_to_dense(sparse_vec, vocab_size=30522):
    """Sparse tensor dense numpy array """
    if isinstance(sparse_vec, torch.Tensor):
        if sparse_vec.is_sparse:
            sparse_vec = sparse_vec.to_dense()
        sparse_vec = sparse_vec.cpu().numpy()
    if len(sparse_vec.shape) > 1:
        return sparse_vec[0]
    return sparse_vec

#  
@app.post("/encode_query", response_model=EncodeResponse)
def encode_query(request: EncodeRequest):
    """  Sparse Vector """
    try:
        query_embeddings = model.encode_query(request.texts)
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
    """  Sparse Vector """
    try:
        doc_embeddings = model.encode_document(request.texts)
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
EOF
```

### 2.4. SPLADE  

```bash
# RunPod  
#  :      (8002)
#      
uvicorn runpod_splade_server:app --host 0.0.0.0 --port 8002
```

### 2.5. SSH  

```bash
#  PC    
#     SPLADE   
#   [], [IP], []   
ssh -L 8002:localhost:8002 []@[IP] -p []

# :
# ssh -L 8002:localhost:8002 root@xxx-xxx-xxx-xxx.runpod.io -p 12345

#      
```

## 3. Docker   
-   Runpod Linux ,   .

### 3.1. Docker Desktop  
```bash
# Docker   
docker ps

# Docker Compose 
docker-compose up -d db
```

### 3.2. PostgreSQL   

```bash
#    
docker ps | grep ddoksori_db

#  docker-compose 
docker-compose ps db

#  
docker logs ddoksori_db
```

### 3.3.  

```bash
#    
ls -la backend/database/schema_v2_final.sql

#   (cat   - zsh/bash  )
cat backend/database/schema_v2_final.sql | docker exec -i ddoksori_db psql -U postgres -d ddoksori
```

#### 3.3.1. SPLADE   (SPLADE   )

```bash
# SPLADE    
ls -la backend/database/migrations/002_add_splade_sparse_vector.sql

# SPLADE  
cat backend/database/migrations/002_add_splade_sparse_vector.sql | docker exec -i ddoksori_db psql -U postgres -d ddoksori
```

### 3.4.   

```bash
#   
docker exec ddoksori_db psql -U postgres -d ddoksori -c "\dt"

# pgvector  
docker exec ddoksori_db psql -U postgres -d ddoksori -c "SELECT * FROM pg_extension WHERE extname = 'vector';"

# documents   
docker exec ddoksori_db psql -U postgres -d ddoksori -c "\d documents"

# chunks   
docker exec ddoksori_db psql -U postgres -d ddoksori -c "\d chunks"

# SPLADE   (SPLADE   )
docker exec ddoksori_db psql -U postgres -d ddoksori -c "
SELECT 
    column_name, 
    data_type, 
    is_nullable
FROM information_schema.columns 
WHERE table_name = 'chunks' 
AND column_name LIKE 'splade%'
ORDER BY column_name;
"
```

### 3.5.   

```bash
cd backend
cp .env.example .env
```
- backend/.env   
-  API KEY 
    - **2026-01-09   **
        - OPENAI_API_KEY
        - HF_TOKEN

## 4.    
### 4.1 Conda  

```bash
#    
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# Conda  
conda activate dsr

#  conda run 
# python ...
```

### 4.2 Law  

```bash
#   
python backend/scripts/embedding/embed_law.py
```

### 4.3 Criteria  

```bash
#   
python backend/scripts/embedding/embed_criteria.py
```

### 4.4 Dispute  

```bash
#    
python backend/scripts/embedding/embed_dispute.py
```

### 4.5 Compensation  

```bash
#    
python backend/scripts/embedding/embed_compensation.py
```

### 4.6   

```bash
#   
docker exec ddoksori_db psql -U postgres -d ddoksori -c "
SELECT 
    COUNT(DISTINCT doc_id) as total_docs,
    COUNT(*) as total_chunks,
    COUNT(embedding) as embedded_chunks,
    COUNT(embedding)::float / COUNT(*) * 100 as embed_rate
FROM chunks;
"

#   
docker exec ddoksori_db psql -U postgres -d ddoksori -c "
SELECT 
    d.doc_type,
    COUNT(DISTINCT d.doc_id) as doc_count,
    COUNT(c.chunk_id) as chunk_count
FROM documents d
LEFT JOIN chunks c ON d.doc_id = c.doc_id
GROUP BY d.doc_type
ORDER BY doc_count DESC;
"
```

### 5. SPLADE 

```bash
# SPLADE sparse vector  ( API )
python backend/scripts/splade/encode_splade_vectors.py --remote --api-url http://localhost:8002

#    
python backend/scripts/splade/encode_splade_vectors.py --remote --api-url http://localhost:8002 --doc-type law
```

### 6. RAG 

### 6.1 Law RAG 

```bash
#   RAG 
python tests/rag/test_rag_law.py
```

** :**
```
 : Vector Similarity Search with doc_type='law' filter
 :
  - doc_type: law
  - chunk_types: None (  )
  - agencies: None ( )

 :
[ 1] : 0.8523
   : article
  : []  [] 750     ...
```

### 5.2 Criteria RAG 

```bash
#   RAG 
python tests/rag/test_rag_criteria.py
```

** :**
```
 : Vector Similarity Search with doc_type LIKE 'criteria_%' filter
 :
  - doc_type: criteria_item, criteria_resolution, criteria_warranty, criteria_lifespan
  - chunk_types: None (  )
  - agencies: None ( )

 :
[ 1] : 0.7845
   : item_classification
  : []  []  5...
```

### 5.3 Dispute RAG 

```bash
#    RAG 
python tests/rag/test_rag_dispute.py
```

** :**
```
 : Vector Similarity Search with doc_type='mediation_case' filter
 :
  - doc_type: mediation_case
  - chunk_types: None (  )
  - agencies: None ( )

 :
[ 1] : 0.9123
   : decision
  : KCA
  : 2024-001
  :       ...
```

### 5.4 Compensation RAG 

```bash
#    RAG 
python tests/rag/test_rag_compensation.py
```

** :**
```
 : Vector Similarity Search with doc_type='consumer_counsel_case' filter
 :
  - doc_type: consumer_counsel_case
  - chunk_types: None (  )
  - agencies: None ( )

 :
[ 1] : 0.7654
   : qa_combined
  : consumer.go.kr
  : []    []  ...
```