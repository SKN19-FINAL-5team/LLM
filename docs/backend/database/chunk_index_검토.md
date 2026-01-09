# chunk_index  

****: 2026-01-06  
****:      chunk_index    
****:  **HIGH** -       

---

##   

###  : chunk_index    

|  | chunk_index  |   |  |
|-----|-----------------|--------|------|
| **compensation_case** |   | **0** |  0-based () |
| **table2 (criteria)** |   (row_idx ) | **1** |  1-based |
| **kca_final** |   (case_index  ) | **1** |  1-based |
| **ecmc** |   (seq 1 ) | **1** |  1-based |
| **law** |   (unit_id ) | N/A |    |

---

##    

### 1. compensation_case () 

```json
{
  "chunk_index": 0,      //  0-based
  "chunk_total": 1,
  "doc_id": "consumer.go.kr:consumer_counsel_case:53321"
}
```

****:   (0-based)  
****:  

---

### 2. criteria/table2 () 

```json
{
  "row_idx": 1,          //  1-based (1~126)
  "chunk_id": "table2_row_p1_...",
  "text": "..."
}
```

****:
- `chunk_index`  
- `row_idx` 1  (1-based)
-  126 row: 1, 2, 3, ..., 126

** **:
```python
#   0-based 
chunk_index = row_idx - 1  # 1 → 0, 2 → 1, 3 → 2, ...
```

---

### 3. dispute_resolution/kca_final 

```json
{
  "case_index": 1,       //     (case 1, 2, 3...)
  "case_no": "201527",
  "chunk_type": "decision"
}
```

****:
- `chunk_index`  
- `case_index` ** **   
-  case_no   (decision, parties_claim, judgment)

** **:
```python
# case_no     
chunks_by_case = {}
for item in data:
    case_no = item['case_no']
    if case_no not in chunks_by_case:
        chunks_by_case[case_no] = []
    chunks_by_case[case_no].append(item)

#   0  
for case_no, chunks in chunks_by_case.items():
    for idx, chunk in enumerate(chunks):
        chunk['chunk_index'] = idx  # 0, 1, 2, ...
        chunk['chunk_total'] = len(chunks)
```

---

### 4. dispute_resolution/ecmc 

```json
{
  "seq": 1,              //  1-based
  "case_index": 1,       //   
  "case_no": "CA09-02073",
  "chunk_type": "decision"
}
```

****:
- `chunk_index`  
- `seq` 1 
- `case_index`  

** **:
```python
# case_no   0-based  
# (kca_final  )
```

---

### 5. law () 

```json
{
  "unit_id": "001706|A1",
  "law_id": "001706",
  "law_name": ""
}
```

****:
- `chunk_index`  
-      

** **:
```python
# law_id   0-based  
chunks_by_law = {}
for item in data:
    law_id = item['law_id']
    if law_id not in chunks_by_law:
        chunks_by_law[law_id] = []
    chunks_by_law[law_id].append(item)

for law_id, chunks in chunks_by_law.items():
    for idx, chunk in enumerate(chunks):
        chunk['chunk_index'] = idx
        chunk['chunk_total'] = len(chunks)
```

---

##       

###  1: CHECK   

```python
#   
INSERT INTO chunks (chunk_id, doc_id, chunk_index, chunk_total, ...)
VALUES ('...', '...', 1, 3, ...)  -- chunk_index 1 

# CHECK (chunk_index < chunk_total) !
# chunk_index=1, chunk_total=3    chunk_index=2 
# 1-based  chunk_index=3   
```

** **:
```
psycopg2.errors.CheckViolation: new row for relation "chunks" violates check constraint "chunks_chunk_index_check"
DETAIL: Failing row contains (..., chunk_index=3, chunk_total=3, ...)
```

###  2: UNIQUE   

```python
#     
#  doc_id  chunk_index   

INSERT INTO chunks (doc_id, chunk_index, ...) VALUES ('doc1', 0, ...)
INSERT INTO chunks (doc_id, chunk_index, ...) VALUES ('doc1', 0, ...)  -- !

# UNIQUE(doc_id, chunk_index) !
```

