#!/usr/bin/env python3
"""
 DB     

Usage:
    cd /home/maroco/ddoksori_demo/backend/scripts
    conda run -n ddoksori python update_metadata_keywords.py
"""

import sys
from pathlib import Path
import psycopg2
import os
import json
from dotenv import load_dotenv
from datetime import datetime

#   sys.path 
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.data_processing.metadata_enricher import MetadataEnricher

# .env 
load_dotenv(project_root / '.env')


def update_metadata():
    """   """
    print("=" * 80)
    print("   ")
    print("=" * 80)
    
    # DB 
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5432'),
            database=os.getenv('DB_NAME', 'ddoksori'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', 'postgres')
        )
        cur = conn.cursor()
        print(" DB  ")
    except Exception as e:
        print(f" DB  : {e}")
        return
    
    # MetadataEnricher 
    enricher = MetadataEnricher()
    print(" MetadataEnricher  ")
    
    #   
    print("\n   ...")
    cur.execute("""
        SELECT d.doc_id, string_agg(c.content, ' ' ORDER BY c.chunk_index) as full_content
        FROM documents d
        JOIN chunks c ON d.doc_id = c.doc_id
        WHERE c.drop = FALSE
        GROUP BY d.doc_id
    """)
    
    docs = cur.fetchall()
    total_docs = len(docs)
    print(f" {total_docs}  ")
    
    #   
    updated_count = 0
    error_count = 0
    start_time = datetime.now()
    
    print("\n    ...")
    print(f"{' ID':<50} {'':<10} {' ':<10} {'':<10}")
    print("-" * 80)
    
    for idx, (doc_id, full_content) in enumerate(docs, 1):
        progress = (idx / total_docs) * 100
        
        try:
            #  
            keywords = enricher.extract_keywords(full_content, top_k=15)
            
            #  
            entities = enricher.extract_entities(full_content)
            
            #   
            legal_terms = enricher.extract_legal_terms(full_content)
            
            #   (  )
            category = enricher.infer_category(full_content)
            
            #   
            metadata_update = {
                'keywords': keywords,
                'products': entities.get('products', [])[:10],
                'companies': entities.get('companies', [])[:5],
                'legal_terms': legal_terms[:20]
            }
            
            if category:
                metadata_update['category'] = category
            
            # DB  (  )
            cur.execute("""
                UPDATE documents
                SET metadata = metadata || %s::jsonb,
                    updated_at = NOW()
                WHERE doc_id = %s
            """, (json.dumps(metadata_update), doc_id))
            
            updated_count += 1
            
            #   
            status = ""
            doc_id_short = doc_id[:47] + "..." if len(doc_id) > 50 else doc_id
            print(f"{doc_id_short:<50} {status:<10} {len(keywords):<10} {progress:>6.1f}%")
            
            #  
            if idx % 100 == 0:
                conn.commit()
                elapsed = (datetime.now() - start_time).total_seconds()
                avg_time = elapsed / idx
                remaining = (total_docs - idx) * avg_time
                print(f"      ({idx}/{total_docs}) -   : {remaining/60:.1f}")
        
        except Exception as e:
            error_count += 1
            status = ""
            doc_id_short = doc_id[:47] + "..." if len(doc_id) > 50 else doc_id
            print(f"{doc_id_short:<50} {status:<10} {'':<10} {progress:>6.1f}%")
            print(f"   : {str(e)}")
    
    #  
    conn.commit()
    
    #  
    elapsed_time = (datetime.now() - start_time).total_seconds()
    
    print("\n" + "=" * 80)
    print("  ")
    print("=" * 80)
    print(f"  -  : {total_docs}")
    print(f"  -  : {updated_count}")
    print(f"  - : {error_count}")
    print(f"  -  : {elapsed_time/60:.1f}")
    print(f"  -   : {elapsed_time/total_docs:.2f}/")
    
    #  
    print("\n  :")
    cur.execute("""
        SELECT 
            doc_type,
            COUNT(*) as total_docs,
            COUNT(CASE WHEN metadata ? 'keywords' THEN 1 END) as has_keywords,
            ROUND(100.0 * COUNT(CASE WHEN metadata ? 'keywords' THEN 1 END) / COUNT(*), 2) as coverage_pct
        FROM documents
        GROUP BY doc_type
        ORDER BY doc_type
    """)
    
    print(f"{' ':<30} {' ':<10} {' ':<15} {'':<10}")
    print("-" * 80)
    for row in cur.fetchall():
        doc_type, total, has_kw, coverage = row
        print(f"{doc_type:<30} {total:<10} {has_kw:<15} {coverage:>6.1f}%")
    
    # 
    cur.close()
    conn.close()
    
    print("\n    !")


if __name__ == "__main__":
    update_metadata()
