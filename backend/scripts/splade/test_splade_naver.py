"""
Naver SPLADE 모델 적용 스니펫
HuggingFace: naver/splade-v3
HuggingFace 권장 방식: SparseEncoder 사용
"""

import torch
from typing import List, Dict, Optional
import numpy as np
import psycopg2
import os
from dotenv import load_dotenv
from pathlib import Path

# 환경 변수 로드
backend_dir = Path(__file__).parent.parent
env_file = backend_dir / '.env'
if env_file.exists():
    load_dotenv(env_file)
else:
    root_env = Path(__file__).parent.parent.parent / '.env'
    if root_env.exists():
        load_dotenv(root_env)
    else:
        load_dotenv()

# HuggingFace 토큰 확인
HF_TOKEN = os.getenv('HF_TOKEN') or os.getenv('HUGGINGFACE_TOKEN')


class NaverSPLADERetriever:
    """Naver SPLADE 모델 기반 Retriever (SparseEncoder 사용)"""
    
    def __init__(self, model_name: str = "naver/splade-v3", device: str = None):
        """
        Args:
            model_name: Naver SPLADE 모델 이름 (기본값: naver/splade-v3)
            device: 사용할 디바이스 ('cuda' 또는 'cpu', None이면 자동 선택)
                    'cuda'로 명시하면 GPU 사용, None이면 자동 감지
        """
        self.model_name = model_name
        self.model = None
        # device 명시적 지정 또는 자동 감지
        if device is None:
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        else:
            self.device = device
        self.use_sparse_encoder = True
        print(f"🔧 SPLADE Retriever 초기화: device={self.device}, CUDA available={torch.cuda.is_available()}")
    
    def load_model(self):
        """모델 로드 (SparseEncoder 우선, 실패 시 SentenceTransformer 시도)"""
        if self.model is None:
            print(f"Loading SPLADE model: {self.model_name}")
            print(f"Device: {self.device}")
            
            # safetensors 사용 강제 (torch 버전 문제 회피)
            os.environ['SAFETENSORS_FAST_GPU'] = '1'
            # transformers에서 safetensors 우선 사용
            os.environ['TRANSFORMERS_SAFE_LOADING'] = '1'
            
            # SparseEncoder 시도 (HuggingFace 권장)
            try:
                from sentence_transformers import SparseEncoder
                print("  시도: SparseEncoder (safetensors 우선)...")
                self.model = SparseEncoder(
                    self.model_name,
                    token=HF_TOKEN if HF_TOKEN else None,
                    trust_remote_code=True
                )
                self.use_sparse_encoder = True
                print("✅ SparseEncoder로 모델 로드 성공!")
                return
            except ImportError:
                print("  ⚠️  SparseEncoder를 사용할 수 없습니다 (sentence-transformers 버전 확인 필요)")
            except Exception as e:
                error_str = str(e)
                print(f"  ⚠️  SparseEncoder 로드 실패: {error_str}")
                
                # torch 버전 문제인 경우
                if "torch.load" in error_str or "CVE-2025-32434" in error_str or "torch>=2.6" in error_str:
                    print("  💡 torch 버전 문제 감지 (현재: 2.5.1, 필요: 2.6+)")
                    print("  💡 해결 방법:")
                    print("     1. torch 업그레이드: pip install torch>=2.6")
                    print("     2. 또는 모델이 safetensors 형식으로 제공되는지 확인")
                    print("  ⚠️  현재는 SPLADE 모델을 사용할 수 없습니다.")
                    raise RuntimeError("torch 버전이 2.6 미만입니다. torch>=2.6으로 업그레이드하거나 safetensors 형식 모델을 사용하세요.")
            
            # SentenceTransformer 대안 시도 (하지만 SPLADE는 sparse vector를 지원하지 않음)
            print("  ⚠️  SentenceTransformer는 SPLADE sparse vector를 지원하지 않습니다.")
            raise RuntimeError("SPLADE 모델을 로드할 수 없습니다. SparseEncoder가 필요합니다.")
    
    def encode_query(self, query: str):
        """
        쿼리를 Sparse Vector로 인코딩
        
        Args:
            query: 입력 쿼리
        
        Returns:
            Sparse vector (torch tensor 또는 numpy array, 30522차원)
        """
        self.load_model()
        
        if self.use_sparse_encoder:
            # SparseEncoder 사용
            query_emb = self.model.encode_query([query])
            # torch tensor인 경우 처리
            import torch
            if isinstance(query_emb, torch.Tensor):
                # sparse tensor인 경우 dense로 변환
                if query_emb.is_sparse:
                    query_emb = query_emb.to_dense()
                # numpy로 변환
                query_emb = query_emb.cpu().numpy()
            # 첫 번째 결과 반환 (배치가 1개이므로)
            if len(query_emb.shape) > 1:
                return query_emb[0]
            return query_emb
        else:
            # SentenceTransformer 사용 (일반 임베딩)
            # SPLADE는 sparse vector를 반환해야 하므로 이 경우는 지원하지 않음
            raise NotImplementedError("SentenceTransformer는 SPLADE sparse vector를 지원하지 않습니다. SparseEncoder를 사용하세요.")
    
    def encode_document(self, document: str):
        """
        문서를 Sparse Vector로 인코딩
        
        Args:
            document: 입력 문서
        
        Returns:
            Sparse vector (torch tensor 또는 numpy array, 30522차원)
        """
        self.load_model()
        
        if self.use_sparse_encoder:
            # SparseEncoder 사용
            doc_emb = self.model.encode_document([document])
            # torch tensor인 경우 처리
            import torch
            if isinstance(doc_emb, torch.Tensor):
                # sparse tensor인 경우 dense로 변환
                if doc_emb.is_sparse:
                    doc_emb = doc_emb.to_dense()
                # numpy로 변환
                doc_emb = doc_emb.cpu().numpy()
            # 첫 번째 결과 반환
            if len(doc_emb.shape) > 1:
                return doc_emb[0]
            return doc_emb
        else:
            raise NotImplementedError("SentenceTransformer는 SPLADE sparse vector를 지원하지 않습니다.")
    
    def compute_similarity(
        self,
        query_vec,
        doc_vec
    ) -> float:
        """
        쿼리와 문서 간 유사도 계산 (dot product)
        
        Args:
            query_vec: 쿼리 sparse vector (torch tensor 또는 numpy array)
            doc_vec: 문서 sparse vector (torch tensor 또는 numpy array)
        
        Returns:
            유사도 점수
        """
        # torch tensor인 경우 numpy로 변환
        import torch
        if isinstance(query_vec, torch.Tensor):
            if query_vec.is_sparse:
                query_vec = query_vec.to_dense()
            query_vec = query_vec.cpu().numpy()
        if isinstance(doc_vec, torch.Tensor):
            if doc_vec.is_sparse:
                doc_vec = doc_vec.to_dense()
            doc_vec = doc_vec.cpu().numpy()
        
        # Sparse vector의 dot product
        similarity = np.dot(query_vec, doc_vec)
        return float(similarity)
    
    def search(
        self,
        query: str,
        documents: List[str],
        top_k: int = 10
    ) -> List[tuple]:
        """
        검색 수행
        
        Args:
            query: 검색 쿼리
            documents: 검색 대상 문서 리스트
            top_k: 반환할 상위 결과 수
        
        Returns:
            (문서, 점수) 튜플 리스트
        """
        query_vec = self.encode_query(query)
        
        # 문서별 점수 계산
        scores = []
        for doc in documents:
            doc_vec = self.encode_document(doc)
            score = self.compute_similarity(query_vec, doc_vec)
            scores.append((doc, score))
        
        # 점수 기준 정렬
        scores.sort(key=lambda x: x[1], reverse=True)
        
        return scores[:top_k]


