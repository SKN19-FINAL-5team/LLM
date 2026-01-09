# Multi-Agent System  

****: 2026-01-07  
****: Multi-Agent System Product Manager  
** **:    
****: v1.0  
** **:   (Python, FastAPI, LangGraph)

---

## 

    Multi-Agent System    . LangGraph  Jurisdiction / Precedent / Consultation Agent   .

###  
- Python 3.11+
- Conda : `ddoksori`
- PostgreSQL  
-  RAG   (hybrid_retriever, query_analyzer )

---

## 1.  

### 1.1  

```
backend/app/mas/
 __init__.py
 state.py                    # LangGraph State 
 supervisor.py               # Supervisor (Orchestrator)
 agents/
    __init__.py
    jurisdiction_agent.py   #   
    precedent_agent.py      #  
    consultation_agent.py   #   (Fallback)
 prompts/
    __init__.py
    jurisdiction_prompt.py  # Jurisdiction Agent 
    precedent_prompt.py     # Precedent Agent 
    consultation_prompt.py  # Consultation Agent 
 utils/
     __init__.py
     llm_client.py           # OpenAI/Claude API 
     response_formatter.py   #  
```

### 1.2  

```bash
cd /home/maroco/ddoksori_demo/backend/app
mkdir -p mas/agents mas/prompts mas/utils
touch mas/__init__.py mas/agents/__init__.py mas/prompts/__init__.py mas/utils/__init__.py
```

---

## 2. State  (state.py)

LangGraph  **State **.    State  .

### 2.1 

```python
# backend/app/mas/state.py

from typing import TypedDict, List, Dict, Optional, Annotated
from langgraph.graph import add_messages

class MASState(TypedDict):
    """Multi-Agent System State"""
    
    # =====  =====
    query: str                              #  
    user_id: Optional[str]                  #  ID ()
    session_id: Optional[str]               #  ID ()
    
    # ===== Query Analysis  =====
    query_type: str                         # LEGAL, PRACTICAL, PRODUCT_SPECIFIC, GENERAL
    extracted_items: List[str]              #   (: [''])
    extracted_articles: List[str]           #   (: [' 750'])
    dispute_types: List[str]                #  (: ['', ''])
    
    # ===== Jurisdiction Agent  =====
    applicable_laws: List[Dict]             #   
    applicable_criteria: List[Dict]         #   
    jurisdiction: Optional[str]             #   ('KCA', 'ECMC', 'KCDRC')
    jurisdiction_reasoning: str             #   
    
    # ===== Precedent Agent  =====
    precedent_cases: List[Dict]             #  
    precedent_found: bool                   #   
    precedent_count: int                    #   
    
    # ===== Consultation Agent  (Fallback) =====
    consultation_cases: List[Dict]          #  
    consultation_count: int                 #   
    
    # =====   =====
    answer: str                             #   ( )
    sources: List[Dict]                     #   
    confidence: float                       #   (0.0-1.0)
    disclaimer: str                         #  
    
    # =====  =====
    processing_time: float                  #   ()
    agent_logs: Annotated[List[Dict], add_messages]  #  
    error_message: Optional[str]            #   ( )
```

### 2.2 

- **TypedDict**:   , IDE 
- **Annotated[List[Dict], add_messages]**: LangGraph    
- **Optional**:   

---

## 3. Query Analysis (state.py  )

Supervisor     .

### 3.1 

```python
# backend/app/mas/state.py ()

from backend.app.rag.query_analyzer import QueryAnalyzer

def query_analysis_node(state: MASState) -> MASState:
    """
      
    """
    import time
    start_time = time.time()
    
    analyzer = QueryAnalyzer()
    analysis = analyzer.analyze(state['query'])
    
    # State 
    state['query_type'] = analysis.query_type.value
    state['extracted_items'] = analysis.extracted_items
    state['extracted_articles'] = analysis.extracted_articles
    state['dispute_types'] = analysis.dispute_types
    
    #  
    if 'agent_logs' not in state:
        state['agent_logs'] = []
    
    state['agent_logs'].append({
        "agent": "query_analysis",
        "timestamp": time.time(),
        "duration": time.time() - start_time,
        "output": {
            "query_type": analysis.query_type.value,
            "extracted_items": analysis.extracted_items[:3],  #  3
            "dispute_types": analysis.dispute_types[:3]
        }
    })
    
    return state
```

---

## 4. Jurisdiction Agent (jurisdiction_agent.py)

     .

### 4.1 

