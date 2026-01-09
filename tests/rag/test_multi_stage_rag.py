"""
  RAG   

4       :
1.   ( )
2.    ( )
3.   ( )
4.   ( )
"""

import os
import sys
from dotenv import load_dotenv
from datetime import datetime
import json

#   backend  Python  
project_root = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'backend'))

from app.rag import MultiStageRetriever


#   
load_dotenv()


# DB 
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME', 'ddoksori'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'postgres')
}


#   
TEST_CASES = [
    {
        'id': 1,
        'name': '  ( )',
        'query': '   3    .    ?',
        'expected_agency': 'ecmc',  #   -> 
        'product_category': '',
        'purchase_method': ''
    },
    {
        'id': 2,
        'name': '   ( )',
        'query': '   2    .   .',
        'expected_agency': 'ecmc',  #  -> 
        'product_category': '',
        'purchase_method': ''
    },
    {
        'id': 3,
        'name': '  ( )',
        'query': '         .    ?',
        'expected_agency': 'kca',  #   -> 
        'product_category': '',
        'purchase_method': ''
    },
    {
        'id': 4,
        'name': '  ( )',
        'query': '        .      ?',
        'expected_agency': 'kcdrc',  #   -> 
        'product_category': '',
        'purchase_method': ''
    }
]


def print_separator(title: str = None):
    """ """
    if title:
        print(f"\n{'='*80}")
        print(f"  {title}")
        print(f"{'='*80}\n")
    else:
        print(f"{'='*80}\n")


def print_test_case_header(test_case: dict):
    """   """
    print_separator(f" {test_case['id']}: {test_case['name']}")
    print(f"**질문:** {test_case['query']}")
    print(f"**예상 기관:** {test_case['expected_agency']}")
    print(f"**제품 카테고리:** {test_case['product_category']}")
    print(f"**구매 방법:** {test_case['purchase_method']}")
    print()


def print_stage_results(stage_name: str, chunks: list):
    """   """
    print(f"\n[{stage_name}] {len(chunks)}개 청크 검색됨")
    if chunks:
        for idx, chunk in enumerate(chunks[:3], 1):  #  3 
            print(f"  {idx}. [{chunk.get('chunk_type', 'N/A')}] "
                  f": {chunk.get('similarity', 0):.3f} - "
                  f"{chunk.get('text', '')[:100]}...")


def evaluate_results(test_case: dict, results: dict) -> dict:
    """
      
    
    Returns:
          
    """
    evaluation = {
        'test_id': test_case['id'],
        'test_name': test_case['name'],
        'timestamp': datetime.now().isoformat()
    }
    
    # 1.   
    stats = results.get('stats', {})
    evaluation['total_chunks'] = stats.get('total_chunks', 0)
    evaluation['law_chunks'] = stats.get('law_chunks', 0)
    evaluation['criteria_chunks'] = stats.get('criteria_chunks', 0)
    evaluation['mediation_chunks'] = stats.get('mediation_chunks', 0)
    evaluation['counsel_chunks'] = stats.get('counsel_chunks', 0)
    evaluation['used_fallback'] = stats.get('used_fallback', False)
    
    # 2.   
    agency_rec = results.get('agency_recommendation')
    if agency_rec and agency_rec.get('top_agency'):
        recommended_agency = agency_rec['top_agency'][0]  # (agency_code, score, info)
        evaluation['recommended_agency'] = recommended_agency
        evaluation['agency_correct'] = (recommended_agency == test_case['expected_agency'])
        evaluation['agency_score'] = agency_rec['top_agency'][1]
    else:
        evaluation['recommended_agency'] = None
        evaluation['agency_correct'] = False
        evaluation['agency_score'] = 0.0
    
    # 3.  
    all_chunks = results.get('all_chunks', [])
    if all_chunks:
        similarities = [chunk.get('similarity', 0) for chunk in all_chunks]
        evaluation['avg_similarity'] = sum(similarities) / len(similarities)
        evaluation['max_similarity'] = max(similarities)
        evaluation['min_similarity'] = min(similarities)
    else:
        evaluation['avg_similarity'] = 0.0
        evaluation['max_similarity'] = 0.0
        evaluation['min_similarity'] = 0.0
    
    # 4. Fallback  
    evaluation['fallback_triggered'] = results.get('used_fallback', False)
    
    return evaluation


