#   - RAG     

****: 2026-01-05  
****: v2.0  
****: PR #4 -    

---

##  

1. [ ](#-)
2. [ ](#-)
3. [ ](#-)
4. [  ](#--)
5. [RAG  ](#rag--)
6. [](#)

---

##   

### 

```

                    RAG  v2                        

                                                         
  [ ]                                          
      (13 , 5,455 )                      
      (3 , 13,544 )              
      (4 , 11,755 )              
                                                         
  [ ]                                    
     KURE-v1  (768)                           
       (32/)                            
     RunPod GPU  ( API)                       
                                                         
  []                                         
     PostgreSQL + pgvector                            
     documents  ()                    
     chunks  ( + )                    
     chunk_relations  (  )            
                                                         
  [ ]                                          
       ( )                        
       ( )                          
       ( + )                  
        (  )            
       (  )                   
                                                         

```

###   

1. ** **: 3     
2. **  **: (article), (question/answer), (overview/claim/decision)
3. **  **: next/prev   
4. **  **: , , ,    
5. ** **:      

---

##   

### 1.   

`.env`       :

```bash
#  
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ddoksori
DB_USER=postgres
DB_PASSWORD=postgres

#  API  (RunPod  )
EMBED_API_URL=http://localhost:8001/embed

# OpenAI API (LLM  ,  )
OPENAI_API_KEY=your_openai_api_key_here
```

### 2. Python  

```bash
cd backend
pip install -r requirements.txt
```

** **:
- `psycopg2-binary`: PostgreSQL 
- `python-dotenv`:   
- `requests`: HTTP  ( API)
- `tqdm`:   

### 3. Docker Compose 

PostgreSQL  Docker :

```bash
cd /path/to/ddoksori_demo
docker-compose up -d
```

  :

```bash
docker exec -it ddoksori_db psql -U postgres -d ddoksori -c "SELECT version();"
```

---

##   

### 1.  

** ** (     ):
```bash
cd backend
python scripts/embed_pipeline_v2.py
```

** ** ():
```bash
docker exec -i ddoksori_db psql -U postgres -d ddoksori < database/schema_v2_final.sql
```

### 2.   

```bash
docker exec -it ddoksori_db psql -U postgres -d ddoksori
```

```sql
--   
\dt

--   
\d documents
\d chunks
\d chunk_relations

--  
\dv

--  
\df
```

---

##    

###  1:   ( API )

   :

```bash
cd backend
python scripts/embed_pipeline_v2.py
```

****:    , `embedding`  NULL .

###  2: RunPod GPU  ()

#### 2-1. RunPod  

1. RunPod  SSH 
2.   :

```bash
# RunPod 
cd /workspace
pip install fastapi uvicorn sentence-transformers torch

#    ()
scp backend/runpod_embed_server.py [user]@[runpod_ip]:/workspace/

#   (RunPod)
uvicorn runpod_embed_server:app --host 0.0.0.0 --port 8000
```

#### 2-2. SSH  

 PC   :

```bash
ssh -L 8001:localhost:8000 [user]@[runpod_ip] -p [port]
```

#### 2-3.   

 PC:

```bash
cd backend
export EMBED_API_URL=http://localhost:8001/embed
python scripts/embed_pipeline_v2.py
```

###  

```
============================================================
  -   v2
============================================================

[1/6]  API  : http://localhost:8001/embed
 API  : {'message': 'Embedding server is running', 'device': 'cuda'}

[2/6] PostgreSQL  ...
   

[3/6]   : .../schema_v2_final.sql
   

[4/6]    ...
     : 13
    :  13,  5455

[4/6]    ...
     : 3
   :  6772,  13544

[4/6]    ...
     : 4
   :  3918,  11755

[5/6]    : 10703
    

[6/6]     : 30754
  : 100%|| 962/962 [15:23<00:00]
     

[]     ...
     

============================================================
 
============================================================
                                  
------------------------------------------------------------
law             statute         13      5455       450.2       5455
counsel_case    KCA           6772     13544       320.5      13544
mediation_case  KCA           2500      7500       380.1       7500
mediation_case  ECMC           800      2400       370.8       2400
mediation_case  KCDRC          618      1855       365.3       1855
============================================================

   !
```

---

##  RAG  

### 1.  

```bash
cd /home/maroco/LLM
python tests/integration/test_rag_v2.py
```

### 2.   

```
============================================================
  - RAG   v2
============================================================

  :
1.   (6 )
2.   ( )

 (1  2): 
```

### 3.   

####  1:    
- ****: "   .    ?"
- ****:  +  

####  2:   
- ****: "   ?"
- ****:   

####  3:   
- ****: "     ?"
- ****:  

####  4:   
- ****: "   ?"
- ****:  (  )

####  5:   
- ****: "   ?"
- ****:  + 

####  6:  
- ****: "    ?"
- ****:  + 

### 4.  

    :

- ****:       
- ****:     
- **  **:      

---

##  

###  1: `psycopg2.OperationalError: could not connect to server`

****: PostgreSQL   

****:
```bash
docker-compose up -d
docker ps  #   
```

###  2: `requests.exceptions.ConnectionError: Connection refused`

****:  API   

****:
1. RunPod  `uvicorn`  
2. SSH   
3.  `curl http://localhost:8001/` 

###  3: `psycopg2.errors.UndefinedTable: relation "documents" does not exist`

****:    

****:
```bash
docker exec -i ddoksori_db psql -U postgres -d ddoksori < backend/database/schema_v2_final.sql
```

###  4:    

****:   GPU  

****: `embed_pipeline_v2.py` `batch_size` 
```python
pipeline.embed_and_insert_chunks(all_chunks, batch_size=64)  #  32 → 64
```

###  5: `ERROR: extension "vector" does not exist`

****: pgvector   

****:
```bash
docker exec -it ddoksori_db psql -U postgres -d ddoksori -c "CREATE EXTENSION vector;"
```

---

##    

### SQL  

```sql
--  
SELECT * FROM v_data_statistics;

--  
SELECT doc_type, COUNT(*) FROM documents GROUP BY doc_type;

--  
SELECT d.doc_type, COUNT(c.chunk_id) 
FROM chunks c 
JOIN documents d ON c.doc_id = d.doc_id 
GROUP BY d.doc_type;

--  
SELECT 
    d.doc_type,
    COUNT(c.chunk_id) AS total_chunks,
    COUNT(c.embedding) AS embedded_chunks,
    ROUND(COUNT(c.embedding)::numeric / COUNT(c.chunk_id) * 100, 2) AS completion_rate
FROM chunks c
JOIN documents d ON c.doc_id = d.doc_id
GROUP BY d.doc_type;
```

---

##   

1.    
2.     
3.  RAG   
4. ⏭ **PR #4**:    
5. ⏭ **PR #5**: LLM    
6. ⏭ **PR #6**:   

---

##   

- [RAG  ](../rag_improvement_proposal.md)
- [  ](../data_analysis_report.md)
- [RunPod GPU  ](../runpod_comprehensive_guide.md)
- [ ](../mas_chatbot_project_plan.md)

---

****: RAG    
** **: 2026-01-05
