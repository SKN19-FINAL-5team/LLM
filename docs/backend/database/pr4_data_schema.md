#    (4  )

PR #4   (, , )     .

---

## 1.    

|   |  |   |   |   |
|---|---|---|---|---|
| **** | ,   | N/A |   | 1 ( ) |
| **** |    | N/A |    | 1 ( ) |
| **** |    |   | // | 2 (  ) |
| **** |     |   |   | 3 (Fallback) |

---

## 2.   

### 2.1.   

```
cases ( )
   
   

laws ( )
    

standards ( )
    

chunks (  )
    
    
    
    
```

### 2.2.  

#### 2.2.1. `cases`  ( ,  )

   .

```sql
CREATE TABLE IF NOT EXISTS cases (
    id SERIAL PRIMARY KEY,
    case_uid VARCHAR(255) UNIQUE NOT NULL,
    case_type VARCHAR(50) NOT NULL,  -- 'precedent' ()  'consultation' ()
    case_no VARCHAR(255),
    decision_date VARCHAR(50),
    agency VARCHAR(50),  -- 'kca', 'ecmc', 'kcdrc' 
    source VARCHAR(255),
    case_index INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_cases_case_type ON cases(case_type);
CREATE INDEX idx_cases_agency ON cases(agency);
CREATE INDEX idx_cases_decision_date ON cases(decision_date);

COMMENT ON TABLE cases IS '   ';
COMMENT ON COLUMN cases.case_type IS 'precedent:  (  ), consultation:  (  )';
```

#### 2.2.2. `laws`  ()

  .

```sql
CREATE TABLE IF NOT EXISTS laws (
    id SERIAL PRIMARY KEY,
    law_uid VARCHAR(255) UNIQUE NOT NULL,
    law_name VARCHAR(255) NOT NULL,  -- : ''
    article VARCHAR(100),  -- : '1', '22'
    clause VARCHAR(100),  -- : '1', '2'
    content TEXT NOT NULL,
    category VARCHAR(100),  -- : '', ''
    enacted_date VARCHAR(50),  -- 
    amended_date VARCHAR(50),  --  
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_laws_law_name ON laws(law_name);
CREATE INDEX idx_laws_category ON laws(category);

COMMENT ON TABLE laws IS '   ';
```

#### 2.2.3. `standards`  ()

  .

```sql
CREATE TABLE IF NOT EXISTS standards (
    id SERIAL PRIMARY KEY,
    standard_uid VARCHAR(255) UNIQUE NOT NULL,
    item_category VARCHAR(100) NOT NULL,  -- : '', '', ''
    item_name VARCHAR(255),  -- : '', ''
    issue_type VARCHAR(255),  -- : '', '', ''
    standard_content TEXT NOT NULL,  --   
    applicable_period VARCHAR(100),  -- : '  1 '
    remedy VARCHAR(255),  -- : '', '', ''
    source VARCHAR(100),  -- : ' '
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_standards_item_category ON standards(item_category);
CREATE INDEX idx_standards_issue_type ON standards(issue_type);

COMMENT ON TABLE standards IS '   ';
```

#### 2.2.4. `chunks`  ()

    .

```sql
CREATE TABLE IF NOT EXISTS chunks (
    id SERIAL PRIMARY KEY,
    chunk_uid VARCHAR(255) UNIQUE NOT NULL,
    
    --   (    )
    case_uid VARCHAR(255) REFERENCES cases(case_uid) ON DELETE CASCADE,  -- /
    law_uid VARCHAR(255) REFERENCES laws(law_uid) ON DELETE CASCADE,  -- 
    standard_uid VARCHAR(255) REFERENCES standards(standard_uid) ON DELETE CASCADE,  -- 
    
    --  
    data_type VARCHAR(50) NOT NULL,  -- 'case', 'law', 'standard'
    chunk_type VARCHAR(50),  -- case: 'decision'/'parties_claim'/'judgment', law: 'article', standard: 'criterion'
    text TEXT NOT NULL,
    text_len INTEGER,
    embedding vector(1024),  -- KURE-v1  (1024)
    seq INTEGER,
    drop BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- : case_uid, law_uid, standard_uid    NOT NULL 
    CHECK (
        (case_uid IS NOT NULL AND law_uid IS NULL AND standard_uid IS NULL) OR
        (case_uid IS NULL AND law_uid IS NOT NULL AND standard_uid IS NULL) OR
        (case_uid IS NULL AND law_uid IS NULL AND standard_uid IS NOT NULL)
    )
);

CREATE INDEX idx_chunks_data_type ON chunks(data_type);
CREATE INDEX idx_chunks_chunk_type ON chunks(chunk_type);
CREATE INDEX idx_chunks_case_uid ON chunks(case_uid);
CREATE INDEX idx_chunks_law_uid ON chunks(law_uid);
CREATE INDEX idx_chunks_standard_uid ON chunks(standard_uid);
CREATE INDEX idx_chunks_embedding ON chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

COMMENT ON TABLE chunks IS '     ';
COMMENT ON COLUMN chunks.data_type IS 'case: /, law: , standard: ';
```

