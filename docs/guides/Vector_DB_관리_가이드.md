#  RAG  Vector DB  

****: 2026-01-06

---

##  

1. [Vector DB ](#vector-db-)
2. [  ](#--)
3. [Vector DB  ](#vector-db--)
4. [  ](#--)
5. [ ](#-)
6. [](#)

---

## Vector DB 

###   

```
 RAG 
 : PostgreSQL 15
  : pgvector
  : KURE-v1 (1024)
  : 11,976
  : 20,269
 DB : 481 MB
```

###   

1. **documents ** (29 MB)
   -   
   - doc_id, doc_type, title, source_org 

2. **chunks ** (444 MB)
   -     
   - 1024  (KURE-v1)
   - HNSW    

3. ** ** (273 MB)
   - pgvector HNSW 
   -    

---

##   

###  1:   ( )

****: 
-   
-  +  +   
-   

** **:

#### 1⃣ Vector DB  

```bash
cd /home/maroco/ddoksori_demo/backend/scripts
./export_vectordb.sh
```

** **:
```
================================================================================
Vector DB  
================================================================================
: ddoksori
: localhost:5432
 : ./vectordb_backups/ddoksori_vectordb_20260106_153000.sql

    ...
  : ./vectordb_backups/ddoksori_vectordb_20260106_153000.sql

   ...
  : ./vectordb_backups/ddoksori_vectordb_20260106_153000.sql.gz

================================================================================
  !
================================================================================
: ./vectordb_backups/ddoksori_vectordb_20260106_153000.sql.gz
: 145MB

   :
  1.   (Google Drive, Dropbox )
  2.   
  3. Git LFS (50MB  )
```

#### 2⃣   

```bash
# 1.   
cd /home/maroco/ddoksori_demo/backend/scripts

# 2.  
./import_vectordb.sh ./vectordb_backups/ddoksori_vectordb_20260106_153000.sql.gz

# 3. 
python check_embedding_status.py
```

###  2: Docker  

****:
-   
-   

```bash
# 1.  DB Docker  
docker exec ddoksori_postgres pg_dump -U postgres ddoksori > ddoksori_backup.sql

# 2. Docker  
docker commit ddoksori_postgres ddoksori_vectordb:v1.0

# 3.  
docker save ddoksori_vectordb:v1.0 | gzip > ddoksori_vectordb_v1.0.tar.gz

# 4.  
docker load < ddoksori_vectordb_v1.0.tar.gz
docker run -d --name ddoksori_postgres -p 5432:5432 ddoksori_vectordb:v1.0
```

###  3:  DB  ( )

****:
-  
-   

****:

```bash
# SSH   DB 
ssh -L 5432:localhost:5432 user@remote-server

# .env  
DB_HOST=localhost  #  
DB_PORT=5432
DB_NAME=ddoksori
DB_USER=postgres
DB_PASSWORD=your_password
```

---

## Vector DB  

###  1: `inspect_vectordb.py` ( )

** **:
```bash
cd /home/maroco/ddoksori_demo
conda run -n ddoksori python backend/scripts/inspect_vectordb.py
```

** **:
```
================================================================================
 Vector DB 
================================================================================

    :
   :           11,976
   :           20,269
   :     20,269
   :     100.00%

   :
  :             457
  :             2
  :             1,608

  :
  :             1024
  :             KURE-v1 (Korean Universal Representation)

================================================================================
   
================================================================================

   :
                                                   
--------------------------------------------------------------------------------
counsel_case                    11,342       13,524       13,524
mediation_case                     632        5,547        5,547
criteria_resolution                  1          139          139
law                                  1        1,059        1,059

  :
  documents:        29 MB
  chunks:           444 MB
   DB:          481 MB
```

**  **:
```bash
python backend/scripts/inspect_vectordb.py --check-quality
```

**  **:
```bash
python backend/scripts/inspect_vectordb.py --export-samples
# : ./vectordb_samples/vectordb_samples_20260106_153000.json
```

###  2: `check_embedding_status.py`

  :
```bash
python backend/scripts/check_embedding_status.py
```

###  3: SQL  

```sql
-- 1.  
SELECT 
    COUNT(DISTINCT doc_id) as total_docs,
    COUNT(*) as total_chunks,
    COUNT(embedding) as embedded_chunks,
    COUNT(embedding)::float / COUNT(*) * 100 as embed_rate
FROM chunks;

-- 2.   
SELECT 
    chunk_type,
    COUNT(*) as count,
    AVG(content_length) as avg_length
FROM chunks
WHERE drop = FALSE
GROUP BY chunk_type
ORDER BY count DESC;

-- 3.   
SELECT 
    chunk_id,
    content,
    1 - (embedding <=> '[0.1, 0.2, ...]'::vector) as similarity
FROM chunks
WHERE embedding IS NOT NULL
ORDER BY embedding <=> '[0.1, 0.2, ...]'::vector
LIMIT 5;

-- 4.  
SELECT 
    pg_size_pretty(pg_total_relation_size('documents')) as documents_size,
    pg_size_pretty(pg_total_relation_size('chunks')) as chunks_size,
    pg_size_pretty(pg_database_size(current_database())) as total_db_size;
```

###  4: pgAdmin / DBeaver

GUI   :
1. pgAdmin : https://www.pgadmin.org/
2.  :
   - Host: localhost
   - Port: 5432
   - Database: ddoksori
   - Username: postgres

---

##   

###   

** **:
- ** **:  
- ** **:  
- **  **: !

** **:

```bash
# crontab 
#   3 
0 3 * * * /home/maroco/ddoksori_demo/backend/scripts/export_vectordb.sh

# 7     
0 4 * * * find /home/maroco/ddoksori_demo/backend/scripts/vectordb_backups -name "*.sql.gz" -mtime +7 -delete
```

###   

```bash
# 1.    ( ,  )
pg_dump -U postgres ddoksori \
  --exclude-table-data=chunks \
  -f ddoksori_schema_only.sql

# 2.   
pg_dump -U postgres ddoksori \
  -t documents \
  -f ddoksori_documents_only.sql
```

---

##  

###   

 ** **:
- Norm : 0.8 ~ 1.2
- Variance: > 0.001
- NaN/Inf: 0

 ** **:
- Norm < 0.1:   
- Variance < 0.001:    ()
-   > 90%:  0 

**  **:
```bash
python backend/scripts/inspect_vectordb.py --check-quality
```

###   

```bash
# RAG   
python backend/scripts/test_search_quality.py

#   
python backend/scripts/test_rag_simple.py
```

---

## 

###  1:  

****:  50%  

****:
```bash
# 1.   
python backend/scripts/check_embedding_status.py

# 2.  
python backend/scripts/database/clear_database.py --force

# 3. 
python backend/scripts/embedding/embed_data_remote.py
```

###  2:   

****:     

****:
```sql
-- 1.   
SELECT COUNT(*) FROM chunks WHERE embedding IS NULL;

-- 2.  
DROP INDEX IF EXISTS idx_chunks_embedding;
CREATE INDEX idx_chunks_embedding 
ON chunks USING hnsw (embedding vector_cosine_ops);
```

###  3:  

****: PostgreSQL OOM 

****:
```bash
# docker-compose.yml 
services:
  postgres:
    environment:
      - POSTGRES_SHARED_BUFFERS=2GB    #  128MB → 2GB
      - POSTGRES_WORK_MEM=256MB        #  4MB → 256MB
```

###  4:  

****:     

****:
```sql
-- HNSW  
CREATE INDEX idx_chunks_embedding 
ON chunks USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- ANALYZE 
ANALYZE chunks;
```

---

##   

###  
- pgvector: https://github.com/pgvector/pgvector
- KURE-v1: https://huggingface.co/nlpai-lab/KURE-v1
- PostgreSQL: https://www.postgresql.org/docs/

###   
- [  ](./____.md)
- [   ](./_____.md)
- [  ](./___.md)

---

##  Quick Reference

```bash
# Vector DB  
python backend/scripts/inspect_vectordb.py

#   
python backend/scripts/check_embedding_status.py

#  
./backend/scripts/export_vectordb.sh

# 
./backend/scripts/import_vectordb.sh <backup_file>

#  
python backend/scripts/inspect_vectordb.py --check-quality

#  
python backend/scripts/inspect_vectordb.py --export-samples

#  
python backend/scripts/test_search_quality.py
```

---

****: 2026-01-06
