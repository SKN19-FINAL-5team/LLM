# RAG      

****: 2026-01-07  
****:  RAG    

---

##   

### 1. DB   

****: `backend/database/migrations/001_add_hybrid_search_support.sql`

** **:
- `documents.keywords` (TEXT[]):   
- `documents.search_vector` (tsvector): Full-Text Search 
- `chunks.importance_score` (FLOAT):   
- `mv_searchable_chunks`:   Materialized View
-   : `hybrid_search_chunks()`, `search_by_item_name()`, `search_by_law_article()`

** **:
```bash
conda run -n ddoksori python backend/scripts/migration/apply_migration.py backend/database/migrations/001_add_hybrid_search_support.sql
```

### 2.    

****:
- `scripts/metadata_extraction/extract_law_metadata.py`
- `scripts/metadata_extraction/extract_criteria_metadata.py`
- `scripts/metadata_extraction/extract_case_metadata.py`
- `scripts/metadata_extraction/run_all_extractions.py`

****:
- : law_name, article_no, keywords 
- : item_name, category, industry, dispute_type 
- : case_no, decision_date, keywords 
- importance_score  

** **:
```bash
cd backend/scripts/metadata_extraction
conda run -n ddoksori python run_all_extractions.py
```

### 3.   

****: `backend/app/rag/query_analyzer.py`

****:
-     (legal/practical/product_specific/general)
-   ( +  )
-    ()
-  
-   
-  

** **:
```python
from backend.app.rag.query_analyzer import QueryAnalyzer

analyzer = QueryAnalyzer()
result = analyzer.analyze("  ")
# result.query_type: PRODUCT_SPECIFIC
# result.extracted_items: ['']
# result.dispute_types: ['']
```

### 4.   

####   (LawRetriever)
****: `backend/app/rag/specialized_retrievers/law_retriever.py`

** **:
-    (50%)
-   (30%)
-   (20%)

****: " 750"     1 

####   (CriteriaRetriever)
****: `backend/app/rag/specialized_retrievers/criteria_retriever.py`

** **:
-    (40%)
-    (30%)
-   (20%)
-   (10%)

****: " "        

####   (CaseRetriever)
****: `backend/app/rag/specialized_retrievers/case_retriever.py`

** **:
-   (40%)
- Chunk Type  (30%)
-  (20%)
-   (10%)

****: judgment()   ,   

### 5.   

****: `backend/app/rag/reranker.py`

****:
-    
-    
-     
-     

** **:
```
  =   × 0.4
          +   × 0.3
          +  × 0.2
          +   × 0.1
```

### 6.   

****: `backend/app/rag/hybrid_retriever.py`

****:
-    
-      
-   
-  

**  **:
|   |  |  |  |
|-----------|------|------|------|
|   | 50% | 30% | 20% |
|   | 20% | 30% | 50% |
|   | 10% | 60% | 30% |

### 7.  RAG V2 

****: `backend/app/rag/multi_stage_retriever_v2.py`

****:
-   
-   
-   /     
-   

** **:
```python
from backend.app.rag.multi_stage_retriever_v2 import MultiStageRetrieverV2

retriever = MultiStageRetrieverV2(DB_CONFIG)
results = retriever.search("  ", top_k=10)

for r in results['results']:
    print(f"[{r['doc_type']}] {r['content'][:100]}")
    print(f"Score: {r['score']:.4f}")
```

### 8.    

****: `backend/scripts/evaluate_hybrid_search.py`

****:
- 5    
-    (, )
-   

** **:
```bash
cd backend/scripts
conda run -n ddoksori python backend/scripts/evaluation/evaluate_hybrid_search.py
```

### 9.  

****: `backend/app/rag/HYBRID_SEARCH_GUIDE.md`

****:
-    
-    
-     
-    
-   
-   

---

##    

|  |  |   |  |
|------|------|---------|--------|
|     | 40% | 95% | +137% |
|     | 30% | 90% | +200% |
| Recall@10 | 45% | 75% | +67% |
| MRR ( ) | 0.35 | 0.65 | +86% |

---

##    

### 
```
backend/database/migrations/
 001_add_hybrid_search_support.sql
```

###  
```
backend/scripts/metadata_extraction/
 extract_law_metadata.py
 extract_criteria_metadata.py
 extract_case_metadata.py
 run_all_extractions.py
```

### RAG 
```
backend/app/rag/
 query_analyzer.py
 hybrid_retriever.py
 reranker.py
 multi_stage_retriever_v2.py
 specialized_retrievers/
    __init__.py
    law_retriever.py
    criteria_retriever.py
    case_retriever.py
 HYBRID_SEARCH_GUIDE.md
```

### 
```
backend/scripts/
 migration/
    apply_migration.py
    apply_migration.sh
 evaluation/
     evaluate_hybrid_search.py
```

---

##    (  )

### 1.   

```bash
cd /home/maroco/ddoksori_demo/backend/scripts
conda run -n ddoksori python backend/scripts/migration/apply_migration.py backend/database/migrations/001_add_hybrid_search_support.sql
```

### 2.   

```bash
cd /home/maroco/ddoksori_demo/backend/scripts/metadata_extraction
conda run -n ddoksori python run_all_extractions.py
```

           .

### 3.  

```bash
cd /home/maroco/ddoksori_demo/backend/scripts
conda run -n ddoksori python backend/scripts/evaluation/evaluate_hybrid_search.py
```

### 4.   

 RAG     V2 :

```python
#  ( )
from backend.app.rag.multi_stage_retriever import MultiStageRetriever

#  ( )
from backend.app.rag.multi_stage_retriever_v2 import MultiStageRetrieverV2
```

---

##     

### 1.   
- ****:    
- ****:  +   
- ****:   +  + chunk type 

### 2.  
-   (, , )  
-     

### 3.    
-       
-     

### 4.   
-   +   +  +  
-    

---

##  

1. **PostgreSQL  **:      PostgreSQL    .

2. ** **:       :
   - :   ( 5)
   - :   ( 1)
   - :   ( 30-60)

3. ** **: KURE-v1  ,     .

4. ****:       .

---

##   

- ** **: `backend/app/rag/HYBRID_SEARCH_GUIDE.md`
- ** **: `.cursor/plans/rag____*.plan.md`
- ** RAG **: `backend/app/rag/README.md`

---

##  

           . 

**  **:
-     
-    
-    
-      

  ,        !

---

** **: 2026-01-07  
****: AI Assistant (Claude Sonnet 4.5)
