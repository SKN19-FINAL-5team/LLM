#!/usr/bin/env python3
"""
hybrid_search_chunks   
    
"""

import os
import sys
import psycopg2
from pathlib import Path
from dotenv import load_dotenv

#   
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

#   
env_file = backend_dir / '.env'
if env_file.exists():
    load_dotenv(env_file)
else:
    load_dotenv()


def test_function_exists():
    """  """
    print("=" * 80)
    print("1.   ")
    print("=" * 80)
    
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'database': os.getenv('DB_NAME', 'ddoksori'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres')
    }
    
    try:
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()
        
        #   
        cur.execute("""
            SELECT 
                p.proname as function_name,
                pg_get_function_arguments(p.oid) as arguments
            FROM pg_proc p
            JOIN pg_namespace n ON p.pronamespace = n.oid
            WHERE n.nspname = 'public'
              AND p.proname = 'hybrid_search_chunks'
        """)
        
        result = cur.fetchone()
        
        if result:
            print(f"  : {result[0]}")
            print(f"   : {result[1]}")
            cur.close()
            conn.close()
            return True
        else:
            print("   .")
            cur.close()
            conn.close()
            return False
            
    except Exception as e:
        print(f"  : {e}")
        return False


def test_function_call():
    """  """
    print("\n" + "=" * 80)
    print("2.   ")
    print("=" * 80)
    
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'database': os.getenv('DB_NAME', 'ddoksori'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres')
    }
    
    try:
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()
        
        #     (1024,  0)
        test_embedding = [0.0] * 1024
        
        #  
        test_keywords = ['', '']
        
        #   (   )
        sql = """
            SELECT * FROM hybrid_search_chunks(
                query_embedding := %s::vector,
                query_keywords := %s,
                doc_type_filter := 'law'::VARCHAR(50),
                chunk_type_filter := NULL::VARCHAR(50),
                source_org_filter := NULL::VARCHAR(100),
                vector_weight := 0.7,
                keyword_weight := 0.3,
                top_k := 5,
                min_similarity := 0.0
            )
        """
        
        print("  ...")
        cur.execute(sql, (test_embedding, test_keywords))
        
        rows = cur.fetchall()
        print(f"   : {len(rows)}  ")
        
        if rows:
            print("\n  (  ):")
            print(f"  chunk_id: {rows[0][0]}")
            print(f"  doc_id: {rows[0][1]}")
            print(f"  final_score: {rows[0][9]}")
        
        cur.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"   : {e}")
        import traceback
        traceback.print_exc()
        return False


def test_law_retriever_integration():
    """LawRetriever  """
    print("\n" + "=" * 80)
    print("3. LawRetriever  ")
    print("=" * 80)
    
    try:
        from app.rag.specialized_retrievers.law_retriever import LawRetriever
        from app.rag.query_analyzer import QueryAnalyzer
        
        db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 5432)),
            'database': os.getenv('DB_NAME', 'ddoksori'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', 'postgres')
        }
        
        retriever = LawRetriever(db_config)
        retriever.connect_db()
        
        query_analyzer = QueryAnalyzer()
        query_analysis = query_analyzer.analyze(" 750")
        
        #   ( )
        test_embedding = [0.0] * 1024
        
        print("LawRetriever._hybrid_search   ...")
        results = retriever._hybrid_search(
            query_embedding=test_embedding,
            keywords=['', '750'],
            law_names=[],
            top_k=5,
            debug=True
        )
        
        print(f" LawRetriever   : {len(results)} ")
        
        retriever.cur.close()
        retriever.conn.close()
        return True
        
    except Exception as e:
        print(f" LawRetriever   : {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """  """
    print("\n" + "=" * 80)
    print("hybrid_search_chunks  ")
    print("=" * 80 + "\n")
    
    results = []
    
    # 1.   
    results.append(("  ", test_function_exists()))
    
    # 2.   
    if results[0][1]:  #   
        results.append(("  ", test_function_call()))
        
        # 3. LawRetriever  
        if results[1][1]:  #    
            results.append(("LawRetriever  ", test_law_retriever_integration()))
    
    #  
    print("\n" + "=" * 80)
    print("  ")
    print("=" * 80)
    
    all_passed = True
    for test_name, passed in results:
        status = " " if passed else " "
        print(f"{status}: {test_name}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n   !")
        return 0
    else:
        print("\n   ")
        return 1


if __name__ == "__main__":
    sys.exit(main())
