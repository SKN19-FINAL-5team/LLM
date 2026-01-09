# pgvector Schema  -  -   

****: 2026-01-06  
****: PostgreSQL + pgvector  RAG     

---

##  

1. [  ](#--)
2. [1: Docker  ](#1-docker--)
3. [2:  ](#2--)
4. [3:  ](#3--)
5. [4:    ](#4----)
6. [5: ](#5-)
7. [](#)
8. [ ](#-)

---

##   

```mermaid
flowchart TD
    A[] --> B[Docker Compose PostgreSQL + pgvector ]
    B --> C[   schema_v2_final.sql]
    C --> D[JSONL   ]
    D --> E[   embed_data_remote.py]
    E --> F[  KURE-v1 ]
    F --> G[PostgreSQL  ]
    G --> H[   ]
    H --> I[]
    
    style A fill:#e1f5ff
    style I fill:#c8e6c9
    style B fill:#fff3e0
    style C fill:#fff3e0
    style E fill:#f3e5f5
    style F fill:#f3e5f5
    style G fill:#f3e5f5
```

###  

1. ** **: Docker PostgreSQL + pgvector  
2. ** **: `schema_v2_final.sql`     
3. ** **: JSONL     
4. ** **: KURE-v1    
5. ** **: documents chunks   
6. ****:    

---

## 1: Docker  

### 1.1 Docker Compose 

```bash
#    
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# PostgreSQL + pgvector  
docker-compose up -d db
```

### 1.2   

```bash
#    
docker ps | grep ddoksori_db

#  docker-compose 
docker-compose ps db

#  
docker logs ddoksori_db

#    (   -it  )
docker exec ddoksori_db psql -U postgres -d ddoksori -c "SELECT version();"
```

****: 
- `docker exec -it`   ,   `-it`  `docker exec` .
- `docker-compose ps`      .

### 1.3   

`backend/.env`    :

```bash
cd backend
cat > .env << EOF
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ddoksori
DB_USER=postgres
DB_PASSWORD=postgres

#  API  ( GPU  )
EMBED_API_URL=http://localhost:8001/embed
EOF
```

****: 
-      `EMBED_API_URL` 
-  GPU (RunPod )   SSH   

---

## 2:  

### 2.1   

- ** **: `backend/database/schema_v2_final.sql`
- ** **: `backend/database/init.sql` (Docker  )

### 2.2   

####  1: Docker    ()

```bash
#  :     
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

#   
pwd

#   
ls -la backend/database/schema_v2_final.sql

#  1-A: cat   (zsh/bash  ) - 
cat backend/database/schema_v2_final.sql | docker exec -i ddoksori_db psql -U postgres -d ddoksori

#  1-B:    (  )
cat "$(pwd)/backend/database/schema_v2_final.sql" | docker exec -i ddoksori_db psql -U postgres -d ddoksori

#  1-C:   (bash , zsh    )
# docker exec -i ddoksori_db psql -U postgres -d ddoksori < backend/database/schema_v2_final.sql
```

****: 
- zsh  `<`  `docker exec`         . `cat` (`|`)   .
- **"No such file or directory"   **:     .      (`$(pwd)/backend/...`) .

####  2: psql  

```bash
#  :    
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

#  PostgreSQL   
PGPASSWORD=postgres psql -h localhost -U postgres -d ddoksori -f backend/database/schema_v2_final.sql

#    
PGPASSWORD=postgres psql -h localhost -U postgres -d ddoksori -f "$(pwd)/backend/database/schema_v2_final.sql"
```

****: 
-  `psql`       1 .
-   : `which psql`  `psql --version`
- ** **:  `psql`   1 (Docker exec) .

####  3: Python  

```python
#  :    
import psycopg2
from pathlib import Path

#       
project_root = Path(__file__).parent.parent.parent if '__file__' in globals() else Path.cwd()
schema_file = project_root / "backend" / "database" / "schema_v2_final.sql"

#   
with open(schema_file, 'r', encoding='utf-8') as f:
    schema_sql = f.read()

#  
conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="ddoksori",
    user="postgres",
    password="postgres"
)

#  
cur = conn.cursor()
cur.execute(schema_sql)
conn.commit()
cur.close()
conn.close()

print("   ")
```

**  **:
```bash
#   
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
conda run -n dsr python << 'EOF'
import psycopg2
from pathlib import Path

schema_file = Path("backend/database/schema_v2_final.sql")
with open(schema_file, 'r', encoding='utf-8') as f:
    schema_sql = f.read()

conn = psycopg2.connect(
    host="localhost", port=5432, database="ddoksori",
    user="postgres", password="postgres"
)
cur = conn.cursor()
cur.execute(schema_sql)
conn.commit()
cur.close()
conn.close()
print("   ")
EOF
```

### 2.3   

#### documents 
-   
-  : `doc_id`, `doc_type`, `title`, `source_org`, `category_path`, `metadata`

#### chunks 
-      
-  : `chunk_id`, `doc_id`, `content`, `embedding vector(1024)`, `chunk_type`

#### 
- `idx_chunks_embedding`: IVFFlat  (  )
- `idx_documents_doc_type`:   
-   

### 2.4   

```bash
# Docker exec  SQL 
docker exec ddoksori_db psql -U postgres -d ddoksori -c "\dt"

# pgvector  
docker exec ddoksori_db psql -U postgres -d ddoksori -c "SELECT * FROM pg_extension WHERE extname = 'vector';"

#   
docker exec ddoksori_db psql -U postgres -d ddoksori -c "\d documents"
docker exec ddoksori_db psql -U postgres -d ddoksori -c "\d chunks"
```

** psql  **:
```bash
# Docker exec  psql 
docker exec -it ddoksori_db psql -U postgres -d ddoksori

# psql :
# \dt
# SELECT * FROM pg_extension WHERE extname = 'vector';
# \d documents
# \d chunks
# \q ()
```

---

## 3:  

### 3.1   

  `backend/data/`     JSONL   .

```bash
#  :    
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

#    (  )
find backend/data -name "*.jsonl" -type f

#    
ls -la backend/data/dispute_resolution/
ls -la backend/data/criteria/
```

**   **:
- `backend/data/dispute_resolution/ecmc_final_rag_chunks_normalized.jsonl`
- `backend/data/dispute_resolution/kca_final.jsonl`
- `backend/data/dispute_resolution/kcdrc_final_rag_chunks_normalized.jsonl`
- `backend/data/criteria/table4_lifespan_chunks.jsonl`
-    JSONL 

### 3.2  

 JSONL      :

```json
{
  "doc_id": "kca_merged:1",
  "doc_type": "mediation_case",
  "title": "  ",
  "source_org": "KCA",
  "chunks": [
    {
      "chunk_id": "kca_merged:1:decision:0",
      "chunk_index": 0,
      "chunk_total": 3,
      "chunk_type": "decision",
      "content": "  ...",
      "content_length": 250,
      "drop": false
    }
  ]
}
```

### 3.3   

- `backend/data/dispute_resolution/ecmc_final_rag_chunks_normalized.jsonl`
- `backend/data/dispute_resolution/kca_final.jsonl`
- `backend/data/dispute_resolution/kcdrc_final_rag_chunks_normalized.jsonl`
- `backend/data/criteria/table4_lifespan_chunks.jsonl`

****:   `backend/data/`      `.jsonl`  .

---

## 4:    

### 4.1 Conda  

```bash
# Conda   (     )
conda activate dsr  #  ddoksori (   )

#  conda run  (   )
conda run -n dsr python ...  #  conda run -n ddoksori python ...

#    
conda env list
```

****: 
-   Conda   `conda env list`   .
-  `dsr`  `ddoksori`  .

### 4.2   

** **: 
- `embedding_tool.py --generate-local` **   **  .
-      .
-        .

####  1:   API  ( - GPU )

**  +   ( )**:
```bash
#  :    
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# SSH   (RunPod   GPU  )
# ssh -L 8001:localhost:8000 user@remote-host

#    (  +  )
conda run -n dsr python backend/scripts/embedding/embed_data_remote.py
```

**  ( )**:
```bash
#  :    
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

#   (API  )
conda run -n dsr python backend/scripts/embedding/embed_data_remote.py --load-only

#   
conda run -n dsr python backend/scripts/embedding/embedding_tool.py --generate-local
```

####  2:    

**2  ()**:
```bash
#  :    
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# 1:  
conda run -n dsr python backend/scripts/embedding/embed_data_remote.py --load-only

# 2:    
#  :       (     )
conda run -n dsr python backend/scripts/embedding/embedding_tool.py --generate-local
```

**   ?**
- `embed_data_remote.py`: JSONL      ( )
- `embedding_tool.py`:      
-   :
  - API      
  -        
  -        

** **:
- `embedding_tool.py --generate-local`  :
  -          (1-3)
  -        ()
  -       
  -  ( )     

**   ( API )**:
```bash
#  :    
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

#  API    +  
# (EMBED_API_URL   )
conda run -n dsr python backend/scripts/embedding/embed_data_remote.py
```

**   ?**
1. ****: API      
2. ****:       
3. ** **:          
4. ** **:   ,       

** embedding_tool.py   **:
- **   **:    Hugging Face   (1-3)
- **   **:    "  ..."        ()
- **    **:          

****: 
- `embed_data.py`   .    :
  - `embed_data_remote.py`:   +   API 
    - `--load-only`:     
  - `embedding_tool.py`:    (    )
    - `--check`:   
    - `--generate-local`:    
    - `--generate-remote`:  API  
-       .
- ** ** `embedding_tool.py --generate-local`  .  `embed_data_remote.py --load-only`  .

### 4.3   

#### embed_data_remote.py 

`embed_data_remote.py`   :

1. ** **
   - PostgreSQL  
   - pgvector  
   - API   (`--load-only`   )

2. ** **
   - `backend/data/`   `.jsonl`  
   -    

3. **Documents **
   - `documents`    
   -   (   )

4. **Chunks **
   -   `content`  
   -   ( ,  )
   - `chunks`   ( )

5. ** ** (`--load-only`   )
   - KURE-v1    (1024)
   -   ( 32  )
   - `chunks`  `embedding`  

6. ** **
   -   
   -   
   -   (  )

#### embedding_tool.py 

`embedding_tool.py --generate-local`   :

1. ** **
   - PostgreSQL  
   - pgvector  

2. **   **
   - `chunks`  `embedding IS NULL`  
   - `drop = FALSE` `content`   
   -   : " X  "

3. **  **   
   - KURE-v1     (  )
   -   (1-3 ,    )
   - GPU     
   -   : ": cuda/cpu"

4. ** **
   -   ( 8  )
   -    (tqdm  )
   - `chunks`  `embedding`  

5. ** **
   -   
   -  
   -  

**       **:
-    Hugging Face  
-    ( MB)   
-    "  ..."       
-  ,      

### 4.4   

```
  API  : http://localhost:8001/embed
 API  : {'status': 'healthy', 'model': 'nlpai-lab/KURE-v1', 'dimension': 1024}

    ...
  : 3
  - kca_final_rag_chunks_normalized.jsonl
  - ecmc_final_rag_chunks_normalized.jsonl
  - kcdrc_final_rag_chunks_normalized.jsonl

   ...
  632  

 Documents  ...
 Documents  : 632

 Chunks    ...
100%|| 5547/5547 [05:23<00:00, 17.15it/s]

  !
  -  : 5,547
  -  : 5,547 (100.0%)
  -   : 457
```

---

## 5: 

### 5.1   

```bash
#      (  )
# conda run -n dsr python backend/scripts/check_embedding_status.py

#  SQL   ( 5.2  )
```

### 5.2 SQL  

```bash
# Docker exec  SQL 
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

#   
docker exec ddoksori_db psql -U postgres -d ddoksori -c "
SELECT 
    chunk_type,
    COUNT(*) as count,
    AVG(content_length) as avg_length
FROM chunks
WHERE drop = FALSE
GROUP BY chunk_type
ORDER BY count DESC;
"
```

### 5.3   

```python
#   
#  :    sys.path backend   
import sys
from pathlib import Path

#    
project_root = Path(__file__).parent.parent.parent if '__file__' in globals() else Path.cwd()
sys.path.insert(0, str(project_root / 'backend'))

from app.rag import VectorRetriever

db_config = {
    'host': 'localhost',
    'port': 5432,
    'database': 'ddoksori',
    'user': 'postgres',
    'password': 'postgres'
}

retriever = VectorRetriever(db_config)
results = retriever.search("  ", top_k=5)

print(f" : {len(results)}")
for i, chunk in enumerate(results, 1):
    print(f"{i}. : {chunk['similarity']:.3f}")
    print(f"   : {chunk['content'][:100]}...")

retriever.close()
```

**  **:
```bash
#   
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
conda run -n dsr python -c "
import sys
sys.path.insert(0, 'backend')
from app.rag import VectorRetriever
db_config = {'host': 'localhost', 'port': 5432, 'database': 'ddoksori', 'user': 'postgres', 'password': 'postgres'}
retriever = VectorRetriever(db_config)
results = retriever.search('  ', top_k=3)
print(f' : {len(results)}')
retriever.close()
"
```

---

## 

###  1: pgvector  

****: `ERROR: extension "vector" does not exist`

****:
```bash
# Docker exec  SQL 
docker exec ddoksori_db psql -U postgres -d ddoksori -c "CREATE EXTENSION IF NOT EXISTS vector;"

# 
docker exec ddoksori_db psql -U postgres -d ddoksori -c "SELECT * FROM pg_extension WHERE extname = 'vector';"
```

###  2:  API  

****: ` API  : Connection refused`

****:
1. **  ** ()
   ```bash
   #   
   cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
   
   #   (API  )
   conda run -n dsr python backend/scripts/embedding/embed_data_remote.py --load-only
   
   #     
   conda run -n dsr python backend/scripts/embedding/embedding_tool.py --generate-local
   ```

2. ** API  **:
   - SSH  
     ```bash
     ssh -L 8001:localhost:8000 user@remote-host
     ```
   -    
     ```bash
     # RunPod 
     uvicorn runpod_embed_server:app --host 0.0.0.0 --port 8000
     ```

3. **  ** (   )
   ```bash
   #   
   cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
   conda run -n dsr python backend/scripts/embedding/embedding_tool.py --generate-local
   ```

###  3:  

****: PostgreSQL OOM    

****:
1.   
   ```python
   # embed_data_remote.py
   self.batch_size = 16  #  32 → 16
   ```

2. Docker   
   ```yaml
   # docker-compose.yml
   services:
     db:
       deploy:
         resources:
           limits:
             memory: 4G
   ```

###  4:   

****:     

****:
```bash
#   
docker exec ddoksori_db psql -U postgres -d ddoksori -c "
SELECT doc_id, COUNT(*) 
FROM documents 
GROUP BY doc_id 
HAVING COUNT(*) > 1;
"

#   (:   )
docker exec ddoksori_db psql -U postgres -d ddoksori -c "
DELETE FROM documents 
WHERE ctid NOT IN (
    SELECT MIN(ctid) 
    FROM documents 
    GROUP BY doc_id
);
"
```

###  5:   

****:   

****:
1.   
   ```bash
   python backend/scripts/inspect_vectordb.py --check-quality
   ```

2.   
   -  content  
   -    

3.  
   ```bash
   docker exec ddoksori_db psql -U postgres -d ddoksori -c "
   DROP INDEX IF EXISTS idx_chunks_embedding;
   CREATE INDEX idx_chunks_embedding 
   ON chunks USING ivfflat(embedding vector_cosine_ops) 
   WITH (lists = 100);
   "
   ```

---

##  

###  
- [  ](./../backend/scripts/embedding_scripts.md) -    
- [   ](./../backend/rag/___.md) -    
- [Vector DB  ](./Vector_DB__.md) - DB   

###  
- `backend/database/schema_v2_final.sql` -  
- `backend/scripts/embedding/embed_data_remote.py` - /  
- `backend/scripts/embedding/embedding_tool.py` -    (/  )
- `backend/scripts/embedding/embedding_tool.py --check` -   

###  
- `docker-compose.yml` - Docker Compose 
- `backend/.env` -   
- `backend/database/init.sql` -   

---

##  

   :

- [ ] Docker   
- [ ]    (documents, chunks  )
- [ ] pgvector   
- [ ]    
- [ ]    (`embed_data_remote.py --load-only`  `embed_data_remote.py`)
- [ ]    (`embedding_tool.py --generate-local`  `embed_data_remote.py`)
- [ ]   100% 
- [ ]    
- [ ]     

****:        :
1.  : `embed_data_remote.py --load-only`
2.  : `embedding_tool.py --generate-local`

---

****: 2026-01-06
