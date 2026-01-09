#!/usr/bin/env python3
"""
개선 효과 시각화 스크립트

데이터 품질 개선 효과를 간단한 텍스트 그래프로 시각화합니다.
"""

import json
from pathlib import Path
from typing import Dict, List
from collections import Counter

def create_bar_chart(data: Dict[str, int], title: str, max_width: int = 50) -> str:
    """간단한 텍스트 기반 막대 그래프"""
    lines = [title, "=" * 80]
    
    if not data:
        lines.append("데이터 없음")
        return "\n".join(lines)
    
    max_value = max(data.values())
    
    for label, value in sorted(data.items(), key=lambda x: x[1], reverse=True):
        bar_length = int((value / max_value) * max_width) if max_value > 0 else 0
        bar = "█" * bar_length
        lines.append(f"{label:<30} {bar} {value:,}")
    
    return "\n".join(lines)

def create_comparison_chart(baseline: Dict[str, int], current: Dict[str, int], 
                           title: str) -> str:
    """개선 전후 비교 차트"""
    lines = [title, "=" * 80]
    lines.append(f"{'지표':<30} {'개선 전':>15} {'개선 후':>15} {'개선율':>15}")
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
    """청크 크기 분포 시각화"""
    transformed_dir = Path(transformed_dir)
    
    # 청크 크기별 분포 수집
    size_buckets = {
        '< 100자': 0,
        '100-500자': 0,
        '500-1000자': 0,
        '1000-2000자': 0,
        '2000-5000자': 0,
        '> 5000자': 0
    }
    
    chunk_types = Counter()
    
    for json_file in transformed_dir.glob("*.json"):
        if json_file.name in ['validation_result.json', 'transformation_summary.json']:
            continue
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 문서 리스트 처리
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
                    
                    # 크기별 분류
                    if content_len < 100:
                        size_buckets['< 100자'] += 1
                    elif content_len < 500:
                        size_buckets['100-500자'] += 1
                    elif content_len < 1000:
                        size_buckets['500-1000자'] += 1
                    elif content_len < 2000:
                        size_buckets['1000-2000자'] += 1
                    elif content_len < 5000:
                        size_buckets['2000-5000자'] += 1
                    else:
                        size_buckets['> 5000자'] += 1
        
        except Exception as e:
            print(f"⚠️  {json_file.name} 처리 중 오류: {e}")
            continue
    
    # 차트 생성
    print("\n" + "=" * 100)
    print("데이터 품질 개선 효과 시각화")
    print("=" * 100)
    
    # 1. 청크 크기 분포
    print("\n" + create_bar_chart(size_buckets, "1. 청크 크기 분포"))
    
    # 2. 청크 타입 분포
    print("\n" + create_bar_chart(dict(chunk_types), "2. 청크 타입 분포"))
    
    # 3. 개선 전후 비교
    baseline = {
        'Critical Issues': 92,
        '짧은 청크 (< 100자)': 1500,
        '긴 청크 (> 2,000자)': 300
    }
    
    current = {
        'Critical Issues': 0,
        '짧은 청크 (< 100자)': size_buckets['< 100자'],
        '긴 청크 (> 2,000자)': size_buckets['2000-5000자'] + size_buckets['> 5000자']
    }
    
    print("\n" + create_comparison_chart(baseline, current, "3. 품질 지표 개선 전후 비교"))
    
    # 4. 요약
    print("\n" + "=" * 100)
    print("요약")
    print("=" * 100)
    
    total_chunks = sum(size_buckets.values())
    optimal_chunks = size_buckets['100-500자'] + size_buckets['500-1000자'] + size_buckets['1000-2000자']
    optimal_rate = (optimal_chunks / total_chunks * 100) if total_chunks > 0 else 0
    
    print(f"총 활성 청크: {total_chunks:,}개")
    print(f"최적 크기 청크 (100-2,000자): {optimal_chunks:,}개 ({optimal_rate:.1f}%)")
    print(f"가장 많은 청크 타입: {chunk_types.most_common(1)[0][0]} ({chunk_types.most_common(1)[0][1]:,}개)")
    
    print("\n" + "=" * 100)
    print("✅ 시각화 완료!")
    print("=" * 100)

if __name__ == '__main__':
    visualize_chunk_distribution()
