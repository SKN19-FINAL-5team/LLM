#!/usr/bin/env python3
"""
MultiMethodRetriever.search_hybrid() 통합 테스트
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 프로젝트 경로 추가
backend_dir = Path(__file__).parent.parent
project_root = backend_dir.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_dir))

# 환경 변수 로드
env_file = backend_dir / '.env'
if env_file.exists():
    load_dotenv(env_file)
else:
    load_dotenv()


def test_hybrid_search():
    """MultiMethodRetriever.search_hybrid() 테스트"""
    print("=" * 80)
    print("MultiMethodRetriever.search_hybrid() 통합 테스트")
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
        
        print("\n2. Hybrid Search 실행 중...")
        query = "민법 제750조 불법행위"
        
        result = retriever.search_hybrid(query=query, top_k=5)
        
        print(f"\n✅ Hybrid Search 성공!")
        print(f"   검색 방법: {result.get('method')}")
        print(f"   결과 수: {result.get('count')}개")
        print(f"   소요 시간: {result.get('elapsed_time', 0):.3f}초")
        print(f"   성공 여부: {result.get('success', False)}")
        
        if result.get('success') and result.get('results'):
            print(f"\n3. 결과 샘플 (상위 3개):")
            for idx, r in enumerate(result['results'][:3], 1):
                print(f"\n   [{idx}]")
                print(f"      chunk_id: {r.get('chunk_id', 'N/A')[:50]}...")
                print(f"      source: {r.get('source', 'N/A')}")
                print(f"      score: {r.get('score', 0):.4f}")
                print(f"      text: {r.get('text', '')[:100]}...")
        
        if not result.get('success'):
            error = result.get('error', 'Unknown error')
            print(f"\n❌ Hybrid Search 실패: {error}")
            retriever.close()
            return False
        
        retriever.close()
        return True
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_all_methods_integration():
    """search_all_methods()에서 hybrid 포함 전체 테스트"""
    print("\n" + "=" * 80)
    print("search_all_methods() 통합 테스트 (hybrid 포함)")
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
        
        print("\n2. 모든 검색 방법 실행 중...")
        query = "온라인 쇼핑몰 환불"
        
        results = retriever.search_all_methods(
            query=query,
            top_k=5,
            methods=['cosine', 'hybrid']  # hybrid만 테스트
        )
        
        print(f"\n✅ 모든 검색 방법 실행 완료!")
        print(f"   쿼리: {query}")
        print(f"   총 방법 수: {results.get('total_methods', 0)}")
        print(f"   성공한 방법 수: {results.get('successful_methods', 0)}")
        
        print(f"\n3. 각 방법별 결과:")
        for method_name, method_data in results.get('methods', {}).items():
            success = method_data.get('success', False)
            count = method_data.get('count', 0)
            elapsed = method_data.get('elapsed_time', 0)
            status = "✅" if success else "❌"
            print(f"   {status} {method_name.upper()}: {count}개 결과 ({elapsed:.3f}초)")
            if not success:
                error = method_data.get('error', 'Unknown error')
                print(f"      오류: {error}")
        
        hybrid_result = results.get('methods', {}).get('hybrid', {})
        if hybrid_result.get('success'):
            print(f"\n✅ Hybrid Search 통합 테스트 성공!")
            retriever.close()
            return True
        else:
            print(f"\n❌ Hybrid Search 통합 테스트 실패")
            retriever.close()
            return False
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """메인 테스트 함수"""
    print("\n" + "=" * 80)
    print("MultiMethodRetriever Hybrid Search 통합 테스트")
    print("=" * 80)
    
    results = []
    
    # 1. Hybrid Search 단독 테스트
    results.append(("Hybrid Search 단독 테스트", test_hybrid_search()))
    
    # 2. 전체 통합 테스트
    if results[0][1]:  # 첫 번째 테스트가 성공한 경우에만
        results.append(("search_all_methods() 통합 테스트", test_all_methods_integration()))
    
    # 결과 요약
    print("\n" + "=" * 80)
    print("테스트 결과 요약")
    print("=" * 80)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ 통과" if passed else "❌ 실패"
        print(f"{status}: {test_name}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n✅ 모든 통합 테스트 통과!")
        print("   hybrid_search_chunks 함수가 정상적으로 작동합니다.")
        return 0
    else:
        print("\n❌ 일부 테스트 실패")
        return 1


if __name__ == "__main__":
    sys.exit(main())
