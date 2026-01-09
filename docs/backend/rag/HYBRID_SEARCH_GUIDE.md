#  RAG   

##  

1. [ ](#-)
2. [](#)
3. [ ](#-)
4. [ ](#-)
5. [  ](#--)
6. [ ](#-)
7. [ ](#-)

---

##  

###  

       :

|  |  |   |
|------|------|---------|
|   |    |      |
|   |  | , ,    |
|   |  |   ( +  +  + ) |
|   |  |       |

###   

- **  **: 40% → 95% 
- **  **: 30% → 90% 
- ** Recall@10**: 45% → 75%
- **MRR ( )**: 0.35 → 0.65

---

## 

###  

```
 
    ↓
QueryAnalyzer ( )
        (legal/practical/product_specific)
      
      
      
    ↓
HybridRetriever ( )
     LawRetriever ( )
           (50%)
          (30%)
          (20%)
    
     CriteriaRetriever ( )
          (40%)
           (30%)
          (20%)
          (10%)
    
     CaseRetriever ( )
           (40%)
         Chunk Type  (30%)
          (20%)
           (10%)
    ↓
Reranker ()
       
      
       (/)
       
    ↓
  
```

###  

```
[Query] "  "
    ↓
[QueryAnalyzer]
    - query_type: PRODUCT_SPECIFIC
    - extracted_items: [""]
    - dispute_types: [""]
    ↓
[HybridRetriever] (: criteria 60%, case 30%, law 10%)
    ↓
[CriteriaRetriever]
    -  ""   →  
    -  ""  →  
    ↓
[Reranker]
    -  :  +   →  
    - : resolution_row () → 2.0
    ↓
[Results] "  " 1 
```

---

##  

### 1. QueryAnalyzer
****: `backend/app/rag/query_analyzer.py`

****:
-    
- , ,  
-   

****:
```python
from backend.app.rag.query_analyzer import QueryAnalyzer

analyzer = QueryAnalyzer()
result = analyzer.analyze(" 750 ")

print(result.query_type)          # QueryType.LEGAL
print(result.extracted_articles)  # [{'law_name': None, 'article_no': '750'}]
print(result.keywords)            # ['', '750', '', ...]
```

### 2.  

#### LawRetriever ()
****: `backend/app/rag/specialized_retrievers/law_retriever.py`

** **:
-     (law_name + article_no)
-   
-    

#### CriteriaRetriever ()
****: `backend/app/rag/specialized_retrievers/criteria_retriever.py`

** **:
-    (item_name, aliases)
-    (category > industry > item_group)
-  

#### CaseRetriever ()
****: `backend/app/rag/specialized_retrievers/case_retriever.py`

** **:
-   
- Chunk Type  (judgment: 1.5, answer: 1.4, ...)
-   (  )
-   (    )

### 3. Reranker
****: `backend/app/rag/reranker.py`

****:
-    
-    
-     

### 4. HybridRetriever
****: `backend/app/rag/hybrid_retriever.py`

****:
-    
-     
-   

### 5. MultiStageRetrieverV2
****: `backend/app/rag/multi_stage_retriever_v2.py`

****:
-   
-   
-  

---

##  

###  

```python
from backend.app.rag.multi_stage_retriever_v2 import MultiStageRetrieverV2

# DB 
DB_CONFIG = {
    'dbname': 'ddoksori',
    'user': 'maroco',
    'password': '',
    'host': 'localhost',
    'port': '5432'
}

#  
retriever = MultiStageRetrieverV2(DB_CONFIG)

#  
results = retriever.search(
    query="   ",
    top_k=10
)

#  
for r in results['results']:
    print(f"[{r['doc_type']}] {r['content']}")
    print(f"Score: {r['score']}")
```

###   ( )

```python
#   (  )
results = retriever.search_multi_stage(
    query=" ",
    law_top_k=5,
    criteria_top_k=3,
    case_top_k=5
)

# Stage 1:  + 
print(":", len(results['stage1']['law']))
print(":", len(results['stage1']['criteria']))

# Stage 2: 
print(":", len(results['stage2']['cases']))

#  
print(":", len(results['unified']))
```

###   

```python
from backend.app.rag.hybrid_retriever import HybridRetriever

retriever = HybridRetriever(DB_CONFIG)

#    
details = retriever.search_with_details(
    query="  ",
    top_k=5
)

#   
print("Query Type:", details['query_analysis']['query_type'])
print("Extracted Items:", details['query_analysis']['extracted_items'])
print("Dispute Types:", details['query_analysis']['dispute_types'])

#    
for r in details['results']:
    print(f"\nChunk: {r['chunk_id']}")
    print(f"  Original Score: {r['scores']['original']}")
    print(f"  Metadata Match: {r['scores']['metadata_match']}")
    print(f"  Importance: {r['scores']['importance']}")
    print(f"  Final Score: {r['scores']['final']}")
```

---

##   

### 1.  

####     
****: `backend/app/rag/hybrid_retriever.py`

```python
QUERY_TYPE_WEIGHTS = {
    QueryType.LEGAL: {
        'law': 0.5,      #    50%
        'criteria': 0.3,
        'case': 0.2
    },
    QueryType.PRODUCT_SPECIFIC: {
        'criteria': 0.6,  #    60%
        'case': 0.3,
        'law': 0.1
    }
}
```

####    

** (LawRetriever)**:
```python
EXACT_MATCH_WEIGHT = 0.5    #   
KEYWORD_WEIGHT = 0.3        #  
VECTOR_WEIGHT = 0.2         #  
```

** (CriteriaRetriever)**:
```python
ITEM_MATCH_WEIGHT = 0.4      #  
HIERARCHY_WEIGHT = 0.3       #  
DISPUTE_WEIGHT = 0.2         # 
VECTOR_WEIGHT = 0.1          #  
```

** (CaseRetriever)**:
```python
VECTOR_WEIGHT = 0.4          #  
CHUNK_TYPE_WEIGHT = 0.3      # chunk type 
RECENCY_WEIGHT = 0.2         # 
AGENCY_WEIGHT = 0.1          #  
```

####  
****: `backend/app/rag/reranker.py`

```python
ORIGINAL_SCORE_WEIGHT = 0.4      #   
METADATA_MATCH_WEIGHT = 0.3      #  
IMPORTANCE_WEIGHT = 0.2          # 
CONTEXTUAL_WEIGHT = 0.1          #  
```

### 2. Chunk Type 

** **:
```python
CHUNK_TYPE_IMPORTANCE = {
    'judgment': 1.5,        #  -  
    'decision': 1.5,        # 
    'answer': 1.4,          # 
    'qa_combined': 1.3,     # Q&A
    'parties_claim': 1.1,   #  
    'case_overview': 1.0    #  
}
```

** **:
```python
# chunks.importance_score
resolution_row: 2.0        #  - 
item_chunk: 1.5            # 
warranty/lifespan: 1.3     # /
```

---

##  

### 1.  

####  
```bash
cd backend/scripts
conda run -n ddoksori python backend/scripts/migration/apply_migration.py backend/database/migrations/001_add_hybrid_search_support.sql
```

####  
```bash
cd backend/scripts/metadata_extraction
conda run -n ddoksori python run_all_extractions.py
```

#### Materialized View 
```sql
--   (  )
SELECT refresh_searchable_chunks();
```

### 2.  
```sql
--   
SELECT schemaname, tablename, indexname
FROM pg_indexes
WHERE tablename IN ('documents', 'chunks')
ORDER BY tablename, indexname;
```

### 3.   
```sql
-- EXPLAIN ANALYZE   
EXPLAIN ANALYZE
SELECT * FROM hybrid_search_chunks(
    query_embedding := ...,
    query_keywords := ARRAY['', ''],
    top_k := 10
);
```

---

##  

###   

****:
1.  
2.   
3.  

****:
```bash
# 1.  
SELECT COUNT(*) FROM documents;
SELECT COUNT(*) FROM chunks WHERE embedding IS NOT NULL;

# 2.  
SELECT COUNT(*) FROM documents WHERE keywords IS NOT NULL;

# 3.  
conda run -n ddoksori python metadata_extraction/run_all_extractions.py
```

###   

****:
1.  
2. Materialized View 
3.    

****:
```sql
-- 1.  
REINDEX INDEX idx_chunks_embedding;

-- 2. Materialized View 
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_searchable_chunks;

-- 3.  
ANALYZE documents;
ANALYZE chunks;
```

###     

****:
1.  (law_name, article_no) 
2.   

****:
```bash
#   
conda run -n ddoksori python metadata_extraction/extract_law_metadata.py
```

 :
```python
# law_retriever.py
EXACT_MATCH_WEIGHT = 0.6  #  0.5 
KEYWORD_WEIGHT = 0.25
VECTOR_WEIGHT = 0.15
```

###    

****:
1.   
2. (aliases) 

****:
```bash
#   
conda run -n ddoksori python metadata_extraction/extract_criteria_metadata.py
```

---

##  

###  
- : `backend/database/migrations/001_add_hybrid_search_support.sql`
-  : `backend/scripts/metadata_extraction/`
-  : `backend/scripts/evaluate_hybrid_search.py`

###  
-  : `.cursor/plans/rag____*.plan.md`
-  : `backend/app/rag/README.md`

---

****: 2026-01-07  
****: 1.0.0  
****: AI Assistant
