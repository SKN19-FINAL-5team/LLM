# Multi-Agent System 구현 가이드

**작성일**: 2026-01-07  
**작성자**: Multi-Agent System Product Manager  
**문서 유형**: 구현 가이드  
**버전**: v1.0  
**대상 독자**: 백엔드 개발자 (Python, FastAPI, LangGraph)

---

## 개요

본 문서는 똑소리 프로젝트의 Multi-Agent System을 구현하기 위한 단계별 가이드입니다. LangGraph 기반으로 Jurisdiction / Precedent / Consultation Agent를 구현하는 방법을 제시합니다.

### 전제 조건
- Python 3.11+
- Conda 환경: `ddoksori`
- PostgreSQL 실행 중
- 기존 RAG 시스템 작동 (hybrid_retriever, query_analyzer 등)

---

## 1. 프로젝트 구조

### 1.1 디렉토리 구조

```
backend/app/mas/
├── __init__.py
├── state.py                    # LangGraph State 정의
├── supervisor.py               # Supervisor (Orchestrator)
├── agents/
│   ├── __init__.py
│   ├── jurisdiction_agent.py   # 관할 조정위원회 판단
│   ├── precedent_agent.py      # 분쟁조정사례 검색
│   └── consultation_agent.py   # 상담사례 검색 (Fallback)
├── prompts/
│   ├── __init__.py
│   ├── jurisdiction_prompt.py  # Jurisdiction Agent 프롬프트
│   ├── precedent_prompt.py     # Precedent Agent 프롬프트
│   └── consultation_prompt.py  # Consultation Agent 프롬프트
└── utils/
    ├── __init__.py
    ├── llm_client.py           # OpenAI/Claude API 래퍼
    └── response_formatter.py   # 답변 포맷팅
```

### 1.2 파일 생성

```bash
cd /home/maroco/ddoksori_demo/backend/app
mkdir -p mas/agents mas/prompts mas/utils
touch mas/__init__.py mas/agents/__init__.py mas/prompts/__init__.py mas/utils/__init__.py
```

---

## 2. State 정의 (state.py)

LangGraph의 핵심은 **State 객체**입니다. 모든 에이전트가 이 State를 읽고 수정합니다.

### 2.1 코드

```python
# backend/app/mas/state.py

from typing import TypedDict, List, Dict, Optional, Annotated
from langgraph.graph import add_messages

class MASState(TypedDict):
    """Multi-Agent System State"""
    
    # ===== 입력 =====
    query: str                              # 사용자 질문
    user_id: Optional[str]                  # 사용자 ID (선택)
    session_id: Optional[str]               # 세션 ID (선택)
    
    # ===== Query Analysis 결과 =====
    query_type: str                         # LEGAL, PRACTICAL, PRODUCT_SPECIFIC, GENERAL
    extracted_items: List[str]              # 품목명 리스트 (예: ['냉장고'])
    extracted_articles: List[str]           # 조문번호 리스트 (예: ['민법 제750조'])
    dispute_types: List[str]                # 분쟁유형 (예: ['환불', '교환'])
    
    # ===== Jurisdiction Agent 결과 =====
    applicable_laws: List[Dict]             # 관련 법령 리스트
    applicable_criteria: List[Dict]         # 관련 기준 리스트
    jurisdiction: Optional[str]             # 관할 조정위원회 ('KCA', 'ECMC', 'KCDRC')
    jurisdiction_reasoning: str             # 관할 판단 근거
    
    # ===== Precedent Agent 결과 =====
    precedent_cases: List[Dict]             # 분쟁조정사례 리스트
    precedent_found: bool                   # 사례 발견 여부
    precedent_count: int                    # 발견된 사례 수
    
    # ===== Consultation Agent 결과 (Fallback) =====
    consultation_cases: List[Dict]          # 상담사례 리스트
    consultation_count: int                 # 발견된 상담사례 수
    
    # ===== 최종 답변 =====
    answer: str                             # 최종 답변 (마크다운 형식)
    sources: List[Dict]                     # 출처 정보 리스트
    confidence: float                       # 답변 신뢰도 (0.0-1.0)
    disclaimer: str                         # 면책 조항
    
    # ===== 메타데이터 =====
    processing_time: float                  # 처리 시간 (초)
    agent_logs: Annotated[List[Dict], add_messages]  # 에이전트 로그
    error_message: Optional[str]            # 오류 메시지 (있을 경우)
```

### 2.2 설명

- **TypedDict**: 타입 힌트 제공, IDE 자동완성
- **Annotated[List[Dict], add_messages]**: LangGraph의 메시지 추가 기능 사용
- **Optional**: 필수가 아닌 필드

---

## 3. Query Analysis (state.py 내 함수)

Supervisor 시작 시 질문을 분석하는 노드입니다.

