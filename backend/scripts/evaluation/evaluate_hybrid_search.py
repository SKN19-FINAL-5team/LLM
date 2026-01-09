#!/usr/bin/env python3
"""
    

      
"""

import sys
from pathlib import Path
import os
import time

sys.path.append(str(Path(__file__).parent.parent / 'app'))

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

#   
TEST_QUERIES = [
    {
        'query': ' 750 ?',
        'expected_type': 'law',
        'description': '    '
    },
    {
        'query': '     ?',
        'expected_type': 'criteria',
        'description': '   '
    },
    {
        'query': '    .   ?',
        'expected_type': 'case',
        'description': '   '
    },
    {
        'query': '   ?',
        'expected_type': 'law',
        'description': '   '
    },
    {
        'query': '       ?',
        'expected_type': 'criteria',
        'description': '   '
    }
]


def evaluate_single_query(retriever, test_case: dict, debug: bool = False) -> dict:
    """  """
    query = test_case['query']
    expected_type = test_case['expected_type']
    
    print(f"\n{'='*60}")
    print(f"Query: {query}")
    print(f"Expected Type: {expected_type}")
    print(f"Description: {test_case['description']}")
    print(f"{'='*60}")
    
    #     
    start_time = time.time()
    results = retriever.search(query=query, top_k=5, debug=debug)
    elapsed_time = time.time() - start_time
    
    #  
    total_results = len(results['results'])
    doc_types = [r['doc_type'] for r in results['results']]
    top_score = results['results'][0]['score'] if total_results > 0 else 0
    
    #      
    has_expected_type = expected_type in doc_types[:3] if total_results >= 3 else expected_type in doc_types
    
    print(f"\n Results:")
    print(f"  - Total: {total_results}")
    print(f"  - Query Type: {results['query_type']}")
    print(f"  - Top Score: {top_score:.4f}")
    print(f"  - Search Time: {elapsed_time:.2f}s")
    print(f"  - Doc Types Distribution: {dict((dt, doc_types.count(dt)) for dt in set(doc_types))}")
    print(f"  - Has Expected Type in Top-3: {' Yes' if has_expected_type else ' No'}")
    
    #  3  
    print(f"\n Top 3 Results:")
    for idx, r in enumerate(results['results'][:3], 1):
        print(f"\n  {idx}. [{r['doc_type']}] Score: {r['score']:.4f}")
        print(f"     Content: {r['content'][:100]}...")
        if 'source_info' in r:
            print(f"     Source Info: {r['source_info']}")
    
    return {
        'query': query,
        'expected_type': expected_type,
        'total_results': total_results,
        'top_score': top_score,
        'elapsed_time': elapsed_time,
        'has_expected_type': has_expected_type,
        'doc_types': doc_types
    }


def main():
    """  """
    import sys
    debug = '--debug' in sys.argv or '-d' in sys.argv
    
    print("="*60)
    print("   ")
    if debug:
        print("(DEBUG MODE)")
    print("="*60)
    
    #  
    try:
        from rag.multi_stage_retriever_v2 import MultiStageRetrieverV2
        retriever = MultiStageRetrieverV2(DB_CONFIG)
        print("   ")
    except Exception as e:
        print(f"   : {e}")
        return
    
    #   
    evaluation_results = []
    for test_case in TEST_QUERIES:
        try:
            result = evaluate_single_query(retriever, test_case, debug=debug)
            evaluation_results.append(result)
        except Exception as e:
            print(f"   : {e}")
            import traceback
            traceback.print_exc()
    
    #   
    print("\n" + "="*60)
    print("   ")
    print("="*60)
    
    if evaluation_results:
        total_queries = len(evaluation_results)
        successful_queries = sum(1 for r in evaluation_results if r['has_expected_type'])
        avg_time = sum(r['elapsed_time'] for r in evaluation_results) / total_queries
        avg_score = sum(r['top_score'] for r in evaluation_results) / total_queries
        
        print(f"  : {total_queries}")
        print(f"   : {successful_queries}/{total_queries} ({successful_queries/total_queries*100:.1f}%)")
        print(f"  : {avg_time:.2f}")
        print(f" Top : {avg_score:.4f}")
        
        print(f"\n{'='*60}")
        if successful_queries == total_queries:
            print("   !")
        else:
            print(f"  {total_queries - successful_queries}  ")
    else:
        print("   ")
    
    # 
    try:
        retriever.close()
    except:
        pass


if __name__ == '__main__':
    main()
