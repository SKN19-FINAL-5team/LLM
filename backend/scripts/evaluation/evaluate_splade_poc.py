"""
SPLADE PoC 평가 스크립트
Dense Vector(KURE-v1) vs BM25 Sparse vs SPLADE 비교
"""

import json
import os
import sys
from typing import List, Dict, Optional
from dotenv import load_dotenv
from datetime import datetime

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.rag.multi_stage_retriever_v2 import MultiStageRetrieverV2
from scripts.splade.test_splade_bm25 import BM25SparseRetriever

# SPLADE는 선택적 (RunPod API 서버 또는 로컬 직접 실행)
SPLADE_AVAILABLE = False
NaverSPLADEDBRetriever = None
RemoteSPLADEDBRetriever = None

# 1. RunPod API 서버 방식 시도 (우선)
try:
    from scripts.splade.test_splade_remote import RemoteSPLADEDBRetriever
    import requests
    # API 서버 연결 확인
    api_url = os.getenv('SPLADE_API_URL', 'http://localhost:8001')
    try:
        response = requests.get(f"{api_url}/health", timeout=5)
        if response.status_code == 200:
            SPLADE_AVAILABLE = True
            print(f"✅ SPLADE API 서버 연결 성공 ({api_url})")
        else:
            print(f"⚠️  SPLADE API 서버 응답 오류 (상태 코드: {response.status_code})")
    except requests.exceptions.RequestException:
        print(f"⚠️  SPLADE API 서버 연결 실패 ({api_url})")
        print("   SSH 터널이 연결되어 있는지 확인하세요.")
        print("   또는 로컬 직접 실행 방식을 사용하세요.")
except ImportError:
    print("⚠️  RemoteSPLADEDBRetriever 모듈을 찾을 수 없습니다.")

# 2. 로컬 직접 실행 방식 (API 서버 실패 시)
if not SPLADE_AVAILABLE:
    try:
        # torch 버전 확인 (로컬 환경 체크)
        import torch
        torch_version = torch.__version__
        try:
            major, minor = map(int, torch_version.split('.')[:2])
            torch_too_old = major < 2 or (major == 2 and minor < 6)
        except:
            torch_too_old = False
        
        if torch_too_old:
            print(f"⚠️  torch 버전이 2.6 미만입니다 (현재: {torch_version})")
            print("   로컬 환경에서는 SPLADE를 사용할 수 없습니다.")
            print("   해결 방법:")
            print("     1. RunPod API 서버 사용 (권장)")
            print("     2. torch 업그레이드: pip install --upgrade torch>=2.6")
            print("   SPLADE 평가는 건너뜁니다. Dense와 BM25만 평가합니다.")
            SPLADE_AVAILABLE = False
        else:
            from scripts.splade.test_splade_naver import NaverSPLADEDBRetriever
            SPLADE_AVAILABLE = True
            print("✅ SPLADE 로컬 직접 실행 모드 사용")
    except ImportError as e:
        print(f"⚠️  SPLADE 로컬 모듈 로드 실패: {e}")
        print("   SPLADE 평가는 건너뜁니다.")
        SPLADE_AVAILABLE = False
    except Exception as e:
        error_str = str(e)
        # torch 버전 문제인 경우
        if "torch.load" in error_str or "CVE-2025-32434" in error_str or "torch>=2.6" in error_str:
            print(f"⚠️  torch 버전 문제로 SPLADE를 사용할 수 없습니다: {error_str}")
            print("   로컬 환경에서는 SPLADE를 건너뜁니다.")
            print("   해결 방법:")
            print("     1. RunPod API 서버 사용 (권장)")
            print("     2. torch 업그레이드: pip install --upgrade torch>=2.6")
            print("   Dense와 BM25만 평가합니다.")
            SPLADE_AVAILABLE = False
        else:
            print(f"⚠️  SPLADE 로컬 모듈 로드 실패: {e}")
            print("   SPLADE 평가는 건너뜁니다.")
            SPLADE_AVAILABLE = False


