# 🎓 RAG 시스템 Vector DB 관리 가이드

**작성일**: 2026-01-06

---

## 📋 목차

1. [Vector DB 개요](#vector-db-개요)
2. [팀원과 공유하는 방법](#팀원과-공유하는-방법)
3. [Vector DB 확인 방법](#vector-db-확인-방법)
4. [백업 및 복원](#백업-및-복원)
5. [품질 관리](#품질-관리)
6. [트러블슈팅](#트러블슈팅)

---

## Vector DB 개요

### 현재 시스템 구성

```
똑소리 RAG 시스템
├── 데이터베이스: PostgreSQL 15
├── 벡터 확장: pgvector
├── 임베딩 모델: KURE-v1 (1024차원)
├── 총 문서: 11,976개
├── 총 청크: 20,269개
└── DB 크기: 481 MB
```

### 핵심 구성 요소

1. **documents 테이블** (29 MB)
   - 문서 메타데이터 저장
   - doc_id, doc_type, title, source_org 등

2. **chunks 테이블** (444 MB)
   - 청크 텍스트 및 임베딩 벡터
   - 1024차원 벡터 (KURE-v1)
   - HNSW 인덱스로 빠른 유사도 검색

3. **임베딩 인덱스** (273 MB)
   - pgvector HNSW 인덱스
   - 코사인 유사도 기반 검색

---

## 팀원과 공유하는 방법

### 방법 1: 데이터베이스 덤프 (권장 ⭐)

**장점**: 
- 완전한 데이터 복제
- 스키마 + 데이터 + 인덱스 모두 포함
- 버전 관리 가능

**단계별 가이드**:

#### 1️⃣ Vector DB 백업 생성

```bash
cd /home/maroco/ddoksori_demo/backend/scripts
./export_vectordb.sh
```

**출력 예시**:
```
================================================================================
Vector DB 백업 생성
================================================================================
데이터베이스: ddoksori
호스트: localhost:5432
출력 파일: ./vectordb_backups/ddoksori_vectordb_20260106_153000.sql

📦 데이터베이스 덤프 생성 중...
✅ 덤프 완료: ./vectordb_backups/ddoksori_vectordb_20260106_153000.sql

🗜️  압축 중...
✅ 압축 완료: ./vectordb_backups/ddoksori_vectordb_20260106_153000.sql.gz

================================================================================
✅ 백업 완료!
================================================================================
파일: ./vectordb_backups/ddoksori_vectordb_20260106_153000.sql.gz
크기: 145MB

📤 팀원과 공유 방법:
  1. 클라우드 스토리지 (Google Drive, Dropbox 등)
  2. 내부 파일 서버
  3. Git LFS (50MB 이하인 경우)
```

#### 2️⃣ 팀원이 복원하는 방법

```bash
# 1. 백업 파일 다운로드
cd /home/maroco/ddoksori_demo/backend/scripts

# 2. 복원 실행
./import_vectordb.sh ./vectordb_backups/ddoksori_vectordb_20260106_153000.sql.gz

# 3. 확인
python check_embedding_status.py
```

### 방법 2: Docker 컨테이너 공유

**장점**:
- 환경 일관성 보장
- 설정 불일치 방지

```bash
# 1. 현재 DB를 Docker 볼륨으로 백업
docker exec ddoksori_postgres pg_dump -U postgres ddoksori > ddoksori_backup.sql

# 2. Docker 이미지 생성
docker commit ddoksori_postgres ddoksori_vectordb:v1.0

# 3. 이미지 저장
docker save ddoksori_vectordb:v1.0 | gzip > ddoksori_vectordb_v1.0.tar.gz

# 4. 팀원이 로드
docker load < ddoksori_vectordb_v1.0.tar.gz
docker run -d --name ddoksori_postgres -p 5432:5432 ddoksori_vectordb:v1.0
```

### 방법 3: 원격 DB 접근 (개발 환경)

**장점**:
- 실시간 동기화
- 중앙 집중식 관리

**설정**:

```bash
# SSH 터널링으로 원격 DB 접근
ssh -L 5432:localhost:5432 user@remote-server

# .env 파일 설정
DB_HOST=localhost  # 로컬 터널
DB_PORT=5432
DB_NAME=ddoksori
DB_USER=postgres
DB_PASSWORD=your_password
```

---

## Vector DB 확인 방법

### 도구 1: `inspect_vectordb.py` (권장 ⭐)

**기본 검사**:
```bash
cd /home/maroco/ddoksori_demo
conda run -n ddoksori python backend/scripts/inspect_vectordb.py
```

**출력 예시**:
```
================================================================================
📊 Vector DB 개요
================================================================================

📄 문서 및 청크 통계:
  총 문서:           11,976개
  총 청크:           20,269개
  임베딩된 청크:     20,269개
  임베딩 완료율:     100.00%

📏 청크 길이 통계:
  평균:             457자
  최소:             2자
  최대:             1,608자

🔢 벡터 정보:
  차원:             1024
  모델:             KURE-v1 (Korean Universal Representation)

================================================================================
📈 데이터 분포 통계
================================================================================

📁 문서 유형별 분포:
문서 유형                             문서 수         청크 수          임베딩
--------------------------------------------------------------------------------
counsel_case                    11,342       13,524       13,524
mediation_case                     632        5,547        5,547
criteria_resolution                  1          139          139
law                                  1        1,059        1,059

💾 저장소 정보:
  documents:        29 MB
  chunks:           444 MB
  전체 DB:          481 MB
```

**품질 상세 분석**:
```bash
python backend/scripts/inspect_vectordb.py --check-quality
```

**샘플 데이터 추출**:
```bash
python backend/scripts/inspect_vectordb.py --export-samples
# 출력: ./vectordb_samples/vectordb_samples_20260106_153000.json
```

### 도구 2: `check_embedding_status.py`

간단한 통계 확인:
```bash
python backend/scripts/check_embedding_status.py
```

### 도구 3: SQL 직접 쿼리

```sql
-- 1. 기본 통계
SELECT 
    COUNT(DISTINCT doc_id) as total_docs,
    COUNT(*) as total_chunks,
    COUNT(embedding) as embedded_chunks,
    COUNT(embedding)::float / COUNT(*) * 100 as embed_rate
FROM chunks;

-- 2. 청크 타입별 분포
SELECT 
    chunk_type,
    COUNT(*) as count,
    AVG(content_length) as avg_length
FROM chunks
WHERE drop = FALSE
GROUP BY chunk_type
ORDER BY count DESC;

-- 3. 유사도 검색 테스트
SELECT 
    chunk_id,
    content,
    1 - (embedding <=> '[0.1, 0.2, ...]'::vector) as similarity
FROM chunks
WHERE embedding IS NOT NULL
ORDER BY embedding <=> '[0.1, 0.2, ...]'::vector
LIMIT 5;

-- 4. 저장소 크기
SELECT 
    pg_size_pretty(pg_total_relation_size('documents')) as documents_size,
    pg_size_pretty(pg_total_relation_size('chunks')) as chunks_size,
    pg_size_pretty(pg_database_size(current_database())) as total_db_size;
```

### 도구 4: pgAdmin / DBeaver

GUI 도구로 시각적 확인:
1. pgAdmin 설치: https://www.pgadmin.org/
2. 연결 정보:
   - Host: localhost
   - Port: 5432
   - Database: ddoksori
   - Username: postgres

---

## 백업 및 복원

### 정기 백업 전략

**권장 스케줄**:
- **일일 백업**: 개발 단계
- **주간 백업**: 프로덕션 안정화
- **릴리스 전 백업**: 필수!

**자동화 스크립트**:

```bash
# crontab 설정
# 매일 새벽 3시에 백업
0 3 * * * /home/maroco/ddoksori_demo/backend/scripts/export_vectordb.sh

# 7일 이상 된 백업 자동 삭제
0 4 * * * find /home/maroco/ddoksori_demo/backend/scripts/vectordb_backups -name "*.sql.gz" -mtime +7 -delete
```

### 백업 크기 최적화

```bash
# 1. 임베딩 제외 백업 (훨씬 작음, 재생성 필요)
pg_dump -U postgres ddoksori \
  --exclude-table-data=chunks \
  -f ddoksori_schema_only.sql

# 2. 특정 테이블만 백업
pg_dump -U postgres ddoksori \
  -t documents \
  -f ddoksori_documents_only.sql
```

---

## 품질 관리

### 임베딩 품질 체크리스트

✅ **정상 지표**:
- Norm 평균: 0.8 ~ 1.2
- Variance: > 0.001
- NaN/Inf: 0개

⚠️ **경고 신호**:
- Norm < 0.1: 의미 없는 벡터
- Variance < 0.001: 모든 값이 유사 (저품질)
- 희소 벡터 > 90%: 대부분 0에 가까움

**품질 분석 실행**:
```bash
python backend/scripts/inspect_vectordb.py --check-quality
```

### 검색 품질 테스트

```bash
# RAG 검색 품질 테스트
python backend/scripts/test_search_quality.py

# 간단한 검색 테스트
python backend/scripts/test_rag_simple.py
```

---

## 트러블슈팅

### 문제 1: 임베딩 중단

**증상**: 임베딩이 50% 정도에서 멈춤

**해결**:
```bash
# 1. 현재 상태 확인
python backend/scripts/check_embedding_status.py

# 2. 데이터베이스 정리
python backend/scripts/database/clear_database.py --force

# 3. 재시작
python backend/scripts/embedding/embed_data_remote.py
```

### 문제 2: 검색 결과 없음

**원인**: 임베딩 미완료 또는 인덱스 누락

**해결**:
```sql
-- 1. 임베딩 상태 확인
SELECT COUNT(*) FROM chunks WHERE embedding IS NULL;

-- 2. 인덱스 재생성
DROP INDEX IF EXISTS idx_chunks_embedding;
CREATE INDEX idx_chunks_embedding 
ON chunks USING hnsw (embedding vector_cosine_ops);
```

### 문제 3: 메모리 부족

**증상**: PostgreSQL OOM 에러

**해결**:
```bash
# docker-compose.yml 수정
services:
  postgres:
    environment:
      - POSTGRES_SHARED_BUFFERS=2GB    # 기본 128MB → 2GB
      - POSTGRES_WORK_MEM=256MB        # 기본 4MB → 256MB
```

### 문제 4: 느린 검색

**원인**: 인덱스 미생성 또는 부적절한 설정

**해결**:
```sql
-- HNSW 인덱스 최적화
CREATE INDEX idx_chunks_embedding 
ON chunks USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- ANALYZE 실행
ANALYZE chunks;
```

---

## 📚 추가 리소스

### 공식 문서
- pgvector: https://github.com/pgvector/pgvector
- KURE-v1: https://huggingface.co/nlpai-lab/KURE-v1
- PostgreSQL: https://www.postgresql.org/docs/

### 팀 내부 문서
- [데이터 변환 가이드](./데이터_변환_및_테스트_가이드.md)
- [청킹 및 임베딩 가이드](./청킹_및_임베딩_결과_확인_가이드.md)
- [스키마 설계 문서](./통합_스키마_설계_근거.md)

---

## 🎯 Quick Reference

```bash
# Vector DB 상태 확인
python backend/scripts/inspect_vectordb.py

# 임베딩 상태 확인
python backend/scripts/check_embedding_status.py

# 백업 생성
./backend/scripts/export_vectordb.sh

# 복원
./backend/scripts/import_vectordb.sh <backup_file>

# 품질 분석
python backend/scripts/inspect_vectordb.py --check-quality

# 샘플 추출
python backend/scripts/inspect_vectordb.py --export-samples

# 검색 테스트
python backend/scripts/test_search_quality.py
```

---

**업데이트**: 2026-01-06
