#!/usr/bin/env python3
"""
table 1/3/4   DB  

Usage:
    cd /home/maroco/ddoksori_demo/backend/scripts
    conda run -n ddoksori python process_criteria_tables.py
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
    print("  (table 1/3/4)   ")
    print("=" * 80)
    
    #  
    criteria_dir = project_root / "data" / "criteria"
    
    if not criteria_dir.exists():
        print(f"      : {criteria_dir}")
        return
    
    #   
    tables = [
        {
            'file': 'table1_item_chunks.jsonl',
            'transform_func': 'transform_criteria_table1',
            'description': ' '
        },
        {
            'file': 'table3_warranty_chunks.jsonl',
            'transform_func': 'transform_criteria_table3',
            'description': ''
        },
        {
            'file': 'table4_lifespan_chunks.jsonl',
            'transform_func': 'transform_criteria_table4',
            'description': ''
        }
    ]
    
    #   
    print("\n  :")
    for table in tables:
        file_path = criteria_dir / table['file']
        exists = "" if file_path.exists() else ""
        print(f"  {exists} {table['file']}")
        table['file_path'] = file_path
    
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
    for table in tables:
        if not table['file_path'].exists():
            error_msg = f"{table['file']}:    "
            errors.append(error_msg)
            print(f"\n {error_msg}")
            continue
        
        print(f"\n{'=' * 80}")
        print(f" : {table['description']} ({table['file']})")
        print(f"{'=' * 80}")
        
        try:
            #   
            transform_func = getattr(transformer, table['transform_func'])
            result = transform_func(str(table['file_path']))
            
            # DB 
            docs_inserted, chunks_inserted = insert_documents_to_db(result['documents'], conn)
            
            total_docs += docs_inserted
            total_chunks += chunks_inserted
            
            print(f"   : {docs_inserted} , {chunks_inserted} ")
        
        except Exception as e:
            error_msg = f"{table['file']}: {str(e)}"
            errors.append(error_msg)
            print(f"   : {e}")
            import traceback
            traceback.print_exc()
    
    #  
    print("\n" + "=" * 80)
    print(" ")
    print("=" * 80)
    print(f"  -  : {len(tables)}")
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