```python
# backend/app/mas/agents/jurisdiction_agent.py

import time
from typing import Dict
from backend.app.rag.specialized_retrievers.law_retriever import LawRetriever
from backend.app.rag.specialized_retrievers.criteria_retriever import CriteriaRetriever
from backend.app.mas.state import MASState
from backend.app.mas.utils.llm_client import get_llm_response
from backend.app.mas.prompts.jurisdiction_prompt import JURISDICTION_PROMPT
import os

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'ddoksori'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'postgres')
}

def jurisdiction_agent(state: MASState) -> MASState:
    """
    Jurisdiction Agent:  +   →   
    """
    start_time = time.time()
    
    query = state['query']
    extracted_items = state.get('extracted_items', [])
    dispute_types = state.get('dispute_types', [])
    
    # 1.  
    law_retriever = LawRetriever(DB_CONFIG)
    laws = law_retriever.search(
        query=query,
        top_k=5
    )
    
    # 2.  
    criteria_retriever = CriteriaRetriever(DB_CONFIG)
    criteria = criteria_retriever.search(
        query=query,
        item_names=extracted_items,
        dispute_types=dispute_types,
        top_k=5
    )
    
    # 3.    (LLM )
    prompt = JURISDICTION_PROMPT.format(
        query=query,
        extracted_items=extracted_items,
        dispute_types=dispute_types,
        laws=format_laws(laws),
        criteria=format_criteria(criteria)
    )
    
    llm_response = get_llm_response(prompt, model="gpt-4o-mini")
    
    # 4. LLM  
    import json
    try:
        result = json.loads(llm_response)
        jurisdiction = result.get('jurisdiction', 'KCA')  #  KCA
        reasoning = result.get('reasoning', '')
    except:
        # JSON    
        jurisdiction = 'KCA'
        reasoning = ' ,  '
    
    # State 
    state['applicable_laws'] = laws
    state['applicable_criteria'] = criteria
    state['jurisdiction'] = jurisdiction
    state['jurisdiction_reasoning'] = reasoning
    
    #  
    state['agent_logs'].append({
        "agent": "jurisdiction_agent",
        "timestamp": time.time(),
        "duration": time.time() - start_time,
        "output": {
            "jurisdiction": jurisdiction,
            "laws_count": len(laws),
            "criteria_count": len(criteria)
        }
    })
    
    return state


def format_laws(laws: list) -> str:
    """   """
    if not laws:
        return "    ."
    
    formatted = []
    for i, law in enumerate(laws[:3], 1):  #  3
        formatted.append(
            f"{i}. {law.get('content', '')[:200]}...\n"
            f"   (: {law.get('score', 0):.2f})"
        )
    return "\n\n".join(formatted)


def format_criteria(criteria: list) -> str:
    """   """
    if not criteria:
        return "    ."
    
    formatted = []
    for i, crit in enumerate(criteria[:3], 1):
        formatted.append(
            f"{i}. {crit.get('content', '')[:200]}...\n"
            f"   (: {crit.get('score', 0):.2f})"
        )
    return "\n\n".join(formatted)
```

### 4.2  (jurisdiction_prompt.py)

```python
# backend/app/mas/prompts/jurisdiction_prompt.py

JURISDICTION_PROMPT = """
     .

      :

****: {query}

** **: {extracted_items}

****: {dispute_types}

** **:
{laws}

** **:
{criteria}

---

**  **:
- **KCA ()**:   
- **ECMC ()**: ,  
- **KCDRC ()**:   

** **:
1. "", "", ""  → ECMC
2. "",  (: "", "") → KCDRC
3.  → KCA

** ** (JSON):
{{
  "jurisdiction": "KCA | ECMC | KCDRC",
  "reasoning": "  2-3 ",
  "confidence": 0.0-1.0
}}

JSON .    .
"""
```

---

## 5. Precedent Agent (precedent_agent.py)

 .

### 5.1 

```python
# backend/app/mas/agents/precedent_agent.py

import time
from backend.app.mas.state import MASState
from backend.app.rag.specialized_retrievers.case_retriever import CaseRetriever
import os

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'ddoksori'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'postgres')
}

def precedent_agent(state: MASState) -> MASState:
    """
    Precedent Agent:  
    """
    start_time = time.time()
    
    query = state['query']
    jurisdiction = state.get('jurisdiction', 'KCA')
    
    #  
    case_retriever = CaseRetriever(DB_CONFIG)
    cases = case_retriever.search(
        query=query,
        top_k=10,
        filters={
            'doc_type': 'mediation_case',
            'source_org': jurisdiction  #  
        },
        chunk_types=['decision', 'judgment', 'reasoning']  #  
    )
    
    # State 
    state['precedent_cases'] = cases[:5]  #  5 
    state['precedent_found'] = len(cases) > 0
    state['precedent_count'] = len(cases)
    
    #  
    state['agent_logs'].append({
        "agent": "precedent_agent",
        "timestamp": time.time(),
        "duration": time.time() - start_time,
        "output": {
            "precedent_found": len(cases) > 0,
            "precedent_count": len(cases)
        }
    })
    
    return state
```

