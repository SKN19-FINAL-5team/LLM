# RAG     

** **: 2026-01-06 15:27:06  
****:  RAG 

---

##  Executive Summary

     RAG      .

###  

|  |   |   |  |
|------|---------|---------|--------|
| **Critical Issues** | 92 | 0 | **100%**  |
| **  (< 100)** | 1,500 | 310 | **79.3%**  |
| **   ** | - | **95.6%** | - |
| **  ** | - | 9,196 (74.7%) | - |

###    

**   **:  **820-900 ** (5.8%) KURE-v1  512       
- ****: judgment, parties_claim        
- **   **:    0.61 → **0.70-0.75** (15-23% )

---

## 1.    

### 1.1 Critical Issues  

****: 92  content  ( mediation_case law )
-  ** **:  ,   
-  ** **:         

### 1.2   

**  **:
-  : 1,500 ( 10%)
-  : 310 ( 2.2%)
- : **79.3%**

**   (100-2,000)**:
-  : 13,530 (**95.6%**)
-  RAG     

** **:
- 2,000-5,000: 251 (1.8%)
- 5,000 : 68 (0.5%)
-   : 319 (  300   )
  - **:        

### 1.3   

|   |  |   |  |  |
|-----------|------|-----------|------|------|
| qa_combined | 11,349 | 517 | 117 | 1,799 |
| judgment | 652 | 2,313 | 65 | 18,995 |
| parties_claim | 609 | 1,093 | 98 | 5,362 |
| decision | 564 | 413 | 10 | 4,611 |
| article | 401 | 216 | 77 | 860 |
| paragraph | 391 | 212 | 72 | 1,086 |
| resolution_row | 126 | 268 | 103 | 2,295 |
| law | 67 | 564 | 5 | 3,837 |

### 1.4        

####   

**KURE-v1    **:  **512 **

- **  **:  1.5-2 = 1
- ** **:  **768-1,024** (512  )
- ** **:     ** **

####    

|   |   |    |   |   () |  |
|-----------|-----------|--------------|-----------|-----------------|--------|
| **judgment** | 2,313 | **~1,156-1,542** | 18,995 | ~80% |  **Critical** |
| **parties_claim** | 1,093 | **~546-729** | 5,362 | ~50% |  **High** |
| **decision** | 413 | ~206-275 | 4,611 | ~10% |  **Medium** |
| **law** | 564 | ~282-376 | 3,837 | ~20% |  **Medium** |
| qa_combined | 517 | ~258-345 | 1,799 | < 5% |  **Low** |

**   **:
- judgment: **652**   520  
- parties_claim: **609**   300  
- ** **:  **820-900 ** ( ~5.8%)

####    

```mermaid
graph LR
    LongChunk[_2000] -->|512| Truncation[]
    Truncation -->|| IncompleteEmbedding[]
    IncompleteEmbedding -->|| LowSearchQuality[]
    IncompleteEmbedding -->|| MissedResults[]
    
    style LongChunk fill:#ff6b6b
    style Truncation fill:#ffa94d
    style IncompleteEmbedding fill:#ffd43b
    style LowSearchQuality fill:#ff6b6b
    style MissedResults fill:#ff6b6b
```

** **:
1. ** **: 512     
2. ** **:   ,      
3. ** **:       
4. ** **:      

####  

** 1:    (Semantic Chunking)**  ****

```python
# : judgment   
def split_judgment_chunk(chunk: Dict, target_size: int = 700) -> List[Dict]:
    """
       
    
    Args:
        chunk:  
        target_size:   (700 =  350 )
    
    Returns:
          
    """
    content = chunk['content']
    
    # 1.   1 
    sections = re.split(r'\n\n+|\d+\.\s+', content)
    
    # 2.    
    sub_chunks = []
    current_chunk = []
    current_length = 0
    
    for section in sections:
        section_length = len(section)
        
        if current_length + section_length > target_size and current_chunk:
            #    
            sub_chunks.append({
                **chunk,
                'content': '\n\n'.join(current_chunk),
                'chunk_id': f"{chunk['chunk_id']}_part{len(sub_chunks)+1}",
                'parent_chunk_id': chunk['chunk_id']
            })
            current_chunk = []
            current_length = 0
        
        current_chunk.append(section)
        current_length += section_length
    
    #   
    if current_chunk:
        sub_chunks.append({
            **chunk,
            'content': '\n\n'.join(current_chunk),
            'chunk_id': f"{chunk['chunk_id']}_part{len(sub_chunks)+1}",
            'parent_chunk_id': chunk['chunk_id']
        })
    
    return sub_chunks
```

**   **:
- judgment (652): 300-700  →  1,500-1,800  
- parties_claim (609): 400-800  →  900-1,000  

