#  RAG      

****: 2026-01-06  
****:   RAG    -  

---

##  Executive Summary ()

###  

|  |  |  |
|------|------|------|
| **  ** | 100% (4/4) |   |
| ** ** | 0.534 |   |
| **  ** | 2.20 |   |
| **Fallback ** | 0% |    |
| **   ** | 11 |   |

###  

1.  **  RAG   **
   - Stage 1 (+):  6 
   - Stage 2 ():  5 
   - Stage 3 (Fallback):  ( Stage 2 )

2.  **     **
   -   (70%) +   (30%) 
   - 4   100% 

3.  ** **
   -  0.5-0.7  (): 75%
   -        (6.09)
   -     (0.497)

---

##  1.    

### 1.1  

| ID |  |   |  |   |
|----|---------|-----------|----------|-----------|
| 1 |   ( ) | ECMC |  |  |
| 2 |    ( ) | ECMC |  |  |
| 3 |   ( ) | KCA |  |  |
| 4 |   ( ) | KCDRC |  |  |

### 1.2   

####  1:   ( )

```
: "   3    .    ?"

 :
- : 3 ( 6745, 367, 610)
- : 3 ( )
- : 5 (judgment, decision )

 :
- 1: ECMC ( 0.757)  
- 2: KCA ( 0.68)

:
- : 0.525
- : 0.667 ( judgment )
- : 0.332 ()

 : 6.09 ( ,   )
```

****: 
-     ECMC  
-  , ,    
-        

####  2:    ( )

```
: "   2    .   ."

 :
- : 3 ( 528, 543, 572)
- : 3 (,  )
- : 5 (parties_claim, judgment)

 :
- 1: ECMC ( 0.864)  
- 2: KCA ( 0.14)

:
- : 0.544
- : 0.686 ( parties_claim)
- : 0.365 ()

 : 0.84
```

****:
-  ''  ECMC   (0.864)
-       
-     (  )

####  3:   ( )

```
: "         .    ?"

 :
- : 3 (  )
- : 3 ( )
- : 5 (judgment, parties_claim)

 :
- 1: KCA ( 0.967)  
- 2: ECMC ( 0.73)

:
- : 0.571 ()
- : 0.690
- : 0.362

 : 0.95
```

****:
-  ''  KCA    (0.967)
-      (0.571)
-      

####  4:   ( )

```
: "        .      ?"

 :
- : 3 ( )
- : 3 ()
- : 5 (judgment)

 :
- 1: KCDRC ( 0.700)  
- 2: KCA ( 0.18)

:
- : 0.497 ()
- : 0.600
- : 0.357

 : 0.91
```

****:
-  '', ''  KCDRC  
-     (0.497) -     
-    

---

##  2. -  

### 2.1   

####  

1. **  **
   - `decision` ():  ,  
   - `reasoning`/`judgment`:  /
   - `law` ():    

2. **Overlapping **
   - 100-150   
   -     

3. **  **
   -  →   
   -    (0.3-0.7 )

####   

1. **   **
   
   :   700 
   
   :
   ```python
   'decision': {'max_length': 600},      #  
   'reasoning': {'max_length': 800},     #  
   'judgment': {'max_length': 800},      #  
   'law': {'max_length': 500},           #  
   'qa_combined': {'max_length': 600}    # Q&A 
   ```

2. ** **
   
   : content  
   ```python
   content = f"[] {law_name}\n[] {path}\n\n{text}"
   ```
   
   :   +  
   ```python
   chunk = {
       'content': text,  #  
       'metadata': {
           'law_name': law_name,
           'article_no': article_no,
           'category': category
       }
   }
   #   metadata  
   ```

3. **   **
   
   -  4   (0.497)
   - KCDRC     
   - , ,    

### 2.2   

####  

- ****: KURE-v1 (1024)
- ****:   0.534 ()
- ****:  0.2 ()

####   

```
 (≥0.7):  0 (0.0%)   ←    
 (0.5-0.7): 3 (75.0%)  ←   
 (<0.5):    1 (25.0%)  ←  
```

** **:
1.      
2.     
3.     ( 0.3)

---

##  3. RAG   

### 3.1   

####  

** ( )**:
```
User Query → Vector Search (All Types) → Top-K Results
```

** ( )**:
```
User Query 
  ↓
Stage 1: Law + Criteria ( )
  ↓
Stage 2: Mediation Cases (Stage 1  )
  ↓
Stage 3: Counsel Cases (Fallback,  )
  ↓
Combined Results + Agency Recommendation
```

####  

1. **  **
   - Stage 1:   ( + )
   - Stage 2:   ()
   - Stage 3:   () -  

2. **  **
   -       
   -     

3. **Fallback **
   -     
   -    ( )

### 3.2   

####  

```python
  =    (70%) +    (30%)
```

**  (70%)**:
-   (: '', '' → ECMC)
-    (  )

**  (30%)**:
-     
-   +  

####  

|  |  |  |  |  |
|--------|------|------|------|--------|
| 1 | ECMC | ECMC | 0.757 |  |
| 2 | ECMC | ECMC | 0.864 |  |
| 3 | KCA | KCA | 0.967 |  |
| 4 | KCDRC | KCDRC | 0.700 |  |

**: 100% (4/4)**

####   

1. **  **
   - '', ''   
   - '', ''   

2. **   **
   -    
   -    

