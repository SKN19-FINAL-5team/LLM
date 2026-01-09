# chunk_index 검토 보고서

**작성일**: 2026-01-06  
**목적**: 임베딩 중 오류 방지를 위한 chunk_index 일관성 검토  
**심각도**: 🔴 **HIGH** - 임베딩 중단 시 재시작 비용 매우 큼

---

## 🚨 핵심 발견

### ⚠️ 문제: chunk_index 인덱싱 방식이 파일마다 다름

| 파일 | chunk_index 필드 | 시작 값 | 상태 |
|-----|-----------------|--------|------|
| **compensation_case** | ✅ 있음 | **0** | ✅ 0-based (정상) |
| **table2 (criteria)** | ❌ 없음 (row_idx만 존재) | **1** | ⚠️ 1-based |
| **kca_final** | ❌ 없음 (case_index는 문서 번호) | **1** | ⚠️ 1-based |
| **ecmc** | ❌ 없음 (seq는 1부터 시작) | **1** | ⚠️ 1-based |
| **law** | ❌ 없음 (unit_id만 존재) | N/A | ⚠️ 인덱스 없음 |

---

## 📊 상세 분석 결과

### 1. compensation_case (피해구제사례) ✅

```json
{
  "chunk_index": 0,      // ✅ 0-based
  "chunk_total": 1,
  "doc_id": "consumer.go.kr:consumer_counsel_case:53321"
}
```

**상태**: ✅ 정상 (0-based)  
**액션**: 변환 불필요

---

### 2. criteria/table2 (해결기준) ⚠️

```json
{
  "row_idx": 1,          // ⚠️ 1-based (1~126)
  "chunk_id": "table2_row_p1_...",
  "text": "..."
}
```

**문제**:
- `chunk_index` 필드 없음
- `row_idx`는 1부터 시작 (1-based)
- 전체 126개 row: 1, 2, 3, ..., 126

**해결 방법**:
```python
# 변환 시 0-based로 변경
chunk_index = row_idx - 1  # 1 → 0, 2 → 1, 3 → 2, ...
```

---

### 3. dispute_resolution/kca_final ⚠️

```json
{
  "case_index": 1,       // ⚠️ 이것은 문서 번호 (case 1, 2, 3...)
  "case_no": "2015일가27",
  "chunk_type": "decision"
}
```

**문제**:
- `chunk_index` 필드 없음
- `case_index`는 **문서 번호**이지 청크 인덱스가 아님
- 같은 case_no에 여러 청크 (decision, parties_claim, judgment)

**해결 방법**:
```python
# case_no별로 그룹화 후 청크 인덱스 할당
chunks_by_case = {}
for item in data:
    case_no = item['case_no']
    if case_no not in chunks_by_case:
        chunks_by_case[case_no] = []
    chunks_by_case[case_no].append(item)

# 각 케이스별로 0부터 인덱스 부여
for case_no, chunks in chunks_by_case.items():
    for idx, chunk in enumerate(chunks):
        chunk['chunk_index'] = idx  # 0, 1, 2, ...
        chunk['chunk_total'] = len(chunks)
```

---

### 4. dispute_resolution/ecmc ⚠️

```json
{
  "seq": 1,              // ⚠️ 1-based
  "case_index": 1,       // ⚠️ 문서 번호
  "case_no": "CA09-02073",
  "chunk_type": "decision"
}
```

**문제**:
- `chunk_index` 필드 없음
- `seq`는 1부터 시작
- `case_index`는 문서 번호

**해결 방법**:
```python
# case_no별로 그룹화 후 0-based 인덱스 할당
# (kca_final과 동일한 방식)
```

---

### 5. law (법령) ⚠️

```json
{
  "unit_id": "001706|A1",
  "law_id": "001706",
  "law_name": "민법"
}
```

**문제**:
- `chunk_index` 필드 없음
- 조문 단위로 나뉘어 있지만 인덱스 없음

**해결 방법**:
```python
# law_id별로 그룹화 후 0-based 인덱스 할당
chunks_by_law = {}
for item in data:
    law_id = item['law_id']
    if law_id not in chunks_by_law:
        chunks_by_law[law_id] = []
    chunks_by_law[law_id].append(item)

for law_id, chunks in chunks_by_law.items():
    for idx, chunk in enumerate(chunks):
        chunk['chunk_index'] = idx
        chunk['chunk_total'] = len(chunks)
```

