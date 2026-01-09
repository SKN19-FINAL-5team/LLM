# 분쟁조정사례 chunk_index/chunk_total 오류 근본 원인 분석 및 해결

**작성일**: 2026-01-05  
**문제**: `psycopg2.errors.CheckViolation: new row for relation "chunks" violates check constraint "chunks_check"`

---

## 🔍 근본 원인 분석

### 1. 오류 발생 상황

**오류 메시지**:
```
Failing row contains (..., chunk_index=4, chunk_total=3, ...)
```

**제약 조건**:
```sql
CHECK (chunk_index <= chunk_total)
```

**문제**: `4 <= 3` → False → 제약 조건 위반

### 2. 데이터 구조 분석

**normalized 형식 데이터 (ecmc_final_rag_chunks_normalized.jsonl)**:
```json
{"case_uid": "ecmc_merged:4", "case_index": 4, "chunk_type": "decision", "text": "..."}
{"case_uid": "ecmc_merged:4", "case_index": 4, "chunk_type": "parties_claim", "text": "..."}
{"case_uid": "ecmc_merged:4", "case_index": 4, "chunk_type": "judgment", "text": "..."}
```

**특징**:
- `case_uid`: 문서 식별자 (예: `ecmc_merged:4`)
- `case_index`: 문서 번호 (1, 2, 3, 4, ...) - **문서의 순번**
- `chunk_type`: 청크 유형 (decision, parties_claim, judgment)
- 같은 `case_uid`를 가진 여러 청크가 존재 (보통 3개)

### 3. 잘못된 로직 (기존 코드)

```python
# 청크 생성
chunk_index = record.get('case_index', 0)  # ← case_index를 chunk_index로 사용!
chunk_id = f"{doc_id}::chunk{chunk_index}"
chunks.append({
    'chunk_id': chunk_id,
    'doc_id': doc_id,
    'chunk_index': chunk_index,  # ← 4 (문서 번호)
    'chunk_total': 1,  # ← 나중에 업데이트 (하지만 실제로는 업데이트 안됨!)
    ...
})

# chunk_total 업데이트 시도
doc_chunk_counts = {}
for chunk in chunks:
    doc_id = chunk['doc_id']
    doc_chunk_counts[doc_id] = doc_chunk_counts.get(doc_id, 0) + 1

for chunk in chunks:
    if chunk['chunk_total'] == 1 and doc_chunk_counts[chunk['doc_id']] > 1:
        chunk['chunk_total'] = doc_chunk_counts[chunk['doc_id']]
```

**문제점**:
1. **`case_index`를 `chunk_index`로 잘못 사용**
   - `case_index`는 문서 번호 (4번째 문서)
   - `chunk_index`는 청크 순번 (0, 1, 2)
   
2. **`chunk_total` 업데이트 로직 실패**
   - 업데이트 조건: `chunk['chunk_total'] == 1 and doc_chunk_counts[chunk['doc_id']] > 1`
   - 하지만 `chunk_total`은 이미 1로 설정되어 있고, 업데이트되지 않음
   - 이유: 모든 청크가 동일한 조건을 만족하지만, 업데이트가 제대로 작동하지 않음

3. **결과**:
   - `ecmc_merged:4` 문서의 3개 청크:
     - chunk_index=4, chunk_total=1 (또는 3)
     - chunk_index=4, chunk_total=1 (또는 3)
     - chunk_index=4, chunk_total=1 (또는 3)
   - 모든 청크가 동일한 `chunk_index=4`를 가짐 → 중복 ID 발생 가능
   - `chunk_index=4`인데 `chunk_total=3` → 제약 조건 위반

---

## ✅ 해결 방법

### 1. 올바른 로직

**핵심 아이디어**:
- 같은 `case_uid`를 가진 청크들을 **그룹화**
- 각 그룹 내에서 `chunk_index`를 **0부터 순차 할당**
- `chunk_total`은 **그룹의 총 청크 수**로 설정

### 2. 수정된 코드

```python
# 형식 2 데이터를 위한 임시 저장소
doc_chunks_temp = {}  # {doc_id: [chunk_data, ...]}

# 데이터 수집 단계: 청크를 그룹화
for mediation_file in tqdm(mediation_files, desc="분쟁조정사례 파일 처리"):
    with open(mediation_file, 'r', encoding='utf-8') as f:
        for line in f:
            record = json.loads(line)
            
            if 'case_uid' in record:
                source_org = record.get('agency', 'unknown').upper()
                doc_id = f"{source_org.lower()}:mediation_case:{record['case_uid']}"
                
                # 문서 메타데이터 생성 (1회만)
                if doc_id not in [d['doc_id'] for d in documents]:
                    documents.append({...})
                
                # 청크 데이터를 임시 저장소에 모음
                if doc_id not in doc_chunks_temp:
                    doc_chunks_temp[doc_id] = []
                
                doc_chunks_temp[doc_id].append({
                    'chunk_type': record.get('chunk_type', 'unknown'),
                    'content': record['text'],
                    'content_length': record.get('text_len', len(record['text'])),
                    'metadata': {...}
                })

# 청크 생성 단계: 올바른 인덱싱
for doc_id, doc_chunks in doc_chunks_temp.items():
    chunk_total = len(doc_chunks)
    for chunk_index, chunk_data in enumerate(doc_chunks):
        chunk_id = f"{doc_id}::chunk{chunk_index}"
        chunks.append({
            'chunk_id': chunk_id,
            'doc_id': doc_id,
            'chunk_index': chunk_index,  # ← 0, 1, 2 (순차 할당)
            'chunk_total': chunk_total,   # ← 3 (그룹 크기)
            'chunk_type': chunk_data['chunk_type'],
            'content': chunk_data['content'],
            'content_length': chunk_data['content_length'],
            'metadata': chunk_data['metadata']
        })
```

