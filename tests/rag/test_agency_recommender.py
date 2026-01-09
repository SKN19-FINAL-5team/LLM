"""
    
      
"""

import sys
import os
from pathlib import Path

#   backend  Python  
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'backend'))

from app.rag.agency_recommender import AgencyRecommender


def print_section(title: str):
    """  """
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def test_rule_based_scoring():
    """    """
    print_section("1.     ")
    
    recommender = AgencyRecommender()
    
    test_cases = [
        {
            'query': '      ',
            'expected_top': 'ecmc',
            'description': ' +  → ECMC'
        },
        {
            'query': '    ',
            'expected_top': 'kcdrc',
            'description': '  → KCDRC'
        },
        {
            'query': '   ',
            'expected_top': 'kca',
            'description': '  → KCA'
        },
        {
            'query': '   ',
            'expected_top': 'kca',
            'description': '  → KCA'
        }
    ]
    
    for idx, test in enumerate(test_cases, 1):
        print(f"  {idx}: {test['description']}")
        print(f": {test['query']}")
        
        scores = recommender.calculate_rule_scores(test['query'])
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        print(f":")
        for agency, score in sorted_scores:
            agency_name = recommender.AGENCIES[agency]['name']
            print(f"  - {agency_name} ({agency}): {score:.4f}")
        
        top_agency = sorted_scores[0][0]
        is_correct = top_agency == test['expected_top']
        status = " " if is_correct else f"  (: {test['expected_top']})"
        print(f": {status}\n")


def test_stat_based_scoring():
    """      """
    print_section("2.      ")
    
    recommender = AgencyRecommender()
    
    #    (KCA   )
    mock_results = [
        {'agency': 'kca', 'similarity': 0.9},
        {'agency': 'kca', 'similarity': 0.85},
        {'agency': 'ecmc', 'similarity': 0.8},
        {'agency': 'kca', 'similarity': 0.75},
        {'agency': 'kca', 'similarity': 0.7},
    ]
    
    print("  :")
    for idx, result in enumerate(mock_results, 1):
        print(f"  {idx}. {result['agency']} (: {result['similarity']:.2f})")
    
    scores = recommender.calculate_stat_scores(mock_results)
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    
    print(f"\n :")
    for agency, score in sorted_scores:
        agency_name = recommender.AGENCIES[agency]['name']
        print(f"  - {agency_name} ({agency}): {score:.4f}")
    
    print(f"\n KCA   : {sorted_scores[0][0] == 'kca'}")


def test_combined_recommendation():
    """ +    """
    print_section("3.    ( 70% +  30%)")
    
    recommender = AgencyRecommender(rule_weight=0.7, stat_weight=0.3)
    
    # :    ( ECMC)
    #    KCA  
    query = "   "
    
    mock_results = [
        {'agency': 'kca', 'similarity': 0.9},
        {'agency': 'kca', 'similarity': 0.85},
        {'agency': 'kca', 'similarity': 0.8},
        {'agency': 'ecmc', 'similarity': 0.75},
    ]
    
    print(f": {query}")
    print("\n :")
    for idx, result in enumerate(mock_results, 1):
        print(f"  {idx}. {result['agency']} (: {result['similarity']:.2f})")
    
    recommendations = recommender.recommend(query, mock_results, top_n=3)
    
    print("\n :")
    for idx, (agency_code, final_score, info) in enumerate(recommendations, 1):
        print(f"{idx}. {info['name']} ({agency_code})")
        print(f"    : {final_score:.4f}")
        print(f"   -  : {info['rule_score']:.4f}")
        print(f"   -  : {info['stat_score']:.4f}")
        print()


def test_explain_recommendation():
    """   """
    print_section("4.    ")
    
    recommender = AgencyRecommender()
    
    query = "     "
    
    mock_results = [
        {'agency': 'kcdrc', 'similarity': 0.9, 'case_no': 'KCDRC-2023-001'},
        {'agency': 'kcdrc', 'similarity': 0.85, 'case_no': 'KCDRC-2023-002'},
        {'agency': 'ecmc', 'similarity': 0.7, 'case_no': 'ECMC-2023-001'},
    ]
    
    print(f": {query}\n")
    
    explanation = recommender.explain_recommendation(query, mock_results)
    
    print("  :")
    for rec in explanation['recommendations']:
        print(f"\n{rec['rank']}: {rec['agency_name']}")
        print(f"  : {rec['description']}")
        print(f"  : {rec['final_score']:.4f} (: {rec['rule_score']:.4f}, : {rec['stat_score']:.4f})")
    
    print("\n  :")
    for agency, count in explanation['search_results_distribution'].items():
        print(f"  - {agency}: {count}")


def test_format_recommendation_text():
    """    """
    print_section("5.     ")
    
    recommender = AgencyRecommender()
    
    query = "G     "
    
    mock_results = [
        {'agency': 'ecmc', 'similarity': 0.9},
        {'agency': 'ecmc', 'similarity': 0.85},
        {'agency': 'kca', 'similarity': 0.7},
    ]
    
    print(f": {query}\n")
    
    formatted_text = recommender.format_recommendation_text(query, mock_results)
    print("  :")
    print("-" * 80)
    print(formatted_text)
    print("-" * 80)


def test_edge_cases():
    """  """
    print_section("6.   ")
    
    recommender = AgencyRecommender()
    
    # 1.    
    print(" 1:   ")
    query = " "
    recommendations = recommender.recommend(query, None, top_n=1)
    print(f": {query}")
    print(f" : {recommendations[0][0]} (: {recommendations[0][1]:.4f})")
    print()
    
    # 2.     
    print(" 2:   ")
    query = " "
    scores = recommender.calculate_rule_scores(query)
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    print(f": {query}")
    print(f"  : {sorted_scores[0][0]} (: {sorted_scores[0][1]:.4f})")
    print(f" KCA  : {sorted_scores[0][0] == 'kca'}")
    print()
    
    # 3.    
    print(" 3:   ")
    query = " "
    recommendations = recommender.recommend(query, [], top_n=1)
    print(f": {query}")
    print(f" : {recommendations[0][0]} (: {recommendations[0][1]:.4f})")


def test_real_world_scenarios():
    """  """
    print_section("7.    ")
    
    recommender = AgencyRecommender()
    
    scenarios = [
        {
            'query': '     ',
            'description': '  '
        },
        {
            'query': '     ',
            'description': '  '
        },
        {
            'query': '     ',
            'description': '   '
        },
        {
            'query': '11      ',
            'description': '   '
        },
        {
            'query': '     ',
            'description': '  '
        }
    ]
    
    for idx, scenario in enumerate(scenarios, 1):
        print(f"\n {idx}: {scenario['description']}")
        print(f": {scenario['query']}")
        
        recommendations = recommender.recommend(scenario['query'], None, top_n=2)
        
        print(" :")
        for rank, (agency_code, score, info) in enumerate(recommendations, 1):
            print(f"  {rank}: {info['name']} (: {score:.4f})")
        print()


def main():
    """  """
    print("\n" + "="*80)
    print("      ")
    print("="*80)
    
    try:
        test_rule_based_scoring()
        test_stat_based_scoring()
        test_combined_recommendation()
        test_explain_recommendation()
        test_format_recommendation_text()
        test_edge_cases()
        test_real_world_scenarios()
        
        print("\n" + "="*80)
        print("     !")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\n    : {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
