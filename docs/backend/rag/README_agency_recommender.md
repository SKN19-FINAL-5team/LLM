#    (Agency Recommender)

## 

         .

###  

1. ** (KCA)** -    
2. ** (ECMC)** -       
3. ** (KCDRC)** -     

---

##  

###   (  70% +   30%)

```python
 = ( × 0.7) + ( × 0.3)
```

#### 1.    (Rule-based Scoring)

        .

** :**

- **ECMC**: , , , , , G 
- **KCDRC**: , , , , ,  
- **KCA**: , , , , ,  

** :**
```python
score = log(1 + match_count) / log(1 + total_keywords)
```

      .

#### 2.    (Statistics-based Scoring)

        .

** :**
```python
score = Σ(rank_weight × similarity)
rank_weight = 1 / (rank + 1)  #    
```

       .

---

## 

###  

```python
from app.rag.agency_recommender import AgencyRecommender

recommender = AgencyRecommender()

#  
query = "   "
recommendations = recommender.recommend(query, search_results, top_n=2)

for agency_code, score, info in recommendations:
    print(f"{info['name']}: {score:.4f}")
```

###    

```python
from app.rag.retriever import VectorRetriever
from app.rag.agency_recommender import AgencyRecommender

#  
retriever = VectorRetriever(db_config)
search_results = retriever.search(query, top_k=5)

#  
recommender = AgencyRecommender()
recommendations = recommender.recommend(query, search_results, top_n=2)
```

###   

```python
explanation = recommender.explain_recommendation(query, search_results)

print(" :")
for rec in explanation['recommendations']:
    print(f"{rec['rank']}: {rec['agency_name']}")
    print(f"  : {rec['final_score']:.4f}")
    print(f"  : {rec['description']}")

print("\n  :")
for agency, count in explanation['search_results_distribution'].items():
    print(f"  {agency}: {count}")
```

###    

```python
formatted_text = recommender.format_recommendation_text(query, search_results)
print(formatted_text)
```

** :**
```
  : 
        
   ( : 0.96)

  : 
       (, , ,  )
   ( : 0.48)

   :
   - : 3
   - : 1
```

---

## API  

### FastAPI 

```python
from fastapi import APIRouter
from app.rag.retriever import VectorRetriever
from app.rag.agency_recommender import AgencyRecommender

router = APIRouter()

@router.post("/recommend-agency")
async def recommend_agency(query: str):
    """  API"""
    #  
    retriever = VectorRetriever(db_config)
    search_results = retriever.search(query, top_k=5)
    
    #  
    recommender = AgencyRecommender()
    explanation = recommender.explain_recommendation(query, search_results)
    
    return {
        "query": query,
        "recommendations": explanation['recommendations'],
        "search_distribution": explanation['search_results_distribution']
    }
```

---

## 

###  

```python
#      (80:20)
recommender = AgencyRecommender(rule_weight=0.8, stat_weight=0.2)

#      (50:50)
recommender = AgencyRecommender(rule_weight=0.5, stat_weight=0.5)
```

###   

```python
class CustomAgencyRecommender(AgencyRecommender):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        #  
        self.KEYWORD_RULES['ecmc'].extend([
            '', '', ''
        ])
        
        self.KEYWORD_RULES['kcdrc'].extend([
            '', '', 'OTT'
        ])
```

---

##  

### 

1. **  **:   O(n),   O(k) (k=  )
2. ** **:        
3. ****:       
4. ****:     

### 

1.      
2.        
3.        

---

## 

###  

```bash
conda run -n ddoksori python backend/scripts/test_agency_recommender.py
```

** :**
-    
-    
-  
-  
-  
-   (  ,    )
-  

###   ( DB)

```bash
conda run -n ddoksori python backend/scripts/test_agency_with_real_data.py
```

---

##   

###  (1-2)

1. **   **
   -    
   -  :   (, ) 

2. **A/B  **
   -    
   -   

###  (1-2)

1. **   **
   -       
   - :  +  

2. **  **
   -   
   -    

###  (3+)

1. **  **
   -      
   -   

2. ** **
   - ,     

---

##  

- [    ](./agency_recommender.py)
- [ ](../../scripts/test_agency_recommender.py)
- [RAG   ](../../../.cursor/plans/rag_____d5ed84e3.plan.md)
