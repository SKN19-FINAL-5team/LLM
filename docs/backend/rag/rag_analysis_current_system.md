#  RAG  -   

****: 2026-01-06  
****:  -   RAG  ,  

---

##  1.   

### 1.1    (CHUNK_PROCESSING_RULES)

  **    **  .

####   

|   |   |   |   |   |   | Overlap  |
|-----------|----------|----------|-----------|-----------|-----------|------------|
| `decision` | 100 | 700 | 600 |  |  | 100 |
| `reasoning` | 150 | 700 | 600 |  |  | 150 |
| `judgment` | 200 | 700 | 600 |  |  | 150 |
| `parties_claim` | 150 | 700 | 600 |  |  | 150 |
| `law` | 50 | 700 | 600 |  |  | 100 |
| `law_reference` | 50 | 700 | 600 |  |  | 100 |
| `resolution_row` | 100 | 700 | 600 |  |  | 100 |
| `qa_combined` | 150 | 700 | 600 |  |  | 100 |
| `article` | 100 | 700 | 600 |  |  | 100 |
| `paragraph` | 100 | 700 | 600 |  |  | 100 |

**  **:
- KURE-v1   : **512 **
-  : **1.5 ≈ 1**
-  : **500-700 ( 250-350 )**

####   

1. ** **
   -        
   - `decision`   ( )
   - `reasoning`, `judgment`  / 

2. **Overlapping **
   ```python
   #        
   if previous_tail and sub_chunks:
       chunk_content = previous_tail + '\n\n' + chunk_content
   ```
   -      (100-150)
   -   

3. **  **
   ```python
   # 1:   
   sections = re.split(r'\n\n+', content)
   
   # 2:   
   sentences = re.split(r'([.!?]\s+)', section)
   ```
   -  :  → 
   -   

4. **  **
   ```python
   def _estimate_token_count(self, text: str) -> int:
       char_count = len(text)
       return int(char_count / 1.5)  #  
   ```
   -    
   -    

5. ** **
   ```python
   # 1.   
   chunks = self._merge_short_chunks(chunks)
   
   # 2.   
   chunks = self._split_long_chunks(chunks)
   
   # 3.   
   # ...
   
   # 4.   
   validation_result = self._validate_token_limit(chunks)
   ```
   -  4 

####    

1. **   **
   
   ****:   700    
   
   ```python
   # :   700
   'max_length': 700,
   'target_length': 600,
   ```
   
   **   **:
   - `decision`:   → **500-600** 
   - `reasoning`/`judgment`:   → **700-800** 
   - `law`:   → **400-500** 
   
   ** **:    

2. **  **
   
   ** **:
   ```python
   #   
   chunk = {
       'content': f"[] {data['law_name']}\n[] {data['path']}\n\n{data['index_text']}"
   }
   ```
   
   ****:
   - (, ) content 
   -      
   -     
   
   ** **:
   -    
   -      
   -      

3. **   **
   
   ** **:
   -    
   -    
   
   ****:
   -     
   -     
   
   ** **:
   -   
   -   
   -    

4. **Overlapping  **
   
   ** **:
   ```python
   #        
   previous_tail = chunk_content[-overlap_size:]
   ```
   
   ****:
   -     
   -    
   -      
   
   ** **:
   -   
   -   overlap 
   -    

---

##  2.   

### 2.1  

** **: `nlpai-lab/KURE-v1`

** **:
- ****: 1024
- ****:  / 
- ** **: 512 
- ** **: Sentence Transformers 

****:
-      
-     
-    (1024)

### 2.2   

```python
# embed_data_remote.py
class EmbeddingPipeline:
    def __init__(self, db_config, embed_api_url):
        self.embed_api_url = embed_api_url
        self.batch_size = 32  #  
```

** **:

1. ** ** (32  )
   ```python
   for i in range(0, len(chunks_to_embed), self.batch_size):
       batch = chunks_to_embed[i:i + self.batch_size]
       embeddings = self.generate_embeddings(texts)
   ```

2. ** API ** (RunPod GPU)
   ```python
   response = requests.post(
       self.embed_api_url,
       json={"texts": texts},
       timeout=300  # 5 
   )
   ```

3. ** ** ()
   ```python
   is_low_quality, reason = self.is_low_quality_embedding(embedding)
   ```

4. **PostgreSQL ** (pgvector)
   ```python
   UPDATE chunks
   SET embedding = %s::vector
   WHERE chunk_id = %s
   ```

####   

1. **  **
   
   ```python
   def is_low_quality_embedding(self, embedding) -> Tuple[bool, str]:
       vec = np.array(embedding)
       
       #  1: Norm  
       if np.linalg.norm(vec) < 0.1:
           return True, "norm  "
       
       #  2:   
       if np.var(vec) < 0.001:
           return True, "  "
       
       #  3: NaN/Inf  
       if np.isnan(vec).any() or np.isinf(vec).any():
           return True, "NaN  Inf  "
       
       #  4:   ( 0)
       near_zero = np.abs(vec) < 0.001
       if near_zero.sum() / len(vec) > 0.9:
           return True, " "
       
       return False, ""
   ```
   
   ** **:
   - Norm  (  )
   -   (  )
   -   (NaN, Inf)
   -   ( 0)

