# RAG CLI  

****: 2026-01-09  
****: LLM  RAG CLI     

---

##  

1. [](#)
2. [ ](#-)
3. [ ](#-)
4. [ ](#-)
5. [Golden Set ](#golden-set-)
6. [  ](#--)
7. [](#)
8. [ ](#-)

---

## 

RAG CLI   (cosine similarity, BM25, SPLADE, hybrid search)  , LLM(GPT-4o-mini)       CLI .

###  

- **   **: cosine, BM25, SPLADE, hybrid search   
- **LLM  **:     LLM     
- **Golden Set **:       
- ** **:   , Top-K     

###  

```
  (CLI)
    ↓
MultiMethodRetriever
     Cosine Similarity 
     BM25 
     SPLADE 
     Hybrid Search 
    ↓
    
    ↓
RAGGenerator.generate_comparative_answer()
         
     LLM    
       
    ↓
CLI  
```

---

##  

### 1.   

`.env`  OpenAI API    :

```bash
# backend/.env  
cd /home/maroco/LLM/backend
cat .env | grep OPENAI_API_KEY
```

** **:
```env
OPENAI_API_KEY=your_openai_api_key_here
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ddoksori
DB_USER=postgres
DB_PASSWORD=postgres
```

### 2. Conda  

```bash
conda activate dsr
```

### 3.  

PostgreSQL    :

```bash
# Docker  
docker ps | grep ddoksori_db

#   
psql -h localhost -U postgres -d ddoksori -c "SELECT COUNT(*) FROM chunks;"
```

---

##  

###  1:   

```bash
cd /home/maroco/LLM/backend
conda activate dsr
python scripts/cli/rag_cli.py --query "   1    .   ?"
```

** **:
```
================================================================================
:    1    .   ?
================================================================================

    ...
 BM25 Retriever  
 SPLADE Retriever  

   ... (top_k=10)

  :
   COSINE: 10  (0.234)
   BM25: 8  (0.156)
   SPLADE: 7  (0.312)
   HYBRID: 10  (0.445)

 LLM   ...

================================================================================

================================================================================
[  ]
- COSINE: 10  (0.234)
- BM25: 8  (0.156)
- SPLADE: 7  (0.312)
- HYBRID: 10  (0.445)

[ ]
     ,    1        .

COSINE    ,    1,        . BM25      .

HYBRID       ,   1          .

[ ]
-  : COSINE, BM25, HYBRID
- : KCA-2024-001234
- :    3

--------------------------------------------------------------------------------

--------------------------------------------------------------------------------
: gpt-4o-mini
  : cosine, bm25, splade, hybrid
   : 35
 :
  - : 2,345
  - : 456
  - : 2,801
================================================================================
```

###  2:  

      :

```bash
python scripts/cli/rag_cli.py
```

```
RAG CLI -   (: Ctrl+C  'quit')
--------------------------------------------------------------------------------

:    .
```

---

##  

### Top-K 

         :

```bash
# Top-K 5  (: 10)
python scripts/cli/rag_cli.py --query "" --top-k 5
```

### LLM  

 LLM     (OpenAI API  ):

```bash
# GPT-4 
python scripts/cli/rag_cli.py --query "" --model gpt-4

# GPT-3.5-turbo 
python scripts/cli/rag_cli.py --query "" --model gpt-3.5-turbo
```

---

## Golden Set 

### Golden Set  

        :

```bash
python scripts/cli/rag_cli.py --golden-set
```

** **:
```
================================================================================
Golden Set  
================================================================================

[1] Q001
    :    1    .   ?
    : product_specific, : easy

[2] Q002
    :     .  ?
    : practical, : easy

[3] Q003
    :  750  .
    : legal, : easy

...

================================================================================
 30 
================================================================================

 :
  -  :   
  - 'all' :    ( )
  - 'q'  'quit' : 

: 1
```

###   (  )

Golden Set      :

```bash
python scripts/cli/rag_cli.py --golden-set
#   'all' 
```

###  Golden Set 

 Golden Set    :

```bash
python scripts/cli/rag_cli.py --golden-set --golden-set-path /path/to/custom_golden_set.json
```

---

##   

     :

### Cosine Similarity 

```bash
python scripts/cli/rag_cli.py --query "" --methods cosine
```

### Cosine Hybrid 

```bash
python scripts/cli/rag_cli.py --query "" --methods cosine hybrid
```

###    

- `cosine`: Cosine Similarity (  )
- `bm25`: BM25 (  )
- `splade`: SPLADE (Sparse Lexical and Expansion )
- `hybrid`: Hybrid Search (    )

****: BM25 SPLADE  .     .

---

##    

```bash
python scripts/cli/rag_cli.py --help
```

** **:

|  |  |  |  |
|------|------|------|--------|
| `--query` | `-q` |   ( ) | - |
| `--golden-set` | `-g` | Golden set   | False |
| `--top-k` | `-k` |       | 10 |
| `--methods` | `-m` |     |   |
| `--model` | - |  LLM  | gpt-4o-mini |
| `--golden-set-path` | - | Golden set JSON   |   |

---

## 

###  1: OPENAI_API_KEY 

****:
```
 OPENAI_API_KEY  .
   .env   API  .
```

** **:
1. `backend/.env`  
2. `OPENAI_API_KEY=your_openai_api_key_here`   API  

###  2:   

****:
```
   : ...
```

** **:
1. PostgreSQL   :
   ```bash
   docker ps | grep ddoksori_db
   ```
2.     :
   ```bash
   docker-compose up -d db
   ```
3. `.env`  DB  

###  3: BM25/SPLADE  

****:
```
  BM25 Retriever  : ...
  SPLADE Retriever  : ...
```

** **:
- BM25 SPLADE  .   cosine hybrid   .
-        .

###  4: Golden Set    

****:
```
 Golden set    : ...
```

** **:
1.   : `backend/evaluation/datasets/gold_real_consumer_cases.json`
2.   `--golden-set-path`    
3.   `--query`   

###  5:   

****:
```
  :
   COSINE: 0 
   BM25: 0 
  ...
```

** **:
1.    :
   ```bash
   psql -h localhost -U postgres -d ddoksori -c "SELECT COUNT(*) FROM chunks;"
   ```
2.   :
   ```bash
   psql -h localhost -U postgres -d ddoksori -c "SELECT COUNT(*) FROM chunks WHERE embedding IS NOT NULL;"
   ```
3.     .

---

##  

###  1:   

```bash
python scripts/cli/rag_cli.py --query " 750  ." --methods cosine hybrid
```

###  2:   

```bash
python scripts/cli/rag_cli.py --query "   ?" --top-k 5
```

###  3:   

```bash
python scripts/cli/rag_cli.py --query "    " --methods cosine bm25 hybrid
```

###  4: Golden Set 

```bash
python scripts/cli/rag_cli.py --golden-set
#    
```

---

##  

- [RAG  ](../guides/rag_architecture_expert_view.md)
- [  ](../guides/embedding_process_guide.md)
- [Vector DB  ](../guides/Vector_DB__.md)
- [  ](../backend/rag/HYBRID_SEARCH_GUIDE.md)

---

##   

- **CLI **: `backend/scripts/cli/rag_cli.py`
- **MultiMethodRetriever**: `backend/app/rag/multi_method_retriever.py`
- **RAGGenerator**: `backend/app/rag/generator.py`
- **Golden Set Loader**: `backend/scripts/cli/golden_set_loader.py`
- **Golden Set **: `backend/evaluation/datasets/gold_real_consumer_cases.json`

---

****: AI Assistant  
** **: 2026-01-09
