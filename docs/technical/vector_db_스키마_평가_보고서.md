# Vector DB   

****: 2026-01-07  
****: Multi-Agent System Product Manager  
** **:    
****: v1.0

---

## Executive Summary

    PostgreSQL + pgvector  Vector DB    . 5     , **  **      .

###  
-  **  **:  85.91ms ( < 500ms) → ****
-  ** **: 100% ,  106.64ms → ****
-  **  **: 12.80ms ( < 100ms) → ****
-  **JSONB **: 26.75ms ( < 200ms) → ****
-  ****: 10      12.26% → ****

---

## 1.  

### 1.1  
- **DBMS**: PostgreSQL 16
- ****: pgvector 0.5+
- ** **: IVFFlat (lists=100)
- ** **: 1024 (KURE-v1)
- ** **: 2026-01-07

### 1.2  
- ** **: 11,976
- ** **: 20,269 ()
- ** **: 20,259 (99.95%)
- **DB **: 
  - chunks : 327 MB (: 30 MB, : 182 MB)
  - documents : 29 MB (: 13 MB)

---

## 2.  

### 2.1    ( 1)

####  
- ** **:     
- **top_k**: 10 
- ** **: 10
- ** **:    < 500ms

#### 

|  |  |  |  |
|------|-----|------|------|
| ** ** | **85.91ms** | < 500ms |  **** |
|  | 17.43ms | - | - |
|   | 10.98ms | - | - |
|   | 711.67ms | - | - |

#### 

1. **   (85.91ms)**:
   -  (500ms) **17.2%** 
   -   20ms   ( 17.43ms)
   -       

2. **  711.67ms**:
   -      (  )
   -    100ms 
   -     

3. **IVFFlat  **:
   - 20,259    10-20ms 
   - lists=100     

#### SQL 
```sql
SELECT 
    c.chunk_id,
    c.content,
    d.doc_type,
    1 - (c.embedding <=> %s::vector) AS similarity
FROM chunks c
JOIN documents d ON c.doc_id = d.doc_id
WHERE c.drop = FALSE AND c.embedding IS NOT NULL
ORDER BY c.embedding <=> %s::vector
LIMIT 10
```

---

### 2.2   ( 2)

####  

|   |   |  (ms) |  |  |
|-----------|---------|-----------|--------|------|
| `doc_type = 'law'` | 10 | 233.40 | 100% |  |
| `doc_type = 'mediation_case'` | 10 | 61.10 | 100% |  |
| `source_org = 'KCA'` | 10 | 25.42 | 100% |  |

#### 

|  |  |  |  |
|------|-----|------|------|
| ** ** | **106.64ms** | < 500ms |   |
| **** | **100%** | 100% |   |

#### 

1. **   (100%)**:
   -     
   - doc_type, source_org   
   - WHERE     

2. **     (233.40ms)**:
   -   (1,059 ) 
   -       
   -   (500ms)  

3. **source_org   (25.42ms)**:
   -    
   -  `idx_documents_source_org` 

#### 
-   : `(doc_type, source_org, embedding)` 
-     

---

### 2.3    ( 3)

####  
- ****: `get_chunk_with_context(chunk_id, window_size)`
- **window_size**: 2 ( 2,   5 )
- ** **: < 100ms

#### 

|  |  |  |  |
|------|-----|------|------|
| ** ** | **12.80ms** | < 100ms |   |
|    | 1 | - | - |

#### 

1. **   (12.80ms)**:
   -  **12.8%** 
   -  `idx_chunks_doc_id` + `chunks_doc_id_chunk_index_key` 

2. **  1**:
   -     
   -   3-5  
   -        

3. **   **:
   - RAG       
   -      

#### SQL 
```sql
CREATE OR REPLACE FUNCTION get_chunk_with_context(
    target_chunk_id VARCHAR(255),
    window_size INTEGER DEFAULT 1
)
RETURNS TABLE (...) AS $$
...
```

---

### 2.4 JSONB   ( 4)

####  
```sql
SELECT 
    d.doc_id,
    d.doc_type,
    d.metadata->>'decision_date' AS decision_date,
    COUNT(c.chunk_id) AS chunk_count
FROM documents d
LEFT JOIN chunks c ON d.doc_id = c.doc_id AND c.drop = FALSE
WHERE d.metadata ? 'decision_date'
GROUP BY d.doc_id, d.doc_type, d.metadata->>'decision_date'
LIMIT 100
```

#### 