def print_evaluation(evaluation: dict):
    """  """
    print(f"\n{''*80}")
    print("  ")
    print(f"{''*80}")
    
    print(f"\n   :")
    print(f"  -   : {evaluation['total_chunks']}")
    print(f"  - : {evaluation['law_chunks']}")
    print(f"  - : {evaluation['criteria_chunks']}")
    print(f"  - : {evaluation['mediation_chunks']}")
    print(f"  - : {evaluation['counsel_chunks']}")
    print(f"  - Fallback : {'' if evaluation['fallback_triggered'] else ''}")
    
    print(f"\n  :")
    print(f"  -  : {evaluation['avg_similarity']:.3f}")
    print(f"  -  : {evaluation['max_similarity']:.3f}")
    print(f"  -  : {evaluation['min_similarity']:.3f}")
    
    print(f"\n  :")
    if evaluation['recommended_agency']:
        status = " " if evaluation['agency_correct'] else " "
        print(f"  -  : {evaluation['recommended_agency']} ({status})")
        print(f"  -  : {evaluation['agency_score']:.3f}")
    else:
        print(f"  -   ")
    
    print()


def run_test(retriever: MultiStageRetriever, test_case: dict) -> dict:
    """
       
    
    Args:
        retriever:   
        test_case:  
        
    Returns:
         
    """
    print_test_case_header(test_case)
    
    #    
    start_time = datetime.now()
    
    results = retriever.search_multi_stage(
        query=test_case['query'],
        law_top_k=3,
        criteria_top_k=3,
        mediation_top_k=5,
        counsel_top_k=3,
        mediation_threshold=2,
        enable_agency_recommendation=True
    )
    
    end_time = datetime.now()
    elapsed_time = (end_time - start_time).total_seconds()
    
    print(f"\n⏱  : {elapsed_time:.2f}")
    
    # Stage  
    stage1 = results.get('stage1', {})
    print_stage_results("Stage 1: ", stage1.get('law', []))
    print_stage_results("Stage 1: ", stage1.get('criteria', []))
    
    stage2 = results.get('stage2', [])
    print_stage_results("Stage 2: ", stage2)
    
    if results.get('used_fallback'):
        stage3 = results.get('stage3', [])
        print_stage_results("Stage 3:  (Fallback)", stage3)
    
    #    
    agency_rec = results.get('agency_recommendation')
    if agency_rec:
        print(f"\n   :")
        print(agency_rec['formatted'])
    
    # 
    evaluation = evaluate_results(test_case, results)
    evaluation['elapsed_time'] = elapsed_time
    print_evaluation(evaluation)
    
    return evaluation


def print_summary(evaluations: list):
    """   """
    print_separator("   ")
    
    total_tests = len(evaluations)
    total_chunks = sum(e['total_chunks'] for e in evaluations)
    avg_chunks = total_chunks / total_tests if total_tests > 0 else 0
    
    fallback_count = sum(1 for e in evaluations if e['fallback_triggered'])
    fallback_rate = fallback_count / total_tests * 100 if total_tests > 0 else 0
    
    agency_correct = sum(1 for e in evaluations if e['agency_correct'])
    agency_accuracy = agency_correct / total_tests * 100 if total_tests > 0 else 0
    
    avg_similarity = sum(e['avg_similarity'] for e in evaluations) / total_tests if total_tests > 0 else 0
    avg_time = sum(e['elapsed_time'] for e in evaluations) / total_tests if total_tests > 0 else 0
    
    print(f"  : {total_tests}")
    print(f"    : {avg_chunks:.1f}")
    print(f" Fallback : {fallback_rate:.1f}% ({fallback_count}/{total_tests})")
    print(f"   : {agency_accuracy:.1f}% ({agency_correct}/{total_tests})")
    print(f"  : {avg_similarity:.3f}")
    print(f"   : {avg_time:.2f}")
    
    print(f"\n  :")
    for e in evaluations:
        status = "" if e['agency_correct'] else ""
        print(f"  {status}  {e['test_id']}: {e['test_name']}")
        print(f"     - : {e['total_chunks']}, : {e['avg_similarity']:.3f}, "
              f": {e['recommended_agency']}, : {e['elapsed_time']:.2f}")


def save_results(evaluations: list, output_file: str = "test_results.json"):
    """  JSON  """
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(evaluations, f, ensure_ascii=False, indent=2)
    print(f"\n  : {output_file}")


def main():
    """  """
    print_separator("   RAG   ")
    
    print("  :")
    print(f"  - DB Host: {DB_CONFIG['host']}")
    print(f"  - DB Name: {DB_CONFIG['database']}")
    print(f"  -   : {len(TEST_CASES)}")
    
    #    
    try:
        retriever = MultiStageRetriever(DB_CONFIG)
        print("   ")
    except Exception as e:
        print(f"   : {e}")
        return
    
    #    
    evaluations = []
    
    for test_case in TEST_CASES:
        try:
            evaluation = run_test(retriever, test_case)
            evaluations.append(evaluation)
        except Exception as e:
            print(f"  {test_case['id']}  : {e}")
            import traceback
            traceback.print_exc()
    
    #  
    retriever.close()
    
    #  
    if evaluations:
        print_summary(evaluations)
        save_results(evaluations)
    else:
        print("\n   .")
    
    print_separator("  ")


if __name__ == "__main__":
    main()
