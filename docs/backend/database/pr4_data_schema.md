# 데이터베이스 스키마 설계 (4가지 데이터 종류)

PR #4에서 추가될 데이터 종류(법령, 분쟁조정기준, 상담사례)를 포함한 전체 데이터베이스 스키마를 설계합니다.

---

## 1. 데이터 종류 및 특성

| 데이터 종류 | 설명 | 실질 효력 | 청킹 전략 | 검색 우선순위 |
|---|---|---|---|---|
| **법령** | 소비자기본법, 전자상거래법 등 | N/A | 조문 단위 | 1 (관할 판단용) |
| **분쟁조정기준** | 품목별 분쟁조정 기준 | N/A | 품목별 기준 단위 | 1 (관할 판단용) |
| **분쟁조정사례** | 조정위원회의 조정명령 사례 | ✅ 있음 | 주문/기초사실/판단 | 2 (유사 사례 검색) |
| **상담사례** | 피해구제 및 상담 사례 | ❌ 없음 | 사례 단위 | 3 (Fallback) |

---

## 2. 데이터베이스 스키마 설계

### 2.1. 테이블 구조 개요

```
cases (사례 메타데이터)
  ├── 분쟁조정사례
  └── 상담사례

laws (법령 데이터)
  └── 법령 조문

standards (분쟁조정기준 데이터)
  └── 품목별 기준

chunks (청크 및 임베딩)
  ├── 분쟁조정사례 청크
  ├── 상담사례 청크
  ├── 법령 청크
  └── 분쟁조정기준 청크
```

### 2.2. 상세 스키마

#### 2.2.1. `cases` 테이블 (기존 유지, 타입 추가)

분쟁조정사례와 상담사례의 메타데이터를 저장합니다.

```sql
CREATE TABLE IF NOT EXISTS cases (
    id SERIAL PRIMARY KEY,
    case_uid VARCHAR(255) UNIQUE NOT NULL,
    case_type VARCHAR(50) NOT NULL,  -- 'precedent' (분쟁조정사례) 또는 'consultation' (상담사례)
    case_no VARCHAR(255),
    decision_date VARCHAR(50),
    agency VARCHAR(50),  -- 'kca', 'ecmc', 'kcdrc' 등
    source VARCHAR(255),
    case_index INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_cases_case_type ON cases(case_type);
CREATE INDEX idx_cases_agency ON cases(agency);
CREATE INDEX idx_cases_decision_date ON cases(decision_date);

COMMENT ON TABLE cases IS '분쟁조정사례 및 상담사례 메타데이터';
COMMENT ON COLUMN cases.case_type IS 'precedent: 분쟁조정사례 (실질 효력 있음), consultation: 상담사례 (실질 효력 없음)';
```

#### 2.2.2. `laws` 테이블 (신규)

법령 데이터를 저장합니다.

```sql
CREATE TABLE IF NOT EXISTS laws (
    id SERIAL PRIMARY KEY,
    law_uid VARCHAR(255) UNIQUE NOT NULL,
    law_name VARCHAR(255) NOT NULL,  -- 예: '소비자기본법'
    article VARCHAR(100),  -- 예: '제1조', '제2조의2'
    clause VARCHAR(100),  -- 예: '제1항', '제2항'
    content TEXT NOT NULL,
    category VARCHAR(100),  -- 예: '기본법', '특별법'
    enacted_date VARCHAR(50),  -- 제정일
    amended_date VARCHAR(50),  -- 최종 개정일
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_laws_law_name ON laws(law_name);
CREATE INDEX idx_laws_category ON laws(category);

COMMENT ON TABLE laws IS '소비자 관련 법령 데이터';
```

#### 2.2.3. `standards` 테이블 (신규)

분쟁조정기준 데이터를 저장합니다.

```sql
CREATE TABLE IF NOT EXISTS standards (
    id SERIAL PRIMARY KEY,
    standard_uid VARCHAR(255) UNIQUE NOT NULL,
    item_category VARCHAR(100) NOT NULL,  -- 예: '전자제품', '의류', '식품'
    item_name VARCHAR(255),  -- 예: '휴대폰', '노트북'
    issue_type VARCHAR(255),  -- 예: '하자', '지연', '환불'
    standard_content TEXT NOT NULL,  -- 조정 기준 내용
    applicable_period VARCHAR(100),  -- 예: '구입 후 1개월 이내'
    remedy VARCHAR(255),  -- 예: '교환', '환불', '수리'
    source VARCHAR(100),  -- 예: '소비자분쟁해결기준 고시'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_standards_item_category ON standards(item_category);
CREATE INDEX idx_standards_issue_type ON standards(issue_type);

COMMENT ON TABLE standards IS '소비자 분쟁조정 기준 데이터';
```

