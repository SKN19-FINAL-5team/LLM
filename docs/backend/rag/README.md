# RAG 모듈

똑소리 프로젝트의 RAG (Retrieval-Augmented Generation) 시스템입니다.

## 📁 파일 구조

```
app/rag/
├── __init__.py                    # 모듈 초기화
├── retriever.py                   # 기본 벡터 검색기
├── generator.py                   # LLM 답변 생성기
├── multi_stage_retriever.py       # 멀티 스테이지 검색기 (신규)
└── agency_recommender.py          # 기관 추천 시스템 (신규)
```

## 🔧 모듈 설명

### 1. `VectorRetriever` (retriever.py)
기본 벡터 유사도 검색 기능을 제공합니다.

**주요 기능:**
- 쿼리 임베딩 생성 (KURE-v1)
- 벡터 유사도 검색 (pgvector)
- 청크 타입 및 기관 필터링

### 2. `RAGGenerator` (generator.py)
검색된 청크를 바탕으로 LLM 답변을 생성합니다.

**주요 기능:**
- 컨텍스트 포맷팅
- OpenAI GPT 기반 답변 생성
- 스트리밍 답변 지원

### 3. `MultiStageRetriever` (multi_stage_retriever.py) ✨ 신규
3단계 계층적 검색으로 더 정확하고 풍부한 컨텍스트를 제공합니다.

**주요 기능:**
- Stage 1: 법령 + 분쟁조정기준 병렬 검색
- Stage 2: 분쟁조정사례 검색 (컨텍스트 강화)
- Stage 3: 피해구제사례 검색 (Fallback)
- 지능형 기관 추천 통합

**검색 흐름:**
```
사용자 쿼리
    ↓
Stage 1: 법령 + 기준 검색 (병렬)
    ↓
Stage 2: 분쟁조정사례 검색 (컨텍스트 활용)
    ↓
결과 충분? → No → Stage 3: 피해구제사례 (Fallback)
    ↓ Yes
결과 통합 + 기관 추천
    ↓
최종 결과
```

### 4. `AgencyRecommender` (agency_recommender.py) ✨ 신규
사용자 입력과 검색 결과를 바탕으로 적절한 분쟁조정 기관을 추천합니다.

**주요 기능:**
- 하이브리드 추천 (규칙 기반 + 검색 통계)
- 키워드 기반 기관 매칭
- 검색 결과 분포 분석
- 신뢰도 점수 계산

**지원 기관:**
- `kca`: 한국소비자원 (일반 소비재, 서비스)
- `ecmc`: 한국전자거래분쟁조정위원회 (온라인 거래)
- `kcdrc`: 한국저작권위원회 (디지털 콘텐츠)

## 🚀 사용 예제

### 기본 검색 (VectorRetriever)

```python
from app.rag import VectorRetriever

db_config = {...}
retriever = VectorRetriever(db_config)

# 검색
chunks = retriever.search(
    query="노트북이 불량입니다. 환불 받을 수 있나요?",
    top_k=5,
    chunk_types=['decision', 'judgment'],
    agencies=['kca']
)

retriever.close()
```

### 멀티 스테이지 검색 (MultiStageRetriever)

```python
from app.rag import MultiStageRetriever

retriever = MultiStageRetriever(db_config)

# 멀티 스테이지 검색
results = retriever.search_multi_stage(
    query="쿠팡에서 옷을 샀는데 배송이 안 됩니다.",
    law_top_k=3,
    criteria_top_k=3,
    mediation_top_k=5,
    enable_agency_recommendation=True
)

# 결과 활용
print(f"총 청크: {len(results['all_chunks'])}")
print(f"추천 기관: {results['agency_recommendation']['top_agency']}")
print(f"Fallback 사용: {results['used_fallback']}")

retriever.close()
```

### 기관 추천 (AgencyRecommender)

```python
from app.rag import AgencyRecommender

recommender = AgencyRecommender()

# 추천
recommendations = recommender.recommend(
    user_input="멜론에서 음원을 구매했는데 다운로드가 안 됩니다.",
    search_results=chunks  # 선택적
)

# 최우선 기관
top_agency, info = recommender.get_top_agency(user_input, chunks)
print(f"{info['name']} - {info['contact']}")

# 포맷팅된 추천
formatted = recommender.format_recommendations(recommendations)
print(formatted)
```

### 답변 생성 (RAGGenerator)

```python
from app.rag import RAGGenerator

generator = RAGGenerator()

# 답변 생성
result = generator.generate_answer(
    query="환불 받을 수 있나요?",
    chunks=chunks
)

print(result['answer'])
print(f"사용된 청크: {result['chunks_used']}개")
```

## 📊 비교: 기본 vs 멀티 스테이지

| 항목 | 기본 검색 | 멀티 스테이지 검색 |
|------|----------|------------------|
| 검색 단계 | 1단계 | 3단계 (계층적) |
| 검색 대상 | 모든 청크 | 법령 → 기준 → 사례 |
| 컨텍스트 활용 | ✗ | ✓ (Stage 1 → Stage 2) |
| Fallback | ✗ | ✓ (분쟁조정 부족 시) |
| 기관 추천 | ✗ | ✓ (하이브리드) |
| 결과 다양성 | 보통 | 높음 |
| 검색 시간 | 빠름 (~1초) | 보통 (~2-3초) |

## 🧪 테스트

### 멀티 스테이지 RAG 테스트

```bash
cd /home/maroco/ddoksori_demo/backend
conda activate ddoksori
python tests/rag/test_multi_stage_rag.py
```

**테스트 항목:**
- 전자제품 환불
- 온라인 거래 분쟁
- 서비스 환불
- 콘텐츠 분쟁

### 결과 분석

```bash
python scripts/analytics/analyze_rag_results.py
```

**분석 내용:**
- 검색 결과 분포
- 유사도 통계
- 기관 추천 정확도
- 성능 분석
- 개선 제안

## 📚 관련 문서

- [멀티 스테이지 RAG 사용 가이드](../../rag/docs/multi_stage_rag_usage.md)
- [임베딩 기준 및 프로세스](../../rag/docs/임베딩_기준_및_프로세스.md)

## 🔜 향후 계획

- [ ] FastAPI 엔드포인트 통합
- [ ] 프론트엔드 UI 개발
- [ ] 사용자 피드백 기반 개선
- [ ] 하이브리드 검색 (키워드 + 벡터)
- [ ] 캐싱 시스템 구현
