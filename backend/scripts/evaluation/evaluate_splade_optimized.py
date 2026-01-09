"""
SPLADE     
  vs    
"""

import json
import os
import sys
import time
from typing import List, Dict, Optional
from dotenv import load_dotenv
from datetime import datetime
from pathlib import Path

#    
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.rag.multi_stage_retriever_v2 import MultiStageRetrieverV2
from scripts.splade.test_splade_bm25 import BM25SparseRetriever
from scripts.splade.test_splade_naver import NaverSPLADEDBRetriever
from scripts.splade.test_splade_remote import RemoteSPLADEDBRetriever
from scripts.splade.test_splade_optimized import OptimizedSPLADEDBRetriever

#   
backend_dir = Path(__file__).parent.parent.parent
env_file = backend_dir / '.env'
if env_file.exists():
    load_dotenv(env_file)
else:
    root_env = backend_dir.parent / '.env'
    if root_env.exists():
        load_dotenv(root_env)
    else:
        load_dotenv()


def evaluate_law_tests(
    dense_retriever: MultiStageRetrieverV2,
    sparse_retriever: BM25SparseRetriever,
    old_splade_retriever: Optional[NaverSPLADEDBRetriever],
    optimized_splade_retriever: Optional[OptimizedSPLADEDBRetriever],
    test_cases: List[Dict]
) -> Dict:
    """  """
    results = {
        'dense': {'success': 0, 'total': 0, 'details': [], 'latency': []},
        'sparse': {'success': 0, 'total': 0, 'details': [], 'latency': []},
        'splade_old': {'success': 0, 'total': 0, 'details': [], 'latency': []},
        'splade_optimized': {'success': 0, 'total': 0, 'details': [], 'latency': []}
    }
    
    for test in test_cases:
        query = test['query']
        expected_article = test.get('expected_article')
        expected_articles = test.get('expected_articles', [])
        expected_law = test.get('expected_law')
        
        # Dense 
        try:
            start_time = time.time()
            dense_results = dense_retriever.search(query, top_k=5, debug=False)
            dense_latency = time.time() - start_time
            
            dense_success = False
            if expected_article:
                for r in dense_results['results'][:3]:
                    content = r.get('content', '')
                    metadata = r.get('source_info', {})
                    law_name = metadata.get('law_name', '') if isinstance(metadata, dict) else ''
                    
                    if expected_article in content:
                        if expected_law:
                            if expected_law in law_name or expected_law in content:
                                dense_success = True
                                break
                        else:
                            dense_success = True
                            break
            elif expected_articles:
                for r in dense_results['results'][:3]:
                    content = r.get('content', '')
                    for article in expected_articles:
                        if article in content:
                            dense_success = True
                            break
                    if dense_success:
                        break
            elif expected_law:
                for r in dense_results['results'][:3]:
                    content = r.get('content', '')
                    metadata = r.get('source_info', {})
                    law_name = metadata.get('law_name', '') if isinstance(metadata, dict) else ''
                    
                    if expected_law in law_name or expected_law in content:
                        dense_success = True
                        break
        except Exception as e:
            print(f"    Dense  : {e}")
            dense_success = False
            dense_latency = 0.0
        
        # Sparse 
        try:
            start_time = time.time()
            sparse_results = sparse_retriever.search_law_bm25(query, top_k=5)
            sparse_latency = time.time() - start_time
            
            sparse_success = False
            if expected_article:
                for r in sparse_results[:3]:
                    content = r.get('content', '')
                    law_name = r.get('law_name', '')
                    
                    if expected_article in content:
                        if expected_law:
                            if expected_law in law_name or expected_law in content:
                                sparse_success = True
                                break
                        else:
                            sparse_success = True
                            break
            elif expected_articles:
                for r in sparse_results[:3]:
                    content = r.get('content', '')
                    for article in expected_articles:
                        if article in content:
                            sparse_success = True
                            break
                    if sparse_success:
                        break
            elif expected_law:
                for r in sparse_results[:3]:
                    content = r.get('content', '')
                    law_name = r.get('law_name', '')
                    
                    if expected_law in law_name or expected_law in content:
                        sparse_success = True
                        break
        except Exception as e:
            print(f"    Sparse  : {e}")
            sparse_success = False
            sparse_latency = 0.0
        
        # SPLADE ( )
        splade_old_success = False
        splade_old_latency = 0.0
        if old_splade_retriever:
            try:
                start_time = time.time()
                splade_old_results = old_splade_retriever.search_law_splade(query, top_k=5)
                splade_old_latency = time.time() - start_time
                
                if expected_article:
                    for r in splade_old_results[:3]:
                        content = r.get('content', '')
                        law_name = r.get('law_name', '')
                        
                        if expected_article in content:
                            if expected_law:
                                if expected_law in law_name or expected_law in content:
                                    splade_old_success = True
                                    break
                            else:
                                splade_old_success = True
                                break
                elif expected_articles:
                    for r in splade_old_results[:3]:
                        content = r.get('content', '')
                        for article in expected_articles:
                            if article in content:
                                splade_old_success = True
                                break
                        if splade_old_success:
                            break
                elif expected_law:
                    for r in splade_old_results[:3]:
                        content = r.get('content', '')
                        law_name = r.get('law_name', '')
                        
                        if expected_law in law_name or expected_law in content:
                            splade_old_success = True
                            break
            except Exception as e:
                print(f"    SPLADE ()  : {e}")
                splade_old_success = False
                splade_old_latency = 0.0
        
        # SPLADE ( )
        splade_opt_success = False
        splade_opt_latency = 0.0
        if optimized_splade_retriever:
            try:
                start_time = time.time()
                splade_opt_results = optimized_splade_retriever.search_law_splade_optimized(query, top_k=5)
                splade_opt_latency = time.time() - start_time
                
                if expected_article:
                    for r in splade_opt_results[:3]:
                        content = r.get('content', '') or ''
                        law_name = r.get('law_name', '') or ''
                        
                        if expected_article in content:
                            if expected_law:
                                if expected_law in law_name or expected_law in content:
                                    splade_opt_success = True
                                    break
                            else:
                                splade_opt_success = True
                                break
                elif expected_articles:
                    for r in splade_opt_results[:3]:
                        content = r.get('content', '')
                        for article in expected_articles:
                            if article in content:
                                splade_opt_success = True
                                break
                        if splade_opt_success:
                            break
                elif expected_law:
                    for r in splade_opt_results[:3]:
                        content = r.get('content', '') or ''
                        law_name = r.get('law_name', '') or ''
                        
                        if expected_law in law_name or expected_law in content:
                            splade_opt_success = True
                            break
            except Exception as e:
                print(f"    SPLADE ()  : {e}")
                splade_opt_success = False
                splade_opt_latency = 0.0
        
        #  
        results['dense']['total'] += 1
        results['sparse']['total'] += 1
        if dense_success:
            results['dense']['success'] += 1
        if sparse_success:
            results['sparse']['success'] += 1
        results['dense']['latency'].append(dense_latency)
        results['sparse']['latency'].append(sparse_latency)
        
        if old_splade_retriever:
            results['splade_old']['total'] += 1
            if splade_old_success:
                results['splade_old']['success'] += 1
            results['splade_old']['latency'].append(splade_old_latency)
        
        if optimized_splade_retriever:
            results['splade_optimized']['total'] += 1
            if splade_opt_success:
                results['splade_optimized']['success'] += 1
            results['splade_optimized']['latency'].append(splade_opt_latency)
        
        #  
        results['dense']['details'].append({
            'test_id': test['id'],
            'query': query,
            'success': dense_success,
            'latency': dense_latency
        })
        results['sparse']['details'].append({
            'test_id': test['id'],
            'query': query,
            'success': sparse_success,
            'latency': sparse_latency
        })
        if old_splade_retriever:
            results['splade_old']['details'].append({
                'test_id': test['id'],
                'query': query,
                'success': splade_old_success,
                'latency': splade_old_latency
            })
        if optimized_splade_retriever:
            results['splade_optimized']['details'].append({
                'test_id': test['id'],
                'query': query,
                'success': splade_opt_success,
                'latency': splade_opt_latency
            })
        
        # 
        print(f"\n[{test['id']}] {test['category']}")
        print(f"Query: {query}")
        print(f"Dense: {'' if dense_success else ''} ({dense_latency*1000:.1f}ms)")
        print(f"Sparse: {'' if sparse_success else ''} ({sparse_latency*1000:.1f}ms)")
        if old_splade_retriever:
            print(f"SPLADE (): {'' if splade_old_success else ''} ({splade_old_latency*1000:.1f}ms)")
        if optimized_splade_retriever:
            print(f"SPLADE (): {'' if splade_opt_success else ''} ({splade_opt_latency*1000:.1f}ms)")
    
    return results


