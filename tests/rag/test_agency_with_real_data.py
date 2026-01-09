"""
      
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

#   backend  Python  
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'backend'))

#   
load_dotenv(project_root / '.env')

from app.rag.retriever import VectorRetriever
from app.rag.agency_recommender import AgencyRecommender


def print_section(title: str):
    """  """
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def test_with_real_search():
    """      """
    print_section("      ")
    
    # DB 
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'database': os.getenv('DB_NAME', 'ddoksori_db'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres')
    }
    
    # Retriever Recommender 
    retriever = VectorRetriever(db_config)
    recommender = AgencyRecommender()
    
    #  
    test_queries = [
        "    .   ?",
        "    ",
        "     ",
        "     ",
        "    "
    ]
    
    try:
        for idx, query in enumerate(test_queries, 1):
            print(f"\n{''*80}")
            print(f" {idx}: {query}")
            print(f"{''*80}")
            
            # 1.   
            print("\n1⃣   ...")
            search_results = retriever.search(query, top_k=5)
            
            if not search_results:
                print("      ")
                continue
            
            print(f"    {len(search_results)}   ")
            
            #   
            print("\n     :")
            for i, chunk in enumerate(search_results[:3], 1):
                print(f"   {i}. [{chunk['agency'].upper()}] {chunk['case_no']} "
                      f"(: {chunk['similarity']:.3f})")
                print(f"      {chunk['text'][:60]}...")
            
            # 2.  
            print("\n2⃣   ...")
            recommendations = recommender.recommend(query, search_results, top_n=2)
            
            print("\n    :")
            for rank, (agency_code, score, info) in enumerate(recommendations, 1):
                print(f"\n   {rank}: {info['name']} ({agency_code.upper()})")
                print(f"     : {score:.4f}")
                print(f"     : {info['rule_score']:.4f}")
                print(f"     : {info['stat_score']:.4f}")
                print(f"    : {info['description']}")
            
            # 3.    
            print("\n3⃣    :")
            print("   " + ""*76)
            formatted = recommender.format_recommendation_text(query, search_results)
            for line in formatted.split('\n'):
                print(f"   {line}")
            print("   " + ""*76)
        
        print(f"\n{'='*80}")
        print("      !")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\n  : {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        retriever.close()
    
    return 0


def test_agency_distribution():
    """   """
    print_section("   ")
    
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'database': os.getenv('DB_NAME', 'ddoksori_db'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres')
    }
    
    retriever = VectorRetriever(db_config)
    
    try:
        retriever.connect_db()
        
        #    
        query = """
            SELECT 
                agency,
                COUNT(DISTINCT case_uid) as case_count,
                COUNT(*) as chunk_count
            FROM cases c
            JOIN chunks ch ON c.case_uid = ch.case_uid
            WHERE ch.drop = FALSE
            GROUP BY agency
            ORDER BY case_count DESC
        """
        
        with retriever.conn.cursor() as cur:
            cur.execute(query)
            results = cur.fetchall()
        
        print("  :")
        print(f"{'':<20} {' ':<15} {' ':<15}")
        print("" * 50)
        
        total_cases = 0
        total_chunks = 0
        
        for agency, case_count, chunk_count in results:
            agency_name = {
                'kca': '',
                'ecmc': '',
                'kcdrc': ''
            }.get(agency, agency)
            
            print(f"{agency_name:<20} {case_count:<15,} {chunk_count:<15,}")
            total_cases += case_count
            total_chunks += chunk_count
        
        print("" * 50)
        print(f"{'':<20} {total_cases:<15,} {total_chunks:<15,}")
        
    except Exception as e:
        print(f"  : {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        retriever.close()
    
    return 0


def main():
    """ """
    print("\n" + "="*80)
    print("        ")
    print("="*80)
    
    # 1.   
    result = test_agency_distribution()
    if result != 0:
        return result
    
    # 2.  
    result = test_with_real_search()
    if result != 0:
        return result
    
    return 0


if __name__ == "__main__":
    exit(main())
