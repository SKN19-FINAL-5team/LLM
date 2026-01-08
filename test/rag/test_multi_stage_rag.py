"""
멀티 스테이지 RAG 시스템 테스트 스크립트

4가지 테스트 케이스로 멀티 스테이지 검색의 효과를 검증:
1. 전자제품 환불 (노트북 불량)
2. 온라인 거래 분쟁 (배송 지연)
3. 서비스 환불 (학원 수강료)
4. 콘텐츠 분쟁 (음원 저작권)
"""

import os
import sys
from dotenv import load_dotenv
from datetime import datetime
import json

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.rag import MultiStageRetriever


# 환경 변수 로드
load_dotenv()


# DB 설정
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME', 'ddoksori'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'postgres')
}


# 테스트 케이스 정의
TEST_CASES = [
    {
        'id': 1,
        'name': '전자제품 환불 (노트북 불량)',
        'query': '온라인에서 노트북을 구매했는데 3일 만에 화면이 안 켜집니다. 환불 받을 수 있나요?',
        'expected_agency': 'ecmc',  # 온라인 구매 -> 전자거래분쟁조정위원회
        'product_category': '전자제품',
        'purchase_method': '온라인'
    },
    {
        'id': 2,
        'name': '온라인 거래 분쟁 (배송 지연)',
        'query': '쿠팡에서 옷을 주문했는데 2주가 지나도 배송이 안 됩니다. 환불 요청했는데 거부당했어요.',
        'expected_agency': 'ecmc',  # 쿠팡 -> 전자거래분쟁조정위원회
        'product_category': '의류',
        'purchase_method': '온라인'
    },
    {
        'id': 3,
        'name': '서비스 환불 (학원 수강료)',
        'query': '영어 학원을 등록했는데 강사가 계속 바뀌고 수업 질이 너무 떨어집니다. 환불 받을 수 있나요?',
        'expected_agency': 'kca',  # 일반 서비스 -> 한국소비자원
        'product_category': '서비스',
        'purchase_method': '오프라인'
    },
    {
        'id': 4,
        'name': '콘텐츠 분쟁 (음원 저작권)',
        'query': '멜론에서 구매한 음원을 다른 기기로 옮기려고 하는데 안 됩니다. 제가 산 음원인데 왜 못 쓰나요?',
        'expected_agency': 'kcdrc',  # 음원 저작권 -> 한국저작권위원회
        'product_category': '콘텐츠',
        'purchase_method': '온라인'
    }
]


def print_separator(title: str = None):
    """구분선 출력"""
    if title:
        print(f"\n{'='*80}")
        print(f"  {title}")
        print(f"{'='*80}\n")
    else:
        print(f"{'='*80}\n")


def print_test_case_header(test_case: dict):
    """테스트 케이스 헤더 출력"""
    print_separator(f"테스트 {test_case['id']}: {test_case['name']}")
    print(f"**질문:** {test_case['query']}")
    print(f"**예상 기관:** {test_case['expected_agency']}")
    print(f"**제품 카테고리:** {test_case['product_category']}")
    print(f"**구매 방법:** {test_case['purchase_method']}")
    print()


def print_stage_results(stage_name: str, chunks: list):
    """검색 단계별 결과 출력"""
    print(f"\n[{stage_name}] {len(chunks)}개 청크 검색")
    if chunks:
        for idx, chunk in enumerate(chunks[:3], 1):  # 상위 3개만 출력
            print(f"  {idx}. [{chunk.get('chunk_type', 'N/A')}] "
                  f"유사도: {chunk.get('similarity', 0):.3f} - "
                  f"{chunk.get('text', '')[:100]}...")


def evaluate_results(test_case: dict, results: dict) -> dict:
    """
    검색 결과 평가
    
    Returns:
        평가 지표 딕셔너리
    """
    evaluation = {
        'test_id': test_case['id'],
        'test_name': test_case['name'],
        'timestamp': datetime.now().isoformat()
    }
    
    # 1. 검색 결과 수
    stats = results.get('stats', {})
    evaluation['total_chunks'] = stats.get('total_chunks', 0)
    evaluation['law_chunks'] = stats.get('law_chunks', 0)
    evaluation['criteria_chunks'] = stats.get('criteria_chunks', 0)
    evaluation['mediation_chunks'] = stats.get('mediation_chunks', 0)
    evaluation['counsel_chunks'] = stats.get('counsel_chunks', 0)
    evaluation['used_fallback'] = stats.get('used_fallback', False)
    
    # 2. 기관 추천 정확도
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
    
    # 3. 유사도 평가
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
    
    # 4. Fallback 사용 여부
    evaluation['fallback_triggered'] = results.get('used_fallback', False)
    
    return evaluation


def print_evaluation(evaluation: dict):
    """평가 결과 출력"""
    print(f"\n{'─'*80}")
    print("📊 평가 결과")
    print(f"{'─'*80}")
    
    print(f"\n✅ 검색 결과 요약:")
    print(f"  - 총 청크 수: {evaluation['total_chunks']}개")
    print(f"  - 법령: {evaluation['law_chunks']}개")
    print(f"  - 기준: {evaluation['criteria_chunks']}개")
    print(f"  - 분쟁조정사례: {evaluation['mediation_chunks']}개")
    print(f"  - 피해구제사례: {evaluation['counsel_chunks']}개")
    print(f"  - Fallback 사용: {'예' if evaluation['fallback_triggered'] else '아니오'}")
    
    print(f"\n✅ 유사도 분석:")
    print(f"  - 평균 유사도: {evaluation['avg_similarity']:.3f}")
    print(f"  - 최대 유사도: {evaluation['max_similarity']:.3f}")
    print(f"  - 최소 유사도: {evaluation['min_similarity']:.3f}")
    
    print(f"\n✅ 기관 추천:")
    if evaluation['recommended_agency']:
        status = "✓ 정확" if evaluation['agency_correct'] else "✗ 부정확"
        print(f"  - 추천 기관: {evaluation['recommended_agency']} ({status})")
        print(f"  - 추천 점수: {evaluation['agency_score']:.3f}")
    else:
        print(f"  - 추천 기관 없음")
    
    print()


