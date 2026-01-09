"""
BM25  Sparse Retrieval  
       
"""

import psycopg2
from typing import List, Dict
import re
import os
from dotenv import load_dotenv


class BM25SparseRetriever:
    """BM25  Sparse Retrieval (SPLADE )"""
    
    def __init__(self, db_config: Dict):
        self.db_config = db_config
        self.conn = None
    
    def connect_db(self):
        if self.conn is None or self.conn.closed:
            self.conn = psycopg2.connect(**self.db_config)
    
    def extract_keywords(self, query: str) -> List[str]:
        """   """
        keywords = []
        
        # 
        law_names = ['', '', '', '', '']
        keywords.extend([law for law in law_names if law in query])
        
        #  
        articles = re.findall(r'\s*\d+\s*', query)
        keywords.extend(articles)
        
        #  
        paragraphs = re.findall(r'\s*\d+\s*', query)
        keywords.extend(paragraphs)
        
        #  (Phase 2   )
        products = [
            '', '', '', 'TV', '', '', '', 
            '', '', '', '', '', '', 
            '', '', '', '', '', '', 
            '', '', '', '', '', ''
        ]
        keywords.extend([p for p in products if p in query])
        
        #   
        dispute_types = [
            '', '', '', '', '', '', '',
            '', '', '', '', '', '', ''
        ]
        keywords.extend([d for d in dispute_types if d in query])
        
        #   (2  )
        korean_words = re.findall(r'[-]{2,}', query)
        keywords.extend(korean_words)
        
        #      
        keywords = [k.strip() for k in keywords if k.strip()]
        return list(set(keywords))
    
    def search_law_bm25(
        self,
        query: str,
        top_k: int = 10
    ) -> List[Dict]:
        """ BM25 """
        self.connect_db()
        keywords = self.extract_keywords(query)
        
        if not keywords:
            return []
        
        # PostgreSQL Full-Text Search with BM25-like ranking
        #     to_tsvector plainto_tsquery 
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
        """ BM25 """
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
        """  BM25 """
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
        """  BM25 """
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
                'case_no': row[4] or row[5],  # case_no  case_sn
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
        """  BM25  ( + )"""
        self.connect_db()
        keywords = self.extract_keywords(query)
        
        if not keywords:
            return []
        
        #      
        mediation_results = self.search_mediation_bm25(query, top_k=top_k)
        counsel_results = self.search_counsel_bm25(query, top_k=top_k)
        
        #    
        all_results = []
        for r in mediation_results:
            r['source'] = 'mediation_case'
            all_results.append(r)
        
        for r in counsel_results:
            r['source'] = 'counsel_case'
            all_results.append(r)
        
        #   
        all_results.sort(key=lambda x: x['bm25_score'], reverse=True)
        return all_results[:top_k]


#  
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
    
    # Law  
    print("=== Law BM25  ===")
    results = retriever.search_law_bm25(" 750 ")
    for i, r in enumerate(results[:3], 1):
        print(f"{i}. {r['law_name']} - Score: {r['bm25_score']:.4f}")
        print(f"   {r['content'][:100]}...")
    
    # Criteria  
    print("\n=== Criteria BM25  ===")
    results = retriever.search_criteria_bm25("  ")
    for i, r in enumerate(results[:3], 1):
        item = r.get('item', 'N/A')
        print(f"{i}. {item} - Score: {r['bm25_score']:.4f}")
        print(f"   {r['content'][:100]}...")
    
    # Mediation Case  
    print("\n=== Mediation Case BM25  ===")
    results = retriever.search_mediation_bm25("  ")
    for i, r in enumerate(results[:3], 1):
        case_no = r.get('case_no', 'N/A')
        print(f"{i}. : {case_no} - Score: {r['bm25_score']:.4f}")
        print(f"   {r['content'][:100]}...")
    
    # Counsel Case  
    print("\n=== Counsel Case BM25  ===")
    results = retriever.search_counsel_bm25("  ")
    for i, r in enumerate(results[:3], 1):
        case_no = r.get('case_no', 'N/A')
        print(f"{i}. : {case_no} - Score: {r['bm25_score']:.4f}")
        print(f"   {r['content'][:100]}...")
    
    #  Case  
    print("\n===  Case BM25  ===")
    results = retriever.search_case_bm25("  ")
    for i, r in enumerate(results[:3], 1):
        case_no = r.get('case_no', 'N/A')
        source = r.get('source', 'N/A')
        print(f"{i}. [{source}] : {case_no} - Score: {r['bm25_score']:.4f}")
        print(f"   {r['content'][:100]}...")