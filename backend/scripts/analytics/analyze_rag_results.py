"""
RAG    

test_multi_stage_rag.py   
"""

import json
import sys
from pathlib import Path
from typing import List, Dict


def load_results(file_path: str = "test_results.json") -> List[Dict]:
    """  JSON  """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"    : {file_path}")
        print(" test_multi_stage_rag.py .")
        sys.exit(1)


def print_separator(title: str = None):
    """ """
    if title:
        print(f"\n{'='*80}")
        print(f"  {title}")
        print(f"{'='*80}\n")
    else:
        print(f"{'='*80}\n")


def analyze_search_distribution(results: List[Dict]):
    """   """
    print_separator("    ")
    
    total_tests = len(results)
    
    #     
    law_chunks = [r['law_chunks'] for r in results]
    criteria_chunks = [r['criteria_chunks'] for r in results]
    mediation_chunks = [r['mediation_chunks'] for r in results]
    counsel_chunks = [r['counsel_chunks'] for r in results]
    
    print("    :")
    print(f"  - : {sum(law_chunks)/total_tests:.1f} (: {min(law_chunks)}~{max(law_chunks)})")
    print(f"  - : {sum(criteria_chunks)/total_tests:.1f} (: {min(criteria_chunks)}~{max(criteria_chunks)})")
    print(f"  - : {sum(mediation_chunks)/total_tests:.1f} (: {min(mediation_chunks)}~{max(mediation_chunks)})")
    print(f"  - : {sum(counsel_chunks)/total_tests:.1f} (: {min(counsel_chunks)}~{max(counsel_chunks)})")
    
    # Fallback  
    fallback_count = sum(1 for r in results if r['fallback_triggered'])
    print(f"\n Fallback :")
    print(f"  -  : {fallback_count}/{total_tests} ({fallback_count/total_tests*100:.1f}%)")
    
    if fallback_count > 0:
        print(f"  - Fallback  :")
        for r in results:
            if r['fallback_triggered']:
                print(f"    •  {r['test_id']}: {r['test_name']}")
                print(f"      (: {r['mediation_chunks']}, : {r['counsel_chunks']})")


def analyze_similarity(results: List[Dict]):
    """ """
    print_separator("  ")
    
    avg_sims = [r['avg_similarity'] for r in results]
    max_sims = [r['max_similarity'] for r in results]
    min_sims = [r['min_similarity'] for r in results]
    
    print("  :")
    print(f"  -   : {sum(avg_sims)/len(avg_sims):.3f}")
    print(f"  -   ( ): {max(max_sims):.3f}")
    print(f"  -   ( ): {min(min_sims):.3f}")
    
    print(f"\n  :")
    for r in sorted(results, key=lambda x: x['avg_similarity'], reverse=True):
        print(f"  •  {r['test_id']}: {r['test_name']}")
        print(f"    ={r['avg_similarity']:.3f}, ={r['max_similarity']:.3f}, ={r['min_similarity']:.3f}")
    
    #   
    high_quality = sum(1 for s in avg_sims if s >= 0.7)
    medium_quality = sum(1 for s in avg_sims if 0.5 <= s < 0.7)
    low_quality = sum(1 for s in avg_sims if s < 0.5)
    
    print(f"\n   :")
    print(f"  -  (≥0.7): {high_quality} ({high_quality/len(results)*100:.1f}%)")
    print(f"  -  (0.5~0.7): {medium_quality} ({medium_quality/len(results)*100:.1f}%)")
    print(f"  -  (<0.5): {low_quality} ({low_quality/len(results)*100:.1f}%)")