### 3.1 코드

```python
# backend/app/mas/state.py (계속)

from backend.app.rag.query_analyzer import QueryAnalyzer

def query_analysis_node(state: MASState) -> MASState:
    """
    질문 분석 노드
    """
    import time
    start_time = time.time()
    
    analyzer = QueryAnalyzer()
    analysis = analyzer.analyze(state['query'])
    
    # State 업데이트
    state['query_type'] = analysis.query_type.value
    state['extracted_items'] = analysis.extracted_items
    state['extracted_articles'] = analysis.extracted_articles
    state['dispute_types'] = analysis.dispute_types
    
    # 로그 추가
    if 'agent_logs' not in state:
        state['agent_logs'] = []
    
    state['agent_logs'].append({
        "agent": "query_analysis",
        "timestamp": time.time(),
        "duration": time.time() - start_time,
        "output": {
            "query_type": analysis.query_type.value,
            "extracted_items": analysis.extracted_items[:3],  # 처음 3개만
            "dispute_types": analysis.dispute_types[:3]
        }
    })
    
    return state
```

---

## 4. Jurisdiction Agent (jurisdiction_agent.py)

법령과 기준을 검색하여 관할 조정위원회를 판단합니다.

### 4.1 코드

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
    Jurisdiction Agent: 법령 + 기준 검색 → 관할 조정위원회 판단
    """
    start_time = time.time()
    
    query = state['query']
    extracted_items = state.get('extracted_items', [])
    dispute_types = state.get('dispute_types', [])
    
    # 1. 법령 검색
    law_retriever = LawRetriever(DB_CONFIG)
    laws = law_retriever.search(
        query=query,
        top_k=5
    )
    
    # 2. 기준 검색
    criteria_retriever = CriteriaRetriever(DB_CONFIG)
    criteria = criteria_retriever.search(
        query=query,
        item_names=extracted_items,
        dispute_types=dispute_types,
        top_k=5
    )
    
    # 3. 관할 조정위원회 판단 (LLM 호출)
    prompt = JURISDICTION_PROMPT.format(
        query=query,
        extracted_items=extracted_items,
        dispute_types=dispute_types,
        laws=format_laws(laws),
        criteria=format_criteria(criteria)
    )
    
    llm_response = get_llm_response(prompt, model="gpt-4o-mini")
    
    # 4. LLM 응답 파싱
    import json
    try:
        result = json.loads(llm_response)
        jurisdiction = result.get('jurisdiction', 'KCA')  # 기본값 KCA
        reasoning = result.get('reasoning', '')
    except:
        # JSON 파싱 실패 시 기본값
        jurisdiction = 'KCA'
        reasoning = '파싱 실패, 기본값 사용'
    
    # State 업데이트
    state['applicable_laws'] = laws
    state['applicable_criteria'] = criteria
    state['jurisdiction'] = jurisdiction
    state['jurisdiction_reasoning'] = reasoning
    
    # 로그 추가
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
    """법령 리스트를 문자열로 포맷팅"""
    if not laws:
        return "관련 법령을 찾을 수 없습니다."
    
    formatted = []
    for i, law in enumerate(laws[:3], 1):  # 최대 3개
        formatted.append(
            f"{i}. {law.get('content', '')[:200]}...\n"
            f"   (유사도: {law.get('score', 0):.2f})"
        )
    return "\n\n".join(formatted)


def format_criteria(criteria: list) -> str:
    """기준 리스트를 문자열로 포맷팅"""
    if not criteria:
        return "관련 기준을 찾을 수 없습니다."
    
    formatted = []
    for i, crit in enumerate(criteria[:3], 1):
        formatted.append(
            f"{i}. {crit.get('content', '')[:200]}...\n"
            f"   (유사도: {crit.get('score', 0):.2f})"
        )
    return "\n\n".join(formatted)
```

### 4.2 프롬프트 (jurisdiction_prompt.py)

```python
# backend/app/mas/prompts/jurisdiction_prompt.py

JURISDICTION_PROMPT = """
당신은 한국의 소비자 분쟁 조정 전문가입니다.

다음 정보를 바탕으로 적절한 관할 조정위원회를 판단해주세요:

**질문**: {query}

**추출된 품목명**: {extracted_items}

**분쟁유형**: {dispute_types}

**관련 법령**:
{laws}

**관련 기준**:
{criteria}

---

**관할 조정위원회 옵션**:
- **KCA (한국소비자원)**: 일반 소비자 분쟁
- **ECMC (전자거래분쟁조정위원회)**: 전자상거래, 온라인 거래
- **KCDRC (지역분쟁조정위원회)**: 지역별 소비자 분쟁

