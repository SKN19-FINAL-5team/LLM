# RAG 평가 시스템

똑소리 프로젝트의 RAG 시스템 정량 평가 프레임워크입니다.

## 🎯 개요

이 평가 시스템은 RAG 검색 성능을 객관적으로 측정하여 시스템 개선의 근거를 제공합니다.

### 주요 기능

- **12가지 평가 지표**: Precision@K, Recall@K, F1@K, MAP, MRR, NDCG@K, Document Type Coverage, Source Diversity 등
- **다양한 검색 방법 비교**: Vector Search, Hybrid Search, Multi-Source Search
- **질문 유형별 분석**: general_inquiry, legal_interpretation, similar_case
- **자동 리포트 생성**: JSON 형식의 상세 결과 및 요약 통계

## 📁 디렉토리 구조

```
evaluation/
├── __init__.py
├── README.md                   # 본 문서
├── EVALUATION_GUIDE.md         # 상세 사용 가이드
├── metrics.py                  # 평가 지표 계산 모듈
├── evaluator.py                # 평가 실행 클래스
├── dataset_generator.py        # 골드 데이터셋 생성 도구
├── dataset_validator.py        # 데이터셋 검증 도구
├── run_evaluation.py           # 평가 실행 스크립트
├── datasets/
│   └── gold_v1.json           # 골드 데이터셋 v1
└── results/                   # 평가 결과 저장 디렉토리
```

## 🚀 빠른 시작

### 1. 골드 데이터셋 생성

```bash
cd backend/evaluation
python dataset_generator.py
# 선택: 1 (초기 데이터셋 생성)
```

### 2. 데이터셋 검증

```bash
python dataset_validator.py datasets/gold_v1.json
```

### 3. 평가 실행

```bash
cd backend
python evaluation/run_evaluation.py \
  --dataset evaluation/datasets/gold_v1.json \
  --methods vector hybrid multi_source \
  --top-k 10
```

### 4. 결과 확인

평가 결과는 `evaluation/results/` 디렉토리에 저장됩니다:
- `evaluation_YYYYMMDD_HHMMSS.json`: 상세 결과
- `evaluation_summary_YYYYMMDD_HHMMSS.json`: 요약 통계

## 📊 평가 지표

### 검색 정확도 지표

| 지표 | 설명 | 목표 |
|------|------|------|
| Precision@K | 상위 K개 중 관련 문서 비율 | > 0.7 |
| Recall@K | 전체 관련 문서 중 검색된 비율 | > 0.65 |
| F1@K | Precision과 Recall의 조화 평균 | > 0.65 |
| MAP | 순위를 고려한 평균 정밀도 | > 0.7 |
| MRR | 첫 번째 관련 문서의 평균 순위 | > 0.75 |
| NDCG@K | 순위와 관련도를 고려한 지표 | > 0.75 |

### 검색 다양성 지표

| 지표 | 설명 | 목표 |
|------|------|------|
| Doc Type Coverage | 기대 문서 유형 포함 비율 | > 0.8 |
| Source Diversity | 출처 다양성 (Shannon Entropy) | > 1.0 |

### 검색 효율성 지표

| 지표 | 설명 | 목표 |
|------|------|------|
| Query Time | 평균 검색 시간 | < 0.5초 |

## 📖 상세 가이드

더 자세한 사용 방법은 [EVALUATION_GUIDE.md](./EVALUATION_GUIDE.md)를 참고하세요.

### 주요 내용

- 골드 데이터셋 생성 및 큐레이션
- 평가 실행 옵션 상세 설명
- 평가 지표 해석 가이드
- 트러블슈팅

## 🔧 요구사항

- Python 3.11+
- PostgreSQL (pgvector 확장)
- 임베딩 API 서버 실행 중
- RAG 데이터베이스에 데이터 임베딩 완료

## 📝 골드 데이터셋 구조

```json
{
  "query_id": "Q001",
  "query": "사용자 질문",
  "query_type": "general_inquiry | legal_interpretation | similar_case",
  "expected_doc_types": ["law", "counsel_case", "mediation_case"],
  "relevant_chunk_ids": ["chunk_id_1", "chunk_id_2"],
  "highly_relevant_chunk_ids": ["chunk_id_1"],
  "irrelevant_chunk_ids": [],
  "metadata": {
    "difficulty": "easy | medium | hard",
    "category": "카테고리",
    "created_at": "2026-01-05T14:30:00",
    "annotator": "작성자"
  }
}
```

## 🎓 평가 결과 예시

```
================================================================================
평가 결과 요약
================================================================================

[HYBRID]
--------------------------------------------------------------------------------
지표                             값
--------------------------------------------------
Precision@1                      0.8000
Precision@3                      0.7333
Precision@5                      0.6800
Recall@3                         0.6500
Recall@5                         0.7200
F1@3                             0.6889
Average Precision                0.7245
Reciprocal Rank                  0.8250
NDCG@3                           0.7856
Doc Type Coverage                0.8500
Source Diversity                 1.2340
Avg Query Time (s)               0.1523

질문 유형별 Precision@3:
  - general_inquiry         0.7800
  - legal_interpretation    0.7000
  - similar_case            0.7200
```

## 🤝 기여

골드 데이터셋 확장에 기여하려면:

1. 실제 사용자 질문 수집
2. RAG 시스템으로 검색 후 관련 청크 레이블링
3. `datasets/gold_v1.json`에 추가
4. `dataset_validator.py`로 검증

## 📚 참고 자료

- [평가 지표 설계 문서](../../rag_evaluation_plan.md)
- [RAG 시스템 가이드](../RAG_SETUP_GUIDE.md)
- [Information Retrieval Evaluation](https://en.wikipedia.org/wiki/Evaluation_measures_(information_retrieval))

---

**작성자**: Manus AI  
**작성일**: 2026-01-05  
**버전**: v1.0
