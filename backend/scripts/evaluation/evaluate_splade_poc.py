"""
SPLADE PoC  
Dense Vector(KURE-v1) vs BM25 Sparse vs SPLADE 
"""

import json
import os
import sys
from typing import List, Dict, Optional
from dotenv import load_dotenv
from datetime import datetime

#    
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.rag.multi_stage_retriever_v2 import MultiStageRetrieverV2
from scripts.splade.test_splade_bm25 import BM25SparseRetriever

# SPLADE  (RunPod API     )
SPLADE_AVAILABLE = False
NaverSPLADEDBRetriever = None
RemoteSPLADEDBRetriever = None

# 1. RunPod API    ()
try:
    from scripts.splade.test_splade_remote import RemoteSPLADEDBRetriever
    import requests
    # API   
    api_url = os.getenv('SPLADE_API_URL', 'http://localhost:8001')
    try:
        response = requests.get(f"{api_url}/health", timeout=5)
        if response.status_code == 200:
            SPLADE_AVAILABLE = True
            print(f" SPLADE API    ({api_url})")
        else:
            print(f"  SPLADE API    ( : {response.status_code})")
    except requests.exceptions.RequestException:
        print(f"  SPLADE API    ({api_url})")
        print("   SSH    .")
        print("        .")
except ImportError:
    print("  RemoteSPLADEDBRetriever    .")

# 2.     (API   )
if not SPLADE_AVAILABLE:
    try:
        # torch   (  )
        import torch
        torch_version = torch.__version__
        try:
            major, minor = map(int, torch_version.split('.')[:2])
            torch_too_old = major < 2 or (major == 2 and minor < 6)
        except:
            torch_too_old = False
        
        if torch_too_old:
            print(f"  torch  2.6  (: {torch_version})")
            print("     SPLADE   .")
            print("    :")
            print("     1. RunPod API   ()")
            print("     2. torch : pip install --upgrade torch>=2.6")
            print("   SPLADE  . Dense BM25 .")
            SPLADE_AVAILABLE = False
        else:
            from scripts.splade.test_splade_naver import NaverSPLADEDBRetriever
            SPLADE_AVAILABLE = True
            print(" SPLADE     ")
    except ImportError as e:
        print(f"  SPLADE    : {e}")
        print("   SPLADE  .")
        SPLADE_AVAILABLE = False
    except Exception as e:
        error_str = str(e)
        # torch   
        if "torch.load" in error_str or "CVE-2025-32434" in error_str or "torch>=2.6" in error_str:
            print(f"  torch   SPLADE   : {error_str}")
            print("     SPLADE .")
            print("    :")
            print("     1. RunPod API   ()")
            print("     2. torch : pip install --upgrade torch>=2.6")
            print("   Dense BM25 .")
            SPLADE_AVAILABLE = False
        else:
            print(f"  SPLADE    : {e}")
            print("   SPLADE  .")
            SPLADE_AVAILABLE = False