**판단 기준**:
1. "전자상거래", "온라인", "인터넷" 키워드 → ECMC
2. "지역", 지역명 (예: "서울", "부산") → KCDRC
3. 기본값 → KCA

**출력 형식** (JSON):
{{
  "jurisdiction": "KCA | ECMC | KCDRC",
  "reasoning": "판단 근거를 2-3문장으로 설명",
  "confidence": 0.0-1.0
}}

JSON만 출력하세요. 다른 설명은 포함하지 마세요.
"""
```

---

## 5. Precedent Agent (precedent_agent.py)

분쟁조정사례를 검색합니다.

### 5.1 코드

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
    Precedent Agent: 분쟁조정사례 검색
    """
    start_time = time.time()
    
    query = state['query']
    jurisdiction = state.get('jurisdiction', 'KCA')
    
    # 분쟁조정사례 검색
    case_retriever = CaseRetriever(DB_CONFIG)
    cases = case_retriever.search(
        query=query,
        top_k=10,
        filters={
            'doc_type': 'mediation_case',
            'source_org': jurisdiction  # 관할 조정위원회
        },
        chunk_types=['decision', 'judgment', 'reasoning']  # 중요 섹션만
    )
    
    # State 업데이트
    state['precedent_cases'] = cases[:5]  # 상위 5개만 저장
    state['precedent_found'] = len(cases) > 0
    state['precedent_count'] = len(cases)
    
    # 로그 추가
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

상담사례를 검색합니다 (Fallback).

### 6.1 코드

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
    Consultation Agent: 상담사례 검색 (Fallback)
    """
    start_time = time.time()
    
    query = state['query']
    
    # 상담사례 검색
    case_retriever = CaseRetriever(DB_CONFIG)
    cases = case_retriever.search(
        query=query,
        top_k=10,
        filters={
            'doc_type': 'counsel_case',
            'source_org': 'consumer.go.kr'
        }
    )
    
    # State 업데이트
    state['consultation_cases'] = cases[:5]
    state['consultation_count'] = len(cases)
    
    # 로그 추가
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

## 7. Answer Generation (supervisor.py 내 함수)

최종 답변을 생성합니다.

### 7.1 코드

```python
# backend/app/mas/supervisor.py (일부)

from backend.app.mas.prompts.answer_prompt import ANSWER_PROMPT

def generate_answer_node(state: MASState) -> MASState:
    """
    최종 답변 생성 노드
    """
    start_time = time.time()
    
    # 데이터 준비
    query = state['query']
    laws = state.get('applicable_laws', [])
    criteria = state.get('applicable_criteria', [])
    precedent_cases = state.get('precedent_cases', [])
    consultation_cases = state.get('consultation_cases', [])
    jurisdiction = state.get('jurisdiction', 'KCA')
    
    # 사례 선택 (precedent 우선, 없으면 consultation)
    if precedent_cases:
        cases = precedent_cases
        case_type = "분쟁조정사례"
    else:
        cases = consultation_cases
        case_type = "상담사례"
    
    # 프롬프트 구성
    prompt = ANSWER_PROMPT.format(
        query=query,
        laws=format_sources(laws),
        criteria=format_sources(criteria),
        cases=format_sources(cases),
        case_type=case_type,
        jurisdiction=jurisdiction
    )
    
    # LLM 호출
    answer = get_llm_response(prompt, model="gpt-4o-mini", max_tokens=1500)
    
    # 출처 정리
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
    
    # 면책 조항
    disclaimer = (
        f"본 답변은 제공된 정보를 바탕으로 한 참고용이며, 법적 효력을 갖지 않습니다. "
        f"정확한 판단을 위해서는 {jurisdiction}에 분쟁조정을 신청하시기 바랍니다."
    )
    
    # State 업데이트
    state['answer'] = answer
    state['sources'] = sources
    state['confidence'] = calculate_confidence(state)
    state['disclaimer'] = disclaimer
    state['processing_time'] = time.time() - start_time
    
    # 로그 추가
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
    """답변 신뢰도 계산"""
    score = 0.5  # 기본
    
    if state.get('precedent_found'):
        score += 0.3  # 분쟁조정사례 있음
    elif state.get('consultation_count', 0) > 0:
        score += 0.1  # 상담사례 있음
    
    if len(state.get('applicable_laws', [])) > 0:
        score += 0.1  # 법령 있음
    
    if len(state.get('applicable_criteria', [])) > 0:
        score += 0.1  # 기준 있음
    
    return min(score, 1.0)
```

---

## 8. Supervisor (Graph 구성)

LangGraph로 전체 워크플로우를 구성합니다.

### 8.1 코드

```python
# backend/app/mas/supervisor.py

from langgraph.graph import StateGraph, END
from backend.app.mas.state import MASState, query_analysis_node
from backend.app.mas.agents.jurisdiction_agent import jurisdiction_agent
from backend.app.mas.agents.precedent_agent import precedent_agent
from backend.app.mas.agents.consultation_agent import consultation_agent

def should_use_consultation(state: MASState) -> str:
    """
    조건부 라우팅: 분쟁조정사례가 없으면 상담사례로 Fallback
    """
    if state.get('precedent_found', False) and len(state.get('precedent_cases', [])) > 0:
        return "generate_answer"  # 답변 생성으로
    else:
        return "consultation_agent"  # 상담사례 검색으로


def build_mas_graph():
    """
    MAS Graph 구성
    """
    # Graph 초기화
    graph = StateGraph(MASState)
    
    # 노드 추가
    graph.add_node("query_analysis", query_analysis_node)
    graph.add_node("jurisdiction_agent", jurisdiction_agent)
    graph.add_node("precedent_agent", precedent_agent)
    graph.add_node("consultation_agent", consultation_agent)
    graph.add_node("generate_answer", generate_answer_node)
    
    # 엣지 정의
    graph.set_entry_point("query_analysis")
    
    graph.add_edge("query_analysis", "jurisdiction_agent")
    graph.add_edge("jurisdiction_agent", "precedent_agent")
    
    # 조건부 엣지 (분쟁사례 있으면 답변 생성, 없으면 상담사례 검색)
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
    
    # 컴파일
    return graph.compile()


# 실행 예시
if __name__ == "__main__":
    mas_graph = build_mas_graph()
    
    initial_state = {
        "query": "냉장고를 구매한 지 1개월이 지났는데 냉동실이 작동하지 않습니다. 무상 수리가 가능한가요?"
    }
    
    result = mas_graph.invoke(initial_state)
    
    print("=" * 80)
    print("질문:", result['query'])
    print("=" * 80)
    print("\n답변:")
    print(result['answer'])
    print("\n관할:", result['jurisdiction'])
    print("신뢰도:", result['confidence'])
    print("처리 시간:", result['processing_time'], "초")
    print("\n면책 조항:")
    print(result['disclaimer'])
```

---

## 9. LLM Client (utils/llm_client.py)

OpenAI API 래퍼입니다.

### 9.1 코드

```python
# backend/app/mas/utils/llm_client.py

import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def get_llm_response(prompt: str, model: str = "gpt-4o-mini", max_tokens: int = 1000) -> str:
    """
    LLM API 호출
    """
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "당신은 한국의 소비자 분쟁 조정 전문가입니다."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.3  # 일관성을 위해 낮게 설정
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"LLM API 오류: {e}")
        return "오류가 발생했습니다. 다시 시도해주세요."
```

---

## 10. FastAPI 연동

### 10.1 엔드포인트 추가

```python
# backend/app/main.py에 추가

from backend.app.mas.supervisor import build_mas_graph

# Graph 초기화 (앱 시작 시 한 번만)
mas_graph = build_mas_graph()

@app.post("/mas/chat")
async def mas_chat(request: ChatRequest):
    """
    Multi-Agent System 기반 챗봇
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