def evaluate_criteria_tests(
    dense_retriever: MultiStageRetrieverV2,
    sparse_retriever: BM25SparseRetriever,
    old_splade_retriever: Optional[NaverSPLADEDBRetriever],
    optimized_splade_retriever: Optional[OptimizedSPLADEDBRetriever],
    test_cases: List[Dict]
) -> Dict:
    """  """
    results = {
        'dense': {'success': 0, 'total': 0, 'details': [], 'latency': []},
        'sparse': {'success': 0, 'total': 0, 'details': [], 'latency': []},
        'splade_old': {'success': 0, 'total': 0, 'details': [], 'latency': []},
        'splade_optimized': {'success': 0, 'total': 0, 'details': [], 'latency': []}
    }
    
    for test in test_cases:
        query = test['query']
        expected_item = test.get('expected_item')
        expected_category = test.get('expected_category')
        not_expected = test.get('not_expected')
        
        # Dense 
        try:
            start_time = time.time()
            dense_results = dense_retriever.search(query, top_k=5, debug=False)
            dense_latency = time.time() - start_time
            
            dense_success = False
            for r in dense_results['results'][:3]:
                content = r.get('content', '')
                metadata = r.get('source_info', {})
                
                if expected_item:
                    if expected_item in content:
                        if not_expected and not_expected in content:
                            continue
                        dense_success = True
                        break
                
                if expected_category:
                    if expected_category in content:
                        dense_success = True
                        break
        except Exception as e:
            print(f"    Dense  : {e}")
            dense_success = False
            dense_latency = 0.0
        
        # Sparse 
        try:
            start_time = time.time()
            sparse_results = sparse_retriever.search_criteria_bm25(query, top_k=5)
            sparse_latency = time.time() - start_time
            
            sparse_success = False
            for r in sparse_results[:3]:
                content = r.get('content', '')
                item = r.get('item', '')
                
                if expected_item:
                    if expected_item in content or expected_item in item:
                        if not_expected and not_expected in content:
                            continue
                        sparse_success = True
                        break
                
                if expected_category:
                    if expected_category in content:
                        sparse_success = True
                        break
        except Exception as e:
            print(f"    Sparse  : {e}")
            sparse_success = False
            sparse_latency = 0.0
        
        # SPLADE ( )
        splade_old_success = False
        splade_old_latency = 0.0
        if old_splade_retriever:
            try:
                start_time = time.time()
                splade_old_results = old_splade_retriever.search_criteria_splade(query, top_k=5)
                splade_old_latency = time.time() - start_time
                
                for r in splade_old_results[:3]:
                    content = r.get('content', '')
                    item = r.get('item', '')
                    
                    if expected_item:
                        if expected_item in content or expected_item in item:
                            if not_expected and not_expected in content:
                                continue
                            splade_old_success = True
                            break
                    
                    if expected_category:
                        if expected_category in content:
                            splade_old_success = True
                            break
            except Exception as e:
                print(f"    SPLADE ()  : {e}")
                splade_old_success = False
                splade_old_latency = 0.0
        
        # SPLADE ( )
        splade_opt_success = False
        splade_opt_latency = 0.0
        if optimized_splade_retriever:
            try:
                start_time = time.time()
                splade_opt_results = optimized_splade_retriever.search_criteria_splade_optimized(query, top_k=5)
                splade_opt_latency = time.time() - start_time
                
                for r in splade_opt_results[:3]:
                    content = r.get('content', '') or ''
                    item = r.get('item', '') or ''
                    
                    if expected_item:
                        if expected_item in content or expected_item in item:
                            if not_expected and not_expected in content:
                                continue
                            splade_opt_success = True
                            break
                    
                    if expected_category:
                        if expected_category in content:
                            splade_opt_success = True
                            break
            except Exception as e:
                print(f"    SPLADE ()  : {e}")
                splade_opt_success = False
                splade_opt_latency = 0.0
        
        #  
        results['dense']['total'] += 1
        results['sparse']['total'] += 1
        if dense_success:
            results['dense']['success'] += 1
        if sparse_success:
            results['sparse']['success'] += 1
        results['dense']['latency'].append(dense_latency)
        results['sparse']['latency'].append(sparse_latency)
        
        if old_splade_retriever:
            results['splade_old']['total'] += 1
            if splade_old_success:
                results['splade_old']['success'] += 1
            results['splade_old']['latency'].append(splade_old_latency)
        
        if optimized_splade_retriever:
            results['splade_optimized']['total'] += 1
            if splade_opt_success:
                results['splade_optimized']['success'] += 1
            results['splade_optimized']['latency'].append(splade_opt_latency)
        
        #  
        results['dense']['details'].append({
            'test_id': test['id'],
            'query': query,
            'success': dense_success,
            'latency': dense_latency
        })
        results['sparse']['details'].append({
            'test_id': test['id'],
            'query': query,
            'success': sparse_success,
            'latency': sparse_latency
        })
        if old_splade_retriever:
            results['splade_old']['details'].append({
                'test_id': test['id'],
                'query': query,
                'success': splade_old_success,
                'latency': splade_old_latency
            })
        if optimized_splade_retriever:
            results['splade_optimized']['details'].append({
                'test_id': test['id'],
                'query': query,
                'success': splade_opt_success,
                'latency': splade_opt_latency
            })
        
        # 
        print(f"\n[{test['id']}] {test['category']}")
        print(f"Query: {query}")
        print(f"Dense: {'' if dense_success else ''} ({dense_latency*1000:.1f}ms)")
        print(f"Sparse: {'' if sparse_success else ''} ({sparse_latency*1000:.1f}ms)")
        if old_splade_retriever:
            print(f"SPLADE (): {'' if splade_old_success else ''} ({splade_old_latency*1000:.1f}ms)")
        if optimized_splade_retriever:
            print(f"SPLADE (): {'' if splade_opt_success else ''} ({splade_opt_latency*1000:.1f}ms)")
    
    return results


