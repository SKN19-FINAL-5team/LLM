# RAG     

##  

  RAG            .

##  test_multi_stage_rag.py

### 

4    RAG   :

1. ** ** ( ) -  
2. **  ** ( ) -  
3. ** ** ( ) -  
4. ** ** ( ) -  

###  

-  ** **:    
-  **  **:    
-  **  **:    
-  ** **:   
-  ** **:  ,   ,  

###  

1.      
2.    
3. Conda  `ddoksori` 

### 

#### 1.    

```bash
# Conda  
conda activate ddoksori

#  
python tests/rag/test_multi_stage_rag.py
```

#### 2.    

```bash
# TC001:   
python tests/rag/test_multi_stage_rag.py --test-id TC001

# TC002:    
python tests/rag/test_multi_stage_rag.py --test-id TC002

# TC003:   
python tests/rag/test_multi_stage_rag.py --test-id TC003

# TC004:   
python tests/rag/test_multi_stage_rag.py --test-id TC004
```

#### 3.    

```bash
python tests/rag/test_multi_stage_rag.py --no-save
```

#### 4.    

```bash
python tests/rag/test_multi_stage_rag.py --output-dir ./my_results
```

###  

####  

     :

1. ** **:  ,  ,   
2. **  **:
   -      
   - /  
   -  3  
   -      
   - LLM  
3. ** **:
   -   (/ )
   -   
   -   ( ,   )
   -    

#### JSON  

    :

```
backend/evaluation/results/rag_test_results_YYYYMMDD_HHMMSS.json
```

JSON  :

```json
{
  "summary": {
    "timestamp": "2026-01-06T...",
    "total_tests": 4,
    "successful_tests": 4,
    "failed_tests": 0,
    "agency_accuracy": 75.0,
    "avg_metrics": {
      "search_time": 0.523,
      "answer_time": 2.145,
      "total_time": 2.668,
      "keyword_match_rate": 0.83,
      "avg_similarity": 0.7234
    }
  },
  "test_results": [
    {
      "test_case_id": "TC001",
      "test_case_name": "  ( )",
      "success": true,
      "recommended_agency": "kca",
      "agency_match": true,
      "keyword_match_rate": 0.85,
      "stages": {
        "full_search": {
          "chunks_count": 10,
          "agency_distribution": {...},
          "avg_similarity": 0.7456
        }
      },
      "answer": {
        "text": "...",
        "generation_time": 2.1
      },
      "metrics": {...}
    }
  ]
}
```

###   

#### TC001:   ( )

- ****: 3      
- ** **:  (kca)
- ** **: , , , , 

#### TC002:    ( )

- ****:     2  
- ** **:  (ecmc)
- ** **: , , , , 

#### TC003:   ( )

- ****:  1    3  
- ** **:  (kca)
- ** **: , , , , 

#### TC004:   ( )

- ****:     
- ** **:  (kcdrc)
- ** **: , , , , 

###  

#### : "  "

```bash
#    
python backend/scripts/embedding/embed_data_remote.py
```

#### : "  "

`.env`    :

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ddoksori
DB_USER=postgres
DB_PASSWORD=postgres
```

#### : "OpenAI API  "

`.env`  OpenAI API  :

```env
OPENAI_API_KEY=sk-...
```

###  

     .      :

-  **  **:  →  →   
-  **Fallback **:    
-  **  **:   +    

##    

###   

-    : **75% **
-   : **0.65 **
-   : **80% **
-   : **1 **
-    : **5 **

###   

-     50%  →     
-    0.5  →      
-    2  →   

##  

       .
