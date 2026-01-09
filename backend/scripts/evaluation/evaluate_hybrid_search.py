#!/usr/bin/env python3
"""
하이브리드 검색 시스템 평가 스크립트

간단한 테스트 쿼리를 사용하여 검색 품질 평가
"""

import sys
from pathlib import Path
import os
import time

sys.path.append(str(Path(__file__).parent.parent / 'app'))

from dotenv import load_dotenv

# 환경 변수 로드
backend_dir = Path(__file__).parent.parent
env_file = backend_dir / '.env'
if env_file.exists():
    load_dotenv(env_file)

# DB 연결 정보
DB_CONFIG = {
    'dbname': os.getenv('POSTGRES_DB', 'ddoksori'),
    'user': os.getenv('POSTGRES_USER', 'maroco'),
    'password': os.getenv('POSTGRES_PASSWORD', ''),
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': os.getenv('POSTGRES_PORT', '5432')
}

# 테스트 쿼리 샘플
TEST_QUERIES = [
    {
        'query': '민법 제750조는 무엇인가요?',
        'expected_type': 'law',
        'description': '법령 조문 정확 매칭 테스트'
    },
    {
        'query': '냉장고가 고장났는데 환불 받을 수 있나요?',
        'expected_type': 'criteria',
        'description': '품목별 기준 검색 테스트'
    },
    {
        'query': '온라인 쇼핑몰에서 옷을 샀는데 불량품이었어요. 어떻게 해야 하나요?',
        'expected_type': 'case',
        'description': '실무 사례 검색 테스트'
    },
    {
        'query': '전자상거래법에서 청약철회는 언제까지 가능한가요?',
        'expected_type': 'law',
        'description': '법령 키워드 검색 테스트'
    },
    {
        'query': '세탁기 수리는 몇 번까지 무상으로 받을 수 있나요?',
        'expected_type': 'criteria',
        'description': '보증 기준 검색 테스트'
    }
]


def evaluate_single_query(retriever, test_case: dict, debug: bool = False) -> dict:
    """단일 쿼리 평가"""
    query = test_case['query']
    expected_type = test_case['expected_type']
    
    print(f"\n{'='*60}")
    print(f"Query: {query}")
    print(f"Expected Type: {expected_type}")
    print(f"Description: {test_case['description']}")
    print(f"{'='*60}")
    
    # 검색 실행 및 시간 측정
    start_time = time.time()
    results = retriever.search(query=query, top_k=5, debug=debug)
    elapsed_time = time.time() - start_time
    
    # 결과 분석
    total_results = len(results['results'])
    doc_types = [r['doc_type'] for r in results['results']]
    top_score = results['results'][0]['score'] if total_results > 0 else 0
    
    # 예상 타입이 상위 결과에 있는지 확인
    has_expected_type = expected_type in doc_types[:3] if total_results >= 3 else expected_type in doc_types
    
    print(f"\n📊 Results:")
    print(f"  - Total: {total_results}")
    print(f"  - Query Type: {results['query_type']}")
    print(f"  - Top Score: {top_score:.4f}")
    print(f"  - Search Time: {elapsed_time:.2f}s")
    print(f"  - Doc Types Distribution: {dict((dt, doc_types.count(dt)) for dt in set(doc_types))}")
    print(f"  - Has Expected Type in Top-3: {'✅ Yes' if has_expected_type else '❌ No'}")
    
    # 상위 3개 결과 출력
    print(f"\n📄 Top 3 Results:")
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
    """메인 평가 함수"""
    import sys
    debug = '--debug' in sys.argv or '-d' in sys.argv
    
    print("="*60)
    print("하이브리드 검색 시스템 평가")
    if debug:
        print("(DEBUG MODE)")
    print("="*60)
    
    # 검색기 초기화
    try:
        from rag.multi_stage_retriever_v2 import MultiStageRetrieverV2
        retriever = MultiStageRetrieverV2(DB_CONFIG)
        print("✅ 검색기 초기화 성공")
    except Exception as e:
        print(f"❌ 검색기 초기화 실패: {e}")
        return
    
    # 각 쿼리 평가
    evaluation_results = []
    for test_case in TEST_QUERIES:
        try:
            result = evaluate_single_query(retriever, test_case, debug=debug)
            evaluation_results.append(result)
        except Exception as e:
            print(f"❌ 쿼리 평가 실패: {e}")
            import traceback
            traceback.print_exc()
    
    # 전체 결과 요약
    print("\n" + "="*60)
    print("전체 평가 결과 요약")
    print("="*60)
    
    if evaluation_results:
        total_queries = len(evaluation_results)
        successful_queries = sum(1 for r in evaluation_results if r['has_expected_type'])
        avg_time = sum(r['elapsed_time'] for r in evaluation_results) / total_queries
        avg_score = sum(r['top_score'] for r in evaluation_results) / total_queries
        
        print(f"총 쿼리 수: {total_queries}")
        print(f"예상 타입 매칭 성공률: {successful_queries}/{total_queries} ({successful_queries/total_queries*100:.1f}%)")
        print(f"평균 검색 시간: {avg_time:.2f}초")
        print(f"평균 Top 점수: {avg_score:.4f}")
        
        print(f"\n{'='*60}")
        if successful_queries == total_queries:
            print("✅ 모든 테스트 통과!")
        else:
            print(f"⚠️  {total_queries - successful_queries}개 테스트 실패")
    else:
        print("❌ 평가 결과 없음")
    
    # 정리
    try:
        retriever.close()
    except:
        pass


if __name__ == '__main__':
    main()
