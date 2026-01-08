"""
똑소리 프로젝트 - RAG 시스템 테스트 v2
작성일: 2026-01-05
다양한 시나리오로 RAG 검색 성능 테스트
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 상위 디렉토리를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from rag.retriever import RAGRetriever, SearchResult
from typing import List
import time


class RAGTester:
    """RAG 시스템 테스터"""
    
    def __init__(self, retriever: RAGRetriever):
        self.retriever = retriever
        self.test_scenarios = self._create_test_scenarios()
    
    def _create_test_scenarios(self) -> List[dict]:
        """테스트 시나리오 생성"""
        return [
            {
                'name': '시나리오 1: 환불 관련 일반 문의',
                'query': '온라인으로 구매한 제품이 불량이에요. 환불 받을 수 있나요?',
                'query_type': 'general_inquiry',
                'expected_doc_types': ['counsel_case', 'mediation_case', 'law'],
                'description': '일반적인 소비자 문의. 상담사례와 법령 정보가 함께 검색되어야 함.'
            },
            {
                'name': '시나리오 2: 법률 해석 질문',
                'query': '소비자기본법에서 소비자의 권리는 무엇인가요?',
                'query_type': 'legal_interpretation',
                'expected_doc_types': ['law'],
                'description': '법령 해석 질문. 법령 데이터가 우선적으로 검색되어야 함.'
            },
            {
                'name': '시나리오 3: 유사 사례 검색',
                'query': '아파트 누수로 인한 손해배상 사례가 있나요?',
                'query_type': 'similar_case',
                'expected_doc_types': ['mediation_case', 'counsel_case'],
                'description': '유사 사례 검색. 분쟁조정사례가 우선적으로 검색되어야 함.'
            },
            {
                'name': '시나리오 4: 감가상각 계산 문의',
                'query': '가전제품 감가상각은 어떻게 계산하나요?',
                'query_type': 'general_inquiry',
                'expected_doc_types': ['counsel_case', 'law'],
                'description': '구체적인 계산 방법 문의. 상담사례에서 답변을 찾아야 함.'
            },
            {
                'name': '시나리오 5: 전자상거래 관련 법령',
                'query': '전자상거래에서 청약철회는 언제까지 가능한가요?',
                'query_type': 'legal_interpretation',
                'expected_doc_types': ['law', 'counsel_case'],
                'description': '전자상거래법 관련 질문. 법령과 상담사례가 함께 검색되어야 함.'
            },
            {
                'name': '시나리오 6: 분쟁조정 절차',
                'query': '소비자분쟁조정위원회에 신청하려면 어떻게 해야 하나요?',
                'query_type': 'general_inquiry',
                'expected_doc_types': ['counsel_case', 'law'],
                'description': '절차 안내 질문. 상담사례와 법령 정보가 필요함.'
            }
        ]
    
    def run_all_tests(self):
        """모든 테스트 시나리오 실행"""
        print("=" * 80)
        print("똑소리 프로젝트 - RAG 시스템 테스트")
        print("=" * 80)
        print()
        
        for i, scenario in enumerate(self.test_scenarios, 1):
            print(f"\n{'=' * 80}")
            print(f"{scenario['name']}")
            print(f"{'=' * 80}")
            print(f"설명: {scenario['description']}")
            print(f"쿼리: {scenario['query']}")
            print(f"쿼리 유형: {scenario['query_type']}")
            print(f"기대 문서 유형: {', '.join(scenario['expected_doc_types'])}")
            print()
            
            # 1. 벡터 검색
            print("--- [1] 벡터 검색 (Vector Search) ---")
            start_time = time.time()
            vector_results = self.retriever.vector_search(scenario['query'], top_k=5)
            vector_time = time.time() - start_time
            self._print_results(vector_results, vector_time)
            
            # 2. 하이브리드 검색
            print("\n--- [2] 하이브리드 검색 (Hybrid Search) ---")
            start_time = time.time()
            hybrid_results = self.retriever.hybrid_search(scenario['query'], top_k=5)
            hybrid_time = time.time() - start_time
            self._print_results(hybrid_results, hybrid_time)
            
            # 3. 멀티 소스 검색
            print("\n--- [3] 멀티 소스 검색 (Multi-Source Search) ---")
            start_time = time.time()
            multi_results = self.retriever.multi_source_search(
                scenario['query'],
                query_type=scenario['query_type'],
                top_k=5
            )
            multi_time = time.time() - start_time
            self._print_results(multi_results, multi_time)
            
            # 4. 컨텍스트 확장
            if vector_results:
                print("\n--- [4] 컨텍스트 확장 (Context Expansion) ---")
                print(f"최상위 결과에 대한 컨텍스트 확장 (window_size=1)")
                start_time = time.time()
                context_results = self.retriever.get_chunk_with_context(
                    vector_results[0].chunk_id,
                    window_size=1
                )
                context_time = time.time() - start_time
                self._print_context_results(context_results, context_time)
            
            # 5. 평가
            print("\n--- [5] 평가 (Evaluation) ---")
            self._evaluate_results(
                scenario['expected_doc_types'],
                vector_results,
                hybrid_results,
                multi_results
            )
            
            print("\n" + "=" * 80)
            input("\n다음 시나리오로 이동하려면 Enter를 누르세요...")
    
    def _print_results(self, results: List[SearchResult], elapsed_time: float):
        """검색 결과 출력"""
        print(f"검색 시간: {elapsed_time:.3f}초")
        print(f"검색 결과 수: {len(results)}개\n")
        
        for i, result in enumerate(results, 1):
            print(f"[{i}] 유사도: {result.similarity:.4f}")
            print(f"    문서 유형: {result.doc_type}")
            print(f"    청크 유형: {result.chunk_type}")
            print(f"    제목: {result.doc_title}")
            print(f"    카테고리: {' > '.join(result.category_path) if result.category_path else 'N/A'}")
            print(f"    내용 (앞 100자): {result.content[:100]}...")
            print()
    
    def _print_context_results(self, results: List[SearchResult], elapsed_time: float):
        """컨텍스트 확장 결과 출력"""
        print(f"검색 시간: {elapsed_time:.3f}초")
        print(f"컨텍스트 청크 수: {len(results)}개\n")
        
        for i, result in enumerate(results, 1):
            is_target = result.metadata and result.metadata.get('is_target', False)
            marker = "★ [타겟]" if is_target else "  "
            print(f"{marker} [{i}] {result.chunk_type}")
            print(f"    내용 (앞 100자): {result.content[:100]}...")
            print()
    
    def _evaluate_results(
        self,
        expected_doc_types: List[str],
        vector_results: List[SearchResult],
        hybrid_results: List[SearchResult],
        multi_results: List[SearchResult]
    ):
        """검색 결과 평가"""
        def calculate_coverage(results: List[SearchResult]) -> float:
            """기대 문서 유형 커버리지 계산"""
            found_types = set(r.doc_type for r in results)
            expected_types = set(expected_doc_types)
            if not expected_types:
                return 1.0
            return len(found_types & expected_types) / len(expected_types)
        
        def calculate_diversity(results: List[SearchResult]) -> float:
            """결과 다양성 계산"""
            if not results:
                return 0.0
            doc_types = [r.doc_type for r in results]
            return len(set(doc_types)) / len(doc_types)
        
        # 평가 지표 계산
        vector_coverage = calculate_coverage(vector_results)
        hybrid_coverage = calculate_coverage(hybrid_results)
        multi_coverage = calculate_coverage(multi_results)
        
        vector_diversity = calculate_diversity(vector_results)
        hybrid_diversity = calculate_diversity(hybrid_results)
        multi_diversity = calculate_diversity(multi_results)
        
        # 결과 출력
        print(f"{'검색 방법':<20} {'커버리지':>10} {'다양성':>10}")
        print("-" * 40)
        print(f"{'벡터 검색':<20} {vector_coverage:>10.2%} {vector_diversity:>10.2%}")
        print(f"{'하이브리드 검색':<20} {hybrid_coverage:>10.2%} {hybrid_diversity:>10.2%}")
        print(f"{'멀티 소스 검색':<20} {multi_coverage:>10.2%} {multi_diversity:>10.2%}")
        print()
        
        # 권장 사항
        best_method = max(
            [
                ('벡터 검색', vector_coverage + vector_diversity),
                ('하이브리드 검색', hybrid_coverage + hybrid_diversity),
                ('멀티 소스 검색', multi_coverage + multi_diversity)
            ],
            key=lambda x: x[1]
        )
        print(f"✅ 이 시나리오에 가장 적합한 검색 방법: {best_method[0]}")
    
    def run_quick_test(self, query: str):
        """빠른 테스트 (단일 쿼리)"""
        print("=" * 80)
        print("빠른 테스트")
        print("=" * 80)
        print(f"쿼리: {query}\n")
        
        # 하이브리드 검색
        results = self.retriever.hybrid_search(query, top_k=3)
        
        print(f"검색 결과 수: {len(results)}개\n")
        for i, result in enumerate(results, 1):
            print(f"[{i}] {result.doc_title} ({result.doc_type})")
            print(f"    유사도: {result.similarity:.4f}")
            print(f"    내용: {result.content[:150]}...")
            print()
        
        # LLM 입력 형식으로 포맷팅
        print("\n--- LLM 입력 형식 ---")
        formatted = self.retriever.format_results_for_llm(results)
        print(formatted[:500] + "...\n")


def main():
    """메인 실행 함수"""
    load_dotenv()
    
    # 데이터베이스 설정
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': os.getenv('DB_PORT', '5432'),
        'database': os.getenv('DB_NAME', 'ddoksori'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres')
    }
    
    # 임베딩 API URL
    embed_api_url = os.getenv('EMBED_API_URL', 'http://localhost:8001/embed')
    
    # RAG Retriever 초기화
    retriever = RAGRetriever(db_config, embed_api_url)
    retriever.connect()
    
    try:
        # 테스터 초기화
        tester = RAGTester(retriever)
        
        # 실행 모드 선택
        print("=" * 80)
        print("똑소리 프로젝트 - RAG 시스템 테스트 v2")
        print("=" * 80)
        print("\n실행 모드를 선택하세요:")
        print("1. 전체 테스트 (6개 시나리오)")
        print("2. 빠른 테스트 (단일 쿼리)")
        print()
        
        choice = input("선택 (1 또는 2): ").strip()
        
        if choice == '1':
            tester.run_all_tests()
        elif choice == '2':
            query = input("\n테스트할 쿼리를 입력하세요: ").strip()
            if query:
                tester.run_quick_test(query)
            else:
                print("쿼리가 입력되지 않았습니다.")
        else:
            print("잘못된 선택입니다.")
        
        print("\n" + "=" * 80)
        print("테스트 완료!")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        retriever.close()


if __name__ == "__main__":
    main()