def run_test(retriever: MultiStageRetriever, test_case: dict) -> dict:
    """
    단일 테스트 케이스 실행
    
    Args:
        retriever: 멀티 스테이지 검색기
        test_case: 테스트 케이스
        
    Returns:
        평가 결과
    """
    print_test_case_header(test_case)
    
    # 멀티 스테이지 검색 실행
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
    
    print(f"\n⏱️ 검색 시간: {elapsed_time:.2f}초")
    
    # Stage별 결과 출력
    stage1 = results.get('stage1', {})
    print_stage_results("Stage 1: 법령", stage1.get('law', []))
    print_stage_results("Stage 1: 기준", stage1.get('criteria', []))
    
    stage2 = results.get('stage2', [])
    print_stage_results("Stage 2: 분쟁조정사례", stage2)
    
    if results.get('used_fallback'):
        stage3 = results.get('stage3', [])
        print_stage_results("Stage 3: 피해구제사례 (Fallback)", stage3)
    
    # 기관 추천 결과 출력
    agency_rec = results.get('agency_recommendation')
    if agency_rec:
        print(f"\n📋 기관 추천 결과:")
        print(agency_rec['formatted'])
    
    # 평가
    evaluation = evaluate_results(test_case, results)
    evaluation['elapsed_time'] = elapsed_time
    print_evaluation(evaluation)
    
    return evaluation


def print_summary(evaluations: list):
    """전체 테스트 요약 출력"""
    print_separator("📈 전체 테스트 요약")
    
    total_tests = len(evaluations)
    total_chunks = sum(e['total_chunks'] for e in evaluations)
    avg_chunks = total_chunks / total_tests if total_tests > 0 else 0
    
    fallback_count = sum(1 for e in evaluations if e['fallback_triggered'])
    fallback_rate = fallback_count / total_tests * 100 if total_tests > 0 else 0
    
    agency_correct = sum(1 for e in evaluations if e['agency_correct'])
    agency_accuracy = agency_correct / total_tests * 100 if total_tests > 0 else 0
    
    avg_similarity = sum(e['avg_similarity'] for e in evaluations) / total_tests if total_tests > 0 else 0
    avg_time = sum(e['elapsed_time'] for e in evaluations) / total_tests if total_tests > 0 else 0
    
    print(f"✅ 총 테스트: {total_tests}건")
    print(f"✅ 평균 검색 청크 수: {avg_chunks:.1f}개")
    print(f"✅ Fallback 사용률: {fallback_rate:.1f}% ({fallback_count}/{total_tests})")
    print(f"✅ 기관 추천 정확도: {agency_accuracy:.1f}% ({agency_correct}/{total_tests})")
    print(f"✅ 평균 유사도: {avg_similarity:.3f}")
    print(f"✅ 평균 검색 시간: {avg_time:.2f}초")
    
    print(f"\n📊 테스트별 상세:")
    for e in evaluations:
        status = "✓" if e['agency_correct'] else "✗"
        print(f"  {status} 테스트 {e['test_id']}: {e['test_name']}")
        print(f"     - 청크: {e['total_chunks']}개, 유사도: {e['avg_similarity']:.3f}, "
              f"기관: {e['recommended_agency']}, 시간: {e['elapsed_time']:.2f}초")


def save_results(evaluations: list, output_file: str = "test_results.json"):
    """테스트 결과를 JSON 파일로 저장"""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(evaluations, f, ensure_ascii=False, indent=2)
    print(f"\n💾 결과 저장: {output_file}")


def main():
    """메인 실행 함수"""
    print_separator("🚀 멀티 스테이지 RAG 시스템 테스트 시작")
    
    print("📌 테스트 설정:")
    print(f"  - DB Host: {DB_CONFIG['host']}")
    print(f"  - DB Name: {DB_CONFIG['database']}")
    print(f"  - 테스트 케이스 수: {len(TEST_CASES)}개")
    
    # 멀티 스테이지 검색기 초기화
    try:
        retriever = MultiStageRetriever(DB_CONFIG)
        print("✅ 검색기 초기화 완료")
    except Exception as e:
        print(f"❌ 검색기 초기화 실패: {e}")
        return
    
    # 각 테스트 케이스 실행
    evaluations = []
    
    for test_case in TEST_CASES:
        try:
            evaluation = run_test(retriever, test_case)
            evaluations.append(evaluation)
        except Exception as e:
            print(f"❌ 테스트 {test_case['id']} 실행 실패: {e}")
            import traceback
            traceback.print_exc()
    
    # 검색기 종료
    retriever.close()
    
    # 전체 요약
    if evaluations:
        print_summary(evaluations)
        save_results(evaluations)
    else:
        print("\n❌ 실행된 테스트가 없습니다.")
    
    print_separator("✅ 테스트 완료")


if __name__ == "__main__":
    main()
