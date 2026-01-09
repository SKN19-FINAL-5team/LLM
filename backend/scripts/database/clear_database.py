#!/usr/bin/env python3
"""
  
 documents chunks       .

:
  python backend/scripts/clear_database.py --force
"""

import os
import sys
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def main():
    print("=" * 80)
    print("   ")
    print("=" * 80)
    print("\n      :")
    print("  - documents ")
    print("  - chunks ")
    print("\n  :     !")
    
    # --force  
    if '--force' not in sys.argv:
        print("\n    --force  :")
        print("   python backend/scripts/database/clear_database.py --force")
        return
    
    #  
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5432'),
            database=os.getenv('DB_NAME', 'ddoksori'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', 'postgres')
        )
        cur = conn.cursor()
        print("\n   ")
    except Exception as e:
        print(f"\n   : {e}")
        return
    
    #   
    print("\n   :")
    cur.execute("SELECT COUNT(*) FROM documents")
    doc_count = cur.fetchone()[0]
    print(f"  -  : {doc_count:,}")
    
    cur.execute("SELECT COUNT(*) FROM chunks")
    chunk_count = cur.fetchone()[0]
    print(f"  -  : {chunk_count:,}")
    
    cur.execute("SELECT COUNT(*) FROM chunks WHERE embedding IS NOT NULL")
    embedded_count = cur.fetchone()[0]
    print(f"  -  : {embedded_count:,}")
    
    #  
    print("\n    ...")
    try:
        # chunks   (  )
        cur.execute("TRUNCATE TABLE chunks CASCADE;")
        print("   chunks  ")
        
        # documents 
        cur.execute("TRUNCATE TABLE documents CASCADE;")
        print("   documents  ")
        
        conn.commit()
        print("\n   !")
        print("\n       :")
        print("  conda run -n ddoksori python backend/scripts/embedding/embed_data_remote.py")
        
    except Exception as e:
        conn.rollback()
        print(f"\n  : {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    main()
