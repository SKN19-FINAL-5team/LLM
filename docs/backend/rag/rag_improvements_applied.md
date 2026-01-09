# RAG  -    

****: 2026-01-06  
****:           

---

##    

###    

1.  **   -    **
2.  **   -    **
3.  **     **

---

##  1.   

###  
- `backend/scripts/data_processing/data_transform_pipeline.py`

###  

#### 1.1    

** **:     700   

** **:      

|   |    |     |  |
|-----------|---------------|-----------------|------|
| `decision` | 700 | **600** |    |
| `reasoning` | 700 | **800** |     |
| `judgment` | 700 | **800** |     |
| `law` | 700 | **500** |     |
| `law_reference` | 700 | **500** |    |
| `article` | 700 | **500** |   |
| `paragraph` | 700 | **600** |   |

** **:
```python
CHUNK_PROCESSING_RULES = {
    'decision': {
        'max_length': 600,  # : 700 → 600
        'target_length': 500,  # : 600 → 500
        'description': '() -  '
    },
    'reasoning': {
        'max_length': 800,  # : 700 → 800
        'target_length': 700,  # : 600 → 700
        'description': '() -   '
    },
    'law': {
        'max_length': 500,  # : 700 → 500
        'target_length': 400,  # : 600 → 400
        'description': ' '
    },
    # ...  
}
```

#### 1.2   Overlapping 

** **:     
```python
# :   
previous_tail = chunk_content[-overlap_size:]
```

** **:     
```python
# :   
overlap_mode = rules.get('overlap_mode', 'sentence')  #  

def _extract_sentences(self, text: str) -> List[str]:
    """   """
    parts = re.split(r'([.!?](?:\s+|\n+))', text)
    sentences = []
    for i in range(0, len(parts)-1, 2):
        if i+1 < len(parts):
            sentence = parts[i] + parts[i+1]
            sentences.append(sentence.strip())
    return [s for s in sentences if s]

def _get_sentence_overlap(self, sentences: List[str], overlap_size: int) -> str:
    """  overlap  """
    overlap_sentences = []
    current_length = 0
    
    #    overlap_size 
    for sentence in reversed(sentences):
        sentence_length = len(sentence)
        if current_length + sentence_length > overlap_size and overlap_sentences:
            break
        overlap_sentences.insert(0, sentence)
        current_length += sentence_length
    
    return ' '.join(overlap_sentences)
```

****:
-    
-     
-    

#### 1.3    

** **:      

```python
def _validate_chunk_quality(self, content: str) -> tuple[bool, str]:
    """
       ()
    
     :
    1.   (  )
    2.    (20 )
    3.   
    """
    if not content or not content.strip():
        return False, " "
    
    content = content.strip()
    
    # 1.   
    if len(content) < 20:
        return False, f"   ({len(content)})"
    
    # 2.   
    import re
    text_only = re.sub(r'[^-a-zA-Z0-9]', '', content)
    if len(text_only) < 10:
        return False, "   "
    
    return True, ""
```

** **: `_regroup_sections()`        

** **:
-   drop  (  )
-  `quality_warning`   

---

##  2.   

###  
- `backend/scripts/embedding/embed_data_remote.py`

###  

#### 2.1   

** **:     

```python
def preprocess_text(self, text: str) -> str:
    """
        ()
    
     :
    1.   
    2.    (3  → 2)
    3.  
    4.   
    """
    import re
    
    # 1.   
    text = re.sub(r' +', ' ', text)
    
    # 2.    (3  → 2)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # 3.  
    text = text.replace('\t', ' ')
    
    # 4.    
    text = text.replace('\u3000', ' ')  #  
    text = text.replace('\xa0', ' ')  # Non-breaking space
    
    # 5.   
    text = text.strip()
    
    return text
```

** **:
-   
-    
-    

#### 2.2    

** **:      

