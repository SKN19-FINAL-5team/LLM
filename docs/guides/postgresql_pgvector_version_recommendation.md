# PostgreSQL  pgvector   

****: 2026-01-08  
****:    PostgreSQL  pgvector   

---

##  

1. [  ](#--)
2. [PostgreSQL   (16 vs 17)](#postgresql---16-vs-17)
3. [pgvector  ](#pgvector--)
4. [    ](#----)

---

##   

###    

- **PostgreSQL**: 16.11 (pgvector/pgvector:pg16 Docker )
- **pgvector**: 0.8.1 (  )

###  

- ** **: pgvector,   
- ****:    
- ** **: RAG      

---

## PostgreSQL   (16 vs 17)

### PostgreSQL 16

####  
- ****: 2023 9 14
- **  **: 16.11 (2025 )
- ** **: 2028 11 14 (5 )

####  
- **   **: `pg_stat_io`   I/O  
- ** **:   ,   
- **  **:    
- **SQL **: `SQL/JSON`    

#### 
1. ** **
   -   2   
   -     
   -       

2. **pgvector  **
   - pgvector 0.8.x   
   - IVFFlat  HNSW    
   -    

3. **    **
   -  PostgreSQL   
   -     
   -   

4. **   **
   -     
   -    
   -    

#### 
1. **  **
   - PostgreSQL 17    
   -     

2. ** **
   - 2028    
   -   

### PostgreSQL 17

####  
- ****: 2024 9 12
- **  **: 17.x (2025 )
- ** **: 2029 11 13 (5 )

####  
- **  **:   ,   
- **  **: `pg_stat_statements` 
- **  **:      
- ****:       

#### 
1. ** **
   -     
   -   
   -   

2. ** **
   - 2029  
   -    

3. ** **
   -    
   -   

#### 
1. **  **
   -    1   
   -     
   -    

2. **pgvector  **
   - pgvector    
   -      
   -    

3. ** **
   -        
   -     

4. ** **
   -     
   -    

---

## pgvector  

###    
- **pgvector**: 0.8.1

### pgvector 0.8.x 

####  
- **0.8.0**: 2024 11 11 
- **0.8.1**: 2025  (  )
- ** PostgreSQL **: 13 ~ 19

####  
- **  **: WHERE         
- **HNSW  **:     
- **  **:       

#### 
1. **PostgreSQL 16  **
   - PostgreSQL 16  
   - IVFFlat  HNSW   

2. ** **
   -     
   - HNSW   

3. ****
   -     
   -     

#### 
1. **PostgreSQL 17 **
   - PostgreSQL 17  
   -     

2. **  **
   -   pgvector 0.9.x    

---

##     

###   

####  1: PostgreSQL 16 + pgvector 0.8.1 ( )  ****

** **:
1. ** **: pgvector  
2. ****:    
3. ** **:       
4. ****:      

****:
-     
-  pgvector  
-      
-       

****:
-  PostgreSQL 17    
-  2028   

** **:
-     
- pgvector  RAG  
-     

####  2: PostgreSQL 17 + pgvector 0.8.1 ( )

** **:
1. ** **: PostgreSQL 17    
2. ** **:    

****:
-      
-      (2029)

****:
-      
-     
-     

** **:
-    
-     
-    

---

##  

### PostgreSQL 16 → 17 

####  
1. ****:    
2. ** **:    
3. **pgvector  **: pgvector 0.8.1 PostgreSQL 17   
4. ** **:     PostgreSQL 17  

####  
1. **  **
   ```bash
   # PostgreSQL 17 Docker  
   docker run -d --name test_pg17 \
     -e POSTGRES_PASSWORD=postgres \
     -p 5433:5432 \
     pgvector/pgvector:pg17
   ```

2. ** **
   ```bash
   # pg_dump 
   pg_dump -h localhost -U postgres -d ddoksori > backup.sql
   
   # PostgreSQL 17 
   psql -h localhost -p 5433 -U postgres -d ddoksori < backup.sql
   ```

3. ****
   -    
   -    
   -   

#### 
-       
-    
-    

---

##   

###   

**PostgreSQL 16 + pgvector 0.8.1 ** 

****:
1. ****: pgvector  
2. ****:    
3. ****:     
4. ****:    

###  

1. **PostgreSQL 17  **
   - PostgreSQL 17    (2025  )
   -     
   -      

2. **pgvector **
   - pgvector 0.9.x    
   -    
   -     

---

##  

- [PostgreSQL  ](https://www.postgresql.org/docs/)
- [pgvector GitHub](https://github.com/pgvector/pgvector)
- [PostgreSQL   ](https://www.postgresql.org/support/versioning/)
- [pgvector  ](https://github.com/pgvector/pgvector#installation)

---

****: 2026-01-08
