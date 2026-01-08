"""
RAG 테스트 결과 분석 스크립트

test_multi_stage_rag.py의 결과를 시각화하고 분석
"""

import json
import sys
from pathlib import Path
from typing import List, Dict


def load_results(file_path: str = "test_results.json") -> List[Dict]:
    """테스트 결과 JSON 파일 로드"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ 파일을 찾을 수 없습니다: {file_path}")
        print("먼저 test_multi_stage_rag.py를 실행하세요.")
        sys.exit(1)


def print_separator(title: str = None):
    """구분선 출력"""
    if title:
        print(f"\n{'='*80}")
        print(f"  {title}")
        print(f"{'='*80}\n")
    else:
        print(f"{'='*80}\n")


def analyze_search_distribution(results: List[Dict]):
    """검색 결과 분포 분석"""
    print_separator("📊 검색 결과 분포 분석")
    
    total_tests = len(results)
    
    # 각 소스별 청크 수 통계
    law_chunks = [r['law_chunks'] for r in results]
    criteria_chunks = [r['criteria_chunks'] for r in results]
    mediation_chunks = [r['mediation_chunks'] for r in results]
    counsel_chunks = [r['counsel_chunks'] for r in results]
    
    print("📈 소스별 평균 청크 수:")
    print(f"  - 법령: {sum(law_chunks)/total_tests:.1f}개 (범위: {min(law_chunks)}~{max(law_chunks)})")
    print(f"  - 기준: {sum(criteria_chunks)/total_tests:.1f}개 (범위: {min(criteria_chunks)}~{max(criteria_chunks)})")
    print(f"  - 분쟁조정사례: {sum(mediation_chunks)/total_tests:.1f}개 (범위: {min(mediation_chunks)}~{max(mediation_chunks)})")
    print(f"  - 피해구제사례: {sum(counsel_chunks)/total_tests:.1f}개 (범위: {min(counsel_chunks)}~{max(counsel_chunks)})")
    
    # Fallback 사용 빈도
    fallback_count = sum(1 for r in results if r['fallback_triggered'])
    print(f"\n🔄 Fallback 사용:")
    print(f"  - 발동 횟수: {fallback_count}/{total_tests} ({fallback_count/total_tests*100:.1f}%)")
    
    if fallback_count > 0:
        print(f"  - Fallback 발동 케이스:")
        for r in results:
            if r['fallback_triggered']:
                print(f"    • 테스트 {r['test_id']}: {r['test_name']}")
                print(f"      (분쟁조정사례: {r['mediation_chunks']}개, 피해구제사례: {r['counsel_chunks']}개)")


def analyze_similarity(results: List[Dict]):
    """유사도 분석"""
    print_separator("📊 유사도 분석")
    
    avg_sims = [r['avg_similarity'] for r in results]
    max_sims = [r['max_similarity'] for r in results]
    min_sims = [r['min_similarity'] for r in results]
    
    print("📈 유사도 통계:")
    print(f"  - 전체 평균 유사도: {sum(avg_sims)/len(avg_sims):.3f}")
    print(f"  - 최고 유사도 (모든 테스트): {max(max_sims):.3f}")
    print(f"  - 최저 유사도 (모든 테스트): {min(min_sims):.3f}")
    
    print(f"\n📊 테스트별 유사도:")
    for r in sorted(results, key=lambda x: x['avg_similarity'], reverse=True):
        print(f"  • 테스트 {r['test_id']}: {r['test_name']}")
        print(f"    평균={r['avg_similarity']:.3f}, 최대={r['max_similarity']:.3f}, 최소={r['min_similarity']:.3f}")
    
    # 유사도 품질 평가
    high_quality = sum(1 for s in avg_sims if s >= 0.7)
    medium_quality = sum(1 for s in avg_sims if 0.5 <= s < 0.7)
    low_quality = sum(1 for s in avg_sims if s < 0.5)
    
    print(f"\n🎯 유사도 품질 분포:")
    print(f"  - 높음 (≥0.7): {high_quality}건 ({high_quality/len(results)*100:.1f}%)")
    print(f"  - 중간 (0.5~0.7): {medium_quality}건 ({medium_quality/len(results)*100:.1f}%)")
    print(f"  - 낮음 (<0.5): {low_quality}건 ({low_quality/len(results)*100:.1f}%)")


def analyze_agency_recommendation(results: List[Dict]):
    """기관 추천 분석"""
    print_separator("📊 기관 추천 분석")
    
    total_tests = len(results)
    correct_count = sum(1 for r in results if r['agency_correct'])
    accuracy = correct_count / total_tests * 100
    
    print(f"🎯 추천 정확도: {accuracy:.1f}% ({correct_count}/{total_tests})")
    
    print(f"\n📊 테스트별 추천 결과:")
    for r in results:
        status = "✓ 정확" if r['agency_correct'] else "✗ 부정확"
        print(f"  • 테스트 {r['test_id']}: {r['test_name']}")
        print(f"    추천 기관: {r['recommended_agency']} ({status})")
        print(f"    추천 점수: {r['agency_score']:.3f}")
    
    # 기관별 추천 빈도
    from collections import Counter
    agency_counts = Counter(r['recommended_agency'] for r in results if r['recommended_agency'])
    
    print(f"\n📈 기관별 추천 빈도:")
    for agency, count in agency_counts.most_common():
        print(f"  - {agency}: {count}회 ({count/total_tests*100:.1f}%)")


def analyze_performance(results: List[Dict]):
    """성능 분석"""
    print_separator("📊 성능 분석")
    
    elapsed_times = [r['elapsed_time'] for r in results]
    total_chunks = [r['total_chunks'] for r in results]
    
    print("⏱️ 검색 시간:")
    print(f"  - 평균 시간: {sum(elapsed_times)/len(elapsed_times):.2f}초")
    print(f"  - 최소 시간: {min(elapsed_times):.2f}초")
    print(f"  - 최대 시간: {max(elapsed_times):.2f}초")
    
    print(f"\n📊 청크 당 검색 시간:")
    avg_time_per_chunk = sum(
        r['elapsed_time'] / r['total_chunks'] 
        for r in results if r['total_chunks'] > 0
    ) / len(results)
    print(f"  - 평균: {avg_time_per_chunk:.3f}초/청크")
    
    print(f"\n📈 테스트별 성능:")
    for r in sorted(results, key=lambda x: x['elapsed_time']):
        print(f"  • 테스트 {r['test_id']}: {r['elapsed_time']:.2f}초 ({r['total_chunks']}개 청크)")


def generate_recommendations(results: List[Dict]):
    """분석 결과 기반 개선 제안"""
    print_separator("💡 개선 제안")
    
    recommendations = []
    
    # 1. Fallback 빈도 체크
    fallback_count = sum(1 for r in results if r['fallback_triggered'])
    fallback_rate = fallback_count / len(results)
    
    if fallback_rate > 0.5:
        recommendations.append(
            "⚠️ Fallback이 50% 이상 발동되고 있습니다. "
            "분쟁조정사례 데이터를 늘리거나 mediation_threshold를 낮추는 것을 고려하세요."
        )
    
    # 2. 유사도 체크
    avg_similarities = [r['avg_similarity'] for r in results]
    overall_avg = sum(avg_similarities) / len(avg_similarities)
    
    if overall_avg < 0.5:
        recommendations.append(
            "⚠️ 전체 평균 유사도가 0.5 미만입니다. "
            "청킹 전략을 재검토하거나 임베딩 모델을 튜닝하세요."
        )
    elif overall_avg >= 0.7:
        recommendations.append(
            "✅ 유사도가 우수합니다. 현재 청킹 및 임베딩 전략을 유지하세요."
        )
    
    # 3. 기관 추천 정확도 체크
    correct_count = sum(1 for r in results if r['agency_correct'])
    accuracy = correct_count / len(results)
    
    if accuracy < 0.75:
        recommendations.append(
            "⚠️ 기관 추천 정확도가 75% 미만입니다. "
            "키워드 규칙을 개선하거나 가중치 비율(rule_weight/result_weight)을 조정하세요."
        )
    elif accuracy == 1.0:
        recommendations.append(
            "✅ 기관 추천이 100% 정확합니다. 현재 알고리즘을 유지하세요."
        )
    
    # 4. 성능 체크
    elapsed_times = [r['elapsed_time'] for r in results]
    avg_time = sum(elapsed_times) / len(elapsed_times)
    
    if avg_time > 5.0:
        recommendations.append(
            "⚠️ 평균 검색 시간이 5초를 초과합니다. "
            "벡터 인덱스를 최적화하거나 top_k 값을 줄이는 것을 고려하세요."
        )
    elif avg_time < 2.0:
        recommendations.append(
            "✅ 검색 성능이 우수합니다 (평균 2초 미만)."
        )
    
    # 5. 검색 결과 수 체크
    total_chunks_list = [r['total_chunks'] for r in results]
    avg_chunks = sum(total_chunks_list) / len(total_chunks_list)
    
    if avg_chunks < 5:
        recommendations.append(
            "⚠️ 평균 검색 결과가 5개 미만입니다. "
            "top_k 값을 늘리거나 검색 필터를 완화하세요."
        )
    elif avg_chunks > 20:
        recommendations.append(
            "⚠️ 평균 검색 결과가 20개를 초과합니다. "
            "LLM 컨텍스트가 너무 길어질 수 있습니다. top_k 값을 줄이세요."
        )
    
    if recommendations:
        for rec in recommendations:
            print(f"\n{rec}")
    else:
        print("\n✅ 모든 지표가 양호합니다. 추가 개선 사항이 없습니다.")


def main():
    """메인 실행 함수"""
    print_separator("🔍 RAG 테스트 결과 분석")
    
    # 결과 파일 로드
    results = load_results()
    
    print(f"📁 로드된 테스트: {len(results)}건")
    print(f"📅 분석 시작\n")
    
    # 각종 분석 실행
    analyze_search_distribution(results)
    analyze_similarity(results)
    analyze_agency_recommendation(results)
    analyze_performance(results)
    generate_recommendations(results)
    
    print_separator("✅ 분석 완료")


if __name__ == "__main__":
    main()
