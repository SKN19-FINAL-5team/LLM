"""
/    SPLADE    
"""

import os
import sys
import json
import numpy as np
from typing import Dict, List, Optional
from pathlib import Path
from dotenv import load_dotenv

#    
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

#   
env_file = backend_dir / '.env'
if env_file.exists():
    load_dotenv(env_file)
else:
    root_env = backend_dir.parent / '.env'
    if root_env.exists():
        load_dotenv(root_env)
    else:
        load_dotenv()

# SPLADE  import
try:
    from scripts.splade.test_splade_naver import NaverSPLADERetriever
    from scripts.splade.test_splade_optimized import OptimizedSPLADEDBRetriever
except ImportError as e:
    print(f"  SPLADE    : {e}")
    sys.exit(1)


class SPLADEDomainOptimizer:
    """SPLADE   """
    
    def __init__(self, db_config: Dict):
        """
        Args:
            db_config:   
        """
        self.db_config = db_config
        self.splade_retriever = None
        
        #    
        self.law_patterns = {
            'article_number': r'\s*\d+\s*',  #  
            'paragraph_number': r'\s*\d+\s*',  #  
            'law_names': [
                '', '', '', '', 
                '', ''
            ]
        }
        
        #    
        self.criteria_patterns = {
            'item_names': [
                '', '', '', 'TV', '', 
                '', '', '', '', '',
                '', '', '', '', '',
                '', '', '', '', ''
            ],
            'dispute_types': [
                '', '', '', '', '', '',
                '', '', '', '', '', ''
            ]
        }
    
    def boost_article_tokens(self, sparse_vec: np.ndarray, query: str) -> np.ndarray:
        """
            
        
        Args:
            sparse_vec: Sparse vector
            query:  
        
        Returns:
              sparse vector
        """
        import re
        
        #   
        article_match = re.search(self.law_patterns['article_number'], query)
        if article_match:
            article_text = article_match.group(0)
            #      
            #      ID  
            #   
            boost_factor = 1.5  # 50%  
            # TODO:   ID   
        
        return sparse_vec
    
    def boost_item_tokens(self, sparse_vec: np.ndarray, query: str) -> np.ndarray:
        """
           
        
        Args:
            sparse_vec: Sparse vector
            query:  
        
        Returns:
              sparse vector
        """
        #  
        for item in self.criteria_patterns['item_names']:
            if item in query:
                boost_factor = 1.3  # 30%  
                # TODO:   ID   
                break
        
        return sparse_vec
    
    def optimize_law_search(
        self,
        retriever: OptimizedSPLADEDBRetriever,
        query: str,
        top_k: int = 10
    ) -> List[Dict]:
        """
          
        
        :
        1.     
        2.  +   
        3.    
        
        Args:
            retriever:  SPLADE Retriever
            query:  
            top_k:    
        
        Returns:
              
        """
        #   
        results = retriever.search_law_splade_optimized(query, top_k=top_k * 2)
        
        #        
        import re
        article_match = re.search(self.law_patterns['article_number'], query)
        if article_match:
            article_text = article_match.group(0)
            
            #      
            prioritized = []
            others = []
            
            for r in results:
                if article_text in r.get('content', ''):
                    prioritized.append(r)
                else:
                    others.append(r)
            
            results = prioritized + others
        
        #    
        for law_name in self.law_patterns['law_names']:
            if law_name in query:
                #    
                law_results = [r for r in results if law_name in r.get('law_name', '') or law_name in r.get('content', '')]
                other_results = [r for r in results if r not in law_results]
                results = law_results + other_results
                break
        
        return results[:top_k]
    
    def optimize_criteria_search(
        self,
        retriever: OptimizedSPLADEDBRetriever,
        query: str,
        top_k: int = 10
    ) -> List[Dict]:
        """
          
        
        :
        1.    
        2.    
        3.   
        
        Args:
            retriever:  SPLADE Retriever
            query:  
            top_k:    
        
        Returns:
              
        """
        #   
        results = retriever.search_criteria_splade_optimized(query, top_k=top_k * 2)
        
        #     
        for item in self.criteria_patterns['item_names']:
            if item in query:
                #    
                item_results = [
                    r for r in results 
                    if item in r.get('item', '') or item in r.get('content', '')
                ]
                other_results = [r for r in results if r not in item_results]
                results = item_results + other_results
                break
        
        #    
        dispute_keywords = []
        for dispute_type in self.criteria_patterns['dispute_types']:
            if dispute_type in query:
                dispute_keywords.append(dispute_type)
        
        if dispute_keywords:
            #     
            dispute_results = [
                r for r in results
                if any(keyword in r.get('content', '') for keyword in dispute_keywords)
            ]
            other_results = [r for r in results if r not in dispute_results]
            results = dispute_results + other_results
        
        return results[:top_k]
    
    def create_hybrid_search(
        self,
        dense_retriever,
        splade_retriever: OptimizedSPLADEDBRetriever,
        query: str,
        doc_type: str,
        top_k: int = 10,
        splade_weight: float = 0.7,
        dense_weight: float = 0.3
    ) -> List[Dict]:
        """
         : SPLADE + Dense Vector
        
        Args:
            dense_retriever: Dense Vector Retriever
            splade_retriever: SPLADE Retriever
            query:  
            doc_type:  
            top_k:    
            splade_weight: SPLADE  
            dense_weight: Dense  
        
        Returns:
              
        """
        # SPLADE 
        if doc_type == 'law':
            splade_results = self.optimize_law_search(splade_retriever, query, top_k=top_k * 2)
        elif doc_type and doc_type.startswith('criteria'):
            splade_results = self.optimize_criteria_search(splade_retriever, query, top_k=top_k * 2)
        else:
            splade_results = []
        
        # Dense 
        try:
            dense_results = dense_retriever.search(query, top_k=top_k * 2, debug=False)
            dense_results_list = dense_results.get('results', [])
        except Exception as e:
            print(f"    Dense  : {e}")
            dense_results_list = []
        
        #     
        combined_results = {}
        
        # SPLADE  
        for r in splade_results:
            chunk_id = r.get('chunk_id')
            if chunk_id:
                combined_results[chunk_id] = {
                    'chunk_id': chunk_id,
                    'doc_id': r.get('doc_id'),
                    'content': r.get('content'),
                    'splade_score': r.get('splade_score', 0.0),
                    'dense_score': 0.0,
                    'final_score': 0.0
                }
        
        # Dense  /
        for r in dense_results_list:
            chunk_id = r.get('chunk_id')
            similarity = r.get('similarity', 0.0)
            
            if chunk_id in combined_results:
                combined_results[chunk_id]['dense_score'] = similarity
            else:
                combined_results[chunk_id] = {
                    'chunk_id': chunk_id,
                    'doc_id': r.get('doc_id'),
                    'content': r.get('content'),
                    'splade_score': 0.0,
                    'dense_score': similarity,
                    'final_score': 0.0
                }
        
        #   
        for chunk_id, result in combined_results.items():
            result['final_score'] = (
                result['splade_score'] * splade_weight +
                result['dense_score'] * dense_weight
            )
        
        # 
        sorted_results = sorted(
            combined_results.values(),
            key=lambda x: x['final_score'],
            reverse=True
        )
        
        return sorted_results[:top_k]


