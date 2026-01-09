#!/usr/bin/env python3
"""
RAG CLI Dry-run 
 DB/API   import    
"""

import sys
from pathlib import Path

#   
backend_dir = Path(__file__).parent.parent.parent
project_root = backend_dir.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_dir))


def test_imports():
    """  import """
    print("=" * 80)
    print("1.  Import ")
    print("=" * 80)
    
    errors = []
    warnings = []
    
    # MultiMethodRetriever import
    try:
        from app.rag.multi_method_retriever import MultiMethodRetriever
        print(" MultiMethodRetriever import ")
    except ImportError as e:
        if 'psycopg2' in str(e) or 'dotenv' in str(e):
            print(f"  MultiMethodRetriever import  ( ): {e}")
            print("   →      .")
            warnings.append(f"MultiMethodRetriever : {e}")
        else:
            print(f" MultiMethodRetriever import : {e}")
            errors.append(f"MultiMethodRetriever: {e}")
    except Exception as e:
        print(f" MultiMethodRetriever import : {e}")
        errors.append(f"MultiMethodRetriever: {e}")
    
    # RAGGenerator import
    try:
        from app.rag.generator import RAGGenerator
        print(" RAGGenerator import ")
    except ImportError as e:
        if 'psycopg2' in str(e) or 'openai' in str(e) or 'dotenv' in str(e):
            print(f"  RAGGenerator import  ( ): {e}")
            print("   →      .")
            warnings.append(f"RAGGenerator : {e}")
        else:
            print(f" RAGGenerator import : {e}")
            errors.append(f"RAGGenerator: {e}")
    except Exception as e:
        print(f" RAGGenerator import : {e}")
        errors.append(f"RAGGenerator: {e}")
    
    # GoldenSetLoader import
    try:
        from scripts.cli.golden_set_loader import GoldenSetLoader
        print(" GoldenSetLoader import ")
    except Exception as e:
        print(f" GoldenSetLoader import : {e}")
        errors.append(f"GoldenSetLoader: {e}")
    
    # CLI  import (   )
    try:
        import scripts.cli.rag_cli as rag_cli
        print(" rag_cli  import ")
    except ImportError as e:
        if 'dotenv' in str(e) or 'psycopg2' in str(e):
            print(f"  rag_cli  import  ( ): {e}")
            print("   →      .")
            warnings.append(f"rag_cli : {e}")
        else:
            print(f" rag_cli  import : {e}")
            errors.append(f"rag_cli: {e}")
    except Exception as e:
        print(f" rag_cli  import : {e}")
        errors.append(f"rag_cli: {e}")
    
    return errors, warnings


def test_class_initialization():
    """   ( DB  )"""
    print("\n" + "=" * 80)
    print("2.    ")
    print("=" * 80)
    
    errors = []
    warnings = []
    
    # MultiMethodRetriever   
    try:
        from app.rag.multi_method_retriever import MultiMethodRetriever
        
        #   
        required_methods = [
            'search_cosine',
            'search_bm25',
            'search_splade',
            'search_hybrid',
            'search_all_methods',
            'close'
        ]
        
        for method_name in required_methods:
            if hasattr(MultiMethodRetriever, method_name):
                print(f" MultiMethodRetriever.{method_name} ")
            else:
                print(f" MultiMethodRetriever.{method_name} ")
                errors.append(f"MultiMethodRetriever.{method_name} ")
    
    except ImportError as e:
        print(f"  MultiMethodRetriever    ( )")
        warnings.append(f"MultiMethodRetriever  : {e}")
    except Exception as e:
        print(f" MultiMethodRetriever   : {e}")
        errors.append(f"MultiMethodRetriever : {e}")
    
    # RAGGenerator   
    try:
        from app.rag.generator import RAGGenerator
        
        #   
        required_methods = [
            'generate_answer',
            'generate_comparative_answer',
            'format_context',
            'format_multi_method_context'
        ]
        
        for method_name in required_methods:
            if hasattr(RAGGenerator, method_name):
                print(f" RAGGenerator.{method_name} ")
            else:
                print(f" RAGGenerator.{method_name} ")
                errors.append(f"RAGGenerator.{method_name} ")
    
    except ImportError as e:
        print(f"  RAGGenerator    ( )")
        warnings.append(f"RAGGenerator  : {e}")
    except Exception as e:
        print(f" RAGGenerator   : {e}")
        errors.append(f"RAGGenerator : {e}")
    
    # GoldenSetLoader   
    try:
        from scripts.cli.golden_set_loader import GoldenSetLoader
        
        #   
        required_methods = [
            'load',
            'get_all_queries',
            'get_query_by_id',
            'get_query_by_index',
            'display_queries',
            'select_query_interactive',
            'get_dataset_info'
        ]
        
        for method_name in required_methods:
            if hasattr(GoldenSetLoader, method_name):
                print(f" GoldenSetLoader.{method_name} ")
            else:
                print(f" GoldenSetLoader.{method_name} ")
                errors.append(f"GoldenSetLoader.{method_name} ")
    
    except Exception as e:
        print(f" GoldenSetLoader   : {e}")
        errors.append(f"GoldenSetLoader : {e}")
    
    return errors, warnings


