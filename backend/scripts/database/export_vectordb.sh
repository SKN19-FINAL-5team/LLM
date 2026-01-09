#!/bin/bash
# Vector DB      

set -e

#   
#   .env  backend/.env  
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

#    (  )
BACKUP_DIR="$SCRIPT_DIR/vectordb_backups"
mkdir -p "$BACKUP_DIR"

# 
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DUMP_FILE="$BACKUP_DIR/ddoksori_vectordb_${TIMESTAMP}.sql"
COMPRESSED_FILE="${DUMP_FILE}.gz"

echo "================================================================================"
echo "Vector DB  "
echo "================================================================================"
echo ": $DB_NAME"
echo ": $DB_HOST:$DB_PORT"
echo " : $DUMP_FILE"
echo ""

# 1.    ( + )
echo "    ..."

# Docker   pg_dump  ( pg_dump   )
if command -v pg_dump >/dev/null 2>&1; then
    #  pg_dump  
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
    # Docker   
    CONTAINER_NAME="ddoksori_db"
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        docker exec "$CONTAINER_NAME" pg_dump \
          -U "$DB_USER" \
          -d "$DB_NAME" \
          --no-owner \
          --no-acl \
          -F p > "$DUMP_FILE"
    else
        echo " : Docker  '$CONTAINER_NAME'   ."
        echo "   docker-compose up -d db   ."
        exit 1
    fi
fi

echo "  : $DUMP_FILE"

# 2. 
echo ""
echo "   ..."
gzip -9 "$DUMP_FILE"
echo "  : $COMPRESSED_FILE"

# 3.  
FILE_SIZE=$(du -h "$COMPRESSED_FILE" | cut -f1)
echo ""
echo "================================================================================"
echo "  !"
echo "================================================================================"
echo ": $COMPRESSED_FILE"
echo ": $FILE_SIZE"
echo ""
echo "   :"
echo "  1.   (Google Drive, Dropbox )"
echo "  2.   "
echo "  3. Git LFS (50MB  )"
echo ""
echo "   :"
echo "  gunzip $COMPRESSED_FILE"
echo "  PGPASSWORD=\$DB_PASSWORD psql -h localhost -U postgres -d ddoksori < $DUMP_FILE"
echo "================================================================================"

# 4.  
echo ""
echo "   ..."
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

echo "  : $BACKUP_DIR/ddoksori_vectordb_${TIMESTAMP}_metadata.json"
