# PR #2:    Vector DB 

## 

 PR (KCA), (ECMC), (KCDRC)    PostgreSQL + pgvector , KURE-v1    .

##  

### 1.  

- **pgvector **: `docker-compose.yml` PostgreSQL  `pgvector/pgvector:pg16` 
- ** **: `backend/database/schema.sql` `cases` `chunks`  
- ** **: `backend/database/init.sql`   

### 2.  

#### Cases 
  .

|  |  |  |
|---|---|---|
| `case_uid` | VARCHAR(255) |   ID (: `kca_merged:1`) |
| `case_no` | VARCHAR(255) |  (: `2015027`) |
| `decision_date` | VARCHAR(50) |  (: `2015.05.11`) |
| `agency` | VARCHAR(50) |   (`kca`, `ecmc`, `kcdrc`) |
| `source` | VARCHAR(255) |   |

#### Chunks 
    .

|  |  |  |
|---|---|---|
| `chunk_uid` | VARCHAR(255) |   ID |
| `case_uid` | VARCHAR(255) |   ID |
| `chunk_type` | VARCHAR(50) |   (`decision`, `parties_claim`, `judgment`) |
| `text` | TEXT |   |
| `embedding` | vector(1024) | KURE-v1   |

### 3.  

`backend/scripts/embedding/embed_data_remote.py`   :

1. KURE-v1   (Hugging Face)
2. JSONL   
3.   `cases`  
4.    `chunks`  
5.    

### 4.  

`backend/data/`    :

- `kca_final_rag_chunks_normalized.jsonl` (2,059 )
- `ecmc_final_rag_chunks_normalized.jsonl` (932 )
- `kcdrc_final_rag_chunks_normalized.jsonl` (367 )

** 3,358 **

##   

### 1.  

```bash
git clone https://github.com/Maroco0109/ddoksori_demo.git
cd ddoksori_demo
git checkout feature/pr2-data-embedding
```

### 2.   

```bash
#   
cd backend
cp .env.example .env
# .env      (  )
```

### 3. Docker Compose PostgreSQL 

```bash
cd ..
docker-compose up -d db
```

### 4. Python  

```bash
cd backend
pip install -r requirements.txt
```

### 5.   

```bash
python scripts/embed_data.py
```

**  :**
- GPU  :  5-10
- CPU  :  20-30

### 6.  

PostgreSQL   :

```bash
docker exec -it ddoksori_db psql -U postgres -d ddoksori
```

```sql
--   
SELECT COUNT(*) FROM cases;

--   
SELECT COUNT(*) FROM chunks;

--  
SELECT agency, COUNT(*) FROM cases GROUP BY agency;

--   
SELECT chunk_type, COUNT(*) FROM chunks GROUP BY chunk_type;
```

##  

- ****: PostgreSQL 16 + pgvector
- ** **: KURE-v1 (nlpai-lab/KURE-v1)
  - : 1024
  -    
- **Python **:
  - `sentence-transformers`:  
  - `psycopg2-binary`: PostgreSQL 
  - `pgvector`: pgvector  

##   (PR #3)

PR #3 RAG   Vector DB   , LLM     .
