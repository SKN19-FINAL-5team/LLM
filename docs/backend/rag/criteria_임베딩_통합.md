# Criteria    

## 
1. [](#)
2. [ ?](#-)
3. [ ](#-)
4. [  ](#--)
5. [ ](#-)
6. [ ](#-)
7. [FAQ](#faq)

---

## 

### 
Criteria (   ) RAG    .

### Criteria  

|  |   |   |
|-------|---------|-----------|
| content_guideline_chunks.jsonl | 8 |   |
| ecommerce_guideline_chunks.jsonl | 18 |   |
| table4_lifespan_chunks.jsonl | 63 |   |
| table1_item_chunks.jsonl | 592 |  592 |
| table3_warranty_chunks.jsonl | 84 | / |
| **** | **765** | ** 5 ** |

###    

-  --    
-  "", ""  592   
-  ,     
-  RAG    

---

##  ?

### 

** **:      ,       

###  ?

#### 
1. ****:     →   
2. ** **:       
3. ** **:     
4. ** **:     

#### 
1. ~~   ~~ → **!** (   )
2.    ( )

### :   

**    **:
```sql
INSERT INTO chunks (...)
VALUES %s
ON CONFLICT (chunk_id) DO NOTHING  -- ←    
```

****:
- 1 Guideline 26 
- 2 Guideline + Table4  
  - Guideline 26: ** DB  →  **
  - Table4 63:   → 

****:   **   **!

---

##  

### 1.  

```bash
#   
cd /home/maroco/ddoksori_demo

#   
ls backend/data/criteria/
# : content_guideline_chunks.jsonl  ecommerce_guideline_chunks.jsonl
#       table1_item_chunks.jsonl  table3_warranty_chunks.jsonl
#       table4_lifespan_chunks.jsonl
```

### 2.   

```bash
# .env  
cat backend/.env | grep DB_

#  :
# DB_HOST=localhost
# DB_PORT=5432
# DB_NAME=ddoksori
# DB_USER=postgres
# DB_PASSWORD=...
```

### 3.  API   

```bash
# API   
curl http://localhost:8001/

#  :
# {"status":"healthy","model":"nlpai-lab/KURE-v1","dimension":1024}
```

### 4. ()   

```bash
# PostgreSQL 
pg_dump -U postgres -d ddoksori -t chunks -t documents \
  > backup_before_criteria_$(date +%Y%m%d_%H%M%S).sql

#  
ls -lh backup_before_criteria_*.sql
```

---

##   

###   

```
 → 1  →  →   →  
```

---

###  A:   (  )

#### Step 1:   (Guideline 26)

```bash
# 1-1.   
export CRITERIA_STAGE=1

# 1-2.  
python backend/scripts/embed_pipeline_v2.py
```

** **:
```
[4/6]    ... (stage=1)
     : 2
    : content_guideline_chunks.jsonl
    : ecommerce_guideline_chunks.jsonl
    :  2,  26

[6/6]     : 26
100%|| 1/1 [00:02<00:00,  2.34s/it]
     
```

#### Step 2: 

```bash
# 2-1.   
python backend/scripts/check_embedding_status.py
```

** **:
```
===    ===
  : 26
 : 26 (100.0%)
 : 0

=== chunk_type  ===
guideline_section: 26
```

**SQL  **:
```sql
-- psql 
psql -U postgres -d ddoksori

-- guideline  
SELECT
    doc_type,
    chunk_type,
    COUNT(*) as count,
    AVG(content_length) as avg_length
FROM chunks
WHERE doc_type = 'guideline'
GROUP BY doc_type, chunk_type;

--  :
--  doc_type  |    chunk_type     | count | avg_length
-- -----------+-------------------+-------+------------
--  guideline | guideline_section |    26 |     1150.5
```

** **:
```bash
#   
python backend/scripts/test_similarity_search.py
```

```python
# test_similarity_search.py   
query = "  "
# → guideline_section    
```

#### Step 3:   ( 739)

**1   **:

```bash
# 3-1.   
export CRITERIA_STAGE=0  #  unset CRITERIA_STAGE

# 3-2.  
python backend/scripts/embed_pipeline_v2.py
```

** **:
```
[4/6]    ... (stage=0)
     : 5
    : content_guideline_chunks.jsonl
    : ecommerce_guideline_chunks.jsonl
    : table4_lifespan_chunks.jsonl
    : table1_item_chunks.jsonl
    : table3_warranty_chunks.jsonl
    :  8,  765

[6/6]     : 765
100%|| 24/24 [01:23<00:00,  3.48s/it]
     
```

****:   26  , ** 739  **!

#### Step 4:  

```bash
# 4-1.   
python backend/scripts/check_embedding_status.py
```

** **:
```
===    ===
  : 765
 : 765 (100.0%)
 : 0

=== chunk_type  ===
guideline_section: 26
lifespan_item: 63
item_basic: 592
warranty_parent: 20
warranty_detail: 64
```

**SQL **:
```sql
-- chunk_type  
SELECT
    chunk_type,
    COUNT(*) as count,
    MIN(content_length) as min_len,
    AVG(content_length) as avg_len,
    MAX(content_length) as max_len
FROM chunks
WHERE doc_type = 'guideline'
GROUP BY chunk_type
ORDER BY count DESC;

--  :
--     chunk_type     | count | min_len | avg_len | max_len
-- -------------------+-------+---------+---------+---------
--  item_basic        |   592 |      45 |    65.3 |     120
--  warranty_detail   |    64 |     180 |   352.1 |     580
--  lifespan_item     |    63 |      85 |   118.7 |     165
--  guideline_section |    26 |     820 |  1150.5 |    1480
--  warranty_parent   |    20 |      60 |    78.4 |     110
```

**  **:
```python
# test_similarity_search.py

test_queries = [
    {
        "query": " ",
        "expected_types": ["item_basic", "warranty_parent", "warranty_detail"]
    },
    {
        "query": "  ",
        "expected_types": ["guideline_section"]
    },
    {
        "query": "  ",
        "expected_types": ["item_basic"]
    }
]

for test in test_queries:
    results = retrieve_similar_chunks(test["query"], top_k=5)
    print(f"\n: {test['query']}")
    for r in results:
        print(f"  - [{r['chunk_type']}] {r['content'][:50]}... (: {r['similarity']:.3f})")
```

---

###  B:     ()

**    **:

```bash
#  
export CRITERIA_STAGE=0

# 
python backend/scripts/embed_pipeline_v2.py

# 
python backend/scripts/check_embedding_status.py
```

****:  
****:     

---

###  C:    (/)

**   **:

```bash
# 1: Guideline (26)
export CRITERIA_STAGE=1
python backend/scripts/embed_pipeline_v2.py
python backend/scripts/check_embedding_status.py

# 2: + Table4 (26 + 63 = 89)
export CRITERIA_STAGE=2
python backend/scripts/embed_pipeline_v2.py
python backend/scripts/check_embedding_status.py

# 3: + Table1 (89 + 592 = 681)
export CRITERIA_STAGE=3
python backend/scripts/embed_pipeline_v2.py
python backend/scripts/check_embedding_status.py

# 4: + Table3 (681 + 84 = 765)
export CRITERIA_STAGE=4
python backend/scripts/embed_pipeline_v2.py
python backend/scripts/check_embedding_status.py
```

****:       
****:    ( )

---

##  

### 1.   

#### check_embedding_status.py

```bash
python backend/scripts/check_embedding_status.py
```

** **:
-    
-    (100% )
-  chunk_type 
-     (1024)

#### test_similarity_search.py

```bash
python backend/scripts/test_similarity_search.py
```

** **:
-     
-    (0.0~1.0)
-   chunk_type 

### 2. SQL  

```sql
-- 1.  
SELECT
    doc_type,
    COUNT(*) as total_chunks,
    COUNT(embedding) as embedded_chunks,
    ROUND(COUNT(embedding)::NUMERIC / COUNT(*) * 100, 2) as completion_rate
FROM chunks
GROUP BY doc_type;

--  :
--   doc_type    | total_chunks | embedded_chunks | completion_rate
-- --------------+--------------+-----------------+-----------------
--  law          |          300 |             300 |          100.00
--  counsel_case |          400 |             400 |          100.00
--  mediation_case |        500 |             500 |          100.00
--  guideline    |          765 |             765 |          100.00


-- 2. guideline chunk_type 
SELECT
    chunk_type,
    COUNT(*) as count,
    ROUND(AVG(content_length), 1) as avg_length
FROM chunks
WHERE doc_type = 'guideline'
GROUP BY chunk_type
ORDER BY count DESC;

--  :
--     chunk_type     | count | avg_length
-- -------------------+-------+------------
--  item_basic        |   592 |       65.3
--  warranty_detail   |    64 |      352.1
--  lifespan_item     |    63 |      118.7
--  guideline_section |    26 |     1150.5
--  warranty_parent   |    20 |       78.4


-- 3. source_org 
SELECT
    source_org,
    COUNT(*) as doc_count
FROM documents
WHERE doc_type = 'guideline'
GROUP BY source_org;

--  :
--  source_org | doc_count
-- ------------+-----------
--  MCST       |         1
--  FTC        |         7


-- 4. parent-child   (table3)
SELECT
    c1.chunk_id as parent_chunk,
    c1.content as parent_content,
    c2.chunk_id as child_chunk,
    c2.content as child_content
FROM chunks c1
JOIN chunks c2
  ON c2.metadata->>'parent_stable_id' = c1.metadata->>'stable_id'
WHERE c1.chunk_type = 'warranty_parent'
LIMIT 3;


-- 5. aliases  
SELECT
    content,
    metadata->>'item_name' as item,
    metadata->>'aliases' as aliases
FROM chunks
WHERE chunk_type = 'item_basic'
  AND metadata->>'aliases' IS NOT NULL
LIMIT 5;

--  :
--           content           |      item       |            aliases
-- ----------------------------+-----------------+-------------------------------
--  [] ...           |           | [" ",""]
--  [] ...           |           | ["",""]
```

### 3.   

```python
# backend/scripts/test_criteria_search.py (  )

from app.rag.retriever import retrieve_similar_chunks

test_cases = [
    {
        "name": " ",
        "query": " ",
        "expected_types": ["item_basic", "warranty_parent", "warranty_detail"],
        "min_similarity": 0.7
    },
    {
        "name": " ",
        "query": "  ",
        "expected_types": ["guideline_section"],
        "min_similarity": 0.65
    },
    {
        "name": " ",
        "query": " ",
        "expected_types": ["lifespan_item"],
        "min_similarity": 0.7
    }
]

for test in test_cases:
    print(f"\n{'='*60}")
    print(f": {test['name']}")
    print(f": {test['query']}")
    print(f"{'='*60}")

    results = retrieve_similar_chunks(test["query"], top_k=5)

    for i, r in enumerate(results, 1):
        print(f"{i}. [{r['chunk_type']}] (: {r['similarity']:.3f})")
        print(f"   {r['content'][:100]}...")

    # 
    types_found = [r['chunk_type'] for r in results]
    assert any(t in test['expected_types'] for t in types_found), \
        f"  {test['expected_types']}    "

    assert all(r['similarity'] >= test['min_similarity'] for r in results), \
        f"   {test['min_similarity']}  "

    print(f"  ")

print(f"\n{'='*60}")
print("   !")
print(f"{'='*60}")
```

:
```bash
python backend/scripts/test_criteria_search.py
```

---

##  

### 1.  API  

****:
```
  API  : Connection refused
       (  )
```

****:  API  

****:
```bash
# API  
python backend/runpod_embed_server.py

#  Docker 
docker-compose up -d embed-server
```

### 2.    

****:
```
  criteria   : /path/to/criteria
```

****:    

****:
```bash
#   
pwd

# criteria  
ls backend/data/criteria/

#   
cd /home/maroco/ddoksori_demo
```

### 3.   

****:
```
ERROR: duplicate key value violates unique constraint "chunks_pkey"
DETAIL: Key (chunk_id)=(guideline:...) already exists.
```

****:     

****:
- ****: `ON CONFLICT ... DO NOTHING`    ( )
- ****:        

```sql
--  criteria  
DELETE FROM chunks WHERE doc_type = 'guideline';
DELETE FROM documents WHERE doc_type = 'guideline';
```

### 4.   100% 

****:
```
 : 750 / 765 (98.0%)
 : 15
```

****:
- API 
-  
-   content  

****:
```bash
#   (  )
python backend/scripts/embed_pipeline_v2.py

#    
psql -U postgres -d ddoksori -c \
  "SELECT chunk_id, content_length FROM chunks
   WHERE doc_type='guideline' AND embedding IS NULL;"
```

### 5.   

****:     0 

****:
-  
-   
-    

****:
```python
# 1.   
SELECT COUNT(*) FROM chunks
WHERE doc_type='guideline' AND embedding IS NOT NULL;

# 2.    
SELECT chunk_id, content,
       1 - (embedding <=> %s::vector) as similarity
FROM chunks
WHERE doc_type='guideline'
ORDER BY embedding <=> %s::vector
LIMIT 5;
```

### 6.  

**   **:

```sql
-- 1. criteria  
DELETE FROM chunks WHERE doc_type = 'guideline';

-- 2. criteria  
DELETE FROM documents WHERE doc_type = 'guideline';

-- 3. 
SELECT doc_type, COUNT(*) FROM chunks GROUP BY doc_type;
-- guideline  
```

** **:
```bash
#   
ls -lh backup_before_criteria_*.sql

# 
psql -U postgres -d ddoksori < backup_before_criteria_20260105_120000.sql
```

---

## FAQ

### Q1.      ?

**A**: !

- `ON CONFLICT (chunk_id) DO NOTHING`      .
- : 1(26) → 2(+63)  , 26  63  .

### Q2. CRITERIA_STAGE=0 4 ?

**A**: !

- `CRITERIA_STAGE=0`:   (stage 1+2+3+4)
- `CRITERIA_STAGE=4`:   (stage 1+2+3+4)

  5   .

### Q3.   ?

**A**: `CRITERIA_STAGE=0`   

```bash
export CRITERIA_STAGE=0
python backend/scripts/embed_pipeline_v2.py
```

,       .

### Q4.   ?

**A**: 2  ()

1. `CRITERIA_STAGE=1` ( )
2.   `CRITERIA_STAGE=0` ()

### Q5.    

**A**:   . :

- `CRITERIA_STAGE=1`: Guideline 
- `CRITERIA_STAGE=2`: Guideline + Table4
- `CRITERIA_STAGE=3`: Guideline + Table4 + Table1
- `CRITERIA_STAGE=4` or `0`: 

### Q6.    ?

**A**:    (GPU  )

- 1 (26): ~1
- 2 ( 63): ~2
- 3 ( 592): ~20
- 4 ( 84): ~3
- ** (765)**: ~25

### Q7.     ?

**A**:  .

-  :  
-  : 

### Q8. DB    ?

**A**:    .

-  : `ON CONFLICT ... DO NOTHING` 
-  :  

---

##  

###   

```bash
# Step 1: 
export CRITERIA_STAGE=1
python backend/scripts/embed_pipeline_v2.py
python backend/scripts/check_embedding_status.py

# Step 2:    
export CRITERIA_STAGE=0
python backend/scripts/embed_pipeline_v2.py
python backend/scripts/check_embedding_status.py

# Step 3:  
python backend/scripts/test_criteria_search.py
```

###  

```bash
#    (  )
export CRITERIA_STAGE=0
python backend/scripts/embed_pipeline_v2.py
```

###   

```bash
# 1.  
tail -f logs/embed_pipeline.log

# 2. DB  
python backend/scripts/check_embedding_status.py

# 3.  
psql -U postgres -d ddoksori -c \
  "DELETE FROM chunks WHERE doc_type='guideline';"

# 4. 
python backend/scripts/embed_pipeline_v2.py
```

---

##  

- [___.md](./___.md) -   
- [     .md](./%20%20%20%20%20.md) -  
- [RAG_SETUP_GUIDE.md](./RAG_SETUP_GUIDE.md) - RAG   

---

##  

- 2026-01-05:   (Criteria     )