def test_golden_set_loader():
    """Golden Set Loader  ( )"""
    print("\n" + "=" * 80)
    print("3. Golden Set Loader ")
    print("=" * 80)
    
    errors = []
    
    try:
        from scripts.cli.golden_set_loader import GoldenSetLoader
        
        loader = GoldenSetLoader()
        
        #   
        if loader.golden_set_path.exists():
            print(f" Golden Set  : {loader.golden_set_path}")
            
            #   (   )
            print(f"    : {loader.golden_set_path.stat().st_size} bytes")
        else:
            print(f"  Golden Set  : {loader.golden_set_path}")
            print("   (    )")
    
    except Exception as e:
        print(f" Golden Set Loader  : {e}")
        errors.append(f"GoldenSetLoader : {e}")
    
    return errors


def test_cli_argument_parsing():
    """CLI   """
    print("\n" + "=" * 80)
    print("4. CLI   ")
    print("=" * 80)
    
    errors = []
    warnings = []
    
    try:
        import argparse
        import scripts.cli.rag_cli as rag_cli
        
        # argparse   
        if hasattr(rag_cli, 'main'):
            print(" rag_cli.main  ")
        else:
            print(" rag_cli.main  ")
            errors.append("rag_cli.main ")
    
    except ImportError as e:
        if 'dotenv' in str(e) or 'psycopg2' in str(e):
            print(f"  CLI     ( )")
            warnings.append(f"CLI  : {e}")
        else:
            print(f" CLI    : {e}")
            errors.append(f"CLI  : {e}")
    except Exception as e:
        print(f" CLI    : {e}")
        errors.append(f"CLI  : {e}")
    
    return errors, warnings


def main():
    """  """
    print("\n" + "=" * 80)
    print("RAG CLI Dry-run  ")
    print("=" * 80 + "\n")
    
    all_errors = []
    all_warnings = []
    
    # 1. Import 
    errors, warnings = test_imports()
    all_errors.extend(errors)
    all_warnings.extend(warnings)
    
    # 2.   
    errors, warnings = test_class_initialization()
    all_errors.extend(errors)
    all_warnings.extend(warnings)
    
    # 3. Golden Set Loader 
    errors = test_golden_set_loader()
    all_errors.extend(errors)
    
    # 4. CLI   
    errors, warnings = test_cli_argument_parsing()
    all_errors.extend(errors)
    all_warnings.extend(warnings)
    
    #  
    print("\n" + "=" * 80)
    print("  ")
    print("=" * 80)
    
    if all_warnings:
        print(f"\n   {len(all_warnings)}  ( ):")
        for warning in all_warnings:
            print(f"  - {warning}")
        print("   →      .")
    
    if all_errors:
        print(f"\n  {len(all_errors)}  :")
        for error in all_errors:
            print(f"  - {error}")
        print("\n        .")
        return 1
    else:
        print("\n  dry-run  !")
        if all_warnings:
            print("   (     )")
        print("      import   .")
        print("      DB  OpenAI API  .")
        return 0


if __name__ == "__main__":
    sys.exit(main())
