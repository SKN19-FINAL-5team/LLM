# 데이터베이스 오류 분석 및 검증 보고서

**작성일**: 2026-01-09  
**분석 대상**: 멀티 스테이지 RAG 테스트 오류

---

## 1. 오류 원인 분석

### 발견된 문제

#### 1.1 첫 번째 테스트 오류
```
relation "chunks" does not exist
LINE 13:             FROM chunks c
```

**원인**: 데이터베이스에 `chunks` 테이블이 존재하지 않음

#### 1.2 후속 테스트 오류
```
current transaction is aborted, commands ignored until end of transaction block
```

**원인**: 첫 번째 오류로 인해 PostgreSQL 트랜잭션이 실패 상태로 남아있어 추가 명령 실행 불가

### 근본 원인

1. **데이터베이스 스키마 미생성**: `documents`와 `chunks` 테이블이 존재하지 않음
2. **백업 파일 문제**: 백업 파일이 스키마와 데이터를 포함하지 않음 (616 bytes, pgvector 확장만 포함)
3. **초기화 누락**: Docker 컨테이너는 실행 중이지만 데이터베이스가 초기화되지 않음

---

## 2. 현재 상태 확인 결과

### Docker 컨테이너 상태
- ✅ 컨테이너 실행 중: `ddoksori_db` (Up 54 minutes, healthy)
- ✅ 포트 매핑: `0.0.0.0:5432->5432/tcp`

### 데이터베이스 스키마 상태
- ❌ `documents` 테이블: 존재하지 않음
- ❌ `chunks` 테이블: 존재하지 않음
- ✅ `pgvector` 확장: 설치됨 (버전 0.8.1)

### 데이터베이스 데이터 상태
- ❌ `documents` 테이블 레코드: 테이블 없음으로 조회 불가
- ❌ `chunks` 테이블 레코드: 테이블 없음으로 조회 불가
- ❌ 임베딩된 청크: 테이블 없음으로 조회 불가

### 백업 파일 검증 결과
- **파일 경로**: `backend/scripts/database/vectordb_backups/ddoksori_vectordb_20260108_234218.sql.gz`
- **파일 크기**: 616 bytes (매우 작음)
- **총 라인 수**: 54줄
- **스키마 포함 여부**: ❌ CREATE TABLE 문 없음
- **데이터 포함 여부**: ❌ INSERT INTO 문 없음
- **포함 내용**: pgvector 확장만 포함

**결론**: 이 백업 파일은 빈 데이터베이스에서 생성된 것으로, 스키마와 데이터가 없습니다.

---

## 3. 백업 스크립트 검토 결과

### `export_vectordb.sh` 분석
- **기능**: `pg_dump`를 사용하여 전체 데이터베이스 덤프 생성
- **포함 내용**: 스키마 + 데이터 + 인덱스 (정상 작동 시)
- **문제점**: 
  - 백업 생성 시점에 데이터베이스가 비어있었을 가능성
  - 백업 파일 크기 검증 로직 없음

### `import_vectordb.sh` 분석
- **기능**: 
  1. 압축 해제
  2. 기존 스키마 삭제 (`DROP SCHEMA public CASCADE`)
  3. SQL 덤프 복원
  4. 복원 검증 (documents, chunks 테이블 카운트)
- **문제점**:
  1. 백업 파일에 스키마가 없으면 복원 후에도 테이블이 생성되지 않음
  2. 백업 파일 크기 검증 없음
  3. 스키마 자동 생성 옵션 없음
  4. 오류 발생 시 롤백 처리 없음

---

## 4. 해결 방안

### 시나리오 1: 스키마 생성 및 데이터 로드 (권장)

#### 4.1 스키마 생성
```bash
# 프로젝트 루트에서 실행
cd /home/maroco/LLM

# Docker를 통해 스키마 실행
docker exec -i ddoksori_db psql -U postgres -d ddoksori < backend/database/schema_v2_final.sql
```

#### 4.2 데이터 임베딩 및 로드
```bash
# 임베딩 파이프라인 실행
conda run -n dsr python backend/scripts/embedding/embed_data_remote.py
```

또는 원격 임베딩 API 사용:
```bash
# 임베딩 API 서버 실행 후
conda run -n dsr python backend/scripts/embedding/embed_data_remote.py
```

### 시나리오 2: 백업 파일이 정상인 경우 (현재는 해당 없음)

현재 백업 파일은 빈 데이터베이스에서 생성된 것이므로 사용 불가합니다.

### 시나리오 3: 유효한 백업 파일이 있는 경우

다른 백업 파일을 확인하거나, 새로운 백업을 생성해야 합니다.

---

## 5. 개선 사항 제안

### 5.1 백업 스크립트 개선 (`export_vectordb.sh`)

1. **백업 파일 크기 검증 추가**
   ```bash
   # 최소 크기 검증 (예: 1KB 이상)
   MIN_SIZE=1024
   if [ $(stat -f%z "$COMPRESSED_FILE" 2>/dev/null || stat -c%s "$COMPRESSED_FILE") -lt $MIN_SIZE ]; then
       echo "⚠️  경고: 백업 파일이 너무 작습니다. 데이터베이스가 비어있을 수 있습니다."
   fi
   ```

2. **스키마 포함 여부 확인**
   ```bash
   # CREATE TABLE 문 확인
   if ! gunzip -c "$COMPRESSED_FILE" | grep -q "CREATE TABLE"; then
       echo "⚠️  경고: 백업 파일에 테이블 스키마가 없습니다."
   fi
   ```