def evaluate_law_tests(
    dense_retriever: MultiStageRetrieverV2,
    sparse_retriever: BM25SparseRetriever,
    test_cases: List[Dict],
    splade_retriever = None  # NaverSPLADEDBRetriever 또는 RemoteSPLADEDBRetriever
) -> Dict:
    """법령 테스트 평가"""
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
        
        # Dense 검색
        try:
            dense_results = dense_retriever.search(query, top_k=5, debug=False)
            dense_success = False
            
            if expected_article:
                # 단일 조문 매칭
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
                # 다중 조문 매칭 (하나라도 매칭되면 성공)
                for r in dense_results['results'][:3]:
                    content = r.get('content', '')
                    for article in expected_articles:
                        if article in content:
                            dense_success = True
                            break
                    if dense_success:
                        break
            elif expected_law:
                # 법령명만 매칭
                for r in dense_results['results'][:3]:
                    content = r.get('content', '')
                    metadata = r.get('source_info', {})
                    law_name = metadata.get('law_name', '') if isinstance(metadata, dict) else ''
                    
                    if expected_law in law_name or expected_law in content:
                        dense_success = True
                        break
        except Exception as e:
            print(f"  ⚠️  Dense 검색 오류: {e}")
            dense_success = False
        
        # Sparse 검색
        try:
            sparse_results = sparse_retriever.search_law_bm25(query, top_k=5)
            sparse_success = False
            
            if expected_article:
                # 단일 조문 매칭
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
                # 다중 조문 매칭
                for r in sparse_results[:3]:
                    content = r.get('content', '')
                    for article in expected_articles:
                        if article in content:
                            sparse_success = True
                            break
                    if sparse_success:
                        break
            elif expected_law:
                # 법령명만 매칭
                for r in sparse_results[:3]:
                    content = r.get('content', '')
                    law_name = r.get('law_name', '')
                    
                    if expected_law in law_name or expected_law in content:
                        sparse_success = True
                        break
        except Exception as e:
            print(f"  ⚠️  Sparse 검색 오류: {e}")
            sparse_success = False
        
        # SPLADE 검색
        splade_success = False
        if splade_retriever:
            try:
                splade_results = splade_retriever.search_law_splade(query, top_k=5)
                
                # 결과가 비어있으면 실패로 간주 (연결 실패 등)
                if not splade_results:
                    splade_success = False
                elif expected_article:
                    # 단일 조문 매칭
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
                    # 다중 조문 매칭
                    for r in splade_results[:3]:
                        content = r.get('content', '')
                        for article in expected_articles:
                            if article in content:
                                splade_success = True
                                break
                        if splade_success:
                            break
                elif expected_law:
                    # 법령명만 매칭
                    for r in splade_results[:3]:
                        content = r.get('content', '')
                        law_name = r.get('law_name', '')
                        
                        if expected_law in law_name or expected_law in content:
                            splade_success = True
                            break
            except Exception as e:
                print(f"  ⚠️  SPLADE 검색 오류: {e}")
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
        print(f"Dense: {'✅' if dense_success else '❌'}")
        print(f"Sparse: {'✅' if sparse_success else '❌'}")
        if splade_retriever:
            print(f"SPLADE: {'✅' if splade_success else '❌'}")
    
    return results


