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
        
        # 분쟁 유형 키워드
        dispute_types = [
            '환불', '교환', '수리', '재수리', '하자판정', '피해보상', '피해구제',
            '계약해제', '계약해지', '위약금', '손해배상', '하자', '품질', '보증'
        ]
        keywords.extend([d for d in dispute_types if d in query])
        
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
    
    def search_mediation_bm25(
        self,
        query: str,
        top_k: int = 10
    ) -> List[Dict]:
        """분쟁조정 사례 BM25 검색"""
        self.connect_db()
        keywords = self.extract_keywords(query)
        
        if not keywords:
            return []
        
        sql = """
            SELECT 
                c.chunk_id,
                c.doc_id,
                c.content,
                c.chunk_type,
                d.metadata->>'case_no' AS case_no,
                d.metadata->>'decision_date' AS decision_date,
                d.source_org AS agency,
                ts_rank_cd(
                    to_tsvector('simple', c.content),
                    plainto_tsquery('simple', %s),
                    32
                ) AS bm25_score
            FROM chunks c
            JOIN documents d ON c.doc_id = d.doc_id
            WHERE 
                d.doc_type = 'mediation_case'
                AND c.drop = FALSE
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
                'chunk_type': row[3],
                'case_no': row[4],
                'decision_date': row[5],
                'agency': row[6],
                'bm25_score': float(row[7]) if row[7] else 0.0
            })
        
        return results
    
    def search_counsel_bm25(
        self,
        query: str,
        top_k: int = 10
    ) -> List[Dict]:
        """피해구제 사례 BM25 검색"""
        self.connect_db()
        keywords = self.extract_keywords(query)
        
        if not keywords:
            return []
        
        sql = """
            SELECT 
                c.chunk_id,
                c.doc_id,
                c.content,
                c.chunk_type,
                d.metadata->>'case_no' AS case_no,
                d.metadata->>'case_sn' AS case_sn,
                d.metadata->>'decision_date' AS decision_date,
                d.source_org AS agency,
                ts_rank_cd(
                    to_tsvector('simple', c.content),
                    plainto_tsquery('simple', %s),
                    32
                ) AS bm25_score
            FROM chunks c
            JOIN documents d ON c.doc_id = d.doc_id
            WHERE 
                d.doc_type = 'counsel_case'
                AND c.drop = FALSE
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
                'chunk_type': row[3],
                'case_no': row[4] or row[5],  # case_no 또는 case_sn
                'decision_date': row[6],
                'agency': row[7],
                'bm25_score': float(row[8]) if row[8] else 0.0
            })
        
        return results
    
    def search_case_bm25(
        self,
        query: str,
        top_k: int = 10
    ) -> List[Dict]:
        """사례 통합 BM25 검색 (분쟁조정 + 피해구제)"""
        self.connect_db()
        keywords = self.extract_keywords(query)
        
        if not keywords:
            return []
        
        # 분쟁조정 사례와 피해구제 사례 모두 검색
        mediation_results = self.search_mediation_bm25(query, top_k=top_k)
        counsel_results = self.search_counsel_bm25(query, top_k=top_k)
        
        # 결과 통합 및 정렬
        all_results = []
        for r in mediation_results:
            r['source'] = 'mediation_case'
            all_results.append(r)
        
        for r in counsel_results:
            r['source'] = 'counsel_case'
            all_results.append(r)
        
        # 점수 기준 정렬
        all_results.sort(key=lambda x: x['bm25_score'], reverse=True)
        return all_results[:top_k]


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
    
    # Mediation Case 검색 테스트
    print("\n=== Mediation Case BM25 검색 ===")
    results = retriever.search_mediation_bm25("냉장고 환불 사례")
    for i, r in enumerate(results[:3], 1):
        case_no = r.get('case_no', 'N/A')
        print(f"{i}. 사건번호: {case_no} - Score: {r['bm25_score']:.4f}")
        print(f"   {r['content'][:100]}...")
    
    # Counsel Case 검색 테스트
    print("\n=== Counsel Case BM25 검색 ===")
    results = retriever.search_counsel_bm25("세탁기 수리 피해구제")
    for i, r in enumerate(results[:3], 1):
        case_no = r.get('case_no', 'N/A')
        print(f"{i}. 사건번호: {case_no} - Score: {r['bm25_score']:.4f}")
        print(f"   {r['content'][:100]}...")
    
    # 통합 Case 검색 테스트
    print("\n=== 통합 Case BM25 검색 ===")
    results = retriever.search_case_bm25("에어컨 하자 교환")
    for i, r in enumerate(results[:3], 1):
        case_no = r.get('case_no', 'N/A')
        source = r.get('source', 'N/A')
        print(f"{i}. [{source}] 사건번호: {case_no} - Score: {r['bm25_score']:.4f}")
        print(f"   {r['content'][:100]}...")