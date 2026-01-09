#!/usr/bin/env python3
"""
BM25 Retriever 성능 종합 테스트 스크립트

다양한 쿼리 유형에 대해 BM25 검색 성능을 테스트하고,
다른 검색 방법(cosine, SPLADE, hybrid)과 비교합니다.
"""

import os
import sys
import json
import time
from typing import List, Dict, Optional
from pathlib import Path
from dotenv import load_dotenv
from collections import defaultdict

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

from app.rag.multi_method_retriever import MultiMethodRetriever


class BM25PerformanceTester:
    """BM25 성능 테스터"""
    
    # 테스트 쿼리 세트
    TEST_QUERIES = {
        'law': [
            "민법 제750조 불법행위",
            "소비자기본법 제68조 집단분쟁조정",
            "전자상거래법 환불 규정",
            "약관규제법 무효 조항",
            "상법 제101조 위탁매매"
        ],
        'criteria': [
            "냉장고 품질보증 기준",
            "세탁기 하자 판정 기준",
            "에어컨 수리 기준",
            "TV 환불 기준",
            "스마트폰 교환 기준"
        ],
        'mediation_case': [
            "냉장고 환불 사례",
            "세탁기 하자 교환 사례",
            "에어컨 수리 피해보상",
            "TV 품질 문제 분쟁조정",
            "스마트폰 계약해제 사례"
        ],
        'counsel_case': [
            "냉장고 수리 피해구제",
            "세탁기 환불 상담",
            "에어컨 하자 보상",
            "TV 교환 피해구제",
            "스마트폰 위약금 상담"
        ],
        'mixed': [
            "냉장고 하자 환불",
            "세탁기 품질 문제 교환",
            "에어컨 수리 기준 및 사례",
            "TV 환불 규정과 분쟁조정",
            "스마트폰 계약해제 관련 법령"
        ]
    }
    
    def __init__(self, db_config: Dict):
        """
        Args:
            db_config: 데이터베이스 연결 설정
        """
        self.db_config = db_config
        self.retriever = None
        self.results = defaultdict(list)
    
    def initialize(self):
        """Retriever 초기화"""
        print("=" * 80)
        print("BM25 Retriever 성능 테스트")
        print("=" * 80)
        print("\n1. MultiMethodRetriever 초기화 중...")
        
        try:
            self.retriever = MultiMethodRetriever(self.db_config)
            print("✅ 초기화 완료\n")
            return True
        except Exception as e:
            print(f"❌ 초기화 실패: {e}\n")
            return False
    
    def test_single_query(
        self,
        query: str,
        category: str,
        top_k: int = 10,
        methods: Optional[List[str]] = None
    ) -> Dict:
        """
        단일 쿼리 테스트
        
        Args:
            query: 검색 쿼리
            category: 쿼리 카테고리
            top_k: 반환할 최대 결과 수
            methods: 테스트할 검색 방법 리스트
        
        Returns:
            테스트 결과 딕셔너리
        """
        if methods is None:
            methods = ['cosine', 'bm25', 'splade', 'hybrid']
        
        print(f"\n{'=' * 80}")
        print(f"📋 쿼리: {query}")
        print(f"📂 카테고리: {category}")
        print(f"{'=' * 80}")
        
        query_results = {
            'query': query,
            'category': category,
            'methods': {}
        }
        
        # 각 검색 방법별 테스트
        for method in methods:
            if method == 'cosine':
                result = self.retriever.search_cosine(query, top_k=top_k)
            elif method == 'bm25':
                result = self.retriever.search_bm25(query, top_k=top_k)
            elif method == 'splade':
                result = self.retriever.search_splade(query, top_k=top_k)
            elif method == 'hybrid':
                result = self.retriever.search_hybrid(query, top_k=top_k)
            else:
                continue
            
            # 결과 분석
            method_result = {
                'success': result.get('success', False),
                'count': result.get('count', 0),
                'elapsed_time': result.get('elapsed_time', 0.0),
                'error': result.get('error'),
                'top_scores': [],
                'source_distribution': defaultdict(int)
            }
            
            if method_result['success'] and result.get('results'):
                # 상위 점수 추출
                scores = [r.get('score', 0.0) for r in result['results'][:5]]
                method_result['top_scores'] = scores
                
                # 소스 분포 분석
                for r in result['results']:
                    source = r.get('source', 'unknown')
                    method_result['source_distribution'][source] += 1
                
                # 결과 요약 출력
                print(f"\n[{method.upper()}]")
                print(f"  ✅ 성공: {method_result['count']}개 결과")
                print(f"  ⏱️  시간: {method_result['elapsed_time']*1000:.1f}ms")
                print(f"  📊 상위 점수: {[f'{s:.4f}' for s in scores[:3]]}")
                print(f"  📁 소스 분포: {dict(method_result['source_distribution'])}")
            else:
                print(f"\n[{method.upper()}]")
                print(f"  ❌ 실패: {method_result.get('error', 'Unknown error')}")
            
            query_results['methods'][method] = method_result
        
        return query_results
    
    def test_all_queries(self, top_k: int = 10) -> Dict:
        """
        모든 테스트 쿼리 실행
        
        Args:
            top_k: 반환할 최대 결과 수
        
        Returns:
            전체 테스트 결과
        """
        all_results = {
            'test_time': time.strftime('%Y-%m-%d %H:%M:%S'),
            'queries': [],
            'summary': {}
        }
        
        # 각 카테고리별 테스트
        for category, queries in self.TEST_QUERIES.items():
            print(f"\n\n{'#' * 80}")
            print(f"# 카테고리: {category.upper()}")
            print(f"{'#' * 80}")
            
            for query in queries:
                result = self.test_single_query(query, category, top_k=top_k)
                all_results['queries'].append(result)
                time.sleep(0.1)  # DB 부하 방지
        
        # 전체 요약 통계 계산
        all_results['summary'] = self._calculate_summary(all_results['queries'])
        
        return all_results
    
    def _calculate_summary(self, query_results: List[Dict]) -> Dict:
        """전체 테스트 결과 요약 통계 계산"""
        summary = {
            'total_queries': len(query_results),
            'methods': defaultdict(lambda: {
                'total_tests': 0,
                'successful': 0,
                'failed': 0,
                'avg_count': 0.0,
                'avg_time': 0.0,
                'total_time': 0.0,
                'avg_top_score': 0.0
            })
        }
        
        for query_result in query_results:
            for method, method_result in query_result['methods'].items():
                stats = summary['methods'][method]
                stats['total_tests'] += 1
                
                if method_result['success']:
                    stats['successful'] += 1
                    stats['avg_count'] += method_result['count']
                    stats['avg_time'] += method_result['elapsed_time']
                    stats['total_time'] += method_result['elapsed_time']
                    
                    if method_result['top_scores']:
                        stats['avg_top_score'] += method_result['top_scores'][0]
                else:
                    stats['failed'] += 1
        
        # 평균 계산
        for method, stats in summary['methods'].items():
            if stats['successful'] > 0:
                stats['avg_count'] /= stats['successful']
                stats['avg_time'] /= stats['successful']
                stats['avg_top_score'] /= stats['successful']
        
        return summary
    
    def print_summary(self, all_results: Dict):
        """테스트 결과 요약 출력"""
        print("\n\n" + "=" * 80)
        print("📊 테스트 결과 요약")
        print("=" * 80)
        
        summary = all_results['summary']
        print(f"\n총 테스트 쿼리 수: {summary['total_queries']}")
        
        print("\n검색 방법별 성능:")
        print("-" * 80)
        print(f"{'Method':<10} {'Success':<10} {'Failed':<10} {'Avg Count':<12} {'Avg Time (ms)':<15} {'Avg Top Score':<15}")
        print("-" * 80)
        
        for method, stats in summary['methods'].items():
            print(f"{method:<10} {stats['successful']:<10} {stats['failed']:<10} "
                  f"{stats['avg_count']:<12.1f} {stats['avg_time']*1000:<15.1f} {stats['avg_top_score']:<15.4f}")
        
        print("\n" + "=" * 80)
        
        # BM25 특별 분석
        if 'bm25' in summary['methods']:
            bm25_stats = summary['methods']['bm25']
            print("\n🔍 BM25 검색 상세 분석:")
            print(f"  - 성공률: {bm25_stats['successful']}/{bm25_stats['total_tests']} "
                  f"({bm25_stats['successful']/bm25_stats['total_tests']*100:.1f}%)")
            print(f"  - 평균 결과 수: {bm25_stats['avg_count']:.1f}개")
            print(f"  - 평균 검색 시간: {bm25_stats['avg_time']*1000:.1f}ms")
            print(f"  - 평균 최고 점수: {bm25_stats['avg_top_score']:.4f}")
    
    def save_results(self, all_results: Dict, output_file: str = 'bm25_test_results.json'):
        """테스트 결과를 JSON 파일로 저장"""
        output_path = backend_dir / 'scripts' / output_file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        print(f"\n💾 테스트 결과 저장: {output_path}")


def main():
    """메인 함수"""
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'database': os.getenv('DB_NAME', 'ddoksori'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres')
    }
    
    tester = BM25PerformanceTester(db_config)
    
    if not tester.initialize():
        print("❌ 초기화 실패로 테스트를 종료합니다.")
        return
    
    # 전체 테스트 실행
    print("\n2. 전체 테스트 시작...\n")
    all_results = tester.test_all_queries(top_k=10)
    
    # 결과 요약 출력
    tester.print_summary(all_results)
    
    # 결과 저장
    tester.save_results(all_results)
    
    print("\n✅ 테스트 완료!")


if __name__ == "__main__":
    main()
