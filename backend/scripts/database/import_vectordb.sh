#!/bin/bash
# Vector DB  

set -e

if [ -z "$1" ]; then
    echo ": $0 <dump_file.sql.gz>"
    echo ""
    echo ": $0 ./vectordb_backups/ddoksori_vectordb_20260106_123456.sql.gz"
    exit 1
fi

DUMP_FILE="$1"

if [ ! -f "$DUMP_FILE" ]; then
    echo "    : $DUMP_FILE"
    exit 1
fi

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

echo "================================================================================"
echo "Vector DB "
echo "================================================================================"
echo " : $DUMP_FILE"
echo ": $DB_NAME"
echo ": $DB_HOST:$DB_PORT"
echo ""
echo "  :    !"
read -p "? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "  ."
    exit 0
fi

# 1.  
if [[ "$DUMP_FILE" == *.gz ]]; then
    echo ""
    echo "   ..."
    SQL_FILE="${DUMP_FILE%.gz}"
    gunzip -k "$DUMP_FILE"
    echo "   : $SQL_FILE"
else
    SQL_FILE="$DUMP_FILE"
fi

# 2.   
echo ""
echo "     ..."

# Docker   psql  ( psql   )
CONTAINER_NAME="ddoksori_db"
if command -v psql >/dev/null 2>&1; then
    #  psql  
    PGPASSWORD="$DB_PASSWORD" psql \
      -h "$DB_HOST" \
      -p "$DB_PORT" \
      -U "$DB_USER" \
      -d "$DB_NAME" \
      -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
else
    # Docker   
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        docker exec "$CONTAINER_NAME" psql \
          -U "$DB_USER" \
          -d "$DB_NAME" \
          -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
    else
        echo " : Docker  '$CONTAINER_NAME'   ."
        echo "   docker-compose up -d db   ."
        exit 1
    fi
fi

echo "    "

# 3.  
echo ""
echo "   ..."

# Docker   psql 
if command -v psql >/dev/null 2>&1; then
    #  psql  
    PGPASSWORD="$DB_PASSWORD" psql \
      -h "$DB_HOST" \
      -p "$DB_PORT" \
      -U "$DB_USER" \
      -d "$DB_NAME" \
      < "$SQL_FILE"
else
    # Docker   
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        cat "$SQL_FILE" | docker exec -i "$CONTAINER_NAME" psql \
          -U "$DB_USER" \
          -d "$DB_NAME"
    else
        echo " : Docker  '$CONTAINER_NAME'   ."
        exit 1
    fi
fi

echo "  !"

# 4. 
echo ""
echo "   ..."

# Docker   psql 
if command -v psql >/dev/null 2>&1; then
    #  psql  
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
    # Docker   
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
        echo " : Docker  '$CONTAINER_NAME'   ."
        DOC_COUNT=0
        CHUNK_COUNT=0
        EMBEDDED_COUNT=0
    fi
fi

echo "================================================================================"
echo "    "
echo "================================================================================"
echo " : $DOC_COUNT"
echo " : $CHUNK_COUNT"
echo " : $EMBEDDED_COUNT"
echo "================================================================================"

# 5.   
if [[ "$DUMP_FILE" == *.gz ]] && [ -f "$SQL_FILE" ]; then
    read -p "  SQL  ? (yes/no): " DELETE_SQL
    if [ "$DELETE_SQL" == "yes" ]; then
        rm "$SQL_FILE"
        echo "    "
    fi
fi
