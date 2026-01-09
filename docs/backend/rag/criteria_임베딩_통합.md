# Criteria 데이터 임베딩 통합 가이드

## 목차
1. [개요](#개요)
2. [점진적 통합이란?](#점진적-통합이란)
3. [사전 준비](#사전-준비)
4. [단계별 실행 가이드](#단계별-실행-가이드)
5. [검증 방법](#검증-방법)
6. [문제 해결](#문제-해결)
7. [FAQ](#faq)

---

## 개요

### 목적
Criteria 데이터(가이드라인 및 기준 정보)를 RAG 시스템에 안전하고 효율적으로 통합합니다.

### Criteria 데이터 구성

| 파일명 | 레코드 수 | 데이터 특성 |
|-------|---------|-----------|
| content_guideline_chunks.jsonl | 8 | 문화체육관광부 가이드라인 |
| ecommerce_guideline_chunks.jsonl | 18 | 전자상거래 지침 |
| table4_lifespan_chunks.jsonl | 63 | 품목별 내용연수 |
| table1_item_chunks.jsonl | 592 | 대상품목 592개 |
| table3_warranty_chunks.jsonl | 84 | 보증기간/부품보유기간 |
| **합계** | **765개** | **총 5개 파일** |

### 통합 후 기대 효과

- ✅ 법령-지침-사례의 완전한 검색 계층 구축
- ✅ "냉장고", "계란" 등 592개 품목으로 정확한 매칭
- ✅ 보증기간, 내용연수 등 실무 기준 제공
- ✅ RAG 검색 품질 대폭 향상

---

## 점진적 통합이란?

### 개념

**점진적 통합**: 대량 데이터를 한 번에 처리하지 않고, 작은 단위로 나눠서 단계별로 검증하며 통합하는 방식

### 왜 점진적으로?

#### 장점
1. **안정성**: 소규모 데이터로 먼저 테스트 → 문제 조기 발견
2. **롤백 용이**: 문제 발생 시 이전 단계로 쉽게 복구
3. **검증 가능**: 각 단계마다 데이터 품질 확인
4. **학습 곡선**: 작은 데이터로 시스템 동작 이해

#### 단점
1. ~~여러 번 실행 필요~~ → **아니요!** (중복 임베딩 자동 스킵)
2. 약간의 시간 추가 (검증 시간)

### 중요: 중복 임베딩 방지

**코드에 내장된 자동 스킵 기능**:
```sql
INSERT INTO chunks (...)
VALUES %s
ON CONFLICT (chunk_id) DO NOTHING  -- ← 이미 있으면 자동 스킵
```

**의미**:
- 1단계에서 Guideline 26개 임베딩
- 2단계에서 Guideline + Table4 처리 시
  - Guideline 26개: **이미 DB에 있음 → 임베딩 스킵**
  - Table4 63개: 새로운 데이터 → 임베딩

**결론**: 각 청크는 **딱 한 번만 임베딩**됩니다!

---

## 사전 준비

### 1. 환경 확인

```bash
# 현재 위치 확인
cd /home/maroco/ddoksori_demo

# 필요한 파일 확인
ls backend/data/criteria/
# 출력: content_guideline_chunks.jsonl  ecommerce_guideline_chunks.jsonl
#       table1_item_chunks.jsonl  table3_warranty_chunks.jsonl
#       table4_lifespan_chunks.jsonl
```

### 2. 데이터베이스 연결 확인

```bash
# .env 파일 확인
cat backend/.env | grep DB_

# 예상 출력:
# DB_HOST=localhost
# DB_PORT=5432
# DB_NAME=ddoksori
# DB_USER=postgres
# DB_PASSWORD=...
```

### 3. 임베딩 API 서버 실행 확인

```bash
# API 서버 상태 확인
curl http://localhost:8001/

# 예상 응답:
# {"status":"healthy","model":"nlpai-lab/KURE-v1","dimension":1024}
```

### 4. (선택) 기존 데이터 백업

```bash
# PostgreSQL 백업
pg_dump -U postgres -d ddoksori -t chunks -t documents \
  > backup_before_criteria_$(date +%Y%m%d_%H%M%S).sql

# 백업 확인
ls -lh backup_before_criteria_*.sql
```

---

## 단계별 실행 가이드

### 전체 프로세스 개요

```
준비 → 1단계 테스트 → 검증 → 전체 실행 → 최종 검증
```

---

### 옵션 A: 추천 방식 (테스트 후 전체)

#### Step 1: 소규모 테스트 (Guideline 26개)

```bash
# 1-1. 환경 변수 설정
export CRITERIA_STAGE=1

# 1-2. 파이프라인 실행
python backend/scripts/embed_pipeline_v2.py
```

**예상 출력**:
```
[4/6] 가이드라인 데이터 처리 중... (stage=1)
   처리 대상 파일: 2개
   처리 중: content_guideline_chunks.jsonl
   처리 중: ecommerce_guideline_chunks.jsonl
✅ 가이드라인 데이터 처리 완료: 문서 2개, 청크 26개

[6/6] 청크 임베딩 및 삽입 중: 26개
100%|████████████████████████| 1/1 [00:02<00:00,  2.34s/it]
✅ 청크 임베딩 및 삽입 완료
```

#### Step 2: 검증

```bash
# 2-1. 임베딩 상태 확인
python backend/scripts/check_embedding_status.py
```

**예상 출력**:
```
=== 임베딩 상태 확인 ===
총 청크 수: 26
임베딩 완료: 26 (100.0%)
임베딩 미완료: 0

=== chunk_type 분포 ===
guideline_section: 26
```

**SQL로 직접 확인**:
```sql
-- psql로 접속
psql -U postgres -d ddoksori

-- guideline 청크 확인
SELECT
    doc_type,
    chunk_type,
    COUNT(*) as count,
    AVG(content_length) as avg_length
FROM chunks
WHERE doc_type = 'guideline'
GROUP BY doc_type, chunk_type;

-- 예상 결과:
--  doc_type  |    chunk_type     | count | avg_length
-- -----------+-------------------+-------+------------
--  guideline | guideline_section |    26 |     1150.5
```

**검색 테스트**:
```bash
# 유사도 검색 테스트
python backend/scripts/test_similarity_search.py
```

```python
# test_similarity_search.py에 추가할 테스트 쿼리
query = "전자상거래 환불 기준"
# → guideline_section 타입의 청크가 검색되어야 함
```

#### Step 3: 전체 실행 (나머지 739개)

**1단계 검증 성공 시**:

```bash
# 3-1. 전체 모드로 설정
export CRITERIA_STAGE=0  # 또는 unset CRITERIA_STAGE

# 3-2. 파이프라인 실행
python backend/scripts/embed_pipeline_v2.py
```

**예상 출력**:
```
[4/6] 가이드라인 데이터 처리 중... (stage=0)
   처리 대상 파일: 5개
   처리 중: content_guideline_chunks.jsonl
   처리 중: ecommerce_guideline_chunks.jsonl
   처리 중: table4_lifespan_chunks.jsonl
   처리 중: table1_item_chunks.jsonl
   처리 중: table3_warranty_chunks.jsonl
✅ 가이드라인 데이터 처리 완료: 문서 8개, 청크 765개

[6/6] 청크 임베딩 및 삽입 중: 765개
100%|████████████████████████| 24/24 [01:23<00:00,  3.48s/it]
✅ 청크 임베딩 및 삽입 완료
```

**중요**: 이미 임베딩된 26개는 자동으로 스킵되므로, **실제로는 739개만 새로 임베딩**됩니다!

#### Step 4: 최종 검증

```bash
# 4-1. 임베딩 상태 확인
python backend/scripts/check_embedding_status.py
```

**예상 출력**:
```
=== 임베딩 상태 확인 ===
총 청크 수: 765
임베딩 완료: 765 (100.0%)
임베딩 미완료: 0

=== chunk_type 분포 ===
guideline_section: 26
lifespan_item: 63
item_basic: 592
warranty_parent: 20
warranty_detail: 64
```

**SQL 검증**:
```sql
-- chunk_type별 분포 확인
SELECT
    chunk_type,
    COUNT(*) as count,
    MIN(content_length) as min_len,
    AVG(content_length) as avg_len,
    MAX(content_length) as max_len
FROM chunks
WHERE doc_type = 'guideline'
GROUP BY chunk_type
ORDER BY count DESC;

-- 예상 결과:
--     chunk_type     | count | min_len | avg_len | max_len
-- -------------------+-------+---------+---------+---------
--  item_basic        |   592 |      45 |    65.3 |     120
--  warranty_detail   |    64 |     180 |   352.1 |     580
--  lifespan_item     |    63 |      85 |   118.7 |     165
--  guideline_section |    26 |     820 |  1150.5 |    1480
--  warranty_parent   |    20 |      60 |    78.4 |     110
```

**검색 품질 테스트**:
```python
# test_similarity_search.py

test_queries = [
    {
        "query": "냉장고 보증기간",
        "expected_types": ["item_basic", "warranty_parent", "warranty_detail"]
    },
    {
        "query": "전자상거래 환불 절차",
        "expected_types": ["guideline_section"]
    },
    {
        "query": "계란 품질 기준",
        "expected_types": ["item_basic"]
    }
]

for test in test_queries:
    results = retrieve_similar_chunks(test["query"], top_k=5)
    print(f"\n쿼리: {test['query']}")
    for r in results:
        print(f"  - [{r['chunk_type']}] {r['content'][:50]}... (유사도: {r['similarity']:.3f})")
```

---

### 옵션 B: 한 번에 전체 실행 (간단)

**테스트 없이 바로 전체 처리**:

```bash
# 전체 모드
export CRITERIA_STAGE=0

# 실행
python backend/scripts/embed_pipeline_v2.py

# 검증
python backend/scripts/check_embedding_status.py
```

**장점**: 빠르고 간단
**단점**: 문제 발생 시 디버깅 어려움

---

### 옵션 C: 완전 점진적 통합 (학습/디버깅용)

**모든 단계를 거치며 검증**:

```bash
# 1단계: Guideline만 (26개)
export CRITERIA_STAGE=1
python backend/scripts/embed_pipeline_v2.py
python backend/scripts/check_embedding_status.py

# 2단계: + Table4 (26 + 63 = 89개)
export CRITERIA_STAGE=2
python backend/scripts/embed_pipeline_v2.py
python backend/scripts/check_embedding_status.py

# 3단계: + Table1 (89 + 592 = 681개)
export CRITERIA_STAGE=3
python backend/scripts/embed_pipeline_v2.py
python backend/scripts/check_embedding_status.py

# 4단계: + Table3 (681 + 84 = 765개)
export CRITERIA_STAGE=4
python backend/scripts/embed_pipeline_v2.py
python backend/scripts/check_embedding_status.py
```

**장점**: 각 데이터 타입의 특성을 상세히 확인 가능
**단점**: 시간이 오래 걸림 (검증 시간)

---

## 검증 방법

### 1. 자동 스크립트 검증

#### check_embedding_status.py

```bash
python backend/scripts/check_embedding_status.py
```

**확인 항목**:
- ✅ 총 청크 수
- ✅ 임베딩 완료율 (100% 목표)
- ✅ chunk_type 분포
- ✅ 임베딩 벡터 차원 (1024)

#### test_similarity_search.py

```bash
python backend/scripts/test_similarity_search.py
```

**확인 항목**:
- ✅ 검색 결과 반환 여부
- ✅ 유사도 점수 (0.0~1.0)
- ✅ 적절한 chunk_type 반환

### 2. SQL 직접 검증

```sql
-- 1. 전체 통계
SELECT
    doc_type,
    COUNT(*) as total_chunks,
    COUNT(embedding) as embedded_chunks,
    ROUND(COUNT(embedding)::NUMERIC / COUNT(*) * 100, 2) as completion_rate
FROM chunks
GROUP BY doc_type;

-- 예상 결과:
--   doc_type    | total_chunks | embedded_chunks | completion_rate
-- --------------+--------------+-----------------+-----------------
--  law          |          300 |             300 |          100.00
--  counsel_case |          400 |             400 |          100.00
--  mediation_case |        500 |             500 |          100.00
--  guideline    |          765 |             765 |          100.00


-- 2. guideline chunk_type 분포
SELECT
    chunk_type,
    COUNT(*) as count,
    ROUND(AVG(content_length), 1) as avg_length
FROM chunks
WHERE doc_type = 'guideline'
GROUP BY chunk_type
ORDER BY count DESC;

-- 예상 결과:
--     chunk_type     | count | avg_length
-- -------------------+-------+------------
--  item_basic        |   592 |       65.3
--  warranty_detail   |    64 |      352.1
--  lifespan_item     |    63 |      118.7
--  guideline_section |    26 |     1150.5
--  warranty_parent   |    20 |       78.4


-- 3. source_org 분포
SELECT
    source_org,
    COUNT(*) as doc_count
FROM documents
WHERE doc_type = 'guideline'
GROUP BY source_org;

-- 예상 결과:
--  source_org | doc_count
-- ------------+-----------
--  MCST       |         1
--  FTC        |         7


-- 4. parent-child 관계 확인 (table3)
SELECT
    c1.chunk_id as parent_chunk,
    c1.content as parent_content,
    c2.chunk_id as child_chunk,
    c2.content as child_content
FROM chunks c1
JOIN chunks c2
  ON c2.metadata->>'parent_stable_id' = c1.metadata->>'stable_id'
WHERE c1.chunk_type = 'warranty_parent'
LIMIT 3;


-- 5. aliases 메타데이터 확인
SELECT
    content,
    metadata->>'item_name' as item,
    metadata->>'aliases' as aliases
FROM chunks
WHERE chunk_type = 'item_basic'
  AND metadata->>'aliases' IS NOT NULL
LIMIT 5;

-- 예상 결과:
--           content           |      item       |            aliases
-- ----------------------------+-----------------+-------------------------------
--  [품목] 재봉기...           | 재봉기          | ["가정용 재봉기","재봉기"]
--  [품목] 냉장고...           | 냉장고          | ["냉장고","냉동냉장고"]
```

### 3. 검색 품질 테스트

```python
# backend/scripts/test_criteria_search.py (새 파일 생성)

from app.rag.retriever import retrieve_similar_chunks

test_cases = [
    {
        "name": "품목 검색",
        "query": "냉장고 보증기간",
        "expected_types": ["item_basic", "warranty_parent", "warranty_detail"],
        "min_similarity": 0.7
    },
    {
        "name": "가이드라인 검색",
        "query": "전자상거래 환불 절차",
        "expected_types": ["guideline_section"],
        "min_similarity": 0.65
    },
    {
        "name": "내용연수 검색",
        "query": "가전제품 내용연수",
        "expected_types": ["lifespan_item"],
        "min_similarity": 0.7
    }
]

for test in test_cases:
    print(f"\n{'='*60}")
    print(f"테스트: {test['name']}")
    print(f"쿼리: {test['query']}")
    print(f"{'='*60}")

    results = retrieve_similar_chunks(test["query"], top_k=5)

    for i, r in enumerate(results, 1):
        print(f"{i}. [{r['chunk_type']}] (유사도: {r['similarity']:.3f})")
        print(f"   {r['content'][:100]}...")

    # 검증
    types_found = [r['chunk_type'] for r in results]
    assert any(t in test['expected_types'] for t in types_found), \
        f"예상 타입 {test['expected_types']} 중 하나가 검색되어야 함"

    assert all(r['similarity'] >= test['min_similarity'] for r in results), \
        f"모든 결과의 유사도가 {test['min_similarity']} 이상이어야 함"

    print(f"✅ 테스트 통과")

print(f"\n{'='*60}")
print("✅ 모든 테스트 통과!")
print(f"{'='*60}")
```

실행:
```bash
python backend/scripts/test_criteria_search.py
```

---

## 문제 해결

### 1. 임베딩 API 연결 실패

**증상**:
```
⚠️  API 연결 실패: Connection refused
   로컬 모드로 계속 진행합니다 (임베딩은 나중에 수행)
```

**원인**: 임베딩 API 서버 미실행

**해결**:
```bash
# API 서버 실행
python backend/runpod_embed_server.py

# 또는 Docker로 실행
docker-compose up -d embed-server
```

### 2. 파일을 찾을 수 없음

**증상**:
```
⚠️  criteria 디렉토리가 존재하지 않습니다: /path/to/criteria
```

**원인**: 데이터 파일 경로 문제

**해결**:
```bash
# 현재 위치 확인
pwd

# criteria 디렉토리 확인
ls backend/data/criteria/

# 프로젝트 루트로 이동
cd /home/maroco/ddoksori_demo
```

### 3. 중복 청크 오류

**증상**:
```
ERROR: duplicate key value violates unique constraint "chunks_pkey"
DETAIL: Key (chunk_id)=(guideline:...) already exists.
```

**원인**: 이미 임베딩된 데이터 재처리 시도

**해결**:
- **정상**: `ON CONFLICT ... DO NOTHING`이 작동하지 않는 경우 (코드 버그)
- **조치**: 코드 확인 또는 기존 데이터 삭제 후 재실행

```sql
-- 기존 criteria 데이터 삭제
DELETE FROM chunks WHERE doc_type = 'guideline';
DELETE FROM documents WHERE doc_type = 'guideline';
```

### 4. 임베딩 완료율 100% 미만

**증상**:
```
임베딩 완료: 750 / 765 (98.0%)
임베딩 미완료: 15
```

**원인**:
- API 타임아웃
- 네트워크 오류
- 일부 청크의 content가 빈 문자열

**해결**:
```bash
# 다시 실행 (미완료 청크만 처리됨)
python backend/scripts/embed_pipeline_v2.py

# 또는 미완료 청크 확인
psql -U postgres -d ddoksori -c \
  "SELECT chunk_id, content_length FROM chunks
   WHERE doc_type='guideline' AND embedding IS NULL;"
```

### 5. 검색 결과 없음

**증상**: 쿼리 실행 시 결과 0개 반환

**원인**:
- 임베딩 미완료
- 쿼리 임베딩 실패
- 유사도 임계값 너무 높음

**해결**:
```python
# 1. 임베딩 완료 확인
SELECT COUNT(*) FROM chunks
WHERE doc_type='guideline' AND embedding IS NOT NULL;

# 2. 직접 벡터 검색 테스트
SELECT chunk_id, content,
       1 - (embedding <=> %s::vector) as similarity
FROM chunks
WHERE doc_type='guideline'
ORDER BY embedding <=> %s::vector
LIMIT 5;
```

### 6. 롤백 필요

**전체 삭제 후 재시작**:

```sql
-- 1. criteria 청크 삭제
DELETE FROM chunks WHERE doc_type = 'guideline';

-- 2. criteria 문서 삭제
DELETE FROM documents WHERE doc_type = 'guideline';

-- 3. 확인
SELECT doc_type, COUNT(*) FROM chunks GROUP BY doc_type;
-- guideline이 사라졌는지 확인
```

**백업에서 복원**:
```bash
# 백업 파일 확인
ls -lh backup_before_criteria_*.sql

# 복원
psql -U postgres -d ddoksori < backup_before_criteria_20260105_120000.sql
```

---

## FAQ

### Q1. 매 단계마다 임베딩을 새로 해야 하나요?

**A**: 아니요!

- `ON CONFLICT (chunk_id) DO NOTHING` 덕분에 이미 임베딩된 청크는 자동으로 스킵됩니다.
- 예: 1단계(26개) → 2단계(+63개) 실행 시, 26개는 스킵되고 63개만 새로 임베딩됩니다.

### Q2. CRITERIA_STAGE=0과 4의 차이는?

**A**: 동일합니다!

- `CRITERIA_STAGE=0`: 전체 파일 (stage 1+2+3+4)
- `CRITERIA_STAGE=4`: 전체 파일 (stage 1+2+3+4)

둘 다 5개 파일 전체를 처리합니다.

### Q3. 가장 빠른 방법은?

**A**: `CRITERIA_STAGE=0`으로 한 번에 실행

```bash
export CRITERIA_STAGE=0
python backend/scripts/embed_pipeline_v2.py
```

단, 문제 발생 시 디버깅이 어려울 수 있습니다.

### Q4. 가장 안전한 방법은?

**A**: 2단계 방식 (추천)

1. `CRITERIA_STAGE=1` (소규모 테스트)
2. 검증 후 `CRITERIA_STAGE=0` (전체)

### Q5. 특정 파일만 처리하고 싶어요

**A**: 현재 구현에서는 불가능합니다. 대신:

- `CRITERIA_STAGE=1`: Guideline 파일만
- `CRITERIA_STAGE=2`: Guideline + Table4
- `CRITERIA_STAGE=3`: Guideline + Table4 + Table1
- `CRITERIA_STAGE=4` or `0`: 전체

### Q6. 처리 시간은 얼마나 걸리나요?

**A**: 대략적인 예상 시간 (GPU 사용 시)

- 1단계 (26개): ~1분
- 2단계 (추가 63개): ~2분
- 3단계 (추가 592개): ~20분
- 4단계 (추가 84개): ~3분
- **전체 (765개)**: ~25분

### Q7. 실패 시 재실행하면 어떻게 되나요?

**A**: 안전하게 재시작됩니다.

- 성공한 청크: 자동 스킵
- 실패한 청크: 재시도

### Q8. DB를 초기화하지 않고 다시 실행하면?

**A**: 중복 없이 안전하게 처리됩니다.

- 기존 청크: `ON CONFLICT ... DO NOTHING`으로 스킵
- 새 청크: 정상 삽입

---

## 권장 워크플로우

### 처음 실행하는 경우

```bash
# Step 1: 테스트
export CRITERIA_STAGE=1
python backend/scripts/embed_pipeline_v2.py
python backend/scripts/check_embedding_status.py

# Step 2: 성공 확인 후 전체
export CRITERIA_STAGE=0
python backend/scripts/embed_pipeline_v2.py
python backend/scripts/check_embedding_status.py

# Step 3: 검색 테스트
python backend/scripts/test_criteria_search.py
```

### 재실행하는 경우

```bash
# 그냥 전체 실행 (중복 자동 스킵)
export CRITERIA_STAGE=0
python backend/scripts/embed_pipeline_v2.py
```

### 문제가 발생한 경우

```bash
# 1. 로그 확인
tail -f logs/embed_pipeline.log

# 2. DB 상태 확인
python backend/scripts/check_embedding_status.py

# 3. 필요시 롤백
psql -U postgres -d ddoksori -c \
  "DELETE FROM chunks WHERE doc_type='guideline';"

# 4. 재실행
python backend/scripts/embed_pipeline_v2.py
```

---

## 참고 문서

- [임베딩_기준_및_프로세스.md](./임베딩_기준_및_프로세스.md) - 임베딩 작동 원리
- [청킹 및 임베딩 결과 확인 가이드.md](./청킹%20및%20임베딩%20결과%20확인%20가이드.md) - 검증 방법
- [RAG_SETUP_GUIDE.md](./RAG_SETUP_GUIDE.md) - RAG 시스템 전체 가이드

---

## 변경 이력

- 2026-01-05: 초안 작성 (Criteria 임베딩 통합 기능 구현 완료)
