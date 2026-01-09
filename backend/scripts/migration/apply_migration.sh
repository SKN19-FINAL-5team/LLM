#!/bin/bash

# Migration  
# : ./apply_migration.sh <migration_file>

set -e  #     

#   
if [ -f "../.env" ]; then
    export $(cat ../.env | grep -v '^#' | xargs)
fi

#  
DB_NAME="${POSTGRES_DB:-ddoksori}"
DB_USER="${POSTGRES_USER:-maroco}"
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"

#  
if [ $# -eq 0 ]; then
    echo ": $0 <migration_file>"
    echo ": $0 ../database/migrations/001_add_hybrid_search_support.sql"
    exit 1
fi

MIGRATION_FILE="$1"

#   
if [ ! -f "$MIGRATION_FILE" ]; then
    echo "     : $MIGRATION_FILE"
    exit 1
fi

echo "========================================"
echo "Migration "
echo "========================================"
echo ": $DB_NAME"
echo ": $DB_HOST:$DB_PORT"
echo " : $MIGRATION_FILE"
echo ""

#   ()
read -p "  ? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    BACKUP_FILE="./vectordb_backups/backup_before_migration_$(date +%Y%m%d_%H%M%S).sql"
    mkdir -p ./vectordb_backups
    echo "   ..."
    pg_dump -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -F p -f "$BACKUP_FILE"
    echo "  : $BACKUP_FILE"
    echo ""
fi

#  
echo "   ..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f "$MIGRATION_FILE"

if [ $? -eq 0 ]; then
    echo ""
    echo "   ."
    echo "========================================"
else
    echo ""
    echo "     ."
    echo "========================================"
    exit 1
fi