2. **  **
   - GPU  
   -   
   -   ()

3. **  **
   ```python
   chunks_to_embed = [
       (chunk['chunk_id'], chunk['content'])
       for chunk in valid_chunks
       if chunk['content'] and len(chunk['content'].strip()) > 0
   ]
   ```

####    

1. **  **
   
   ** **: KURE-v1 
   
   ****:
   -     
   -   
   -   
   
   ** **:
   -    ( )
   - Fallback  
   -    

2. **    **
   
   ** **:
   -     
   -    
   
   ****:
   -     
   -   (GPU )
   
   ** **:
   -   
   -   
   -   

3. **   **
   
   ** **:
   ```python
   embedding_model VARCHAR(50) DEFAULT 'KURE-v1'
   ```
   
   ****:
   -       
   -   
   
   ** **:
   -    
   -   
   - A/B  

---

##  3. RAG  

### 3.1  

```mermaid
graph TD
    User[ ] --> Embed[ ]
    Embed --> Search[Vector ]
    Search --> Filter[]
    Filter --> Format[ ]
    Format --> LLM[LLM  ]
    LLM --> Response[]
```

### 3.2   (retriever.py)

```python
def search(
    self, 
    query: str, 
    top_k: int = 5,
    chunk_types: Optional[List[str]] = None,
    agencies: Optional[List[str]] = None
) -> List[Dict]:
    """  """
    
    # 1.  
    query_embedding = self.embed_query(query)
    
    # 2. SQL  
    sql = """
        SELECT 
            c.chunk_uid,
            c.case_uid,
            c.chunk_type,
            c.text,
            cs.case_no,
            cs.decision_date,
            cs.agency,
            1 - (c.embedding <=> %s::vector) AS similarity
        FROM chunks c
        JOIN cases cs ON c.case_uid = cs.case_uid
        WHERE c.drop = FALSE
    """
    
    # 3.  (chunk_type, agency)
    if chunk_types:
        sql += f" AND c.chunk_type IN ({placeholders})"
    if agencies:
        sql += f" AND cs.agency IN ({placeholders})"
    
    # 4.   ( )
    sql += """
        ORDER BY c.embedding <=> %s::vector
        LIMIT %s
    """
    
    return results
```

** **:
- ****:   (HNSW )
- ****: chunk_type, agency 
- ****:    
- ****:   

### 3.3    (generator.py)

```python
def generate_answer(self, query: str, chunks: List[Dict]) -> Dict:
    """LLM   """
    
    # 1.  
    context = self.format_context(chunks)
    
    # 2.  
    system_prompt = """     . 
     " "        .
    
    **  :**
    1.       .
    2.       .
    3.   ,  ,    .
    4.     .
    5.     ,  "      " ."""
    
    # 3. LLM  (GPT-4o-mini)
    response = self.client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.3,
        max_tokens=1000
    )
    
    return response
```

** **:
- ****: GPT-4o-mini
- **Temperature**: 0.3 ( )
- ** **: 1000 
- ****:    

### 3.4 API  (main.py)

|  |  |  |
|-----------|--------|------|
| `/search` | POST | Vector  (LLM ) |
| `/chat` | POST | RAG    |
| `/chat/stream` | POST |    |
| `/case/{case_uid}` | GET |     |

####   

1. **  **
   ```sql
   -- HNSW  
   CREATE INDEX idx_chunks_embedding 
   ON chunks USING ivfflat(embedding vector_cosine_ops) 
   WITH (lists = 100);
   ```
   -   
   -   

2. ** **
   ```python
   def generate_answer_stream(self, query, chunks):
       """  """
       stream = self.client.chat.completions.create(
           model=self.model,
           messages=[...],
           stream=True
       )
       
       for chunk in stream:
           if chunk.choices[0].delta.content:
               yield chunk.choices[0].delta.content
   ```
   -   
   -   

3. ** **
   ```python
   def format_context(self, chunks: List[Dict]) -> str:
       """  LLM  """
       for idx, chunk in enumerate(chunks, 1):
           case_info = f"[ {idx}]"
           case_info += f" : {chunk['case_no']}"
           case_info += f", : {chunk['decision_date']}"
           case_info += f", : {agency_name}"
           
           context_parts.append(
               f"{case_info}\n"
               f"[{chunk_type_name}]\n"
               f"{chunk['text']}\n"
               f"(: {chunk['similarity']:.3f})\n"
           )
   ```
   -  
   -   

####    

