# PR #2: 데이터 임베딩 및 Vector DB 구축

## 개요

이 PR에서는 한국소비자원(KCA), 한국전자거래분쟁조정위원회(ECMC), 한국저작권위원회(KCDRC)의 분쟁조정 사례 데이터를 PostgreSQL + pgvector에 저장하고, KURE-v1 모델을 사용하여 임베딩을 생성합니다.

## 변경 사항

### 1. 데이터베이스 설정

- **pgvector 지원**: `docker-compose.yml`에서 PostgreSQL 이미지를 `pgvector/pgvector:pg16`으로 변경
- **스키마 정의**: `backend/database/schema.sql`에 `cases`와 `chunks` 테이블 정의
- **초기화 스크립트**: `backend/database/init.sql`로 데이터베이스 자동 생성

### 2. 데이터 구조

#### Cases 테이블
사례 메타데이터를 저장합니다.

| 컬럼명 | 타입 | 설명 |
|---|---|---|
| `case_uid` | VARCHAR(255) | 사례 고유 ID (예: `kca_merged:1`) |
| `case_no` | VARCHAR(255) | 사건번호 (예: `2015일가027`) |
| `decision_date` | VARCHAR(50) | 결정일자 (예: `2015.05.11`) |
| `agency` | VARCHAR(50) | 발행 기관 (`kca`, `ecmc`, `kcdrc`) |
| `source` | VARCHAR(255) | 데이터 출처 |

#### Chunks 테이블
청크 텍스트와 임베딩 벡터를 저장합니다.

| 컬럼명 | 타입 | 설명 |
|---|---|---|
| `chunk_uid` | VARCHAR(255) | 청크 고유 ID |
| `case_uid` | VARCHAR(255) | 연결된 사례 ID |
| `chunk_type` | VARCHAR(50) | 청크 타입 (`decision`, `parties_claim`, `judgment`) |
| `text` | TEXT | 텍스트 내용 |
| `embedding` | vector(1024) | KURE-v1 임베딩 벡터 |

### 3. 임베딩 파이프라인

`backend/scripts/embedding/embed_data_remote.py`는 다음 작업을 수행합니다:

1. KURE-v1 모델 로드 (Hugging Face)
2. JSONL 파일에서 데이터 읽기
3. 사례 메타데이터를 `cases` 테이블에 삽입
4. 각 청크를 임베딩하여 `chunks` 테이블에 삽입
5. 삽입된 데이터 통계 출력

### 4. 데이터 파일

`backend/data/` 디렉토리에 다음 파일들이 포함됩니다:

- `kca_final_rag_chunks_normalized.jsonl` (2,059 청크)
- `ecmc_final_rag_chunks_normalized.jsonl` (932 청크)
- `kcdrc_final_rag_chunks_normalized.jsonl` (367 청크)

**총 3,358개 청크**

## 설치 및 실행

### 1. 리포지토리 클론

```bash
git clone https://github.com/Maroco0109/ddoksori_demo.git
cd ddoksori_demo
git checkout feature/pr2-data-embedding
```

### 2. 환경 변수 설정

```bash
# 백엔드 환경 변수
cd backend
cp .env.example .env
# .env 파일을 열어서 필요한 값 수정 (기본값 사용 가능)
```

### 3. Docker Compose로 PostgreSQL 실행

```bash
cd ..
docker-compose up -d db
```

### 4. Python 패키지 설치

```bash
cd backend
pip install -r requirements.txt
```

### 5. 데이터 임베딩 실행

```bash
python scripts/embed_data.py
```

**예상 소요 시간:**
- GPU 사용 시: 약 5-10분
- CPU 사용 시: 약 20-30분

### 6. 데이터 확인

PostgreSQL에 접속하여 데이터를 확인합니다:

```bash
docker exec -it ddoksori_db psql -U postgres -d ddoksori
```

```sql
-- 사례 수 확인
SELECT COUNT(*) FROM cases;

-- 청크 수 확인
SELECT COUNT(*) FROM chunks;

-- 기관별 통계
SELECT agency, COUNT(*) FROM cases GROUP BY agency;

-- 청크 타입별 통계
SELECT chunk_type, COUNT(*) FROM chunks GROUP BY chunk_type;
```

## 기술 스택

- **데이터베이스**: PostgreSQL 16 + pgvector
- **임베딩 모델**: KURE-v1 (nlpai-lab/KURE-v1)
  - 차원: 1024
  - 한국어 특화 임베딩 모델
- **Python 라이브러리**:
  - `sentence-transformers`: 임베딩 생성
  - `psycopg2-binary`: PostgreSQL 연결
  - `pgvector`: pgvector 확장 지원

## 다음 단계 (PR #3)

PR #3에서는 RAG 시스템을 구축하여 Vector DB에서 유사 사례를 검색하고, LLM을 사용하여 답변을 생성하는 기능을 구현합니다.
