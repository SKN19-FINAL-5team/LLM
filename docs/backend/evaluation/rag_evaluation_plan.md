#   - RAG    

****: 2026-01-05  
** **: feature/pr4-multi-agent-prep  
****: RAG          

---

##  

1. [  ](#--)
2. [  ](#--)
3. [  ](#--)
4. [ ](#-)
5. [ ](#-)

---

##    

###  

RAG     :
- ** ** 
- ** **   
- ****   
- ** **  

###  

1. ** ** (Vector Search)
2. ** ** (Hybrid Search)
3. **  ** (Multi-Source Search)
4. ** ** (Context Expansion)

---

##    

###  

  **- ** ,     :

```json
{
  "query_id": "Q001",
  "query": "   .    ?",
  "query_type": "general_inquiry",
  "expected_doc_types": ["counsel_case", "mediation_case", "law"],
  "relevant_chunk_ids": [
    "consumer.go.kr:consumer_counsel_case:12345::chunk0",
    "consumer.go.kr:consumer_mediation_case:67890::chunk1"
  ],
  "highly_relevant_chunk_ids": [
    "consumer.go.kr:consumer_counsel_case:12345::chunk0"
  ],
  "irrelevant_chunk_ids": [
    "statute:civil_law:article_100::chunk0"
  ],
  "metadata": {
    "difficulty": "easy",
    "category": "",
    "created_at": "2026-01-05",
    "annotator": "expert_1"
  }
}
```

###  

|  |  |  |
|------|------|------|
| `query_id` | string |   ID |
| `query` | string |   |
| `query_type` | string |   (general_inquiry, legal_interpretation, similar_case) |
| `expected_doc_types` | array |     |
| `relevant_chunk_ids` | array |    ID  () |
| `highly_relevant_chunk_ids` | array |     ID  ( ) |
| `irrelevant_chunk_ids` | array |    ID  ( ) |
| `metadata` | object |   |

###  

- ** **: 30~50 
- ** **: 100~200  ()

###   

|   |  |  |
|----------|------|------|
| `general_inquiry` | 50% |    |
| `legal_interpretation` | 25% |      |
| `similar_case` | 25% |    |

###  

|  |  |  |
|--------|------|------|
| `easy` | 40% |  ,    |
| `medium` | 40% |  ,    |
| `hard` | 20% |  ,   |

---

##    

### 1.   

#### 1.1 Precision@K ()

 K      

```
Precision@K = ( K    ) / K
```

****: K = 1, 3, 5, 10

****:
-    
-      

#### 1.2 Recall@K ()

     K  

```
Recall@K = ( K    ) / (   )
```

****: K = 1, 3, 5, 10

****:
-     
-      

#### 1.3 F1-Score@K

Precision Recall  

```
F1@K = 2 * (Precision@K * Recall@K) / (Precision@K + Recall@K)
```

****:
- Precision Recall  
-    

#### 1.4 Mean Average Precision (MAP)

   Average Precision 

```
AP = (1/|R|) * Σ(Precision@k * rel(k))
MAP = (1/|Q|) * Σ AP(q)
```

:
- `R`:   
- `rel(k)`: k     1,  0
- `Q`:   

****:
-     
-     

#### 1.5 Mean Reciprocal Rank (MRR)

      

```
RR = 1 / (    )
MRR = (1/|Q|) * Σ RR(q)
```

****:
-       
-      

#### 1.6 Normalized Discounted Cumulative Gain (NDCG@K)

    

```
DCG@K = Σ(rel_i / log2(i+1))
IDCG@K =    DCG
NDCG@K = DCG@K / IDCG@K
```

:
- `rel_i`: i   (0, 1, 2)
  - 0:  
  - 1:  
  - 2:   

****:
-     
- 0~1  , 1  

### 2.   

#### 2.1 Document Type Coverage

     

```
Coverage = (   ) / (   )
```

****:
- 1.0     
-      

#### 2.2 Source Diversity

    (Shannon Entropy)

```
Diversity = -Σ(p_i * log2(p_i))
```

 `p_i`   

****:
-     
-   

### 3.   

#### 3.1 Average Query Time

   ()

```
Avg_Time = Σ(query_time) / |Q|
```

****: < 0.5 ( ), < 1.0 ( )

#### 3.2 Throughput

    

```
Throughput = |Q| / Total_Time
```

****: > 10 queries/sec

### 4.   

#### 4.1 Context Relevance

  

```
Context_Relevance = (    ) / (   )
```

****:
-    
-   

#### 4.2 Context Completeness

    

```
Completeness = (   ) / (   )
```

****:
- 1.0   
- LLM      

---

##   

### Phase 1: RAG        

****:       

****:
-     ( )
-   

### Phase 2:       

****:        

** **:
1. **  **
   -     
   -   
   -     ( RAG  )

2. ** **
   - JSON   
   -   (v1, v2, ...)
   -   (  )

****:
- `backend/evaluation/dataset_generator.py`
- `backend/evaluation/datasets/gold_v1.json`
- `backend/evaluation/dataset_validator.py`

### Phase 3:      

****:      

** **:
1. **  **
   - `PrecisionRecallCalculator`
   - `RankingMetricsCalculator` (MAP, MRR, NDCG)
   - `DiversityCalculator`
   - `EfficiencyCalculator`

2. **   **
   ```python
   {
     "query_id": "Q001",
     "metrics": {
       "precision@1": 1.0,
       "precision@3": 0.67,
       "recall@3": 0.5,
       "f1@3": 0.57,
       "map": 0.75,
       "mrr": 1.0,
       "ndcg@3": 0.85,
       "doc_type_coverage": 0.67,
       "query_time": 0.12
     },
     "retrieved_chunks": [...],
     "relevant_chunks": [...]
   }
   ```

****:
- `backend/evaluation/metrics.py`
- `backend/evaluation/evaluator.py`

### Phase 4:      

****:       

** **:
1. **  **
   -   
   -     
   -   (JSON, CSV)

2. ** **
   -   
   -   
   -  
   -   
   -  (matplotlib)

3. ** **
   -   
   -    
   -   

****:
- `backend/evaluation/run_evaluation.py`
- `backend/evaluation/report_generator.py`
- `backend/evaluation/results/` (  )

### Phase 5:   

****:       

** **:
1. ** **
   -     
   -    

2. ** **
   -    
   -   

3. ****
   -    
   -    
   -    

****:
- `backend/tests/test_evaluation.py`
- `backend/evaluation/EVALUATION_GUIDE.md`

---

##   

###  

```
backend/
 evaluation/
    __init__.py
    metrics.py                  #    
    evaluator.py                #   
    dataset_generator.py        #   
    dataset_validator.py        #   
    report_generator.py         #   
    run_evaluation.py           #   
    EVALUATION_GUIDE.md         #   
    datasets/
       gold_v1.json            #   v1
       gold_v2.json            #   v2 ()
    results/
        evaluation_2026-01-05.json
        evaluation_2026-01-05.csv
        comparison_report.md
 tests/
     test_evaluation.py          #   
```

###   

```markdown
# RAG   

****: 2026-01-05  
****: gold_v1 (50 queries)  
** **: Vector, Hybrid, Multi-Source

##   

|  | Vector | Hybrid | Multi-Source |
|------|--------|--------|--------------|
| Precision@3 | 0.65 | 0.72 | 0.78 |
| Recall@3 | 0.58 | 0.68 | 0.75 |
| F1@3 | 0.61 | 0.70 | 0.76 |
| MAP | 0.62 | 0.71 | 0.77 |
| MRR | 0.70 | 0.78 | 0.85 |
| NDCG@3 | 0.68 | 0.75 | 0.82 |
| Avg Time (s) | 0.08 | 0.15 | 0.22 |

##   

### General Inquiry (25 queries)
- Best Method: Multi-Source
- Precision@3: 0.82
- Recall@3: 0.78

### Legal Interpretation (13 queries)
- Best Method: Hybrid
- Precision@3: 0.75
- Recall@3: 0.70

### Similar Case (12 queries)
- Best Method: Multi-Source
- Precision@3: 0.73
- Recall@3: 0.72

##  

1. **Multi-Source   **:    
2. **Hybrid  **:    
3. **  **: Multi-Source    
```

---

##   

###  

-  6    
-  30    
-      
-      

###   

- **Precision@3**: > 0.70
- **Recall@3**: > 0.65
- **MAP**: > 0.70
- **MRR**: > 0.75
- **NDCG@3**: > 0.75
- **Query Time**: < 0.5 (), < 1.0 ()

---

##   

- [Information Retrieval Evaluation Metrics](https://en.wikipedia.org/wiki/Evaluation_measures_(information_retrieval))
- [TREC Evaluation Guidelines](https://trec.nist.gov/)
- [RAG Evaluation Best Practices](https://www.llamaindex.ai/blog/evaluating-rag)

---

****: Manus AI (RAG  )  
** **: 2026-01-05
