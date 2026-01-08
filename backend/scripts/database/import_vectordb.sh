#!/bin/bash
# Vector DB 복원 스크립트

set -e

if [ -z "$1" ]; then
    echo "사용법: $0 <dump_file.sql.gz>"
    echo ""
    echo "예시: $0 ./vectordb_backups/ddoksori_vectordb_20260106_123456.sql.gz"
    exit 1
fi

DUMP_FILE="$1"

if [ ! -f "$DUMP_FILE" ]; then
    echo "❌ 파일을 찾을 수 없습니다: $DUMP_FILE"
    exit 1
fi

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

echo "================================================================================"
echo "Vector DB 복원"
echo "================================================================================"
echo "소스 파일: $DUMP_FILE"
echo "데이터베이스: $DB_NAME"
echo "호스트: $DB_HOST:$DB_PORT"
echo ""
echo "⚠️  주의: 기존 데이터가 모두 삭제됩니다!"
read -p "계속하시겠습니까? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "❌ 복원이 취소되었습니다."
    exit 0
fi

# 1. 압축 해제
if [[ "$DUMP_FILE" == *.gz ]]; then
    echo ""
    echo "📦 압축 해제 중..."
    SQL_FILE="${DUMP_FILE%.gz}"
    gunzip -k "$DUMP_FILE"
    echo "✅ 압축 해제 완료: $SQL_FILE"
else
    SQL_FILE="$DUMP_FILE"
fi

# 2. 기존 데이터 삭제
echo ""
echo "🗑️  기존 데이터 삭제 중..."

# Docker 컨테이너 내부에서 psql 실행 (로컬에 psql이 없는 경우 대비)
CONTAINER_NAME="ddoksori_db"
if command -v psql >/dev/null 2>&1; then
    # 로컬에 psql이 있는 경우
    PGPASSWORD="$DB_PASSWORD" psql \
      -h "$DB_HOST" \
      -p "$DB_PORT" \
      -U "$DB_USER" \
      -d "$DB_NAME" \
      -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
else
    # Docker 컨테이너 내부에서 실행
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        docker exec "$CONTAINER_NAME" psql \
          -U "$DB_USER" \
          -d "$DB_NAME" \
          -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
    else
        echo "❌ 오류: Docker 컨테이너 '$CONTAINER_NAME'가 실행 중이지 않습니다."
        echo "   docker-compose up -d db 를 먼저 실행하세요."
        exit 1
    fi
fi

echo "✅ 기존 데이터 삭제 완료"

# 3. 덤프 복원
echo ""
echo "📥 데이터베이스 복원 중..."

# Docker 컨테이너 내부에서 psql 실행
if command -v psql >/dev/null 2>&1; then
    # 로컬에 psql이 있는 경우
    PGPASSWORD="$DB_PASSWORD" psql \
      -h "$DB_HOST" \
      -p "$DB_PORT" \
      -U "$DB_USER" \
      -d "$DB_NAME" \
      < "$SQL_FILE"
else
    # Docker 컨테이너 내부에서 실행
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        cat "$SQL_FILE" | docker exec -i "$CONTAINER_NAME" psql \
          -U "$DB_USER" \
          -d "$DB_NAME"
    else
        echo "❌ 오류: Docker 컨테이너 '$CONTAINER_NAME'가 실행 중이지 않습니다."
        exit 1
    fi
fi

echo "✅ 복원 완료!"

# 4. 검증
echo ""
echo "🔍 복원 검증 중..."

# Docker 컨테이너 내부에서 psql 실행
if command -v psql >/dev/null 2>&1; then
    # 로컬에 psql이 있는 경우
    DOC_COUNT=$(PGPASSWORD="$DB_PASSWORD" psql \
      -h "$DB_HOST" \
      -p "$DB_PORT" \
      -U "$DB_USER" \
      -d "$DB_NAME" \
      -t -c "SELECT COUNT(*) FROM documents;" | tr -d ' ')

    CHUNK_COUNT=$(PGPASSWORD="$DB_PASSWORD" psql \
      -h "$DB_HOST" \
      -p "$DB_PORT" \
      -U "$DB_USER" \
      -d "$DB_NAME" \
      -t -c "SELECT COUNT(*) FROM chunks;" | tr -d ' ')

    EMBEDDED_COUNT=$(PGPASSWORD="$DB_PASSWORD" psql \
      -h "$DB_HOST" \
      -p "$DB_PORT" \
      -U "$DB_USER" \
      -d "$DB_NAME" \
      -t -c "SELECT COUNT(*) FROM chunks WHERE embedding IS NOT NULL;" | tr -d ' ')
else
    # Docker 컨테이너 내부에서 실행
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        DOC_COUNT=$(docker exec "$CONTAINER_NAME" psql \
          -U "$DB_USER" \
          -d "$DB_NAME" \
          -t -c "SELECT COUNT(*) FROM documents;" | tr -d ' ')

        CHUNK_COUNT=$(docker exec "$CONTAINER_NAME" psql \
          -U "$DB_USER" \
          -d "$DB_NAME" \
          -t -c "SELECT COUNT(*) FROM chunks;" | tr -d ' ')

        EMBEDDED_COUNT=$(docker exec "$CONTAINER_NAME" psql \
          -U "$DB_USER" \
          -d "$DB_NAME" \
          -t -c "SELECT COUNT(*) FROM chunks WHERE embedding IS NOT NULL;" | tr -d ' ')
    else
        echo "❌ 오류: Docker 컨테이너 '$CONTAINER_NAME'가 실행 중이지 않습니다."
        DOC_COUNT=0
        CHUNK_COUNT=0
        EMBEDDED_COUNT=0
    fi
fi

echo "================================================================================"
echo "✅ 복원 완료 및 검증"
echo "================================================================================"
echo "문서 수: $DOC_COUNT"
echo "청크 수: $CHUNK_COUNT"
echo "임베딩된 청크: $EMBEDDED_COUNT"
echo "================================================================================"

# 5. 임시 파일 정리
if [[ "$DUMP_FILE" == *.gz ]] && [ -f "$SQL_FILE" ]; then
    read -p "압축 해제된 SQL 파일을 삭제하시겠습니까? (yes/no): " DELETE_SQL
    if [ "$DELETE_SQL" == "yes" ]; then
        rm "$SQL_FILE"
        echo "✅ 임시 파일 삭제 완료"
    fi
fi
