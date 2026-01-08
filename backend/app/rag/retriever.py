"""
RAG Retriever Module
Vector DB에서 유사한 청크를 검색하는 모듈
"""

import os
import psycopg2
from typing import List, Dict, Optional
from sentence_transformers import SentenceTransformer
import torch


class VectorRetriever:
    """Vector DB에서 유사 청크를 검색하는 클래스"""
    
    def __init__(self, db_config: Dict, model_name: str = None):
        """
        Args:
            db_config: 데이터베이스 연결 설정
            model_name: 임베딩 모델 이름 (기본값: 환경변수에서 로드)
        """
        self.db_config = db_config
        self.model_name = model_name or os.getenv('EMBEDDING_MODEL', 'nlpai-lab/KURE-v1')
        self.model = None
        self.conn = None
        
    def load_model(self):
        """임베딩 모델 로드"""
        if self.model is None:
            print(f"Loading embedding model: {self.model_name}")
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            self.model = SentenceTransformer(self.model_name, device=device)
            print(f"Model loaded on {device}")
    
    def connect_db(self):
        """데이터베이스 연결"""
        if self.conn is None or self.conn.closed:
            self.conn = psycopg2.connect(**self.db_config)
    
    def close(self):
        """리소스 정리"""
        if self.conn and not self.conn.closed:
            self.conn.close()
    
    def embed_query(self, query: str) -> List[float]:
        """
        쿼리 텍스트를 임베딩 벡터로 변환
        
        Args:
            query: 사용자 질문
            
        Returns:
            임베딩 벡터 (1024차원)
        """
        self.load_model()
        embedding = self.model.encode(query, convert_to_numpy=True)
        return embedding.tolist()
    
    def search(
        self, 
        query: str, 
        top_k: int = 5,
        chunk_types: Optional[List[str]] = None,
        agencies: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        유사한 청크를 검색
        
        Args:
            query: 사용자 질문
            top_k: 반환할 최대 결과 수
            chunk_types: 필터링할 청크 타입 리스트 (예: ['decision', 'reasoning'])
            agencies: 필터링할 기관 리스트 (예: ['kca', 'ecmc'])
            
        Returns:
            검색된 청크 리스트 (유사도 순)
        """
        self.connect_db()
        
        # 쿼리 임베딩
        query_embedding = self.embed_query(query)
        
        # SQL 쿼리 구성
        sql = """
            SELECT 
                c.chunk_id,
                c.doc_id,
                c.chunk_type,
                c.content,
                c.content_length,
                d.title,
                d.metadata->>'decision_date' AS decision_date,
                d.source_org AS agency,
                d.doc_type AS source,
                1 - (c.embedding <=> %s::vector) AS similarity
            FROM chunks c
            JOIN documents d ON c.doc_id = d.doc_id
            WHERE c.drop = FALSE
        """
        
        params = [query_embedding]
        
        # 청크 타입 필터링
        if chunk_types:
            placeholders = ','.join(['%s'] * len(chunk_types))
            sql += f" AND c.chunk_type IN ({placeholders})"
            params.extend(chunk_types)
        
        # 기관 필터링
        if agencies:
            placeholders = ','.join(['%s'] * len(agencies))
            sql += f" AND d.source_org IN ({placeholders})"
            params.extend(agencies)
        
        sql += """
            ORDER BY c.embedding <=> %s::vector
            LIMIT %s
        """
        params.append(query_embedding)
        params.append(top_k)
        
        # 쿼리 실행
        with self.conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
        
        # 결과 포맷팅
        results = []
        for row in rows:
            results.append({
                'chunk_uid': row[0],  # chunk_id (호환성 유지)
                'case_uid': row[1],   # doc_id (호환성 유지)
                'chunk_type': row[2],
                'text': row[3],       # content
                'text_len': row[4],   # content_length
                'case_no': row[5],    # title (사례번호 대신)
                'decision_date': row[6],
                'agency': row[7],     # source_org
                'source': row[8],     # doc_type
                'similarity': float(row[9])
            })
        
        return results
    
    def get_case_chunks(self, case_uid: str) -> List[Dict]:
        """
        특정 사례의 모든 청크를 가져오기
        
        Args:
            case_uid: 사례 고유 ID (doc_id)
            
        Returns:
            해당 사례의 모든 청크 리스트
        """
        self.connect_db()
        
        sql = """
            SELECT 
                c.chunk_id,
                c.doc_id,
                c.chunk_type,
                c.content,
                c.chunk_index,
                d.title,
                d.metadata->>'decision_date' AS decision_date,
                d.source_org
            FROM chunks c
            JOIN documents d ON c.doc_id = d.doc_id
            WHERE c.doc_id = %s AND c.drop = FALSE
            ORDER BY c.chunk_index
        """
        
        with self.conn.cursor() as cur:
            cur.execute(sql, (case_uid,))
            rows = cur.fetchall()
        
        results = []
        for row in rows:
            results.append({
                'chunk_uid': row[0],
                'case_uid': row[1],
                'chunk_type': row[2],
                'text': row[3],
                'seq': row[4],
                'case_no': row[5],
                'decision_date': row[6],
                'agency': row[7]
            })
        
        return results
