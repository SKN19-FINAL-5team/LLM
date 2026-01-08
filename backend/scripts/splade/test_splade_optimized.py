"""
최적화된 SPLADE Retriever
RDB에 사전 인코딩된 sparse vector를 사용하여 검색 성능 최적화
"""

import json
import numpy as np
import psycopg2
from typing import List, Dict, Optional
from pathlib import Path
import os
from dotenv import load_dotenv

# 환경 변수 로드
backend_dir = Path(__file__).parent.parent
env_file = backend_dir / '.env'
if env_file.exists():
    load_dotenv(env_file)
else:
    root_env = backend_dir.parent / '.env'
    if root_env.exists():
        load_dotenv(root_env)
    else:
        load_dotenv()

# SPLADE 모듈 import (쿼리 인코딩용)
try:
    from scripts.splade.test_splade_naver import NaverSPLADERetriever
    from scripts.splade.test_splade_remote import RemoteSPLADERetriever
    SPLADE_AVAILABLE = True
except ImportError:
    SPLADE_AVAILABLE = False
    NaverSPLADERetriever = None
    RemoteSPLADERetriever = None


class OptimizedSPLADEDBRetriever:
    """최적화된 SPLADE DB Retriever (사전 인코딩된 sparse vector 사용)"""
    
    def __init__(
        self,
        db_config: Dict,
        use_remote: bool = False,
        api_url: str = None,
        device: str = None
    ):
        """
        Args:
            db_config: 데이터베이스 연결 설정
            use_remote: 원격 API 서버 사용 여부
            api_url: 원격 API URL
            device: 로컬 모드 디바이스
        """
        self.db_config = db_config
        self.conn = None
        self.query_encoder = None
        
        # 쿼리 인코딩용 Retriever 초기화
        if use_remote:
            if api_url is None:
                api_url = os.getenv('SPLADE_API_URL', 'http://localhost:8001')
            try:
                self.query_encoder = RemoteSPLADERetriever(api_url=api_url)
                print(f"✅ 원격 SPLADE API 사용 (쿼리 인코딩): {api_url}")
            except Exception as e:
                print(f"⚠️  원격 API 연결 실패: {e}")
                use_remote = False
        
        if not use_remote and SPLADE_AVAILABLE:
            try:
                import torch
                if device is None:
                    device = 'cuda' if torch.cuda.is_available() else 'cpu'
                self.query_encoder = NaverSPLADERetriever(device=device)
                self.query_encoder.load_model()
                print(f"✅ 로컬 SPLADE 모델 사용 (쿼리 인코딩): device={device}")
            except Exception as e:
                print(f"⚠️  로컬 모델 로드 실패: {e}")
                raise RuntimeError("SPLADE 쿼리 인코더를 초기화할 수 없습니다.")
    
    def connect_db(self):
        """DB 연결"""
        if self.conn is None or self.conn.closed:
            self.conn = psycopg2.connect(**self.db_config)
    
    def jsonb_to_sparse_vector(self, jsonb_data: Dict[str, float]) -> np.ndarray:
        """
        JSONB 형식의 sparse vector를 numpy array로 변환
        
        Args:
            jsonb_data: {token_id: weight} 형태의 딕셔너리
        
        Returns:
            Sparse vector (numpy array, 30522차원)
        """
        # SPLADE-v3는 30522 차원
        vocab_size = 30522
        sparse_vec = np.zeros(vocab_size, dtype=np.float32)
        
        for token_id_str, weight in jsonb_data.items():
            try:
                token_id = int(token_id_str)
                if 0 <= token_id < vocab_size:
                    sparse_vec[token_id] = float(weight)
            except (ValueError, TypeError):
                continue
        
        return sparse_vec
    
    def compute_similarity_batch(
        self,
        query_vec: np.ndarray,
        doc_vectors: List[Dict[str, float]]
    ) -> List[float]:
        """
        배치로 유사도 계산
        
        Args:
            query_vec: 쿼리 sparse vector
            doc_vectors: 문서 sparse vector 리스트 (JSONB 형식)
        
        Returns:
            유사도 점수 리스트
        """
        similarities = []
        
        for doc_vec_jsonb in doc_vectors:
            if doc_vec_jsonb is None:
                similarities.append(0.0)
                continue
            
            # JSONB를 numpy array로 변환
            doc_vec = self.jsonb_to_sparse_vector(doc_vec_jsonb)
            
            # Dot product 계산
            similarity = np.dot(query_vec, doc_vec)
            similarities.append(float(similarity))
        
        return similarities
    
    def search_law_splade_optimized(
        self,
        query: str,
        top_k: int = 10,
        min_score: float = 0.0
    ) -> List[Dict]:
        """
        법령 SPLADE 검색 (최적화 버전)
        
        Args:
            query: 검색 쿼리
            top_k: 반환할 상위 결과 수
            min_score: 최소 유사도 점수
        
        Returns:
            검색 결과 리스트
        """
        self.connect_db()
        
        # 쿼리 인코딩
        try:
            query_vec = self.query_encoder.encode_query(query)
            if query_vec is None or query_vec.size == 0:
                return []
        except Exception as e:
            print(f"  ⚠️  쿼리 인코딩 실패: {e}")
            return []
        
        # numpy array로 변환
        if isinstance(query_vec, dict):
            # 이미 JSONB 형식인 경우
            query_vec = self.jsonb_to_sparse_vector(query_vec)
        elif not isinstance(query_vec, np.ndarray):
            import torch
            if isinstance(query_vec, torch.Tensor):
                if query_vec.is_sparse:
                    query_vec = query_vec.to_dense()
                query_vec = query_vec.cpu().numpy()
        
        # DB에서 사전 인코딩된 sparse vector 가져오기
        cur = self.conn.cursor()
        cur.execute("""
            SELECT 
                c.chunk_id,
                c.doc_id,
                c.content,
                c.splade_sparse_vector,
                d.metadata->>'law_name' as law_name
            FROM chunks c
            JOIN documents d ON c.doc_id = d.doc_id
            WHERE 
                d.doc_type = 'law'
                AND c.drop = FALSE
                AND c.splade_encoded = TRUE
                AND c.splade_sparse_vector IS NOT NULL
        """)
        
        chunks = cur.fetchall()
        cur.close()
        
        if not chunks:
            return []
        
        # 배치 유사도 계산
        doc_vectors = [row[3] for row in chunks]  # splade_sparse_vector
        similarities = self.compute_similarity_batch(query_vec, doc_vectors)
        
        # 결과 구성
        results = []
        for (chunk_id, doc_id, content, _, law_name), score in zip(chunks, similarities):
            if score >= min_score:
                results.append({
                    'chunk_id': chunk_id,
                    'doc_id': doc_id,
                    'content': content,
                    'law_name': law_name if law_name else '',
                    'splade_score': score
                })
        
        # 점수 기준 정렬
        results.sort(key=lambda x: x['splade_score'], reverse=True)
        
        return results[:top_k]
    
    def search_criteria_splade_optimized(
        self,
        query: str,
        top_k: int = 10,
        min_score: float = 0.0
    ) -> List[Dict]:
        """
        기준 SPLADE 검색 (최적화 버전)
        
        Args:
            query: 검색 쿼리
            top_k: 반환할 상위 결과 수
            min_score: 최소 유사도 점수
        
        Returns:
            검색 결과 리스트
        """
        self.connect_db()
        
        # 쿼리 인코딩
        try:
            query_vec = self.query_encoder.encode_query(query)
            if query_vec is None or query_vec.size == 0:
                return []
        except Exception as e:
            print(f"  ⚠️  쿼리 인코딩 실패: {e}")
            return []
        
        # numpy array로 변환
        if isinstance(query_vec, dict):
            query_vec = self.jsonb_to_sparse_vector(query_vec)
        elif not isinstance(query_vec, np.ndarray):
            import torch
            if isinstance(query_vec, torch.Tensor):
                if query_vec.is_sparse:
                    query_vec = query_vec.to_dense()
                query_vec = query_vec.cpu().numpy()
        
        # DB에서 사전 인코딩된 sparse vector 가져오기
        cur = self.conn.cursor()
        cur.execute("""
            SELECT 
                c.chunk_id,
                c.doc_id,
                c.content,
                c.splade_sparse_vector,
                d.metadata->>'item' as item
            FROM chunks c
            JOIN documents d ON c.doc_id = d.doc_id
            WHERE 
                d.doc_type LIKE 'criteria%%'
                AND c.drop = FALSE
                AND c.splade_encoded = TRUE
                AND c.splade_sparse_vector IS NOT NULL
        """)
        
        chunks = cur.fetchall()
        cur.close()
        
        if not chunks:
            return []
        
        # 배치 유사도 계산
        doc_vectors = [row[3] for row in chunks]
        similarities = self.compute_similarity_batch(query_vec, doc_vectors)
        
        # 결과 구성
        results = []
        for (chunk_id, doc_id, content, _, item), score in zip(chunks, similarities):
            if score >= min_score:
                results.append({
                    'chunk_id': chunk_id,
                    'doc_id': doc_id,
                    'content': content,
                    'item': item if item else '',
                    'splade_score': score
                })
        
        # 점수 기준 정렬
        results.sort(key=lambda x: x['splade_score'], reverse=True)
        
        return results[:top_k]
    
    def search_hybrid(
        self,
        query: str,
        doc_type: str = None,
        top_k: int = 10,
        splade_weight: float = 0.7,
        dense_weight: float = 0.3
    ) -> List[Dict]:
        """
        하이브리드 검색: SPLADE + Dense Vector
        
        Args:
            query: 검색 쿼리
            doc_type: 문서 타입 필터
            top_k: 반환할 상위 결과 수
            splade_weight: SPLADE 점수 가중치
            dense_weight: Dense 점수 가중치
        
        Returns:
            검색 결과 리스트
        """
        # TODO: Dense Retriever와 통합
        # 현재는 SPLADE만 반환
        if doc_type == 'law' or doc_type is None:
            return self.search_law_splade_optimized(query, top_k=top_k)
        elif doc_type and doc_type.startswith('criteria'):
            return self.search_criteria_splade_optimized(query, top_k=top_k)
        else:
            return []