def analyze_agency_recommendation(results: List[Dict]):
    """  """
    print_separator("   ")
    
    total_tests = len(results)
    correct_count = sum(1 for r in results if r['agency_correct'])
    accuracy = correct_count / total_tests * 100
    
    print(f"  : {accuracy:.1f}% ({correct_count}/{total_tests})")
    
    print(f"\n   :")
    for r in results:
        status = " " if r['agency_correct'] else " "
        print(f"  •  {r['test_id']}: {r['test_name']}")
        print(f"     : {r['recommended_agency']} ({status})")
        print(f"     : {r['agency_score']:.3f}")
    
    #   
    from collections import Counter
    agency_counts = Counter(r['recommended_agency'] for r in results if r['recommended_agency'])
    
    print(f"\n   :")
    for agency, count in agency_counts.most_common():
        print(f"  - {agency}: {count} ({count/total_tests*100:.1f}%)")


def analyze_performance(results: List[Dict]):
    """ """
    print_separator("  ")
    
    elapsed_times = [r['elapsed_time'] for r in results]
    total_chunks = [r['total_chunks'] for r in results]
    
    print("⏱  :")
    print(f"  -  : {sum(elapsed_times)/len(elapsed_times):.2f}")
    print(f"  -  : {min(elapsed_times):.2f}")
    print(f"  -  : {max(elapsed_times):.2f}")
    
    print(f"\n    :")
    avg_time_per_chunk = sum(
        r['elapsed_time'] / r['total_chunks'] 
        for r in results if r['total_chunks'] > 0
    ) / len(results)
    print(f"  - : {avg_time_per_chunk:.3f}/")
    
    print(f"\n  :")
    for r in sorted(results, key=lambda x: x['elapsed_time']):
        print(f"  •  {r['test_id']}: {r['elapsed_time']:.2f} ({r['total_chunks']} )")


def generate_recommendations(results: List[Dict]):
    """    """
    print_separator("  ")
    
    recommendations = []
    
    # 1. Fallback  
    fallback_count = sum(1 for r in results if r['fallback_triggered'])
    fallback_rate = fallback_count / len(results)
    
    if fallback_rate > 0.5:
        recommendations.append(
            " Fallback 50%   . "
            "   mediation_threshold   ."
        )
    
    # 2.  
    avg_similarities = [r['avg_similarity'] for r in results]
    overall_avg = sum(avg_similarities) / len(avg_similarities)
    
    if overall_avg < 0.5:
        recommendations.append(
            "    0.5 . "
            "     ."
        )
    elif overall_avg >= 0.7:
        recommendations.append(
            "  .      ."
        )
    
    # 3.    
    correct_count = sum(1 for r in results if r['agency_correct'])
    accuracy = correct_count / len(results)
    
    if accuracy < 0.75:
        recommendations.append(
            "    75% . "
            "    (rule_weight/result_weight) ."
        )
    elif accuracy == 1.0:
        recommendations.append(
            "   100% .   ."
        )
    
    # 4.  
    elapsed_times = [r['elapsed_time'] for r in results]
    avg_time = sum(elapsed_times) / len(elapsed_times)
    
    if avg_time > 5.0:
        recommendations.append(
            "    5 . "
            "   top_k    ."
        )
    elif avg_time < 2.0:
        recommendations.append(
            "    ( 2 )."
        )
    
    # 5.    
    total_chunks_list = [r['total_chunks'] for r in results]
    avg_chunks = sum(total_chunks_list) / len(total_chunks_list)
    
    if avg_chunks < 5:
        recommendations.append(
            "    5 . "
            "top_k     ."
        )
    elif avg_chunks > 20:
        recommendations.append(
            "    20 . "
            "LLM     . top_k  ."
        )
    
    if recommendations:
        for rec in recommendations:
            print(f"\n{rec}")
    else:
        print("\n   .    .")


def main():
    """  """
    print_separator(" RAG   ")
    
    #   
    results = load_results()
    
    print(f"  : {len(results)}")
    print(f"  \n")
    
    #   
    analyze_search_distribution(results)
    analyze_similarity(results)
    analyze_agency_recommendation(results)
    analyze_performance(results)
    generate_recommendations(results)
    
    print_separator("  ")


if __name__ == "__main__":
    main()