---

## 🔥 임베딩 중 발생 가능한 오류 시나리오

### 시나리오 1: CHECK 제약 조건 위반

```python
# ❌ 잘못된 경우
INSERT INTO chunks (chunk_id, doc_id, chunk_index, chunk_total, ...)
VALUES ('...', '...', 1, 3, ...)  -- chunk_index가 1부터 시작

# CHECK (chunk_index < chunk_total) 위반!
# chunk_index=1, chunk_total=3 이면 마지막 청크는 chunk_index=2여야 하는데
# 1-based로 하면 chunk_index=3이 되어 오류 발생
```

**오류 메시지**:
```
psycopg2.errors.CheckViolation: new row for relation "chunks" violates check constraint "chunks_chunk_index_check"
DETAIL: Failing row contains (..., chunk_index=3, chunk_total=3, ...)
```

### 시나리오 2: UNIQUE 제약 조건 위반

```python
# ❌ 인덱스를 잘못 할당한 경우
# 같은 doc_id에 대해 chunk_index가 중복될 수 있음

INSERT INTO chunks (doc_id, chunk_index, ...) VALUES ('doc1', 0, ...)
INSERT INTO chunks (doc_id, chunk_index, ...) VALUES ('doc1', 0, ...)  -- 중복!

# UNIQUE(doc_id, chunk_index) 위반!
```

**오류 메시지**:
```
psycopg2.errors.UniqueViolation: duplicate key value violates unique constraint "chunks_doc_id_chunk_index_key"
DETAIL: Key (doc_id, chunk_index)=(doc1, 0) already exists.
```

### 시나리오 3: 임베딩 배치 중간 중단

```python
# 10,000개 청크 중 5,234번째에서 오류 발생
# → 전체 프로세스 중단
# → 처음부터 다시 시작해야 함 (5,233개 재임베딩!)
```

**임베딩 재시작 비용**:
- 시간: 5,000개 청크 × 0.5초 = **~42분** 낭비
- GPU 비용: RunPod 사용 시 **$3~5** 낭비
- 인력 비용: 모니터링 및 재시작 시간

---

## ✅ 해결 방안

### 1. 데이터 변환 시 통일된 인덱싱 로직

```python
class DataTransformer:
    """모든 데이터를 0-based chunk_index로 통일"""
    
    def _assign_chunk_indices(self, chunks: List[dict]) -> List[dict]:
        """
        청크 리스트에 0-based 인덱스 할당
        
        Args:
            chunks: 같은 문서의 청크 리스트
        
        Returns:
            chunk_index, chunk_total이 할당된 청크 리스트
        """
        total = len(chunks)
        for idx, chunk in enumerate(chunks):
            chunk['chunk_index'] = idx  # 0, 1, 2, ...
            chunk['chunk_total'] = total
        return chunks
    
    def transform_law_data(self, file_path):
        """법령 데이터 변환 - 0-based 인덱스 할당"""
        chunks_by_law = {}
        
        with open(file_path, 'r') as f:
            for line in f:
                data = json.loads(line)
                law_id = data['law_id']
                
                if law_id not in chunks_by_law:
                    chunks_by_law[law_id] = []
                chunks_by_law[law_id].append(data)
        
        # 각 법령별로 0-based 인덱스 할당
        for law_id, chunks in chunks_by_law.items():
            chunks = self._assign_chunk_indices(chunks)
            self._insert_chunks(f"statute:{law_id}", chunks)
    
    def transform_criteria_table2(self, file_path):
        """기준 데이터 변환 - row_idx를 0-based로 변환"""
        chunks = []
        
        with open(file_path, 'r') as f:
            for line in f:
                data = json.loads(line)
                chunks.append(data)
        
        # 0-based 인덱스 할당 (row_idx는 무시)
        chunks = self._assign_chunk_indices(chunks)
        self._insert_chunks('criteria:table2', chunks)
    
    def transform_mediation_kca(self, file_path):
        """분쟁조정사례 변환 - case_no별로 0-based 인덱스 할당"""
        chunks_by_case = {}
        
        with open(file_path, 'r') as f:
            for line in f:
                data = json.loads(line)
                case_no = data['case_no']
                
                if case_no not in chunks_by_case:
                    chunks_by_case[case_no] = []
                chunks_by_case[case_no].append(data)
        
        # 각 케이스별로 0-based 인덱스 할당
        for case_no, chunks in chunks_by_case.items():
            chunks = self._assign_chunk_indices(chunks)
            self._insert_chunks(f"kca:mediation:{case_no}", chunks)
```