1. **   **
   
   ** **:     
   
   ```python
   # : , ,    
   chunks = retriever.search(query=request.message, top_k=5)
   ```
   
   ****:
   -        
   -      
   -    
   
   ** **:   RAG 
   ```
   Stage 1:  +   
   Stage 2: Stage 1    
   Stage 3:     Fallback
   ```

2. **   **
   
   ** **:   
   
   ```python
   # :    
   agencies: Optional[List[str]] = None
   ```
   
   ****:
   -      
   - KCA, ECMC, KCDRC     
   
   ** **:   +    
   ```python
   def recommend_agency(user_input, search_results):
       #    ( )
       rule_scores = apply_keyword_rules(user_input)
       
       #    (   )
       result_scores = analyze_agency_distribution(search_results)
       
       #  (7:3 )
       final_scores = rule_scores * 0.7 + result_scores * 0.3
       
       return sorted_agencies(final_scores)
   ```

3. **Fallback  **
   
   ** **:
   ```python
   if not chunks:
       return ".      ."
   ```
   
   ****:
   -       
   -     
   
   ** **:
   -    
   -   
   -   

4. **  **
   
   ** **:   
   
   ```python
   class ChatRequest(BaseModel):
       message: str  #  
   ```
   
   ****:
   - , , ,      
   -   
   
   ** **:   
   ```python
   class StructuredUserInput(BaseModel):
       query: str  #  
       item: Optional[str]  # 
       amount: Optional[int]  # 
       purchase_date: Optional[date]  # 
       merchant: Optional[str]  # 
       issue_type: Optional[str]  #  
   ```

5. **   (Re-ranking) **
   
   ** **:    
   
   ```sql
   ORDER BY c.embedding <=> %s::vector
   LIMIT %s
   ```
   
   ****:
   -   
   - , ,     
   
   ** **:  
   ```python
   def rerank_chunks(chunks, user_query, user_context):
       for chunk in chunks:
           # 1.   (40%)
           semantic_score = chunk['similarity']
           
           # 2.   (20%)
           recency_score = calculate_recency(chunk['decision_date'])
           
           # 3.   (20%)
           agency_score = match_agency(chunk['agency'], user_context)
           
           # 4.    (20%)
           type_score = get_type_weight(chunk['chunk_type'])
           
           #  
           chunk['final_score'] = (
               semantic_score * 0.4 +
               recency_score * 0.2 +
               agency_score * 0.2 +
               type_score * 0.2
           )
       
       return sorted(chunks, key=lambda x: x['final_score'], reverse=True)
   ```

6. **   **
   
   ** **:   
   
   ****:
   -    
   -     
   
   ** **:    
   ```python
   # schema   
   def expand_context(chunk_id, window_size=1):
       return get_chunk_with_context(chunk_id, window_size)
   ```

---

##  4.  

### 4.1    ()

|  |  |
|------|-----|
|    | 550 |
|    | 100 |
|    | 700 |
|    | < 1% |

### 4.2    (embed_data_remote.py )

**  **:
-  Norm 
-   
-    (NaN/Inf)
-   

**  **: 5% 

### 4.3  

|  |  |
|------|-----|
|    | < 100ms (HNSW ) |
| Top-K | 5 () |
|   | 0.0 () |

---

##  5.   

### 5.1   

|   |   |   |  |
|----------|----------|----------|---------|
|    |  700 |   (500-800) |  |
|   | content  |    +   |  |
|    |   |  ,   |  |
| Overlapping |   |   +   |  |

### 5.2   

|   |   |   |  |
|----------|----------|----------|---------|
|   | KURE-v1 |   + Fallback |  |
|    |   |   +   |  |
|   |    |    +  |  |

### 5.3 RAG  

|   |   |   |  |
|----------|----------|----------|---------|
|   |   |   RAG |  |
|   |  |  +    |  |
| Fallback |  |  →    |  |
|   |  | //    |  |
|  |  |   |  |
|   |   |    |  |

** **:
- :    (   )
- :    ( )
- :    ( )

---

##  6.  

### Phase 1:   RAG  ()

****: / →   

** **: `backend/app/rag/multi_stage_retriever.py`

** **:
-   20-30% 
-      

### Phase 2:    ()

****:     

** **: `backend/app/rag/agency_recommender.py`

** **:
-    
-      

### Phase 3:   ()

****:   

** **: 
- `backend/scripts/data_processing/data_transform_pipeline.py`
- `backend/database/schema_v2_final.sql`

** **:
-  
-   

---

##  7. 

###  

1. **  **
   -   
   - Overlapping 
   -   
   -   

2. **  **
   -    
   -   

3. ** **
   - HNSW 
   -  
   -  

###   

1. **  **
   -   RAG
   -  
   - Fallback 

2. ** **
   -   
   -  

3. ** **
   -  
   -  
   - 

** **:   ** **  , **  ** ** **  **  **

---

** **:   RAG    