---

## 3. JSONL   ()

### 3.1.   (`laws.jsonl`)

```jsonl
{"law_uid": "law_001", "law_name": "", "article": "1", "clause": null, "content": "        , ·   ...", "category": "", "enacted_date": "1986.12.31", "amended_date": "2023.01.03"}
{"law_uid": "law_002", "law_name": "    ", "article": "17", "clause": "1", "content": "           ...", "category": "", "enacted_date": "2002.03.30", "amended_date": "2023.06.13"}
```

### 3.2.   (`standards.jsonl`)

```jsonl
{"standard_uid": "std_001", "item_category": "", "item_name": "", "issue_type": " ", "standard_content": "  1        ", "applicable_period": "  1 ", "remedy": "", "source": " "}
{"standard_uid": "std_002", "item_category": "", "item_name": "", "issue_type": " ", "standard_content": " 1       ", "applicable_period": " 1 ", "remedy": "/", "source": " "}
```

### 3.3.   (`consultation_cases.jsonl`)

  , `case_type: "consultation"` .

```jsonl
{"case_uid": "consultation_001", "case_type": "consultation", "case_no": null, "decision_date": "2023.05.10", "agency": "kca", "source": "24", "case_index": 1, "chunk_uid": "consultation_001_summary", "data_type": "case", "chunk_type": "summary", "text": "       .    .        .", "text_len": 85, "seq": 1, "drop": false}
```

---

## 4.    (PR #4 )

### 4.1.   

- ** **:   (article + clause + content)
- **chunk_type**: `"article"`
- ** **: `content` ( )

### 4.2.   

- ** **:    (item_name + issue_type + standard_content)
- **chunk_type**: `"criterion"`
- ** **: `standard_content` ( )

### 4.3.   

- ** **:      ( )
- **chunk_type**: `"summary"`, `"resolution"` 
- ** **:  

---

## 5.   

### 5.1.   ( +  )

```sql
SELECT 
    c.text,
    l.law_name,
    l.article,
    s.item_category,
    s.remedy,
    1 - (c.embedding <=> %s::vector) AS similarity
FROM chunks c
LEFT JOIN laws l ON c.law_uid = l.law_uid
LEFT JOIN standards s ON c.standard_uid = s.standard_uid
WHERE c.data_type IN ('law', 'standard') AND c.drop = FALSE
ORDER BY c.embedding <=> %s::vector
LIMIT 5;
```

### 5.2.   ( )

```sql
SELECT 
    c.text,
    cs.case_no,
    cs.agency,
    cs.decision_date,
    1 - (c.embedding <=> %s::vector) AS similarity
FROM chunks c
JOIN cases cs ON c.case_uid = cs.case_uid
WHERE c.data_type = 'case' AND cs.case_type = 'precedent' AND c.drop = FALSE
ORDER BY c.embedding <=> %s::vector
LIMIT 5;
```

### 5.3.   (Fallback)

```sql
SELECT 
    c.text,
    cs.agency,
    cs.decision_date,
    1 - (c.embedding <=> %s::vector) AS similarity
FROM chunks c
JOIN cases cs ON c.case_uid = cs.case_uid
WHERE c.data_type = 'case' AND cs.case_type = 'consultation' AND c.drop = FALSE
ORDER BY c.embedding <=> %s::vector
LIMIT 5;
```

---

## 6. PR #4  

- [ ] `laws`   `standards`  
- [ ] `cases`  `case_type`  
- [ ] `chunks`  `law_uid`, `standard_uid`, `data_type`  
- [ ]     
- [ ]     
- [ ]     
- [ ] `VectorRetriever`  `data_type`   
- [ ] LangGraph     
- [ ]     

---

    PR #4 , ///     .
