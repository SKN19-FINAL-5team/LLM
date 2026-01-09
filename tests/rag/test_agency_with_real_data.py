"""
실제 데이터베이스와 함께 기관 추천 로직 테스트
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# 프로젝트 루트와 backend 디렉토리를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'backend'))

# 환경 변수 로드
load_dotenv(project_root / '.env')

from app.rag.retriever import VectorRetriever
from app.rag.agency_recommender import AgencyRecommender


def print_section(title: str):
    """섹션 구분선 출력"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def test_with_real_search():
    """실제 검색 결과와 함께 기관 추천 테스트"""
    print_section("실제 데이터베이스 검색과 기관 추천 통합 테스트")
    
    # DB 설정
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'database': os.getenv('DB_NAME', 'ddoksori_db'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres')
    }
    
    # Retriever와 Recommender 초기화
    retriever = VectorRetriever(db_config)
    recommender = AgencyRecommender()
    
    # 테스트 쿼리들
    test_queries = [
        "온라인 쇼핑몰에서 구매한 노트북이 불량입니다. 환불받을 수 있나요?",
        "넷플릭스 구독을 취소했는데 환불이 안됩니다",
        "백화점에서 산 의류를 교환하고 싶은데 거절당했어요",
        "쿠팡에서 산 제품이 배송 중에 파손되었습니다",
        "멜론 음원을 구매했는데 다운로드가 안됩니다"
    ]
    
    try:
        for idx, query in enumerate(test_queries, 1):
            print(f"\n{'─'*80}")
            print(f"테스트 {idx}: {query}")
            print(f"{'─'*80}")
            
            # 1. 벡터 검색 수행
            print("\n1️⃣ 벡터 검색 실행...")
            search_results = retriever.search(query, top_k=5)
            
            if not search_results:
                print("   ⚠️ 검색 결과 없음")
                continue
            
            print(f"   ✅ {len(search_results)}개의 관련 사례 발견")
            
            # 검색 결과 요약
            print("\n   검색 결과 요약:")
            for i, chunk in enumerate(search_results[:3], 1):
                print(f"   {i}. [{chunk['agency'].upper()}] {chunk['case_no']} "
                      f"(유사도: {chunk['similarity']:.3f})")
                print(f"      {chunk['text'][:60]}...")
            
            # 2. 기관 추천
            print("\n2️⃣ 기관 추천 실행...")
            recommendations = recommender.recommend(query, search_results, top_n=2)
            
            print("\n   추천 결과:")
            for rank, (agency_code, score, info) in enumerate(recommendations, 1):
                print(f"\n   {rank}순위: {info['name']} ({agency_code.upper()})")
                print(f"   ├─ 최종 점수: {score:.4f}")
                print(f"   ├─ 규칙 점수: {info['rule_score']:.4f}")
                print(f"   ├─ 통계 점수: {info['stat_score']:.4f}")
                print(f"   └─ 설명: {info['description']}")
            
            # 3. 사용자 친화적 텍스트 생성
            print("\n3️⃣ 사용자 친화적 추천 텍스트:")
            print("   " + "─"*76)
            formatted = recommender.format_recommendation_text(query, search_results)
            for line in formatted.split('\n'):
                print(f"   {line}")
            print("   " + "─"*76)
        
        print(f"\n{'='*80}")
        print("  ✅ 모든 통합 테스트 완료!")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        retriever.close()
    
    return 0


def test_agency_distribution():
    """데이터베이스의 기관 분포 분석"""
    print_section("데이터베이스 기관 분포 분석")
    
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'database': os.getenv('DB_NAME', 'ddoksori_db'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres')
    }
    
    retriever = VectorRetriever(db_config)
    
    try:
        retriever.connect_db()
        
        # 기관별 사례 수 조회
        query = """
            SELECT 
                agency,
                COUNT(DISTINCT case_uid) as case_count,
                COUNT(*) as chunk_count
            FROM cases c
            JOIN chunks ch ON c.case_uid = ch.case_uid
            WHERE ch.drop = FALSE
            GROUP BY agency
            ORDER BY case_count DESC
        """
        
        with retriever.conn.cursor() as cur:
            cur.execute(query)
            results = cur.fetchall()
        
        print("기관별 데이터 분포:")
        print(f"{'기관':<20} {'사례 수':<15} {'청크 수':<15}")
        print("─" * 50)
        
        total_cases = 0
        total_chunks = 0
        
        for agency, case_count, chunk_count in results:
            agency_name = {
                'kca': '한국소비자원',
                'ecmc': '한국전자거래분쟁조정위원회',
                'kcdrc': '한국저작권위원회'
            }.get(agency, agency)
            
            print(f"{agency_name:<20} {case_count:<15,} {chunk_count:<15,}")
            total_cases += case_count
            total_chunks += chunk_count
        
        print("─" * 50)
        print(f"{'총계':<20} {total_cases:<15,} {total_chunks:<15,}")
        
    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        retriever.close()
    
    return 0


def main():
    """메인 함수"""
    print("\n" + "="*80)
    print("  실제 데이터와 함께 기관 추천 로직 테스트")
    print("="*80)
    
    # 1. 데이터 분포 분석
    result = test_agency_distribution()
    if result != 0:
        return result
    
    # 2. 통합 테스트
    result = test_with_real_search()
    if result != 0:
        return result
    
    return 0


if __name__ == "__main__":
    exit(main())
