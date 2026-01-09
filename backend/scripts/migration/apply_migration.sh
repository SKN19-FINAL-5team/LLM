#!/bin/bash

# Migration 적용 스크립트
# 사용법: ./apply_migration.sh <migration_file>

set -e  # 에러 발생 시 즉시 종료

# 환경 변수 로드
if [ -f "../.env" ]; then
    export $(cat ../.env | grep -v '^#' | xargs)
fi

# 기본값 설정
DB_NAME="${POSTGRES_DB:-ddoksori}"
DB_USER="${POSTGRES_USER:-maroco}"
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"

# 인자 확인
if [ $# -eq 0 ]; then
    echo "사용법: $0 <migration_file>"
    echo "예시: $0 ../database/migrations/001_add_hybrid_search_support.sql"
    exit 1
fi

MIGRATION_FILE="$1"

# 파일 존재 확인
if [ ! -f "$MIGRATION_FILE" ]; then
    echo "❌ 마이그레이션 파일을 찾을 수 없습니다: $MIGRATION_FILE"
    exit 1
fi

echo "========================================"
echo "Migration 적용"
echo "========================================"
echo "데이터베이스: $DB_NAME"
echo "호스트: $DB_HOST:$DB_PORT"
echo "마이그레이션 파일: $MIGRATION_FILE"
echo ""

# 백업 생성 (선택사항)
read -p "백업을 먼저 생성하시겠습니까? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    BACKUP_FILE="./vectordb_backups/backup_before_migration_$(date +%Y%m%d_%H%M%S).sql"
    mkdir -p ./vectordb_backups
    echo "📦 백업 생성 중..."
    pg_dump -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -F p -f "$BACKUP_FILE"
    echo "✅ 백업 완료: $BACKUP_FILE"
    echo ""
fi

# 마이그레이션 적용
echo "🔧 마이그레이션 적용 중..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f "$MIGRATION_FILE"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ 마이그레이션이 성공적으로 적용되었습니다."
    echo "========================================"
else
    echo ""
    echo "❌ 마이그레이션 적용 중 오류가 발생했습니다."
    echo "========================================"
    exit 1
fi
