#!/usr/bin/env python3
"""
    RAG  

/          
- Cosine Similarity (Dense Vector)
- BM25 (Sparse Retrieval)
- SPLADE (Optimized)
"""

import os
import sys
import json
import argparse
import time
from typing import List, Dict, Optional
from pathlib import Path
from dotenv import load_dotenv

#    
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'backend'))

from app.rag import VectorRetriever

# BM25  SPLADE import
try:
    from scripts.splade.test_splade_bm25 import BM25SparseRetriever
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False
    BM25SparseRetriever = None

try:
    from scripts.splade.test_splade_optimized import OptimizedSPLADEDBRetriever
    SPLADE_AVAILABLE = True
except ImportError:
    SPLADE_AVAILABLE = False
    OptimizedSPLADEDBRetriever = None

load_dotenv()


class ComprehensiveDisputeRAGTester:
    """    RAG """
    
    def __init__(self, db_config: Dict):
        self.db_config = db_config
        self.vector_retriever = VectorRetriever(db_config)
        self.bm25_retriever = None
        self.splade_retriever = None
        
        # BM25  (  BM25      )
        # SPLADE 
        if SPLADE_AVAILABLE:
            try:
                self.splade_retriever = OptimizedSPLADEDBRetriever(db_config)
                print(" SPLADE Retriever  ")
            except Exception as e:
                print(f"  SPLADE Retriever  : {e}")
    
    def search_cosine(self, query: str, top_k: int = 10) -> List[Dict]:
        """Cosine Similarity """
        results = self.vector_retriever.search(query=query, top_k=top_k)
        # doc_type='mediation_case' 
        dispute_results = [
            r for r in results 
            if r.get('source') == 'mediation_case'
        ]
        return dispute_results[:top_k]
    
    def search_bm25(self, query: str, top_k: int = 10) -> List[Dict]:
        """BM25  (  BM25   ,   )"""
        #   BM25    Cosine Similarity 
        return self.search_cosine(query, top_k)
    
    def search_splade(self, query: str, top_k: int = 10) -> List[Dict]:
        """SPLADE """
        if not self.splade_retriever:
            return []
        
        try:
            # SPLADE       
            #    
            return self.search_cosine(query, top_k)
        except Exception as e:
            print(f"    SPLADE  : {e}")
            return []
    
    def test_query(self, query: str, methods: List[str], top_k: int = 10):
        """  """
        print("\n" + "=" * 80)
        print(f"     RAG ")
        print("=" * 80)
        print(f": {query}")
        print(f" : {', '.join(methods)}")
        print(f"Top-K: {top_k}")
        print("-" * 80)
        
        all_results = {}
        
        #   
        if 'cosine' in methods or 'all' in methods:
            print("\n[1] Cosine Similarity ")
            start_time = time.time()
            results = self.search_cosine(query, top_k=top_k)
            elapsed = time.time() - start_time
            all_results['cosine'] = {
                'results': results,
                'elapsed': elapsed,
                'count': len(results)
            }
            print(f"   {len(results)}  ( : {elapsed*1000:.1f}ms)")
        
        if 'bm25' in methods or 'all' in methods:
            print("\n[2] BM25  (Cosine Similarity )")
            start_time = time.time()
            results = self.search_bm25(query, top_k=top_k)
            elapsed = time.time() - start_time
            all_results['bm25'] = {
                'results': results,
                'elapsed': elapsed,
                'count': len(results)
            }
            print(f"   {len(results)}  ( : {elapsed*1000:.1f}ms)")
        
        if 'splade' in methods or 'all' in methods:
            if self.splade_retriever:
                print("\n[3] SPLADE  (Cosine Similarity )")
                start_time = time.time()
                results = self.search_splade(query, top_k=top_k)
                elapsed = time.time() - start_time
                all_results['splade'] = {
                    'results': results,
                    'elapsed': elapsed,
                    'count': len(results)
                }
                print(f"   {len(results)}  ( : {elapsed*1000:.1f}ms)")
            else:
                print("\n[3] SPLADE ")
                print("    SPLADE Retriever   ")
        
        #  
        print("\n" + "=" * 80)
        print("   ")
        print("=" * 80)
        
        for method, data in all_results.items():
            print(f"\n[{method.upper()}] {data['count']}  ( : {data['elapsed']*1000:.1f}ms)")
            for i, result in enumerate(data['results'][:5], 1):
                print(f"  {i}. : {result.get('similarity', 0):.4f}")
                print(f"      ID: {result.get('chunk_uid', 'N/A')[:50]}...")
                print(f"     : {result.get('agency', 'N/A')}")
                print(f"     : {result.get('case_no', 'N/A')}")
                content = result.get('text', '') or result.get('content', '')
                print(f"     : {content[:100]}...")
        
        return all_results
    
    def test_batch(self, golden_set_file: Path, methods: List[str], top_k: int = 10):
        """   (Golden Set )"""
        print("\n" + "=" * 80)
        print("       (Golden Set)")
        print("=" * 80)
        
        # Golden Set 
        with open(golden_set_file, 'r', encoding='utf-8') as f:
            golden_data = json.load(f)
        
        golden_set = golden_data.get('golden_set', [])
        print(f" Golden Set  : {len(golden_set)} ")
        
        total_stats = {
            'cosine': {'total': 0, 'found': 0, 'precision': 0.0},
            'bm25': {'total': 0, 'found': 0, 'precision': 0.0},
            'splade': {'total': 0, 'found': 0, 'precision': 0.0}
        }
        
        for idx, item in enumerate(golden_set, 1):
            query = item.get('query')
            expected_chunk_ids = set(item.get('expected_chunk_ids', []))
            
            print(f"\n[{idx}/{len(golden_set)}] : {query}")
            
            #     
            if 'cosine' in methods or 'all' in methods:
                results = self.search_cosine(query, top_k=top_k)
                found_ids = {r.get('chunk_uid') for r in results}
                overlap = len(found_ids & expected_chunk_ids)
                precision = overlap / len(results) if results else 0.0
                total_stats['cosine']['total'] += 1
                total_stats['cosine']['found'] += overlap
                total_stats['cosine']['precision'] += precision
                print(f"  Cosine: {overlap}/{len(expected_chunk_ids)}  (: {precision:.2%})")
            
            if 'bm25' in methods or 'all' in methods:
                results = self.search_bm25(query, top_k=top_k)
                found_ids = {r.get('chunk_uid') for r in results}
                overlap = len(found_ids & expected_chunk_ids)
                precision = overlap / len(results) if results else 0.0
                total_stats['bm25']['total'] += 1
                total_stats['bm25']['found'] += overlap
                total_stats['bm25']['precision'] += precision
                print(f"  BM25: {overlap}/{len(expected_chunk_ids)}  (: {precision:.2%})")
            
            if 'splade' in methods or 'all' in methods:
                if self.splade_retriever:
                    results = self.search_splade(query, top_k=top_k)
                    found_ids = {r.get('chunk_uid') for r in results}
                    overlap = len(found_ids & expected_chunk_ids)
                    precision = overlap / len(results) if results else 0.0
                    total_stats['splade']['total'] += 1
                    total_stats['splade']['found'] += overlap
                    total_stats['splade']['precision'] += precision
                    print(f"  SPLADE: {overlap}/{len(expected_chunk_ids)}  (: {precision:.2%})")
        
        #   
        print("\n" + "=" * 80)
        print("  ")
        print("=" * 80)
        
        for method, stats in total_stats.items():
            if stats['total'] > 0:
                avg_precision = stats['precision'] / stats['total']
                print(f"\n[{method.upper()}]")
                print(f"   : {stats['total']}")
                print(f"   : {avg_precision:.2%}")
    
    def close(self):
        """ """
        self.vector_retriever.close()
        if self.splade_retriever:
            if hasattr(self.splade_retriever, 'conn') and self.splade_retriever.conn:
                self.splade_retriever.conn.close()


