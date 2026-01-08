# 테스트 가이드

**작성일**: 2026-01-07  
**버전**: v1.0

---

## 개요

본 디렉토리는 똑소리 프로젝트의 모든 테스트 코드를 포함합니다.

---

## 디렉토리 구조

```
test/
├── README.md                       # 본 문서
├── unit/                           # 단위 테스트
│   ├── test_vector_db_schema.py    # Vector DB 스키마 테스트
│   ├── test_chunking_quality.py    # 청킹 품질 테스트
│   └── test_api.py                 # FastAPI 엔드포인트 테스트
├── integration/                    # 통합 테스트
│   ├── test_rag.py                 # RAG 시스템 통합 테스트
│   └── test_rag_v2.py              # RAG V2 통합 테스트
└── rag/                            # RAG 시스템 테스트
    ├── test_agency_recommender.py  # 기관 추천 테스트
    ├── test_agency_with_real_data.py  # 실제 데이터 기관 추천 테스트
    ├── test_multi_stage_rag.py     # 멀티 스테이지 RAG 테스트
    ├── test_rag_simple.py          # 간단한 RAG 테스트
    ├── test_search_quality.py     # 검색 품질 테스트
    └── test_similarity_search.py  # 유사도 검색 테스트
```

---

## 테스트 실행

### 단위 테스트

#### Vector DB 스키마 테스트

```bash
cd /home/maroco/ddoksori_demo
conda activate ddoksori
python test/unit/test_vector_db_schema.py
```

**테스트 항목**:
- 벡터 검색 성능 (< 500ms)
- 메타데이터 필터링 정확도 (100%)
- 청크 관계 조회 (< 100ms)
- JSONB 쿼리 성능 (< 200ms)
- 동시성 테스트 (성능 저하 < 20%)

#### 청킹 품질 테스트

```bash
cd /home/maroco/ddoksori_demo
conda activate ddoksori
python test/unit/test_chunking_quality.py
```

**테스트 항목**:
- 청크 크기 분포 분석
- 문장 경계 보존 (70% 이상)
- 오버랩 품질 평가
- 메타데이터 추출 정확도
- 빈/짧은 청크 감지

#### API 테스트

```bash
cd /home/maroco/ddoksori_demo
conda activate ddoksori
python test/unit/test_api.py
```

**테스트 항목**:
- 헬스 체크
- 검색 API
- 채팅 API

### 통합 테스트

#### RAG 시스템 통합 테스트

```bash
cd /home/maroco/ddoksori_demo
conda activate ddoksori
python test/integration/test_rag.py
python test/integration/test_rag_v2.py
```

**테스트 항목**:
- Vector DB 검색 기능
- LLM 답변 생성
- 멀티 스테이지 검색

### RAG 시스템 테스트

#### 멀티 스테이지 RAG 테스트

```bash
cd /home/maroco/ddoksori_demo
conda activate ddoksori
python test/rag/test_multi_stage_rag.py
```

**테스트 항목**:
- 전자제품 환불 시나리오
- 온라인 거래 분쟁 시나리오
- 서비스 환불 시나리오
- 콘텐츠 분쟁 시나리오

#### 기관 추천 테스트

```bash
python test/rag/test_agency_recommender.py
python test/rag/test_agency_with_real_data.py
```

---

## 테스트 결과

테스트 실행 후 결과는 `/tmp/` 디렉토리에 JSON 형식으로 저장됩니다:

- `/tmp/vector_db_test_results.json`
- `/tmp/chunking_quality_test_results.json`

---

## 환경 요구사항

- Python 3.11+
- Conda 환경: `ddoksori`
- PostgreSQL 16 실행 중
- 데이터 임베딩 완료

---

## 문제 해결

### PostgreSQL 연결 실패

```bash
# DB 상태 확인
docker ps | grep ddoksori_db

# DB 재시작
docker-compose restart db
```

### Conda 환경 활성화 실패

```bash
# 환경 확인
conda env list

# 환경 활성화
conda activate ddoksori
```

---

## 참고 문서

- [`docs/technical/vector_db_스키마_평가_보고서.md`](../docs/technical/vector_db_스키마_평가_보고서.md)
- [`docs/technical/청킹_로직_평가_보고서.md`](../docs/technical/청킹_로직_평가_보고서.md)