class NaverSPLADEDBRetriever:
    """Naver SPLADE 모델을 사용한 DB 검색"""
    
    def __init__(
        self,
        db_config: Dict,
        model_name: str = "naver/splade-v3",
        device: str = None
    ):
        """
        Args:
            db_config: 데이터베이스 연결 설정
            model_name: SPLADE 모델 이름
            device: 사용할 디바이스 ('cuda' 또는 'cpu', None이면 자동 선택)
        """
        self.db_config = db_config
        # device가 None이면 자동 감지, 'cuda'로 명시하면 GPU 강제 사용
        if device is None:
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.splade_retriever = NaverSPLADERetriever(model_name, device=device)
        self.conn = None
        print(f"🔧 SPLADE DB Retriever 초기화: device={device}")
    
    def connect_db(self):
        """DB 연결"""
        if self.conn is None or self.conn.closed:
            self.conn = psycopg2.connect(**self.db_config)
    
    def search_law_splade(
        self,
        query: str,
        top_k: int = 10
    ) -> List[Dict]:
        """법령 SPLADE 검색"""
        self.connect_db()
        
        try:
            # 쿼리 인코딩
            query_vec = self.splade_retriever.encode_query(query)
            
            if query_vec is None or query_vec.size == 0:
                return []
        except Exception as e:
            print(f"  ⚠️  쿼리 인코딩 실패: {e}")
            return []
        
        # 모든 법령 chunk 가져오기
        cur = self.conn.cursor()
        cur.execute("""
            SELECT 
                c.chunk_id,
                c.doc_id,
                c.content,
                d.metadata->>'law_name' as law_name
            FROM chunks c
            JOIN documents d ON c.doc_id = d.doc_id
            WHERE d.doc_type = 'law'
            LIMIT 1000
        """)
        
        chunks = cur.fetchall()
        
        # 각 chunk에 대해 유사도 계산
        results = []
        for chunk_id, doc_id, content, law_name in chunks:
            try:
                doc_vec = self.splade_retriever.encode_document(content)
                score = self.splade_retriever.compute_similarity(query_vec, doc_vec)
                
                if score > 0:
                    results.append({
                        'chunk_id': chunk_id,
                        'doc_id': doc_id,
                        'content': content,
                        'law_name': law_name,
                        'splade_score': float(score)
                    })
            except Exception as e:
                # 개별 문서 인코딩 실패는 무시하고 계속
                continue
        
        # 점수 기준 정렬
        results.sort(key=lambda x: x['splade_score'], reverse=True)
        
        return results[:top_k]
    
    def search_criteria_splade(
        self,
        query: str,
        top_k: int = 10
    ) -> List[Dict]:
        """기준 SPLADE 검색"""
        self.connect_db()
        
        try:
            # 쿼리 인코딩
            query_vec = self.splade_retriever.encode_query(query)
            
            if query_vec is None or query_vec.size == 0:
                return []
        except Exception as e:
            print(f"  ⚠️  쿼리 인코딩 실패: {e}")
            return []
        
        # 모든 기준 chunk 가져오기
        cur = self.conn.cursor()
        cur.execute("""
            SELECT 
                c.chunk_id,
                c.doc_id,
                c.content,
                d.metadata->>'item' as item
            FROM chunks c
            JOIN documents d ON c.doc_id = d.doc_id
            WHERE d.doc_type LIKE 'criteria%%'
            LIMIT 1000
        """)
        
        chunks = cur.fetchall()
        
        # 각 chunk에 대해 유사도 계산
        results = []
        for chunk_id, doc_id, content, item in chunks:
            try:
                doc_vec = self.splade_retriever.encode_document(content)
                score = self.splade_retriever.compute_similarity(query_vec, doc_vec)
                
                if score > 0:
                    results.append({
                        'chunk_id': chunk_id,
                        'doc_id': doc_id,
                        'content': content,
                        'item': item,
                        'splade_score': float(score)
                    })
            except Exception as e:
                # 개별 문서 인코딩 실패는 무시하고 계속
                continue
        
        # 점수 기준 정렬
        results.sort(key=lambda x: x['splade_score'], reverse=True)
        
        return results[:top_k]


