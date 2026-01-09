#  

****: 2026-01-07  
****: v1.0

---

## 

       .

---

##  

```
tests/
 README.md                       #  
 unit/                           #  
    test_vector_db_schema.py    # Vector DB  
    test_chunking_quality.py    #   
    test_api.py                 # FastAPI  
 integration/                    #  
    test_rag.py                 # RAG   
    test_rag_v2.py              # RAG V2  
 rag/                            # RAG  
     test_agency_recommender.py  #   
     test_agency_with_real_data.py  #     
     test_multi_stage_rag.py     #   RAG 
     test_rag_simple.py          #  RAG 
     test_search_quality.py     #   
     test_similarity_search.py  #   
```

---

##  

###  

#### Vector DB  

```bash
cd /home/maroco/ddoksori_demo
conda activate ddoksori
python tests/unit/test_vector_db_schema.py
```

** **:
-    (< 500ms)
-    (100%)
-    (< 100ms)
- JSONB   (< 200ms)
-   (  < 20%)

####   

```bash
cd /home/maroco/ddoksori_demo
conda activate ddoksori
python tests/unit/test_chunking_quality.py
```

** **:
-    
-    (70% )
-   
-   
- /  

#### API 

```bash
cd /home/maroco/ddoksori_demo
conda activate ddoksori
python tests/unit/test_api.py
```

** **:
-  
-  API
-  API

###  

#### RAG   

```bash
cd /home/maroco/ddoksori_demo
conda activate ddoksori
python tests/integration/test_rag.py
python tests/integration/test_rag_v2.py
```

** **:
- Vector DB  
- LLM  
-   

### RAG  

####   RAG 

```bash
cd /home/maroco/ddoksori_demo
conda activate ddoksori
python tests/rag/test_multi_stage_rag.py
```

** **:
-   
-    
-   
-   

####   

```bash
python tests/rag/test_agency_recommender.py
python tests/rag/test_agency_with_real_data.py
```

---

##  

    `/tmp/`  JSON  :

- `/tmp/vector_db_test_results.json`
- `/tmp/chunking_quality_test_results.json`

---

##  

- Python 3.11+
- Conda : `ddoksori`
- PostgreSQL 16  
-   

---

##  

### PostgreSQL  

```bash
# DB  
docker ps | grep ddoksori_db

# DB 
docker-compose restart db
```

### Conda   

```bash
#  
conda env list

#  
conda activate ddoksori
```

---

##  

- [`docs/technical/vector_db___.md`](../docs/technical/vector_db___.md)
- [`docs/technical/___.md`](../docs/technical/___.md)
