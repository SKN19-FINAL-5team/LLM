"""
  - RAG   v2
: 2026-01-05
  RAG   
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

#   backend  Python  
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'backend'))

from rag.retriever import RAGRetriever, SearchResult
from typing import List
import time


class RAGTester:
    """RAG  """
    
    def __init__(self, retriever: RAGRetriever):
        self.retriever = retriever
        self.test_scenarios = self._create_test_scenarios()
    
    def _create_test_scenarios(self) -> List[dict]:
        """  """
        return [
            {
                'name': ' 1:    ',
                'query': '   .    ?',
                'query_type': 'general_inquiry',
                'expected_doc_types': ['counsel_case', 'mediation_case', 'law'],
                'description': '  .      .'
            },
            {
                'name': ' 2:   ',
                'query': '   ?',
                'query_type': 'legal_interpretation',
                'expected_doc_types': ['law'],
                'description': '  .     .'
            },
            {
                'name': ' 3:   ',
                'query': '     ?',
                'query_type': 'similar_case',
                'expected_doc_types': ['mediation_case', 'counsel_case'],
                'description': '  .    .'
            },
            {
                'name': ' 4:   ',
                'query': '   ?',
                'query_type': 'general_inquiry',
                'expected_doc_types': ['counsel_case', 'law'],
                'description': '   .    .'
            },
            {
                'name': ' 5:   ',
                'query': '   ?',
                'query_type': 'legal_interpretation',
                'expected_doc_types': ['law', 'counsel_case'],
                'description': '  .     .'
            },
            {
                'name': ' 6:  ',
                'query': '    ?',
                'query_type': 'general_inquiry',
                'expected_doc_types': ['counsel_case', 'law'],
                'description': '  .    .'
            }
        ]
    
    def run_all_tests(self):
        """   """
        print("=" * 80)
        print("  - RAG  ")
        print("=" * 80)
        print()
        
        for i, scenario in enumerate(self.test_scenarios, 1):
            print(f"\n{'=' * 80}")
            print(f"{scenario['name']}")
            print(f"{'=' * 80}")
            print(f": {scenario['description']}")
            print(f": {scenario['query']}")
            print(f" : {scenario['query_type']}")
            print(f"  : {', '.join(scenario['expected_doc_types'])}")
            print()
            
            # 1.  
            print("--- [1]   (Vector Search) ---")
            start_time = time.time()
            vector_results = self.retriever.vector_search(scenario['query'], top_k=5)
            vector_time = time.time() - start_time
            self._print_results(vector_results, vector_time)
            
            # 2.  
            print("\n--- [2]   (Hybrid Search) ---")
            start_time = time.time()
            hybrid_results = self.retriever.hybrid_search(scenario['query'], top_k=5)
            hybrid_time = time.time() - start_time
            self._print_results(hybrid_results, hybrid_time)
            
            # 3.   
            print("\n--- [3]    (Multi-Source Search) ---")
            start_time = time.time()
            multi_results = self.retriever.multi_source_search(
                scenario['query'],
                query_type=scenario['query_type'],
                top_k=5
            )
            multi_time = time.time() - start_time
            self._print_results(multi_results, multi_time)
            
            # 4.  
            if vector_results:
                print("\n--- [4]   (Context Expansion) ---")
                print(f"     (window_size=1)")
                start_time = time.time()
                context_results = self.retriever.get_chunk_with_context(
                    vector_results[0].chunk_id,
                    window_size=1
                )
                context_time = time.time() - start_time
                self._print_context_results(context_results, context_time)
            
            # 5. 
            print("\n--- [5]  (Evaluation) ---")
            self._evaluate_results(
                scenario['expected_doc_types'],
                vector_results,
                hybrid_results,
                multi_results
            )
            
            print("\n" + "=" * 80)
            input("\n   Enter ...")
    
    def _print_results(self, results: List[SearchResult], elapsed_time: float):
        """  """
        print(f" : {elapsed_time:.3f}")
        print(f"  : {len(results)}\n")
        
        for i, result in enumerate(results, 1):
            print(f"[{i}] : {result.similarity:.4f}")
            print(f"     : {result.doc_type}")
            print(f"     : {result.chunk_type}")
            print(f"    : {result.doc_title}")
            print(f"    : {' > '.join(result.category_path) if result.category_path else 'N/A'}")
            print(f"     ( 100): {result.content[:100]}...")
            print()
    
    def _print_context_results(self, results: List[SearchResult], elapsed_time: float):
        """   """
        print(f" : {elapsed_time:.3f}")
        print(f"  : {len(results)}\n")
        
        for i, result in enumerate(results, 1):
            is_target = result.metadata and result.metadata.get('is_target', False)
            marker = " []" if is_target else "  "
            print(f"{marker} [{i}] {result.chunk_type}")
            print(f"     ( 100): {result.content[:100]}...")
            print()
    
    def _evaluate_results(
        self,
        expected_doc_types: List[str],
        vector_results: List[SearchResult],
        hybrid_results: List[SearchResult],
        multi_results: List[SearchResult]
    ):
        """  """
        def calculate_coverage(results: List[SearchResult]) -> float:
            """    """
            found_types = set(r.doc_type for r in results)
            expected_types = set(expected_doc_types)
            if not expected_types:
                return 1.0
            return len(found_types & expected_types) / len(expected_types)
        
        def calculate_diversity(results: List[SearchResult]) -> float:
            """  """
            if not results:
                return 0.0
            doc_types = [r.doc_type for r in results]
            return len(set(doc_types)) / len(doc_types)
        
        #   
        vector_coverage = calculate_coverage(vector_results)
        hybrid_coverage = calculate_coverage(hybrid_results)
        multi_coverage = calculate_coverage(multi_results)
        
        vector_diversity = calculate_diversity(vector_results)
        hybrid_diversity = calculate_diversity(hybrid_results)
        multi_diversity = calculate_diversity(multi_results)
        
        #  
        print(f"{' ':<20} {'':>10} {'':>10}")
        print("-" * 40)
        print(f"{' ':<20} {vector_coverage:>10.2%} {vector_diversity:>10.2%}")
        print(f"{' ':<20} {hybrid_coverage:>10.2%} {hybrid_diversity:>10.2%}")
        print(f"{'  ':<20} {multi_coverage:>10.2%} {multi_diversity:>10.2%}")
        print()
        
        #  
        best_method = max(
            [
                (' ', vector_coverage + vector_diversity),
                (' ', hybrid_coverage + hybrid_diversity),
                ('  ', multi_coverage + multi_diversity)
            ],
            key=lambda x: x[1]
        )
        print(f"      : {best_method[0]}")
    
    def run_quick_test(self, query: str):
        """  ( )"""
        print("=" * 80)
        print(" ")
        print("=" * 80)
        print(f": {query}\n")
        
        #  
        results = self.retriever.hybrid_search(query, top_k=3)
        
        print(f"  : {len(results)}\n")
        for i, result in enumerate(results, 1):
            print(f"[{i}] {result.doc_title} ({result.doc_type})")
            print(f"    : {result.similarity:.4f}")
            print(f"    : {result.content[:150]}...")
            print()
        
        # LLM   
        print("\n--- LLM   ---")
        formatted = self.retriever.format_results_for_llm(results)
        print(formatted[:500] + "...\n")


def main():
    """  """
    load_dotenv()
    
    #  
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': os.getenv('DB_PORT', '5432'),
        'database': os.getenv('DB_NAME', 'ddoksori'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres')
    }
    
    #  API URL
    embed_api_url = os.getenv('EMBED_API_URL', 'http://localhost:8001/embed')
    
    # RAG Retriever 
    retriever = RAGRetriever(db_config, embed_api_url)
    retriever.connect()
    
    try:
        #  
        tester = RAGTester(retriever)
        
        #   
        print("=" * 80)
        print("  - RAG   v2")
        print("=" * 80)
        print("\n  :")
        print("1.   (6 )")
        print("2.   ( )")
        print()
        
        choice = input(" (1  2): ").strip()
        
        if choice == '1':
            tester.run_all_tests()
        elif choice == '2':
            query = input("\n  : ").strip()
            if query:
                tester.run_quick_test(query)
            else:
                print("  .")
        else:
            print(" .")
        
        print("\n" + "=" * 80)
        print(" !")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n  : {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        retriever.close()


if __name__ == "__main__":
    main()
