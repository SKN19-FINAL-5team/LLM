"""
기관 추천 로직 테스트 스크립트
다양한 시나리오에서 기관 추천이 올바르게 동작하는지 검증
"""

import sys
import os
from pathlib import Path

# 프로젝트 루트와 backend 디렉토리를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'backend'))

from app.rag.agency_recommender import AgencyRecommender


def print_section(title: str):
    """섹션 구분선 출력"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def test_rule_based_scoring():
    """규칙 기반 점수 계산 테스트"""
    print_section("1. 규칙 기반 점수 계산 테스트")
    
    recommender = AgencyRecommender()
    
    test_cases = [
        {
            'query': '온라인 쇼핑몰에서 구매한 노트북이 배송 중 파손되었습니다',
            'expected_top': 'ecmc',
            'description': '전자상거래 + 배송 → ECMC'
        },
        {
            'query': '넷플릭스 구독을 취소했는데 환불이 안됩니다',
            'expected_top': 'kcdrc',
            'description': '콘텐츠 구독 → KCDRC'
        },
        {
            'query': '백화점에서 산 전자제품이 불량입니다',
            'expected_top': 'kca',
            'description': '일반 소비재 → KCA'
        },
        {
            'query': '학원 수강료 환불을 거부당했습니다',
            'expected_top': 'kca',
            'description': '교육 서비스 → KCA'
        }
    ]
    
    for idx, test in enumerate(test_cases, 1):
        print(f"테스트 케이스 {idx}: {test['description']}")
        print(f"질문: {test['query']}")
        
        scores = recommender.calculate_rule_scores(test['query'])
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        print(f"점수:")
        for agency, score in sorted_scores:
            agency_name = recommender.AGENCIES[agency]['name']
            print(f"  - {agency_name} ({agency}): {score:.4f}")
        
        top_agency = sorted_scores[0][0]
        is_correct = top_agency == test['expected_top']
        status = "✅ 통과" if is_correct else f"❌ 실패 (예상: {test['expected_top']})"
        print(f"결과: {status}\n")


def test_stat_based_scoring():
    """검색 결과 통계 기반 점수 계산 테스트"""
    print_section("2. 검색 결과 통계 점수 계산 테스트")
    
    recommender = AgencyRecommender()
    
    # 가상의 검색 결과 (KCA가 많이 나온 경우)
    mock_results = [
        {'agency': 'kca', 'similarity': 0.9},
        {'agency': 'kca', 'similarity': 0.85},
        {'agency': 'ecmc', 'similarity': 0.8},
        {'agency': 'kca', 'similarity': 0.75},
        {'agency': 'kca', 'similarity': 0.7},
    ]
    
    print("가상 검색 결과:")
    for idx, result in enumerate(mock_results, 1):
        print(f"  {idx}. {result['agency']} (유사도: {result['similarity']:.2f})")
    
    scores = recommender.calculate_stat_scores(mock_results)
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    
    print(f"\n통계 점수:")
    for agency, score in sorted_scores:
        agency_name = recommender.AGENCIES[agency]['name']
        print(f"  - {agency_name} ({agency}): {score:.4f}")
    
    print(f"\n✅ KCA가 최고 점수를 받았는지: {sorted_scores[0][0] == 'kca'}")


def test_combined_recommendation():
    """규칙 + 통계 결합 추천 테스트"""
    print_section("3. 결합 추천 테스트 (규칙 70% + 통계 30%)")
    
    recommender = AgencyRecommender(rule_weight=0.7, stat_weight=0.3)
    
    # 시나리오: 쿠팡에서 산 제품 (규칙상 ECMC)
    # 하지만 검색 결과는 KCA가 많이 나옴
    query = "쿠팡에서 구매한 노트북이 고장났습니다"
    
    mock_results = [
        {'agency': 'kca', 'similarity': 0.9},
        {'agency': 'kca', 'similarity': 0.85},
        {'agency': 'kca', 'similarity': 0.8},
        {'agency': 'ecmc', 'similarity': 0.75},
    ]
    
    print(f"질문: {query}")
    print("\n검색 결과:")
    for idx, result in enumerate(mock_results, 1):
        print(f"  {idx}. {result['agency']} (유사도: {result['similarity']:.2f})")
    
    recommendations = recommender.recommend(query, mock_results, top_n=3)
    
    print("\n추천 결과:")
    for idx, (agency_code, final_score, info) in enumerate(recommendations, 1):
        print(f"{idx}. {info['name']} ({agency_code})")
        print(f"   최종 점수: {final_score:.4f}")
        print(f"   - 규칙 점수: {info['rule_score']:.4f}")
        print(f"   - 통계 점수: {info['stat_score']:.4f}")
        print()


def test_explain_recommendation():
    """추천 설명 생성 테스트"""
    print_section("4. 추천 설명 생성 테스트")
    
    recommender = AgencyRecommender()
    
    query = "넷플릭스 구독료를 이중으로 결제했는데 환불이 안됩니다"
    
    mock_results = [
        {'agency': 'kcdrc', 'similarity': 0.9, 'case_no': 'KCDRC-2023-001'},
        {'agency': 'kcdrc', 'similarity': 0.85, 'case_no': 'KCDRC-2023-002'},
        {'agency': 'ecmc', 'similarity': 0.7, 'case_no': 'ECMC-2023-001'},
    ]
    
    print(f"질문: {query}\n")
    
    explanation = recommender.explain_recommendation(query, mock_results)
    
    print("상세 추천 정보:")
    for rec in explanation['recommendations']:
        print(f"\n{rec['rank']}순위: {rec['agency_name']}")
        print(f"  설명: {rec['description']}")
        print(f"  점수: {rec['final_score']:.4f} (규칙: {rec['rule_score']:.4f}, 통계: {rec['stat_score']:.4f})")
    
    print("\n검색 결과 분포:")
    for agency, count in explanation['search_results_distribution'].items():
        print(f"  - {agency}: {count}건")


def test_format_recommendation_text():
    """사용자 친화적 텍스트 포맷팅 테스트"""
    print_section("5. 사용자 친화적 텍스트 포맷팅 테스트")
    
    recommender = AgencyRecommender()
    
    query = "G마켓에서 산 스마트폰이 배송 중 파손되었어요"
    
    mock_results = [
        {'agency': 'ecmc', 'similarity': 0.9},
        {'agency': 'ecmc', 'similarity': 0.85},
        {'agency': 'kca', 'similarity': 0.7},
    ]
    
    print(f"질문: {query}\n")
    
    formatted_text = recommender.format_recommendation_text(query, mock_results)
    print("생성된 추천 텍스트:")
    print("-" * 80)
    print(formatted_text)
    print("-" * 80)


def test_edge_cases():
    """엣지 케이스 테스트"""
    print_section("6. 엣지 케이스 테스트")
    
    recommender = AgencyRecommender()
    
    # 1. 검색 결과가 없는 경우
    print("테스트 1: 검색 결과 없음")
    query = "환불 문의"
    recommendations = recommender.recommend(query, None, top_n=1)
    print(f"질문: {query}")
    print(f"추천 결과: {recommendations[0][0]} (점수: {recommendations[0][1]:.4f})")
    print()
    
    # 2. 키워드가 전혀 매칭되지 않는 경우
    print("테스트 2: 키워드 매칭 없음")
    query = "이것저것 문의합니다"
    scores = recommender.calculate_rule_scores(query)
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    print(f"질문: {query}")
    print(f"최고 점수 기관: {sorted_scores[0][0]} (점수: {sorted_scores[0][1]:.4f})")
    print(f"✅ KCA가 기본값으로 선택되었는지: {sorted_scores[0][0] == 'kca'}")
    print()
    
    # 3. 빈 검색 결과 리스트
    print("테스트 3: 빈 검색 결과")
    query = "환불 요청"
    recommendations = recommender.recommend(query, [], top_n=1)
    print(f"질문: {query}")
    print(f"추천 결과: {recommendations[0][0]} (점수: {recommendations[0][1]:.4f})")


def test_real_world_scenarios():
    """실제 시나리오 테스트"""
    print_section("7. 실제 시나리오 종합 테스트")
    
    recommender = AgencyRecommender()
    
    scenarios = [
        {
            'query': '쿠팡에서 산 냉장고가 고장났는데 환불을 거부당했습니다',
            'description': '온라인 가전제품 분쟁'
        },
        {
            'query': '멜론에서 유료 음원을 구매했는데 다운로드가 안됩니다',
            'description': '음원 콘텐츠 분쟁'
        },
        {
            'query': '오프라인 매장에서 구매한 의류 환불을 거부당했어요',
            'description': '오프라인 일반 소비재 분쟁'
        },
        {
            'query': '11번가에서 주문한 상품이 한 달째 배송이 안됩니다',
            'description': '온라인 배송 지연 분쟁'
        },
        {
            'query': '네이버 웹툰 이용권을 환불받고 싶은데 거절당했습니다',
            'description': '웹툰 콘텐츠 분쟁'
        }
    ]
    
    for idx, scenario in enumerate(scenarios, 1):
        print(f"\n시나리오 {idx}: {scenario['description']}")
        print(f"질문: {scenario['query']}")
        
        recommendations = recommender.recommend(scenario['query'], None, top_n=2)
        
        print("추천 기관:")
        for rank, (agency_code, score, info) in enumerate(recommendations, 1):
            print(f"  {rank}순위: {info['name']} (점수: {score:.4f})")
        print()


def main():
    """메인 테스트 실행"""
    print("\n" + "="*80)
    print("  기관 추천 로직 테스트 시작")
    print("="*80)
    
    try:
        test_rule_based_scoring()
        test_stat_based_scoring()
        test_combined_recommendation()
        test_explain_recommendation()
        test_format_recommendation_text()
        test_edge_cases()
        test_real_world_scenarios()
        
        print("\n" + "="*80)
        print("  ✅ 모든 테스트 완료!")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\n❌ 테스트 중 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
