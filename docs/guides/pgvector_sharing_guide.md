# pgvector   

****: 2026-01-06  
****: Docker  pgvector    

---

##  

1. [](#)
2. [() ](#-)
3. [() ](#-)
4. [Docker   ](#docker---)
5. [  ](#--)
6. [ ](#-)

---

## 

###   

|  |  |  |   |
|------|------|------|----------|
| ** ** |  ,    |    (100-500MB) |   -   |
| **Docker  ** |    | Docker    |    |
| ** DB ** |   |   |    |

###   

```mermaid
flowchart LR
    A[] -->|1.  | B[ ]
    B -->|2. | C[.sql.gz ]
    C -->|3. | D[/]
    D -->|4. | E[]
    E -->|5. | F[ DB]
    F -->|6. | G[]
    
    style A fill:#e1f5ff
    style E fill:#fff3e0
    style G fill:#c8e6c9
```

---

## () 

### Step 1:   

```bash
#  :    
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# Docker   
docker ps | grep ddoksori_db

#    (SQL  )
docker exec ddoksori_db psql -U postgres -d ddoksori -c "
SELECT 
    COUNT(DISTINCT doc_id) as total_docs,
    COUNT(*) as total_chunks,
    COUNT(embedding) as embedded_chunks,
    CASE 
        WHEN COUNT(*) > 0 THEN COUNT(embedding)::float / COUNT(*) * 100 
        ELSE 0 
    END as embed_rate
FROM chunks;
"
```

** **:
- [ ] Docker    
- [ ]     
- [ ]    (100% )

### Step 2:    

```bash
#  :    
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

#    
ls -lh backend/scripts/database/export_vectordb.sh

#   
chmod +x backend/scripts/database/export_vectordb.sh
```

### Step 3:  

```bash
#  :    
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# Docker    
docker ps | grep ddoksori_db

#    (     )
./backend/scripts/database/export_vectordb.sh

#      
cd backend/scripts/database
./export_vectordb.sh
```

****: 
-   `pg_dump`   Docker   .
- `pg_dump: command not found`   Docker    .

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
```

### Step 4:   

```bash
#  :    
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

#    (   )
ls -lh backend/scripts/database/vectordb_backups/ 2>/dev/null || echo "  .   ."

#    (  )
find backend/scripts/database/vectordb_backups -name "*.sql.gz" -type f -exec gunzip -t {} \; 2>&1
```

****: 
-    `ls`  `total 0` , `find`    .  .
-       .
-    :
  ```bash
  find backend/scripts/database/vectordb_backups -name "*.sql.gz" -type f
  ```

### Step 5:  

     :

```bash
#  :    
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

#   
find backend/scripts/database/vectordb_backups -name "*_metadata.json" -type f -exec cat {} \;
```

****: 
-      .  .
-      .
-    :
  ```bash
  ls -lh backend/scripts/database/vectordb_backups/
  ```

** **:
```json
{
  "backup_timestamp": "20260106_153000",
  "database_name": "ddoksori",
  "host": "localhost",
  "port": "5432",
  "compressed_file": "ddoksori_vectordb_20260106_153000.sql.gz",
  "file_size": "145M",
  "created_by": "user",
  "backup_date": "2026-01-06T15:30:00+09:00"
}
```

### Step 6:   

####  1:   ()

**Google Drive / Dropbox / OneDrive**:
1.    
2.   
3.   

****:
-   100MB   Google Drive     
-   Google Drive    

####  2:   

```bash
#  :    
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# SCP  
find backend/scripts/database/vectordb_backups -name "*.sql.gz" -type f -exec scp {} user@server:/shared/vectordb/ \;

#  rsync  (  )
rsync -avz backend/scripts/database/vectordb_backups/ddoksori_vectordb_*.sql.gz \
    user@server:/shared/vectordb/ 2>/dev/null || \
    find backend/scripts/database/vectordb_backups -name "*.sql.gz" -type f -exec rsync -avz {} user@server:/shared/vectordb/ \;
```

####  3: Git LFS (50MB  )

```bash
#  :    
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# Git LFS  ( 1)
git lfs install

# .gitattributes  
echo "*.sql.gz filter=lfs diff=lfs merge=lfs -text" >> .gitattributes

#     (  )
find backend/scripts/database/vectordb_backups -name "*.sql.gz" -type f -exec git add {} \;
git commit -m "Add vectordb backup"
git push
```

****: Git LFS     50MB   

### Step 7:   

   :

1. **     **
2. ** ** (: `ddoksori_vectordb_20260106_153000.sql.gz`)
3. ** ** (  )
4. **  ** (    )
5. **  ** ()

** **:
```
,

pgvector    .

  :
- : ddoksori_vectordb_20260106_153000.sql.gz
- : 145MB
- : [  ]

  :
   :
[] docs/guides/pgvector_sharing_guide.md#-

  !
```

---

## () 

### Step 1:  

#### 1.1 Docker  

```bash
# Docker  
docker --version
docker-compose --version

#   (  )
git clone <repository-url>
cd <->

#  :    
pwd  #    
```

#### 1.2 PostgreSQL  

```bash
# Docker Compose PostgreSQL  
docker-compose up -d db

#   
docker ps | grep ddoksori_db

#    (   -it  )
docker exec ddoksori_db psql -U postgres -d ddoksori -c "SELECT version();"
```

#### 1.3   

```bash
#  :    
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# backend/.env  
cat > backend/.env << EOF
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ddoksori
DB_USER=postgres
DB_PASSWORD=postgres
EOF
```

### Step 2:   

####  1:   

```bash
#  :    
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

#   
mkdir -p backend/scripts/database/vectordb_backups

# Google Drive    
mv ~/Downloads/ddoksori_vectordb_*.sql.gz \
   backend/scripts/database/vectordb_backups/ 2>/dev/null || \
   find ~/Downloads -name "ddoksori_vectordb_*.sql.gz" -type f -exec mv {} backend/scripts/database/vectordb_backups/ \;

####  2: SCP 

```bash
#  :    
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

#   
mkdir -p backend/scripts/database/vectordb_backups

#  
scp user@server:/shared/vectordb/ddoksori_vectordb_*.sql.gz \
    backend/scripts/database/vectordb_backups/ 2>/dev/null || \
    echo "   .   ."
```

### Step 3:   

```bash
#  :    
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

#    (zsh glob   )
find backend/scripts/database/vectordb_backups -name "*.sql.gz" -type f -ls

#  ls  (  )
ls -lh backend/scripts/database/vectordb_backups/*.sql.gz 2>/dev/null || echo "  ."

#    
find backend/scripts/database/vectordb_backups -name "*.sql.gz" -type f -exec gunzip -t {} \;

#    ( )
find backend/scripts/database/vectordb_backups -name "*.sql.gz" -type f -exec du -h {} \;
```

### Step 4:   

```bash
#    
ls -lh backend/scripts/database/import_vectordb.sh

#   
chmod +x backend/scripts/database/import_vectordb.sh
```

### Step 5:  

** **:      !

```bash
#  :    
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# Docker    
docker ps | grep ddoksori_db

#    (     )
./backend/scripts/database/import_vectordb.sh \
    backend/scripts/database/vectordb_backups/ddoksori_vectordb_20260106_153000.sql.gz

#      
cd backend/scripts/database
./import_vectordb.sh vectordb_backups/ddoksori_vectordb_20260106_153000.sql.gz
```

****: 
-   `psql`   Docker   .
- `psql: command not found`   Docker    .

** **:
```
================================================================================
Vector DB 
================================================================================
 : vectordb_backups/ddoksori_vectordb_20260106_153000.sql.gz
: ddoksori
: localhost:5432

  :    !
? (yes/no): yes

   ...
   : vectordb_backups/ddoksori_vectordb_20260106_153000.sql

     ...
    

   ...
  !

   ...
================================================================================
    
================================================================================
 : 11976
 : 20269
 : 20269
================================================================================
```

### Step 6:  

#### 6.1   

```bash
#  :    
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

#    (SQL  )
#  : chunks      (   )
docker exec ddoksori_db psql -U postgres -d ddoksori -c "
SELECT 
    COUNT(DISTINCT doc_id) as total_docs,
    COUNT(*) as total_chunks,
    COUNT(embedding) as embedded_chunks,
    CASE 
        WHEN COUNT(*) > 0 THEN COUNT(embedding)::float / COUNT(*) * 100 
        ELSE 0 
    END as embed_rate
FROM chunks;
" 2>&1 || echo " chunks  .   ."
```

#### 6.2 SQL  

```bash
#  :    
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

#  1: docker exec  SQL  ()
#  : chunks      (   )
docker exec ddoksori_db psql -U postgres -d ddoksori -c "
SELECT 
    COUNT(DISTINCT doc_id) as total_docs,
    COUNT(*) as total_chunks,
    COUNT(embedding) as embedded_chunks,
    CASE 
        WHEN COUNT(*) > 0 THEN COUNT(embedding)::float / COUNT(*) * 100 
        ELSE 0 
    END as embed_rate
FROM chunks;
" 2>&1 || echo " chunks  .   ."

#  2:  psql  (  )
# docker exec -it ddoksori_db psql -U postgres -d ddoksori
# psql   SQL    \q 
```

#### 6.3   

```bash
#  :    
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

#     
conda run -n dsr python -c "
import sys
sys.path.insert(0, 'backend')
from app.rag import VectorRetriever

db_config = {
    'host': 'localhost',
    'port': 5432,
    'database': 'ddoksori',
    'user': 'postgres',
    'password': 'postgres'
}

retriever = VectorRetriever(db_config)
results = retriever.search('  ', top_k=3)
print(f'   : {len(results)} ')
retriever.close()
"
```

### Step 7: RAG  

```bash
#  :    
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

#   RAG  
conda run -n dsr python tests/rag/test_multi_stage_rag.py --test-id TC001
```

---

## Docker   

###  1: Docker  

####  

```bash
#  :    
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# 1.  DB   
docker commit ddoksori_db ddoksori_vectordb:v1.0

# 2.  tar  
docker save ddoksori_vectordb:v1.0 | gzip > ddoksori_vectordb_v1.0.tar.gz

# 3.   (  )
```

####  

```bash
#  :    
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# 1.  
docker load < ddoksori_vectordb_v1.0.tar.gz

# 2.     
docker-compose down db
docker rm ddoksori_db 2>/dev/null || true

# 3.   
docker run -d \
  --name ddoksori_db \
  -p 5432:5432 \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=ddoksori \
  ddoksori_vectordb:v1.0

# 4. 
docker exec ddoksori_db psql -U postgres -d ddoksori -c "SELECT COUNT(*) FROM chunks;"
```

###  2: Docker  

####  

```bash
#  :    
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# 1.  
docker run --rm \
  -v ddoksori_postgres_data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/postgres_data_backup.tar.gz -C /data .

# 2.   
```

####  

```bash
#  :    
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# 1.  
docker run --rm \
  -v ddoksori_postgres_data:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/postgres_data_backup.tar.gz -C /data

# 2.  
docker-compose restart db
```

---

##   

###  

    :

- [ ] Docker    
- [ ]   
- [ ]    
- [ ]    
- [ ]   100%
- [ ]    
- [ ] RAG   

###   

####  1:   

****: `ERROR: relation "documents" already exists`

****:
```bash
#  :    
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

#      
docker exec ddoksori_db psql -U postgres -d ddoksori \
  -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

# pgvector  
docker exec ddoksori_db psql -U postgres -d ddoksori \
  -c "CREATE EXTENSION IF NOT EXISTS vector;"

#  
find backend/scripts/database/vectordb_backups -name "*.sql.gz" -type f | head -1 | \
  xargs -I {} ./backend/scripts/database/import_vectordb.sh {}
```

####  2: `pg_dump: command not found`  `psql: command not found`

****:       `pg_dump: command not found`  `psql: command not found`  

****:   PostgreSQL     

****:

1. **  ()**: 
   -     Docker   .
   - Docker    :
   ```bash
   docker ps | grep ddoksori_db
   ```
   -      Docker  .

2. **  ()**:
   -  PostgreSQL  :
   ```bash
   # Ubuntu/Debian
   sudo apt-get update
   sudo apt-get install postgresql-client
   
   # macOS (Homebrew)
   brew install postgresql
   ```

****: 
-   `pg_dump`/`psql`   Docker   .
- Docker      ,  `docker-compose up -d db` .

####  3:  

****: `Permission denied: ./export_vectordb.sh`

****:
```bash
chmod +x backend/scripts/database/export_vectordb.sh
chmod +x backend/scripts/database/import_vectordb.sh
```

####  4:   

****: `gunzip: corrupt input`

****:
-    
-      
-     

####  5:   

****: `No space left on device`

****:
```bash
#   
df -h

#  Docker  
docker system prune -a

#       (    2)
```

####  6: pgvector  

****: `ERROR: type "vector" does not exist`

****:
```bash
#  :    
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# pgvector  
docker exec ddoksori_db psql -U postgres -d ddoksori \
  -c "CREATE EXTENSION IF NOT EXISTS vector;"

# 
docker exec ddoksori_db psql -U postgres -d ddoksori \
  -c "SELECT * FROM pg_extension WHERE extname = 'vector';"
```

---

##  

###  
- [  ](./embedding_process_guide.md) -     
- [Vector DB  ](./Vector_DB__.md) -     

###  
- `backend/scripts/database/export_vectordb.sh` -   
- `backend/scripts/database/import_vectordb.sh` -  
- SQL     ( Step 1 )

###  
- `docker-compose.yml` - Docker Compose 
- `backend/.env` -   

---

## 

###  

- [ ]    
- [ ]     
- [ ]   
- [ ]    
- [ ]      
- [ ]    

###  

- [ ] Docker   
- [ ] PostgreSQL   
- [ ]    
- [ ]    
- [ ]   
- [ ]   
- [ ] RAG   

---

****: 2026-01-06
