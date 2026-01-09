#!/usr/bin/env python3
"""
Migration 적용 스크립트
"""

import sys
import os
from pathlib import Path
import psycopg2
from dotenv import load_dotenv

# 환경 변수 로드
backend_dir = Path(__file__).parent.parent
env_file = backend_dir / '.env'
if env_file.exists():
    load_dotenv(env_file)

# DB 연결 정보
DB_CONFIG = {
    'dbname': os.getenv('POSTGRES_DB', 'ddoksori'),
    'user': os.getenv('POSTGRES_USER', 'maroco'),
    'password': os.getenv('POSTGRES_PASSWORD', ''),
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': os.getenv('POSTGRES_PORT', '5432')
}


def apply_migration(migration_file: str):
    """마이그레이션 SQL 파일을 실행"""
    
    # 파일 존재 확인
    migration_path = Path(migration_file)
    if not migration_path.exists():
        print(f"❌ 마이그레이션 파일을 찾을 수 없습니다: {migration_file}")
        sys.exit(1)
    
    # SQL 파일 읽기
    print(f"📄 마이그레이션 파일 읽기: {migration_path.name}")
    with open(migration_path, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # DB 연결 및 실행
    print(f"🔗 데이터베이스 연결 중: {DB_CONFIG['dbname']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}")
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True  # DDL 문은 autocommit 필요
        cur = conn.cursor()
        
        print("🔧 마이그레이션 적용 중...")
        cur.execute(sql_content)
        
        print("✅ 마이그레이션이 성공적으로 적용되었습니다!")
        
        # 통계 조회
        cur.execute("""
            SELECT 
                COUNT(*) FILTER (WHERE keywords IS NOT NULL) as docs_with_keywords,
                COUNT(*) FILTER (WHERE search_vector IS NOT NULL) as docs_with_search_vector
            FROM documents
        """)
        stats = cur.fetchone()
        print(f"\n📊 현재 상태:")
        print(f"  - keywords 설정된 documents: {stats[0]}건")
        print(f"  - search_vector 설정된 documents: {stats[1]}건")
        
        cur.close()
        conn.close()
        
    except psycopg2.Error as e:
        print(f"\n❌ 마이그레이션 적용 중 오류 발생:")
        print(f"  {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 예기치 않은 오류 발생:")
        print(f"  {e}")
        sys.exit(1)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("사용법: python apply_migration.py <migration_file>")
        print("예시: python apply_migration.py ../database/migrations/001_add_hybrid_search_support.sql")
        sys.exit(1)
    
    migration_file = sys.argv[1]
    
    print("=" * 50)
    print("Migration 적용")
    print("=" * 50)
    
    apply_migration(migration_file)
    
    print("=" * 50)
