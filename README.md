# 똑소리 (ddoksori_demo)

**한국 소비자 분쟁 조정을 위한 멀티 에이전트 챗봇 시스템**

## 1. 프로젝트 개요

본 프로젝트는 복잡하고 전문적인 한국의 소비자 분쟁 관련 문의에 대해 정확하고 신뢰도 높은 답변을 제공하는 MAS(Multi-Agent System) 챗봇을 개발하는 것을 목표로 합니다. React, FastAPI, LangGraph, PostgreSQL 등 현대적인 기술 스택을 활용하여, 4년제 컴퓨터공학과 졸업생 수준의 개발자가 이해하고 기여할 수 있는 모범적인 프로젝트 구조를 제시합니다.

**주요 데이터 소스:**
- KCA, ECMC, KCDRC의 분쟁조정사례집
- 한국소비자원, 소비자24의 상담사례
- 한국소비자원의 소비자분쟁조정기준
- 대한민국 법령

## 2. 시스템 아키텍처

### 2.1. 전체 시스템 아키텍처

```mermaid
graph TB
    subgraph "Frontend Layer - React Application"
        A[사용자] -->|질문 입력| B[Chat Interface]
        B -->|HTTP/WebSocket| C[API Client]
    end
    
    subgraph "Backend Layer - FastAPI Server"
        C -->|REST API| D[API Gateway]
        D --> E[Session Manager]
        D --> F[WebSocket Handler]
        
        E --> G[LangGraph Orchestrator]
        
        subgraph "Multi-Agent System"
            G -->|1. 질의 분석| H[Query Analysis Agent]
            H -->|질의 분류 & 키워드 추출| I[Routing Decision]
            
            I -->|2. 정보 검색| J[Information Retrieval Agent]
            J -->|Vector Search| K[Vector Search Module]
            J -->|Keyword Search| L[Keyword Search Module]
            J -->|Hybrid Search| M[Hybrid Ranking Module]
            
            I -->|3. 답변 생성| N[Answer Generation Agent]
            M -->|검색 결과 전달| N
            N -->|초안 생성| O[LLM API Claude/GPT]
            
            O -->|4. 법률 검토| P[Legal Review Agent]
            P -->|최종 검토| O
            P -->|검증 완료| Q[Response Formatter]
        end
        
        Q -->|출처 포함 답변| F
        F -->|실시간 스트리밍| C
    end
    
    subgraph "Data Layer - PostgreSQL with pgvector"
        K -->|코사인 유사도 검색| R[(Vector Store)]
        L -->|전문 검색| S[(Relational Tables)]
        
        subgraph "Database Schema"
            R -->|임베딩 벡터| T[chunks 테이블]
            S -->|메타데이터| U[documents 테이블]
            T -.참조.- U
            T -.관계.- V[chunk_relations 테이블]
        end
        
        subgraph "Data Sources"
            U -->|법령 데이터| W[법제처 법령 11건]
            U -->|상담사례| X[소비자24 상담 13,544건]
            U -->|분쟁조정사례| Y[KCA/ECMC/KCDRC 3,173건]
        end
    end
    
    subgraph "External Services"
        O -.LLM API 호출.- Z[OpenAI GPT-4]
        O -.LLM API 호출.- AA[Anthropic Claude]
        K -.임베딩 생성.- AB[Embedding API Server]
        AB -->|KURE-v1 1024d| AC[RunPod GPU]
    end
    
    style H fill:#e1f5ff
    style J fill:#e1f5ff
    style N fill:#e1f5ff
    style P fill:#e1f5ff
    style R fill:#fff4e6
    style S fill:#fff4e6
    style Z fill:#f0f0f0
    style AA fill:#f0f0f0
```

### 2.2. 에이전트 간 데이터 흐름