3. **  **
   -  70% :  30%
   -    

---

##  4.  

### 4.1  

|  |  |  |
|------|-----|------|
|   | 2.20 |   |
|   | 0.84 |    |
|   | 6.09 |    |
|   | 0.20 |   |

****:
-    KURE-v1   ( 5)
-   1  ( )
-     

### 4.2   

|  |  |  |
|------|------|------|
|  | 3 | 3-3 |
|  | 3 | 3-3 |
|  | 5 | 5-5 |
|  | 0 | 0-0 |
| **** | **11** | **11-11** |

****:
-    11 
- LLM    ( 6,000-7,000)
- GPT-4o-mini   (128K)  

---

##  5.   

### 5.1    (High Priority)

#### 1.    

****:  4   (0.497)

****:
```python
# 1. KCDRC    
- , , ,   
-     

# 2.      
CHUNK_PROCESSING_RULES = {
    'copyright_case': {  # 
        'min_length': 200,
        'max_length': 800,
        'enrich_keywords': ['', '', '']
    }
}
```

#### 2.   

****:    6 

****:
```python
# FastAPI    
@app.on_event("startup")
async def load_models():
    """      """
    retriever.load_model()
    print(" Embedding model preloaded")
```

#### 3.    

****:    (0.33-0.39)

****:
```python
# content   
chunk = {
    'content': raw_text,  #   
    'metadata': {
        'law_name': '',
        'article_no': '610',
        'category': '',
        'keywords': ['', '', '']
    }
}

#      
final_score = (
    similarity * 0.7 +
    metadata_match_score * 0.3
)
```

### 5.2   (Medium Priority)

#### 1.    

```python
OPTIMIZED_CHUNK_LENGTHS = {
    'decision': {'max_length': 600, 'target': 500},
    'reasoning': {'max_length': 800, 'target': 700},
    'judgment': {'max_length': 800, 'target': 700},
    'law': {'max_length': 500, 'target': 400},
    'qa_combined': {'max_length': 600, 'target': 500}
}
```

** **:
-   +5-10% 
- LLM   

#### 2.  (Re-ranking) 

```python
def rerank_chunks(chunks, user_query, user_context):
    """ """
    for chunk in chunks:
        semantic_score = chunk['similarity'] * 0.4
        recency_score = calculate_recency(chunk['decision_date']) * 0.2
        agency_score = match_agency(chunk['agency'], user_context) * 0.2
        type_score = get_type_weight(chunk['chunk_type']) * 0.2
        
        chunk['final_score'] = (
            semantic_score + recency_score + 
            agency_score + type_score
        )
    
    return sorted(chunks, key=lambda x: x['final_score'], reverse=True)
```

** **:
-      
-   

#### 3.   

```python
#      
expanded_chunks = []
for chunk in top_chunks:
    context = get_chunk_with_context(
        chunk_id=chunk['chunk_id'],
        window_size=1  #  1
    )
    expanded_chunks.extend(context)
```

** **:
-   
-   

### 5.3   (Long Term)

#### 1.   

```python
#    
models = [
    'nlpai-lab/KURE-v1',  #  
    'BM-K/KoSimCSE-roberta',  #   
    'sentence-transformers/paraphrase-multilingual-mpnet-base-v2'  # 
]

#  
ensemble_results = combine_multi_model_search(query, models, weights=[0.5, 0.3, 0.2])
```

#### 2.   

```python
#      
class SearchFeedback:
    def __init__(self):
        self.feedback_db = []
    
    def record_feedback(self, query, chunks, user_rating):
        """ """
        self.feedback_db.append({
            'query': query,
            'chunks': chunks,
            'rating': user_rating,  # 1-5 
            'timestamp': datetime.now()
        })
    
    def improve_ranking(self):
        """   """
        #      
        pass
```

#### 3.   (Query Expansion)

```python
def expand_query(query):
    """,   """
    # : "" → ["", "", "", ""]
    synonyms = get_synonyms(query)
    expanded = [query] + synonyms
    
    #     
    all_results = []
    for q in expanded:
        results = search(q)
        all_results.extend(results)
    
    return deduplicate_and_rerank(all_results)
```

---

##  6. 

### 6.1  

 ** **:
1.   RAG   
2.    100% 
3.  2.2  
4.    (0.5-0.6)

 **  **:
1.    
2.    
3.      

### 6.2  

1. **  RAG  **
   -  →  →    
   - Fallback   

2. **   **
   -  +   (70:30) 
   -   100% 

3. **  **
   -   
   - Overlapping  
   -   

### 6.3  

** ** (1-2):
- [ ]     
- [ ] FastAPI   
- [ ]   

** ** (1):
- [ ]    
- [ ]   
- [ ]   

** ** (3-6):
- [ ]   
- [ ]   
- [ ] A/B  

---

##   

###  

1. [  ](./rag_analysis_current_system.md)
   - -   
   -    

2. [   README](../backend/app/rag/README_agency_recommender.md)
   -   
   -  

3. [ README](../backend/scripts/TEST_README.md)
   -   
   -   

###  

- `backend/app/rag/multi_stage_retriever.py`:   
- `backend/app/rag/agency_recommender.py`:  
- `backend/scripts/testing/test_multi_stage_rag.py`:  
- `backend/scripts/analytics/analyze_rag_results.py`:  

---

** **: 1.0  
** **: 2026-01-06  
****: RAG System Team
