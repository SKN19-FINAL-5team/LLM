#   RAG 

##   

### test_multi_stage_rag.py

  RAG  4   .

** :**
1.   ( )
2.    ( )
3.   ( )
4.   ( )

##   

### 1.  

```bash
# Conda  
conda activate ddoksori

#   
cd /home/maroco/ddoksori_demo/backend
```

### 2.   

`.env`     :

```bash
#  
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ddoksori
DB_USER=postgres
DB_PASSWORD=your_password

#  
EMBEDDING_MODEL=nlpai-lab/KURE-v1

# OpenAI API ( )
OPENAI_API_KEY=your_api_key
```

### 3.  

```bash
#   RAG  
python tests/rag/test_multi_stage_rag.py
```

** :**
-     
- Stage    
-   
-   (, )
- `test_results.json`  

### 4.  

```bash
#    (test_results.json )
python scripts/analytics/analyze_rag_results.py
```

** :**
-    
-  
-   
-  
-  

##   

###   

```
================================================================================
     RAG   
================================================================================

  :
  - DB Host: localhost
  - DB Name: ddoksori
  -   : 4
   

================================================================================
   1:   ( )
================================================================================

**:**    3    .    ?
...

[Stage 1]     ...
  - : 3
  - : 3

[Stage 2]   ...
  - : 5

[Agency Recommendation]   ...
  -  :  (: 0.85)

  


   :
  -   : 11
  - : 5
  - Fallback : 

  :
  -  : 0.742

  :
  -  : ecmc ( )
  -  : 0.850
```

##   

### : "ModuleNotFoundError: No module named 'app'"

**:** Python   

**:**
```bash
# backend   
cd /home/maroco/ddoksori_demo/backend
python tests/rag/test_multi_stage_rag.py
```

### : "psycopg2.OperationalError: could not connect to server"

**:** PostgreSQL   

**:**
1. PostgreSQL   
2. `.env`  DB  
3. DB   

### : "No chunks found"

**:**    

**:**
```bash
#    (   )
python scripts/embedding/embed_data_remote.py
```

### : "Fallback "

**:**   ( )

**:** 
- Stage 3 Fallback  2     
-    

##   

### 1.   
- :  2-3
- :  2-3
- :  3-5
- ** :  8-12**

### 2. 
-  : **0.6-0.8** ()
-  : 0.5

### 3.   
- : **75% **
- : 100%

### 4. 
-   : **2-3** ()
-  : 5

##   

### test_results.json

     JSON  :

```json
[
  {
    "test_id": 1,
    "test_name": "  ( )",
    "total_chunks": 11,
    "law_chunks": 3,
    "criteria_chunks": 3,
    "mediation_chunks": 5,
    "counsel_chunks": 0,
    "used_fallback": false,
    "recommended_agency": "ecmc",
    "agency_correct": true,
    "agency_score": 0.85,
    "avg_similarity": 0.742,
    "max_similarity": 0.891,
    "min_similarity": 0.623,
    "elapsed_time": 2.34,
    "timestamp": "2026-01-06T..."
  },
  ...
]
```

##   

- [  RAG  ](../../rag/docs/multi_stage_rag_usage.md)
- [RAG  README](../../app/rag/README.md)