---

## 6. Consultation Agent (consultation_agent.py)

  (Fallback).

### 6.1 

```python
# backend/app/mas/agents/consultation_agent.py

import time
from backend.app.mas.state import MASState
from backend.app.rag.specialized_retrievers.case_retriever import CaseRetriever
import os

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'ddoksori'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'postgres')
}

def consultation_agent(state: MASState) -> MASState:
    """
    Consultation Agent:   (Fallback)
    """
    start_time = time.time()
    
    query = state['query']
    
    #  
    case_retriever = CaseRetriever(DB_CONFIG)
    cases = case_retriever.search(
        query=query,
        top_k=10,
        filters={
            'doc_type': 'counsel_case',
            'source_org': 'consumer.go.kr'
        }
    )
    
    # State 
    state['consultation_cases'] = cases[:5]
    state['consultation_count'] = len(cases)
    
    #  
    state['agent_logs'].append({
        "agent": "consultation_agent",
        "timestamp": time.time(),
        "duration": time.time() - start_time,
        "output": {
            "consultation_count": len(cases)
        }
    })
    
    return state
```

---

## 7. Answer Generation (supervisor.py  )

  .

### 7.1 

```python
# backend/app/mas/supervisor.py ()

from backend.app.mas.prompts.answer_prompt import ANSWER_PROMPT

def generate_answer_node(state: MASState) -> MASState:
    """
       
    """
    start_time = time.time()
    
    #  
    query = state['query']
    laws = state.get('applicable_laws', [])
    criteria = state.get('applicable_criteria', [])
    precedent_cases = state.get('precedent_cases', [])
    consultation_cases = state.get('consultation_cases', [])
    jurisdiction = state.get('jurisdiction', 'KCA')
    
    #   (precedent ,  consultation)
    if precedent_cases:
        cases = precedent_cases
        case_type = ""
    else:
        cases = consultation_cases
        case_type = ""
    
    #  
    prompt = ANSWER_PROMPT.format(
        query=query,
        laws=format_sources(laws),
        criteria=format_sources(criteria),
        cases=format_sources(cases),
        case_type=case_type,
        jurisdiction=jurisdiction
    )
    
    # LLM 
    answer = get_llm_response(prompt, model="gpt-4o-mini", max_tokens=1500)
    
    #  
    sources = []
    for law in laws[:3]:
        sources.append({
            "type": "law",
            "content": law.get('content', '')[:100],
            "score": law.get('score', 0)
        })
    for crit in criteria[:3]:
        sources.append({
            "type": "criteria",
            "content": crit.get('content', '')[:100],
            "score": crit.get('score', 0)
        })
    for case in cases[:3]:
        sources.append({
            "type": case_type,
            "content": case.get('content', '')[:100],
            "score": case.get('score', 0)
        })
    
    #  
    disclaimer = (
        f"      ,    . "
        f"   {jurisdiction}   ."
    )
    
    # State 
    state['answer'] = answer
    state['sources'] = sources
    state['confidence'] = calculate_confidence(state)
    state['disclaimer'] = disclaimer
    state['processing_time'] = time.time() - start_time
    
    #  
    state['agent_logs'].append({
        "agent": "generate_answer",
        "timestamp": time.time(),
        "duration": time.time() - start_time,
        "output": {
            "answer_length": len(answer),
            "sources_count": len(sources)
        }
    })
    
    return state


def calculate_confidence(state: MASState) -> float:
    """  """
    score = 0.5  # 
    
    if state.get('precedent_found'):
        score += 0.3  #  
    elif state.get('consultation_count', 0) > 0:
        score += 0.1  #  
    
    if len(state.get('applicable_laws', [])) > 0:
        score += 0.1  #  
    
    if len(state.get('applicable_criteria', [])) > 0:
        score += 0.1  #  
    
    return min(score, 1.0)
```

---

## 8. Supervisor (Graph )

LangGraph   .

### 8.1 

