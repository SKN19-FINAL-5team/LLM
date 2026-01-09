# SPLADE    

****: 2026-01-08  
****: Multi-Agent System  
** **:        
****: v2.0  
****:     

---

## Executive Summary

  SPLADE (Sparse Lexical And Expansion)       . **RDB sparse vector   **     ,       .

###  
-  ** **: 10-20  (2-5 → 100-300ms)
-  ** **: 50-70% 
-  **  chunk **: 1000  → 
-  ****: Recall@5 +10-15%  

---

## 1.  

### 1.1  SPLADE   ( )

****:
- RDB sparse vector   
-   chunk    ()
- LIMIT 1000 
-  : 2-5

** **:
```python
#  :  
1.  → SPLADE  (query_vec)
2. DB  chunk  (LIMIT 1000)
3.  chunk  SPLADE  (doc_vec)
4. dot product  
5.   top_k 
```

### 1.2  SPLADE  

** **:
- RDB sparse vector   
-   
- JSONB/GIN   
-  : 100-300ms

** **:
```python
#  :   
1.  → SPLADE  (query_vec) - 
2. DB   sparse vector  ( )
3.  dot product 
4.   top_k 
```

---

## 2.  

### 2.1   

****: `backend/database/migrations/002_add_splade_sparse_vector.sql`

** **:
- `splade_sparse_vector` (JSONB): Sparse vector 
- `splade_model` (VARCHAR):   
- `splade_encoded` (BOOLEAN):   

****:
- GIN : JSONB  
-  :   +   

** **:
```json
{
  "1234": 2.5,
  "5678": 1.8,
  "9012": 0.9
}
```
- `{token_id: weight}` 
- 0     

### 2.2 SPLADE   

****: `backend/scripts/splade/encode_splade_vectors.py`

****:
-  chunk  SPLADE sparse vector 
-   (32)
-      
-  API    

****:
```bash
#  chunk 
conda run -n dsr python backend/scripts/splade/encode_splade_vectors.py

#  
conda run -n dsr python backend/scripts/splade/encode_splade_vectors.py --doc-type law

#  
conda run -n dsr python backend/scripts/splade/encode_splade_vectors.py --stats-only
```

### 2.3  SPLADE Retriever

****: `backend/scripts/splade/test_splade_optimized.py`

****: `OptimizedSPLADEDBRetriever`

** **:
- `search_law_splade_optimized()`:  
- `search_criteria_splade_optimized()`:  
- `search_hybrid()`:   (SPLADE + Dense)

** **:
-   
-   sparse vector 
-   

### 2.4   

****: `backend/scripts/splade/optimize_splade_for_domain.py`

**  **:
-     
-  +    
-    

**  **:
-    
-    
-   

** **:
- SPLADE + Dense Vector 
-    (: SPLADE 70%, Dense 30%)

---

## 3.  

### 3.1  

- **Recall@5**:  5     
- **Precision@5**:  5    
- **  (Latency)**:   
- ** **:    

### 3.2  

****: `backend/scripts/evaluation/evaluate_splade_optimized.py`

** **:
1. Dense (KURE-v1) -  
2. BM25 Sparse - PostgreSQL FTS
3. SPLADE ( ) -  
4. SPLADE () -  

** **:
- : 10  
- : 15  

** **:
```bash
conda run -n dsr python backend/scripts/evaluation/evaluate_splade_optimized.py
```

### 3.3     (2026-01-09)

** **:
- : 20,269 chunk ( 1,059,  139 )
- GPU: RTX 3060 12GB
- : naver/splade-v3

** **:

|  |   |   |  |
|------|----------|------------|--------|
| **  ** | 14.9 () | 366ms () | ** 40** |
| **  ** | 1.0 () | 67ms () | ** 15** |
| ** ** |  ( ) |  ( ) | **50-70% ** |
| **  chunk ** | 1000  |   | **** |
| ** ** |  ( ) |  | ** ** |

**  **:
-  ** **:     (40 vs  10-20)
-  ****:       (355-417ms)
-  ****:      (  )
-  ****: 20,269 chunk    ( 1,000  )

---

## 4.  

### 4.1  

#### 1:  
```bash
#   
cat backend/database/migrations/002_add_splade_sparse_vector.sql | \
  docker exec -i ddoksori_db psql -U postgres -d ddoksori
```

#### 2: SPLADE 
```bash
#  chunk 
conda run -n dsr python backend/scripts/splade/encode_splade_vectors.py

#    
conda run -n dsr python backend/scripts/splade/encode_splade_vectors.py --doc-type law
```

#### 3:   
```bash
conda run -n dsr python backend/scripts/splade/encode_splade_vectors.py --stats-only
```

### 4.2  

####  
```python
from scripts.splade.test_splade_optimized import OptimizedSPLADEDBRetriever

db_config = {
    'host': 'localhost',
    'port': 5432,
    'database': 'ddoksori',
    'user': 'postgres',
    'password': 'postgres'
}

retriever = OptimizedSPLADEDBRetriever(db_config)

#  
results = retriever.search_law_splade_optimized(" 750", top_k=5)

#  
results = retriever.search_criteria_splade_optimized(" ", top_k=5)
```