### 2. 변환 전 검증 스크립트

```python
def validate_chunk_indices_before_insert():
    """
    DB 삽입 전 chunk_index 검증
    - 0부터 시작하는지
    - 연속적인지
    - chunk_total과 일치하는지
    """
    for doc_id, chunks in documents.items():
        # 인덱스 정렬
        chunks.sort(key=lambda x: x['chunk_index'])
        
        # 검증
        expected_indices = list(range(len(chunks)))
        actual_indices = [c['chunk_index'] for c in chunks]
        
        if expected_indices != actual_indices:
            raise ValueError(
                f"Invalid chunk_index for {doc_id}:\n"
                f"  Expected: {expected_indices}\n"
                f"  Actual: {actual_indices}"
            )
        
        # chunk_total 검증
        for chunk in chunks:
            if chunk['chunk_total'] != len(chunks):
                raise ValueError(
                    f"Invalid chunk_total for {chunk['chunk_id']}:\n"
                    f"  Expected: {len(chunks)}\n"
                    f"  Actual: {chunk['chunk_total']}"
                )
        
        print(f"✅ {doc_id}: {len(chunks)} chunks validated")
```

### 3. 안전한 배치 삽입

```python
def safe_batch_insert(chunks: List[dict], batch_size: int = 100):
    """
    안전한 배치 삽입 - 오류 발생 시 재시작 지점 기록
    """
    total = len(chunks)
    
    for i in range(0, total, batch_size):
        batch = chunks[i:i+batch_size]
        
        try:
            # 배치 삽입
            cursor.executemany("""
                INSERT INTO chunks (...)
                VALUES (...)
            """, batch)
            conn.commit()
            
            # 진행 상황 저장
            save_progress(i + len(batch))
            
            print(f"✅ Batch {i//batch_size + 1}/{(total+batch_size-1)//batch_size}: "
                  f"{i + len(batch)}/{total} chunks inserted")
            
        except Exception as e:
            conn.rollback()
            print(f"❌ Error at batch {i//batch_size + 1} (chunk {i}):")
            print(f"   {e}")
            
            # 문제가 된 청크 출력
            for idx, chunk in enumerate(batch):
                print(f"   [{idx}] chunk_id={chunk['chunk_id']}, "
                      f"chunk_index={chunk['chunk_index']}, "
                      f"chunk_total={chunk['chunk_total']}")
            
            raise
```

---

## 📋 변환 체크리스트

### 변환 전 필수 확인 사항

- [ ] **모든 chunk_index가 0부터 시작하는지 확인**
- [ ] **같은 doc_id 내에서 chunk_index가 연속적인지 확인**
- [ ] **chunk_index < chunk_total 조건 만족하는지 확인**
- [ ] **UNIQUE(doc_id, chunk_index) 위반 없는지 확인**

### 파일별 변환 전략

#### ✅ compensation_case
- [x] 이미 0-based
- [ ] 그대로 사용
- [ ] 검증만 수행

#### ⚠️ criteria/table2
- [ ] row_idx 무시
- [ ] 새로운 0-based 인덱스 할당
- [ ] 검증 수행

#### ⚠️ dispute_resolution/kca_final
- [ ] case_no별 그룹화
- [ ] 각 그룹에 0-based 인덱스 할당
- [ ] 검증 수행

#### ⚠️ dispute_resolution/ecmc
- [ ] case_no별 그룹화
- [ ] 각 그룹에 0-based 인덱스 할당
- [ ] drop=true 청크 포함하여 인덱스 할당 (나중에 검색만 제외)
- [ ] 검증 수행

#### ⚠️ law
- [ ] law_id별 그룹화
- [ ] 각 법령에 0-based 인덱스 할당
- [ ] 검증 수행