def evaluate_law_tests(
    dense_retriever: MultiStageRetrieverV2,
    sparse_retriever: BM25SparseRetriever,
    test_cases: List[Dict],
    splade_retriever = None  # NaverSPLADEDBRetriever  RemoteSPLADEDBRetriever
) -> Dict:
    """  """
    results = {
        'dense': {'success': 0, 'total': 0, 'details': []},
        'sparse': {'success': 0, 'total': 0, 'details': []}
    }
    if splade_retriever:
        results['splade'] = {'success': 0, 'total': 0, 'details': []}
    
    for test in test_cases:
        query = test['query']
        expected_article = test.get('expected_article')
        expected_articles = test.get('expected_articles', [])
        expected_law = test.get('expected_law')
        
        # Dense 
        try:
            dense_results = dense_retriever.search(query, top_k=5, debug=False)
            dense_success = False
            
            if expected_article:
                #   
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
                #    (  )
                for r in dense_results['results'][:3]:
                    content = r.get('content', '')
                    for article in expected_articles:
                        if article in content:
                            dense_success = True
                            break
                    if dense_success:
                        break
            elif expected_law:
                #  
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
        
        # Sparse 
        try:
            sparse_results = sparse_retriever.search_law_bm25(query, top_k=5)
            sparse_success = False
            
            if expected_article:
                #   
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
                #   
                for r in sparse_results[:3]:
                    content = r.get('content', '')
                    for article in expected_articles:
                        if article in content:
                            sparse_success = True
                            break
                    if sparse_success:
                        break
            elif expected_law:
                #  
                for r in sparse_results[:3]:
                    content = r.get('content', '')
                    law_name = r.get('law_name', '')
                    
                    if expected_law in law_name or expected_law in content:
                        sparse_success = True
                        break
        except Exception as e:
            print(f"    Sparse  : {e}")
            sparse_success = False
        
        # SPLADE 
        splade_success = False
        if splade_retriever:
            try:
                splade_results = splade_retriever.search_law_splade(query, top_k=5)
                
                #     (  )
                if not splade_results:
                    splade_success = False
                elif expected_article:
                    #   
                    for r in splade_results[:3]:
                        content = r.get('content', '')
                        law_name = r.get('law_name', '')
                        
                        if expected_article in content:
                            if expected_law:
                                if expected_law in law_name or expected_law in content:
                                    splade_success = True
                                    break
                            else:
                                splade_success = True
                                break
                elif expected_articles:
                    #   
                    for r in splade_results[:3]:
                        content = r.get('content', '')
                        for article in expected_articles:
                            if article in content:
                                splade_success = True
                                break
                        if splade_success:
                            break
                elif expected_law:
                    #  
                    for r in splade_results[:3]:
                        content = r.get('content', '')
                        law_name = r.get('law_name', '')
                        
                        if expected_law in law_name or expected_law in content:
                            splade_success = True
                            break
            except Exception as e:
                print(f"    SPLADE  : {e}")
                splade_success = False
        
        results['dense']['total'] += 1
        results['sparse']['total'] += 1
        if dense_success:
            results['dense']['success'] += 1
        if sparse_success:
            results['sparse']['success'] += 1
        
        if splade_retriever:
            results['splade']['total'] += 1
            if splade_success:
                results['splade']['success'] += 1
            results['splade']['details'].append({
                'test_id': test['id'],
                'query': query,
                'success': splade_success
            })
        
        results['dense']['details'].append({
            'test_id': test['id'],
            'query': query,
            'success': dense_success
        })
        results['sparse']['details'].append({
            'test_id': test['id'],
            'query': query,
            'success': sparse_success
        })
        
        print(f"\n[{test['id']}] {test['category']}")
        print(f"Query: {query}")
        print(f"Dense: {'' if dense_success else ''}")
        print(f"Sparse: {'' if sparse_success else ''}")
        if splade_retriever:
            print(f"SPLADE: {'' if splade_success else ''}")
    
    return results


