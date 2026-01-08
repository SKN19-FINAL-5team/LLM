# pgvector 팀원 공유 가이드

**작성일**: 2026-01-06  
**목적**: Docker로 생성한 pgvector 데이터베이스를 팀원들과 공유하는 방법

---

## 📋 목차

1. [개요](#개요)
2. [공유자(생성자) 가이드](#공유자생성자-가이드)
3. [수신자(팀원) 가이드](#수신자팀원-가이드)
4. [Docker 기반 공유 방법](#docker-기반-공유-방법)
5. [검증 및 트러블슈팅](#검증-및-트러블슈팅)
6. [참고 문서](#참고-문서)

---

## 개요

### 공유 방법 비교

| 방법 | 장점 | 단점 | 권장 상황 |
|------|------|------|----------|
| **데이터베이스 덤프** | 완전한 복제, 버전 관리 가능 | 파일 크기 큼 (100-500MB) | ⭐ 권장 - 가장 안정적 |
| **Docker 볼륨 공유** | 환경 일관성 보장 | Docker 이미지 크기 큼 | 개발 환경 동기화 |
| **원격 DB 접근** | 실시간 동기화 | 네트워크 의존성 | 공동 개발 시 |

### 공유 프로세스 개요

```mermaid
flowchart LR
    A[공유자] -->|1. 백업 생성| B[덤프 파일]
    B -->|2. 압축| C[.sql.gz 파일]
    C -->|3. 공유| D[클라우드/서버]
    D -->|4. 다운로드| E[수신자]
    E -->|5. 복원| F[로컬 DB]
    F -->|6. 검증| G[완료]
    
    style A fill:#e1f5ff
    style E fill:#fff3e0
    style G fill:#c8e6c9
```

---

## 공유자(생성자) 가이드

### Step 1: 데이터베이스 상태 확인

```bash
# ⚠️ 중요: 프로젝트 루트 디렉토리에서 실행
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# Docker 컨테이너 실행 확인
docker ps | grep ddoksori_db

# 데이터베이스 통계 확인 (SQL로 직접 확인)
docker exec ddoksori_db psql -U postgres -d ddoksori -c "
SELECT 
    COUNT(DISTINCT doc_id) as total_docs,
    COUNT(*) as total_chunks,
    COUNT(embedding) as embedded_chunks,
    CASE 
        WHEN COUNT(*) > 0 THEN COUNT(embedding)::float / COUNT(*) * 100 
        ELSE 0 
    END as embed_rate
FROM chunks;
"
```

**확인 사항**:
- [ ] Docker 컨테이너가 실행 중인지 확인
- [ ] 데이터가 정상적으로 로드되어 있는지 확인
- [ ] 임베딩이 완료되었는지 확인 (100% 권장)

### Step 2: 백업 스크립트 위치 확인

```bash
# ⚠️ 중요: 프로젝트 루트 디렉토리에서 실행
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# 백업 스크립트 위치 확인
ls -lh backend/scripts/database/export_vectordb.sh

# 실행 권한 부여
chmod +x backend/scripts/database/export_vectordb.sh
```

### Step 3: 백업 생성

```bash
# ⚠️ 중요: 프로젝트 루트 디렉토리에서 실행
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# Docker 컨테이너가 실행 중인지 확인
docker ps | grep ddoksori_db

# 백업 스크립트 실행 (상대 경로 또는 절대 경로 사용)
./backend/scripts/database/export_vectordb.sh

# 또는 백업 디렉토리로 이동 후 실행
cd backend/scripts/database
./export_vectordb.sh
```

**참고**: 
- 스크립트는 로컬에 `pg_dump`가 없으면 자동으로 Docker 컨테이너 내부에서 실행합니다.
- `pg_dump: command not found` 오류가 발생하면 Docker 컨테이너가 실행 중인지 확인하세요.

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
```

### Step 4: 백업 파일 검증

```bash
# ⚠️ 중요: 프로젝트 루트 디렉토리에서 실행
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# 백업 파일 확인 (디렉토리가 없을 수 있음)
ls -lh backend/scripts/database/vectordb_backups/ 2>/dev/null || echo "백업 디렉토리가 없습니다. 백업을 먼저 생성하세요."

# 파일 무결성 확인 (압축 해제 테스트)
find backend/scripts/database/vectordb_backups -name "*.sql.gz" -type f -exec gunzip -t {} \; 2>&1
```

**참고**: 
- 백업 파일이 없으면 `ls` 명령어는 `total 0`만 출력하고, `find` 명령어는 아무것도 출력하지 않습니다. 이는 정상입니다.
- 백업 파일이 있는 경우에만 검증 결과가 표시됩니다.
- 백업 파일 목록 확인:
  ```bash
  find backend/scripts/database/vectordb_backups -name "*.sql.gz" -type f
  ```

### Step 5: 메타데이터 확인

백업과 함께 생성된 메타데이터 파일 확인:

```bash
# ⚠️ 중요: 프로젝트 루트 디렉토리에서 실행
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# 메타데이터 파일 확인
find backend/scripts/database/vectordb_backups -name "*_metadata.json" -type f -exec cat {} \;
```

**참고**: 
- 백업 파일이 없으면 아무것도 출력되지 않습니다. 이는 정상입니다.
- 백업 파일이 있는 경우에만 메타데이터가 표시됩니다.
- 백업 파일 목록 확인:
  ```bash
  ls -lh backend/scripts/database/vectordb_backups/
  ```

**메타데이터 예시**:
```json
{
  "backup_timestamp": "20260106_153000",
  "database_name": "ddoksori",
  "host": "localhost",
  "port": "5432",
  "compressed_file": "ddoksori_vectordb_20260106_153000.sql.gz",
  "file_size": "145M",
  "created_by": "user",
  "backup_date": "2026-01-06T15:30:00+09:00"
}
```

### Step 6: 공유 방법 선택

#### 방법 1: 클라우드 스토리지 (권장)

**Google Drive / Dropbox / OneDrive**:
1. 백업 파일을 클라우드에 업로드
2. 공유 링크 생성
3. 팀원에게 링크 공유

**주의사항**:
- 파일 크기가 100MB 이상인 경우 Google Drive는 다운로드 제한이 있을 수 있음
- 대용량 파일은 Google Drive 데스크톱 앱 사용 권장

#### 방법 2: 내부 파일 서버

```bash
# ⚠️ 중요: 프로젝트 루트 디렉토리에서 실행
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# SCP로 서버에 업로드
find backend/scripts/database/vectordb_backups -name "*.sql.gz" -type f -exec scp {} user@server:/shared/vectordb/ \;

# 또는 rsync 사용 (특정 파일 지정)
rsync -avz backend/scripts/database/vectordb_backups/ddoksori_vectordb_*.sql.gz \
    user@server:/shared/vectordb/ 2>/dev/null || \
    find backend/scripts/database/vectordb_backups -name "*.sql.gz" -type f -exec rsync -avz {} user@server:/shared/vectordb/ \;
```

#### 방법 3: Git LFS (50MB 이하인 경우)

```bash
# ⚠️ 중요: 프로젝트 루트 디렉토리에서 실행
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# Git LFS 초기화 (최초 1회)
git lfs install

# .gitattributes 파일 생성
echo "*.sql.gz filter=lfs diff=lfs merge=lfs -text" >> .gitattributes

# 파일 추가 및 커밋 (파일이 있는 경우에만)
find backend/scripts/database/vectordb_backups -name "*.sql.gz" -type f -exec git add {} \;
git commit -m "Add vectordb backup"
git push
```

**주의**: Git LFS는 대용량 파일에 적합하지 않으므로 50MB 이하인 경우에만 권장

### Step 7: 공유 정보 전달

팀원에게 다음 정보를 전달:

1. **백업 파일 다운로드 링크 또는 위치**
2. **백업 파일명** (예: `ddoksori_vectordb_20260106_153000.sql.gz`)
3. **파일 크기** (다운로드 시간 예상)
4. **복원 가이드 링크** (이 문서의 수신자 가이드 섹션)
5. **데이터베이스 버전 정보** (선택사항)

**예시 메시지**:
```
안녕하세요,

pgvector 데이터베이스 백업 파일을 공유합니다.

📦 파일 정보:
- 파일명: ddoksori_vectordb_20260106_153000.sql.gz
- 크기: 145MB
- 다운로드: [링크 또는 위치]

📥 복원 방법:
아래 가이드를 참고하여 복원해주세요:
[링크] docs/guides/pgvector_sharing_guide.md#수신자팀원-가이드

문의사항이 있으시면 알려주세요!
```

---

## 수신자(팀원) 가이드

### Step 1: 사전 준비

#### 1.1 Docker 환경 확인

```bash
# Docker 설치 확인
docker --version
docker-compose --version

# 프로젝트 클론 (아직 없는 경우)
git clone <repository-url>
cd <프로젝트-디렉토리명>

# ⚠️ 중요: 프로젝트 루트 디렉토리 확인
pwd  # 프로젝트 루트 디렉토리여야 함
```

#### 1.2 PostgreSQL 컨테이너 실행

```bash
# Docker Compose로 PostgreSQL 컨테이너 실행
docker-compose up -d db

# 컨테이너 상태 확인
docker ps | grep ddoksori_db

# 데이터베이스 연결 테스트 (스크립트 실행 시 -it 옵션 제거)
docker exec ddoksori_db psql -U postgres -d ddoksori -c "SELECT version();"
```

#### 1.3 환경 변수 설정

```bash
# ⚠️ 중요: 프로젝트 루트 디렉토리에서 실행
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# backend/.env 파일 생성
cat > backend/.env << EOF
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ddoksori
DB_USER=postgres
DB_PASSWORD=postgres
EOF
```

### Step 2: 백업 파일 다운로드

#### 방법 1: 클라우드 스토리지에서 다운로드

```bash
# ⚠️ 중요: 프로젝트 루트 디렉토리에서 실행
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# 다운로드 디렉토리 생성
mkdir -p backend/scripts/database/vectordb_backups

# Google Drive 등에서 다운로드 후 이동
mv ~/Downloads/ddoksori_vectordb_*.sql.gz \
   backend/scripts/database/vectordb_backups/ 2>/dev/null || \
   find ~/Downloads -name "ddoksori_vectordb_*.sql.gz" -type f -exec mv {} backend/scripts/database/vectordb_backups/ \;

#### 방법 2: SCP로 다운로드

```bash
# ⚠️ 중요: 프로젝트 루트 디렉토리에서 실행
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# 다운로드 디렉토리 생성
mkdir -p backend/scripts/database/vectordb_backups

# 서버에서 다운로드
scp user@server:/shared/vectordb/ddoksori_vectordb_*.sql.gz \
    backend/scripts/database/vectordb_backups/ 2>/dev/null || \
    echo "파일을 찾을 수 없습니다. 서버 경로를 확인하세요."
```

### Step 3: 백업 파일 검증

```bash
# ⚠️ 중요: 프로젝트 루트 디렉토리에서 실행
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# 파일 존재 확인 (zsh에서는 glob 패턴 문제 가능)
find backend/scripts/database/vectordb_backups -name "*.sql.gz" -type f -ls

# 또는 ls 사용 (파일이 있는 경우)
ls -lh backend/scripts/database/vectordb_backups/*.sql.gz 2>/dev/null || echo "백업 파일이 없습니다."

# 압축 파일 무결성 확인
find backend/scripts/database/vectordb_backups -name "*.sql.gz" -type f -exec gunzip -t {} \;

# 파일 크기 확인 (공유자와 일치하는지)
find backend/scripts/database/vectordb_backups -name "*.sql.gz" -type f -exec du -h {} \;
```

### Step 4: 복원 스크립트 준비

```bash
# 복원 스크립트 위치 확인
ls -lh backend/scripts/database/import_vectordb.sh

# 실행 권한 부여
chmod +x backend/scripts/database/import_vectordb.sh
```

### Step 5: 데이터베이스 복원

**⚠️ 주의**: 복원 시 기존 데이터가 모두 삭제됩니다!

```bash
# ⚠️ 중요: 프로젝트 루트 디렉토리에서 실행
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# Docker 컨테이너가 실행 중인지 확인
docker ps | grep ddoksori_db

# 복원 스크립트 실행 (상대 경로 또는 절대 경로 사용)
./backend/scripts/database/import_vectordb.sh \
    backend/scripts/database/vectordb_backups/ddoksori_vectordb_20260106_153000.sql.gz

# 또는 복원 디렉토리로 이동 후 실행
cd backend/scripts/database
./import_vectordb.sh vectordb_backups/ddoksori_vectordb_20260106_153000.sql.gz
```

**참고**: 
- 스크립트는 로컬에 `psql`이 없으면 자동으로 Docker 컨테이너 내부에서 실행합니다.
- `psql: command not found` 오류가 발생하면 Docker 컨테이너가 실행 중인지 확인하세요.

**프롬프트 예시**:
```
================================================================================
Vector DB 복원
================================================================================
소스 파일: vectordb_backups/ddoksori_vectordb_20260106_153000.sql.gz
데이터베이스: ddoksori
호스트: localhost:5432

⚠️  주의: 기존 데이터가 모두 삭제됩니다!
계속하시겠습니까? (yes/no): yes

📦 압축 해제 중...
✅ 압축 해제 완료: vectordb_backups/ddoksori_vectordb_20260106_153000.sql

🗑️  기존 데이터 삭제 중...
✅ 기존 데이터 삭제 완료

📥 데이터베이스 복원 중...
✅ 복원 완료!

🔍 복원 검증 중...
================================================================================
✅ 복원 완료 및 검증
================================================================================
문서 수: 11976
청크 수: 20269
임베딩된 청크: 20269
================================================================================
```

### Step 6: 복원 검증

#### 6.1 기본 통계 확인

```bash
# ⚠️ 중요: 프로젝트 루트 디렉토리에서 실행
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# 임베딩 상태 확인 (SQL로 직접 확인)
# ⚠️ 주의: chunks 테이블이 없는 경우 오류 발생 (스키마 생성 후 실행)
docker exec ddoksori_db psql -U postgres -d ddoksori -c "
SELECT 
    COUNT(DISTINCT doc_id) as total_docs,
    COUNT(*) as total_chunks,
    COUNT(embedding) as embedded_chunks,
    CASE 
        WHEN COUNT(*) > 0 THEN COUNT(embedding)::float / COUNT(*) * 100 
        ELSE 0 
    END as embed_rate
FROM chunks;
" 2>&1 || echo "⚠️ chunks 테이블이 없습니다. 스키마를 먼저 생성하세요."
```

#### 6.2 SQL로 직접 확인

```bash
# ⚠️ 중요: 프로젝트 루트 디렉토리에서 실행
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# 방법 1: docker exec로 직접 SQL 실행 (권장)
# ⚠️ 주의: chunks 테이블이 없는 경우 오류 발생 (스키마 생성 후 실행)
docker exec ddoksori_db psql -U postgres -d ddoksori -c "
SELECT 
    COUNT(DISTINCT doc_id) as total_docs,
    COUNT(*) as total_chunks,
    COUNT(embedding) as embedded_chunks,
    CASE 
        WHEN COUNT(*) > 0 THEN COUNT(embedding)::float / COUNT(*) * 100 
        ELSE 0 
    END as embed_rate
FROM chunks;
" 2>&1 || echo "⚠️ chunks 테이블이 없습니다. 스키마를 먼저 생성하세요."

# 방법 2: 대화형 psql 접속 (대화형 터미널에서만 사용)
# docker exec -it ddoksori_db psql -U postgres -d ddoksori
# psql 프롬프트에서 위 SQL 쿼리 실행 후 \q로 종료
```

#### 6.3 벡터 검색 테스트

```bash
# ⚠️ 중요: 프로젝트 루트 디렉토리에서 실행
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# 간단한 검색 테스트 스크립트 실행
conda run -n dsr python -c "
import sys
sys.path.insert(0, 'backend')
from app.rag import VectorRetriever

db_config = {
    'host': 'localhost',
    'port': 5432,
    'database': 'ddoksori',
    'user': 'postgres',
    'password': 'postgres'
}

retriever = VectorRetriever(db_config)
results = retriever.search('환불 관련 문의', top_k=3)
print(f'✅ 검색 테스트 성공: {len(results)}개 결과')
retriever.close()
"
```

### Step 7: RAG 시스템 테스트

```bash
# ⚠️ 중요: 프로젝트 루트 디렉토리에서 실행
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# 멀티 스테이지 RAG 테스트 실행
conda run -n dsr python test/rag/test_multi_stage_rag.py --test-id TC001
```

---

## Docker 기반 공유 방법

### 방법 1: Docker 이미지로 공유

#### 공유자 작업

```bash
# ⚠️ 중요: 프로젝트 루트 디렉토리에서 실행
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# 1. 현재 DB 컨테이너를 이미지로 커밋
docker commit ddoksori_db ddoksori_vectordb:v1.0

# 2. 이미지를 tar 파일로 저장
docker save ddoksori_vectordb:v1.0 | gzip > ddoksori_vectordb_v1.0.tar.gz

# 3. 파일 공유 (클라우드 스토리지 등)
```

#### 수신자 작업

```bash
# ⚠️ 중요: 프로젝트 루트 디렉토리에서 실행
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# 1. 이미지 로드
docker load < ddoksori_vectordb_v1.0.tar.gz

# 2. 기존 컨테이너 중지 및 제거
docker-compose down db
docker rm ddoksori_db 2>/dev/null || true

# 3. 새 컨테이너 실행
docker run -d \
  --name ddoksori_db \
  -p 5432:5432 \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=ddoksori \
  ddoksori_vectordb:v1.0

# 4. 검증
docker exec ddoksori_db psql -U postgres -d ddoksori -c "SELECT COUNT(*) FROM chunks;"
```

### 방법 2: Docker 볼륨 공유

#### 공유자 작업

```bash
# ⚠️ 중요: 프로젝트 루트 디렉토리에서 실행
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# 1. 볼륨 백업
docker run --rm \
  -v ddoksori_postgres_data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/postgres_data_backup.tar.gz -C /data .

# 2. 백업 파일 공유
```

#### 수신자 작업

```bash
# ⚠️ 중요: 프로젝트 루트 디렉토리에서 실행
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# 1. 볼륨 복원
docker run --rm \
  -v ddoksori_postgres_data:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/postgres_data_backup.tar.gz -C /data

# 2. 컨테이너 재시작
docker-compose restart db
```

---

## 검증 및 트러블슈팅

### 검증 체크리스트

복원 후 다음 항목을 확인하세요:

- [ ] Docker 컨테이너가 정상 실행 중
- [ ] 데이터베이스 연결 성공
- [ ] 문서 수가 예상과 일치
- [ ] 청크 수가 예상과 일치
- [ ] 임베딩 완료율 100%
- [ ] 벡터 검색 테스트 성공
- [ ] RAG 시스템 테스트 성공

### 일반적인 문제 해결

#### 문제 1: 복원 중 오류

**증상**: `ERROR: relation "documents" already exists`

**해결**:
```bash
# ⚠️ 중요: 프로젝트 루트 디렉토리에서 실행
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# 기존 스키마 완전 삭제 후 재시도
docker exec ddoksori_db psql -U postgres -d ddoksori \
  -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

# pgvector 확장 재생성
docker exec ddoksori_db psql -U postgres -d ddoksori \
  -c "CREATE EXTENSION IF NOT EXISTS vector;"

# 복원 재시도
find backend/scripts/database/vectordb_backups -name "*.sql.gz" -type f | head -1 | \
  xargs -I {} ./backend/scripts/database/import_vectordb.sh {}
```

#### 문제 2: `pg_dump: command not found` 또는 `psql: command not found`

**증상**: 백업 또는 복원 스크립트 실행 시 `pg_dump: command not found` 또는 `psql: command not found` 오류 발생

**원인**: 로컬 시스템에 PostgreSQL 클라이언트 도구가 설치되어 있지 않음

**해결**:

1. **자동 해결 (권장)**: 
   - 최신 버전의 스크립트는 자동으로 Docker 컨테이너 내부에서 실행합니다.
   - Docker 컨테이너가 실행 중인지 확인:
   ```bash
   docker ps | grep ddoksori_db
   ```
   - 컨테이너가 실행 중이면 스크립트가 자동으로 Docker 내부에서 실행됩니다.

2. **수동 해결 (선택사항)**:
   - 로컬에 PostgreSQL 클라이언트 설치:
   ```bash
   # Ubuntu/Debian
   sudo apt-get update
   sudo apt-get install postgresql-client
   
   # macOS (Homebrew)
   brew install postgresql
   ```

**참고**: 
- 스크립트는 로컬에 `pg_dump`/`psql`이 없으면 자동으로 Docker 컨테이너 내부에서 실행합니다.
- Docker 컨테이너가 실행 중이지 않으면 오류가 발생하므로, 먼저 `docker-compose up -d db`를 실행하세요.

#### 문제 3: 권한 오류

**증상**: `Permission denied: ./export_vectordb.sh`

**해결**:
```bash
chmod +x backend/scripts/database/export_vectordb.sh
chmod +x backend/scripts/database/import_vectordb.sh
```

#### 문제 4: 압축 파일 손상

**증상**: `gunzip: corrupt input`

**해결**:
- 백업 파일을 다시 다운로드
- 다운로드 중 네트워크 오류가 있었는지 확인
- 파일 크기가 원본과 일치하는지 확인

#### 문제 5: 디스크 공간 부족

**증상**: `No space left on device`

**해결**:
```bash
# 디스크 공간 확인
df -h

# 불필요한 Docker 리소스 정리
docker system prune -a

# 압축 해제 전 충분한 공간 확보 (최소 백업 파일 크기의 2배)
```

#### 문제 6: pgvector 확장 누락

**증상**: `ERROR: type "vector" does not exist`

**해결**:
```bash
# ⚠️ 중요: 프로젝트 루트 디렉토리에서 실행
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# pgvector 확장 활성화
docker exec ddoksori_db psql -U postgres -d ddoksori \
  -c "CREATE EXTENSION IF NOT EXISTS vector;"

# 확인
docker exec ddoksori_db psql -U postgres -d ddoksori \
  -c "SELECT * FROM pg_extension WHERE extname = 'vector';"
```

---

## 참고 문서

### 관련 가이드
- [임베딩 프로세스 가이드](./embedding_process_guide.md) - 스키마 생성 및 임베딩 가이드
- [Vector DB 관리 가이드](./Vector_DB_관리_가이드.md) - 백업 및 관리 상세 가이드

### 스크립트 파일
- `backend/scripts/database/export_vectordb.sh` - 백업 생성 스크립트
- `backend/scripts/database/import_vectordb.sh` - 복원 스크립트
- SQL 쿼리로 직접 상태 확인 (위 Step 1 참조)

### 설정 파일
- `docker-compose.yml` - Docker Compose 설정
- `backend/.env` - 환경 변수 설정

---

## 요약

### 공유자 체크리스트

- [ ] 데이터베이스 상태 확인 완료
- [ ] 백업 스크립트 실행 권한 확인
- [ ] 백업 생성 완료
- [ ] 백업 파일 검증 완료
- [ ] 공유 방법 선택 및 파일 업로드
- [ ] 팀원에게 공유 정보 전달

### 수신자 체크리스트

- [ ] Docker 환경 준비 완료
- [ ] PostgreSQL 컨테이너 실행 확인
- [ ] 백업 파일 다운로드 완료
- [ ] 백업 파일 검증 완료
- [ ] 데이터베이스 복원 완료
- [ ] 복원 검증 완료
- [ ] RAG 시스템 테스트 성공

---

**업데이트**: 2026-01-06
