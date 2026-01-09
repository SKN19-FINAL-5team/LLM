#    

##  

RAG          .

##   

### 1.    (`metadata_enricher.py`)

   :

####  

1. **** (`keywords`)
   -    
   -  
   -  10  

2. ** ** (`legal_terms`)
   -     
   - : , , , , , ,  

3. **** (`entities`)
   - : ,   
   - : ,     

4. ** ** (`category_tags`)
   -    
   - 11 : , , , , , , , , , , 

5. ** ** (`law_references`)
   - " +  +  + "  
   - : " 750", " 16"

6. **** (`dates`)
   - YYYY-MM-DD, YYYY.MM.DD 
   - YYYY MM DD 

### 2.    

`data_transform_pipeline.py`    :

```python
transformer = DataTransformer(
    enrich_metadata=True  #    ()
)
```

####  

- `DataTransformer.__init__()`: `enrich_metadata`  
- `_enrich_document()`:      
-  `transform_*`    
-     

##    

###  
- **  **: 13,367 (drop )
- **  **: 14,159

###   

|   |   |  |
|---------------|---------|---------|
|  | 13,366 | 100.0% |
|   | 13,333 | 99.7% |
|   | 7,898 | 59.1% |
|   | 940 | 7.0% |
|  | 1,121 | 8.4% |
|  | 584 | 4.4% |

##   

```json
{
  "keywords": [
    "",
    "",
    "",
    "",
    ""
  ],
  "legal_terms": [
    "",
    "",
    "",
    "",
    ""
  ],
  "category_tags": [
    ""
  ],
  "entities": {
    "companies": [" "],
    "products": [" S24"]
  },
  "law_references": [
    " 750",
    " 16"
  ],
  "dates": [
    "2024-01-15",
    "2024.01.20"
  ]
}
```

##   

### 1.    (  )

```bash
cd backend/scripts
conda activate ddoksori
python data_transform_pipeline.py
```

### 2.    ()

```python
# data_transform_pipeline.py main() 
transformer = DataTransformer(
    enrich_metadata=False  #   
)
```

### 3.  

```bash
cd backend/scripts
conda activate ddoksori
python metadata_enricher.py
```

##   

```
================================================================================
 !   .
   (    )
================================================================================

-  Critical : 0
-   : 1,028 (   ,  )
```

##  RAG  

      :

### 1. Hybrid Search (Vector + Metadata Filtering)

```sql
--   +  
SELECT c.*, d.title, 
       1 - (c.embedding <=> query_embedding) as similarity
FROM chunks c
JOIN documents d ON c.doc_id = d.doc_id
WHERE c.metadata->>'category_tags' ? ''
  AND c.drop = FALSE
ORDER BY c.embedding <=> query_embedding
LIMIT 10;
```

### 2.    

```sql
--     
SELECT c.*, d.title
FROM chunks c
JOIN documents d ON c.doc_id = d.doc_id
WHERE c.metadata->'law_references' @> '[" 750"]'
  AND c.drop = FALSE;
```

### 3.    (Re-ranking)

      

##   

1. **  **
   - `backend/scripts/data_processing/metadata_enricher.py`

2. **  **
   - `backend/scripts/data_processing/data_transform_pipeline.py` (  )

3. ** **
   - `backend/data/transformed/*.json` ( )

##   

1.    
2.     (/)
3.      DB 
4.  Hybrid Search API 
5.    

##    

1. **  **
   - TF-IDF  KeyBERT 
   -    

2. **  **
   - NER   (KoNLPy, KoELECTRA )
   -     

3. **  **
   -    
   -    

4. ** **
   - PostgreSQL GIN  
   -   

---

** **: 2026-01-06
****: AI Assistant
** **: 
