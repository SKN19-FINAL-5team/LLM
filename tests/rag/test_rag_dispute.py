#!/usr/bin/env python3
"""
   RAG  

  (doc_type='mediation_case')  RAG 
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

#   backend  Python  
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'backend'))

from app.rag import VectorRetriever

#   
load_dotenv()


def test_dispute_rag():
    """   RAG """
    print("=" * 80)
    print("     RAG ")
    print("=" * 80)
    
    #   
    print("\n[ ]")
    print("  Vector Similarity Search with doc_type='mediation_case' filter")
    print("  -     ")
    print("  -     (doc_type='mediation_case')")
    
    # DB 
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'database': os.getenv('DB_NAME', 'ddoksori'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres')
    }
    
    # Retriever 
    retriever = VectorRetriever(db_config)
    
    #   
    print("\n[ ]")
    print("  - doc_type: 'mediation_case'")
    print("  - chunk_types: None (  )")
    print("  - agencies: None ( )")
    
    #  
    test_queries = [
        "    ?",
        "      ?",
        "     ?",
    ]
    
    for idx, query in enumerate(test_queries, 1):
        print("\n" + "-" * 80)
        print(f"[  {idx}]")
        print(f": {query}")
        print("-" * 80)
        
        try:
            #  
            chunks = retriever.search(query=query, top_k=10)
            
            # doc_type='mediation_case' 
            dispute_chunks = [
                chunk for chunk in chunks 
                if chunk.get('source') == 'mediation_case'
            ]
            
            print(f"\n : {len(dispute_chunks)}     ( {len(chunks)} )")
            
            if not dispute_chunks:
                print("      .")
                print("         .")
                continue
            
            #  5 
            for i, chunk in enumerate(dispute_chunks[:5], 1):
                print(f"\n[ {i}]")
                print(f"  : {chunk.get('similarity', 0):.4f}")
                print(f"   : {chunk.get('chunk_type', 'N/A')}")
                print(f"  : {chunk.get('agency', 'N/A')}")
                print(f"  : {chunk.get('case_no', 'N/A')}")
                print(f"  : {chunk.get('decision_date', 'N/A')}")
                print(f"   ID: {chunk.get('case_uid', 'N/A')}")
                content = chunk.get('text', '') or chunk.get('content', '')
                content_preview = content[:150] + "..." if len(content) > 150 else content
                print(f"   : {content_preview}")
            
        except Exception as e:
            print(f"  : {str(e)}")
            import traceback
            traceback.print_exc()
    
    retriever.close()
    print("\n" + "=" * 80)
    print("    RAG  ")
    print("=" * 80)


if __name__ == "__main__":
    test_dispute_rag()
