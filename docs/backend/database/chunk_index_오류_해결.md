#  chunk_index/chunk_total      

****: 2026-01-05  
****: `psycopg2.errors.CheckViolation: new row for relation "chunks" violates check constraint "chunks_check"`

---

##    

### 1.   

** **:
```
Failing row contains (..., chunk_index=4, chunk_total=3, ...)
```

** **:
```sql
CHECK (chunk_index <= chunk_total)
```

****: `4 <= 3` → False →   

### 2.   

**normalized   (ecmc_final_rag_chunks_normalized.jsonl)**:
```json
{"case_uid": "ecmc_merged:4", "case_index": 4, "chunk_type": "decision", "text": "..."}
{"case_uid": "ecmc_merged:4", "case_index": 4, "chunk_type": "parties_claim", "text": "..."}
{"case_uid": "ecmc_merged:4", "case_index": 4, "chunk_type": "judgment", "text": "..."}
```

****:
- `case_uid`:   (: `ecmc_merged:4`)
- `case_index`:   (1, 2, 3, 4, ...) - ** **
- `chunk_type`:   (decision, parties_claim, judgment)
-  `case_uid`     ( 3)

### 3.   ( )

```python
#  
chunk_index = record.get('case_index', 0)  # ← case_index chunk_index !
chunk_id = f"{doc_id}::chunk{chunk_index}"
chunks.append({
    'chunk_id': chunk_id,
    'doc_id': doc_id,
    'chunk_index': chunk_index,  # ← 4 ( )
    'chunk_total': 1,  # ←   (   !)
    ...
})

# chunk_total  
doc_chunk_counts = {}
for chunk in chunks:
    doc_id = chunk['doc_id']
    doc_chunk_counts[doc_id] = doc_chunk_counts.get(doc_id, 0) + 1

for chunk in chunks:
    if chunk['chunk_total'] == 1 and doc_chunk_counts[chunk['doc_id']] > 1:
        chunk['chunk_total'] = doc_chunk_counts[chunk['doc_id']]
```

****:
1. **`case_index` `chunk_index`  **
   - `case_index`   (4 )
   - `chunk_index`   (0, 1, 2)
   
2. **`chunk_total`   **
   -  : `chunk['chunk_total'] == 1 and doc_chunk_counts[chunk['doc_id']] > 1`
   -  `chunk_total`  1  ,  
   - :     ,    

3. ****:
   - `ecmc_merged:4`  3 :
     - chunk_index=4, chunk_total=1 ( 3)
     - chunk_index=4, chunk_total=1 ( 3)
     - chunk_index=4, chunk_total=1 ( 3)
   -    `chunk_index=4`  →  ID  
   - `chunk_index=4` `chunk_total=3` →   

---

##   

### 1.  

** **:
-  `case_uid`   ****
-    `chunk_index` **0  **
- `chunk_total` **   ** 

### 2.  

```python
#  2    
doc_chunks_temp = {}  # {doc_id: [chunk_data, ...]}

#   :  
for mediation_file in tqdm(mediation_files, desc="  "):
    with open(mediation_file, 'r', encoding='utf-8') as f:
        for line in f:
            record = json.loads(line)
            
            if 'case_uid' in record:
                source_org = record.get('agency', 'unknown').upper()
                doc_id = f"{source_org.lower()}:mediation_case:{record['case_uid']}"
                
                #    (1)
                if doc_id not in [d['doc_id'] for d in documents]:
                    documents.append({...})
                
                #     
                if doc_id not in doc_chunks_temp:
                    doc_chunks_temp[doc_id] = []
                
                doc_chunks_temp[doc_id].append({
                    'chunk_type': record.get('chunk_type', 'unknown'),
                    'content': record['text'],
                    'content_length': record.get('text_len', len(record['text'])),
                    'metadata': {...}
                })

#   :  
for doc_id, doc_chunks in doc_chunks_temp.items():
    chunk_total = len(doc_chunks)
    for chunk_index, chunk_data in enumerate(doc_chunks):
        chunk_id = f"{doc_id}::chunk{chunk_index}"
        chunks.append({
            'chunk_id': chunk_id,
            'doc_id': doc_id,
            'chunk_index': chunk_index,  # ← 0, 1, 2 ( )
            'chunk_total': chunk_total,   # ← 3 ( )
            'chunk_type': chunk_data['chunk_type'],
            'content': chunk_data['content'],
            'content_length': chunk_data['content_length'],
            'metadata': chunk_data['metadata']
        })
```

### 3.  

** ()**:
```
ecmc:mediation_case:ecmc_merged:4
   chunk_id: ...::chunk4, chunk_index=4, chunk_total=1 ( 3)
   chunk_id: ...::chunk4, chunk_index=4, chunk_total=1 ( 3)  ←  ID!
   chunk_id: ...::chunk4, chunk_index=4, chunk_total=1 ( 3)  ←  ID!

:
- chunk_index=4 > chunk_total=3 →   
-  chunk_id → Primary Key  
```

** ()**:
```
ecmc:mediation_case:ecmc_merged:4
   chunk_id: ...::chunk0, chunk_index=0, chunk_total=3, chunk_type=decision
   chunk_id: ...::chunk1, chunk_index=1, chunk_total=3, chunk_type=parties_claim
   chunk_id: ...::chunk2, chunk_index=2, chunk_total=3, chunk_type=judgment

:
- 0 <= 3, 1 <= 3, 2 <= 3 →   
-  chunk_id → Primary Key 
-     
```

---

##   

### 1.  

****:
- `ecmc_final_rag_chunks_normalized.jsonl`
- `kca_final_rag_chunks_normalized.jsonl`
- `kcdrc_final_rag_chunks_normalized.jsonl`

** **:  3,000 (normalized  )

** **:  9,000 (  3 )

### 2.   

****:
- `kca_cases_116_chunks_v2.jsonl` (  )

****:  `doc_id`, `chunk_id`, `chunk_index`, `chunk_total`  

---

##   

### 1.   

```bash
#    
SELECT doc_id, chunk_index, chunk_total
FROM chunks
WHERE chunk_index >= chunk_total;
```

### 2.   

```bash
#      
SELECT COUNT(*)
FROM chunks
WHERE chunk_index >= chunk_total;
-- : 0

#      
SELECT doc_id, COUNT(*) as total, MAX(chunk_index) + 1 as max_index
FROM chunks
GROUP BY doc_id
HAVING COUNT(*) != MAX(chunk_index) + 1;
-- : 0 (  )
```

### 3.   

```bash
#    
SELECT chunk_index, COUNT(*) 
FROM chunks 
WHERE doc_type = 'mediation_case'
GROUP BY chunk_index 
ORDER BY chunk_index;

#     
SELECT chunk_total, COUNT(*) 
FROM chunks 
WHERE doc_type = 'mediation_case'
GROUP BY chunk_total 
ORDER BY chunk_total;
```

---

##  

### 1.     

- `case_index`:   ( )
- `chunk_index`:   ( , 0 )
- **   !**

### 2.   

-      
-       
-   ""  " " 

### 3.   

-      
-     
-      

### 4.   

-      
-        
-      

---

##   

- ** **: `backend/database/schema_v2_final.sql`
- ** **: `backend/scripts/embed_pipeline_v2.py`
- ** **: `backend/data/dispute_resolution/*.jsonl`

---

****: Manus AI  
****: 16192c0  
****: feature/pr4-multi-agent-prep
