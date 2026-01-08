"""
기관 추천 로직 사용 예시
"""

import sys
from pathlib import Path

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.rag.agency_recommender import AgencyRecommender


def example_basic():
    """기본 사용 예시"""
    print("="*80)
    print("예시 1: 기본 기관 추천 (규칙 기반만)")
    print("="*80 + "\n")
    
    recommender = AgencyRecommender()
    
    queries = [
        "쿠팡에서 산 노트북이 불량입니다",
        "넷플릭스 구독을 취소했는데 환불이 안됩니다",
        "백화점에서 산 의류를 교환하고 싶어요"
    ]
    
    for query in queries:
        print(f"질문: {query}")
        recommendations = recommender.recommend(query, None, top_n=2)
        
        print("추천 기관:")
        for rank, (code, score, info) in enumerate(recommendations, 1):
            print(f"  {rank}순위: {info['name']} (점수: {score:.4f})")
        print()


def example_with_mock_search():
    """검색 결과와 함께 사용하는 예시"""
    print("="*80)
    print("예시 2: 검색 결과와 함께 기관 추천 (규칙 + 통계)")
    print("="*80 + "\n")
    
    recommender = AgencyRecommender()
    
    # 가상의 검색 결과
    query = "G마켓에서 구매한 스마트폰이 배송 중 파손되었습니다"
    
    mock_search_results = [
        {
            'agency': 'ecmc',
            'similarity': 0.92,
            'case_no': 'ECMC-2023-001',
            'text': '온라인 쇼핑몰에서 구매한 제품이 배송 중 파손된 경우...'
        },
        {
            'agency': 'ecmc',
            'similarity': 0.88,
            'case_no': 'ECMC-2023-002',
            'text': '전자상거래 플랫폼에서 상품 주문 후 배송 과정에서...'
        },
        {
            'agency': 'kca',
            'similarity': 0.75,
            'case_no': 'KCA-2023-001',
            'text': '스마트폰 구매 후 제품 하자가 발견되어...'
        },
    ]
    
    print(f"질문: {query}")
    print(f"\n검색된 사례 {len(mock_search_results)}건:")
    for i, result in enumerate(mock_search_results, 1):
        print(f"  {i}. [{result['agency'].upper()}] {result['case_no']} "
              f"(유사도: {result['similarity']:.2f})")
    
    print("\n기관 추천 결과:")
    recommendations = recommender.recommend(query, mock_search_results, top_n=2)
    
    for rank, (code, score, info) in enumerate(recommendations, 1):
        print(f"\n{rank}순위: {info['name']}")
        print(f"  - 최종 점수: {score:.4f}")
        print(f"  - 규칙 점수: {info['rule_score']:.4f} (키워드 매칭)")
        print(f"  - 통계 점수: {info['stat_score']:.4f} (검색 결과 분석)")
        print(f"  - 설명: {info['description']}")


def example_detailed_explanation():
    """상세 설명 생성 예시"""
    print("\n" + "="*80)
    print("예시 3: 상세 추천 설명 생성")
    print("="*80 + "\n")
    
    recommender = AgencyRecommender()
    
    query = "11번가에서 주문한 음원이 다운로드가 안됩니다"
    
    mock_search_results = [
        {'agency': 'kcdrc', 'similarity': 0.9, 'case_no': 'KCDRC-2023-001'},
        {'agency': 'kcdrc', 'similarity': 0.85, 'case_no': 'KCDRC-2023-002'},
        {'agency': 'ecmc', 'similarity': 0.7, 'case_no': 'ECMC-2023-001'},
    ]
    
    print(f"질문: {query}\n")
    
    explanation = recommender.explain_recommendation(query, mock_search_results)
    
    print("📊 상세 추천 정보:")
    print("-" * 80)
    
    for rec in explanation['recommendations']:
        print(f"\n{rec['rank']}순위: {rec['agency_name']} ({rec['agency_code'].upper()})")
        print(f"  정식명: {rec['full_name']}")
        print(f"  설명: {rec['description']}")
        print(f"  최종 점수: {rec['final_score']:.4f}")
        print(f"    └─ 규칙 기반: {rec['rule_score']:.4f}")
        print(f"    └─ 통계 기반: {rec['stat_score']:.4f}")
    
    print("\n📈 검색 결과 기관 분포:")
    for agency, count in explanation['search_results_distribution'].items():
        print(f"  - {agency.upper()}: {count}건")
    
    print("\n⚙️  가중치 설정:")
    print(f"  - 규칙 기반: {explanation['weights']['rule_weight']*100:.0f}%")
    print(f"  - 통계 기반: {explanation['weights']['stat_weight']*100:.0f}%")


def example_formatted_text():
    """사용자 친화적 텍스트 포맷팅 예시"""
    print("\n" + "="*80)
    print("예시 4: 사용자 친화적 텍스트 생성")
    print("="*80 + "\n")
    
    recommender = AgencyRecommender()
    
    scenarios = [
        {
            'query': '쿠팡에서 산 냉장고가 고장났어요',
            'results': [
                {'agency': 'ecmc', 'similarity': 0.9},
                {'agency': 'ecmc', 'similarity': 0.85},
                {'agency': 'kca', 'similarity': 0.7},
            ]
        },
        {
            'query': '유튜브 프리미엄 구독을 취소하고 싶어요',
            'results': [
                {'agency': 'kcdrc', 'similarity': 0.92},
                {'agency': 'kcdrc', 'similarity': 0.88},
            ]
        }
    ]
    
    for scenario in scenarios:
        print(f"질문: {scenario['query']}")
        print("-" * 80)
        
        formatted = recommender.format_recommendation_text(
            scenario['query'], 
            scenario['results']
        )
        print(formatted)
        print("\n")


def example_custom_weights():
    """커스텀 가중치 사용 예시"""
    print("="*80)
    print("예시 5: 가중치 커스터마이징")
    print("="*80 + "\n")
    
    query = "온라인에서 산 전자제품이 불량입니다"
    
    mock_results = [
        {'agency': 'kca', 'similarity': 0.9},
        {'agency': 'kca', 'similarity': 0.85},
        {'agency': 'ecmc', 'similarity': 0.7},
    ]
    
    print(f"질문: {query}\n")
    
    # 다양한 가중치 설정 비교
    weight_configs = [
        (0.7, 0.3, "기본 (규칙 70% + 통계 30%)"),
        (0.9, 0.1, "규칙 중심 (규칙 90% + 통계 10%)"),
        (0.5, 0.5, "균형 (규칙 50% + 통계 50%)"),
        (0.3, 0.7, "통계 중심 (규칙 30% + 통계 70%)"),
    ]
    
    for rule_weight, stat_weight, description in weight_configs:
        recommender = AgencyRecommender(
            rule_weight=rule_weight, 
            stat_weight=stat_weight
        )
        
        recommendations = recommender.recommend(query, mock_results, top_n=1)
        top_agency, top_score, top_info = recommendations[0]
        
        print(f"{description}")
        print(f"  → 추천: {top_info['name']} (점수: {top_score:.4f})")


def main():
    """모든 예시 실행"""
    example_basic()
    example_with_mock_search()
    example_detailed_explanation()
    example_formatted_text()
    example_custom_weights()
    
    print("\n" + "="*80)
    print("✅ 모든 예시 실행 완료!")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