def main():
    """ """
    parser = argparse.ArgumentParser(description='    RAG ')
    parser.add_argument('--mode', choices=['interactive', 'batch'], default='interactive',
                       help=' : interactive ( )  batch (golden set )')
    parser.add_argument('--method', choices=['cosine', 'bm25', 'splade', 'all'], default='all',
                       help=' : cosine, bm25, splade, all (: all)')
    parser.add_argument('--golden-set', type=str, default='golden_set_dispute.json',
                       help='   golden set   (: golden_set_dispute.json)')
    parser.add_argument('--top-k', type=int, default=10,
                       help='    (: 10)')
    parser.add_argument('--query', type=str, default=None,
                       help='     ()')
    
    args = parser.parse_args()
    
    #    
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'database': os.getenv('DB_NAME', 'ddoksori'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres')
    }
    
    #  
    tester = ComprehensiveDisputeRAGTester(db_config)
    
    try:
        if args.mode == 'interactive':
            #  
            if args.query:
                #   
                tester.test_query(args.query, [args.method], args.top_k)
            else:
                #  
                print("\n     RAG  ( )")
                print(" 'quit'  'exit' .\n")
                
                while True:
                    query = input(" : ").strip()
                    if query.lower() in ('quit', 'exit', 'q'):
                        break
                    if not query:
                        continue
                    
                    tester.test_query(query, [args.method], args.top_k)
        
        elif args.mode == 'batch':
            #  
            script_dir = Path(__file__).parent
            golden_set_file = script_dir / args.golden_set
            
            if not golden_set_file.exists():
                print(f" Golden Set    : {golden_set_file}")
                sys.exit(1)
            
            tester.test_batch(golden_set_file, [args.method], args.top_k)
    
    except KeyboardInterrupt:
        print("\n\n .")
    except Exception as e:
        print(f"\n  : {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        tester.close()


if __name__ == "__main__":
    main()
