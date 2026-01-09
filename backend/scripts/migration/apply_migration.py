#!/usr/bin/env python3
"""
Migration  
"""

import sys
import os
from pathlib import Path
import psycopg2
from dotenv import load_dotenv

#   
backend_dir = Path(__file__).parent.parent
env_file = backend_dir / '.env'
if env_file.exists():
    load_dotenv(env_file)

# DB  
DB_CONFIG = {
    'dbname': os.getenv('POSTGRES_DB', 'ddoksori'),
    'user': os.getenv('POSTGRES_USER', 'maroco'),
    'password': os.getenv('POSTGRES_PASSWORD', ''),
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': os.getenv('POSTGRES_PORT', '5432')
}


def apply_migration(migration_file: str):
    """ SQL  """
    
    #   
    migration_path = Path(migration_file)
    if not migration_path.exists():
        print(f"     : {migration_file}")
        sys.exit(1)
    
    # SQL  
    print(f"   : {migration_path.name}")
    with open(migration_path, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # DB   
    print(f"   : {DB_CONFIG['dbname']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}")
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True  # DDL  autocommit 
        cur = conn.cursor()
        
        print("   ...")
        cur.execute(sql_content)
        
        print("   !")
        
        #  
        cur.execute("""
            SELECT 
                COUNT(*) FILTER (WHERE keywords IS NOT NULL) as docs_with_keywords,
                COUNT(*) FILTER (WHERE search_vector IS NOT NULL) as docs_with_search_vector
            FROM documents
        """)
        stats = cur.fetchone()
        print(f"\n  :")
        print(f"  - keywords  documents: {stats[0]}")
        print(f"  - search_vector  documents: {stats[1]}")
        
        cur.close()
        conn.close()
        
    except psycopg2.Error as e:
        print(f"\n     :")
        print(f"  {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n    :")
        print(f"  {e}")
        sys.exit(1)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(": python apply_migration.py <migration_file>")
        print(": python apply_migration.py ../database/migrations/001_add_hybrid_search_support.sql")
        sys.exit(1)
    
    migration_file = sys.argv[1]
    
    print("=" * 50)
    print("Migration ")
    print("=" * 50)
    
    apply_migration(migration_file)
    
    print("=" * 50)