```mermaid
sequenceDiagram
    participant U as 사용자
    participant FE as Frontend<br/>(React)
    participant API as API Gateway<br/>(FastAPI)
    participant Orch as LangGraph<br/>Orchestrator
    participant QA as Query Analysis<br/>Agent
    participant IR as Information<br/>Retrieval Agent
    participant DB as PostgreSQL<br/>(pgvector)
    participant AG as Answer<br/>Generation Agent
    participant LLM as External LLM<br/>(Claude/GPT)
    participant LR as Legal Review<br/>Agent
    
    U->>FE: 질문 입력
    FE->>API: POST /chat/query
    API->>Orch: 세션 생성 & 질의 전달
    
    rect rgb(225, 245, 255)
        Note over Orch,QA: Phase 1: 질의 분석
        Orch->>QA: 질의 분석 요청
        QA->>QA: 질의 유형 분류<br/>(일반/법률/유사사례)
        QA->>QA: 키워드 추출
        QA-->>Orch: 분석 결과 반환
    end
    
    rect rgb(225, 245, 255)
        Note over Orch,DB: Phase 2: 정보 검색
        Orch->>IR: 검색 요청<br/>(질의 + 분석 결과)
        IR->>DB: Vector Search<br/>(임베딩 유사도)
        DB-->>IR: 상위 K개 청크
        IR->>DB: Keyword Search<br/>(전문 검색)
        DB-->>IR: 관련 문서
        IR->>IR: Hybrid Ranking<br/>(재순위화)
        IR-->>Orch: 검색 결과<br/>(청크 + 메타데이터)
    end
    
    rect rgb(225, 245, 255)
        Note over Orch,LLM: Phase 3: 답변 생성
        Orch->>AG: 답변 생성 요청<br/>(질의 + 검색 결과)
        AG->>LLM: 프롬프트 + 컨텍스트
        LLM-->>AG: 초안 답변
        AG->>AG: 출처 정보 추가
        AG-->>Orch: 답변 초안
    end
    
    rect rgb(225, 245, 255)
        Note over Orch,LR: Phase 4: 법률 검토
        Orch->>LR: 검토 요청<br/>(답변 초안)
        LR->>LLM: 법률 검토 프롬프트
        LLM-->>LR: 검토 의견
        LR->>LR: 수정 필요 여부 판단
        alt 수정 필요
            LR->>AG: 재생성 요청
            AG->>LLM: 수정된 프롬프트
            LLM-->>AG: 수정된 답변
        end
        LR-->>Orch: 최종 승인
    end
    
    Orch->>API: 최종 답변 + 출처
    API->>U: 스트리밍 응답
```

### 2.3. 에이전트 역할 및 책임 분리

#### Orchestrator (LangGraph)

**역할**: 총괄 지휘자 (Conductor)

**책임**:
- 전체 워크플로우 정의 (에이전트 호출 순서, 조건부 분기)
- 상태 관리 (State): 각 에이전트의 결과를 공유 상태에 저장하고 다음 에이전트에게 전달
- 에러 처리 및 재시도 로직

**핵심 원칙**: Orchestrator는 "어떻게" (How) 에이전트들을 연결할지만 정의하며, 각 에이전트의 내부 구현에는 관여하지 않습니다.

#### Query Analysis Agent

**역할**: 질의 분석 전문가

**책임**:
- **의도 파악**: 질문의 유형 분류 (일반 문의, 법률 해석, 유사 사례 검색 등)
- **키워드 추출**: 검색에 사용할 핵심 키워드 식별
- **메타데이터 생성**: 검색 필터링에 사용할 메타데이터 생성

**필요성**: 사용자의 모호한 질문을 기계가 이해할 수 있는 구조화된 정보로 변환합니다.

#### Information Retrieval Agent

**역할**: 정보 검색 전문가

**책임**:
- **쿼리 증강**: HyDE, Multi-Query 등을 통해 원본 쿼리를 검색에 더 적합한 형태로 변환
- **다중 검색 전략**: Vector Search, Keyword Search, Hybrid Search 등 다양한 검색 방법 동원
- **재순위화 (Re-ranking)**: 여러 검색 결과를 종합하여 가장 관련성 높은 순서로 정렬

**핵심**: Orchestrator는 단순히 "검색해줘"라고 요청하며, 쿼리 증강과 검색 전략은 이 에이전트가 자율적으로 결정합니다.

#### Answer Generation Agent

**역할**: 답변 생성 전문가

**책임**:
- **프롬프트 엔지니어링**: 검색된 정보를 바탕으로 LLM에게 전달할 최적의 프롬프트 구성
- **LLM 호출**: 외부 LLM (Claude, GPT 등) API 호출
- **출처 관리**: 답변의 근거가 된 출처 정보를 명확히 정리하고 연결

