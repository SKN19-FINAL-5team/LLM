#!/usr/bin/env python3
"""
   

     .
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import requests
from typing import List, Dict, Tuple
import json
from datetime import datetime

load_dotenv()

class SearchQualityTester:
    """  """
    
    def __init__(self):
        """"""
        try:
            self.conn = psycopg2.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                port=os.getenv('DB_PORT', '5432'),
                database=os.getenv('DB_NAME', 'ddoksori'),
                user=os.getenv('DB_USER', 'postgres'),
                password=os.getenv('DB_PASSWORD', 'postgres')
            )
            self.cur = self.conn.cursor(cursor_factory=RealDictCursor)
            print("   ")
        except Exception as e:
            print(f"   : {e}")
            sys.exit(1)
        
        self.embed_api_url = os.getenv('EMBED_API_URL', 'http://localhost:8001/embed')
    
    def check_data_status(self) -> Dict:
        """  """
        print("\n" + "=" * 100)
        print("  ")
        print("=" * 100)
        
        #     
        self.cur.execute("""
            SELECT 
                COUNT(*) as total_chunks,
                COUNT(CASE WHEN embedding IS NOT NULL THEN 1 END) as embedded_chunks,
                COUNT(CASE WHEN drop = FALSE THEN 1 END) as active_chunks,
                COUNT(CASE WHEN drop = FALSE AND embedding IS NOT NULL THEN 1 END) as searchable_chunks
            FROM chunks
        """)
        
        stats = dict(self.cur.fetchone())
        
        print(f"\n  :")
        print(f"  -  : {stats['total_chunks']:,}")
        print(f"  -  : {stats['active_chunks']:,}")
        print(f"  -  : {stats['embedded_chunks']:,}")
        print(f"  -  : {stats['searchable_chunks']:,}")
        
        if stats['searchable_chunks'] > 0:
            embed_rate = stats['embedded_chunks'] / stats['total_chunks'] * 100
            searchable_rate = stats['searchable_chunks'] / stats['active_chunks'] * 100
            print(f"\n   : {embed_rate:.1f}%")
            print(f"   : {searchable_rate:.1f}%")
        
        return stats
    
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
            print(f"    API : {e}")
            return None
    
    def search_chunks(self, query: str, top_k: int = 10, 
                     doc_types: List[str] = None) -> List[Dict]:
        """ """
        #   
        query_embedding = self.get_query_embedding(query)
        if query_embedding is None:
            return []
        
        # 
        if doc_types:
            query_sql = """
                SELECT 
                    c.chunk_id,
                    c.doc_id,
                    c.chunk_type,
                    c.content,
                    c.content_length,
                    d.doc_type,
                    d.title,
                    d.source_org,
                    1 - (c.embedding <=> %s::vector) AS similarity
                FROM chunks c
                JOIN documents d ON c.doc_id = d.doc_id
                WHERE 
                    c.drop = FALSE
                    AND c.embedding IS NOT NULL
                    AND d.doc_type = ANY(%s)
                ORDER BY c.embedding <=> %s::vector
                LIMIT %s
            """
            params = [query_embedding, doc_types, query_embedding, top_k]
        else:
            query_sql = """
                SELECT 
                    c.chunk_id,
                    c.doc_id,
                    c.chunk_type,
                    c.content,
                    c.content_length,
                    d.doc_type,
                    d.title,
                    d.source_org,
                    1 - (c.embedding <=> %s::vector) AS similarity
                FROM chunks c
                JOIN documents d ON c.doc_id = d.doc_id
                WHERE 
                    c.drop = FALSE
                    AND c.embedding IS NOT NULL
                ORDER BY c.embedding <=> %s::vector
                LIMIT %s
            """
            params = [query_embedding, query_embedding, top_k]
        
        self.cur.execute(query_sql, params)
        return [dict(row) for row in self.cur.fetchall()]
    
    def evaluate_relevance(self, query: str, result: Dict) -> Dict:
        """   (  )"""
        content = result['content'].lower()
        query_terms = query.lower().split()
        
        #  
        matched_terms = [term for term in query_terms if term in content]
        keyword_score = len(matched_terms) / len(query_terms) if query_terms else 0
        
        return {
            'keyword_score': keyword_score,
            'matched_terms': matched_terms,
            'similarity': result['similarity']
        }
    
    def run_test_queries(self) -> List[Dict]:
        """  """
        print("\n" + "=" * 100)
        print("  ")
        print("=" * 100)
        
        test_cases = [
            {
                'id': 1,
                'query': '    .    ?',
                'doc_types': ['counsel_case', 'mediation_case'],
                'expected_keywords': ['', '', '', '']
            },
            {
                'id': 2,
                'query': '  ',
                'doc_types': ['counsel_case', 'mediation_case'],
                'expected_keywords': ['', '']
            },
            {
                'id': 3,
                'query': '     ',
                'doc_types': ['counsel_case', 'mediation_case'],
                'expected_keywords': ['', '', '']
            },
            {
                'id': 4,
                'query': '   ',
                'doc_types': ['counsel_case'],
                'expected_keywords': ['', '']
            },
            {
                'id': 5,
                'query': '  ',
                'doc_types': ['counsel_case', 'mediation_case'],
                'expected_keywords': ['', '', '']
            }
        ]
        
        results = []
        
        for test_case in test_cases:
            print(f"\n[ {test_case['id']}] {test_case['query']}")
            print("-" * 100)
            
            search_results = self.search_chunks(
                query=test_case['query'],
                top_k=5,
                doc_types=test_case.get('doc_types')
            )
            
            if not search_results:
                print("     ")
                results.append({
                    'test_id': test_case['id'],
                    'query': test_case['query'],
                    'success': False,
                    'results_count': 0
                })
                continue
            
            print(f"   {len(search_results)}  ")
            
            #  3  
            evaluations = []
            for idx, result in enumerate(search_results[:3], 1):
                eval_result = self.evaluate_relevance(test_case['query'], result)
                evaluations.append(eval_result)
                
                print(f"\n  [{idx}] : {result['similarity']:.4f}, "
                      f" : {eval_result['keyword_score']:.2f}")
                print(f"      : {result['doc_type']}/{result['chunk_type']}, "
                      f": {result['content_length']}")
                print(f"      : {result['title'][:80]}")
                print(f"      : {result['content'][:150].replace(chr(10), ' ')}...")
            
            #   
            avg_similarity = sum(e['similarity'] for e in evaluations) / len(evaluations)
            avg_keyword_score = sum(e['keyword_score'] for e in evaluations) / len(evaluations)
            
            results.append({
                'test_id': test_case['id'],
                'query': test_case['query'],
                'success': True,
                'results_count': len(search_results),
                'avg_similarity': avg_similarity,
                'avg_keyword_score': avg_keyword_score,
                'top_similarity': search_results[0]['similarity'],
                'evaluations': evaluations
            })
        
        return results
    
    def generate_report(self, test_results: List[Dict], stats: Dict) -> str:
        """  """
        print("\n" + "=" * 100)
        print("    ")
        print("=" * 100)
        
        report = []
        report.append("=" * 100)
        report.append("   ")
        report.append("=" * 100)
        report.append(f" : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # 1.  
        report.append("1.  ")
        report.append("-" * 100)
        report.append(f" : {stats['total_chunks']:,}")
        report.append(f" : {stats['active_chunks']:,}")
        report.append(f"  : {stats['searchable_chunks']:,}")
        
        if stats['searchable_chunks'] > 0:
            searchable_rate = stats['searchable_chunks'] / stats['active_chunks'] * 100
            report.append(f" : {searchable_rate:.1f}%")
        
        report.append("")
        
        # 2.   
        report.append("2.   ")
        report.append("-" * 100)
        
        successful_tests = [r for r in test_results if r['success']]
        
        if successful_tests:
            avg_similarity = sum(r['avg_similarity'] for r in successful_tests) / len(successful_tests)
            avg_keyword = sum(r['avg_keyword_score'] for r in successful_tests) / len(successful_tests)
            avg_top_sim = sum(r['top_similarity'] for r in successful_tests) / len(successful_tests)
            
            report.append(f" : {len(successful_tests)}/{len(test_results)}")
            report.append(f"  ( 3): {avg_similarity:.4f}")
            report.append(f"   : {avg_keyword:.2f}")
            report.append(f"  : {avg_top_sim:.4f}")
        else:
            report.append("   ")
        
        report.append("")
        
        # 3.   
        report.append("3.   ")
        report.append("-" * 100)
        
        for result in test_results:
            report.append(f"\n[ {result['test_id']}] {result['query']}")
            
            if result['success']:
                report.append(f"   : {result['results_count']} ")
                report.append(f"   : {result['avg_similarity']:.4f}")
                report.append(f"   : {result['avg_keyword_score']:.2f}")
                report.append(f"   : {result['top_similarity']:.4f}")
            else:
                report.append(f"   :   ")
        
        report.append("")
        
        # 4.  
        report.append("4.   ")
        report.append("-" * 100)
        
        if successful_tests:
            if avg_similarity >= 0.7:
                report.append(" :   0.7 ")
            elif avg_similarity >= 0.5:
                report.append("  :   0.5 ")
            else:
                report.append("  :   0.5 ")
            
            if avg_keyword >= 0.3:
                report.append("   ")
            else:
                report.append("     ")
        
        report.append("")
        
        # 5.  
        report.append("5.  ")
        report.append("-" * 100)
        
        if stats['searchable_chunks'] < stats['active_chunks']:
            remaining = stats['active_chunks'] - stats['searchable_chunks']
            report.append(f"  {remaining:,}    ")
        
        if successful_tests and avg_similarity < 0.7:
            report.append("          ")
        
        report.append("")
        report.append("=" * 100)
        
        return "\n".join(report)
    
    def save_report(self, report: str, output_file: str = None):
        """ """
        if output_file is None:
            output_file = "backend/data/transformed/search_quality_report.txt"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"\n  : {output_file}")
    
    def run(self):
        """ """
        print("=" * 100)
        print("   ")
        print("=" * 100)
        
        try:
            # 1.   
            stats = self.check_data_status()
            
            if stats['searchable_chunks'] == 0:
                print("\n    .")
                print("     : python backend/scripts/embedding/embed_data_remote.py")
                return 1
            
            # 2.   
            test_results = self.run_test_queries()
            
            # 3.  
            report = self.generate_report(test_results, stats)
            
            # 4.   
            print("\n" + report)
            self.save_report(report)
            
            print("\n  !")
            return 0
            
        except Exception as e:
            print(f"\n  : {e}")
            import traceback
            traceback.print_exc()
            return 1
        finally:
            if self.cur:
                self.cur.close()
            if self.conn:
                self.conn.close()

def main():
    """ """
    tester = SearchQualityTester()
    return tester.run()

if __name__ == '__main__':
    sys.exit(main())