|  |  |  |  |
|------|-----|------|------|
| ** ** | **26.75ms** | < 200ms |   |
|   | 100  | - | - |

#### 

1. ** JSONB  (26.75ms)**:
   -  **13.4%** 
   - GIN  `idx_documents_metadata` 
   - `metadata ? 'key'`   

2. **JSONB **:
   - decision_date, case_no    
   -      
   -    

3. **GROUP BY **:
   - 100   30ms 
   -    

---

### 2.5   ( 5)

####  
- **  **: 10
- ** **:   (top_k=10)
- ** **:   < 20%

#### 

|  |  |  |  |
|------|-----|------|------|
| **  ** | 88.13ms | - | - |
| **  ** | 77.32ms | - | - |
| ** ** | **-12.26%** | < 20% |  **** |

#### 

1. **  (  12.26% )**:
   -      
   - : PostgreSQL   
   -   

2. **DB   **:
   - 10    
   -   

3. ** **:
   - 10     
   -     

#### 
-   **50-100  **  
-     Read Replica 

---

### 2.6  

####  

|   |  |  |  |
|-------------|------|--------|------|
| `idx_chunks_embedding` | **182 MB** | chunks |   (IVFFlat) |
| `idx_documents_metadata` | 7.4 MB | documents | JSONB  (GIN) |
| `idx_documents_keywords` | 5.5 MB | documents |   (GIN) |
| `chunks_pkey` | 2.3 MB | chunks | Primary Key |
| `chunks_doc_id_chunk_index_key` | 1.9 MB | chunks | Unique Constraint |
| `idx_chunks_doc_id` | 1.4 MB | chunks |    |

####  

|  |   |   |   |  |
|--------|----------|-------------|-------------|------|
| **chunks** | **327 MB** | 30 MB | ~297 MB | **9.9:1** |
| **documents** | **29 MB** | 13 MB | ~16 MB | **1.2:1** |
| chunk_relations | 40 KB | 0 KB | 40 KB | - |

#### 

1. **   (182 MB)**:
   -  (30 MB) **6.1**
   - IVFFlat   
   - HNSW     (  )

2. **/  (chunks: 9.9:1)**:
   -    10
   -   
   -     

3. **documents   (1.2:1)**:
   -    
   - GIN  (metadata, keywords) 

---

## 3.  

### 3.1   

#### documents 

****:
```sql
CREATE TABLE documents (
    doc_id VARCHAR(255) PRIMARY KEY,
    doc_type VARCHAR(50) NOT NULL,
    title TEXT NOT NULL,
    source_org VARCHAR(100),
    category_path TEXT[],
    url TEXT,
    collected_at TIMESTAMP,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

****:
-  ** **:   
-  **JSONB **:   
-  **category_path **:   
-  ****: title TEXT    ( VARCHAR(500) )

#### chunks 

****:
```sql
CREATE TABLE chunks (
    chunk_id VARCHAR(255) PRIMARY KEY,
    doc_id VARCHAR(255) REFERENCES documents(doc_id),
    chunk_index INTEGER NOT NULL,
    chunk_total INTEGER NOT NULL,
    chunk_type VARCHAR(50),
    content TEXT NOT NULL,
    content_length INTEGER,
    embedding vector(1024),
    embedding_model VARCHAR(50) DEFAULT 'KURE-v1',
    drop BOOLEAN DEFAULT FALSE,
    ...
);
```

****:
-  ** **:    
-  **drop **: Soft Delete 
-  **chunk_index/total**:    
-  **content_length**:   
-  ****: importance_score   (  )

#### chunk_relations 

****:
```sql
CREATE TABLE chunk_relations (
    source_chunk_id VARCHAR(255) REFERENCES chunks(chunk_id),
    target_chunk_id VARCHAR(255) REFERENCES chunks(chunk_id),
    relation_type VARCHAR(50) NOT NULL,
    confidence FLOAT DEFAULT 1.0,
    ...
);
```

****:
-  **  **:     
- ℹ ** **:  0
-  ** **: Graph RAG    

---

### 3.2   

####   (IVFFlat)

****:
```sql
CREATE INDEX idx_chunks_embedding 
ON chunks USING ivfflat(embedding vector_cosine_ops) 
WITH (lists = 100);
```

****:
-  **lists=100**: 20K   ( sqrt(N) )
-  ** **:    (85.91ms)
-  **HNSW **: HNSW     2-3

#### lists  

|   |  lists |  |  |
|-------------|-----------|------|------|
| < 10K | 50 | - | - |
| 10K - 100K | 100-300 | **100** |  |
| 100K - 1M | 500-1000 | - | - |
| > 1M | 2000+ | - | - |

****:
-  20K : lists=100 
- 100K   : lists=300-500 
- HNSW    ( >  )

#### GIN  (JSONB, )

****:
```sql
CREATE INDEX idx_documents_metadata 
ON documents USING GIN(metadata);