```python
# backend/app/mas/supervisor.py

from langgraph.graph import StateGraph, END
from backend.app.mas.state import MASState, query_analysis_node
from backend.app.mas.agents.jurisdiction_agent import jurisdiction_agent
from backend.app.mas.agents.precedent_agent import precedent_agent
from backend.app.mas.agents.consultation_agent import consultation_agent

def should_use_consultation(state: MASState) -> str:
    """
     :    Fallback
    """
    if state.get('precedent_found', False) and len(state.get('precedent_cases', [])) > 0:
        return "generate_answer"  #  
    else:
        return "consultation_agent"  #  


def build_mas_graph():
    """
    MAS Graph 
    """
    # Graph 
    graph = StateGraph(MASState)
    
    #  
    graph.add_node("query_analysis", query_analysis_node)
    graph.add_node("jurisdiction_agent", jurisdiction_agent)
    graph.add_node("precedent_agent", precedent_agent)
    graph.add_node("consultation_agent", consultation_agent)
    graph.add_node("generate_answer", generate_answer_node)
    
    #  
    graph.set_entry_point("query_analysis")
    
    graph.add_edge("query_analysis", "jurisdiction_agent")
    graph.add_edge("jurisdiction_agent", "precedent_agent")
    
    #   (   ,   )
    graph.add_conditional_edges(
        "precedent_agent",
        should_use_consultation,
        {
            "generate_answer": "generate_answer",
            "consultation_agent": "consultation_agent"
        }
    )
    
    graph.add_edge("consultation_agent", "generate_answer")
    graph.add_edge("generate_answer", END)
    
    # 
    return graph.compile()


#  
if __name__ == "__main__":
    mas_graph = build_mas_graph()
    
    initial_state = {
        "query": "   1    .   ?"
    }
    
    result = mas_graph.invoke(initial_state)
    
    print("=" * 80)
    print(":", result['query'])
    print("=" * 80)
    print("\n:")
    print(result['answer'])
    print("\n:", result['jurisdiction'])
    print(":", result['confidence'])
    print(" :", result['processing_time'], "")
    print("\n :")
    print(result['disclaimer'])
```

---

## 9. LLM Client (utils/llm_client.py)

OpenAI API .

### 9.1 

```python
# backend/app/mas/utils/llm_client.py

import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def get_llm_response(prompt: str, model: str = "gpt-4o-mini", max_tokens: int = 1000) -> str:
    """
    LLM API 
    """
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "     ."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.3  #    
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"LLM API : {e}")
        return " .  ."
```

---

## 10. FastAPI 

### 10.1  

```python
# backend/app/main.py 

from backend.app.mas.supervisor import build_mas_graph

# Graph  (    )
mas_graph = build_mas_graph()

@app.post("/mas/chat")
async def mas_chat(request: ChatRequest):
    """
    Multi-Agent System  
    """
    initial_state = {
        "query": request.message
    }
    
    try:
        result = mas_graph.invoke(initial_state)
        
        return {
            "answer": result['answer'],
            "jurisdiction": result['jurisdiction'],
            "confidence": result['confidence'],
            "disclaimer": result['disclaimer'],
            "sources": result['sources'],
            "processing_time": result['processing_time']
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

## 11. 

### 11.1  

```python
# tests/unit/test_mas_agents.py

def test_jurisdiction_agent():
    """Jurisdiction Agent """
    state = {
        'query': '    .',
        'extracted_items': [''],
        'dispute_types': [''],
        'agent_logs': []
    }
    
    result = jurisdiction_agent(state)
    
    assert result['jurisdiction'] == 'ECMC'  #   → ECMC
    assert len(result['applicable_laws']) > 0
```

### 11.2  

```python
# tests/integration/test_mas_workflow.py

def test_full_workflow():
    """ MAS  """
    mas_graph = build_mas_graph()
    
    result = mas_graph.invoke({
        "query": "   ?"
    })
    
    assert 'answer' in result
    assert result['jurisdiction'] in ['KCA', 'ECMC', 'KCDRC']
    assert len(result['sources']) > 0
```

---

## 12. 

    **2-3  MAS MVP**   .

###  
1. Week 1: State + Jurisdiction Agent
2. Week 2: Precedent Agent + Supervisor
3. Week 3: Consultation Agent + 

###  
- [LangGraph  ](https://langchain-ai.github.io/langgraph/)
- [`MAS___.md`](./MAS___.md)
- [`README.md`](../../README.md)

---

****: Multi-Agent System Product Manager  
** **: 2026-01-07