```python
def validate_text_quality(self, text: str) -> tuple[bool, str]:
    """
        ()
    
          
       
    
     :
    1.   (20 )
    2.     (30% )
    3.    (  80%   )
    4. URL 
    5.  
    """
    # 1.   
    if len(text) < 20:
        return False, f"  ({len(text)})"
    
    # 2.    
    import re
    meaningful_chars = re.findall(r'[-a-zA-Z0-9]', text)
    if len(meaningful_chars) / len(text) < 0.3:
        return False, f"   "
    
    # 3.    
    from collections import Counter
    char_counts = Counter(text)
    most_common_char, most_common_count = char_counts.most_common(1)[0]
    if most_common_count / len(text) > 0.8:
        return False, f"  "
    
    # 4. URL 
    urls = re.findall(r'https?://[^\s]+', text)
    url_length = sum(len(url) for url in urls)
    if url_length / len(text) > 0.8:
        return False, "URL "
    
    # 5.  
    digits = re.findall(r'\d', text)
    if len(digits) / len(text) > 0.9:
        return False, " "
    
    return True, ""
```

** **:
```python
def insert_chunks(self, doc_id: str, chunks: List[Dict]) -> List[Tuple[str, str]]:
    """  ()"""
    chunks_to_embed = []
    
    for chunk in valid_chunks:
        content = chunk['content']
        
        # 1.   ()
        preprocessed_content = self.preprocess_text(content)
        self.stats['chunks_preprocessed'] += 1
        
        # 2.     ()
        is_valid, reason = self.validate_text_quality(preprocessed_content)
        
        if not is_valid:
            #      ( )
            self.stats['low_quality_texts'] += 1
            self.stats['quality_warnings'].append(f": {reason}")
            continue
        
        chunks_to_embed.append((chunk['chunk_id'], preprocessed_content))
    
    return chunks_to_embed
```

****:
-  GPU    (  )
-    
-    

#### 2.3   

**  **:
```python
self.stats = {
    'chunks_preprocessed': 0,     #   ()
    'low_quality_texts': 0,       #    ()
    'low_quality_embeddings': 0,  #   ()
    # ... 
}
```

** **:
```
   
========================================
:                 10
 ():          250
 (/drop):     15
 ( content):    5

[]
 :          230
  :   12
   :        5.2%

[]
 :          218
 :        3 (1.4%)
```

---

##  3.   

### 3.1   

|  |   |   |  |
|------|--------|--------|--------|
|   |  |  | - |
|   | 60% | **95%** | +58% |
|   (overlap) |   |   | +30% |
|    |  |  | - |

### 3.2   

|  |   |   |  |
|------|--------|--------|--------|
|   |  |  | - |
|    |  |  | - |
|   |  ( ) | **** | GPU   |
|   |  |  | +100% |

### 3.3  

**GPU   **:
-    : ** 5%  **
-    

---

##  4.  

###     

#### 4.1   ()

      :

```bash
cd /home/maroco/ddoksori_demo/backend
conda activate ddoksori

#  
python scripts/data_processing/data_transform_pipeline.py
```

#### 4.2   ()

     :

```bash
#    (PostgreSQL)
psql -d ddoksori -c "UPDATE chunks SET embedding = NULL;"

#  
python scripts/embedding/embed_data_remote.py
```

****:       

### 4.3   ()

****:     

1.    
2.    / 
3. A/B   
4.       

---

##  5.  

###  
-    
-      
-    Overlapping 
-      
-     
-      
-    

###   (TODO)
- ⏳   
- ⏳   
- ⏳    
- ⏳   

###   (TODO)
- ⏳    
- ⏳    
- ⏳    ( )

---

##  6.  

###    ()
1. **  RAG **
   - / →   
   - Fallback 
   
2. **  **
   -   +   
   - KCA/ECMC/KCDRC 

3. **  **
   - , ,     

###    ()
1. ** (Re-ranking)**
   -  
   - ,  

2. ** **
   -   
   -    

###    ()
1. **  **
   - Fallback 
   -   

2. **  **
   -   
   -  

---

##  7. 

###   

 ** **
-     (500-800)
-   Overlapping
-   

 ** **
-   ( )
-    ( )
-   

###  

-    : **  95%**
-  GPU  : ** 5%**
-    : **  **
-   : **  **

** **:     **   **,   **  RAG **   

---

****: AI Assistant  
** **: 1.0  
** **: 2026-01-06