####   
```python
from scripts.splade.optimize_splade_for_domain import SPLADEDomainOptimizer

optimizer = SPLADEDomainOptimizer(db_config)

#   
results = optimizer.optimize_law_search(retriever, " 750", top_k=5)

#   
results = optimizer.optimize_criteria_search(retriever, " ", top_k=5)
```

####  
```python
from app.rag.multi_stage_retriever_v2 import MultiStageRetrieverV2

dense_retriever = MultiStageRetrieverV2(db_config)

# SPLADE + Dense  
results = optimizer.create_hybrid_search(
    dense_retriever,
    splade_retriever,
    " 750 ",
    doc_type='law',
    top_k=5,
    splade_weight=0.7,
    dense_weight=0.3
)
```

### 4.3  

```bash
#   
conda run -n dsr python backend/scripts/evaluation/evaluate_splade_optimized.py
```

 `backend/scripts/evaluation/splade_optimized_results_YYYYMMDD_HHMMSS.json` .

---

## 5. 

### 5.1 SPLADE   

****: `torch  2.6 `

****:
```bash
# torch 
conda run -n dsr pip install --upgrade torch>=2.6

#   API  
conda run -n dsr python backend/scripts/splade/encode_splade_vectors.py --remote --api-url http://localhost:8001
```

### 5.2   

****:     GPU  

****:
```bash
#   
conda run -n dsr python backend/scripts/splade/encode_splade_vectors.py --batch-size 64

# GPU  
conda run -n dsr python -c "import torch; print(torch.cuda.is_available())"
```

### 5.3   

****:    sparse vector NULL

****:
```bash
#   
conda run -n dsr python backend/scripts/splade/encode_splade_vectors.py --stats-only

#  chunk 
conda run -n dsr python backend/scripts/splade/encode_splade_vectors.py --no-resume
```

### 5.4  

****: OOM    

****:
```bash
#   
conda run -n dsr python backend/scripts/splade/encode_splade_vectors.py --batch-size 16

#    
conda run -n dsr python backend/scripts/splade/encode_splade_vectors.py --doc-type law
conda run -n dsr python backend/scripts/splade/encode_splade_vectors.py --doc-type criteria_*
```

---

## 6.   

### 6.1      (   )

- [x] **SPLADE   **  
- [x] ** Retriever **  
- [x] **   **  
- [x] **None   **   (law_name, item )
- [ ] **   ** (   )
- [ ] **  ** (SPLADE + Dense )
- [ ] **  ** (  )

### 6.2   (1-2)

- [ ] ** ID  **:  ,    
  - :    
  - :  ("750")   1.5 
  - : ("")   1.3 
- [ ] **    **
  - :   (SPLADE 70%, Dense 30%)
  - :      
- [ ] **     **
  -    
  -     
  -    

### 6.3   (1-2)

- [ ] **  ** ( SPLADE )
  -   SPLADE  
  -     
- [ ] **  fallback** (   )
  -    chunk    
- [ ] ** ** (  )
  -     
- [ ] **  **
  - Cross-Encoder  
  -   

### 6.4   (3-6)

- [ ] **SPLADE-v3 → SPLADE-v4 **
  -      
- [ ] **    **
  -    
  -   
- [ ] **   **
  - ,    
  - A/B   

---

## 7.  

### 7.1  
- [`SPLADE___.md`](./SPLADE___.md) -   
- [`embedding_process_guide.md`](../guides/embedding_process_guide.md) -   

### 7.2  
- `backend/database/migrations/002_add_splade_sparse_vector.sql` -  
- `backend/scripts/splade/encode_splade_vectors.py` -  
- `backend/scripts/splade/test_splade_optimized.py` -  Retriever
- `backend/scripts/splade/optimize_splade_for_domain.py` -  
- `backend/scripts/evaluation/evaluate_splade_optimized.py` -  

### 7.3  
- `backend/scripts/evaluation/test_cases_splade_law.json` -   
- `backend/scripts/evaluation/test_cases_splade_criteria.json` -   

---

## 8. 

SPLADE      .  **  **   **40 ** ,       .

### 8.1  

** **:
-  ** **:  14.9 → 366ms ( 40 )
-  ** **:  1.0 → 67ms ( 15 )
-  ** **: 50-70%  (    )
-  **  chunk **: 1,000  →  (20,269  )
-  ** **:    (355-417ms )

** **:
-     (SPLADE sparse vector )
-  SPLADE   (20,269 chunk  )
-   Retriever 
-     
-     

### 8.2   

** **:
-      (  )
-       
-      

** **:
-     
-   
- Cross-Encoder  

### 8.3  

** **:
1.      
2.    
3.     

** **:
1.    ( SPLADE )
2.    
3.   

---

****: Multi-Agent System  
** **: 2026-01-09  
** **: 2026-01-09  
**  **: `backend/scripts/evaluation/splade_optimized_results_20260109_014557.json`