## 11. 테스트

### 11.1 단위 테스트

```python
# test/unit/test_mas_agents.py

def test_jurisdiction_agent():
    """Jurisdiction Agent 테스트"""
    state = {
        'query': '온라인으로 구매한 화장품이 알레르기를 유발했습니다.',
        'extracted_items': ['화장품'],
        'dispute_types': ['환불'],
        'agent_logs': []
    }
    
    result = jurisdiction_agent(state)
    
    assert result['jurisdiction'] == 'ECMC'  # 온라인 거래 → ECMC
    assert len(result['applicable_laws']) > 0
```

### 11.2 통합 테스트

```python
# test/integration/test_mas_workflow.py

def test_full_workflow():
    """전체 MAS 파이프라인 테스트"""
    mas_graph = build_mas_graph()
    
    result = mas_graph.invoke({
        "query": "냉장고 환불 기준이 무엇인가요?"
    })
    
    assert 'answer' in result
    assert result['jurisdiction'] in ['KCA', 'ECMC', 'KCDRC']
    assert len(result['sources']) > 0
```

---

## 12. 결론

본 가이드를 따라 구현하면 **2-3주 내에 MAS MVP**를 완성할 수 있습니다.

### 구현 순서
1. Week 1: State + Jurisdiction Agent
2. Week 2: Precedent Agent + Supervisor
3. Week 3: Consultation Agent + 테스트

### 참고 자료
- [LangGraph 공식 문서](https://langchain-ai.github.io/langgraph/)
- [`MAS_아키텍처_평가_보고서.md`](./MAS_아키텍처_평가_보고서.md)
- [`README.md`](../../README.md)

---

**작성자**: Multi-Agent System Product Manager  
**최종 업데이트**: 2026-01-07
