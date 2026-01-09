"""
  -    
: 2026-01-05

:
  python scripts/test_similarity_search.py
  python scripts/test_similarity_search.py " "
"""

import psycopg2
import requests
import json
from dotenv import load_dotenv
import os
import sys

#  
load_dotenv()

def get_embedding(text: str, api_url: str) -> list:
    """   """
    try:
        response = requests.post(api_url, json={"text": text}, timeout=10)
        response.raise_for_status()
        return response.json()['embedding']
    except Exception as e:
        print(f"  API : {e}")
        sys.exit(1)


def search_similar_chunks(conn, query_embedding: list, top_k: int = 5):
    """  """
    cur = conn.cursor()
    
    #   
    cur.execute("""
        SELECT 
            c.chunk_id,
            c.doc_id,
            d.doc_type,
            d.title,
            c.chunk_type,
            c.content,
            1 - (c.embedding <=> %s::vector) as similarity
        FROM chunks c
        JOIN documents d ON c.doc_id = d.doc_id
        WHERE c.embedding IS NOT NULL
        ORDER BY c.embedding <=> %s::vector
        LIMIT %s
    """, (query_embedding, query_embedding, top_k))
    
    results = cur.fetchall()
    cur.close()
    
    return results


def main():
    #  
    if len(sys.argv) > 1:
        test_query = " ".join(sys.argv[1:])
    else:
        test_query = "    .    ?"
    
    print("=" * 80)
    print("  -   ")
    print("=" * 80)
    print(f"\n  : {test_query}")
    print("-" * 80)
    
    #  
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5432'),
            database=os.getenv('DB_NAME', 'ddoksori'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', 'postgres')
        )
    except Exception as e:
        print(f"   : {e}")
        sys.exit(1)
    
    #  API URL
    embed_api_url = os.getenv('EMBED_API_URL', 'http://localhost:8001/embed')
    
    # 1.   
    print(f"\n  API  ... ({embed_api_url})")
    query_embedding = get_embedding(test_query, embed_api_url)
    print(f"     (: {len(query_embedding)})")
    
    # 2.  
    print(f"\n    ...")
    results = search_similar_chunks(conn, query_embedding, top_k=5)
    
    if not results:
        print("   .   .")
        conn.close()
        sys.exit(1)
    
    print(f"  {len(results)}   ")
    print("\n" + "=" * 80)
    print(" ")
    print("=" * 80)
    
    for i, row in enumerate(results, 1):
        chunk_id, doc_id, doc_type, doc_title, chunk_type, content, similarity = row
        
        print(f"\n[{i}] : {similarity:.4f} ({similarity*100:.2f}%)")
        print(f"     ID: {chunk_id}")
        print(f"     ID: {doc_id}")
        print(f"     : {doc_type}")
        print(f"     : {doc_title[:80]}{'...' if len(doc_title) > 80 else ''}")
        print(f"     : {chunk_type}")
        print(f"     :")
        
        #  200  
        content_preview = content[:200] + "..." if len(content) > 200 else content
        for line in content_preview.split('\n'):
            if line.strip():
                print(f"      {line.strip()}")
    
    print("\n" + "=" * 80)
    print(" !")
    print("=" * 80)
    
    #    
    print("\n   :")
    print("  python scripts/test_similarity_search.py \"   ?\"")
    print("  python scripts/test_similarity_search.py \"   ?\"")
    print("  python scripts/test_similarity_search.py \" ?\"")
    
    conn.close()


if __name__ == "__main__":
    main()
