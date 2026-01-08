#!/usr/bin/env python3
"""
간단한 RAG 테스트 스크립트

사례 데이터(mediation_case, counsel_case)에 대한 유사도 검색 테스트

Requirements:
- 변환된 데이터가 DB에 삽입되어 있어야 함
- 임베딩이 생성되어 있어야 함
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import requests
from typing import List, Dict
import json

load_dotenv()

class SimpleRAGTester:
    """간단한 RAG 테스트"""
    
    def __init__(self):
        """초기화"""
        self.conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5432'),
            database=os.getenv('DB_NAME', 'ddoksori'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', 'postgres')
        )
        self.cur = self.conn.cursor(cursor_factory=RealDictCursor)
        
        self.embed_api_url = os.getenv('EMBED_API_URL', 'http://localhost:8001/embed')
        
        print("✅ 데이터베이스 연결 성공")
    
    def check_data_status(self) -> Dict:
        """데이터 상태 확인"""
        print("\n" + "=" * 80)
        print("데이터 상태 확인")
        print("=" * 80)
        
        # 1. 문서 수
        self.cur.execute("""
            SELECT doc_type, COUNT(*) as count
            FROM documents
            GROUP BY doc_type
            ORDER BY doc_type
        """)
        doc_counts = {row['doc_type']: row['count'] for row in self.cur.fetchall()}
        
        print("\n📊 문서 통계:")
        for doc_type, count in doc_counts.items():
            print(f"  - {doc_type}: {count:,}개")
        
        # 2. 청크 수 및 임베딩 상태
        self.cur.execute("""
            SELECT 
                d.doc_type,
                COUNT(*) as total_chunks,
                COUNT(CASE WHEN c.embedding IS NOT NULL THEN 1 END) as embedded_chunks,
                COUNT(CASE WHEN c.drop = FALSE THEN 1 END) as active_chunks
            FROM chunks c
            JOIN documents d ON c.doc_id = d.doc_id
            GROUP BY d.doc_type
            ORDER BY d.doc_type
        """)
        
        print("\n📊 청크 통계:")
        chunk_stats = {}
        for row in self.cur.fetchall():
            doc_type = row['doc_type']
            chunk_stats[doc_type] = row
            
            embedded_rate = (row['embedded_chunks'] / row['total_chunks'] * 100) if row['total_chunks'] > 0 else 0
            print(f"  [{doc_type}]")
            print(f"    - 총 청크: {row['total_chunks']:,}개")
            print(f"    - 임베딩 완료: {row['embedded_chunks']:,}개 ({embedded_rate:.1f}%)")
            print(f"    - 활성 청크: {row['active_chunks']:,}개")
        
        # 3. 사례 데이터 (mediation_case, counsel_case) 확인
        case_types = ['mediation_case', 'counsel_case']
        case_available = {ct: ct in doc_counts and chunk_stats.get(ct, {}).get('embedded_chunks', 0) > 0 
                         for ct in case_types}
        
        print("\n🔍 사례 데이터 임베딩 상태:")
        for case_type in case_types:
            if case_available[case_type]:
                print(f"  ✅ {case_type}: 사용 가능")
            else:
                print(f"  ❌ {case_type}: 사용 불가 (데이터 없음 또는 임베딩 미완료)")
        
        return {
            'doc_counts': doc_counts,
            'chunk_stats': chunk_stats,
            'case_available': case_available,
            'ready': any(case_available.values())
        }
    
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
            print(f"❌ 임베딩 API 오류: {e}")
            print(f"   API URL: {self.embed_api_url}")
            print("   임베딩 서버가 실행 중인지 확인하세요.")
            return None
    
    def search_similar_cases(self, query: str, top_k: int = 5, min_similarity: float = 0.0) -> List[Dict]:
        """
        사례 데이터에서 유사한 청크 검색
        
        Args:
            query: 검색 쿼리
            top_k: 상위 k개 결과
            min_similarity: 최소 유사도
        
        Returns:
            검색 결과 리스트
        """
        print(f"\n🔍 검색 쿼리: {query}")
        print(f"   top_k: {top_k}, min_similarity: {min_similarity}")
        
        # 1. 쿼리 임베딩 생성
        query_embedding = self.get_query_embedding(query)
        if query_embedding is None:
            return []
        
        print("   ✅ 쿼리 임베딩 생성 완료")
        
        # 2. 유사도 검색 (사례 데이터만)
        self.cur.execute("""
            SELECT 
                c.chunk_id,
                c.doc_id,
                c.chunk_type,
                c.content,
                c.content_length,
                d.doc_type,
                d.title,
                d.source_org,
                d.metadata,
                1 - (c.embedding <=> %s::vector) AS similarity
            FROM chunks c
            JOIN documents d ON c.doc_id = d.doc_id
            WHERE 
                c.drop = FALSE
                AND c.embedding IS NOT NULL
                AND d.doc_type IN ('mediation_case', 'counsel_case')
                AND 1 - (c.embedding <=> %s::vector) >= %s
            ORDER BY c.embedding <=> %s::vector
            LIMIT %s
        """, (query_embedding, query_embedding, min_similarity, query_embedding, top_k))
        
        results = self.cur.fetchall()
        
        print(f"   ✅ {len(results)}개 결과 발견")
        
        return [dict(row) for row in results]
    
    def display_results(self, results: List[Dict]):
        """검색 결과 출력"""
        print("\n" + "=" * 80)
        print("검색 결과")
        print("=" * 80)
        
        if not results:
            print("❌ 검색 결과가 없습니다.")
            return
        
        for idx, result in enumerate(results, 1):
            print(f"\n[{idx}] 유사도: {result['similarity']:.4f}")
            print(f"    문서 유형: {result['doc_type']}")
            print(f"    출처: {result['source_org']}")
            print(f"    제목: {result['title']}")
            print(f"    청크 ID: {result['chunk_id']}")
            print(f"    청크 타입: {result['chunk_type']}")
            print(f"    길이: {result['content_length']}자")
            
            # 내용 미리보기
            content_preview = result['content'][:300].replace('\n', ' ')
            print(f"    내용: {content_preview}...")
            
            # 메타데이터
            if result.get('metadata'):
                metadata = result['metadata']
                if isinstance(metadata, str):
                    try:
                        metadata = json.loads(metadata)
                    except:
                        pass
                
                if isinstance(metadata, dict):
                    if 'case_no' in metadata:
                        print(f"    사건번호: {metadata['case_no']}")
                    if 'decision_date' in metadata:
                        print(f"    결정일: {metadata['decision_date']}")
    
    def run_test_queries(self):
        """테스트 쿼리 실행"""
        print("\n" + "=" * 80)
        print("RAG 테스트 쿼리 실행")
        print("=" * 80)
        
        test_queries = [
            {
                'query': '온라인 쇼핑몰에서 구매한 제품이 불량이에요. 환불 받을 수 있나요?',
                'top_k': 3,
                'min_similarity': 0.3
            },
            {
                'query': '배송비 과다 청구 문제로 분쟁이 생겼습니다.',
                'top_k': 3,
                'min_similarity': 0.3
            },
            {
                'query': '전자상거래 계약 해지 시 위약금을 청구받았습니다.',
                'top_k': 3,
                'min_similarity': 0.3
            }
        ]
        
        for test in test_queries:
            print("\n" + "-" * 80)
            results = self.search_similar_cases(
                query=test['query'],
                top_k=test['top_k'],
                min_similarity=test['min_similarity']
            )
            self.display_results(results)
            print("-" * 80)
    
    def interactive_search(self):
        """대화형 검색"""
        print("\n" + "=" * 80)
        print("대화형 검색 모드")
        print("=" * 80)
        print("사례 데이터에서 유사한 내용을 검색합니다.")
        print("종료하려면 'quit' 또는 'exit'를 입력하세요.")
        print("-" * 80)
        
        while True:
            try:
                query = input("\n🔍 검색어: ").strip()
                
                if query.lower() in ['quit', 'exit', 'q']:
                    print("종료합니다.")
                    break
                
                if not query:
                    continue
                
                results = self.search_similar_cases(
                    query=query,
                    top_k=5,
                    min_similarity=0.3
                )
                self.display_results(results)
                
            except KeyboardInterrupt:
                print("\n\n종료합니다.")
                break
            except Exception as e:
                print(f"❌ 오류: {e}")
    
    def close(self):
        """리소스 정리"""
        if self.cur:
            self.cur.close()
        if self.conn:
            self.conn.close()

def main():
    """메인 함수"""
    import sys
    
    tester = SimpleRAGTester()
    
    try:
        # 1. 데이터 상태 확인
        status = tester.check_data_status()
        
        if not status['ready']:
            print("\n" + "=" * 80)
            print("❌ RAG 테스트를 실행할 수 없습니다.")
            print("=" * 80)
            print("\n다음 단계를 먼저 수행하세요:")
            print("1. 데이터 변환: python backend/scripts/data_processing/data_transform_pipeline.py")
            print("2. DB 삽입: (데이터 변환 스크립트에 DB 삽입 기능 추가)")
            print("3. 임베딩 생성: python backend/scripts/embedding/embed_data_remote.py")
            return 1
        
        print("\n✅ RAG 테스트 준비 완료!")
        
        # 2. 모드 선택
        if len(sys.argv) > 1 and sys.argv[1] == '--test':
            # 테스트 모드: 미리 정의된 쿼리 실행
            tester.run_test_queries()
        else:
            # 대화형 모드
            tester.interactive_search()
        
        return 0
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        tester.close()

if __name__ == '__main__':
    exit(main())