#### 2.2.4. `chunks` 테이블 (확장)

모든 데이터의 청크와 임베딩을 저장합니다.

```sql
CREATE TABLE IF NOT EXISTS chunks (
    id SERIAL PRIMARY KEY,
    chunk_uid VARCHAR(255) UNIQUE NOT NULL,
    
    -- 참조 정보 (데이터 종류에 따라 하나만 사용)
    case_uid VARCHAR(255) REFERENCES cases(case_uid) ON DELETE CASCADE,  -- 분쟁/상담사례
    law_uid VARCHAR(255) REFERENCES laws(law_uid) ON DELETE CASCADE,  -- 법령
    standard_uid VARCHAR(255) REFERENCES standards(standard_uid) ON DELETE CASCADE,  -- 분쟁조정기준
    
    -- 청크 정보
    data_type VARCHAR(50) NOT NULL,  -- 'case', 'law', 'standard'
    chunk_type VARCHAR(50),  -- case: 'decision'/'parties_claim'/'judgment', law: 'article', standard: 'criterion'
    text TEXT NOT NULL,
    text_len INTEGER,
    embedding vector(1024),  -- KURE-v1 임베딩 (1024차원)
    seq INTEGER,
    drop BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 제약조건: case_uid, law_uid, standard_uid 중 정확히 하나만 NOT NULL이어야 함
    CHECK (
        (case_uid IS NOT NULL AND law_uid IS NULL AND standard_uid IS NULL) OR
        (case_uid IS NULL AND law_uid IS NOT NULL AND standard_uid IS NULL) OR
        (case_uid IS NULL AND law_uid IS NULL AND standard_uid IS NOT NULL)
    )
);

CREATE INDEX idx_chunks_data_type ON chunks(data_type);
CREATE INDEX idx_chunks_chunk_type ON chunks(chunk_type);
CREATE INDEX idx_chunks_case_uid ON chunks(case_uid);
CREATE INDEX idx_chunks_law_uid ON chunks(law_uid);
CREATE INDEX idx_chunks_standard_uid ON chunks(standard_uid);
CREATE INDEX idx_chunks_embedding ON chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

COMMENT ON TABLE chunks IS '모든 데이터의 청크 및 임베딩 벡터';
COMMENT ON COLUMN chunks.data_type IS 'case: 분쟁/상담사례, law: 법령, standard: 분쟁조정기준';
```

---

## 3. JSONL 데이터 형식 (예상)

### 3.1. 법령 데이터 (`laws.jsonl`)

```jsonl
{"law_uid": "law_001", "law_name": "소비자기본법", "article": "제1조", "clause": null, "content": "이 법은 소비자의 권익을 증진하기 위하여 소비자의 권리와 책무, 국가·지방자치단체 및 사업자의 책무...", "category": "기본법", "enacted_date": "1986.12.31", "amended_date": "2023.01.03"}
{"law_uid": "law_002", "law_name": "전자상거래 등에서의 소비자보호에 관한 법률", "article": "제17조", "clause": "제1항", "content": "통신판매업자는 청약철회 등이 있는 때에는 지체 없이 재화 등의 대금을 환급하여야 한다...", "category": "특별법", "enacted_date": "2002.03.30", "amended_date": "2023.06.13"}
```

### 3.2. 분쟁조정기준 데이터 (`standards.jsonl`)

```jsonl
{"standard_uid": "std_001", "item_category": "전자제품", "item_name": "휴대폰", "issue_type": "액정 파손", "standard_content": "구입 후 1개월 이내 자연 파손 시 제조사 책임으로 무상 교환", "applicable_period": "구입 후 1개월 이내", "remedy": "교환", "source": "소비자분쟁해결기준 고시"}
{"standard_uid": "std_002", "item_category": "의류", "item_name": "셔츠", "issue_type": "색상 변색", "standard_content": "세탁 1회 이내 변색 발생 시 환불 또는 교환", "applicable_period": "세탁 1회 이내", "remedy": "환불/교환", "source": "소비자분쟁해결기준 고시"}
```

