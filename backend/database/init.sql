-- Database initialization script
-- This script runs when the PostgreSQL container is first created
-- PostgreSQL은 /docker-entrypoint-initdb.d/ 디렉토리의 .sql, .sh 파일을 알파벳 순서로 자동 실행합니다.

-- Create database if not exists
SELECT 'CREATE DATABASE ddoksori'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'ddoksori')\gexec

-- Connect to ddoksori database
\c ddoksori

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE ddoksori TO postgres;

-- Note: 실제 테이블 스키마(schema_v2_final.sql)는 별도로 실행해야 합니다.
-- Docker 컨테이너 내에서 실행:
--   docker exec -i ddoksori_db psql -U postgres -d ddoksori < /path/to/schema_v2_final.sql
-- 또는 로컬에서 실행:
--   psql -h localhost -p 5432 -U postgres -d ddoksori -f backend/database/schema_v2_final.sql
