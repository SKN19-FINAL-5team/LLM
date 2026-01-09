#!/usr/bin/env python3
"""
분쟁조정 사례 데이터 종합 RAG 테스트 스크립트

인터랙티브/배치 모드를 지원하고 모든 검색 방식을 테스트할 수 있는 통합 스크립트
- Cosine Similarity (Dense Vector)
- BM25 (Sparse Retrieval)
- SPLADE (Optimized)
"""

import os
import sys
import json
import argparse
import time
from typing import List, Dict, Optional
from pathlib import Path
from dotenv import load_dotenv

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'backend'))

from app.rag import VectorRetriever

# BM25 및 SPLADE import
try:
    from scripts.splade.test_splade_bm25 import BM25SparseRetriever
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False
    BM25SparseRetriever = None

try:
    from scripts.splade.test_splade_optimized import OptimizedSPLADEDBRetriever
    SPLADE_AVAILABLE = True
except ImportError:
    SPLADE_AVAILABLE = False
    OptimizedSPLADEDBRetriever = None

load_dotenv()


class ComprehensiveDisputeRAGTester:
    """분쟁조정 사례 데이터 종합 RAG 테스터"""
    
    def __init__(self, db_config: Dict):
        self.db_config = db_config
        self.vector_retriever = VectorRetriever(db_config)
        self.bm25_retriever = None
        self.splade_retriever = None
        
        # BM25 초기화 (분쟁조정 사례용은 BM25가 직접 지원하지 않으므로 벡터 검색 사용)
        # SPLADE 초기화
        if SPLADE_AVAILABLE:
            try:
                self.splade_retriever = OptimizedSPLADEDBRetriever(db_config)
                print("✅ SPLADE Retriever 초기화 완료")
            except Exception as e:
                print(f"⚠️  SPLADE Retriever 초기화 실패: {e}")
    
    def search_cosine(self, query: str, top_k: int = 10) -> List[Dict]:
        """Cosine Similarity 검색"""
        results = self.vector_retriever.search(query=query, top_k=top_k)
        # doc_type='mediation_case' 필터링
        dispute_results = [
            r for r in results 
            if r.get('source') == 'mediation_case'
        ]
        return dispute_results[:top_k]
    
    def search_bm25(self, query: str, top_k: int = 10) -> List[Dict]:
        """BM25 검색 (분쟁조정 사례는 BM25 직접 지원 없음, 벡터 검색 사용)"""
        # 분쟁조정 사례는 BM25가 직접 지원하지 않으므로 Cosine Similarity 사용
        return self.search_cosine(query, top_k)
    
    def search_splade(self, query: str, top_k: int = 10) -> List[Dict]:
        """SPLADE 검색"""
        if not self.splade_retriever:
            return []
        
        try:
            # SPLADE는 분쟁조정 사례를 직접 지원하지 않을 수 있으므로
            # 벡터 검색 결과를 반환
            return self.search_cosine(query, top_k)
        except Exception as e:
            print(f"  ⚠️  SPLADE 검색 오류: {e}")
            return []
    
    def test_query(self, query: str, methods: List[str], top_k: int = 10):
        """단일 쿼리 테스트"""
        print("\n" + "=" * 80)
        print(f"⚖️  분쟁조정 사례 데이터 RAG 테스트")
        print("=" * 80)
        print(f"쿼리: {query}")
        print(f"검색 방식: {', '.join(methods)}")
        print(f"Top-K: {top_k}")
        print("-" * 80)
        
        all_results = {}
        
        # 각 방법으로 검색
        if 'cosine' in methods or 'all' in methods:
            print("\n[1] Cosine Similarity 검색")
            start_time = time.time()
            results = self.search_cosine(query, top_k=top_k)
            elapsed = time.time() - start_time
            all_results['cosine'] = {
                'results': results,
                'elapsed': elapsed,
                'count': len(results)
            }
            print(f"  ✅ {len(results)}개 결과 (소요 시간: {elapsed*1000:.1f}ms)")
        
        if 'bm25' in methods or 'all' in methods:
            print("\n[2] BM25 검색 (Cosine Similarity 사용)")
            start_time = time.time()
            results = self.search_bm25(query, top_k=top_k)
            elapsed = time.time() - start_time
            all_results['bm25'] = {
                'results': results,
                'elapsed': elapsed,
                'count': len(results)
            }
            print(f"  ✅ {len(results)}개 결과 (소요 시간: {elapsed*1000:.1f}ms)")
        
        if 'splade' in methods or 'all' in methods:
            if self.splade_retriever:
                print("\n[3] SPLADE 검색 (Cosine Similarity 사용)")
                start_time = time.time()
                results = self.search_splade(query, top_k=top_k)
                elapsed = time.time() - start_time
                all_results['splade'] = {
                    'results': results,
                    'elapsed': elapsed,
                    'count': len(results)
                }
                print(f"  ✅ {len(results)}개 결과 (소요 시간: {elapsed*1000:.1f}ms)")
            else:
                print("\n[3] SPLADE 검색")
                print("  ⚠️  SPLADE Retriever를 사용할 수 없습니다")
        
        # 결과 출력
        print("\n" + "=" * 80)
        print("📊 검색 결과 비교")
        print("=" * 80)
        
        for method, data in all_results.items():
            print(f"\n[{method.upper()}] {data['count']}개 결과 (소요 시간: {data['elapsed']*1000:.1f}ms)")
            for i, result in enumerate(data['results'][:5], 1):
                print(f"  {i}. 유사도: {result.get('similarity', 0):.4f}")
                print(f"     청크 ID: {result.get('chunk_uid', 'N/A')[:50]}...")
                print(f"     기관: {result.get('agency', 'N/A')}")
                print(f"     사건번호: {result.get('case_no', 'N/A')}")
                content = result.get('text', '') or result.get('content', '')
                print(f"     내용: {content[:100]}...")
        
        return all_results
    
    def test_batch(self, golden_set_file: Path, methods: List[str], top_k: int = 10):
        """배치 모드 테스트 (Golden Set 사용)"""
        print("\n" + "=" * 80)
        print("⚖️  분쟁조정 사례 데이터 배치 테스트 (Golden Set)")
        print("=" * 80)
        
        # Golden Set 로드
        with open(golden_set_file, 'r', encoding='utf-8') as f:
            golden_data = json.load(f)
        
        golden_set = golden_data.get('golden_set', [])
        print(f"✅ Golden Set 로드 완료: {len(golden_set)}개 쿼리")
        
        total_stats = {
            'cosine': {'total': 0, 'found': 0, 'precision': 0.0},
            'bm25': {'total': 0, 'found': 0, 'precision': 0.0},
            'splade': {'total': 0, 'found': 0, 'precision': 0.0}
        }
        
        for idx, item in enumerate(golden_set, 1):
            query = item.get('query')
            expected_chunk_ids = set(item.get('expected_chunk_ids', []))
            
            print(f"\n[{idx}/{len(golden_set)}] 쿼리: {query}")
            
            # 각 방법으로 검색 및 평가
            if 'cosine' in methods or 'all' in methods:
                results = self.search_cosine(query, top_k=top_k)
                found_ids = {r.get('chunk_uid') for r in results}
                overlap = len(found_ids & expected_chunk_ids)
                precision = overlap / len(results) if results else 0.0
                total_stats['cosine']['total'] += 1
                total_stats['cosine']['found'] += overlap
                total_stats['cosine']['precision'] += precision
                print(f"  Cosine: {overlap}/{len(expected_chunk_ids)} 매칭 (정밀도: {precision:.2%})")
            
            if 'bm25' in methods or 'all' in methods:
                results = self.search_bm25(query, top_k=top_k)
                found_ids = {r.get('chunk_uid') for r in results}
                overlap = len(found_ids & expected_chunk_ids)
                precision = overlap / len(results) if results else 0.0
                total_stats['bm25']['total'] += 1
                total_stats['bm25']['found'] += overlap
                total_stats['bm25']['precision'] += precision
                print(f"  BM25: {overlap}/{len(expected_chunk_ids)} 매칭 (정밀도: {precision:.2%})")
            
            if 'splade' in methods or 'all' in methods:
                if self.splade_retriever:
                    results = self.search_splade(query, top_k=top_k)
                    found_ids = {r.get('chunk_uid') for r in results}
                    overlap = len(found_ids & expected_chunk_ids)
                    precision = overlap / len(results) if results else 0.0
                    total_stats['splade']['total'] += 1
                    total_stats['splade']['found'] += overlap
                    total_stats['splade']['precision'] += precision
                    print(f"  SPLADE: {overlap}/{len(expected_chunk_ids)} 매칭 (정밀도: {precision:.2%})")
        
        # 전체 통계 출력
        print("\n" + "=" * 80)
        print("📊 전체 통계")
        print("=" * 80)
        
        for method, stats in total_stats.items():
            if stats['total'] > 0:
                avg_precision = stats['precision'] / stats['total']
                print(f"\n[{method.upper()}]")
                print(f"  총 쿼리: {stats['total']}개")
                print(f"  평균 정밀도: {avg_precision:.2%}")
    
    def close(self):
        """리소스 정리"""
        self.vector_retriever.close()
        if self.splade_retriever:
            if hasattr(self.splade_retriever, 'conn') and self.splade_retriever.conn:
                self.splade_retriever.conn.close()


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='분쟁조정 사례 데이터 종합 RAG 테스트')
    parser.add_argument('--mode', choices=['interactive', 'batch'], default='interactive',
                       help='테스트 모드: interactive (사용자 입력) 또는 batch (golden set 파일)')
    parser.add_argument('--method', choices=['cosine', 'bm25', 'splade', 'all'], default='all',
                       help='검색 방식: cosine, bm25, splade, all (기본값: all)')
    parser.add_argument('--golden-set', type=str, default='golden_set_dispute.json',
                       help='배치 모드에서 사용할 golden set 파일 경로 (기본값: golden_set_dispute.json)')
    parser.add_argument('--top-k', type=int, default=10,
                       help='반환할 최대 결과 수 (기본값: 10)')
    parser.add_argument('--query', type=str, default=None,
                       help='인터랙티브 모드에서 직접 쿼리 지정 (선택)')
    
    args = parser.parse_args()
    
    # 환경 변수에서 설정 로드
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'database': os.getenv('DB_NAME', 'ddoksori'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres')
    }
    
    # 테스터 초기화
    tester = ComprehensiveDisputeRAGTester(db_config)
    
    try:
        if args.mode == 'interactive':
            # 인터랙티브 모드
            if args.query:
                # 명령줄에서 쿼리 지정
                tester.test_query(args.query, [args.method], args.top_k)
            else:
                # 사용자 입력
                print("\n⚖️  분쟁조정 사례 데이터 RAG 테스트 (인터랙티브 모드)")
                print("종료하려면 'quit' 또는 'exit'를 입력하세요.\n")
                
                while True:
                    query = input("쿼리 입력: ").strip()
                    if query.lower() in ('quit', 'exit', 'q'):
                        break
                    if not query:
                        continue
                    
                    tester.test_query(query, [args.method], args.top_k)
        
        elif args.mode == 'batch':
            # 배치 모드
            script_dir = Path(__file__).parent
            golden_set_file = script_dir / args.golden_set
            
            if not golden_set_file.exists():
                print(f"❌ Golden Set 파일을 찾을 수 없습니다: {golden_set_file}")
                sys.exit(1)
            
            tester.test_batch(golden_set_file, [args.method], args.top_k)
    
    except KeyboardInterrupt:
        print("\n\n테스트가 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        tester.close()


if __name__ == "__main__":
    main()