3. **데이터 포함 여부 확인**
   ```bash
   # INSERT 문 확인
   if ! gunzip -c "$COMPRESSED_FILE" | grep -q "INSERT INTO"; then
       echo "⚠️  경고: 백업 파일에 데이터가 없습니다."
   fi
   ```

### 5.2 복원 스크립트 개선 (`import_vectordb.sh`)

1. **백업 파일 사전 검증**
   ```bash
   # 파일 크기 확인
   FILE_SIZE=$(stat -f%z "$DUMP_FILE" 2>/dev/null || stat -c%s "$DUMP_FILE")
   if [ "$FILE_SIZE" -lt 1024 ]; then
       echo "❌ 오류: 백업 파일이 너무 작습니다. ($FILE_SIZE bytes)"
       echo "   백업 파일이 손상되었거나 빈 데이터베이스에서 생성되었을 수 있습니다."
       exit 1
   fi
   
   # 스키마 포함 여부 확인
   if ! grep -q "CREATE TABLE" "$SQL_FILE"; then
       echo "⚠️  경고: 백업 파일에 테이블 스키마가 없습니다."
       read -p "스키마를 자동으로 생성하시겠습니까? (yes/no): " CREATE_SCHEMA
       if [ "$CREATE_SCHEMA" == "yes" ]; then
           # schema_v2_final.sql 실행
           docker exec -i "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" < "$PROJECT_ROOT/backend/database/schema_v2_final.sql"
       fi
   fi
   ```

2. **트랜잭션 오류 처리**
   ```bash
   # 복원 시 오류 발생 시 롤백
   set +e  # 오류 발생해도 계속 진행
   # 복원 실행
   set -e  # 다시 오류 시 종료
   ```

3. **복원 후 상세 검증**
   ```bash
   # 테이블 존재 여부 확인
   if ! docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -c "\dt" | grep -q "documents"; then
       echo "❌ 오류: documents 테이블이 생성되지 않았습니다."
       exit 1
   fi
   ```

### 5.3 테스트 코드 개선 (`test_multi_stage_rag.py`)

1. **데이터베이스 연결 전 테이블 존재 여부 확인**
   ```python
   def check_database_schema(self, db_config):
       """데이터베이스 스키마 확인"""
       conn = psycopg2.connect(**db_config)
       cur = conn.cursor()
       
       # 테이블 존재 확인
       cur.execute("""
           SELECT EXISTS (
               SELECT FROM information_schema.tables 
               WHERE table_schema = 'public' 
               AND table_name = 'chunks'
           );
       """)
       chunks_exists = cur.fetchone()[0]
       
       cur.execute("""
           SELECT EXISTS (
               SELECT FROM information_schema.tables 
               WHERE table_schema = 'public' 
               AND table_name = 'documents'
           );
       """)
       documents_exists = cur.fetchone()[0]
       
       cur.close()
       conn.close()
       
       if not chunks_exists or not documents_exists:
           raise RuntimeError(
               "데이터베이스 스키마가 생성되지 않았습니다. "
               "다음 명령어로 스키마를 생성하세요:\n"
               "docker exec -i ddoksori_db psql -U postgres -d ddoksori < backend/database/schema_v2_final.sql"
           )
   ```

2. **트랜잭션 롤백 처리**
   ```python
   # retriever.py의 search 메서드에서
   try:
       with self.conn.cursor() as cur:
           cur.execute(sql, params)
           rows = cur.fetchall()
   except psycopg2.Error as e:
       self.conn.rollback()  # 트랜잭션 롤백
       raise
   ```

---

## 6. 즉시 실행 가능한 해결 방법

### 단계별 실행

1. **스키마 생성**
   ```bash
   cd /home/maroco/LLM
   docker exec -i ddoksori_db psql -U postgres -d ddoksori < backend/database/schema_v2_final.sql
   ```

2. **스키마 생성 확인**
   ```bash
   docker exec ddoksori_db psql -U postgres -d ddoksori -c "\dt"
   ```

3. **데이터 임베딩 및 로드** (원본 데이터가 있는 경우)
   ```bash
   conda run -n dsr python backend/scripts/embedding/embed_data_remote.py
   ```

4. **데이터 확인**
   ```bash
   docker exec ddoksori_db psql -U postgres -d ddoksori -c "SELECT COUNT(*) FROM documents;"
   docker exec ddoksori_db psql -U postgres -d ddoksori -c "SELECT COUNT(*) FROM chunks;"
   ```

5. **테스트 재실행**
   ```bash
   conda run -n dsr python -m tests.rag.test_multi_stage_rag
   ```

---

## 7. 요약

### 문제점
1. 데이터베이스에 `documents`와 `chunks` 테이블이 없음
2. 백업 파일이 빈 데이터베이스에서 생성되어 스키마와 데이터가 없음
3. 복원 스크립트가 백업 파일 검증을 하지 않음

### 해결 방법
1. 스키마 생성 (`schema_v2_final.sql` 실행)
2. 데이터 임베딩 및 로드 (`embed_data_remote.py` 실행)
3. 백업/복원 스크립트 개선 (검증 로직 추가)

### 권장 사항
- 백업 생성 전 데이터베이스 상태 확인
- 복원 전 백업 파일 검증
- 테스트 실행 전 스키마 존재 여부 확인