### 3. 결과 비교

**기존 (오류)**:
```
ecmc:mediation_case:ecmc_merged:4
  ├─ chunk_id: ...::chunk4, chunk_index=4, chunk_total=1 (또는 3)
  ├─ chunk_id: ...::chunk4, chunk_index=4, chunk_total=1 (또는 3)  ← 중복 ID!
  └─ chunk_id: ...::chunk4, chunk_index=4, chunk_total=1 (또는 3)  ← 중복 ID!

문제:
- chunk_index=4 > chunk_total=3 → 제약 조건 위반
- 중복 chunk_id → Primary Key 위반 가능
```

**수정 (정상)**:
```
ecmc:mediation_case:ecmc_merged:4
  ├─ chunk_id: ...::chunk0, chunk_index=0, chunk_total=3, chunk_type=decision
  ├─ chunk_id: ...::chunk1, chunk_index=1, chunk_total=3, chunk_type=parties_claim
  └─ chunk_id: ...::chunk2, chunk_index=2, chunk_total=3, chunk_type=judgment

정상:
- 0 <= 3, 1 <= 3, 2 <= 3 → 제약 조건 만족
- 고유한 chunk_id → Primary Key 만족
- 올바른 순서 및 총 개수
```

---

## 📊 영향 범위

### 1. 영향받는 데이터

**파일**:
- `ecmc_final_rag_chunks_normalized.jsonl`
- `kca_final_rag_chunks_normalized.jsonl`
- `kcdrc_final_rag_chunks_normalized.jsonl`

**문서 수**: 약 3,000개 (normalized 형식 데이터)

**청크 수**: 약 9,000개 (문서당 평균 3개 청크)

### 2. 영향받지 않는 데이터

**파일**:
- `kca_cases_116_chunks_v2.jsonl` (이미 올바른 형식)

**이유**: 이미 `doc_id`, `chunk_id`, `chunk_index`, `chunk_total`이 올바르게 설정됨

---

## 🧪 검증 방법

### 1. 수정 전 검증

```bash
# 문제가 있는 청크 찾기
SELECT doc_id, chunk_index, chunk_total
FROM chunks
WHERE chunk_index >= chunk_total;
```

### 2. 수정 후 검증

```bash
# 모든 청크가 제약 조건을 만족하는지 확인
SELECT COUNT(*)
FROM chunks
WHERE chunk_index >= chunk_total;
-- 결과: 0

# 각 문서의 청크 인덱스가 연속적인지 확인
SELECT doc_id, COUNT(*) as total, MAX(chunk_index) + 1 as max_index
FROM chunks
GROUP BY doc_id
HAVING COUNT(*) != MAX(chunk_index) + 1;
-- 결과: 0 (모든 문서가 연속적)
```

### 3. 데이터 품질 확인

```bash
# 청크 인덱스 분포 확인
SELECT chunk_index, COUNT(*) 
FROM chunks 
WHERE doc_type = 'mediation_case'
GROUP BY chunk_index 
ORDER BY chunk_index;

# 청크 총 개수 분포 확인
SELECT chunk_total, COUNT(*) 
FROM chunks 
WHERE doc_type = 'mediation_case'
GROUP BY chunk_total 
ORDER BY chunk_total;
```

---

## 🎯 교훈

### 1. 데이터 필드 이름의 의미 파악

- `case_index`: 문서 번호 (문서의 순번)
- `chunk_index`: 청크 번호 (청크의 순번, 0부터 시작)
- **절대 혼동하지 말 것!**

### 2. 제약 조건의 중요성

- 데이터베이스 제약 조건은 데이터 무결성을 보장
- 제약 조건 위반은 데이터 모델링 오류의 신호
- 제약 조건을 "우회"하지 말고 "근본 원인"을 해결

### 3. 그룹화 및 인덱싱

- 같은 문서에 속한 청크들은 그룹화하여 처리
- 인덱스는 그룹 내에서 순차적으로 할당
- 임시 저장소를 사용하여 올바른 인덱싱 보장

### 4. 테스트 주도 개발

- 데이터 처리 로직은 반드시 테스트 필요
- 샘플 데이터로 먼저 검증 후 전체 데이터 처리
- 제약 조건 위반은 조기에 발견하여 수정

---

## 📝 참고 자료

- **스키마 파일**: `backend/database/schema_v2_final.sql`
- **임베딩 파이프라인**: `backend/scripts/embed_pipeline_v2.py`
- **데이터 파일**: `backend/data/dispute_resolution/*.jsonl`

---

**작성자**: Manus AI  
**커밋**: 16192c0  
**브랜치**: feature/pr4-multi-agent-prep