---

## 🔧 수정된 스키마 확인

현재 스키마 (`schema_v2_final.sql`)는 이미 0-based를 지원합니다:

```sql
CHECK (chunk_index >= 0)  -- ✅ 0부터 시작 허용
CHECK (chunk_total > 0)
CHECK (chunk_index < chunk_total)  -- ✅ 0-based 전제
```

**예시**:
- chunk_total = 3인 문서
- 유효한 chunk_index: 0, 1, 2 ✅
- 무효한 chunk_index: 1, 2, 3 ❌ (3 < 3 위반)

---

## 📊 예상 변환 결과

### 변환 전 (원본 데이터)

| 파일 | 인덱스 필드 | 범위 |
|-----|-----------|------|
| compensation_case | chunk_index | 0~ |
| table2 | row_idx | 1~126 |
| kca_final | (없음) | N/A |
| ecmc | seq | 1~ |
| law | (없음) | N/A |

### 변환 후 (DB 삽입)

| 파일 | chunk_index | chunk_total | 검증 |
|-----|------------|------------|------|
| compensation_case | 0~ | ✓ | ✅ |
| table2 | 0~125 | 126 | ✅ |
| kca_final (case 1) | 0~2 | 3 | ✅ |
| ecmc (case 1) | 0~2 | 3 | ✅ |
| law (민법) | 0~1751 | 1752 | ✅ |

---

## ⚡ 긴급 액션 아이템

### 1. 즉시 수행 (Priority: HIGH)

```python
# 데이터 변환 스크립트에 다음 함수 필수 포함
def _assign_chunk_indices(self, chunks: List[dict]) -> List[dict]:
    """모든 청크에 0-based 인덱스 할당"""
    total = len(chunks)
    for idx, chunk in enumerate(chunks):
        chunk['chunk_index'] = idx
        chunk['chunk_total'] = total
    return chunks
```

### 2. 변환 전 테스트 (Priority: HIGH)

```bash
# 작은 샘플로 먼저 테스트
cd /home/maroco/ddoksori_demo/backend
conda activate ddoksori

# 1. 스키마 적용
docker exec -it ddoksori_db psql -U postgres -d ddoksori -f /schema/schema_v2_final.sql

# 2. 샘플 데이터 변환 (각 파일에서 10개씩만)
python scripts/test_transform_sample.py

# 3. chunk_index 검증
python scripts/validate_chunk_indices.py

# 4. 문제 없으면 전체 변환
python scripts/data_transform_pipeline.py
```

### 3. 변환 후 검증 (Priority: HIGH)

```sql
-- 1. 모든 chunk_index가 0부터 시작하는지 확인
SELECT doc_id, MIN(chunk_index) as min_idx
FROM chunks
GROUP BY doc_id
HAVING MIN(chunk_index) != 0;
-- 결과: 0개여야 함

-- 2. chunk_index가 연속적인지 확인
SELECT doc_id, chunk_total, COUNT(*) as actual_count
FROM chunks
GROUP BY doc_id, chunk_total
HAVING COUNT(*) != chunk_total;
-- 결과: 0개여야 함

-- 3. chunk_index < chunk_total 확인
SELECT chunk_id, chunk_index, chunk_total
FROM chunks
WHERE chunk_index >= chunk_total;
-- 결과: 0개여야 함
```

---

## 📝 결론

### 🔴 심각도: HIGH

원본 데이터의 인덱싱 방식이 불일치하여 **임베딩 중 오류 발생 가능성 매우 높음**.

### ✅ 해결 방법

1. **데이터 변환 시 모든 chunk_index를 0-based로 통일**
2. **원본 데이터의 인덱스는 무시하고 새로 할당**
3. **변환 전후 검증 필수**

### ⚡ 다음 단계

1. **데이터 변환 스크립트에 `_assign_chunk_indices()` 함수 추가**
2. **샘플 데이터로 테스트**
3. **검증 통과 후 전체 변환**
4. **임베딩 시작**

---

**작성자**: Manus AI (RAG 시스템 전문가)  
**최종 수정**: 2026-01-06  
**승인 필요**: ⚠️ 데이터 변환 스크립트 작성 전 필독
