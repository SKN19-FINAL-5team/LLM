# 똑소리 프로젝트 - RAG 평가 시스템 사용 가이드

**작성일**: 2026-01-05  
**버전**: v1.0

---

## 📋 목차

1. [개요](#개요)
2. [평가 시스템 구조](#평가-시스템-구조)
3. [골드 데이터셋 생성](#골드-데이터셋-생성)
4. [평가 실행](#평가-실행)
5. [평가 지표 해석](#평가-지표-해석)
6. [트러블슈팅](#트러블슈팅)

---

## 🎯 개요

RAG 평가 시스템은 검색 성능을 정량적으로 측정하여 시스템 개선의 근거를 제공합니다.

### 주요 기능

- **12가지 평가 지표**: Precision, Recall, F1, MAP, MRR, NDCG 등
- **다양한 검색 방법 비교**: Vector, Hybrid, Multi-Source
- **질문 유형별 분석**: general_inquiry, legal_interpretation, similar_case
- **자동 리포트 생성**: JSON, 요약 통계

---

## 🏗 평가 시스템 구조

```
backend/evaluation/
├── __init__.py
├── metrics.py              # 평가 지표 계산 모듈
├── evaluator.py            # 평가 실행 클래스
├── dataset_generator.py    # 데이터셋 생성 도구
├── dataset_validator.py    # 데이터셋 검증 도구
├── run_evaluation.py       # 평가 실행 스크립트
├── EVALUATION_GUIDE.md     # 본 가이드
├── datasets/
│   └── gold_v1.json       # 골드 데이터셋
└── results/               # 평가 결과
    ├── evaluation_20260105_143000.json
    └── evaluation_summary_20260105_143000.json
```

---

## 📝 골드 데이터셋 생성

### 1. 자동 생성 (초기 데이터셋)

```bash
cd backend/evaluation
python dataset_generator.py
```

**선택**: 1 (초기 데이터셋 생성)

**결과**: `datasets/gold_v1.json` 생성 (샘플 10개 질문)

### 2. 데이터셋 구조

```json
{
  "query_id": "Q001",
  "query": "온라인으로 구매한 제품이 불량이에요. 환불 받을 수 있나요?",
  "query_type": "general_inquiry",
  "expected_doc_types": ["counsel_case", "law"],
  "relevant_chunk_ids": [
    "consumer.go.kr:consumer_counsel_case:53321::chunk0"
  ],
  "highly_relevant_chunk_ids": [
    "consumer.go.kr:consumer_counsel_case:53321::chunk0"
  ],
  "irrelevant_chunk_ids": [],
  "metadata": {
    "difficulty": "easy",
    "category": "환불",
    "created_at": "2026-01-05T14:30:00",
    "annotator": "expert_1"
  }
}
```

### 3. 수동 큐레이션

실제 사용자 질문을 기반으로 골드 데이터셋을 확장하려면:

1. **질문 수집**: 실제 사용자 로그에서 대표적인 질문 선정
2. **정답 레이블링**: RAG 시스템으로 검색 후 관련 청크 수동 선택
3. **데이터셋 추가**: JSON 파일에 직접 추가 또는 `dataset_generator.py` 수정

### 4. 데이터셋 검증

```bash
cd backend/evaluation
python dataset_validator.py datasets/gold_v1.json
```

**검증 항목**:
- 필수 필드 존재 여부
- 필드 타입 확인
- query_id 중복 검사
- 관련도 일관성 (highly_relevant ⊆ relevant)

---

## 🚀 평가 실행

### 기본 사용법

```bash
cd backend
python evaluation/run_evaluation.py \
  --dataset evaluation/datasets/gold_v1.json \
  --methods vector hybrid multi_source \
  --top-k 10 \
  --output-dir evaluation/results
```

### 옵션 설명

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--dataset` | 골드 데이터셋 경로 | (필수) |
| `--methods` | 평가할 검색 방법 | vector hybrid multi_source |
| `--top-k` | 검색할 청크 수 | 10 |
| `--output-dir` | 결과 저장 디렉토리 | evaluation/results |
| `--db-host` | 데이터베이스 호스트 | 환경변수 DB_HOST |
| `--db-port` | 데이터베이스 포트 | 환경변수 DB_PORT |
| `--embed-api-url` | 임베딩 API URL | 환경변수 EMBED_API_URL |

### 예시: 특정 검색 방법만 평가

```bash
python evaluation/run_evaluation.py \
  --dataset evaluation/datasets/gold_v1.json \
  --methods hybrid \
  --top-k 5
```

### 평가 실행 과정

```
============================================================
똑소리 프로젝트 - RAG 시스템 정량 평가
============================================================
데이터셋: evaluation/datasets/gold_v1.json
검색 방법: vector, hybrid, multi_source
Top-K: 10
============================================================

[1/3] RAG Retriever 초기화 중...
✅ RAG Retriever 초기화 완료

[2/3] Evaluator 초기화 중...
✅ 데이터셋 로드 완료: 10개 질문
✅ Evaluator 초기화 완료

[3/3] 평가 실행 중...

[VECTOR] 평가 중...
  진행: 10/10 (100.0%)
✅ [VECTOR] 평가 완료

[HYBRID] 평가 중...
  진행: 10/10 (100.0%)
✅ [HYBRID] 평가 완료

[MULTI_SOURCE] 평가 중...
  진행: 10/10 (100.0%)
✅ [MULTI_SOURCE] 평가 완료

✅ 평가 결과 저장: evaluation/results/evaluation_20260105_143000.json
✅ 요약 통계 저장: evaluation/results/evaluation_summary_20260105_143000.json
```

### 결과 파일

#### 1. 상세 결과 (`evaluation_YYYYMMDD_HHMMSS.json`)

각 질문에 대한 상세 평가 결과:
- 검색된 청크 목록
- 개별 지표 값
- 관련 청크 매칭 정보

#### 2. 요약 통계 (`evaluation_summary_YYYYMMDD_HHMMSS.json`)

집계된 평가 지표:
- 전체 평균 지표
- 질문 유형별 지표
- 검색 방법 간 비교

---

## 📊 평가 지표 해석

### 1. Precision@K (정밀도)

**의미**: 상위 K개 결과 중 관련 있는 문서의 비율

**해석**:
- **0.8 이상**: 매우 우수
- **0.6 ~ 0.8**: 우수
- **0.4 ~ 0.6**: 보통
- **0.4 미만**: 개선 필요

**개선 방법**:
- 벡터 검색 가중치 조정
- 키워드 필터링 강화
- 임베딩 모델 개선

### 2. Recall@K (재현율)

**의미**: 전체 관련 문서 중 상위 K개에 포함된 비율

**해석**:
- **0.7 이상**: 매우 우수
- **0.5 ~ 0.7**: 우수
- **0.3 ~ 0.5**: 보통
- **0.3 미만**: 개선 필요

**개선 방법**:
- K 값 증가
- 검색 범위 확대
- 쿼리 확장 기법 적용

### 3. F1-Score@K

**의미**: Precision과 Recall의 조화 평균

**해석**:
- **0.7 이상**: 매우 우수
- **0.5 ~ 0.7**: 우수
- **0.3 ~ 0.5**: 보통
- **0.3 미만**: 개선 필요

**개선 방법**:
- Precision과 Recall 균형 조정
- 하이브리드 검색 가중치 최적화

### 4. MAP (Mean Average Precision)

**의미**: 검색 순위를 고려한 종합 정확도

**해석**:
- **0.7 이상**: 매우 우수
- **0.5 ~ 0.7**: 우수
- **0.3 ~ 0.5**: 보통
- **0.3 미만**: 개선 필요

**개선 방법**:
- 순위 학습(Learning to Rank) 적용
- 재순위화(Reranking) 모델 추가

### 5. MRR (Mean Reciprocal Rank)

**의미**: 첫 번째 관련 문서의 평균 순위

**해석**:
- **0.8 이상**: 매우 우수 (대부분 1~2위에 정답)
- **0.6 ~ 0.8**: 우수 (대부분 3~4위에 정답)
- **0.4 ~ 0.6**: 보통 (대부분 5~10위에 정답)
- **0.4 미만**: 개선 필요

**개선 방법**:
- 첫 번째 결과 최적화
- 쿼리 이해 개선

### 6. NDCG@K (Normalized Discounted Cumulative Gain)

**의미**: 순위와 관련도를 모두 고려한 지표

**해석**:
- **0.8 이상**: 매우 우수
- **0.6 ~ 0.8**: 우수
- **0.4 ~ 0.6**: 보통
- **0.4 미만**: 개선 필요

**개선 방법**:
- 관련도 점수 정교화
- 순위 최적화

### 7. Document Type Coverage

**의미**: 기대 문서 유형 포함 비율

**해석**:
- **1.0**: 완벽 (모든 유형 포함)
- **0.7 ~ 1.0**: 우수
- **0.5 ~ 0.7**: 보통
- **0.5 미만**: 개선 필요

**개선 방법**:
- 멀티 소스 검색 가중치 조정
- 문서 유형별 최소 결과 수 보장

### 8. Source Diversity

**의미**: 검색 결과의 출처 다양성 (Shannon Entropy)

**해석**:
- **1.5 이상**: 매우 다양
- **1.0 ~ 1.5**: 다양
- **0.5 ~ 1.0**: 보통
- **0.5 미만**: 편향됨

**개선 방법**:
- 출처별 최대 결과 수 제한
- 다양성 보상 추가

### 9. Query Time

**의미**: 평균 검색 시간 (초)

**목표**:
- **Vector 검색**: < 0.1초
- **Hybrid 검색**: < 0.3초
- **Multi-Source 검색**: < 0.5초

**개선 방법**:
- 인덱스 최적화
- 배치 처리
- 캐싱 적용

---

## 🔧 트러블슈팅

### 문제 1: `ModuleNotFoundError: No module named 'rag'`

**원인**: Python 경로 문제

**해결**:
```bash
cd backend
export PYTHONPATH=$PYTHONPATH:$(pwd)
python evaluation/run_evaluation.py ...
```

### 문제 2: 데이터셋 검증 실패

**원인**: 골드 데이터셋 형식 오류

**해결**:
```bash
python evaluation/dataset_validator.py datasets/gold_v1.json
```

오류 메시지를 확인하고 JSON 파일 수정

### 문제 3: 평가 시간이 너무 오래 걸림

**원인**: 데이터셋 크기가 크거나 검색이 느림

**해결**:
- 데이터셋을 작은 샘플로 먼저 테스트
- `--top-k` 값을 줄임
- 데이터베이스 인덱스 확인

### 문제 4: `relevant_chunk_ids`가 비어있음

**원인**: 골드 데이터셋 작성 중 정답 레이블링 누락

**해결**:
- RAG 시스템으로 검색 후 관련 청크 ID 수동 추가
- 또는 `dataset_generator.py`의 `suggest_relevant_chunks()` 함수 활용

---

## 📚 참고 자료

- [평가 지표 설계 문서](../../rag_evaluation_plan.md)
- [RAG 시스템 가이드](../RAG_SETUP_GUIDE.md)
- [Information Retrieval Evaluation](https://en.wikipedia.org/wiki/Evaluation_measures_(information_retrieval))

---

**작성자**: Manus AI (RAG 시스템 전문가)  
**최종 수정**: 2026-01-05
