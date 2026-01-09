# RAG  

  RAG    .

##  

   RAG        .

###  

- **12  **: Precision@K, Recall@K, F1@K, MAP, MRR, NDCG@K, Document Type Coverage, Source Diversity 
- **   **: Vector Search, Hybrid Search, Multi-Source Search
- **  **: general_inquiry, legal_interpretation, similar_case
- **  **: JSON      

##   

```
evaluation/
 __init__.py
 README.md                   #  
 EVALUATION_GUIDE.md         #   
 metrics.py                  #    
 evaluator.py                #   
 dataset_generator.py        #    
 dataset_validator.py        #   
 run_evaluation.py           #   
 datasets/
    gold_v1.json           #   v1
 results/                   #    
```

##   

### 1.   

```bash
cd backend/evaluation
python dataset_generator.py
# : 1 (  )
```

### 2.  

```bash
python dataset_validator.py datasets/gold_v1.json
```

### 3.  

```bash
cd backend
python evaluation/run_evaluation.py \
  --dataset evaluation/datasets/gold_v1.json \
  --methods vector hybrid multi_source \
  --top-k 10
```

### 4.  

  `evaluation/results/`  :
- `evaluation_YYYYMMDD_HHMMSS.json`:  
- `evaluation_summary_YYYYMMDD_HHMMSS.json`:  

##   

###   

|  |  |  |
|------|------|------|
| Precision@K |  K     | > 0.7 |
| Recall@K |       | > 0.65 |
| F1@K | Precision Recall   | > 0.65 |
| MAP |     | > 0.7 |
| MRR |       | > 0.75 |
| NDCG@K |     | > 0.75 |

###   

|  |  |  |
|------|------|------|
| Doc Type Coverage |      | > 0.8 |
| Source Diversity |   (Shannon Entropy) | > 1.0 |

###   

|  |  |  |
|------|------|------|
| Query Time |    | < 0.5 |

##   

    [EVALUATION_GUIDE.md](./EVALUATION_GUIDE.md) .

###  

-     
-     
-    
- 

##  

- Python 3.11+
- PostgreSQL (pgvector )
-  API   
- RAG    

##    

```json
{
  "query_id": "Q001",
  "query": " ",
  "query_type": "general_inquiry | legal_interpretation | similar_case",
  "expected_doc_types": ["law", "counsel_case", "mediation_case"],
  "relevant_chunk_ids": ["chunk_id_1", "chunk_id_2"],
  "highly_relevant_chunk_ids": ["chunk_id_1"],
  "irrelevant_chunk_ids": [],
  "metadata": {
    "difficulty": "easy | medium | hard",
    "category": "",
    "created_at": "2026-01-05T14:30:00",
    "annotator": ""
  }
}
```

##    

```
================================================================================
  
================================================================================

[HYBRID]
--------------------------------------------------------------------------------
                             
--------------------------------------------------
Precision@1                      0.8000
Precision@3                      0.7333
Precision@5                      0.6800
Recall@3                         0.6500
Recall@5                         0.7200
F1@3                             0.6889
Average Precision                0.7245
Reciprocal Rank                  0.8250
NDCG@3                           0.7856
Doc Type Coverage                0.8500
Source Diversity                 1.2340
Avg Query Time (s)               0.1523

  Precision@3:
  - general_inquiry         0.7800
  - legal_interpretation    0.7000
  - similar_case            0.7200
```

##  

   :

1.    
2. RAG      
3. `datasets/gold_v1.json` 
4. `dataset_validator.py` 

##   

- [   ](../../rag_evaluation_plan.md)
- [RAG  ](../RAG_SETUP_GUIDE.md)
- [Information Retrieval Evaluation](https://en.wikipedia.org/wiki/Evaluation_measures_(information_retrieval))

---

****: Manus AI  
****: 2026-01-05  
****: v1.0
