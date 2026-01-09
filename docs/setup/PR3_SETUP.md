# PR #3: RAG  

## 

 PR Vector DB   LLM      RAG (Retrieval-Augmented Generation)  .

##  

### 1. RAG  

#### `backend/app/rag/retriever.py`
Vector DB    .

** :**
- `search()`:     
- `get_case_chunks()`:     
-      

#### `backend/app/rag/generator.py`
   LLM   .

** :**
- `generate_answer()`: OpenAI GPT    
- `generate_answer_stream()`:    
-      

### 2. FastAPI 

#### `backend/app/main.py`

|  |  |  |
|---|---|---|
| `/` | GET | API   |
| `/health` | GET |   DB   |
| `/search` | POST | Vector DB  (LLM  ) |
| `/chat` | POST | RAG     |
| `/chat/stream` | POST |     |
| `/case/{case_uid}` | GET |     |

### 3.  

#### `tests/integration/test_rag.py`
RAG     .

- `test_retriever()`: Vector DB    (API  )
- `test_generator()`: LLM     (API  )
- `test_full_pipeline()`:  RAG   (API  )

#### `tests/unit/test_api.py`
FastAPI     HTTP API .

- `test_health()`:  
- `test_search()`:  API 
- `test_chat()`:  API  (API  )

##   

### 1.     

```bash
git clone https://github.com/Maroco0109/ddoksori_demo.git
cd ddoksori_demo
git checkout feature/pr3-rag-system
```

### 2.   

```bash
cd backend
cp .env.example .env
```

`.env`   **OpenAI API ** :

```env
#    
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ddoksori
DB_USER=postgres
DB_PASSWORD=postgres

#   
EMBEDDING_MODEL=nlpai-lab/KURE-v1
EMBEDDING_DIMENSION=1024

#  OpenAI API   ()
OPENAI_API_KEY=your_openai_api_key_here
```

> **:** OpenAI API       , LLM   .

### 3. Python  

```bash
#   (Miniconda  )
conda activate your_env_name

#  
pip install -r requirements.txt
```

**  :**
- `openai==1.58.1`: OpenAI API 

### 4. PostgreSQL   

PR #2      .

```bash
# PostgreSQL 
cd ..
docker-compose up -d db

#   (PR #2  )
cd backend
python scripts/embed_data.py
```

### 5. FastAPI  

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

    URL API    :
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

##  

###  1: Python   

####    (API  )

```bash
cd backend
python tests/test_rag.py
```

   :
1. Vector DB   (API  )
2. LLM    (API   -  )
3.  RAG  (API   -  )

#### API   (  )

   ,  :

```bash
cd backend
python tests/test_api.py
```

###  2: cURL API 

####  

```bash
curl http://localhost:8000/health
```

####  API (API  )

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "    .",
    "top_k": 3
  }'
```

####  API (API  )

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "      ?",
    "top_k": 5
  }'
```

###  3: Swagger UI 

1.  http://localhost:8000/docs 
2.    "Try it out"  
3.    "Execute"  

##  

###  API  

```json
{
  "query": "    .",
  "results_count": 3,
  "results": [
    {
      "chunk_uid": "kca_merged:123_decision",
      "case_uid": "kca_merged:123",
      "chunk_type": "decision",
      "text": " ...",
      "case_no": "2021456",
      "decision_date": "2021.06.15",
      "agency": "kca",
      "similarity": 0.8542
    }
  ]
}
```

###  API  

```json
{
  "answer": ",         .  ( 2021456) ...",
  "chunks_used": 5,
  "model": "gpt-4o-mini",
  "sources": [
    {
      "case_no": "2021456",
      "agency": "kca",
      "decision_date": "2021.06.15",
      "chunk_type": "decision",
      "similarity": 0.8542
    }
  ]
}
```

##  

- **Vector DB**: PostgreSQL 16 + pgvector (  )
- ** **: KURE-v1 (nlpai-lab/KURE-v1, 1024)
- **LLM**: OpenAI GPT-4o-mini
- ** **: FastAPI
- **Python **:
  - `sentence-transformers`:  
  - `openai`: OpenAI API 
  - `psycopg2-binary`: PostgreSQL 
  - `pgvector`: pgvector  

##   (PR #4)

PR #4             .

##  

### OpenAI API  

```
Error: The api_key client option must be set
```

** :** `.env`   OpenAI API  .

###   

```
.      .
```

**:** 
1.  DB  .
2.      .

** :**
1. `python scripts/embed_data.py`   .
2.    .

### GPU   

** :**
```python
import torch
print(torch.cuda.is_available())  # True 
```

** :** PR #2   GPU   .
