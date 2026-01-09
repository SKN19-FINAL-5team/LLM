"""
로컬에서 RunPod의 SPLADE API 서버를 사용하는 클라이언트
SSH 터널을 통해 접근 (localhost:8002 -> RunPod:8000)
"""

import requests
import numpy as np
from typing import List, Dict, Optional
import psycopg2
from pathlib import Path
import os
from dotenv import load_dotenv

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

# API URL (SSH 터널을 통해 localhost:8002로 접근)
SPLADE_API_URL = os.getenv('SPLADE_API_URL', 'http://localhost:8002')


class RemoteSPLADERetriever:
    """RunPod의 SPLADE API를 사용하는 Retriever"""
    
    def __init__(self, api_url: str = None):
        """
        Args:
            api_url: SPLADE API 서버 URL (기본값: http://localhost:8002)
        """
        self.api_url = api_url or SPLADE_API_URL
        self.base_url = self.api_url.rstrip('/')
    
    def _check_connection(self, silent: bool = False):
        """API 서버 연결 확인"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                return True
        except Exception as e:
            if not silent:
                print(f"⚠️  API 서버 연결 실패: {e}")
                print(f"   URL: {self.base_url}")
                print(f"   SSH 터널이 연결되어 있는지 확인하세요.")
            return False
        return False
    
    def encode_query(self, query: str) -> np.ndarray:
        """
        쿼리를 Sparse Vector로 인코딩
        
        Args:
            query: 입력 쿼리
        
        Returns:
            Sparse vector (numpy array, 30522차원)
        """
        # 연결 확인 (에러 메시지는 한 번만 출력)
        if not self._check_connection():
            raise ConnectionError("SPLADE API 서버에 연결할 수 없습니다.")
        
        try:
            response = requests.post(
                f"{self.base_url}/encode_query",
                json={"texts": [query]},
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            return np.array(result['embeddings'][0])
        except Exception as e:
            raise RuntimeError(f"Query encoding failed: {e}")
    
    def encode_document(self, document: str) -> np.ndarray:
        """
        문서를 Sparse Vector로 인코딩
        
        Args:
            document: 입력 문서
        
        Returns:
            Sparse vector (numpy array, 30522차원)
        """
        # 연결 확인 (조용한 모드)
        if not self._check_connection(silent=True):
            raise ConnectionError("SPLADE API 서버에 연결할 수 없습니다.")
        
        try:
            response = requests.post(
                f"{self.base_url}/encode_document",
                json={"texts": [document]},
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            return np.array(result['embeddings'][0])
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"API 서버 연결 실패: {e}")
        except Exception as e:
            raise RuntimeError(f"Document encoding failed: {e}")
    
    def encode_documents_batch(self, documents: List[str]) -> List[np.ndarray]:
        """
        여러 문서를 배치로 인코딩
        
        Args:
            documents: 입력 문서 리스트
        
        Returns:
            Sparse vector 리스트
        """
        # 연결 확인 (조용한 모드)
        if not self._check_connection(silent=True):
            raise ConnectionError("SPLADE API 서버에 연결할 수 없습니다.")
        
        try:
            response = requests.post(
                f"{self.base_url}/encode_document",
                json={"texts": documents},
                timeout=60
            )
            response.raise_for_status()
            result = response.json()
            return [np.array(emb) for emb in result['embeddings']]
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"API 서버 연결 실패: {e}")
        except Exception as e:
            raise RuntimeError(f"Batch document encoding failed: {e}")
    
    def compute_similarity(
        self,
        query_vec: np.ndarray,
        doc_vec: np.ndarray
    ) -> float:
        """
        쿼리와 문서 간 유사도 계산 (dot product)
        
        Args:
            query_vec: 쿼리 sparse vector
            doc_vec: 문서 sparse vector
        
        Returns:
            유사도 점수
        """
        try:
            response = requests.post(
                f"{self.base_url}/similarity",
                json={
                    "query_embedding": query_vec.tolist(),
                    "document_embeddings": [doc_vec.tolist()]
                },
                timeout=10
            )
            response.raise_for_status()
            result = response.json()
            return result['similarities'][0]
        except Exception as e:
            raise RuntimeError(f"Similarity computation failed: {e}")


class RemoteSPLADEDBRetriever:
    """RunPod SPLADE API를 사용한 DB 검색"""
    
    def __init__(
        self,
        db_config: Dict,
        api_url: str = None
    ):
        """
        Args:
            db_config: 데이터베이스 연결 설정
            api_url: SPLADE API 서버 URL
        """
        self.db_config = db_config
        self.splade_retriever = RemoteSPLADERetriever(api_url)
        self.conn = None
        self.api_available = False
        
        # 초기화 시 실제 연결 테스트
        try:
            if self.splade_retriever._check_connection():
                self.api_available = True
            else:
                self.api_available = False
                raise ConnectionError("API 서버에 연결할 수 없습니다.")
        except Exception as e:
            self.api_available = False
            raise ConnectionError(f"API 서버 연결 실패: {e}")
    
    def connect_db(self):
        """DB 연결"""
        if self.conn is None or self.conn.closed:
            self.conn = psycopg2.connect(**self.db_config)
    
    def search_law_splade(
        self,
        query: str,
        top_k: int = 10
    ) -> List[Dict]:
        """법령 SPLADE 검색 (배치 인코딩 사용)"""
        # API 서버 사용 불가 시 빈 결과 반환
        if not self.api_available:
            return []
        
        self.connect_db()
        
        try:
            # 쿼리 인코딩 (조용한 모드로 연결 확인)
            query_vec = self.splade_retriever.encode_query(query)
            
            if query_vec is None or query_vec.size == 0:
                return []
        except ConnectionError:
            # 연결 실패 시 조용히 빈 결과 반환
            self.api_available = False
            return []
        except Exception as e:
            # 다른 에러는 한 번만 출력
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
        
        # 배치 인코딩 (32개씩)
        batch_size = 32
        results = []
        
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i+batch_size]
            contents = [c[2] for c in batch]  # content만 추출
            
            try:
                # 배치 인코딩
                doc_vecs = self.splade_retriever.encode_documents_batch(contents)
                
                # 각 문서에 대해 유사도 계산
                for (chunk_id, doc_id, content, law_name), doc_vec in zip(batch, doc_vecs):
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
                print(f"  ⚠️  배치 인코딩 실패 (batch {i//batch_size + 1}): {e}")
                continue
        
        # 점수 기준 정렬
        results.sort(key=lambda x: x['splade_score'], reverse=True)
        
        return results[:top_k]
    
    def search_criteria_splade(
        self,
        query: str,
        top_k: int = 10
    ) -> List[Dict]:
        """기준 SPLADE 검색 (배치 인코딩 사용)"""
        # API 서버 사용 불가 시 빈 결과 반환
        if not self.api_available:
            return []
        
        self.connect_db()
        
        try:
            # 쿼리 인코딩 (조용한 모드로 연결 확인)
            query_vec = self.splade_retriever.encode_query(query)
            
            if query_vec is None or query_vec.size == 0:
                return []
        except ConnectionError:
            # 연결 실패 시 조용히 빈 결과 반환
            self.api_available = False
            return []
        except Exception as e:
            # 다른 에러는 한 번만 출력
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
        
        # 배치 인코딩 (32개씩)
        batch_size = 32
        results = []
        
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i+batch_size]
            contents = [c[2] for c in batch]  # content만 추출
            
            try:
                # 배치 인코딩
                doc_vecs = self.splade_retriever.encode_documents_batch(contents)
                
                # 각 문서에 대해 유사도 계산
                for (chunk_id, doc_id, content, item), doc_vec in zip(batch, doc_vecs):
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
                print(f"  ⚠️  배치 인코딩 실패 (batch {i//batch_size + 1}): {e}")
                continue
        
        # 점수 기준 정렬
        results.sort(key=lambda x: x['splade_score'], reverse=True)
        
        return results[:top_k]


# 사용 예시
if __name__ == "__main__":
    # API 서버 연결 확인
    retriever = RemoteSPLADERetriever()
    
    if retriever._check_connection():
        print("✅ SPLADE API 서버 연결 성공!")
        
        # 테스트
        query = "민법 제750조 불법행위"
        print(f"\nQuery: {query}")
        query_vec = retriever.encode_query(query)
        print(f"✅ Encoded (shape: {query_vec.shape}, non-zero: {np.count_nonzero(query_vec)})")
    else:
        print("❌ SPLADE API 서버 연결 실패")
        print("   SSH 터널을 확인하세요: ssh -L 8002:localhost:8000 [user]@[host] -p [port]")
