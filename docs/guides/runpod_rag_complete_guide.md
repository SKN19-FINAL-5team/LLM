# RunPod GPU   RAG   

****: 2026-01-07  
****: Docker   RunPod GPU ,  , RAG     

---

##  

1. [Docker   ](#1-docker---)
2. [SSH    RunPod ](#2-ssh----runpod-)
3. [RunPod  ](#3-runpod--)
4. [  ](#4---)
5. [RAG ](#5-rag-)
6. [](#6-)

---

## 1. Docker   

### 1.1 Docker  

```bash
#    
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# Docker   
docker ps

# PostgreSQL  
docker-compose up -d db

#   
docker ps | grep ddoksori_db
```

### 1.2  

```bash
#    
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

#   
cat backend/database/schema_v2_final.sql | docker exec -i ddoksori_db psql -U postgres -d ddoksori

# SPLADE   (SPLADE   )
cat backend/database/migrations/002_add_splade_sparse_vector.sql | docker exec -i ddoksori_db psql -U postgres -d ddoksori
```

**SPLADE  :**
- `splade_sparse_vector` (JSONB): SPLADE sparse vector 
- `splade_model` (VARCHAR):   
- `splade_encoded` (BOOLEAN):    
- GIN    

### 1.3  

```bash
#   
docker exec ddoksori_db psql -U postgres -d ddoksori -c "\dt"

# chunks   
docker exec ddoksori_db psql -U postgres -d ddoksori -c "\d chunks"

# SPLADE  
docker exec ddoksori_db psql -U postgres -d ddoksori -c "
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'chunks' 
AND column_name LIKE 'splade%';
"
```

### 1.4   

```bash
# backend/.env  
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cat > backend/.env << EOF
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ddoksori
DB_USER=postgres
DB_PASSWORD=postgres

#  API  ( GPU  )
EMBED_API_URL=http://localhost:8001/embed

# SPLADE API  ( GPU  )
SPLADE_API_URL=http://localhost:8002
EOF
```

---

## 2. SSH    RunPod 

### 2.1 SSH  

** **:  (`skn19.final.5team@gmail.com`) Google Drive SSH   .

** 1: gdown  ()**

```bash
# gdown 
pip install gdown

# SSH  
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# Google Drive .ssh  
#  [FOLDER_ID]  Google Drive  ID 
gdown --folder https://drive.google.com/drive/folders/[FOLDER_ID] -O ~/.ssh --remaining-ok

#   
chmod 600 ~/.ssh/runpod_key
chmod 644 ~/.ssh/runpod_key.pub
```

** 2: Google Drive  UI  **

1. Google Drive : `skn19.final.5team@gmail.com`  
2. `.ssh`  ZIP 
3.    `~/.ssh` 
4.      

### 2.2 RunPod  

1. [RunPod](https://www.runpod.io/) 
2. `Secure Cloud`  `Community Cloud` GPU 
   - ** GPU**: `NVIDIA RTX 4090`  `NVIDIA A100`
3.  : `RunPod Pytorch 2.8`   PyTorch 
   - **SPLADE  **: PyTorch 2.6  
4.     `Deploy` 
5. ****:    `SSH Key`  SSH  

### 2.3 SSH   

1. `My Pods`    `Connect`  
2. `Connect via SSH`  SSH   
   - : `ssh root@xxx.xxx.xxx.xxx -p xxxxx -i ~/.ssh/runpod_key`

### 2.4 SSH  

**  :**
```bash
#     ( )
ssh -i ~/.ssh/runpod_key -L 8001:localhost:8000 []@[IP] -p []
```

**SPLADE   ( ):**
```bash
#     ( )
ssh -i ~/.ssh/runpod_key -L 8002:localhost:8002 []@[IP] -p []
```

### 2.5 SSH   

```bash
#   
curl http://localhost:8001/

# SPLADE   ( )
curl http://localhost:8002/
```

---

## 3. RunPod  

### 3.1   

#### 3.1.1 RunPod SSH 

```bash
# 2.3  SSH  
ssh -i ~/.ssh/runpod_key []@[IP] -p []
```

#### 3.1.2     

```bash
# RunPod  
pip install fastapi uvicorn sentence-transformers hf_transfer

# API   
cat > runpod_embed_server.py << 'EOF'
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
import torch
from typing import List
import traceback

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

#   (   )
uvicorn runpod_embed_server:app --host 0.0.0.0 --port 8000
```

#### 3.1.3  

```bash
#  PC   
curl http://localhost:8001/
#  : {"message":"Embedding server is running","device":"cuda"}
```

### 3.2 SPLADE   ()

SPLADE (Sparse Lexical And Expansion)  Dense Vector Sparse Vector     .

#### 3.2.1     

```bash
# RunPod   (   screen/tmux )
# sentence-transformers 5.0.0  
pip install sentence-transformers fastapi uvicorn hf_transfer python-dotenv

# HuggingFace   ( )
# export HF_TOKEN=your_token_here

# SPLADE   
cat > runpod_splade_server.py << 'EOF'
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import torch
import numpy as np
from typing import List
import os
from dotenv import load_dotenv

load_dotenv()

try:
    from sentence_transformers import SparseEncoder
    print(f" SparseEncoder  ")
except ImportError as e:
    print(f" SparseEncoder import : {e}")
    print("   pip install --upgrade sentence-transformers>=5.0.0")
    raise

HF_TOKEN = os.getenv('HF_TOKEN') or os.getenv('HUGGINGFACE_TOKEN')

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

app = FastAPI(title="SPLADE Sparse Encoder API")

class EncodeRequest(BaseModel):
    texts: List[str]

class EncodeResponse(BaseModel):
    embeddings: List[List[float]]
    shapes: List[List[int]]

def sparse_to_dense(sparse_vec, vocab_size=30522):
    """Sparse tensor dense numpy array """
    if isinstance(sparse_vec, torch.Tensor):
        if sparse_vec.is_sparse:
            sparse_vec = sparse_vec.to_dense()
        sparse_vec = sparse_vec.cpu().numpy()
    if len(sparse_vec.shape) > 1:
        return sparse_vec[0]
    return sparse_vec

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
    return {
        "status": "healthy",
        "device": device,
        "cuda_available": torch.cuda.is_available()
    }
EOF

#   (   )
uvicorn runpod_splade_server:app --host 0.0.0.0 --port 8002
```

#### 3.2.2  

```bash
#  PC   
curl http://localhost:8002/
curl http://localhost:8002/health

# SPLADE  
conda run -n dsr python backend/scripts/splade/test_splade_remote.py
```

---

## 4.   

### 4.1 Dense Vector 

```bash
#   
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# Law  
conda run -n dsr python backend/scripts/embedding/embed_law.py

# Criteria  
conda run -n dsr python backend/scripts/embedding/embed_criteria.py

# Dispute  
conda run -n dsr python backend/scripts/embedding/embed_dispute.py

# Compensation  
conda run -n dsr python backend/scripts/embedding/embed_compensation.py
```

### 4.2 SPLADE Sparse Vector  ()

```bash
#   
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

#   SPLADE  ( API )
conda run -n dsr python backend/scripts/splade/encode_splade_vectors.py --remote --api-url http://localhost:8002

#    
conda run -n dsr python backend/scripts/splade/encode_splade_vectors.py --remote --api-url http://localhost:8002 --doc-type law

#   
conda run -n dsr python backend/scripts/splade/encode_splade_vectors.py --stats-only
```

### 4.3   

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

---

## 5. RAG 

### 5.1 Law RAG 

```bash
#   
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

conda run -n dsr python tests/rag/test_rag_law.py
```

### 5.2 Criteria RAG 

```bash
conda run -n dsr python tests/rag/test_rag_criteria.py
```

### 5.3 Dispute RAG 

```bash
conda run -n dsr python tests/rag/test_rag_dispute.py
```

### 5.4 Compensation RAG 

```bash
conda run -n dsr python tests/rag/test_rag_compensation.py
```

---

## 6. 

###  1: SSH  

****: `Connection refused`  `Permission denied`

****:
```bash
# SSH     
chmod 700 ~/.ssh
chmod 600 ~/.ssh/runpod_key
chmod 644 ~/.ssh/runpod_key.pub

# SSH  
ssh -i ~/.ssh/runpod_key -v []@[IP] -p []
```

###  2: SSH   

****: `curl http://localhost:8001/` 

****:
1. SSH     
2. RunPod    
3.   : `lsof -i :8001` (Mac/Linux)  `netstat -ano | findstr :8001` (Windows)

###  3:   

****: `psycopg2.OperationalError`

****:
```bash
# Docker   
docker ps | grep ddoksori_db

#  
docker-compose restart db

#  
docker exec ddoksori_db psql -U postgres -d ddoksori -c "SELECT version();"
```

###  4:   

****: `No such file or directory`

****:
```bash
#    
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

#   
ls -la backend/database/schema_v2_final.sql

#   
cat "$(pwd)/backend/database/schema_v2_final.sql" | docker exec -i ddoksori_db psql -U postgres -d ddoksori
```

###  5: SPLADE   "column splade_encoded does not exist" 

****: `psycopg2.errors.UndefinedColumn: column "splade_encoded" does not exist`

****:
```bash
# SPLADE  
cat backend/database/migrations/002_add_splade_sparse_vector.sql | docker exec -i ddoksori_db psql -U postgres -d ddoksori

#  
docker exec ddoksori_db psql -U postgres -d ddoksori -c "
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'chunks' 
AND column_name LIKE 'splade%';
"
```

###  6: SPLADE   

****: `torch.load`   `CVE-2025-32434` 

****:
```bash
# RunPod  
# PyTorch  
python -c "import torch; print(torch.__version__)"

# PyTorch 2.6  
pip install --upgrade torch>=2.6

# sentence-transformers 
pip install --upgrade sentence-transformers>=5.0.0
```

###  7: Google Drive SSH   

****: `gdown`  

****:
```bash
# gdown  
pip install --upgrade gdown

# Google Drive  UI  
# 1. skn19.final.5team@gmail.com  
# 2. .ssh  ZIP 
# 3.    ~/.ssh 
```

---

##  

###  
- [ ] Docker   
- [ ]    (documents, chunks  )
- [ ] SPLADE    (SPLADE  )
- [ ]    

### RunPod 
- [ ] SSH   
- [ ] RunPod    SSH  
- [ ] SSH    (: `curl http://localhost:8001/` )
- [ ] SPLADE  SSH    (SPLADE  )

###  
- [ ] RunPod    
- [ ] RunPod SPLADE    (SPLADE  )

###  
- [ ] Law   
- [ ] Criteria   
- [ ] Dispute   
- [ ] Compensation   
- [ ] SPLADE   ()

### RAG 
- [ ] Law RAG  
- [ ] Criteria RAG  
- [ ] Dispute RAG  
- [ ] Compensation RAG  

---

****: 2026-01-09  
** **: 2026-01-09 (    )
