#!/usr/bin/env python3
"""
hybrid_search_chunks 함수 테스트 스크립트
함수가 정상적으로 생성되고 호출되는지 확인
"""

import os
import sys
import psycopg2
from pathlib import Path
from dotenv import load_dotenv

# 프로젝트 경로 추가
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# 환경 변수 로드
env_file = backend_dir / '.env'
if env_file.exists():
    load_dotenv(env_file)
else:
    load_dotenv()


def test_function_exists():
    """함수 존재 확인"""
    print("=" * 80)
    print("1. 함수 존재 확인")
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
        
        # 함수 존재 확인
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
            print(f"✅ 함수 존재: {result[0]}")
            print(f"   시그니처: {result[1]}")
            cur.close()
            conn.close()
            return True
        else:
            print("❌ 함수가 존재하지 않습니다.")
            cur.close()
            conn.close()
            return False
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return False


def test_function_call():
    """함수 호출 테스트"""
    print("\n" + "=" * 80)
    print("2. 함수 호출 테스트")
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
        
        # 테스트용 임베딩 벡터 생성 (1024차원, 모두 0)
        test_embedding = [0.0] * 1024
        
        # 테스트용 키워드
        test_keywords = ['법령', '조문']
        
        # 함수 호출 (타입 명시적 캐스팅 포함)
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
        
        print("함수 호출 중...")
        cur.execute(sql, (test_embedding, test_keywords))
        
        rows = cur.fetchall()
        print(f"✅ 함수 호출 성공: {len(rows)}개 결과 반환")
        
        if rows:
            print("\n결과 샘플 (첫 번째 행):")
            print(f"  chunk_id: {rows[0][0]}")
            print(f"  doc_id: {rows[0][1]}")
            print(f"  final_score: {rows[0][9]}")
        
        cur.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 함수 호출 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_law_retriever_integration():
    """LawRetriever 통합 테스트"""
    print("\n" + "=" * 80)
    print("3. LawRetriever 통합 테스트")
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
        query_analysis = query_analyzer.analyze("민법 제750조")
        
        # 임베딩 생성 (간단한 테스트용)
        test_embedding = [0.0] * 1024
        
        print("LawRetriever._hybrid_search 메서드 테스트 중...")
        results = retriever._hybrid_search(
            query_embedding=test_embedding,
            keywords=['민법', '제750조'],
            law_names=[],
            top_k=5,
            debug=True
        )
        
        print(f"✅ LawRetriever 통합 테스트 성공: {len(results)}개 결과")
        
        retriever.cur.close()
        retriever.conn.close()
        return True
        
    except Exception as e:
        print(f"❌ LawRetriever 통합 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """메인 테스트 함수"""
    print("\n" + "=" * 80)
    print("hybrid_search_chunks 함수 테스트")
    print("=" * 80 + "\n")
    
    results = []
    
    # 1. 함수 존재 확인
    results.append(("함수 존재 확인", test_function_exists()))
    
    # 2. 함수 호출 테스트
    if results[0][1]:  # 함수가 존재하는 경우에만
        results.append(("함수 호출 테스트", test_function_call()))
        
        # 3. LawRetriever 통합 테스트
        if results[1][1]:  # 함수 호출이 성공한 경우에만
            results.append(("LawRetriever 통합 테스트", test_law_retriever_integration()))
    
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
        print("\n✅ 모든 테스트 통과!")
        return 0
    else:
        print("\n❌ 일부 테스트 실패")
        return 1


if __name__ == "__main__":
    sys.exit(main())
