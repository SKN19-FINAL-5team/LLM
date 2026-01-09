"""
BM25 기반 Sparse Retrieval 테스트 스니펫
법령 및 분쟁조정기준 데이터에 대한 키워드 기반 검색
"""

import psycopg2
from typing import List, Dict
import re
import os
from dotenv import load_dotenv


class BM25SparseRetriever:
    """BM25 기반 Sparse Retrieval (SPLADE 시뮬레이션)"""
    
    def __init__(self, db_config: Dict):
        self.db_config = db_config
        self.conn = None
    
    def connect_db(self):
        if self.conn is None or self.conn.closed:
            self.conn = psycopg2.connect(**self.db_config)
    
    def extract_keywords(self, query: str) -> List[str]:
        """쿼리에서 핵심 키워드 추출"""
        keywords = []
        
        # 법령명
        law_names = ['민법', '상법', '소비자기본법', '전자상거래법', '약관규제법']
        keywords.extend([law for law in law_names if law in query])
        
        # 조문 번호
        articles = re.findall(r'제\s*\d+\s*조', query)
        keywords.extend(articles)
        
        # 항 번호
        paragraphs = re.findall(r'제\s*\d+\s*항', query)
        keywords.extend(paragraphs)
        
        # 품목명 (Phase 2에서 확장된 사전 활용)
        products = [
            '냉장고', '세탁기', '에어컨', 'TV', '텔레비전', '스마트폰', '휴대폰', 
            '노트북', '컴퓨터', '모니터', '프린터', '청소기', '전자레인지', 
            '밥솥', '정수기', '공기청정기', '가습기', '선풍기', '보일러', 
            '비데', '안마의자', '식기세척기', '의류건조기', '다리미', '믹서기'
        ]
        keywords.extend([p for p in products if p in query])
        
        # 일반 키워드 (2글자 이상 한글)
        korean_words = re.findall(r'[가-힣]{2,}', query)
        keywords.extend(korean_words)
        
        # 중복 제거 및 빈 문자열 제거
        keywords = [k.strip() for k in keywords if k.strip()]
        return list(set(keywords))
    
    def search_law_bm25(
        self,
        query: str,
        top_k: int = 10
    ) -> List[Dict]:
        """법령 BM25 검색"""
        self.connect_db()
        keywords = self.extract_keywords(query)
        
        if not keywords:
            return []
        
        # PostgreSQL Full-Text Search with BM25-like ranking
        # 한국어 텍스트 검색을 위해 to_tsvector와 plainto_tsquery 사용
        sql = """
            SELECT 
                c.chunk_id,
                c.doc_id,
                c.content,
                d.metadata->>'law_name' as law_name,
                ts_rank_cd(
                    to_tsvector('simple', c.content),
                    plainto_tsquery('simple', %s),
                    32  -- BM25-like normalization
                ) AS bm25_score
            FROM chunks c
            JOIN documents d ON c.doc_id = d.doc_id
            WHERE 
                d.doc_type = 'law'
                AND to_tsvector('simple', c.content) @@ plainto_tsquery('simple', %s)
            ORDER BY bm25_score DESC
            LIMIT %s
        """
        
        cur = self.conn.cursor()
        keyword_query = ' '.join(keywords)
        cur.execute(sql, (keyword_query, keyword_query, top_k))
        
        results = []
        for row in cur.fetchall():
            results.append({
                'chunk_id': row[0],
                'doc_id': row[1],
                'content': row[2],
                'law_name': row[3],
                'bm25_score': float(row[4]) if row[4] else 0.0
            })
        
        return results
    
    def search_criteria_bm25(
        self,
        query: str,
        top_k: int = 10
    ) -> List[Dict]:
        """기준 BM25 검색"""
        self.connect_db()
        keywords = self.extract_keywords(query)
        
        if not keywords:
            return []
        
        sql = """
            SELECT 
                c.chunk_id,
                c.doc_id,
                c.content,
                d.metadata->>'item' as item,
                ts_rank_cd(
                    to_tsvector('simple', c.content),
                    plainto_tsquery('simple', %s),
                    32
                ) AS bm25_score
            FROM chunks c
            JOIN documents d ON c.doc_id = d.doc_id
            WHERE 
                d.doc_type LIKE 'criteria%%'
                AND to_tsvector('simple', c.content) @@ plainto_tsquery('simple', %s)
            ORDER BY bm25_score DESC
            LIMIT %s
        """
        
        cur = self.conn.cursor()
        keyword_query = ' '.join(keywords)
        cur.execute(sql, (keyword_query, keyword_query, top_k))
        
        results = []
        for row in cur.fetchall():
            results.append({
                'chunk_id': row[0],
                'doc_id': row[1],
                'content': row[2],
                'item': row[3],
                'bm25_score': float(row[4]) if row[4] else 0.0
            })
        
        return results


# 사용 예시
if __name__ == "__main__":
    load_dotenv()
    
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'database': os.getenv('DB_NAME', 'ddoksori'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres')
    }
    
    retriever = BM25SparseRetriever(db_config)
    
    # Law 검색 테스트
    print("=== Law BM25 검색 ===")
    results = retriever.search_law_bm25("민법 제750조 불법행위")
    for i, r in enumerate(results[:3], 1):
        print(f"{i}. {r['law_name']} - Score: {r['bm25_score']:.4f}")
        print(f"   {r['content'][:100]}...")
    
    # Criteria 검색 테스트
    print("\n=== Criteria BM25 검색 ===")
    results = retriever.search_criteria_bm25("냉장고 품질보증 기준")
    for i, r in enumerate(results[:3], 1):
        item = r.get('item', 'N/A')
        print(f"{i}. {item} - Score: {r['bm25_score']:.4f}")
        print(f"   {r['content'][:100]}...")
