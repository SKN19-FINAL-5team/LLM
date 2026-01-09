#      

****: 2026-01-09  
** **:   RAG  

---

## 1.   

###  

#### 1.1    
```
relation "chunks" does not exist
LINE 13:             FROM chunks c
```

****:  `chunks`   

#### 1.2   
```
current transaction is aborted, commands ignored until end of transaction block
```

****:     PostgreSQL        

###  

1. **  **: `documents` `chunks`   
2. **  **:       (616 bytes, pgvector  )
3. ** **: Docker      

---

## 2.    

### Docker  
-    : `ddoksori_db` (Up 54 minutes, healthy)
-   : `0.0.0.0:5432->5432/tcp`

###   
-  `documents` :  
-  `chunks` :  
-  `pgvector` :  ( 0.8.1)

###   
-  `documents`  :    
-  `chunks`  :    
-   :    

###    
- ** **: `backend/scripts/database/vectordb_backups/ddoksori_vectordb_20260108_234218.sql.gz`
- ** **: 616 bytes ( )
- **  **: 54
- **  **:  CREATE TABLE  
- **  **:  INSERT INTO  
- ** **: pgvector  

****:       ,   .

---

## 3.    

### `export_vectordb.sh` 
- ****: `pg_dump`     
- ** **:  +  +  (  )
- ****: 
  -      
  -      

### `import_vectordb.sh` 
- ****: 
  1.  
  2.    (`DROP SCHEMA public CASCADE`)
  3. SQL  
  4.   (documents, chunks  )
- ****:
  1.         
  2.     
  3.     
  4.      

---

## 4.  

###  1:      ()

#### 4.1  
```bash
#   
cd /home/maroco/LLM

# Docker   
docker exec -i ddoksori_db psql -U postgres -d ddoksori < backend/database/schema_v2_final.sql
```

#### 4.2    
```bash
#   
conda run -n dsr python backend/scripts/embedding/embed_data_remote.py
```

   API :
```bash
#  API   
conda run -n dsr python backend/scripts/embedding/embed_data_remote.py
```

###  2:     (  )

        .

###  3:     

   ,    .

---

## 5.   

### 5.1    (`export_vectordb.sh`)

1. **    **
   ```bash
   #    (: 1KB )
   MIN_SIZE=1024
   if [ $(stat -f%z "$COMPRESSED_FILE" 2>/dev/null || stat -c%s "$COMPRESSED_FILE") -lt $MIN_SIZE ]; then
       echo "  :    .    ."
   fi
   ```

2. **   **
   ```bash
   # CREATE TABLE  
   if ! gunzip -c "$COMPRESSED_FILE" | grep -q "CREATE TABLE"; then
       echo "  :     ."
   fi
   ```

3. **   **
   ```bash
   # INSERT  
   if ! gunzip -c "$COMPRESSED_FILE" | grep -q "INSERT INTO"; then
       echo "  :    ."
   fi
   ```

### 5.2    (`import_vectordb.sh`)

1. **   **
   ```bash
   #   
   FILE_SIZE=$(stat -f%z "$DUMP_FILE" 2>/dev/null || stat -c%s "$DUMP_FILE")
   if [ "$FILE_SIZE" -lt 1024 ]; then
       echo " :    . ($FILE_SIZE bytes)"
       echo "          ."
       exit 1
   fi
   
   #    
   if ! grep -q "CREATE TABLE" "$SQL_FILE"; then
       echo "  :     ."
       read -p "  ? (yes/no): " CREATE_SCHEMA
       if [ "$CREATE_SCHEMA" == "yes" ]; then
           # schema_v2_final.sql 
           docker exec -i "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" < "$PROJECT_ROOT/backend/database/schema_v2_final.sql"
       fi
   fi
   ```

2. **  **
   ```bash
   #      
   set +e  #    
   #  
   set -e  #    
   ```

3. **   **
   ```bash
   #    
   if ! docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "\dt" | grep -q "documents"; then
       echo " : documents   ."
       exit 1
   fi
   ```

### 5.3    (`test_multi_stage_rag.py`)

1. **      **
   ```python
   def check_database_schema(self, db_config):
       """  """
       conn = psycopg2.connect(**db_config)
       cur = conn.cursor()
       
       #   
       cur.execute("""
           SELECT EXISTS (
               SELECT FROM information_schema.tables 
               WHERE table_schema = 'public' 
               AND table_name = 'chunks'
           );
       """)
       chunks_exists = cur.fetchone()[0]
       
       cur.execute("""
           SELECT EXISTS (
               SELECT FROM information_schema.tables 
               WHERE table_schema = 'public' 
               AND table_name = 'documents'
           );
       """)
       documents_exists = cur.fetchone()[0]
       
       cur.close()
       conn.close()
       
       if not chunks_exists or not documents_exists:
           raise RuntimeError(
               "   . "
               "   :\n"
               "docker exec -i ddoksori_db psql -U postgres -d ddoksori < backend/database/schema_v2_final.sql"
           )
   ```

2. **  **
   ```python
   # retriever.py search 
   try:
       with self.conn.cursor() as cur:
           cur.execute(sql, params)
           rows = cur.fetchall()
   except psycopg2.Error as e:
       self.conn.rollback()  #  
       raise
   ```

---

## 6.     

###  

1. ** **
   ```bash
   cd /home/maroco/LLM
   docker exec -i ddoksori_db psql -U postgres -d ddoksori < backend/database/schema_v2_final.sql
   ```

2. **  **
   ```bash
   docker exec ddoksori_db psql -U postgres -d ddoksori -c "\dt"
   ```

3. **   ** (   )
   ```bash
   conda run -n dsr python backend/scripts/embedding/embed_data_remote.py
   ```

4. ** **
   ```bash
   docker exec ddoksori_db psql -U postgres -d ddoksori -c "SELECT COUNT(*) FROM documents;"
   docker exec ddoksori_db psql -U postgres -d ddoksori -c "SELECT COUNT(*) FROM chunks;"
   ```

5. ** **
   ```bash
   conda run -n dsr python -m tests.rag.test_multi_stage_rag
   ```

---

## 7. 

### 
1.  `documents` `chunks`  
2.        
3.       

###  
1.   (`schema_v2_final.sql` )
2.     (`embed_data_remote.py` )
3. /   (  )

###  
-      
-     
-       