**필요성**: 검색된 "날 것의 정보"를 사용자가 이해하기 쉬운 자연스러운 답변으로 가공합니다.

#### Legal Review Agent

**역할**: 법률 검토 전문가

**책임**:
- **사실 검증 (Fact-checking)**: 생성된 답변이 법률적으로 올바른지, 검색된 정보와 일치하는지 검증
- **환각 (Hallucination) 방지**: LLM이 만들어낸 허위 정보를 필터링
- **어조 및 표현 수정**: 법률 용어를 더 쉽고 정확하게 다듬음

**필요성**: 법률이라는 민감한 도메인에서 신뢰성과 안정성을 확보하기 위한 필수적인 장치입니다.

#### 설계 원칙

| 원칙 | 설명 |
|:---|:---|
| **단일 책임** | 각 에이전트는 하나의 명확한 책임만 가집니다 |
| **캡슐화** | 내부 구현은 숨기고, 인터페이스만 노출합니다 |
| **확장성** | 새로운 에이전트 추가 및 기존 에이전트 교체가 쉬워야 합니다 |
| **명확한 데이터 흐름** | State 객체를 통해 데이터 전달을 명확히 합니다 |

> 💡 **상세 설계 문서**: `docs/rag_architecture_expert_view.md`에서 각 에이전트의 상세 구현 가이드 및 코드 예시를 확인할 수 있습니다.

### 2.3. 배포 아키텍처 (AWS EC2 + Docker)

```mermaid
graph TB
    subgraph "Internet"
        A[사용자 브라우저]
    end
    
    subgraph "AWS EC2 Instance"
        B[Nginx Reverse Proxy<br/>:80, :443]
        
        subgraph "Docker Compose Environment"
            C[Frontend Container<br/>React:5173]
            D[Backend Container<br/>FastAPI:8000]
            E[PostgreSQL Container<br/>pgvector:5432]
            F[Embedding API<br/>:8001]
        end
        
        G[Docker Volume<br/>postgres_data]
        H[Docker Network<br/>ddoksori_network]
    end
    
    subgraph "External Services"
        I[OpenAI API]
        J[Anthropic API]
        K[RunPod GPU Server<br/>Embedding API]
    end
    
    A -->|HTTPS| B
    B -->|Proxy Pass| C
    B -->|Proxy Pass /api| D
    
    C -.내부 통신.- D
    D -.내부 통신.- E
    D -->|HTTP| F
    F -->|HTTP| K
    
    D -->|HTTPS| I
    D -->|HTTPS| J
    
    E -.마운트.- G
    C -.연결.- H
    D -.연결.- H
    E -.연결.- H
    F -.연결.- H
    
    style B fill:#ff9999
    style C fill:#99ccff
    style D fill:#99ff99
    style E fill:#ffff99
    style F fill:#ffcc99
```

### 2.4. 기술 스택 상세

| 영역 | 기술 | 버전/상세 | 목적 |
|---|---|---|---|
| **프론트엔드** | React | 18+ | 사용자 인터페이스 |
| | TypeScript | 5+ | 타입 안전성 확보 |
| | TailwindCSS | 3+ | 유틸리티 기반 스타일링 |
| | Vite | 5+ | 빠른 개발 서버 및 빌드 |
| | React Query | - | 서버 상태 관리 |
| | WebSocket | - | 실시간 답변 스트리밍 |
| **백엔드** | FastAPI | 0.100+ | 비동기 API 서버 |
| | LangGraph | 0.0.40+ | Multi-Agent 오케스트레이션 |
| | LangChain | 0.1+ | LLM 통합 및 프롬프트 관리 |
| | Pydantic | 2+ | 데이터 검증 및 직렬화 |
| | psycopg2 | 2.9+ | PostgreSQL 연결 |
| **데이터베이스** | PostgreSQL | 16 | 관계형 데이터베이스 |
| | pgvector | 0.5+ | 벡터 유사도 검색 (IVFFlat) |
| | **데이터 규모** | 30,754개 청크 | 법령(5,455) + 상담(13,544) + 분쟁(11,755) |
| **AI/ML** | OpenAI GPT-4 | - | 답변 생성 |
| | Anthropic Claude 3 | - | 법률 검토 |
| | KURE-v1 | 1024차원 | 한국어 임베딩 모델 |
| | RunPod GPU | - | 임베딩 API 서버 |
| **인프라** | Docker Compose | - | 로컬 개발 환경 |
| | AWS EC2 | - | 프로덕션 배포 |
| | Nginx | - | 리버스 프록시 및 SSL 종료 |
| | Docker Volume | - | 데이터 영속성 |

