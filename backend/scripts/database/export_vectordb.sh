#!/bin/bash
# Vector DB 백업 및 공유용 덤프 생성 스크립트

set -e

# 환경 변수 로드
# 프로젝트 루트의 .env 또는 backend/.env 파일 로드
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

if [ -f "$PROJECT_ROOT/backend/.env" ]; then
    source "$PROJECT_ROOT/backend/.env" 2>/dev/null || true
elif [ -f "$PROJECT_ROOT/.env" ]; then
    source "$PROJECT_ROOT/.env" 2>/dev/null || true
fi

DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-ddoksori}"
DB_USER="${DB_USER:-postgres}"

# 백업 디렉토리 생성 (스크립트 위치 기준)
BACKUP_DIR="$SCRIPT_DIR/vectordb_backups"
mkdir -p "$BACKUP_DIR"

# 타임스탬프
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DUMP_FILE="$BACKUP_DIR/ddoksori_vectordb_${TIMESTAMP}.sql"
COMPRESSED_FILE="${DUMP_FILE}.gz"

echo "================================================================================"
echo "Vector DB 백업 생성"
echo "================================================================================"
echo "데이터베이스: $DB_NAME"
echo "호스트: $DB_HOST:$DB_PORT"
echo "출력 파일: $DUMP_FILE"
echo ""

# 1. 전체 데이터베이스 덤프 (스키마 + 데이터)
echo "📦 데이터베이스 덤프 생성 중..."

# Docker 컨테이너 내부에서 pg_dump 실행 (로컬에 pg_dump가 없는 경우 대비)
if command -v pg_dump >/dev/null 2>&1; then
    # 로컬에 pg_dump가 있는 경우
    PGPASSWORD="$DB_PASSWORD" pg_dump \
      -h "$DB_HOST" \
      -p "$DB_PORT" \
      -U "$DB_USER" \
      -d "$DB_NAME" \
      --no-owner \
      --no-acl \
      -F p \
      -f "$DUMP_FILE"
else
    # Docker 컨테이너 내부에서 실행
    CONTAINER_NAME="ddoksori_db"
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        docker exec "$CONTAINER_NAME" pg_dump \
          -U "$DB_USER" \
          -d "$DB_NAME" \
          --no-owner \
          --no-acl \
          -F p > "$DUMP_FILE"
    else
        echo "❌ 오류: Docker 컨테이너 '$CONTAINER_NAME'가 실행 중이지 않습니다."
        echo "   docker-compose up -d db 를 먼저 실행하세요."
        exit 1
    fi
fi

echo "✅ 덤프 완료: $DUMP_FILE"

# 2. 압축
echo ""
echo "🗜️  압축 중..."
gzip -9 "$DUMP_FILE"
echo "✅ 압축 완료: $COMPRESSED_FILE"

# 3. 파일 정보
FILE_SIZE=$(du -h "$COMPRESSED_FILE" | cut -f1)
echo ""
echo "================================================================================"
echo "✅ 백업 완료!"
echo "================================================================================"
echo "파일: $COMPRESSED_FILE"
echo "크기: $FILE_SIZE"
echo ""
echo "📤 팀원과 공유 방법:"
echo "  1. 클라우드 스토리지 (Google Drive, Dropbox 등)"
echo "  2. 내부 파일 서버"
echo "  3. Git LFS (50MB 이하인 경우)"
echo ""
echo "📥 팀원이 복원하는 방법:"
echo "  gunzip $COMPRESSED_FILE"
echo "  PGPASSWORD=\$DB_PASSWORD psql -h localhost -U postgres -d ddoksori < $DUMP_FILE"
echo "================================================================================"

# 4. 메타데이터 저장
echo ""
echo "📝 메타데이터 생성 중..."
cat > "$BACKUP_DIR/ddoksori_vectordb_${TIMESTAMP}_metadata.json" << EOF
{
  "backup_timestamp": "$TIMESTAMP",
  "database_name": "$DB_NAME",
  "host": "$DB_HOST",
  "port": "$DB_PORT",
  "compressed_file": "$(basename $COMPRESSED_FILE)",
  "file_size": "$FILE_SIZE",
  "created_by": "$(whoami)",
  "backup_date": "$(date -Iseconds)",
  "instructions": {
    "decompress": "gunzip $(basename $COMPRESSED_FILE)",
    "restore": "PGPASSWORD=\\\$DB_PASSWORD psql -h localhost -U postgres -d ddoksori < $(basename $DUMP_FILE)"
  }
}
EOF

echo "✅ 메타데이터 저장: $BACKUP_DIR/ddoksori_vectordb_${TIMESTAMP}_metadata.json"
