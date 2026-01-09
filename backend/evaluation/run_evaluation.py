"""
  - RAG   
: 2026-01-05

:
  python run_evaluation.py --dataset datasets/gold_v1.json --methods vector hybrid multi_source
"""

import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

#    
sys.path.insert(0, str(Path(__file__).parent.parent))

from rag.retriever import RAGRetriever
from evaluation.evaluator import RAGEvaluator


def parse_args():
    """  """
    parser = argparse.ArgumentParser(description="RAG   ")
    
    parser.add_argument(
        "--dataset",
        type=str,
        required=True,
        help="   (: datasets/gold_v1.json)"
    )
    
    parser.add_argument(
        "--methods",
        nargs="+",
        default=["vector", "hybrid", "multi_source"],
        choices=["vector", "hybrid", "multi_source"],
        help="   (: vector hybrid multi_source)"
    )
    
    parser.add_argument(
        "--top-k",
        type=int,
        default=10,
        help="   (: 10)"
    )
    
    parser.add_argument(
        "--output-dir",
        type=str,
        default="evaluation/results",
        help="   (: evaluation/results)"
    )
    
    parser.add_argument(
        "--db-host",
        type=str,
        default=None,
        help="  (:  DB_HOST)"
    )
    
    parser.add_argument(
        "--db-port",
        type=str,
        default=None,
        help="  (:  DB_PORT)"
    )
    
    parser.add_argument(
        "--db-name",
        type=str,
        default=None,
        help="  (:  DB_NAME)"
    )
    
    parser.add_argument(
        "--embed-api-url",
        type=str,
        default=None,
        help=" API URL (:  EMBED_API_URL)"
    )
    
    return parser.parse_args()


def main():
    """  """
    #   
    load_dotenv()
    
    #  
    args = parse_args()
    
    #   
    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        print(f"    : {dataset_path}")
        sys.exit(1)
    
    #  
    db_config = {
        'host': args.db_host or os.getenv('DB_HOST', 'localhost'),
        'port': args.db_port or os.getenv('DB_PORT', '5432'),
        'database': args.db_name or os.getenv('DB_NAME', 'ddoksori'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres')
    }
    
    #  API URL
    embed_api_url = args.embed_api_url or os.getenv('EMBED_API_URL', 'http://localhost:8001/embed')
    
    print("=" * 80)
    print("  - RAG   ")
    print("=" * 80)
    print(f": {dataset_path}")
    print(f" : {', '.join(args.methods)}")
    print(f"Top-K: {args.top_k}")
    print(f" : {args.output_dir}")
    print(f": {db_config['host']}:{db_config['port']}/{db_config['database']}")
    print(f" API: {embed_api_url}")
    print("=" * 80)
    print()
    
    # RAG Retriever 
    print("[1/3] RAG Retriever  ...")
    retriever = RAGRetriever(db_config, embed_api_url)
    retriever.connect()
    print(" RAG Retriever  ")
    
    try:
        # Evaluator 
        print("\n[2/3] Evaluator  ...")
        evaluator = RAGEvaluator(retriever, str(dataset_path))
        evaluator.load_dataset()
        print(" Evaluator  ")
        
        #  
        print("\n[3/3]   ...")
        all_results = evaluator.evaluate_all(
            search_methods=args.methods,
            top_k=args.top_k
        )
        
        #  
        json_path, summary_path = evaluator.save_results(all_results, args.output_dir)
        
        #  
        evaluator.print_summary(all_results)
        
        print("\n" + "=" * 80)
        print(" !")
        print("=" * 80)
        print(f" : {json_path}")
        print(f" : {summary_path}")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n  : {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    finally:
        retriever.close()


if __name__ == "__main__":
    main()
