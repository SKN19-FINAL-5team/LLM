"""
RAG   
Vector DB   LLM    .
"""

import os
import sys
from dotenv import load_dotenv

#   backend  Python  
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'backend'))

from app.rag import VectorRetriever, RAGGenerator

#   
load_dotenv()


def test_retriever():
    """Vector DB   """
    print("=" * 60)
    print("1. Vector DB   ")
    print("=" * 60)
    
    # DB 
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'database': os.getenv('DB_NAME', 'ddoksori'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres')
    }
    
    # Retriever 
    retriever = VectorRetriever(db_config)
    
    #  
    test_queries = [
        "       ?",
        "   .",
        "      ?"
    ]
    
    for idx, query in enumerate(test_queries, 1):
        print(f"\n[  {idx}]")
        print(f": {query}")
        print("-" * 60)
        
        try:
            #  
            chunks = retriever.search(query=query, top_k=3)
            
            print(f" : {len(chunks)}  \n")
            
            for i, chunk in enumerate(chunks, 1):
                print(f"[ {i}]")
                print(f"  : {chunk.get('case_no', 'N/A')}")
                print(f"  : {chunk.get('agency', 'N/A')}")
                print(f"   : {chunk.get('chunk_type', 'N/A')}")
                print(f"  : {chunk.get('similarity', 0):.4f}")
                print(f"   : {chunk.get('text_len', 0)}")
                print(f"   : {chunk.get('text', '')[:100]}...")
                print()
            
        except Exception as e:
            print(f"  : {str(e)}")
    
    retriever.close()
    print("\n Vector DB   \n")


def test_generator():
    """LLM    """
    print("=" * 60)
    print("2. LLM    ")
    print("=" * 60)
    
    # OpenAI API  
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key or api_key == 'your_openai_api_key_here':
        print("  OPENAI_API_KEY  .")
        print("   .env   API       .")
        print("      test_retriever() .\n")
        return
    
    # DB 
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'database': os.getenv('DB_NAME', 'ddoksori'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres')
    }
    
    # RAG  
    retriever = VectorRetriever(db_config)
    generator = RAGGenerator()
    
    #  
    query = "       ?"
    
    print(f"\n[ ]")
    print(f"{query}")
    print("-" * 60)
    
    try:
        # 1. 
        print("\n[1] Vector DB    ...")
        chunks = retriever.search(query=query, top_k=5)
        print(f" {len(chunks)}   ")
        
        # 2.  
        print("\n[2] LLM   ...")
        result = generator.generate_answer(query=query, chunks=chunks)
        
        # 3.  
        print("\n[ ]")
        print("-" * 60)
        print(result['answer'])
        print("-" * 60)
        
        print(f"\n[]")
        print(f"  : {result['model']}")
        print(f"    : {result['chunks_used']}")
        if 'usage' in result:
            print(f"   :")
            print(f"    - : {result['usage']['prompt_tokens']}")
            print(f"    - : {result['usage']['completion_tokens']}")
            print(f"    - : {result['usage']['total_tokens']}")
        
    except Exception as e:
        print(f"  : {str(e)}")
    
    retriever.close()
    print("\n LLM    \n")


def test_full_pipeline():
    """ RAG  """
    print("=" * 60)
    print("3.  RAG  ")
    print("=" * 60)
    
    # OpenAI API  
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key or api_key == 'your_openai_api_key_here':
        print("  OPENAI_API_KEY  .")
        print("   .env   API       .\n")
        return
    
    # DB 
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'database': os.getenv('DB_NAME', 'ddoksori'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres')
    }
    
    # RAG  
    retriever = VectorRetriever(db_config)
    generator = RAGGenerator()
    
    #   
    test_cases = [
        {
            "query": "      ?",
            "chunk_types": ["decision", "judgment"]
        },
        {
            "query": "   .",
            "agencies": ["kca", "ecmc"]
        }
    ]
    
    for idx, test_case in enumerate(test_cases, 1):
        print(f"\n[  {idx}]")
        print(f": {test_case['query']}")
        if 'chunk_types' in test_case:
            print(f"  : {test_case['chunk_types']}")
        if 'agencies' in test_case:
            print(f" : {test_case['agencies']}")
        print("-" * 60)
        
        try:
            # 
            chunks = retriever.search(
                query=test_case['query'],
                top_k=3,
                chunk_types=test_case.get('chunk_types'),
                agencies=test_case.get('agencies')
            )
            
            #  
            result = generator.generate_answer(
                query=test_case['query'],
                chunks=chunks
            )
            
            #  
            print(f"\n[]")
            print(result['answer'])
            print(f"\n( : {result['chunks_used']})")
            print()
            
        except Exception as e:
            print(f"  : {str(e)}\n")
    
    retriever.close()
    print("    \n")


def main():
    """  """
    print("\n" + "=" * 60)
    print("RAG   ")
    print("=" * 60 + "\n")
    
    # 1. Vector DB   (API  )
    test_retriever()
    
    # 2. LLM    (API  )
    test_generator()
    
    # 3.    (API  )
    test_full_pipeline()
    
    print("=" * 60)
    print("  !")
    print("=" * 60)


if __name__ == "__main__":
    main()
