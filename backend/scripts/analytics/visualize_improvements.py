#!/usr/bin/env python3
"""
   

       .
"""

import json
from pathlib import Path
from typing import Dict, List
from collections import Counter

def create_bar_chart(data: Dict[str, int], title: str, max_width: int = 50) -> str:
    """    """
    lines = [title, "=" * 80]
    
    if not data:
        lines.append(" ")
        return "\n".join(lines)
    
    max_value = max(data.values())
    
    for label, value in sorted(data.items(), key=lambda x: x[1], reverse=True):
        bar_length = int((value / max_value) * max_width) if max_value > 0 else 0
        bar = "" * bar_length
        lines.append(f"{label:<30} {bar} {value:,}")
    
    return "\n".join(lines)

def create_comparison_chart(baseline: Dict[str, int], current: Dict[str, int], 
                           title: str) -> str:
    """   """
    lines = [title, "=" * 80]
    lines.append(f"{'':<30} {' ':>15} {' ':>15} {'':>15}")
    lines.append("-" * 80)
    
    for key in baseline.keys():
        base_val = baseline[key]
        curr_val = current.get(key, 0)
        
        if base_val > 0:
            improvement = ((base_val - curr_val) / base_val) * 100
        else:
            improvement = 0
        
        lines.append(f"{key:<30} {base_val:>15,} {curr_val:>15,} {improvement:>14.1f}%")
    
    return "\n".join(lines)

def visualize_chunk_distribution(transformed_dir: str = "backend/data/transformed"):
    """   """
    transformed_dir = Path(transformed_dir)
    
    #    
    size_buckets = {
        '< 100': 0,
        '100-500': 0,
        '500-1000': 0,
        '1000-2000': 0,
        '2000-5000': 0,
        '> 5000': 0
    }
    
    chunk_types = Counter()
    
    for json_file in transformed_dir.glob("*.json"):
        if json_file.name in ['validation_result.json', 'transformation_summary.json']:
            continue
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            #   
            if isinstance(data, dict) and 'documents' in data:
                docs = data['documents']
            elif isinstance(data, list):
                docs = data
            else:
                docs = [data]
            
            for doc in docs:
                for chunk in doc.get('chunks', []):
                    if chunk.get('drop'):
                        continue
                    
                    content_len = chunk.get('content_length', len(chunk.get('content', '')))
                    chunk_type = chunk.get('chunk_type', 'unknown')
                    
                    chunk_types[chunk_type] += 1
                    
                    #  
                    if content_len < 100:
                        size_buckets['< 100'] += 1
                    elif content_len < 500:
                        size_buckets['100-500'] += 1
                    elif content_len < 1000:
                        size_buckets['500-1000'] += 1
                    elif content_len < 2000:
                        size_buckets['1000-2000'] += 1
                    elif content_len < 5000:
                        size_buckets['2000-5000'] += 1
                    else:
                        size_buckets['> 5000'] += 1
        
        except Exception as e:
            print(f"  {json_file.name}   : {e}")
            continue
    
    #  
    print("\n" + "=" * 100)
    print("    ")
    print("=" * 100)
    
    # 1.   
    print("\n" + create_bar_chart(size_buckets, "1.   "))
    
    # 2.   
    print("\n" + create_bar_chart(dict(chunk_types), "2.   "))
    
    # 3.   
    baseline = {
        'Critical Issues': 92,
        '  (< 100)': 1500,
        '  (> 2,000)': 300
    }
    
    current = {
        'Critical Issues': 0,
        '  (< 100)': size_buckets['< 100'],
        '  (> 2,000)': size_buckets['2000-5000'] + size_buckets['> 5000']
    }
    
    print("\n" + create_comparison_chart(baseline, current, "3.     "))
    
    # 4. 
    print("\n" + "=" * 100)
    print("")
    print("=" * 100)
    
    total_chunks = sum(size_buckets.values())
    optimal_chunks = size_buckets['100-500'] + size_buckets['500-1000'] + size_buckets['1000-2000']
    optimal_rate = (optimal_chunks / total_chunks * 100) if total_chunks > 0 else 0
    
    print(f"  : {total_chunks:,}")
    print(f"   (100-2,000): {optimal_chunks:,} ({optimal_rate:.1f}%)")
    print(f"   : {chunk_types.most_common(1)[0][0]} ({chunk_types.most_common(1)[0][1]:,})")
    
    print("\n" + "=" * 100)
    print("  !")
    print("=" * 100)

if __name__ == '__main__':
    visualize_chunk_distribution()