# 사용 예시
if __name__ == "__main__":
    import sys
    
    # DB 설정
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'database': os.getenv('DB_NAME', 'ddoksori'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres')
    }
    
    # Retriever 초기화
    try:
        retriever = OptimizedSPLADEDBRetriever(db_config)
    except Exception as e:
        print(f"❌ Retriever 초기화 실패: {e}")
        sys.exit(1)
    
    # 테스트 쿼리
    test_queries = [
        "민법 제750조 불법행위",
        "냉장고 품질보증 기준"
    ]
    
    for query in test_queries:
        print(f"\n{'='*80}")
        print(f"Query: {query}")
        print(f"{'='*80}")
        
        # 법령 검색
        if "법" in query or "조" in query:
            results = retriever.search_law_splade_optimized(query, top_k=5)
            print(f"\n법령 검색 결과: {len(results)}개")
            for i, r in enumerate(results[:3], 1):
                print(f"\n{i}. Score: {r['splade_score']:.4f}")
                print(f"   Law: {r.get('law_name', 'N/A')}")
                print(f"   Content: {r['content'][:100]}...")
        
        # 기준 검색
        else:
            results = retriever.search_criteria_splade_optimized(query, top_k=5)
            print(f"\n기준 검색 결과: {len(results)}개")
            for i, r in enumerate(results[:3], 1):
                print(f"\n{i}. Score: {r['splade_score']:.4f}")
                print(f"   Item: {r.get('item', 'N/A')}")
                print(f"   Content: {r['content'][:100]}...")
    
    # 연결 종료
    if retriever.conn:
        retriever.conn.close()