def main():
    """ """
    import argparse
    
    parser = argparse.ArgumentParser(description='SPLADE  ')
    parser.add_argument('--test', action='store_true', help=' ')
    parser.add_argument('--query', type=str, help=' ')
    parser.add_argument('--doc-type', type=str, choices=['law', 'criteria'], help=' ')
    
    args = parser.parse_args()
    
    # DB 
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'database': os.getenv('DB_NAME', 'ddoksori'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres')
    }
    
    # Optimizer 
    optimizer = SPLADEDomainOptimizer(db_config)
    
    # Retriever 
    try:
        splade_retriever = OptimizedSPLADEDBRetriever(db_config)
        print(" SPLADE Retriever  ")
    except Exception as e:
        print(f" SPLADE Retriever  : {e}")
        sys.exit(1)
    
    #  
    if args.test and args.query:
        print(f"\n{'='*80}")
        print(f" : {args.query}")
        print(f"{'='*80}")
        
        if args.doc_type == 'law':
            results = optimizer.optimize_law_search(splade_retriever, args.query, top_k=5)
            print(f"\n  : {len(results)}")
            for i, r in enumerate(results[:3], 1):
                print(f"\n{i}. Score: {r.get('splade_score', 0.0):.4f}")
                print(f"   Law: {r.get('law_name', 'N/A')}")
                print(f"   Content: {r.get('content', '')[:100]}...")
        elif args.doc_type == 'criteria':
            results = optimizer.optimize_criteria_search(splade_retriever, args.query, top_k=5)
            print(f"\n  : {len(results)}")
            for i, r in enumerate(results[:3], 1):
                print(f"\n{i}. Score: {r.get('splade_score', 0.0):.4f}")
                print(f"   Item: {r.get('item', 'N/A')}")
                print(f"   Content: {r.get('content', '')[:100]}...")
        else:
            print("  --doc-type  (law  criteria)")
    else:
        print(" SPLADE     ")
        print("\n:")
        print("  python optimize_splade_for_domain.py --test --query ' 750' --doc-type law")
        print("  python optimize_splade_for_domain.py --test --query ' ' --doc-type criteria")
    
    #  
    if splade_retriever.conn:
        splade_retriever.conn.close()


if __name__ == "__main__":
    main()
