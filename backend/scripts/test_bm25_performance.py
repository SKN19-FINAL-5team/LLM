#!/usr/bin/env python3
"""
BM25 Retriever    

    BM25   ,
  (cosine, SPLADE, hybrid) .
"""

import os
import sys
import json
import time
from typing import List, Dict, Optional
from pathlib import Path
from dotenv import load_dotenv
from collections import defaultdict

#   
backend_dir = Path(__file__).parent.parent
project_root = backend_dir.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_dir))

#   
env_file = backend_dir / '.env'
if env_file.exists():
    load_dotenv(env_file)
else:
    load_dotenv()

from app.rag.multi_method_retriever import MultiMethodRetriever


class BM25PerformanceTester:
    """BM25  """
    
    #   
    TEST_QUERIES = {
        'law': [
            " 750 ",
            " 68 ",
            "  ",
            "  ",
            " 101 "
        ],
        'criteria': [
            "  ",
            "   ",
            "  ",
            "TV  ",
            "  "
        ],
        'mediation_case': [
            "  ",
            "   ",
            "  ",
            "TV   ",
            "  "
        ],
        'counsel_case': [
            "  ",
            "  ",
            "  ",
            "TV  ",
            "  "
        ],
        'mixed': [
            "  ",
            "   ",
            "    ",
            "TV   ",
            "   "
        ]
    }
    
    def __init__(self, db_config: Dict):
        """
        Args:
            db_config:   
        """
        self.db_config = db_config
        self.retriever = None
        self.results = defaultdict(list)
    
    def initialize(self):
        """Retriever """
        print("=" * 80)
        print("BM25 Retriever  ")
        print("=" * 80)
        print("\n1. MultiMethodRetriever  ...")
        
        try:
            self.retriever = MultiMethodRetriever(self.db_config)
            print("  \n")
            return True
        except Exception as e:
            print(f"  : {e}\n")
            return False
    
    def test_single_query(
        self,
        query: str,
        category: str,
        top_k: int = 10,
        methods: Optional[List[str]] = None
    ) -> Dict:
        """
          
        
        Args:
            query:  
            category:  
            top_k:    
            methods:    
        
        Returns:
              
        """
        if methods is None:
            methods = ['cosine', 'bm25', 'splade', 'hybrid']
        
        print(f"\n{'=' * 80}")
        print(f" : {query}")
        print(f" : {category}")
        print(f"{'=' * 80}")
        
        query_results = {
            'query': query,
            'category': category,
            'methods': {}
        }
        
        #    
        for method in methods:
            if method == 'cosine':
                result = self.retriever.search_cosine(query, top_k=top_k)
            elif method == 'bm25':
                result = self.retriever.search_bm25(query, top_k=top_k)
            elif method == 'splade':
                result = self.retriever.search_splade(query, top_k=top_k)
            elif method == 'hybrid':
                result = self.retriever.search_hybrid(query, top_k=top_k)
            else:
                continue
            
            #  
            method_result = {
                'success': result.get('success', False),
                'count': result.get('count', 0),
                'elapsed_time': result.get('elapsed_time', 0.0),
                'error': result.get('error'),
                'top_scores': [],
                'source_distribution': defaultdict(int)
            }
            
            if method_result['success'] and result.get('results'):
                #   
                scores = [r.get('score', 0.0) for r in result['results'][:5]]
                method_result['top_scores'] = scores
                
                #   
                for r in result['results']:
                    source = r.get('source', 'unknown')
                    method_result['source_distribution'][source] += 1
                
                #   
                print(f"\n[{method.upper()}]")
                print(f"   : {method_result['count']} ")
                print(f"  ⏱  : {method_result['elapsed_time']*1000:.1f}ms")
                print(f"    : {[f'{s:.4f}' for s in scores[:3]]}")
                print(f"    : {dict(method_result['source_distribution'])}")
            else:
                print(f"\n[{method.upper()}]")
                print(f"   : {method_result.get('error', 'Unknown error')}")
            
            query_results['methods'][method] = method_result
        
        return query_results
    
    def test_all_queries(self, top_k: int = 10) -> Dict:
        """
           
        
        Args:
            top_k:    
        
        Returns:
              
        """
        all_results = {
            'test_time': time.strftime('%Y-%m-%d %H:%M:%S'),
            'queries': [],
            'summary': {}
        }
        
        #   
        for category, queries in self.TEST_QUERIES.items():
            print(f"\n\n{'#' * 80}")
            print(f"# : {category.upper()}")
            print(f"{'#' * 80}")
            
            for query in queries:
                result = self.test_single_query(query, category, top_k=top_k)
                all_results['queries'].append(result)
                time.sleep(0.1)  # DB  
        
        #    
        all_results['summary'] = self._calculate_summary(all_results['queries'])
        
        return all_results
    
    def _calculate_summary(self, query_results: List[Dict]) -> Dict:
        """     """
        summary = {
            'total_queries': len(query_results),
            'methods': defaultdict(lambda: {
                'total_tests': 0,
                'successful': 0,
                'failed': 0,
                'avg_count': 0.0,
                'avg_time': 0.0,
                'total_time': 0.0,
                'avg_top_score': 0.0
            })
        }
        
        for query_result in query_results:
            for method, method_result in query_result['methods'].items():
                stats = summary['methods'][method]
                stats['total_tests'] += 1
                
                if method_result['success']:
                    stats['successful'] += 1
                    stats['avg_count'] += method_result['count']
                    stats['avg_time'] += method_result['elapsed_time']
                    stats['total_time'] += method_result['elapsed_time']
                    
                    if method_result['top_scores']:
                        stats['avg_top_score'] += method_result['top_scores'][0]
                else:
                    stats['failed'] += 1
        
        #  
        for method, stats in summary['methods'].items():
            if stats['successful'] > 0:
                stats['avg_count'] /= stats['successful']
                stats['avg_time'] /= stats['successful']
                stats['avg_top_score'] /= stats['successful']
        
        return summary
    
    def print_summary(self, all_results: Dict):
        """   """
        print("\n\n" + "=" * 80)
        print("   ")
        print("=" * 80)
        
        summary = all_results['summary']
        print(f"\n   : {summary['total_queries']}")
        
        print("\n  :")
        print("-" * 80)
        print(f"{'Method':<10} {'Success':<10} {'Failed':<10} {'Avg Count':<12} {'Avg Time (ms)':<15} {'Avg Top Score':<15}")
        print("-" * 80)
        
        for method, stats in summary['methods'].items():
            print(f"{method:<10} {stats['successful']:<10} {stats['failed']:<10} "
                  f"{stats['avg_count']:<12.1f} {stats['avg_time']*1000:<15.1f} {stats['avg_top_score']:<15.4f}")
        
        print("\n" + "=" * 80)
        
        # BM25  
        if 'bm25' in summary['methods']:
            bm25_stats = summary['methods']['bm25']
            print("\n BM25   :")
            print(f"  - : {bm25_stats['successful']}/{bm25_stats['total_tests']} "
                  f"({bm25_stats['successful']/bm25_stats['total_tests']*100:.1f}%)")
            print(f"  -   : {bm25_stats['avg_count']:.1f}")
            print(f"  -   : {bm25_stats['avg_time']*1000:.1f}ms")
            print(f"  -   : {bm25_stats['avg_top_score']:.4f}")
    
    def save_results(self, all_results: Dict, output_file: str = 'bm25_test_results.json'):
        """  JSON  """
        output_path = backend_dir / 'scripts' / output_file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        print(f"\n   : {output_path}")


def main():
    """ """
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'database': os.getenv('DB_NAME', 'ddoksori'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres')
    }
    
    tester = BM25PerformanceTester(db_config)
    
    if not tester.initialize():
        print("    .")
        return
    
    #   
    print("\n2.   ...\n")
    all_results = tester.test_all_queries(top_k=10)
    
    #   
    tester.print_summary(all_results)
    
    #  
    tester.save_results(all_results)
    
    print("\n  !")


if __name__ == "__main__":
    main()
