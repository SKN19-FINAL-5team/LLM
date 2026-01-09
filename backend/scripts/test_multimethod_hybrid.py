#!/usr/bin/env python3
"""
MultiMethodRetriever.search_hybrid()  
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

#   
backend_dir = Path(__file__).parent.parent
project_root = backend_dir.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_dir))

#   
env_file = backend_dir / '.env'
if env_file.exists():
    load_dotenv(env_file)
else:
    load_dotenv()


def test_hybrid_search():
    """MultiMethodRetriever.search_hybrid() """
    print("=" * 80)
    print("MultiMethodRetriever.search_hybrid() 테스트 시작")
    print("=" * 80)
    
    try:
        from app.rag.multi_method_retriever import MultiMethodRetriever
        
        db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 5432)),
            'database': os.getenv('DB_NAME', 'ddoksori'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', 'postgres')
        }
        
        print("\n1. MultiMethodRetriever 초기화 중...")
        retriever = MultiMethodRetriever(db_config)
        
        print("\n2. Hybrid Search  ...")
        query = " 750 "
        
        result = retriever.search_hybrid(query=query, top_k=5)
        
        print(f"\n Hybrid Search !")
        print(f"    : {result.get('method')}")
        print(f"    : {result.get('count')}")
        print(f"    : {result.get('elapsed_time', 0):.3f}")
        print(f"    : {result.get('success', False)}")
        
        if result.get('success') and result.get('results'):
            print(f"\n3.   ( 3):")
            for idx, r in enumerate(result['results'][:3], 1):
                print(f"\n   [{idx}]")
                print(f"      chunk_id: {r.get('chunk_id', 'N/A')[:50]}...")
                print(f"      source: {r.get('source', 'N/A')}")
                print(f"      score: {r.get('score', 0):.4f}")
                print(f"      text: {r.get('text', '')[:100]}...")
        
        if not result.get('success'):
            error = result.get('error', 'Unknown error')
            print(f"\n Hybrid Search : {error}")
            retriever.close()
            return False
        
        retriever.close()
        return True
        
    except Exception as e:
        print(f"\n  : {e}")
        import traceback
        traceback.print_exc()
        return False


def test_all_methods_integration():
    """search_all_methods() hybrid   """
    print("\n" + "=" * 80)
    print("search_all_methods()   (hybrid )")
    print("=" * 80)
    
    try:
        from app.rag.multi_method_retriever import MultiMethodRetriever
        
        db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 5432)),
            'database': os.getenv('DB_NAME', 'ddoksori'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', 'postgres')
        }
        
        print("\n1. MultiMethodRetriever 초기화 중...")
        retriever = MultiMethodRetriever(db_config)
        
        print("\n2.     ...")
        query = "  "
        
        results = retriever.search_all_methods(
            query=query,
            top_k=5,
            methods=['cosine', 'hybrid']  # hybrid 
        )
        
        print(f"\n     !")
        print(f"   : {query}")
        print(f"     : {results.get('total_methods', 0)}")
        print(f"     : {results.get('successful_methods', 0)}")
        
        print(f"\n3.   :")
        for method_name, method_data in results.get('methods', {}).items():
            success = method_data.get('success', False)
            count = method_data.get('count', 0)
            elapsed = method_data.get('elapsed_time', 0)
            status = "" if success else ""
            print(f"   {status} {method_name.upper()}: {count}  ({elapsed:.3f})")
            if not success:
                error = method_data.get('error', 'Unknown error')
                print(f"      : {error}")
        
        hybrid_result = results.get('methods', {}).get('hybrid', {})
        if hybrid_result.get('success'):
            print(f"\n Hybrid Search   !")
            retriever.close()
            return True
        else:
            print(f"\n Hybrid Search   ")
            retriever.close()
            return False
        
    except Exception as e:
        print(f"\n  : {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """  """
    print("\n" + "=" * 80)
    print("MultiMethodRetriever Hybrid Search  ")
    print("=" * 80)
    
    results = []
    
    # 1. Hybrid Search  
    results.append(("Hybrid Search  ", test_hybrid_search()))
    
    # 2.   
    if results[0][1]:  #     
        results.append(("search_all_methods()  ", test_all_methods_integration()))
    
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
        print("\n    !")
        print("   hybrid_search_chunks   .")
        return 0
    else:
        print("\n   ")
        return 1


if __name__ == "__main__":
    sys.exit(main())
