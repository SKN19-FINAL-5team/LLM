#   

## 

  JSONL      KURE-v1   , PostgreSQL + pgvector .

##  

1. **PostgreSQL + pgvector **
   ```bash
   docker-compose up -d postgres
   ```

2. **  **
   
   `backend/.env`     :
   ```
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=ddoksori
   DB_USER=postgres
   DB_PASSWORD=postgres
   ```

3. **Python  **
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

##  

```bash
cd backend
python scripts/embed_data.py
```

##  

1. ** **: KURE-v1   Hugging Face 
2. ** **: `database/schema_v2_final.sql`   
3. ** **: `data/`   `.jsonl`  
4. **Cases **:   `cases`  
5. **Chunks   **: 
   -    KURE-v1  (1024)
   -    `chunks`  
6. ****:    

##  

### Cases 
- `case_uid`:   ID
- `case_no`: 
- `decision_date`: 
- `agency`:   (kca, ecmc, kcdrc)
- `source`:  

### Chunks 
- `chunk_uid`:   ID
- `case_uid`:   ID
- `chunk_type`:   (decision, parties_claim, judgment)
- `text`:  
- `embedding`: KURE-v1   (1024)

##   

-  3,358  
- GPU  :  5-10
- CPU  :  20-30

##  

### pgvector  
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

###  
  :
```python
pipeline.embed_and_insert_chunks(records, batch_size=16)
```

### KURE-v1   
Hugging Face   :
```bash
export HF_TOKEN=your_token_here
```