# 사용 예시
if __name__ == "__main__":
    # 간단한 테스트
    print("=== Naver SPLADE 모델 테스트 ===")
    retriever = NaverSPLADERetriever()
    
    query = "민법 제750조 불법행위"
    print(f"\nQuery: {query}")
    print("Encoding query...")
    
    try:
        query_vec = retriever.encode_query(query)
        print(f"✅ Encoded sparse vector (shape: {query_vec.shape})")
        
        # numpy array로 변환 (필요한 경우)
        import torch
        if isinstance(query_vec, torch.Tensor):
            if query_vec.is_sparse:
                query_vec = query_vec.to_dense()
            query_vec = query_vec.cpu().numpy()
        
        # 0이 아닌 값의 개수
        non_zero_count = np.count_nonzero(query_vec)
        print(f"  Non-zero values: {non_zero_count}")
        
        # Top-10 가중치
        top_indices = np.argsort(query_vec)[-10:][::-1]
        print("\nTop 10 token indices (가중치):")
        for idx in top_indices:
            if query_vec[idx] > 0:
                print(f"  Token {idx}: {query_vec[idx]:.4f}")
        
        # 문서 인코딩 테스트
        test_doc = "민법 제750조 불법행위로 인한 손해배상"
        print(f"\nDocument: {test_doc}")
        doc_vec = retriever.encode_document(test_doc)
        similarity = retriever.compute_similarity(query_vec, doc_vec)
        print(f"✅ Similarity: {similarity:.4f}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        print("\nNote: 모델을 사용하려면 다음이 필요합니다:")
        print("  1. HuggingFace 계정 로그인 및 접근 권한 승인")
        print("  2. sentence-transformers 설치: pip install sentence-transformers")
        print("  3. HF_TOKEN 환경 변수 설정")