** **:
```
psycopg2.errors.UniqueViolation: duplicate key value violates unique constraint "chunks_doc_id_chunk_index_key"
DETAIL: Key (doc_id, chunk_index)=(doc1, 0) already exists.
```

###  3:    

```python
# 10,000   5,234  
# →   
# →     (5,233 !)
```

**  **:
- : 5,000  × 0.5 = **~42** 
- GPU : RunPod   **$3~5** 
-  :    

---

##   

### 1.      

```python
class DataTransformer:
    """  0-based chunk_index """
    
    def _assign_chunk_indices(self, chunks: List[dict]) -> List[dict]:
        """
          0-based  
        
        Args:
            chunks:    
        
        Returns:
            chunk_index, chunk_total   
        """
        total = len(chunks)
        for idx, chunk in enumerate(chunks):
            chunk['chunk_index'] = idx  # 0, 1, 2, ...
            chunk['chunk_total'] = total
        return chunks
    
    def transform_law_data(self, file_path):
        """   - 0-based  """
        chunks_by_law = {}
        
        with open(file_path, 'r') as f:
            for line in f:
                data = json.loads(line)
                law_id = data['law_id']
                
                if law_id not in chunks_by_law:
                    chunks_by_law[law_id] = []
                chunks_by_law[law_id].append(data)
        
        #   0-based  
        for law_id, chunks in chunks_by_law.items():
            chunks = self._assign_chunk_indices(chunks)
            self._insert_chunks(f"statute:{law_id}", chunks)
    
    def transform_criteria_table2(self, file_path):
        """   - row_idx 0-based """
        chunks = []
        
        with open(file_path, 'r') as f:
            for line in f:
                data = json.loads(line)
                chunks.append(data)
        
        # 0-based   (row_idx )
        chunks = self._assign_chunk_indices(chunks)
        self._insert_chunks('criteria:table2', chunks)
    
    def transform_mediation_kca(self, file_path):
        """  - case_no 0-based  """
        chunks_by_case = {}
        
        with open(file_path, 'r') as f:
            for line in f:
                data = json.loads(line)
                case_no = data['case_no']
                
                if case_no not in chunks_by_case:
                    chunks_by_case[case_no] = []
                chunks_by_case[case_no].append(data)
        
        #   0-based  
        for case_no, chunks in chunks_by_case.items():
            chunks = self._assign_chunk_indices(chunks)
            self._insert_chunks(f"kca:mediation:{case_no}", chunks)
```

### 2.    

```python
def validate_chunk_indices_before_insert():
    """
    DB   chunk_index 
    - 0 
    - 
    - chunk_total 
    """
    for doc_id, chunks in documents.items():
        #  
        chunks.sort(key=lambda x: x['chunk_index'])
        
        # 
        expected_indices = list(range(len(chunks)))
        actual_indices = [c['chunk_index'] for c in chunks]
        
        if expected_indices != actual_indices:
            raise ValueError(
                f"Invalid chunk_index for {doc_id}:\n"
                f"  Expected: {expected_indices}\n"
                f"  Actual: {actual_indices}"
            )
        
        # chunk_total 
        for chunk in chunks:
            if chunk['chunk_total'] != len(chunks):
                raise ValueError(
                    f"Invalid chunk_total for {chunk['chunk_id']}:\n"
                    f"  Expected: {len(chunks)}\n"
                    f"  Actual: {chunk['chunk_total']}"
                )
        
        print(f" {doc_id}: {len(chunks)} chunks validated")
```

### 3.   

