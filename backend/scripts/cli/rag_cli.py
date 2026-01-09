#!/usr/bin/env python3
"""
RAG CLI Interface
 CLI  ,     
LLM       CLI 
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

#   
backend_dir = Path(__file__).parent.parent.parent
project_root = backend_dir.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_dir))

from app.rag.multi_method_retriever import MultiMethodRetriever
from app.rag.generator import RAGGenerator
from scripts.cli.golden_set_loader import GoldenSetLoader

#   
load_dotenv()


def format_output(answer: str, metadata: dict) -> str:
    """
       
    
    Args:
        answer: LLM  
        metadata:  (,   )
    
    Returns:
         
    """
    output = []
    output.append("\n" + "=" * 80)
    output.append("")
    output.append("=" * 80)
    output.append(answer)
    output.append("\n" + "-" * 80)
    output.append("")
    output.append("-" * 80)
    output.append(f": {metadata.get('model', 'N/A')}")
    output.append(f"  : {', '.join(metadata.get('methods_used', []))}")
    output.append(f"   : {metadata.get('total_results', 0)}")
    
    if 'usage' in metadata:
        usage = metadata['usage']
        output.append(f" :")
        output.append(f"  - : {usage.get('prompt_tokens', 0)}")
        output.append(f"  - : {usage.get('completion_tokens', 0)}")
        output.append(f"  - : {usage.get('total_tokens', 0)}")
    
    output.append("=" * 80)
    
    return "\n".join(output)


def run_query(
    query: str,
    db_config: dict,
    top_k: int = 10,
    methods: Optional[list] = None,
    model: str = "gpt-4o-mini"
) -> dict:
    """
      
    
    Args:
        query:  
        db_config:  
        top_k:       
        methods:     (None  )
        model:  LLM 
    
    Returns:
         
    """
    print(f"\n{'='*80}")
    print(f": {query}")
    print(f"{'='*80}\n")
    
    # 1. MultiMethodRetriever 
    print("    ...")
    retriever = MultiMethodRetriever(db_config)
    
    # 2.    
    print(f"\n   ... (top_k={top_k})")
    method_results = retriever.search_all_methods(
        query=query,
        top_k=top_k,
        methods=methods
    )
    
    #   
    print("\n  :")
    for method_name, method_data in method_results.get('methods', {}).items():
        if method_data.get('success', False):
            count = method_data.get('count', 0)
            elapsed = method_data.get('elapsed_time', 0)
            print(f"   {method_name.upper()}: {count}  ({elapsed:.3f})")
        else:
            error = method_data.get('error', 'Unknown error')
            print(f"   {method_name.upper()}:  - {error}")
    
    # 3. LLM  
    print("\n LLM   ...")
    generator = RAGGenerator(model=model)
    
    result = generator.generate_comparative_answer(
        query=query,
        method_results=method_results
    )
    
    # 4.  
    output = format_output(result['answer'], result)
    print(output)
    
    #  
    retriever.close()
    
    return result


def main():
    """ """
    parser = argparse.ArgumentParser(
        description='RAG CLI -     LLM  ',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
 :
  #   
  python rag_cli.py --query "   ?"
  
  # Golden set 
  python rag_cli.py --golden-set
  
  #    
  python rag_cli.py --query "" --methods cosine hybrid
  
  # Top-K 
  python rag_cli.py --query "" --top-k 5
        """
    )
    
    parser.add_argument(
        '--query', '-q',
        type=str,
        help='  ( )'
    )
    
    parser.add_argument(
        '--golden-set', '-g',
        action='store_true',
        help='Golden set  '
    )
    
    parser.add_argument(
        '--top-k', '-k',
        type=int,
        default=10,
        help='       (: 10)'
    )
    
    parser.add_argument(
        '--methods', '-m',
        nargs='+',
        choices=['cosine', 'bm25', 'splade', 'hybrid'],
        help='    (:  )'
    )
    
    parser.add_argument(
        '--model',
        type=str,
        default='gpt-4o-mini',
        help=' LLM  (: gpt-4o-mini)'
    )
    
    parser.add_argument(
        '--golden-set-path',
        type=str,
        help='Golden set JSON   (: backend/evaluation/datasets/gold_real_consumer_cases.json)'
    )
    
    args = parser.parse_args()
    
    # OpenAI API  
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key or api_key == 'your_openai_api_key_here':
        print(" OPENAI_API_KEY  .")
        print("   .env   API  .")
        sys.exit(1)
    
    # DB 
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'database': os.getenv('DB_NAME', 'ddoksori'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres')
    }
    
    #  
    query = None
    
    if args.golden_set:
        # Golden set 
        golden_set_path = Path(args.golden_set_path) if args.golden_set_path else None
        loader = GoldenSetLoader(golden_set_path)
        
        selected = loader.select_query_interactive()
        
        if selected is None:
            print("  .")
            sys.exit(0)
        
        if isinstance(selected, dict) and selected.get('all'):
            #    ( )
            queries = selected['queries']
            print(f"\n {len(queries)}  .\n")
            
            for idx, test_case in enumerate(queries, 1):
                query = test_case.get('query')
                query_id = test_case.get('query_id', f'Q{idx:03d}')
                
                print(f"\n{'#'*80}")
                print(f"#  {idx}/{len(queries)}: {query_id}")
                print(f"{'#'*80}")
                
                try:
                    run_query(
                        query=query,
                        db_config=db_config,
                        top_k=args.top_k,
                        methods=args.methods,
                        model=args.model
                    )
                except Exception as e:
                    print(f"\n  : {e}")
                    continue
        else:
            #   
            query = selected.get('query')
            if not query:
                print("    .")
                sys.exit(1)
    
    elif args.query:
        #   
        query = args.query
    
    else:
        #  :  
        print("\nRAG CLI -   (: Ctrl+C  'quit')")
        print("-" * 80)
        
        try:
            query = input("\n: ").strip()
            
            if query.lower() in ['quit', 'exit', 'q']:
                print(".")
                sys.exit(0)
            
            if not query:
                print("  .")
                sys.exit(1)
        
        except KeyboardInterrupt:
            print("\n\n.")
            sys.exit(0)
    
    #  
    try:
        run_query(
            query=query,
            db_config=db_config,
            top_k=args.top_k,
            methods=args.methods,
            model=args.model
        )
    except Exception as e:
        print(f"\n  : {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