** 2: Overlapping Chunks** ( )

```python
#   100-150 
overlap_size = 150

#    150    
chunk_n['content'] = prev_chunk_tail + current_content
```

****:
-     
-   
-   

** 3:   ** ()

```
 
   (300) ←  
   (600 × N) ←  
```

****:
- 2 :   →  
-    

####  

**Phase 1:   (1)**
1. judgment, parties_claim     
2.  : 600-800 (300-400 )
3.    

**Phase 2:   (1-2)**
1.    
2.   
3.   

**Phase 3:  ()**
1.     
2. 512     

####  

|  |  |   () |
|------|------|----------------|
|    | ~820-900 (5.8%) | < 10 (< 0.1%) |
|    (judgment) | 2,313 | 600 |
|    | 0.6146 | **0.70-0.75** () |
|    | 14,159 |  16,500-17,000 |

**   **:
-      **+15-20%**
-     **-50%** 

---

## 2.    

### 2.1  

- ** **: 12,314
- **  **: 9,196 (74.7%)
- ** **: KURE-v1 (1024)
- ** **: 5 (   )

### 2.2  

|  |  |
|------|------|
|   | **5/5 (100%)** |
|   ( 3) | **0.6146** |
|    | **0.6326** |
|    | 0.17 |

### 2.3   

####  1: "    .    ?"
-  : 5 
-  : **0.7287** ()
-  : 0.7400
-  : 0.19

**  **:
1. "    " (: 0.7400)
2. "    ,  " (: 0.7239)
3. "  7   " (: 0.7223)

####  2: "  "
-  : 5 
-  : **0.6627**
-  : 0.6675

####  3: "     "
-  : 5 
-  : **0.6900**
-  : **0.44** ()
-  : 0.6991

####  4: "   "
-  : 1  
-  : 0.4623 ()
- **:     

####  5: "  "
-  : 5 
-  : 0.5293
-  : 0.5942

### 2.4   

** **:  **** (0.5 )

****:
-      
-   /     (0.72+)
-       

**  **:
-    0.6146 (: 0.7 )
-      (0.17)
-   ( )  

---

## 3.   

### 3.1   

|   |   |   |  / |
|-----------|---------|---------|----------------|
| counsel_case | 11,342 | 11,342 | 1.0 |
| mediation_case | 274 | 846 | 3.1 |
| criteria_resolution | 1 | 126 | 126.0 |

### 3.2  

|  |   |  |
|------|---------|------|
| consumer.go.kr | 11,342 | 97.6% |
| ECMC | 274 | 2.4% |
| KCA | 1 | 0.01% |

****:  consumer.go.kr  

---

## 4.   

### 4.1  

|  |  |  |
|------|------|------|
| ** ** | Critical Issues | 100%   |
| |    | 79.3%   |
| |    | 95.6%  |
| ** ** |   | 100%  |
| |   | 0.61 ()  |
| ** ** |   | 74.7%  |

### 4.2  

1. **  **
   -       
   -      

2. **  **
   -     95.6% 
   -     

3. **  **
   -     
   -   

### 4.3   

- ** **:       
- ** **:        
- ** **:      

---

## 5.  

### 5.1   (1-2)

1. ** :    **  ** **
   -  **Critical**:  820-900  KURE-v1 512   
   -  ****:   ,  ,   
   - ****: 
     - judgment (652): 600-800 
     - parties_claim (609): 600-800 
     -  1.4      
   - ****:   (   )
   - ** **:   0.61 → 0.70-0.75

2. ** **
   -   3,118    
   - : `embed_data_remote.py`   
   - ****:       

3. **   **
   -     0.17 ()
   - :   (Vector + Keyword)  

### 5.2   (1-2)

1. ** **
   -  ,       
   - KCA, ECMC     

2. ** **
   -    (TF-IDF, KeyBERT)
   -   ( ,  )
   -   (, )

3. **  **
   -    
   -    

### 5.3   (3+)

1. **Hybrid Search **
   - Vector Search + BM25 
   -   

2. **  **
   -    
   - A/B  

3. **  **
   -      
   - Overlapping chunks  

---

## 6. 

###  

 **Critical Issues 100% **:     
 **   95.6%**: RAG     
 **  100% **:      

###  

1. **  ()**:         
   -  820-900  512    
   -    ,   
2. **1 **:      
3. **2 **:       
4. **1 **:     

###  

    **** , RAG     . 

** **:
- Critical Issues 100%   
-     95.6%  
-    0.61 () 

** **:
-  ****:  820-900  KURE-v1 512   
-      **0.70-0.75**   
-        ** **

---

****: AI Assistant  
** **:  , 
