"""
    
"""

import sys
from pathlib import Path

#    
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.rag.agency_recommender import AgencyRecommender


def example_basic():
    """  """
    print("="*80)
    print(" 1:    ( )")
    print("="*80 + "\n")
    
    recommender = AgencyRecommender()
    
    queries = [
        "   ",
        "    ",
        "    "
    ]
    
    for query in queries:
        print(f": {query}")
        recommendations = recommender.recommend(query, None, top_n=2)
        
        print(" :")
        for rank, (code, score, info) in enumerate(recommendations, 1):
            print(f"  {rank}: {info['name']} (: {score:.4f})")
        print()


def example_with_mock_search():
    """    """
    print("="*80)
    print(" 2:      ( + )")
    print("="*80 + "\n")
    
    recommender = AgencyRecommender()
    
    #   
    query = "G     "
    
    mock_search_results = [
        {
            'agency': 'ecmc',
            'similarity': 0.92,
            'case_no': 'ECMC-2023-001',
            'text': '       ...'
        },
        {
            'agency': 'ecmc',
            'similarity': 0.88,
            'case_no': 'ECMC-2023-002',
            'text': '      ...'
        },
        {
            'agency': 'kca',
            'similarity': 0.75,
            'case_no': 'KCA-2023-001',
            'text': '     ...'
        },
    ]
    
    print(f": {query}")
    print(f"\n  {len(mock_search_results)}:")
    for i, result in enumerate(mock_search_results, 1):
        print(f"  {i}. [{result['agency'].upper()}] {result['case_no']} "
              f"(: {result['similarity']:.2f})")
    
    print("\n  :")
    recommendations = recommender.recommend(query, mock_search_results, top_n=2)
    
    for rank, (code, score, info) in enumerate(recommendations, 1):
        print(f"\n{rank}: {info['name']}")
        print(f"  -  : {score:.4f}")
        print(f"  -  : {info['rule_score']:.4f} ( )")
        print(f"  -  : {info['stat_score']:.4f} (  )")
        print(f"  - : {info['description']}")


def example_detailed_explanation():
    """   """
    print("\n" + "="*80)
    print(" 3:    ")
    print("="*80 + "\n")
    
    recommender = AgencyRecommender()
    
    query = "11    "
    
    mock_search_results = [
        {'agency': 'kcdrc', 'similarity': 0.9, 'case_no': 'KCDRC-2023-001'},
        {'agency': 'kcdrc', 'similarity': 0.85, 'case_no': 'KCDRC-2023-002'},
        {'agency': 'ecmc', 'similarity': 0.7, 'case_no': 'ECMC-2023-001'},
    ]
    
    print(f": {query}\n")
    
    explanation = recommender.explain_recommendation(query, mock_search_results)
    
    print("   :")
    print("-" * 80)
    
    for rec in explanation['recommendations']:
        print(f"\n{rec['rank']}: {rec['agency_name']} ({rec['agency_code'].upper()})")
        print(f"  : {rec['full_name']}")
        print(f"  : {rec['description']}")
        print(f"   : {rec['final_score']:.4f}")
        print(f"      : {rec['rule_score']:.4f}")
        print(f"      : {rec['stat_score']:.4f}")
    
    print("\n    :")
    for agency, count in explanation['search_results_distribution'].items():
        print(f"  - {agency.upper()}: {count}")
    
    print("\n   :")
    print(f"  -  : {explanation['weights']['rule_weight']*100:.0f}%")
    print(f"  -  : {explanation['weights']['stat_weight']*100:.0f}%")


def example_formatted_text():
    """    """
    print("\n" + "="*80)
    print(" 4:    ")
    print("="*80 + "\n")
    
    recommender = AgencyRecommender()
    
    scenarios = [
        {
            'query': '   ',
            'results': [
                {'agency': 'ecmc', 'similarity': 0.9},
                {'agency': 'ecmc', 'similarity': 0.85},
                {'agency': 'kca', 'similarity': 0.7},
            ]
        },
        {
            'query': '    ',
            'results': [
                {'agency': 'kcdrc', 'similarity': 0.92},
                {'agency': 'kcdrc', 'similarity': 0.88},
            ]
        }
    ]
    
    for scenario in scenarios:
        print(f": {scenario['query']}")
        print("-" * 80)
        
        formatted = recommender.format_recommendation_text(
            scenario['query'], 
            scenario['results']
        )
        print(formatted)
        print("\n")


def example_custom_weights():
    """   """
    print("="*80)
    print(" 5:  ")
    print("="*80 + "\n")
    
    query = "   "
    
    mock_results = [
        {'agency': 'kca', 'similarity': 0.9},
        {'agency': 'kca', 'similarity': 0.85},
        {'agency': 'ecmc', 'similarity': 0.7},
    ]
    
    print(f": {query}\n")
    
    #    
    weight_configs = [
        (0.7, 0.3, " ( 70% +  30%)"),
        (0.9, 0.1, "  ( 90% +  10%)"),
        (0.5, 0.5, " ( 50% +  50%)"),
        (0.3, 0.7, "  ( 30% +  70%)"),
    ]
    
    for rule_weight, stat_weight, description in weight_configs:
        recommender = AgencyRecommender(
            rule_weight=rule_weight, 
            stat_weight=stat_weight
        )
        
        recommendations = recommender.recommend(query, mock_results, top_n=1)
        top_agency, top_score, top_info = recommendations[0]
        
        print(f"{description}")
        print(f"  → : {top_info['name']} (: {top_score:.4f})")


def main():
    """  """
    example_basic()
    example_with_mock_search()
    example_detailed_explanation()
    example_formatted_text()
    example_custom_weights()
    
    print("\n" + "="*80)
    print("    !")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