def evaluate_criteria_tests(
    dense_retriever: MultiStageRetrieverV2,
    sparse_retriever: BM25SparseRetriever,
    test_cases: List[Dict],
    splade_retriever = None  # NaverSPLADEDBRetriever 또는 RemoteSPLADEDBRetriever
) -> Dict:
    """기준 테스트 평가"""
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
        
        # Dense 검색
        try:
            dense_results = dense_retriever.search(query, top_k=5, debug=False)
            dense_success = False
            
            for r in dense_results['results'][:3]:
                content = r.get('content', '')
                metadata = r.get('source_info', {})
                
                # 품목명 매칭
                if expected_item:
                    if expected_item in content:
                        # 부정 키워드 체크
                        if not_expected and not_expected in content:
                            continue
                        dense_success = True
                        break
                
                # 카테고리 매칭
                if expected_category:
                    if expected_category in content:
                        dense_success = True
                        break
        except Exception as e:
            print(f"  ⚠️  Dense 검색 오류: {e}")
            dense_success = False
        
        # Sparse 검색
        try:
            sparse_results = sparse_retriever.search_criteria_bm25(query, top_k=5)
            sparse_success = False
            
            for r in sparse_results[:3]:
                content = r.get('content', '')
                item = r.get('item', '')
                
                # 품목명 매칭
                if expected_item:
                    if expected_item in content or expected_item in item:
                        # 부정 키워드 체크
                        if not_expected and not_expected in content:
                            continue
                        sparse_success = True
                        break
                
                # 카테고리 매칭
                if expected_category:
                    if expected_category in content:
                        sparse_success = True
                        break
        except Exception as e:
            print(f"  ⚠️  Sparse 검색 오류: {e}")
            sparse_success = False
        
        # SPLADE 검색
        splade_success = False
        if splade_retriever:
            try:
                splade_results = splade_retriever.search_criteria_splade(query, top_k=5)
                
                for r in splade_results[:3]:
                    content = r.get('content', '')
                    item = r.get('item', '')
                    
                    # 품목명 매칭
                    if expected_item:
                        if expected_item in content or expected_item in item:
                            # 부정 키워드 체크
                            if not_expected and not_expected in content:
                                continue
                            splade_success = True
                            break
                    
                    # 카테고리 매칭
                    if expected_category:
                        if expected_category in content:
                            splade_success = True
                            break
            except Exception as e:
                print(f"  ⚠️  SPLADE 검색 오류: {e}")
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
        print(f"Dense: {'✅' if dense_success else '❌'}")
        print(f"Sparse: {'✅' if sparse_success else '❌'}")
        if splade_retriever:
            print(f"SPLADE: {'✅' if splade_success else '❌'}")
    
    return results


