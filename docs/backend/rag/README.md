# RAG 

  RAG (Retrieval-Augmented Generation) .

##   

```
app/rag/
 __init__.py                    #  
 retriever.py                   #   
 generator.py                   # LLM  
 multi_stage_retriever.py       #    ()
 agency_recommender.py          #    ()
```

##   

### 1. `VectorRetriever` (retriever.py)
     .

** :**
-    (KURE-v1)
-    (pgvector)
-     

### 2. `RAGGenerator` (generator.py)
   LLM  .

** :**
-  
- OpenAI GPT   
-   

### 3. `MultiStageRetriever` (multi_stage_retriever.py)  
3       .

** :**
- Stage 1:  +   
- Stage 2:   ( )
- Stage 3:   (Fallback)
-    

** :**
```
 
    ↓
Stage 1:  +   ()
    ↓
Stage 2:   ( )
    ↓
 ? → No → Stage 3:  (Fallback)
    ↓ Yes
  +  
    ↓
 
```

### 4. `AgencyRecommender` (agency_recommender.py)  
        .

** :**
-   (  +  )
-    
-    
-   

** :**
- `kca`:  ( , )
- `ecmc`:  ( )
- `kcdrc`:  ( )

##   

###   (VectorRetriever)

```python
from app.rag import VectorRetriever

db_config = {...}
retriever = VectorRetriever(db_config)

# 
chunks = retriever.search(
    query=" .    ?",
    top_k=5,
    chunk_types=['decision', 'judgment'],
    agencies=['kca']
)

retriever.close()
```

###    (MultiStageRetriever)

```python
from app.rag import MultiStageRetriever

retriever = MultiStageRetriever(db_config)

#   
results = retriever.search_multi_stage(
    query="     .",
    law_top_k=3,
    criteria_top_k=3,
    mediation_top_k=5,
    enable_agency_recommendation=True
)

#  
print(f" : {len(results['all_chunks'])}")
print(f" : {results['agency_recommendation']['top_agency']}")
print(f"Fallback : {results['used_fallback']}")

retriever.close()
```

###   (AgencyRecommender)

```python
from app.rag import AgencyRecommender

recommender = AgencyRecommender()

# 
recommendations = recommender.recommend(
    user_input="     .",
    search_results=chunks  # 
)

#  
top_agency, info = recommender.get_top_agency(user_input, chunks)
print(f"{info['name']} - {info['contact']}")

#  
formatted = recommender.format_recommendations(recommendations)
print(formatted)
```

###   (RAGGenerator)

```python
from app.rag import RAGGenerator

generator = RAGGenerator()

#  
result = generator.generate_answer(
    query="   ?",
    chunks=chunks
)

print(result['answer'])
print(f" : {result['chunks_used']}")
```

##  :  vs  

|  |   |    |
|------|----------|------------------|
|   | 1 | 3 () |
|   |   |  →  →  |
|   |  |  (Stage 1 → Stage 2) |
| Fallback |  |  (  ) |
|   |  |  () |
|   |  |  |
|   |  (~1) |  (~2-3) |

##  

###   RAG 

```bash
cd /home/maroco/ddoksori_demo/backend
conda activate ddoksori
python tests/rag/test_multi_stage_rag.py
```

** :**
-  
-   
-  
-  

###  

```bash
python scripts/analytics/analyze_rag_results.py
```

** :**
-   
-  
-   
-  
-  

##   

- [  RAG  ](../../rag/docs/multi_stage_rag_usage.md)
- [   ](../../rag/docs/___.md)

##   

- [ ] FastAPI  
- [ ]  UI 
- [ ]    
- [ ]   ( + )
- [ ]   
