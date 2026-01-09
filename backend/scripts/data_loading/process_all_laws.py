#!/usr/bin/env python3
"""
13   DB  

Usage:
    cd /home/maroco/ddoksori_demo/backend/scripts
    conda run -n ddoksori python process_all_laws.py
"""

import sys
from pathlib import Path
import psycopg2
import os
from dotenv import load_dotenv

#   sys.path 
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.data_processing.data_transform_pipeline import DataTransformer
from scripts.data_processing.db_inserter import insert_documents_to_db

# .env 
load_dotenv(project_root / '.env')


def main():
    """ """
    print("=" * 80)
    print("    ")
    print("=" * 80)
    
    #  
    law_dir = project_root / "data" / "law"
    
    if not law_dir.exists():
        print(f"      : {law_dir}")
        return
    
    #    ( )
    law_files = []
    seen_files = set()
    
    for law_file in sorted(law_dir.glob("*.jsonl")):
        # E-Commerce vs E_Commerce   (  )
        base_name = law_file.stem.replace('-', '_')
        
        if base_name in seen_files:
            print(f"      : {law_file.name}")
            continue
        
        seen_files.add(base_name)
        law_files.append(law_file)
    
    print(f"\n  : {len(law_files)}")
    for f in law_files:
        print(f"  - {f.name}")
    
    # DB 
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5432'),
            database=os.getenv('DB_NAME', 'ddoksori'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', 'postgres')
        )
        print("\n DB  ")
    except Exception as e:
        print(f"\n DB  : {e}")
        return
    
    #   
    transformer = DataTransformer(use_db=False, enrich_metadata=False)
    
    total_docs = 0
    total_chunks = 0
    errors = []
    
    #    
    for law_file in law_files:
        print(f"\n{'=' * 80}")
        print(f" : {law_file.name}")
        print(f"{'=' * 80}")
        
        try:
            # 
            result = transformer.transform_law_single_file(str(law_file))
            
            # DB 
            docs_inserted, chunks_inserted = insert_documents_to_db(result['documents'], conn)
            
            total_docs += docs_inserted
            total_chunks += chunks_inserted
            
            print(f"   : {docs_inserted} , {chunks_inserted} ")
        
        except Exception as e:
            error_msg = f"{law_file.name}: {str(e)}"
            errors.append(error_msg)
            print(f"   : {e}")
            import traceback
            traceback.print_exc()
    
    #  
    print("\n" + "=" * 80)
    print(" ")
    print("=" * 80)
    print(f"  -  : {len(law_files)}")
    print(f"  -  : {total_docs}")
    print(f"  -  : {total_chunks}")
    print(f"  - : {len(errors)}")
    
    if errors:
        print("\n :")
        for error in errors:
            print(f"  - {error}")
    
    # 
    transformer.close()
    conn.close()
    
    print("\n    !")


if __name__ == "__main__":
    main()