def main():
    load_dotenv()
    
    # DB 설정
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'database': os.getenv('DB_NAME', 'ddoksori'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres')
    }
    
    # Retriever 초기화
    print("🔧 Retriever 초기화 중...")
    dense_retriever = MultiStageRetrieverV2(db_config)
    sparse_retriever = BM25SparseRetriever(db_config)
    
    # SPLADE Retriever 초기화 (선택적)
    splade_retriever = None
    if SPLADE_AVAILABLE:
        try:
            # RunPod API 서버 방식 우선 사용
            if RemoteSPLADEDBRetriever is not None:
                api_url = os.getenv('SPLADE_API_URL', 'http://localhost:8001')
                print(f"  SPLADE Retriever 초기화 시도 (RunPod API 서버: {api_url})...")
                try:
                    splade_retriever = RemoteSPLADEDBRetriever(db_config, api_url=api_url)
                    print(f"  ✅ SPLADE Retriever 초기화 성공 (RunPod API 서버 사용)")
                except ConnectionError as e:
                    print(f"  ⚠️  API 서버 연결 실패: {e}")
                    print(f"  💡 로컬 직접 실행 모드로 전환 시도...")
                    # 로컬 모드로 전환
                    splade_retriever = None  # 아래 로컬 모드 코드로 진행
            
            # 로컬 직접 실행 방식 (API 서버 실패 시 또는 처음부터)
            if splade_retriever is None:
                if NaverSPLADEDBRetriever is not None:
                    import torch
                    use_gpu = torch.cuda.is_available()
                    device = 'cuda' if use_gpu else 'cpu'
                    print(f"  SPLADE Retriever 초기화 시도 (로컬 직접 실행)...")
                    print(f"  GPU 사용 가능: {use_gpu}, Device: {device}")
                    
                    # torch 버전 재확인
                    torch_version = torch.__version__
                    try:
                        major, minor = map(int, torch_version.split('.')[:2])
                        if major < 2 or (major == 2 and minor < 6):
                            print(f"  ⚠️  torch 버전이 2.6 미만입니다 (현재: {torch_version})")
                            print("  SPLADE 모델 로드가 실패할 수 있습니다.")
                            print("  시도는 하지만 실패 시 자동으로 건너뜁니다.")
                    except:
                        pass
                    
                    try:
                        splade_retriever = NaverSPLADEDBRetriever(db_config, device=device)
                        # 모델 로드 시도 (실패하면 None 반환)
                        splade_retriever.splade_retriever.load_model()
                        print(f"  ✅ SPLADE Retriever 초기화 성공 (로컬, device: {device})")
                    except RuntimeError as e:
                        if "torch 버전" in str(e) or "torch>=2.6" in str(e):
                            print(f"  ⚠️  torch 버전 문제로 SPLADE를 사용할 수 없습니다.")
                            print("  Dense와 BM25만 평가합니다.")
                            splade_retriever = None
                        else:
                            raise
                else:
                    # RemoteSPLADEDBRetriever도 없고 NaverSPLADEDBRetriever도 없는 경우
                    if splade_retriever is None:
                        raise RuntimeError("SPLADE Retriever를 사용할 수 없습니다. (모듈을 찾을 수 없음)")
        except Exception as e:
            print(f"  ⚠️  SPLADE Retriever 초기화 실패: {e}")
            print("  SPLADE 평가는 건너뜁니다. Dense와 BM25만 평가합니다.")
            splade_retriever = None
    else:
        print("  ⚠️  SPLADE 모듈 사용 불가")
        print("     Dense와 BM25만 평가합니다.")
        print("     SPLADE를 사용하려면:")
        print("     1. RunPod에 SPLADE API 서버 실행 후 SSH 터널 연결 (권장)")
        print("     2. 또는 로컬에서 torch>=2.6으로 업그레이드")
    
    # 테스트 케이스 로드
    script_dir = os.path.dirname(os.path.abspath(__file__))
    law_test_file = os.path.join(script_dir, 'test_cases_splade_law.json')
    criteria_test_file = os.path.join(script_dir, 'test_cases_splade_criteria.json')
    
    with open(law_test_file, 'r', encoding='utf-8') as f:
        law_tests = json.load(f)
    
    with open(criteria_test_file, 'r', encoding='utf-8') as f:
        criteria_tests = json.load(f)
    
    print("=" * 80)
    if splade_retriever:
        print("SPLADE PoC 평가: Dense vs BM25 vs SPLADE 비교")
    else:
        print("SPLADE PoC 평가: Dense vs BM25 비교 (SPLADE 접근 권한 없음)")
    print("=" * 80)
    
    # 법령 테스트
    print("\n\n=== 법령 검색 평가 ===")
    law_results = evaluate_law_tests(dense_retriever, sparse_retriever, law_tests, splade_retriever)
    
    # 기준 테스트
    print("\n\n=== 기준 검색 평가 ===")
    criteria_results = evaluate_criteria_tests(dense_retriever, sparse_retriever, criteria_tests, splade_retriever)
    
    # 결과 출력
    print("\n\n" + "=" * 80)
    print("최종 결과")
    print("=" * 80)
    
    print("\n법령 검색:")
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
        print(f"  SPLADE: 사용 불가 (torch 버전 또는 API 서버 연결 필요)")
    
    print("\n기준 검색:")
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
        print(f"  SPLADE: 사용 불가 (torch 버전 또는 API 서버 연결 필요)")
    
    # 전체 통계
    total_dense_success = law_results['dense']['success'] + criteria_results['dense']['success']
    total_dense_total = law_results['dense']['total'] + criteria_results['dense']['total']
    total_sparse_success = law_results['sparse']['success'] + criteria_results['sparse']['success']
    total_sparse_total = law_results['sparse']['total'] + criteria_results['sparse']['total']
    
    print("\n전체:")
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
        print(f"  SPLADE: 사용 불가 (torch 버전 또는 API 서버 연결 필요)")
    
    # 결과 저장
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
    
    # SPLADE 결과 추가 (있는 경우)
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
    
    print(f"\n✅ 결과 저장: {results_file}")
    
    # 리소스 정리
    dense_retriever.close()


if __name__ == "__main__":
    main()
