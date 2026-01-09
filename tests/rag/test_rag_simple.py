#!/usr/bin/env python3
"""
 RAG  

 (mediation_case, counsel_case)    

Requirements:
-   DB   
-    
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
    """ RAG """
    
    def __init__(self):
        """"""
        self.conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5432'),
            database=os.getenv('DB_NAME', 'ddoksori'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', 'postgres')
        )
        self.cur = self.conn.cursor(cursor_factory=RealDictCursor)
        
        self.embed_api_url = os.getenv('EMBED_API_URL', 'http://localhost:8001/embed')
        
        print("   ")
    
    def check_data_status(self) -> Dict:
        """  """
        print("\n" + "=" * 80)
        print("  ")
        print("=" * 80)
        
        # 1.  
        self.cur.execute("""
            SELECT doc_type, COUNT(*) as count
            FROM documents
            GROUP BY doc_type
            ORDER BY doc_type
        """)
        doc_counts = {row['doc_type']: row['count'] for row in self.cur.fetchall()}
        
        print("\n  :")
        for doc_type, count in doc_counts.items():
            print(f"  - {doc_type}: {count:,}")
        
        # 2.     
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
        
        print("\n  :")
        chunk_stats = {}
        for row in self.cur.fetchall():
            doc_type = row['doc_type']
            chunk_stats[doc_type] = row
            
            embedded_rate = (row['embedded_chunks'] / row['total_chunks'] * 100) if row['total_chunks'] > 0 else 0
            print(f"  [{doc_type}]")
            print(f"    -  : {row['total_chunks']:,}")
            print(f"    -  : {row['embedded_chunks']:,} ({embedded_rate:.1f}%)")
            print(f"    -  : {row['active_chunks']:,}")
        
        # 3.   (mediation_case, counsel_case) 
        case_types = ['mediation_case', 'counsel_case']
        case_available = {ct: ct in doc_counts and chunk_stats.get(ct, {}).get('embedded_chunks', 0) > 0 
                         for ct in case_types}
        
        print("\n    :")
        for case_type in case_types:
            if case_available[case_type]:
                print(f"   {case_type}:  ")
            else:
                print(f"   {case_type}:   (    )")
        
        return {
            'doc_counts': doc_counts,
            'chunk_stats': chunk_stats,
            'case_available': case_available,
            'ready': any(case_available.values())
        }
    
    def get_query_embedding(self, query: str) -> List[float]:
        """  """
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
            print(f"  API : {e}")
            print(f"   API URL: {self.embed_api_url}")
            print("       .")
            return None
    
    def search_similar_cases(self, query: str, top_k: int = 5, min_similarity: float = 0.0) -> List[Dict]:
        """
            
        
        Args:
            query:  
            top_k:  k 
            min_similarity:  
        
        Returns:
              
        """
        print(f"\n  : {query}")
        print(f"   top_k: {top_k}, min_similarity: {min_similarity}")
        
        # 1.   
        query_embedding = self.get_query_embedding(query)
        if query_embedding is None:
            return []
        
        print("       ")
        
        # 2.   ( )
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
        
        print(f"    {len(results)}  ")
        
        return [dict(row) for row in results]
    
    def display_results(self, results: List[Dict]):
        """  """
        print("\n" + "=" * 80)
        print(" ")
        print("=" * 80)
        
        if not results:
            print("   .")
            return
        
        for idx, result in enumerate(results, 1):
            print(f"\n[{idx}] : {result['similarity']:.4f}")
            print(f"     : {result['doc_type']}")
            print(f"    : {result['source_org']}")
            print(f"    : {result['title']}")
            print(f"     ID: {result['chunk_id']}")
            print(f"     : {result['chunk_type']}")
            print(f"    : {result['content_length']}")
            
            #  
            content_preview = result['content'][:300].replace('\n', ' ')
            print(f"    : {content_preview}...")
            
            # 
            if result.get('metadata'):
                metadata = result['metadata']
                if isinstance(metadata, str):
                    try:
                        metadata = json.loads(metadata)
                    except:
                        pass
                
                if isinstance(metadata, dict):
                    if 'case_no' in metadata:
                        print(f"    : {metadata['case_no']}")
                    if 'decision_date' in metadata:
                        print(f"    : {metadata['decision_date']}")
    
    def run_test_queries(self):
        """  """
        print("\n" + "=" * 80)
        print("RAG   ")
        print("=" * 80)
        
        test_queries = [
            {
                'query': '    .    ?',
                'top_k': 3,
                'min_similarity': 0.3
            },
            {
                'query': '     .',
                'top_k': 3,
                'min_similarity': 0.3
            },
            {
                'query': '     .',
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
        """ """
        print("\n" + "=" * 80)
        print("  ")
        print("=" * 80)
        print("    .")
        print(" 'quit'  'exit' .")
        print("-" * 80)
        
        while True:
            try:
                query = input("\n : ").strip()
                
                if query.lower() in ['quit', 'exit', 'q']:
                    print(".")
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
                print("\n\n.")
                break
            except Exception as e:
                print(f" : {e}")
    
    def close(self):
        """ """
        if self.cur:
            self.cur.close()
        if self.conn:
            self.conn.close()

def main():
    """ """
    import sys
    
    tester = SimpleRAGTester()
    
    try:
        # 1.   
        status = tester.check_data_status()
        
        if not status['ready']:
            print("\n" + "=" * 80)
            print(" RAG    .")
            print("=" * 80)
            print("\n   :")
            print("1.  : python backend/scripts/data_processing/data_transform_pipeline.py")
            print("2. DB : (   DB   )")
            print("3.  : python backend/scripts/embedding/embed_data_remote.py")
            return 1
        
        print("\n RAG   !")
        
        # 2.  
        if len(sys.argv) > 1 and sys.argv[1] == '--test':
            #  :    
            tester.run_test_queries()
        else:
            #  
            tester.interactive_search()
        
        return 0
        
    except Exception as e:
        print(f"\n  : {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        tester.close()

if __name__ == '__main__':
    exit(main())
