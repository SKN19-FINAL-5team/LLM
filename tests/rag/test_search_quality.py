#!/usr/bin/env python3
"""
검색 품질 테스트 스크립트

개선 후 데이터의 검색 품질을 측정합니다.
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import requests
from typing import List, Dict, Tuple
import json
from datetime import datetime

load_dotenv()

class SearchQualityTester:
    """검색 품질 테스트"""
    
    def __init__(self):
        """초기화"""
        try:
            self.conn = psycopg2.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                port=os.getenv('DB_PORT', '5432'),
                database=os.getenv('DB_NAME', 'ddoksori'),
                user=os.getenv('DB_USER', 'postgres'),
                password=os.getenv('DB_PASSWORD', 'postgres')
            )
            self.cur = self.conn.cursor(cursor_factory=RealDictCursor)
            print("✅ 데이터베이스 연결 성공")
        except Exception as e:
            print(f"❌ 데이터베이스 연결 실패: {e}")
            sys.exit(1)
        
        self.embed_api_url = os.getenv('EMBED_API_URL', 'http://localhost:8001/embed')
    
    def check_data_status(self) -> Dict:
        """데이터 상태 확인"""
        print("\n" + "=" * 100)
        print("데이터 상태 확인")
        print("=" * 100)
        
        # 총 청크 및 임베딩 상태
        self.cur.execute("""
            SELECT 
                COUNT(*) as total_chunks,
                COUNT(CASE WHEN embedding IS NOT NULL THEN 1 END) as embedded_chunks,
                COUNT(CASE WHEN drop = FALSE THEN 1 END) as active_chunks,
                COUNT(CASE WHEN drop = FALSE AND embedding IS NOT NULL THEN 1 END) as searchable_chunks
            FROM chunks
        """)
        
        stats = dict(self.cur.fetchone())
        
        print(f"\n📊 청크 통계:")
        print(f"  - 총 청크: {stats['total_chunks']:,}개")
        print(f"  - 활성 청크: {stats['active_chunks']:,}개")
        print(f"  - 임베딩 완료: {stats['embedded_chunks']:,}개")
        print(f"  - 검색 가능: {stats['searchable_chunks']:,}개")
        
        if stats['searchable_chunks'] > 0:
            embed_rate = stats['embedded_chunks'] / stats['total_chunks'] * 100
            searchable_rate = stats['searchable_chunks'] / stats['active_chunks'] * 100
            print(f"\n  임베딩 완료율: {embed_rate:.1f}%")
            print(f"  검색 가능율: {searchable_rate:.1f}%")
        
        return stats
    
    def get_query_embedding(self, query: str) -> List[float]:
        """쿼리 임베딩 생성"""
        try:
            response = requests.post(
                self.embed_api_url,
                json={"texts": [query]},
                timeout=30
            )
            response.raise_for_status()
            embeddings = response.json()['embeddings']
            return embeddings[0]
        except requests.exceptions.RequestException as e:
            print(f"  ❌ 임베딩 API 오류: {e}")
            return None
    
    def search_chunks(self, query: str, top_k: int = 10, 
                     doc_types: List[str] = None) -> List[Dict]:
        """청크 검색"""
        # 쿼리 임베딩 생성
        query_embedding = self.get_query_embedding(query)
        if query_embedding is None:
            return []
        
        # 검색
        if doc_types:
            query_sql = """
                SELECT 
                    c.chunk_id,
                    c.doc_id,
                    c.chunk_type,
                    c.content,
                    c.content_length,
                    d.doc_type,
                    d.title,
                    d.source_org,
                    1 - (c.embedding <=> %s::vector) AS similarity
                FROM chunks c
                JOIN documents d ON c.doc_id = d.doc_id
                WHERE 
                    c.drop = FALSE
                    AND c.embedding IS NOT NULL
                    AND d.doc_type = ANY(%s)
                ORDER BY c.embedding <=> %s::vector
                LIMIT %s
            """
            params = [query_embedding, doc_types, query_embedding, top_k]
        else:
            query_sql = """
                SELECT 
                    c.chunk_id,
                    c.doc_id,
                    c.chunk_type,
                    c.content,
                    c.content_length,
                    d.doc_type,
                    d.title,
                    d.source_org,
                    1 - (c.embedding <=> %s::vector) AS similarity
                FROM chunks c
                JOIN documents d ON c.doc_id = d.doc_id
                WHERE 
                    c.drop = FALSE
                    AND c.embedding IS NOT NULL
                ORDER BY c.embedding <=> %s::vector
                LIMIT %s
            """
            params = [query_embedding, query_embedding, top_k]
        
        self.cur.execute(query_sql, params)
        return [dict(row) for row in self.cur.fetchall()]
    
    def evaluate_relevance(self, query: str, result: Dict) -> Dict:
        """결과 관련성 평가 (간단한 키워드 기반)"""
        content = result['content'].lower()
        query_terms = query.lower().split()
        
        # 키워드 매칭
        matched_terms = [term for term in query_terms if term in content]
        keyword_score = len(matched_terms) / len(query_terms) if query_terms else 0
        
        return {
            'keyword_score': keyword_score,
            'matched_terms': matched_terms,
            'similarity': result['similarity']
        }
    
    def run_test_queries(self) -> List[Dict]:
        """테스트 쿼리 실행"""
        print("\n" + "=" * 100)
        print("검색 품질 테스트")
        print("=" * 100)
        
        test_cases = [
            {
                'id': 1,
                'query': '온라인 쇼핑몰에서 구매한 제품이 불량이에요. 환불 받을 수 있나요?',
                'doc_types': ['counsel_case', 'mediation_case'],
                'expected_keywords': ['불량', '환불', '온라인', '쇼핑']
            },
            {
                'id': 2,
                'query': '배송비가 과다하게 청구되었습니다',
                'doc_types': ['counsel_case', 'mediation_case'],
                'expected_keywords': ['배송비', '청구']
            },
            {
                'id': 3,
                'query': '전자상거래 계약 해지 시 위약금을 받았습니다',
                'doc_types': ['counsel_case', 'mediation_case'],
                'expected_keywords': ['계약', '해지', '위약금']
            },
            {
                'id': 4,
                'query': '식품 표시가 잘못되어 있습니다',
                'doc_types': ['counsel_case'],
                'expected_keywords': ['식품', '표시']
            },
            {
                'id': 5,
                'query': '통신판매업자의 거짓 광고',
                'doc_types': ['counsel_case', 'mediation_case'],
                'expected_keywords': ['통신판매', '광고', '거짓']
            }
        ]
        
        results = []
        
        for test_case in test_cases:
            print(f"\n[테스트 {test_case['id']}] {test_case['query']}")
            print("-" * 100)
            
            search_results = self.search_chunks(
                query=test_case['query'],
                top_k=5,
                doc_types=test_case.get('doc_types')
            )
            
            if not search_results:
                print("  ❌ 검색 결과 없음")
                results.append({
                    'test_id': test_case['id'],
                    'query': test_case['query'],
                    'success': False,
                    'results_count': 0
                })
                continue
            
            print(f"  ✅ {len(search_results)}개 결과 발견")
            
            # 상위 3개 결과 평가
            evaluations = []
            for idx, result in enumerate(search_results[:3], 1):
                eval_result = self.evaluate_relevance(test_case['query'], result)
                evaluations.append(eval_result)
                
                print(f"\n  [{idx}] 유사도: {result['similarity']:.4f}, "
                      f"키워드 매칭: {eval_result['keyword_score']:.2f}")
                print(f"      타입: {result['doc_type']}/{result['chunk_type']}, "
                      f"길이: {result['content_length']}자")
                print(f"      제목: {result['title'][:80]}")
                print(f"      내용: {result['content'][:150].replace(chr(10), ' ')}...")
            
            # 테스트 결과 저장
            avg_similarity = sum(e['similarity'] for e in evaluations) / len(evaluations)
            avg_keyword_score = sum(e['keyword_score'] for e in evaluations) / len(evaluations)
            
            results.append({
                'test_id': test_case['id'],
                'query': test_case['query'],
                'success': True,
                'results_count': len(search_results),
                'avg_similarity': avg_similarity,
                'avg_keyword_score': avg_keyword_score,
                'top_similarity': search_results[0]['similarity'],
                'evaluations': evaluations
            })
        
        return results
    
    def generate_report(self, test_results: List[Dict], stats: Dict) -> str:
        """테스트 리포트 생성"""
        print("\n" + "=" * 100)
        print("검색 품질 테스트 리포트 생성")
        print("=" * 100)
        
        report = []
        report.append("=" * 100)
        report.append("검색 품질 테스트 리포트")
        report.append("=" * 100)
        report.append(f"생성 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # 1. 데이터 상태
        report.append("1. 데이터 상태")
        report.append("-" * 100)
        report.append(f"총 청크: {stats['total_chunks']:,}개")
        report.append(f"활성 청크: {stats['active_chunks']:,}개")
        report.append(f"검색 가능 청크: {stats['searchable_chunks']:,}개")
        
        if stats['searchable_chunks'] > 0:
            searchable_rate = stats['searchable_chunks'] / stats['active_chunks'] * 100
            report.append(f"검색 가능율: {searchable_rate:.1f}%")
        
        report.append("")
        
        # 2. 테스트 결과 요약
        report.append("2. 테스트 결과 요약")
        report.append("-" * 100)
        
        successful_tests = [r for r in test_results if r['success']]
        
        if successful_tests:
            avg_similarity = sum(r['avg_similarity'] for r in successful_tests) / len(successful_tests)
            avg_keyword = sum(r['avg_keyword_score'] for r in successful_tests) / len(successful_tests)
            avg_top_sim = sum(r['top_similarity'] for r in successful_tests) / len(successful_tests)
            
            report.append(f"성공한 테스트: {len(successful_tests)}/{len(test_results)}개")
            report.append(f"평균 유사도 (상위 3개): {avg_similarity:.4f}")
            report.append(f"평균 키워드 매칭 점수: {avg_keyword:.2f}")
            report.append(f"최고 유사도 평균: {avg_top_sim:.4f}")
        else:
            report.append("❌ 성공한 테스트 없음")
        
        report.append("")
        
        # 3. 테스트별 상세 결과
        report.append("3. 테스트별 상세 결과")
        report.append("-" * 100)
        
        for result in test_results:
            report.append(f"\n[테스트 {result['test_id']}] {result['query']}")
            
            if result['success']:
                report.append(f"  ✅ 성공: {result['results_count']}개 결과")
                report.append(f"  평균 유사도: {result['avg_similarity']:.4f}")
                report.append(f"  키워드 매칭: {result['avg_keyword_score']:.2f}")
                report.append(f"  최고 유사도: {result['top_similarity']:.4f}")
            else:
                report.append(f"  ❌ 실패: 검색 결과 없음")
        
        report.append("")
        
        # 4. 품질 평가
        report.append("4. 검색 품질 평가")
        report.append("-" * 100)
        
        if successful_tests:
            if avg_similarity >= 0.7:
                report.append("✅ 우수: 평균 유사도 0.7 이상")
            elif avg_similarity >= 0.5:
                report.append("⚠️  양호: 평균 유사도 0.5 이상")
            else:
                report.append("❌ 개선 필요: 평균 유사도 0.5 미만")
            
            if avg_keyword >= 0.3:
                report.append("✅ 키워드 매칭 양호")
            else:
                report.append("⚠️  키워드 매칭 개선 필요")
        
        report.append("")
        
        # 5. 개선 사항
        report.append("5. 권장 사항")
        report.append("-" * 100)
        
        if stats['searchable_chunks'] < stats['active_chunks']:
            remaining = stats['active_chunks'] - stats['searchable_chunks']
            report.append(f"⚠️  {remaining:,}개 청크의 임베딩 생성 필요")
        
        if successful_tests and avg_similarity < 0.7:
            report.append("⚠️  임베딩 모델 개선 또는 청크 크기 재조정 검토 필요")
        
        report.append("")
        report.append("=" * 100)
        
        return "\n".join(report)
    
    def save_report(self, report: str, output_file: str = None):
        """리포트 저장"""
        if output_file is None:
            output_file = "backend/data/transformed/search_quality_report.txt"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"\n💾 리포트 저장: {output_file}")
    
    def run(self):
        """테스트 실행"""
        print("=" * 100)
        print("검색 품질 테스트 시작")
        print("=" * 100)
        
        try:
            # 1. 데이터 상태 확인
            stats = self.check_data_status()
            
            if stats['searchable_chunks'] == 0:
                print("\n❌ 검색 가능한 청크가 없습니다.")
                print("   임베딩을 먼저 생성하세요: python backend/scripts/embedding/embed_data_remote.py")
                return 1
            
            # 2. 테스트 쿼리 실행
            test_results = self.run_test_queries()
            
            # 3. 리포트 생성
            report = self.generate_report(test_results, stats)
            
            # 4. 출력 및 저장
            print("\n" + report)
            self.save_report(report)
            
            print("\n✅ 테스트 완료!")
            return 0
            
        except Exception as e:
            print(f"\n❌ 오류 발생: {e}")
            import traceback
            traceback.print_exc()
            return 1
        finally:
            if self.cur:
                self.cur.close()
            if self.conn:
                self.conn.close()

def main():
    """메인 함수"""
    tester = SearchQualityTester()
    return tester.run()

if __name__ == '__main__':
    sys.exit(main())