## 3. PR 단위 개발 로드맵

본 프로젝트는 주요 기능 단위로 Pull Request(PR)를 생성하여 체계적으로 개발을 진행합니다. 각 PR은 전문 Persona(RAG Data Scientist, AI/MAS System Engineer, Data Scientist)의 관점에서 검토되어 높은 품질을 보장합니다.

### 개발 진행 순서

| 진행 순서 | PR # | 주요 기능 | 상세 개발 내용 | 검토 Persona |
|:---|:---|:---|:---|:---|
| 1 | 1 | **RAG 파이프라인 고도화 및 테스트 체계 확립** | - **테스트 스크립트 통합**: `interactive_rag_test.py`를 중심으로 Vanilla RAG, Self-RAG, CRAG 등 다양한 RAG 아키텍처를 평가할 수 있는 단일 테스트 스크립트로 통합<br>- **불필요한 테스트 제거**: 로컬/Runpod 환경에 따라 분리된 단순 테스트 케이스 제거 (Cosine 유사도, BM25, Hybrid Search, SPLADE 등)<br>- **Golden Set 생성 알고리즘 점검**: `dataset_generator.py`의 로직을 검토하여, 실제 사용자 질의와 평가 목적에 더 부합하는 데이터셋 생성<br>- **테스트 결과 저장 스크립트 점검**: `run_evaluation.py` 및 `analyze_rag_results.py`를 검토하여 테스트 결과를 체계적으로 저장하고 시각화 | **RAG Data Scientist** |
| 2 | 2 | **MAS - 답변 생성 및 검토 에이전트 구현** | - **답변 생성 에이전트**: 기존 `RAGGenerator`를 LangGraph 에이전트로 전환하여 검색된 정보를 바탕으로 답변 초안 생성<br>- **답변 검토 에이전트**: 생성된 답변의 사실성, 법적 표현의 적절성 등을 검토하는 에이전트 신규 구현 (LLM + 필요시 Chrome MCP 활용)<br>- **가드레일 설정**: "법적 판단"으로 해석될 수 있는 표현을 "유사 사례 제공" 및 "절차 안내" 중심으로 수정<br>- **분쟁조정기관 정보 제공**: 적합한 분쟁조정기관 제공, 절차 안내, 제출 양식 안내, 사용자 맞춤 내용 생성 기능 구현 | **AI/MAS System Engineer** |
| 3 | 5 | **데이터 임베딩 파이프라인 개선** | - **임베딩 알고리즘 분석**: `embed_data_remote.py`의 전처리 및 품질 검증 로직을 데이터 유형(법령, 사례 등)에 맞게 최적화<br>- **스키마 및 청킹 전략 검토**: 현재 DB 스키마(`schema_v2_final.sql`)의 효율성 분석. 청킹 방식 변경 시 "일관된 스키마 유지 후 청킹 방식만 변경"하는 접근법 적용<br>- **품질 관리**: 저품질 텍스트/임베딩을 필터링하고, 임베딩 결과의 분포를 시각적으로 확인하는 단계 추가<br>- **데이터 타입별 최적화**: 법령, 분쟁조정사례, 피해구제사례, 분쟁조정기준에 대한 임베딩 전략 개별 최적화 | **Data Scientist** |
| 4 | 6 | **종합 평가 및 성능 튜닝** | - **정량 평가 자동화**: RAGAS 등을 활용하여 Context Precision/Recall, Faithfulness, Answer Relevancy 등 RAG 파이프라인 성능 측정<br>- **에이전트별 성능 측정**: 각 에이전트의 성능을 개별적으로 측정하고, 전체 시스템의 End-to-End 성능 평가<br>- **하이퍼파라미터 튜닝**: 평가 결과를 바탕으로 각 컴포넌트(청킹, 임베딩, 검색, 생성)의 하이퍼파라미터 최적화<br>- **벤치마크 구축**: 다양한 RAG 전략(Vanilla, Self-RAG, CRAG)의 성능 비교 및 최적 전략 선정 | **RAG Data Scientist** |
| 5 | 3 | **MAS - 질의 분석 및 검색 에이전트 구현** | - **질의 분석 에이전트**: 사용자 질문의 의도를 파악하고, 검색에 필요한 구조화된 정보(키워드, 필터 등)를 생성하는 에이전트 신규 구현<br>- **검색 에이전트**: 질의 분석 에이전트로부터 받은 정보를 활용하여 `hybrid_retriever`를 실행. LLM 없이 데이터베이스 검색 역할만 수행<br>- **계층적 검색 전략**: 법령 → 기준 → 분쟁조정사례 → 피해구제사례 순으로 검색하는 Fallback 메커니즘 구현 | **AI/MAS System Engineer** |
| 6 | 4 | **MAS - 오케스트레이터 및 모델 최적화** | - **오케스트레이터 구현**: LangGraph를 사용하여 질의 분석 → 검색 → 답변 생성 → 답변 검토 순으로 에이전트들을 연결하는 전체 워크플로우 완성<br>- **에이전트별 LLM 선정**: 각 에이전트의 역할에 맞는 최적 LLM 모델 검토 및 적용<br>  - *오케스트레이터/질의분석*: Rule-base 또는 소형 LLM (e.g., Llama3-8B-Instruct) 적용 가능성 검토<br>  - *답변생성/검토*: 고성능 LLM (e.g., GPT-4o, Claude 3 Opus) 사용<br>- **비용 최적화**: 로컬 모델(Ollama, Hugging Face)을 일반 작업에 우선 활용하고, API 기반 모델은 고난이도 추론 영역에만 사용 | **AI/MAS System Engineer** |

