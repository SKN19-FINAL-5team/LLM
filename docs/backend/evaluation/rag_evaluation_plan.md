# 똑소리 프로젝트 - RAG 정량 평가 지표 설계

**작성일**: 2026-01-05  
**대상 브랜치**: feature/pr4-multi-agent-prep  
**목적**: RAG 시스템의 검색 성능을 객관적으로 측정하고 개선하기 위한 평가 프레임워크 구축

---

## 📋 목차

1. [평가 지표 개요](#평가-지표-개요)
2. [골드 데이터셋 구조](#골드-데이터셋-구조)
3. [정량 평가 지표](#정량-평가-지표)
4. [구현 계획](#구현-계획)
5. [예상 결과물](#예상-결과물)

---

## 🎯 평가 지표 개요

### 평가 목적

RAG 시스템의 검색 품질을 정량적으로 측정하여:
- **검색 정확도** 향상
- **검색 전략** 비교 및 최적화
- **하이퍼파라미터** 튜닝 근거 제공
- **시스템 개선** 효과 측정

### 평가 대상

1. **벡터 검색** (Vector Search)
2. **하이브리드 검색** (Hybrid Search)
3. **멀티 소스 검색** (Multi-Source Search)
4. **컨텍스트 확장** (Context Expansion)

---

## 📊 골드 데이터셋 구조

### 데이터셋 형식

골드 데이터셋은 **질문-정답 쌍**으로 구성되며, 각 항목은 다음 정보를 포함합니다:

```json
{
  "query_id": "Q001",
  "query": "온라인으로 구매한 제품이 불량이에요. 환불 받을 수 있나요?",
  "query_type": "general_inquiry",
  "expected_doc_types": ["counsel_case", "mediation_case", "law"],
  "relevant_chunk_ids": [
    "consumer.go.kr:consumer_counsel_case:12345::chunk0",
    "consumer.go.kr:consumer_mediation_case:67890::chunk1"
  ],
  "highly_relevant_chunk_ids": [
    "consumer.go.kr:consumer_counsel_case:12345::chunk0"
  ],
  "irrelevant_chunk_ids": [
    "statute:civil_law:article_100::chunk0"
  ],
  "metadata": {
    "difficulty": "easy",
    "category": "환불",
    "created_at": "2026-01-05",
    "annotator": "expert_1"
  }
}
```

### 필드 설명

| 필드 | 타입 | 설명 |
|------|------|------|
| `query_id` | string | 질문 고유 ID |
| `query` | string | 사용자 질문 |
| `query_type` | string | 질문 유형 (general_inquiry, legal_interpretation, similar_case) |
| `expected_doc_types` | array | 기대되는 문서 유형 목록 |
| `relevant_chunk_ids` | array | 관련 있는 청크 ID 목록 (정답) |
| `highly_relevant_chunk_ids` | array | 매우 관련 있는 청크 ID 목록 (최상위 정답) |
| `irrelevant_chunk_ids` | array | 관련 없는 청크 ID 목록 (오답 예시) |
| `metadata` | object | 추가 메타데이터 |

### 데이터셋 크기

- **초기 버전**: 30~50개 질문
- **확장 버전**: 100~200개 질문 (추후)

### 질문 유형별 분포

| 질문 유형 | 비율 | 설명 |
|----------|------|------|
| `general_inquiry` | 50% | 일반적인 소비자 문의 |
| `legal_interpretation` | 25% | 법률 해석 및 조항 질문 |
| `similar_case` | 25% | 유사 사례 검색 |

### 난이도별 분포

| 난이도 | 비율 | 설명 |
|--------|------|------|
| `easy` | 40% | 명확한 키워드, 단일 문서 유형 |
| `medium` | 40% | 복합 키워드, 다중 문서 유형 |
| `hard` | 20% | 모호한 표현, 추론 필요 |

---

## 📈 정량 평가 지표

### 1. 검색 정확도 지표

#### 1.1 Precision@K (정밀도)

상위 K개 결과 중 관련 있는 문서의 비율

```
Precision@K = (상위 K개 중 관련 문서 수) / K
```

**측정**: K = 1, 3, 5, 10

**해석**:
- 높을수록 검색 결과가 정확함
- 사용자가 상위 결과만 볼 때 중요

#### 1.2 Recall@K (재현율)

전체 관련 문서 중 상위 K개에 포함된 비율

```
Recall@K = (상위 K개 중 관련 문서 수) / (전체 관련 문서 수)
```

**측정**: K = 1, 3, 5, 10

**해석**:
- 높을수록 관련 문서를 많이 찾음
- 전체 관련 정보를 찾을 때 중요

#### 1.3 F1-Score@K

Precision과 Recall의 조화 평균

```
F1@K = 2 * (Precision@K * Recall@K) / (Precision@K + Recall@K)
```

**해석**:
- Precision과 Recall의 균형 지표
- 전체적인 검색 성능 평가

#### 1.4 Mean Average Precision (MAP)

모든 질문에 대한 Average Precision의 평균

```
AP = (1/|R|) * Σ(Precision@k * rel(k))
MAP = (1/|Q|) * Σ AP(q)
```

여기서:
- `R`: 관련 문서 집합
- `rel(k)`: k번째 위치의 문서가 관련 있으면 1, 아니면 0
- `Q`: 전체 질문 집합

**해석**:
- 검색 순위를 고려한 종합 지표
- 높을수록 관련 문서가 상위에 위치

#### 1.5 Mean Reciprocal Rank (MRR)

첫 번째 관련 문서의 순위 역수의 평균

```
RR = 1 / (첫 번째 관련 문서의 순위)
MRR = (1/|Q|) * Σ RR(q)
```

**해석**:
- 첫 번째 정답이 얼마나 빨리 나오는지 측정
- 사용자가 첫 결과만 볼 때 중요

#### 1.6 Normalized Discounted Cumulative Gain (NDCG@K)

순위와 관련도를 모두 고려한 지표

```
DCG@K = Σ(rel_i / log2(i+1))
IDCG@K = 이상적인 순서일 때의 DCG
NDCG@K = DCG@K / IDCG@K
```

여기서:
- `rel_i`: i번째 문서의 관련도 (0, 1, 2)
  - 0: 관련 없음
  - 1: 관련 있음
  - 2: 매우 관련 있음

**해석**:
- 관련도 등급을 고려한 순위 평가
- 0~1 사이 값, 1에 가까울수록 좋음

### 2. 검색 다양성 지표

#### 2.1 Document Type Coverage

검색 결과에 포함된 문서 유형의 다양성

```
Coverage = (검색된 문서 유형 수) / (기대 문서 유형 수)
```

**해석**:
- 1.0이면 모든 기대 문서 유형 포함
- 다양한 관점의 정보 제공 여부 측정

#### 2.2 Source Diversity

검색 결과의 출처 다양성 (Shannon Entropy)

```
Diversity = -Σ(p_i * log2(p_i))
```

여기서 `p_i`는 각 출처의 비율

**해석**:
- 높을수록 다양한 출처에서 정보 제공
- 편향 방지 지표

### 3. 검색 효율성 지표

#### 3.1 Average Query Time

평균 검색 시간 (초)

```
Avg_Time = Σ(query_time) / |Q|
```

**목표**: < 0.5초 (벡터 검색), < 1.0초 (하이브리드 검색)

#### 3.2 Throughput

초당 처리 가능한 쿼리 수

```
Throughput = |Q| / Total_Time
```

**목표**: > 10 queries/sec

### 4. 컨텍스트 확장 지표

#### 4.1 Context Relevance

확장된 컨텍스트의 관련성

```
Context_Relevance = (관련 있는 확장 청크 수) / (전체 확장 청크 수)
```

**해석**:
- 높을수록 유용한 컨텍스트 제공
- 노이즈 최소화 지표

#### 4.2 Context Completeness

필요한 정보가 컨텍스트에 모두 포함되었는지

```
Completeness = (포함된 필수 정보 수) / (전체 필수 정보 수)
```

**해석**:
- 1.0이면 완전한 정보 제공
- LLM 답변 생성에 충분한 정보 제공 여부

---

## 🛠 구현 계획

### Phase 1: RAG 평가 지표 설계 및 골드 데이터셋 구조 분석

**목표**: 평가 지표 확정 및 데이터셋 구조 설계

**산출물**:
- 평가 지표 설계 문서 (본 문서)
- 골드 데이터셋 스키마

### Phase 2: 평가 데이터셋 생성 및 관리 시스템 구현

**목표**: 골드 데이터셋 생성 도구 및 관리 시스템 구축

**구현 내용**:
1. **데이터셋 생성 도구**
   - 질문 템플릿 기반 자동 생성
   - 수동 큐레이션 인터페이스
   - 관련 청크 자동 추천 (현재 RAG 시스템 활용)

2. **데이터셋 관리**
   - JSON 파일 형식으로 저장
   - 버전 관리 (v1, v2, ...)
   - 검증 스크립트 (필수 필드 확인)

**산출물**:
- `backend/evaluation/dataset_generator.py`
- `backend/evaluation/datasets/gold_v1.json`
- `backend/evaluation/dataset_validator.py`

### Phase 3: 정량 평가 지표 계산 모듈 구현

**목표**: 각 평가 지표를 계산하는 모듈 구현

**구현 내용**:
1. **지표 계산 클래스**
   - `PrecisionRecallCalculator`
   - `RankingMetricsCalculator` (MAP, MRR, NDCG)
   - `DiversityCalculator`
   - `EfficiencyCalculator`

2. **평가 결과 데이터 구조**
   ```python
   {
     "query_id": "Q001",
     "metrics": {
       "precision@1": 1.0,
       "precision@3": 0.67,
       "recall@3": 0.5,
       "f1@3": 0.57,
       "map": 0.75,
       "mrr": 1.0,
       "ndcg@3": 0.85,
       "doc_type_coverage": 0.67,
       "query_time": 0.12
     },
     "retrieved_chunks": [...],
     "relevant_chunks": [...]
   }
   ```

**산출물**:
- `backend/evaluation/metrics.py`
- `backend/evaluation/evaluator.py`

### Phase 4: 평가 실행 및 리포팅 시스템 구현

**목표**: 평가 자동 실행 및 결과 리포트 생성

**구현 내용**:
1. **평가 실행 스크립트**
   - 골드 데이터셋 로드
   - 각 검색 방법별 평가 실행
   - 결과 저장 (JSON, CSV)

2. **리포트 생성**
   - 전체 평균 지표
   - 질문 유형별 지표
   - 난이도별 지표
   - 검색 방법 비교표
   - 시각화 (matplotlib)

3. **비교 분석**
   - 이전 버전과 비교
   - 검색 방법 간 비교
   - 개선 효과 측정

**산출물**:
- `backend/evaluation/run_evaluation.py`
- `backend/evaluation/report_generator.py`
- `backend/evaluation/results/` (결과 저장 디렉토리)

### Phase 5: 테스트 및 문서화

**목표**: 평가 시스템 검증 및 사용 가이드 작성

**구현 내용**:
1. **단위 테스트**
   - 각 지표 계산 함수 테스트
   - 엣지 케이스 처리 확인

2. **통합 테스트**
   - 전체 평가 파이프라인 테스트
   - 샘플 데이터셋으로 실행

3. **문서화**
   - 평가 시스템 사용 가이드
   - 골드 데이터셋 작성 가이드
   - 평가 지표 해석 가이드

**산출물**:
- `backend/tests/test_evaluation.py`
- `backend/evaluation/EVALUATION_GUIDE.md`

---

## 📦 예상 결과물

### 디렉토리 구조

```
backend/
├── evaluation/
│   ├── __init__.py
│   ├── metrics.py                  # 평가 지표 계산 모듈
│   ├── evaluator.py                # 평가 실행 클래스
│   ├── dataset_generator.py        # 데이터셋 생성 도구
│   ├── dataset_validator.py        # 데이터셋 검증 도구
│   ├── report_generator.py         # 리포트 생성 도구
│   ├── run_evaluation.py           # 평가 실행 스크립트
│   ├── EVALUATION_GUIDE.md         # 평가 시스템 가이드
│   ├── datasets/
│   │   ├── gold_v1.json            # 골드 데이터셋 v1
│   │   └── gold_v2.json            # 골드 데이터셋 v2 (추후)
│   └── results/
│       ├── evaluation_2026-01-05.json
│       ├── evaluation_2026-01-05.csv
│       └── comparison_report.md
└── tests/
    └── test_evaluation.py          # 평가 시스템 테스트
```

### 평가 리포트 예시

```markdown
# RAG 시스템 평가 리포트

**평가일**: 2026-01-05  
**데이터셋**: gold_v1 (50 queries)  
**검색 방법**: Vector, Hybrid, Multi-Source

## 전체 평균 지표

| 지표 | Vector | Hybrid | Multi-Source |
|------|--------|--------|--------------|
| Precision@3 | 0.65 | 0.72 | 0.78 |
| Recall@3 | 0.58 | 0.68 | 0.75 |
| F1@3 | 0.61 | 0.70 | 0.76 |
| MAP | 0.62 | 0.71 | 0.77 |
| MRR | 0.70 | 0.78 | 0.85 |
| NDCG@3 | 0.68 | 0.75 | 0.82 |
| Avg Time (s) | 0.08 | 0.15 | 0.22 |

## 질문 유형별 성능

### General Inquiry (25 queries)
- Best Method: Multi-Source
- Precision@3: 0.82
- Recall@3: 0.78

### Legal Interpretation (13 queries)
- Best Method: Hybrid
- Precision@3: 0.75
- Recall@3: 0.70

### Similar Case (12 queries)
- Best Method: Multi-Source
- Precision@3: 0.73
- Recall@3: 0.72

## 권장 사항

1. **Multi-Source 검색 사용 권장**: 전반적으로 가장 높은 성능
2. **Hybrid 검색 최적화**: 법률 해석 질문에 효과적
3. **검색 속도 개선**: Multi-Source 검색 시간 단축 필요
```

---

## 🎯 성공 기준

### 평가 시스템

- ✅ 6가지 이상의 정량 지표 구현
- ✅ 30개 이상의 골드 데이터셋 구축
- ✅ 자동 평가 및 리포트 생성
- ✅ 검색 방법 간 비교 분석

### 검색 성능 목표

- **Precision@3**: > 0.70
- **Recall@3**: > 0.65
- **MAP**: > 0.70
- **MRR**: > 0.75
- **NDCG@3**: > 0.75
- **Query Time**: < 0.5초 (벡터), < 1.0초 (하이브리드)

---

## 📚 참고 자료

- [Information Retrieval Evaluation Metrics](https://en.wikipedia.org/wiki/Evaluation_measures_(information_retrieval))
- [TREC Evaluation Guidelines](https://trec.nist.gov/)
- [RAG Evaluation Best Practices](https://www.llamaindex.ai/blog/evaluating-rag)

---

**작성자**: Manus AI (RAG 시스템 전문가)  
**최종 수정**: 2026-01-05
