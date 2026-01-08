"""
법령/분쟁조정기준 데이터 특성에 맞는 SPLADE 가중치 튜닝 및 최적화
"""

import os
import sys
import json
import numpy as np
from typing import Dict, List, Optional
from pathlib import Path
from dotenv import load_dotenv

# 프로젝트 루트 경로 추가
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# 환경 변수 로드
env_file = backend_dir / '.env'
if env_file.exists():
    load_dotenv(env_file)
else:
    root_env = backend_dir.parent / '.env'
    if root_env.exists():
        load_dotenv(root_env)
    else:
        load_dotenv()

# SPLADE 모듈 import
try:
    from scripts.splade.test_splade_naver import NaverSPLADERetriever
    from scripts.splade.test_splade_optimized import OptimizedSPLADEDBRetriever
except ImportError as e:
    print(f"⚠️  SPLADE 모듈을 찾을 수 없습니다: {e}")
    sys.exit(1)


class SPLADEDomainOptimizer:
    """SPLADE 도메인 최적화 클래스"""
    
    def __init__(self, db_config: Dict):
        """
        Args:
            db_config: 데이터베이스 연결 설정
        """
        self.db_config = db_config
        self.splade_retriever = None
        
        # 법령 특화 키워드 패턴
        self.law_patterns = {
            'article_number': r'제\s*\d+\s*조',  # 조문 번호
            'paragraph_number': r'제\s*\d+\s*항',  # 항 번호
            'law_names': [
                '민법', '상법', '소비자기본법', '전자상거래법', 
                '약관규제법', '소비자분쟁조정법'
            ]
        }
        
        # 기준 특화 키워드 패턴
        self.criteria_patterns = {
            'item_names': [
                '냉장고', '세탁기', '에어컨', 'TV', '텔레비전', 
                '스마트폰', '휴대폰', '노트북', '컴퓨터', '모니터',
                '프린터', '청소기', '전자레인지', '밥솥', '정수기',
                '공기청정기', '가습기', '선풍기', '보일러', '비데'
            ],
            'dispute_types': [
                '환불', '반품', '취소', '교환', '수리', '보증',
                '품질', '불량', '고장', '손상', '배송', '지연'
            ]
        }
    
    def boost_article_tokens(self, sparse_vec: np.ndarray, query: str) -> np.ndarray:
        """
        조문 번호 토큰 가중치 부스팅
        
        Args:
            sparse_vec: Sparse vector
            query: 검색 쿼리
        
        Returns:
            가중치가 부스팅된 sparse vector
        """
        import re
        
        # 조문 번호 추출
        article_match = re.search(self.law_patterns['article_number'], query)
        if article_match:
            article_text = article_match.group(0)
            # 조문 번호 관련 토큰 가중치 부스팅
            # 실제 구현에서는 토크나이저를 통해 토큰 ID를 찾아야 함
            # 여기서는 예시로 보여줌
            boost_factor = 1.5  # 50% 가중치 증가
            # TODO: 실제 토큰 ID 매핑 구현 필요
        
        return sparse_vec
    
    def boost_item_tokens(self, sparse_vec: np.ndarray, query: str) -> np.ndarray:
        """
        품목명 토큰 가중치 부스팅
        
        Args:
            sparse_vec: Sparse vector
            query: 검색 쿼리
        
        Returns:
            가중치가 부스팅된 sparse vector
        """
        # 품목명 확인
        for item in self.criteria_patterns['item_names']:
            if item in query:
                boost_factor = 1.3  # 30% 가중치 증가
                # TODO: 실제 토큰 ID 매핑 구현 필요
                break
        
        return sparse_vec
    
    def optimize_law_search(
        self,
        retriever: OptimizedSPLADEDBRetriever,
        query: str,
        top_k: int = 10
    ) -> List[Dict]:
        """
        법령 검색 최적화
        
        전략:
        1. 조문 번호 정확 매칭 우선
        2. 법령명 + 조문 조합 검색
        3. 법률 용어 확장 검색
        
        Args:
            retriever: 최적화된 SPLADE Retriever
            query: 검색 쿼리
            top_k: 반환할 상위 결과 수
        
        Returns:
            검색 결과 리스트
        """
        # 기본 검색 수행
        results = retriever.search_law_splade_optimized(query, top_k=top_k * 2)
        
        # 조문 번호가 있는 경우 정확 매칭 우선 정렬
        import re
        article_match = re.search(self.law_patterns['article_number'], query)
        if article_match:
            article_text = article_match.group(0)
            
            # 조문 번호가 포함된 결과를 상위로 이동
            prioritized = []
            others = []
            
            for r in results:
                if article_text in r.get('content', ''):
                    prioritized.append(r)
                else:
                    others.append(r)
            
            results = prioritized + others
        
        # 법령명 확인 및 필터링
        for law_name in self.law_patterns['law_names']:
            if law_name in query:
                # 해당 법령의 결과를 우선시
                law_results = [r for r in results if law_name in r.get('law_name', '') or law_name in r.get('content', '')]
                other_results = [r for r in results if r not in law_results]
                results = law_results + other_results
                break
        
        return results[:top_k]
    
    def optimize_criteria_search(
        self,
        retriever: OptimizedSPLADEDBRetriever,
        query: str,
        top_k: int = 10
    ) -> List[Dict]:
        """
        기준 검색 최적화
        
        전략:
        1. 품목명 정확 매칭 우선
        2. 카테고리 계층 구조 반영
        3. 분쟁유형 키워드 확장
        
        Args:
            retriever: 최적화된 SPLADE Retriever
            query: 검색 쿼리
            top_k: 반환할 상위 결과 수
        
        Returns:
            검색 결과 리스트
        """
        # 기본 검색 수행
        results = retriever.search_criteria_splade_optimized(query, top_k=top_k * 2)
        
        # 품목명 확인 및 우선 정렬
        for item in self.criteria_patterns['item_names']:
            if item in query:
                # 해당 품목의 결과를 우선시
                item_results = [
                    r for r in results 
                    if item in r.get('item', '') or item in r.get('content', '')
                ]
                other_results = [r for r in results if r not in item_results]
                results = item_results + other_results
                break
        
        # 분쟁유형 확인 및 확장
        dispute_keywords = []
        for dispute_type in self.criteria_patterns['dispute_types']:
            if dispute_type in query:
                dispute_keywords.append(dispute_type)
        
        if dispute_keywords:
            # 분쟁유형 키워드가 포함된 결과를 우선시
            dispute_results = [
                r for r in results
                if any(keyword in r.get('content', '') for keyword in dispute_keywords)
            ]
            other_results = [r for r in results if r not in dispute_results]
            results = dispute_results + other_results
        
        return results[:top_k]
    
    def create_hybrid_search(
        self,
        dense_retriever,
        splade_retriever: OptimizedSPLADEDBRetriever,
        query: str,
        doc_type: str,
        top_k: int = 10,
        splade_weight: float = 0.7,
        dense_weight: float = 0.3
    ) -> List[Dict]:
        """
        하이브리드 검색: SPLADE + Dense Vector
        
        Args:
            dense_retriever: Dense Vector Retriever
            splade_retriever: SPLADE Retriever
            query: 검색 쿼리
            doc_type: 문서 타입
            top_k: 반환할 상위 결과 수
            splade_weight: SPLADE 점수 가중치
            dense_weight: Dense 점수 가중치
        
        Returns:
            검색 결과 리스트
        """
        # SPLADE 검색
        if doc_type == 'law':
            splade_results = self.optimize_law_search(splade_retriever, query, top_k=top_k * 2)
        elif doc_type and doc_type.startswith('criteria'):
            splade_results = self.optimize_criteria_search(splade_retriever, query, top_k=top_k * 2)
        else:
            splade_results = []
        
        # Dense 검색
        try:
            dense_results = dense_retriever.search(query, top_k=top_k * 2, debug=False)
            dense_results_list = dense_results.get('results', [])
        except Exception as e:
            print(f"  ⚠️  Dense 검색 오류: {e}")
            dense_results_list = []
        
        # 결과 통합 및 점수 계산
        combined_results = {}
        
        # SPLADE 결과 추가
        for r in splade_results:
            chunk_id = r.get('chunk_id')
            if chunk_id:
                combined_results[chunk_id] = {
                    'chunk_id': chunk_id,
                    'doc_id': r.get('doc_id'),
                    'content': r.get('content'),
                    'splade_score': r.get('splade_score', 0.0),
                    'dense_score': 0.0,
                    'final_score': 0.0
                }
        
        # Dense 결과 추가/업데이트
        for r in dense_results_list:
            chunk_id = r.get('chunk_id')
            similarity = r.get('similarity', 0.0)
            
            if chunk_id in combined_results:
                combined_results[chunk_id]['dense_score'] = similarity
            else:
                combined_results[chunk_id] = {
                    'chunk_id': chunk_id,
                    'doc_id': r.get('doc_id'),
                    'content': r.get('content'),
                    'splade_score': 0.0,
                    'dense_score': similarity,
                    'final_score': 0.0
                }
        
        # 최종 점수 계산
        for chunk_id, result in combined_results.items():
            result['final_score'] = (
                result['splade_score'] * splade_weight +
                result['dense_score'] * dense_weight
            )
        
        # 정렬
        sorted_results = sorted(
            combined_results.values(),
            key=lambda x: x['final_score'],
            reverse=True
        )
        
        return sorted_results[:top_k]


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='SPLADE 도메인 최적화')
    parser.add_argument('--test', action='store_true', help='테스트 모드')
    parser.add_argument('--query', type=str, help='테스트 쿼리')
    parser.add_argument('--doc-type', type=str, choices=['law', 'criteria'], help='문서 타입')
    
    args = parser.parse_args()
    
    # DB 설정
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'database': os.getenv('DB_NAME', 'ddoksori'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres')
    }
    
    # Optimizer 초기화
    optimizer = SPLADEDomainOptimizer(db_config)
    
    # Retriever 초기화
    try:
        splade_retriever = OptimizedSPLADEDBRetriever(db_config)
        print("✅ SPLADE Retriever 초기화 완료")
    except Exception as e:
        print(f"❌ SPLADE Retriever 초기화 실패: {e}")
        sys.exit(1)
    
    # 테스트 모드
    if args.test and args.query:
        print(f"\n{'='*80}")
        print(f"테스트 쿼리: {args.query}")
        print(f"{'='*80}")
        
        if args.doc_type == 'law':
            results = optimizer.optimize_law_search(splade_retriever, args.query, top_k=5)
            print(f"\n법령 검색 결과: {len(results)}개")
            for i, r in enumerate(results[:3], 1):
                print(f"\n{i}. Score: {r.get('splade_score', 0.0):.4f}")
                print(f"   Law: {r.get('law_name', 'N/A')}")
                print(f"   Content: {r.get('content', '')[:100]}...")
        elif args.doc_type == 'criteria':
            results = optimizer.optimize_criteria_search(splade_retriever, args.query, top_k=5)
            print(f"\n기준 검색 결과: {len(results)}개")
            for i, r in enumerate(results[:3], 1):
                print(f"\n{i}. Score: {r.get('splade_score', 0.0):.4f}")
                print(f"   Item: {r.get('item', 'N/A')}")
                print(f"   Content: {r.get('content', '')[:100]}...")
        else:
            print("⚠️  --doc-type을 지정해주세요 (law 또는 criteria)")
    else:
        print("✅ SPLADE 도메인 최적화 모듈 로드 완료")
        print("\n사용법:")
        print("  python optimize_splade_for_domain.py --test --query '민법 제750조' --doc-type law")
        print("  python optimize_splade_for_domain.py --test --query '냉장고 환불' --doc-type criteria")
    
    # 연결 종료
    if splade_retriever.conn:
        splade_retriever.conn.close()


if __name__ == "__main__":
    main()