## 4. 평가 전략

- **정량 평가**: `Ragas` 라이브러리를 활용하여 Context Precision/Recall, Faithfulness, Answer Relevancy 등 RAG 파이프라인 성능 측정
- **정성 평가**: 법률 전문가 및 일반인 평가단을 통해 답변의 유용성, 명확성, 신뢰성 검증
- **테스트**: Golden Set(평가 데이터셋) 기반 자동화된 파이프라인 평가 및 A/B 테스트 진행

## 5. 시작하기 (Getting Started)

```bash
# 1. 리포지토리 클론
git clone https://github.com/Maroco0109/ddoksori_demo.git
cd ddoksori_demo

# 2. 환경 변수 설정
# .env 파일을 생성하고 필요한 API 키 등을 입력합니다.

# 3. Docker Compose를 사용하여 서비스 실행
docker-compose up --build
```

## 6. 문서 및 가이드

### 6.1. 데이터베이스 및 임베딩

- **[pgvector Schema 생성 - 임베딩 - 데이터 로드 가이드](docs/guides/embedding_process_guide.md)**
  - PostgreSQL + pgvector 환경 설정
  - 스키마 생성 및 데이터 로드 프로세스
  - 임베딩 생성 및 검증 방법

- **[pgvector 팀원 공유 가이드](docs/guides/pgvector_sharing_guide.md)**
  - 데이터베이스 백업 및 복원 방법
  - 팀원과 pgvector 공유하는 step-by-step 가이드
  - Docker 기반 공유 방법

- **[Vector DB 관리 가이드](docs/guides/Vector_DB_관리_가이드.md)**
  - Vector DB 상태 확인 및 관리
  - 백업 및 복원 전략
  - 품질 관리 및 트러블슈팅

### 6.2. RAG 시스템 테스트

- **[인터랙티브 RAG 테스트 도구](tests/rag/interactive_rag_test.py)**
  - CLI 기반 인터랙티브 테스트 인터페이스
  - 단일 검색 vs 멀티 스테이지 검색 비교 분석
  - 유사도 통계 및 기관 추천 결과 비교
  - 결과 저장 및 CSV 내보내기

**사용 방법**:
```bash
conda activate ddoksori
python tests/rag/interactive_rag_test.py
```

### 6.3. 기타 문서

- [RAG 아키텍처 전문가 뷰](docs/guides/rag_architecture_expert_view.md) - 에이전트 상세 설계
- [백엔드 스크립트 가이드](docs/backend/scripts/embedding_scripts.md) - 임베딩 스크립트 사용법
- [RAG 시스템 테스트 가이드](docs/backend/scripts/TEST_README.md) - 테스트 스크립트 사용법
