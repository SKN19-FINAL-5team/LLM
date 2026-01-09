#   - RAG    

****: 2026-01-05  
****: v1.0

---

##  

1. [](#)
2. [  ](#--)
3. [  ](#--)
4. [ ](#-)
5. [  ](#--)
6. [](#)

---

##  

RAG          .

###  

- **12  **: Precision, Recall, F1, MAP, MRR, NDCG 
- **   **: Vector, Hybrid, Multi-Source
- **  **: general_inquiry, legal_interpretation, similar_case
- **  **: JSON,  

---

##    

```
backend/evaluation/
 __init__.py
 metrics.py              #    
 evaluator.py            #   
 dataset_generator.py    #   
 dataset_validator.py    #   
 run_evaluation.py       #   
 EVALUATION_GUIDE.md     #  
 datasets/
    gold_v1.json       #  
 results/               #  
     evaluation_20260105_143000.json
     evaluation_summary_20260105_143000.json
```

---

##    

### 1.   ( )

```bash
cd backend/evaluation
python dataset_generator.py
```

****: 1 (  )

****: `datasets/gold_v1.json`  ( 10 )

### 2.  

```json
{
  "query_id": "Q001",
  "query": "   .    ?",
  "query_type": "general_inquiry",
  "expected_doc_types": ["counsel_case", "law"],
  "relevant_chunk_ids": [
    "consumer.go.kr:consumer_counsel_case:53321::chunk0"
  ],
  "highly_relevant_chunk_ids": [
    "consumer.go.kr:consumer_counsel_case:53321::chunk0"
  ],
  "irrelevant_chunk_ids": [],
  "metadata": {
    "difficulty": "easy",
    "category": "",
    "created_at": "2026-01-05T14:30:00",
    "annotator": "expert_1"
  }
}
```

### 3.  

      :

1. ** **:      
2. ** **: RAG       
3. ** **: JSON     `dataset_generator.py` 

### 4.  

```bash
cd backend/evaluation
python dataset_validator.py datasets/gold_v1.json
```

** **:
-    
-   
- query_id  
-   (highly_relevant ⊆ relevant)

---

##   

###  

```bash
cd backend
python evaluation/run_evaluation.py \
  --dataset evaluation/datasets/gold_v1.json \
  --methods vector hybrid multi_source \
  --top-k 10 \
  --output-dir evaluation/results
```

###  

|  |  |  |
|------|------|--------|
| `--dataset` |    | () |
| `--methods` |    | vector hybrid multi_source |
| `--top-k` |    | 10 |
| `--output-dir` |    | evaluation/results |
| `--db-host` |   |  DB_HOST |
| `--db-port` |   |  DB_PORT |
| `--embed-api-url` |  API URL |  EMBED_API_URL |

### :    

```bash
python evaluation/run_evaluation.py \
  --dataset evaluation/datasets/gold_v1.json \
  --methods hybrid \
  --top-k 5
```

###   

```
============================================================
  - RAG   
============================================================
: evaluation/datasets/gold_v1.json
 : vector, hybrid, multi_source
Top-K: 10
============================================================

[1/3] RAG Retriever  ...
 RAG Retriever  

[2/3] Evaluator  ...
   : 10 
 Evaluator  

[3/3]   ...

[VECTOR]  ...
  : 10/10 (100.0%)
 [VECTOR]  

[HYBRID]  ...
  : 10/10 (100.0%)
 [HYBRID]  

[MULTI_SOURCE]  ...
  : 10/10 (100.0%)
 [MULTI_SOURCE]  

   : evaluation/results/evaluation_20260105_143000.json
   : evaluation/results/evaluation_summary_20260105_143000.json
```

###  

#### 1.   (`evaluation_YYYYMMDD_HHMMSS.json`)

     :
-   
-   
-    

#### 2.   (`evaluation_summary_YYYYMMDD_HHMMSS.json`)

  :
-   
-   
-    

---

##    

### 1. Precision@K ()

****:  K      

****:
- **0.8 **:  
- **0.6 ~ 0.8**: 
- **0.4 ~ 0.6**: 
- **0.4 **:  

** **:
-    
-   
-   

### 2. Recall@K ()

****:      K  

****:
- **0.7 **:  
- **0.5 ~ 0.7**: 
- **0.3 ~ 0.5**: 
- **0.3 **:  

** **:
- K  
-   
-    

### 3. F1-Score@K

****: Precision Recall  

****:
- **0.7 **:  
- **0.5 ~ 0.7**: 
- **0.3 ~ 0.5**: 
- **0.3 **:  

** **:
- Precision Recall  
-    

### 4. MAP (Mean Average Precision)

****:     

****:
- **0.7 **:  
- **0.5 ~ 0.7**: 
- **0.3 ~ 0.5**: 
- **0.3 **:  

** **:
-  (Learning to Rank) 
- (Reranking)  

### 5. MRR (Mean Reciprocal Rank)

****:      

****:
- **0.8 **:   ( 1~2 )
- **0.6 ~ 0.8**:  ( 3~4 )
- **0.4 ~ 0.6**:  ( 5~10 )
- **0.4 **:  

** **:
-    
-   

### 6. NDCG@K (Normalized Discounted Cumulative Gain)

****:     

****:
- **0.8 **:  
- **0.6 ~ 0.8**: 
- **0.4 ~ 0.6**: 
- **0.4 **:  

** **:
-   
-  

### 7. Document Type Coverage

****:     

****:
- **1.0**:  (  )
- **0.7 ~ 1.0**: 
- **0.5 ~ 0.7**: 
- **0.5 **:  

** **:
-     
-      

### 8. Source Diversity

****:     (Shannon Entropy)

****:
- **1.5 **:  
- **1.0 ~ 1.5**: 
- **0.5 ~ 1.0**: 
- **0.5 **: 

** **:
-     
-   

### 9. Query Time

****:    ()

****:
- **Vector **: < 0.1
- **Hybrid **: < 0.3
- **Multi-Source **: < 0.5

** **:
-  
-  
-  

---

##  

###  1: `ModuleNotFoundError: No module named 'rag'`

****: Python  

****:
```bash
cd backend
export PYTHONPATH=$PYTHONPATH:$(pwd)
python evaluation/run_evaluation.py ...
```

###  2:   

****:    

****:
```bash
python evaluation/dataset_validator.py datasets/gold_v1.json
```

   JSON  

###  3:     

****:     

****:
-     
- `--top-k`  
-   

###  4: `relevant_chunk_ids` 

****:       

****:
- RAG      ID  
-  `dataset_generator.py` `suggest_relevant_chunks()`  

---

##   

- [   ](../../rag_evaluation_plan.md)
- [RAG  ](../RAG_SETUP_GUIDE.md)
- [Information Retrieval Evaluation](https://en.wikipedia.org/wiki/Evaluation_measures_(information_retrieval))

---

****: Manus AI (RAG  )  
** **: 2026-01-05