def evaluate_criteria_tests(
    dense_retriever: MultiStageRetrieverV2,
    sparse_retriever: BM25SparseRetriever,
    test_cases: List[Dict],
    splade_retriever = None  # NaverSPLADEDBRetriever  RemoteSPLADEDBRetriever
) -> Dict:
    """  """
    results = {
        'dense': {'success': 0, 'total': 0, 'details': []},
        'sparse': {'success': 0, 'total': 0, 'details': []}
    }
    if splade_retriever:
        results['splade'] = {'success': 0, 'total': 0, 'details': []}
    
    for test in test_cases:
        query = test['query']
        expected_item = test.get('expected_item')
        expected_category = test.get('expected_category')
        not_expected = test.get('not_expected')
        
        # Dense 
        try:
            dense_results = dense_retriever.search(query, top_k=5, debug=False)
            dense_success = False
            
            for r in dense_results['results'][:3]:
                content = r.get('content', '')
                metadata = r.get('source_info', {})
                
                #  
                if expected_item:
                    if expected_item in content:
                        #   
                        if not_expected and not_expected in content:
                            continue
                        dense_success = True
                        break
                
                #  
                if expected_category:
                    if expected_category in content:
                        dense_success = True
                        break
        except Exception as e:
            print(f"    Dense  : {e}")
            dense_success = False
        
        # Sparse 
        try:
            sparse_results = sparse_retriever.search_criteria_bm25(query, top_k=5)
            sparse_success = False
            
            for r in sparse_results[:3]:
                content = r.get('content', '')
                item = r.get('item', '')
                
                #  
                if expected_item:
                    if expected_item in content or expected_item in item:
                        #   
                        if not_expected and not_expected in content:
                            continue
                        sparse_success = True
                        break
                
                #  
                if expected_category:
                    if expected_category in content:
                        sparse_success = True
                        break
        except Exception as e:
            print(f"    Sparse  : {e}")
            sparse_success = False
        
        # SPLADE 
        splade_success = False
        if splade_retriever:
            try:
                splade_results = splade_retriever.search_criteria_splade(query, top_k=5)
                
                for r in splade_results[:3]:
                    content = r.get('content', '')
                    item = r.get('item', '')
                    
                    #  
                    if expected_item:
                        if expected_item in content or expected_item in item:
                            #   
                            if not_expected and not_expected in content:
                                continue
                            splade_success = True
                            break
                    
                    #  
                    if expected_category:
                        if expected_category in content:
                            splade_success = True
                            break
            except Exception as e:
                print(f"    SPLADE  : {e}")
                splade_success = False
        
        results['dense']['total'] += 1
        results['sparse']['total'] += 1
        if dense_success:
            results['dense']['success'] += 1
        if sparse_success:
            results['sparse']['success'] += 1
        
        if splade_retriever:
            results['splade']['total'] += 1
            if splade_success:
                results['splade']['success'] += 1
            results['splade']['details'].append({
                'test_id': test['id'],
                'query': query,
                'success': splade_success
            })
        
        results['dense']['details'].append({
            'test_id': test['id'],
            'query': query,
            'success': dense_success
        })
        results['sparse']['details'].append({
            'test_id': test['id'],
            'query': query,
            'success': sparse_success
        })
        
        print(f"\n[{test['id']}] {test['category']}")
        print(f"Query: {query}")
        print(f"Dense: {'' if dense_success else ''}")
        print(f"Sparse: {'' if sparse_success else ''}")
        if splade_retriever:
            print(f"SPLADE: {'' if splade_success else ''}")
    
    return results