```python
def safe_batch_insert(chunks: List[dict], batch_size: int = 100):
    """
       -      
    """
    total = len(chunks)
    
    for i in range(0, total, batch_size):
        batch = chunks[i:i+batch_size]
        
        try:
            #  
            cursor.executemany("""
                INSERT INTO chunks (...)
                VALUES (...)
            """, batch)
            conn.commit()
            
            #   
            save_progress(i + len(batch))
            
            print(f" Batch {i//batch_size + 1}/{(total+batch_size-1)//batch_size}: "
                  f"{i + len(batch)}/{total} chunks inserted")
            
        except Exception as e:
            conn.rollback()
            print(f" Error at batch {i//batch_size + 1} (chunk {i}):")
            print(f"   {e}")
            
            #    
            for idx, chunk in enumerate(batch):
                print(f"   [{idx}] chunk_id={chunk['chunk_id']}, "
                      f"chunk_index={chunk['chunk_index']}, "
                      f"chunk_total={chunk['chunk_total']}")
            
            raise
```

---

##   

###     

- [ ] ** chunk_index 0  **
- [ ] ** doc_id  chunk_index  **
- [ ] **chunk_index < chunk_total   **
- [ ] **UNIQUE(doc_id, chunk_index)   **

###   

####  compensation_case
- [x]  0-based
- [ ]  
- [ ]  

####  criteria/table2
- [ ] row_idx 
- [ ]  0-based  
- [ ]  

####  dispute_resolution/kca_final
- [ ] case_no 
- [ ]   0-based  
- [ ]  

####  dispute_resolution/ecmc
- [ ] case_no 
- [ ]   0-based  
- [ ] drop=true     (  )
- [ ]  

####  law
- [ ] law_id 
- [ ]   0-based  
- [ ]  

---

##    

  (`schema_v2_final.sql`)  0-based :

```sql
CHECK (chunk_index >= 0)  --  0  
CHECK (chunk_total > 0)
CHECK (chunk_index < chunk_total)  --  0-based 
```

****:
- chunk_total = 3 
-  chunk_index: 0, 1, 2 
-  chunk_index: 1, 2, 3  (3 < 3 )

---

##    

###   ( )

|  |   |  |
|-----|-----------|------|
| compensation_case | chunk_index | 0~ |
| table2 | row_idx | 1~126 |
| kca_final | () | N/A |
| ecmc | seq | 1~ |
| law | () | N/A |

###   (DB )

|  | chunk_index | chunk_total |  |
|-----|------------|------------|------|
| compensation_case | 0~ |  |  |
| table2 | 0~125 | 126 |  |
| kca_final (case 1) | 0~2 | 3 |  |
| ecmc (case 1) | 0~2 | 3 |  |
| law () | 0~1751 | 1752 |  |

---

##    

### 1.   (Priority: HIGH)

```python
#       
def _assign_chunk_indices(self, chunks: List[dict]) -> List[dict]:
    """  0-based  """
    total = len(chunks)
    for idx, chunk in enumerate(chunks):
        chunk['chunk_index'] = idx
        chunk['chunk_total'] = total
    return chunks
```

### 2.    (Priority: HIGH)

```bash
#    
cd /home/maroco/ddoksori_demo/backend
conda activate ddoksori

# 1.  
docker exec -it ddoksori_db psql -U postgres -d ddoksori -f /schema/schema_v2_final.sql

# 2.    (  10)
python scripts/test_transform_sample.py

# 3. chunk_index 
python scripts/validate_chunk_indices.py

# 4.    
python scripts/data_transform_pipeline.py
```

### 3.    (Priority: HIGH)

```sql
-- 1.  chunk_index 0  
SELECT doc_id, MIN(chunk_index) as min_idx
FROM chunks
GROUP BY doc_id
HAVING MIN(chunk_index) != 0;
-- : 0 

-- 2. chunk_index  
SELECT doc_id, chunk_total, COUNT(*) as actual_count
FROM chunks
GROUP BY doc_id, chunk_total
HAVING COUNT(*) != chunk_total;
-- : 0 

-- 3. chunk_index < chunk_total 
SELECT chunk_id, chunk_index, chunk_total
FROM chunks
WHERE chunk_index >= chunk_total;
-- : 0 
```

---

##  

###  : HIGH

     **      **.

###   

1. **    chunk_index 0-based **
2. **     **
3. **   **

###   

1. **   `_assign_chunk_indices()`  **
2. **  **
3. **    **
4. ** **

---

****: Manus AI (RAG  )  
** **: 2026-01-06  
** **:       