CREATE INDEX idx_documents_category 
ON documents USING GIN(category_path);
```

****:
-  **JSONB  **: 26.75ms (100 )
-  **  **: category_path  
-  ** **: 7.4 MB (metadata), 880 KB (category)

---

### 3.3  

####   (search_similar_chunks)

****:
-     (doc_type, chunk_type, source_org)
-     
-  JOIN   

** **:
```sql
-- 
WHERE c.drop = FALSE
    AND c.embedding IS NOT NULL
    AND (doc_type_filter IS NULL OR d.doc_type = doc_type_filter)
    
-- :    (PostgreSQL 12+)
/*+ IndexScan(c idx_chunks_embedding_active) */
```

####   

****:
-  window_size   
-  is_target    
-    (12.80ms)

---

## 4.   

### 4.1  ( )

|  |  |  |  |
|------|------|------|------|
|   | 85.91ms | < 500ms |  17% |
|   | 106.64ms | < 500ms |  21% |
|    | 12.80ms | < 100ms |  13% |
| JSONB  | 26.75ms | < 200ms |  13% |
|  |   |  < 20% |  |

****:    ,   

### 4.2  ( )

|  |  |   |   |
|------|------|-----------|-----------|
|   | 20K | 100K | lists  (100 → 300) |
|   | 10 | 50-100 | Read Replica |
| DB  | 350 MB | 10 GB |  (doc_type) |

### 4.3  ( )

-  **Foreign Key **:   
-  **Unique **: (doc_id, chunk_index)  
-  **CHECK **: chunk_index < chunk_total 
-  ****: updated_at  

### 4.4  ( )

-  ** **: documents, chunks, chunk_relations
-  ****:  / 
-  ** **: v_chunks_with_documents, v_data_statistics
-  ** **: search_similar_chunks, get_chunk_with_context

---

## 5.  

### 5.1  ( )

#### 1. HNSW   

****:
-   2-5 
- Recall  

****:
-   2-3  (182 MB → 400-500 MB)
-    

****:     

#### 2.   

```sql
CREATE INDEX idx_chunks_type_embedding 
ON chunks(chunk_type) 
INCLUDE (embedding) 
WHERE drop = FALSE;
```

****: chunk_type  +    10-20% 

### 5.2  ( )

#### 3.  

** 100K   **:
```sql
-- doc_type 
CREATE TABLE chunks_law PARTITION OF chunks
FOR VALUES IN ('law');

CREATE TABLE chunks_mediation PARTITION OF chunks
FOR VALUES IN ('mediation_case');
```

****:   20-30% ,  

#### 4.   

```sql
CREATE MATERIALIZED VIEW mv_popular_chunks AS
SELECT 
    c.chunk_id,
    c.content,
    d.doc_type,
    c.embedding
FROM chunks c
JOIN documents d ON c.doc_id = d.doc_id
WHERE c.drop = FALSE
    AND d.doc_type IN ('law', 'criteria_resolution')
WITH DATA;

CREATE INDEX idx_mv_popular_embedding 
ON mv_popular_chunks USING ivfflat(embedding vector_cosine_ops);
```

****: /  50% 

### 5.3  ( )

#### 5. Read Replica 

**100+   **:
- Primary: Write ( /)
- Replica 1-2: Read ( )

#### 6.  DB   

****:
- Milvus, Weaviate, Qdrant 
- 10M+    

---

## 6. 

  Vector DB  **     **.    ,    :

### 
-  **  ** (85.91ms,  17%)
-  ** ** (100% )
-  ** ** (  )
-  ** JSONB ** (26.75ms)
-  **  ** (, )

###  
-  ** **: 50-100
-  ** **: 100K   
-  ** **:  100ms 

###   
   **   **,        .

---

****: Multi-Agent System Product Manager  
** **: 2026-01-07  
** **:
- [`schema_v2_final.sql`](../../backend/database/schema_v2_final.sql)
-  : `/tmp/vector_db_test_results.json`
-  : [`test_vector_db_schema.py`](../../tests/unit/test_vector_db_schema.py)
