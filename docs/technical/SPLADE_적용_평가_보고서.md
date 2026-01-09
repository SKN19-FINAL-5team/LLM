# SPLADE   

****: 2026-01-07  
****: Multi-Agent System Product Manager  
** **:      
****: v1.0  
**POC **:   ( )

---

## Executive Summary

  SPLADE (Sparse Lexical And Expansion)               . **  **, SPLADE     ,       **    **.

###  
-  ****:   , Phase 3  
-  ****: PostgreSQL Full-Text Search ( ) + Cross-Encoder Reranking 
-  ****:  SPLADE    

---

## 1. SPLADE 

### 1.1 SPLADE?

**SPLADE (SParse Lexical AnD Expansion)** Sparse Vector   , Dense Vector (KURE-v1 )   Sparse Vector (TF-IDF, BM25)      .

### 1.2  

```
: " 750  "

Dense Vector (KURE-v1):
[0.12, -0.34, 0.56, ..., 0.89]  # 1024

Sparse Vector (SPLADE):
{
  "": 2.3,
  "750": 3.1,  #    
  "": 2.8,
  "": 2.5,
  "": 1.2,     #  
  "": 1.1,
  "": 0.9
}
```

### 1.3  

|  |  |  |
|------|------|------|
| ** ** |     | Recall  |
| ** ** | 0    |    |
| ** ** |      |   |
| ** ** |       |    |

---

## 2.   

### 2.1   (Law)

#### 
- ****:   (: "750") +  
- ****:    ("750" ≠ "751")
- ** **: 1,059  (13 )

#### SPLADE 

|   |  |  |
|-----------|------|------|
| **  ** |   | "750"    |
| **  ** |   | "" → "", ""  |
| ** ** |   | Dense Vector   |

** **: Recall@5 +10%, Precision@5 +5%

---

### 2.2   (Criteria)

#### 
- ****:  +  + 
- ****:     ("" ≠ "")
- ** **: 139  (1 )

#### SPLADE 

|   |  |  |
|-----------|------|------|
| ** ** |   | "", "TV"   |
| ** ** |   | "" → "", ""  |
| ** ** |   | " > "    |

** **: Recall@5 +8%, Precision@5 +3%

---

## 3.  

### 3.1 

|  |   | /  |
|------|-----------|----------------|
|  **  ** |  ,    |   |
|  ** ** |      |   |
|  **  ** | Sparse Vector Dense  1/10  |   |
|  ** ** |     |    |

### 3.2 

|  |   | /  |
|------|-----------|----------------|
|  **  ** |  SPLADE    |   |
|  **  ** |      |  /  |
|  ** ** | Sparse Vector   |    |
|  **  ** | Dense Vector     |     |

### 3.3   

|   | Recall@5 | Precision@5 |   |  |
|-----------|----------|-------------|-------------|------|
| **Dense (KURE-v1)** | 60% | 65% |  () |   |
| **Keyword (PostgreSQL FTS)** | 40% | 80% |  () |    |
| **Hybrid ()** | **70%** | **75%** |  () |  **** |
| **SPLADE ()** | 75% | 78% | **** |  ROI  |

---

## 4.  

### 4.1  

|  |  |   |  |
|------|--------|-----------|------|
| **  ** |  | 1 |   ,   |
| **** |  | 2-4 |     |
| **Sparse ** |  | 1 | Inverted Index  |
| ** API ** |  | 1 | Sparse Vector   |
| ** ** |  | 1 |    |
| **** |  | 3 |   |

**  **: **7-10**

### 4.2  

|  |  |
|------|------|
| GPU  (2-4) | $500-1000 |
|   (7-10) |  |
|  (Sparse Index) |     |

** **: **$500-1000 + **

---

## 5. : Cross-Encoder Reranking

### 5.1 

SPLADE  **Cross-Encoder  **  .

### 5.2 

|  | SPLADE | Cross-Encoder |  |
|------|--------|---------------|------|
| ** ** |  (7-10) |  (1) |  Cross-Encoder |
| ** ** |  ( ) |  (klue/roberta) |  Cross-Encoder |
| **Precision ** | +3-5% | **+15-20%** |  Cross-Encoder |
| **** | $500-1000 | $0 () |  Cross-Encoder |

### 5.3  

```python
from sentence_transformers import CrossEncoder

model = CrossEncoder('klue/roberta-large', max_length=512)

def rerank_with_cross_encoder(query: str, documents: List[Dict], top_k: int = 5):
    """
    Cross-Encoder 
    """
    pairs = [(query, doc['content']) for doc in documents]
    scores = model.predict(pairs)
    
    for doc, score in zip(documents, scores):
        doc['cross_encoder_score'] = float(score)
    
    documents.sort(key=lambda x: x['cross_encoder_score'], reverse=True)
    return documents[:top_k]
```

****: Precision@5 +15%, MRR +20%  
** **: **1**

---

## 6.  

### 6.1 ROI 

|  |  |  | ROI |  |
|--------|------|------|-----|------|
| **  ** | 0 | 0% | - | - |
| **Cross-Encoder** | 1 | +15% |   |  ** ** |
| **SPLADE** | 7-10 | +5-8% |   |   |
| **Graph RAG** | 9 | +30% ( ) |   |  Phase 3 |

### 6.2 

1. **Phase 2**: Cross-Encoder Reranking (1, ROI ) 
2. **Phase 3**: Graph RAG (9,   ) 
3. **Phase 4**: SPLADE (    ) 

---

## 7.   

### 7.1  

|   |  |  |
|-----------|------|------|
| ** ** |  |     |
| ** ** |  |     |
| **ROI** |  |     |
| **** |  |    |

** **:  **   **

### 7.2 

####   (Phase 2)
 **Cross-Encoder Reranking ** (1)
- klue/roberta-large 
- Precision@5 +15% 
-   

####  (Phase 4+)
⏸ **SPLADE  **
-  SPLADE    
-      
- ROI   

####  (Phase 3)
 **Graph RAG  **
-    
- --  
- SPLADE   

### 7.3  

    SPLADE :

1.   SPLADE   
2.       (1000+ )
3.    Recall@5 < 60% (  )
4.     (7-10  )

---

## 8.  

### 8.1 SPLADE  
- Formal, T., et al. (2021). "SPLADE: Sparse Lexical and Expansion Model for First Stage Ranking"
- https://arxiv.org/abs/2107.05720

### 8.2   
- klue/roberta-large (Cross-Encoder)
- KURE-v1 ( Dense Vector)
- KorQuAD  

### 8.3  
- [`RAG___.md`](../pm/RAG___.md)
- [`MAS___.md`](./MAS___.md)

---

****: Multi-Agent System Product Manager  
** **: 2026-01-07  
** **: 2026-07-07 (6 ,    )