def calculate_metrics(results: Dict) -> Dict:
    """  """
    metrics = {}
    
    for method, data in results.items():
        if data['total'] == 0:
            continue
        
        success_rate = (data['success'] / data['total']) * 100
        avg_latency = sum(data['latency']) / len(data['latency']) if data['latency'] else 0.0
        min_latency = min(data['latency']) if data['latency'] else 0.0
        max_latency = max(data['latency']) if data['latency'] else 0.0
        
        metrics[method] = {
            'success_rate': success_rate,
            'avg_latency_ms': avg_latency * 1000,
            'min_latency_ms': min_latency * 1000,
            'max_latency_ms': max_latency * 1000,
            'total': data['total'],
            'success': data['success']
        }
    
    return metrics


def main():
    """ """
    load_dotenv()
    
    # DB 
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'database': os.getenv('DB_NAME', 'ddoksori'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres')
    }
    
    # Retriever 
    print(" Retriever  ...")
    dense_retriever = MultiStageRetrieverV2(db_config)
    sparse_retriever = BM25SparseRetriever(db_config)
    
    # SPLADE Retriever  ( )
    old_splade_retriever = None
    try:
        import torch
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        old_splade_retriever = NaverSPLADEDBRetriever(db_config, device=device)
        old_splade_retriever.splade_retriever.load_model()
        print(" SPLADE ( )  ")
    except Exception as e:
        print(f"  SPLADE ( )  : {e}")
    
    # SPLADE Retriever  ( )
    optimized_splade_retriever = None
    try:
        optimized_splade_retriever = OptimizedSPLADEDBRetriever(db_config)
        print(" SPLADE ( )  ")
    except Exception as e:
        print(f"  SPLADE ( )  : {e}")
    
    #   
    script_dir = os.path.dirname(os.path.abspath(__file__))
    law_test_file = os.path.join(script_dir, 'test_cases_splade_law.json')
    criteria_test_file = os.path.join(script_dir, 'test_cases_splade_criteria.json')
    
    with open(law_test_file, 'r', encoding='utf-8') as f:
        law_tests = json.load(f)
    
    with open(criteria_test_file, 'r', encoding='utf-8') as f:
        criteria_tests = json.load(f)
    
    print("\n" + "=" * 80)
    print("SPLADE   ")
    print("=" * 80)
    
    #  
    print("\n\n===    ===")
    law_results = evaluate_law_tests(
        dense_retriever, sparse_retriever,
        old_splade_retriever, optimized_splade_retriever,
        law_tests
    )
    
    #  
    print("\n\n===    ===")
    criteria_results = evaluate_criteria_tests(
        dense_retriever, sparse_retriever,
        old_splade_retriever, optimized_splade_retriever,
        criteria_tests
    )
    
    #  
    law_metrics = calculate_metrics(law_results)
    criteria_metrics = calculate_metrics(criteria_results)
    
    #  
    print("\n\n" + "=" * 80)
    print(" ")
    print("=" * 80)
    
    print("\n :")
    for method in ['dense', 'sparse', 'splade_old', 'splade_optimized']:
        if method in law_metrics:
            m = law_metrics[method]
            print(f"  {method.upper()}: {m['success']}/{m['total']} ({m['success_rate']:.1f}%) | "
                  f" : {m['avg_latency_ms']:.1f}ms")
    
    print("\n :")
    for method in ['dense', 'sparse', 'splade_old', 'splade_optimized']:
        if method in criteria_metrics:
            m = criteria_metrics[method]
            print(f"  {method.upper()}: {m['success']}/{m['total']} ({m['success_rate']:.1f}%) | "
                  f" : {m['avg_latency_ms']:.1f}ms")
    
    #   
    if 'splade_old' in law_metrics and 'splade_optimized' in law_metrics:
        old_metrics = law_metrics['splade_old']
        opt_metrics = law_metrics['splade_optimized']
        
        speedup = old_metrics['avg_latency_ms'] / opt_metrics['avg_latency_ms'] if opt_metrics['avg_latency_ms'] > 0 else 0
        accuracy_improvement = opt_metrics['success_rate'] - old_metrics['success_rate']
        
        print("\n" + "=" * 80)
        print("   ( )")
        print("=" * 80)
        print(f" : {speedup:.2f} (: {old_metrics['avg_latency_ms']:.1f}ms → : {opt_metrics['avg_latency_ms']:.1f}ms)")
        print(f" : {accuracy_improvement:+.1f}% (: {old_metrics['success_rate']:.1f}% → : {opt_metrics['success_rate']:.1f}%)")
    
    #  
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_file = os.path.join(script_dir, f'splade_optimized_results_{timestamp}.json')
    
    results_summary = {
        'timestamp': timestamp,
        'law_metrics': law_metrics,
        'criteria_metrics': criteria_metrics,
        'law_results': law_results,
        'criteria_results': criteria_results
    }
    
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results_summary, f, ensure_ascii=False, indent=2)
    
    print(f"\n  : {results_file}")
    
    #  
    dense_retriever.close()
    if old_splade_retriever and old_splade_retriever.conn:
        old_splade_retriever.conn.close()
    if optimized_splade_retriever and optimized_splade_retriever.conn:
        optimized_splade_retriever.conn.close()


if __name__ == "__main__":
    main()
