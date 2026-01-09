-- Database initialization script
-- This script runs when the PostgreSQL container is first created

-- Create database if not exists
SELECT 'CREATE DATABASE ddoksori'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'ddoksori')\gexec

-- Connect to ddoksori database
\c ddoksori

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE ddoksori TO postgres;