def main():
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
    
    # SPLADE Retriever  ()
    splade_retriever = None
    if SPLADE_AVAILABLE:
        try:
            # RunPod API    
            if RemoteSPLADEDBRetriever is not None:
                api_url = os.getenv('SPLADE_API_URL', 'http://localhost:8001')
                print(f"  SPLADE Retriever   (RunPod API : {api_url})...")
                try:
                    splade_retriever = RemoteSPLADEDBRetriever(db_config, api_url=api_url)
                    print(f"   SPLADE Retriever   (RunPod API  )")
                except ConnectionError as e:
                    print(f"    API   : {e}")
                    print(f"        ...")
                    #   
                    splade_retriever = None  #     
            
            #     (API     )
            if splade_retriever is None:
                if NaverSPLADEDBRetriever is not None:
                    import torch
                    use_gpu = torch.cuda.is_available()
                    device = 'cuda' if use_gpu else 'cpu'
                    print(f"  SPLADE Retriever   (  )...")
                    print(f"  GPU  : {use_gpu}, Device: {device}")
                    
                    # torch  
                    torch_version = torch.__version__
                    try:
                        major, minor = map(int, torch_version.split('.')[:2])
                        if major < 2 or (major == 2 and minor < 6):
                            print(f"    torch  2.6  (: {torch_version})")
                            print("  SPLADE     .")
                            print("       .")
                    except:
                        pass
                    
                    try:
                        splade_retriever = NaverSPLADEDBRetriever(db_config, device=device)
                        #    ( None )
                        splade_retriever.splade_retriever.load_model()
                        print(f"   SPLADE Retriever   (, device: {device})")
                    except RuntimeError as e:
                        if "torch " in str(e) or "torch>=2.6" in str(e):
                            print(f"    torch   SPLADE   .")
                            print("  Dense BM25 .")
                            splade_retriever = None
                        else:
                            raise
                else:
                    # RemoteSPLADEDBRetriever  NaverSPLADEDBRetriever  
                    if splade_retriever is None:
                        raise RuntimeError("SPLADE Retriever   . (   )")
        except Exception as e:
            print(f"    SPLADE Retriever  : {e}")
            print("  SPLADE  . Dense BM25 .")
            splade_retriever = None
    else:
        print("    SPLADE   ")
        print("     Dense BM25 .")
        print("     SPLADE :")
        print("     1. RunPod SPLADE API    SSH   ()")
        print("     2.   torch>=2.6 ")
    
    #   
    script_dir = os.path.dirname(os.path.abspath(__file__))
    law_test_file = os.path.join(script_dir, 'test_cases_splade_law.json')
    criteria_test_file = os.path.join(script_dir, 'test_cases_splade_criteria.json')
    
    with open(law_test_file, 'r', encoding='utf-8') as f:
        law_tests = json.load(f)
    
    with open(criteria_test_file, 'r', encoding='utf-8') as f:
        criteria_tests = json.load(f)
    
    print("=" * 80)
    if splade_retriever:
        print("SPLADE PoC : Dense vs BM25 vs SPLADE ")
    else:
        print("SPLADE PoC : Dense vs BM25  (SPLADE   )")
    print("=" * 80)
    
    #  
    print("\n\n===    ===")
    law_results = evaluate_law_tests(dense_retriever, sparse_retriever, law_tests, splade_retriever)
    
    #  
    print("\n\n===    ===")
    criteria_results = evaluate_criteria_tests(dense_retriever, sparse_retriever, criteria_tests, splade_retriever)
    
    #  
    print("\n\n" + "=" * 80)
    print(" ")
    print("=" * 80)
    
    print("\n :")
    methods = ['dense', 'sparse']
    if splade_retriever and 'splade' in law_results:
        methods.append('splade')
    for method in methods:
        if method in law_results:
            success = law_results[method]['success']
            total = law_results[method]['total']
            rate = (success / total * 100) if total > 0 else 0
            print(f"  {method.upper()}: {success}/{total} ({rate:.1f}%)")
    if not (splade_retriever and 'splade' in law_results):
        print(f"  SPLADE:   (torch   API   )")
    
    print("\n :")
    methods = ['dense', 'sparse']
    if splade_retriever and 'splade' in criteria_results:
        methods.append('splade')
    for method in methods:
        if method in criteria_results:
            success = criteria_results[method]['success']
            total = criteria_results[method]['total']
            rate = (success / total * 100) if total > 0 else 0
            print(f"  {method.upper()}: {success}/{total} ({rate:.1f}%)")
    if not (splade_retriever and 'splade' in criteria_results):
        print(f"  SPLADE:   (torch   API   )")
    
    #  
    total_dense_success = law_results['dense']['success'] + criteria_results['dense']['success']
    total_dense_total = law_results['dense']['total'] + criteria_results['dense']['total']
    total_sparse_success = law_results['sparse']['success'] + criteria_results['sparse']['success']
    total_sparse_total = law_results['sparse']['total'] + criteria_results['sparse']['total']
    
    print("\n:")
    dense_rate = (total_dense_success / total_dense_total * 100) if total_dense_total > 0 else 0
    sparse_rate = (total_sparse_success / total_sparse_total * 100) if total_sparse_total > 0 else 0
    print(f"  DENSE: {total_dense_success}/{total_dense_total} ({dense_rate:.1f}%)")
    print(f"  SPARSE: {total_sparse_success}/{total_sparse_total} ({sparse_rate:.1f}%)")
    
    if splade_retriever and 'splade' in law_results and 'splade' in criteria_results:
        total_splade_success = law_results['splade']['success'] + criteria_results['splade']['success']
        total_splade_total = law_results['splade']['total'] + criteria_results['splade']['total']
        splade_rate = (total_splade_success / total_splade_total * 100) if total_splade_total > 0 else 0
        print(f"  SPLADE: {total_splade_success}/{total_splade_total} ({splade_rate:.1f}%)")
    else:
        print(f"  SPLADE:   (torch   API   )")
    
    #  
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_file = os.path.join(script_dir, f'splade_poc_results_{timestamp}.json')
    
    results_summary = {
        'timestamp': timestamp,
        'splade_available': splade_retriever is not None,
        'law_results': {
            'dense': {
                'success': law_results['dense']['success'],
                'total': law_results['dense']['total'],
                'rate': (law_results['dense']['success'] / law_results['dense']['total'] * 100) if law_results['dense']['total'] > 0 else 0
            },
            'sparse': {
                'success': law_results['sparse']['success'],
                'total': law_results['sparse']['total'],
                'rate': (law_results['sparse']['success'] / law_results['sparse']['total'] * 100) if law_results['sparse']['total'] > 0 else 0
            }
        },
        'criteria_results': {
            'dense': {
                'success': criteria_results['dense']['success'],
                'total': criteria_results['dense']['total'],
                'rate': (criteria_results['dense']['success'] / criteria_results['dense']['total'] * 100) if criteria_results['dense']['total'] > 0 else 0
            },
            'sparse': {
                'success': criteria_results['sparse']['success'],
                'total': criteria_results['sparse']['total'],
                'rate': (criteria_results['sparse']['success'] / criteria_results['sparse']['total'] * 100) if criteria_results['sparse']['total'] > 0 else 0
            }
        },
        'overall': {
            'dense': {
                'success': total_dense_success,
                'total': total_dense_total,
                'rate': dense_rate
            },
            'sparse': {
                'success': total_sparse_success,
                'total': total_sparse_total,
                'rate': sparse_rate
            }
        },
        'details': {
            'law': {
                'dense': law_results['dense']['details'],
                'sparse': law_results['sparse']['details']
            },
            'criteria': {
                'dense': criteria_results['dense']['details'],
                'sparse': criteria_results['sparse']['details']
            }
        }
    }
    
    # SPLADE   ( )
    if splade_retriever and 'splade' in law_results:
        results_summary['law_results']['splade'] = {
            'success': law_results['splade']['success'],
            'total': law_results['splade']['total'],
            'rate': (law_results['splade']['success'] / law_results['splade']['total'] * 100) if law_results['splade']['total'] > 0 else 0
        }
        results_summary['details']['law']['splade'] = law_results['splade']['details']
    
    if splade_retriever and 'splade' in criteria_results:
        results_summary['criteria_results']['splade'] = {
            'success': criteria_results['splade']['success'],
            'total': criteria_results['splade']['total'],
            'rate': (criteria_results['splade']['success'] / criteria_results['splade']['total'] * 100) if criteria_results['splade']['total'] > 0 else 0
        }
        results_summary['details']['criteria']['splade'] = criteria_results['splade']['details']
        
        total_splade_success = law_results['splade']['success'] + criteria_results['splade']['success']
        total_splade_total = law_results['splade']['total'] + criteria_results['splade']['total']
        splade_rate = (total_splade_success / total_splade_total * 100) if total_splade_total > 0 else 0
        results_summary['overall']['splade'] = {
            'success': total_splade_success,
            'total': total_splade_total,
            'rate': splade_rate
        }
    
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results_summary, f, ensure_ascii=False, indent=2)
    
    print(f"\n  : {results_file}")
    
    #  
    dense_retriever.close()


if __name__ == "__main__":
    main()
