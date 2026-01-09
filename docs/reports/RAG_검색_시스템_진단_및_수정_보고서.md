# RAG      

##   

** **: 2026-01-07  
** **: RAG    ,  ,   

##   

### 1. SQL  Parameter  (Critical)

****:
```
IndexError: tuple index out of range
```

** **:
- `criteria_retriever.py`: line 158, 235
- `case_retriever.py`: `_vector_search()`
- `law_retriever.py`: SQL  

** **:
PostgreSQL JSONB `?`  psycopg2 placeholder(`%s`)  

****:
```python
#  
sql = "... d.metadata->'aliases' ? %s ..."
params = (item_name,)  #  ?  placeholder  2 
```

** **:
1. `?`  `??` escape
2.  `jsonb_exists()`  
3. SQL   `%`  `%%` escape (LIKE )

### 2.    (Critical)

****:
-     0 
- metadata   

** **:
- ** JSONL**: `law_name`, `article_no`, `path`   
- **DB (documents.metadata)**: `law_id` 

** **:
```json
//  JSONL (Civil_Law_chunks.jsonl)
{
    "law_name": "",
    "article_no": "750",
    "path": " 750",
    "law_id": "001706"
}

// DB documents.metadata
{
    "law_id": "001706"  // !
}
```

** **:
- : chunk_id  content   
- :      

### 3. Import  (Minor)

****:
```
NameError: name 're' is not defined
```

** **:
- `law_retriever.py`: line 188

** **:
```python
import re  # 
```

##    

### 1. criteria_retriever.py

####  1: JSONB `?`  
```python
# Before
d.metadata->'aliases' ? %s

# After
jsonb_exists(d.metadata->'aliases', %s)
```

####  2: LIKE  escape
```python
# Before
d.doc_type LIKE 'criteria%'

# After
d.doc_type LIKE 'criteria%%'  # SQL   %% 
```

### 2. case_retriever.py

#### : LIKE  escape
```python
# Before
d.doc_type LIKE '%case%'

# After
d.doc_type LIKE '%%%%case%%%%'  # 4 % = SQL 2 %
```

### 3. law_retriever.py

####  1: Import 
```python
import re
```

####  2:    (metadata → content )
```python
# Before (metadata )
sql += " AND d.metadata->>'law_name' ILIKE %s"
sql += " AND d.metadata->>'article_no' = %s"

# After (content + chunk_id )
if law_name:
    sql += " AND (d.title ILIKE %s OR c.content ILIKE %s)"
    params.append(f'%{law_name}%')
    params.append(f'%{law_name}%')

if article_no:
    # chunk_id : statute:001706:001706|A750
    article_num = article_no.replace('', '').replace('', '').strip()
    sql += """ AND (
        c.chunk_id ILIKE %s 
        OR c.content ILIKE %s
        OR c.content ILIKE %s
    )"""
    params.append(f'%|A{article_num}%')   # chunk_id 
    params.append(f'%{article_no}%')       # 750
    params.append(f'%{article_num}%')    # 750
```

####  3:   
```python
# Before
chunk_id, doc_id, content, law_name_db, article_no_db, path, metadata = row

# After
chunk_id, doc_id, content, law_name_db, chunk_type, metadata = row

# content   
article_match = re.search(r'\s*\d+\s*', content)
article_no_db = article_match.group(0) if article_match else None

# path 
path = f"{law_name_db} {article_no_db}" if article_no_db else law_name_db
```

### 4. check_db_status.py ( )

DB      :
- documents/chunks  
-    
-  750  
-   

### 5. check_law_metadata.py ( )

    :
- documents.metadata 
- chunks  
- chunk_id  
-  JSONL 

##   

###  
- **  **: 5
- **   **: 3/5 (60.0%) 
- **  **: 0.93
- ** Top **: 0.3777

###   (3/5)

1.  ** 750 ?**
   - : law → : law (1)
   - Top Score: 0.5600
   -  : 4.00s

2.  **     ?**
   - : criteria → : criteria (5)
   - Top Score: 0.3316
   -  : 0.16s

3.  **       ?**
   - : criteria → : criteria (5)
   - Top Score: 0.3302
   -  : 0.13s

###   (2/5)

1.  **    .**
   - : case → : criteria (3)
   - : query_type='practical'  case  

2.  **   ?**
   - : law → : criteria (3)
   - : DB    ( )

##  DB   

### Documents 
| Doc Type | Count | With Keywords | With Search Vector |
|----------|-------|---------------|-------------------|
| counsel_case | 11,342 | 11,342 | 0 |
| criteria_resolution | 1 | 1 | 0 |
| law | 1 | 1 | 0 |
| mediation_case | 632 | 555 | 0 |
| **** | **11,976** | **11,897** | **0** |

### Chunks 
| Doc Type | Chunks | With Embedding | With Importance | Dropped |
|----------|--------|----------------|-----------------|---------|
| counsel_case | 13,524 | 13,524 | 13,524 | 0 |
| criteria_resolution | 139 | 139 | 139 | 0 |
| law | 1,059 | 1,059 | 1,059 | 0 |
| mediation_case | 5,547 | 5,537 | 5,547 | 0 |
| **** | **20,269** | **20,259** | **20,269** | **0** |

###  
1.   :  1, 1,059  ()
2.   750   
3.  search_vector (FTS)   NULL
4.    

##   

### 1.    (10-20)

#### A. hybrid_retriever  
```python
# query_type='practical'  case 
if query_info.query_type in [QueryType.PRACTICAL, QueryType.GENERAL]:
    case_results = self.case_retriever.search(...)
    all_results.extend(case_results)
```

#### B. case_retriever   
```python
#   
min_similarity = 0.3  # 0.5 → 0.3

#   
if any(kw in query for kw in ['', '', '', '']):
    #   case  
```

### 2.   (1-2)

#### A.  
-      :
  -     
  - 
  -    

#### B. Full-Text Search  
```sql
-- search_vector 
UPDATE documents 
SET search_vector = to_tsvector('korean', title || ' ' || COALESCE(array_to_string(keywords, ' '), ''));
```

### 3.   (2-4)

#### A.    
- documents.metadata  JSONL   
- law_name, article_no, path   

#### B.   
- BM25 + Vector Hybrid
- Query Expansion
- Learning to Rank

##   

###  
1.  SQL parameter   
2.      
3.     
4.  60%     ( !)
5.     1 

###  
1.  `FIX_PLAN.md`:  
2.  `FINAL_FIX_PLAN.md`:   
3.  `TEST_RESULTS_SUMMARY.md`:   
4.  `DIAGNOSIS_AND_FIX_REPORT.md`:  
5.  `check_db_status.py`: DB   
6.  `check_law_metadata.py`:    

###  
1.  `criteria_retriever.py`: SQL  
2.  `case_retriever.py`: SQL  
3.  `law_retriever.py`: Import     
4.  `extract_case_metadata.py`: SQL  
5.  `extract_law_metadata.py`: SQL  
6.  `extract_criteria_metadata.py`: SQL  

##  

**   ,   (60%) .**

 :
- SQL   
-    
-    
-    (1 )

  80%     :
1. Case  
2.   
3.   
4. Full-Text Search 
5.   

##    

###  1 ()
1. `hybrid_retriever.py` practical query  case  
2. `case_retriever.py`   

###  2 (1 )
1.      
2. Full-Text Search    

###  3 (1 )
1.    
2.   
3.   

---

****: AI Assistant  
** **:    