### 3.3. 상담사례 데이터 (`consultation_cases.jsonl`)

분쟁조정사례와 동일한 구조이지만, `case_type: "consultation"`으로 구분합니다.

```jsonl
{"case_uid": "consultation_001", "case_type": "consultation", "case_no": null, "decision_date": "2023.05.10", "agency": "kca", "source": "소비자24", "case_index": 1, "chunk_uid": "consultation_001_summary", "data_type": "case", "chunk_type": "summary", "text": "온라인 쇼핑몰에서 구입한 의류가 사진과 다른 색상으로 도착. 판매자에게 환불 요청했으나 거부당함. 소비자원 상담 후 판매자와 협의하여 전액 환불 완료.", "text_len": 85, "seq": 1, "drop": false}
```

---

## 4. 데이터 임베딩 파이프라인 (PR #4에서 구현)

### 4.1. 법령 데이터 임베딩

- **청킹 단위**: 조문 단위 (article + clause + content)
- **chunk_type**: `"article"`
- **임베딩 대상**: `content` (조문 전문)

### 4.2. 분쟁조정기준 데이터 임베딩

- **청킹 단위**: 품목별 기준 단위 (item_name + issue_type + standard_content)
- **chunk_type**: `"criterion"`
- **임베딩 대상**: `standard_content` (기준 내용)

### 4.3. 상담사례 데이터 임베딩

- **청킹 단위**: 사례 단위 또는 구조적 청킹 (분쟁조정사례와 동일)
- **chunk_type**: `"summary"`, `"resolution"` 등
- **임베딩 대상**: 사례 전문

---

## 5. 검색 쿼리 예시

### 5.1. 관할위원회 판단 (법령 + 분쟁조정기준 검색)

```sql
SELECT 
    c.text,
    l.law_name,
    l.article,
    s.item_category,
    s.remedy,
    1 - (c.embedding <=> %s::vector) AS similarity
FROM chunks c
LEFT JOIN laws l ON c.law_uid = l.law_uid
LEFT JOIN standards s ON c.standard_uid = s.standard_uid
WHERE c.data_type IN ('law', 'standard') AND c.drop = FALSE
ORDER BY c.embedding <=> %s::vector
LIMIT 5;
```

### 5.2. 분쟁조정사례 검색 (우선순위 높음)

```sql
SELECT 
    c.text,
    cs.case_no,
    cs.agency,
    cs.decision_date,
    1 - (c.embedding <=> %s::vector) AS similarity
FROM chunks c
JOIN cases cs ON c.case_uid = cs.case_uid
WHERE c.data_type = 'case' AND cs.case_type = 'precedent' AND c.drop = FALSE
ORDER BY c.embedding <=> %s::vector
LIMIT 5;
```

### 5.3. 상담사례 검색 (Fallback)

```sql
SELECT 
    c.text,
    cs.agency,
    cs.decision_date,
    1 - (c.embedding <=> %s::vector) AS similarity
FROM chunks c
JOIN cases cs ON c.case_uid = cs.case_uid
WHERE c.data_type = 'case' AND cs.case_type = 'consultation' AND c.drop = FALSE
ORDER BY c.embedding <=> %s::vector
LIMIT 5;
```

---

## 6. PR #4 구현 체크리스트

- [ ] `laws` 테이블 및 `standards` 테이블 생성
- [ ] `cases` 테이블에 `case_type` 컬럼 추가
- [ ] `chunks` 테이블에 `law_uid`, `standard_uid`, `data_type` 컬럼 추가
- [ ] 법령 데이터 임베딩 스크립트 작성
- [ ] 분쟁조정기준 데이터 임베딩 스크립트 작성
- [ ] 상담사례 데이터 임베딩 스크립트 작성
- [ ] `VectorRetriever` 클래스에 `data_type` 필터링 기능 추가
- [ ] LangGraph 기반 멀티 에이전트 워크플로우 구현
- [ ] 테스트 스크립트 작성 및 검증

---

이 스키마 설계를 바탕으로 PR #4를 진행하면, 법령/분쟁조정기준/분쟁조정사례/상담사례를 체계적으로 관리하고 검색할 수 있습니다.
