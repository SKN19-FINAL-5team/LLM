#!/usr/bin/env python3
"""
   

:
1.     (chunk_type)
2.     (   )
3.    (   )
4.    (   )
"""

import psycopg2
import os
import json
import statistics
import re
from typing import List, Dict, Tuple
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'ddoksori'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'postgres')
}

class ChunkingQualityTest:
    """   """
    
    def __init__(self, db_config: Dict):
        self.db_config = db_config
        self.conn = None
        self.test_results = []
    
    def connect(self):
        """DB """
        if self.conn is None or self.conn.closed:
            self.conn = psycopg2.connect(**self.db_config)
    
    def close(self):
        """DB  """
        if self.conn and not self.conn.closed:
            self.conn.close()
    
    def test_chunk_size_distribution(self) -> Dict:
        """
         1:     (chunk_type)
        """
        print("\n===  1:     ===")
        
        self.connect()
        cur = self.conn.cursor()
        
        # chunk_type 
        cur.execute("""
            SELECT 
                c.chunk_type,
                d.doc_type,
                COUNT(*) AS chunk_count,
                AVG(c.content_length) AS avg_length,
                MIN(c.content_length) AS min_length,
                MAX(c.content_length) AS max_length,
                PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY c.content_length) AS q1,
                PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY c.content_length) AS median,
                PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY c.content_length) AS q3
            FROM chunks c
            JOIN documents d ON c.doc_id = d.doc_id
            WHERE c.drop = FALSE
            GROUP BY c.chunk_type, d.doc_type
            ORDER BY d.doc_type, c.chunk_type
        """)
        
        stats = cur.fetchall()
        cur.close()
        
        #   (data_transform_pipeline.py )
        chunking_rules = {
            'decision': {'target': 500, 'max': 600},
            'reasoning': {'target': 700, 'max': 800},
            'judgment': {'target': 700, 'max': 800},
            'parties_claim': {'target': 650, 'max': 750},
            'law': {'target': 400, 'max': 500},
            'qa_combined': {'target': 600, 'max': 700}
        }
        
        distribution_results = []
        
        print(f"\n{'Chunk Type':<20} {'Doc Type':<20} {'Count':<8} {'Avg':<8} {'Q1-Med-Q3':<20} {'Min-Max':<15}")
        print("-" * 100)
        
        for row in stats:
            chunk_type, doc_type, count, avg, min_len, max_len, q1, median, q3 = row
            
            #   
            rule = chunking_rules.get(chunk_type, None)
            if rule:
                within_target = abs(avg - rule['target']) <= rule['target'] * 0.3  # 30%  
                within_max = max_len <= rule['max'] * 1.2  # 20%  
            else:
                within_target = True
                within_max = True
            
            status = "" if (within_target and within_max) else ""
            
            print(f"{chunk_type or 'None':<20} {doc_type:<20} {count:<8} {avg:>7.0f} "
                  f"{q1:>6.0f}-{median:>6.0f}-{q3:>6.0f}  {min_len:>6.0f}-{max_len:>6.0f}  {status}")
            
            distribution_results.append({
                "chunk_type": chunk_type,
                "doc_type": doc_type,
                "chunk_count": int(count),
                "avg_length": float(round(avg, 1)),
                "median_length": float(round(median, 1)),
                "min_length": int(min_len),
                "max_length": int(max_len),
                "q1": float(round(q1, 1)),
                "q3": float(round(q3, 1)),
                "within_target": within_target,
                "within_max": within_max
            })
        
        result = {
            "test_name": "Chunk Size Distribution",
            "status": "completed",
            "distributions": distribution_results
        }
        
        self.test_results.append(result)
        return result
    
    def test_sentence_boundary_preservation(self, sample_size: int = 100) -> Dict:
        """
         2:     (   )
        """
        print("\n===  2:     ===")
        
        self.connect()
        cur = self.conn.cursor()
        
        #   
        cur.execute("""
            SELECT chunk_id, content, chunk_type
            FROM chunks
            WHERE drop = FALSE AND content_length > 100
            ORDER BY RANDOM()
            LIMIT %s
        """, (sample_size,))
        
        samples = cur.fetchall()
        cur.close()
        
        #    ()
        sentence_endings = ['.', '.', '.', '?', '?', '?', '?', '!', '?']
        
        proper_starts = 0  #   
        proper_ends = 0    #   
        
        for chunk_id, content, chunk_type in samples:
            content = content.strip()
            
            #  :       
            starts_properly = bool(re.match(r'^[A-Z0-9-\[]', content))
            if starts_properly:
                proper_starts += 1
            
            #  :    
            ends_properly = any(content.endswith(end) for end in sentence_endings)
            if ends_properly:
                proper_ends += 1
        
        proper_start_ratio = (proper_starts / sample_size) * 100
        proper_end_ratio = (proper_ends / sample_size) * 100
        
        passed = proper_start_ratio > 70 and proper_end_ratio > 70  # 70% 
        
        result = {
            "test_name": "Sentence Boundary Preservation",
            "status": "passed" if passed else "warning",
            "sample_size": sample_size,
            "proper_starts": proper_starts,
            "proper_start_ratio": round(proper_start_ratio, 2),
            "proper_ends": proper_ends,
            "proper_end_ratio": round(proper_end_ratio, 2),
            "threshold_percent": 70
        }
        
        print(f"   : {sample_size}")
        print(f"   : {proper_starts} ({proper_start_ratio:.1f}%)")
        print(f"   : {proper_ends} ({proper_end_ratio:.1f}%)")
        print(f"  : {' PASSED' if passed else ' WARNING'}")
        
        self.test_results.append(result)
        return result
    
    def test_overlap_quality(self, sample_size: int = 50) -> Dict:
        """
         3:    (   )
        """
        print("\n===  3:    ===")
        
        self.connect()
        cur = self.conn.cursor()
        
        #    
        cur.execute("""
            SELECT 
                c1.chunk_id AS chunk1_id,
                c1.content AS chunk1_content,
                c1.content_length AS chunk1_len,
                c2.chunk_id AS chunk2_id,
                c2.content AS chunk2_content,
                c2.content_length AS chunk2_len
            FROM chunks c1
            JOIN chunks c2 ON c1.doc_id = c2.doc_id AND c1.chunk_index + 1 = c2.chunk_index
            WHERE c1.drop = FALSE AND c2.drop = FALSE
            ORDER BY RANDOM()
            LIMIT %s
        """, (sample_size,))
        
        pairs = cur.fetchall()
        cur.close()
        
        overlap_found = 0
        overlap_lengths = []
        
        for chunk1_id, content1, len1, chunk2_id, content2, len2 in pairs:
            #   : 1  100 2  100 
            overlap = self.find_overlap(content1[-100:], content2[:100])
            
            if overlap > 10:  # 10  
                overlap_found += 1
                overlap_lengths.append(overlap)
        
        overlap_ratio = (overlap_found / sample_size) * 100 if sample_size > 0 else 0
        avg_overlap = statistics.mean(overlap_lengths) if overlap_lengths else 0
        
        result = {
            "test_name": "Overlap Quality",
            "status": "info",
            "sample_size": sample_size,
            "overlap_found": overlap_found,
            "overlap_ratio": round(overlap_ratio, 2),
            "avg_overlap_length": round(avg_overlap, 1) if avg_overlap > 0 else 0
        }
        
        print(f"   : {sample_size}")
        print(f"   : {overlap_found} ({overlap_ratio:.1f}%)")
        if avg_overlap > 0:
            print(f"    : {avg_overlap:.1f}")
        print(f"  : ℹ INFO")
        
        self.test_results.append(result)
        return result
    
    def find_overlap(self, str1: str, str2: str) -> int:
        """     """
        max_overlap = 0
        for i in range(1, min(len(str1), len(str2)) + 1):
            if str1[-i:] == str2[:i]:
                max_overlap = i
        return max_overlap
    
    def test_metadata_extraction(self, sample_size: int = 20) -> Dict:
        """
         4:   
        """
        print("\n===  4:    ( ) ===")
        
        self.connect()
        cur = self.conn.cursor()
        
        #    
        cur.execute("""
            SELECT 
                c.chunk_id,
                c.content,
                c.chunk_type,
                d.metadata
            FROM chunks c
            JOIN documents d ON c.doc_id = d.doc_id
            WHERE c.drop = FALSE 
                AND d.metadata IS NOT NULL
                AND jsonb_typeof(d.metadata) = 'object'
            ORDER BY RANDOM()
            LIMIT %s
        """, (sample_size,))
        
        samples = cur.fetchall()
        cur.close()
        
        metadata_stats = {
            "has_keywords": 0,
            "has_decision_date": 0,
            "has_case_no": 0,
            "total": len(samples)
        }
        
        print(f"\n   {len(samples)} :")
        
        for i, (chunk_id, content, chunk_type, metadata) in enumerate(samples[:5], 1):  #  5 
            print(f"\n   {i}:")
            print(f"    Chunk ID: {chunk_id[:50]}...")
            print(f"    Chunk Type: {chunk_type}")
            print(f"    Content: {content[:100]}...")
            
            if metadata:
                if 'keywords' in metadata:
                    metadata_stats['has_keywords'] += 1
                    print(f"    Keywords: {metadata.get('keywords', [])[:3]}")
                
                if 'decision_date' in metadata:
                    metadata_stats['has_decision_date'] += 1
                    print(f"    Decision Date: {metadata.get('decision_date')}")
                
                if 'case_no' in metadata:
                    metadata_stats['has_case_no'] += 1
                    print(f"    Case No: {metadata.get('case_no')}")
        
        #   
        for chunk_id, content, chunk_type, metadata in samples[5:]:
            if metadata:
                if 'keywords' in metadata:
                    metadata_stats['has_keywords'] += 1
                if 'decision_date' in metadata:
                    metadata_stats['has_decision_date'] += 1
                if 'case_no' in metadata:
                    metadata_stats['has_case_no'] += 1
        
        result = {
            "test_name": "Metadata Extraction Accuracy",
            "status": "info",
            "sample_size": len(samples),
            "has_keywords": metadata_stats['has_keywords'],
            "has_decision_date": metadata_stats['has_decision_date'],
            "has_case_no": metadata_stats['has_case_no'],
            "keywords_ratio": round((metadata_stats['has_keywords'] / len(samples)) * 100, 2) if len(samples) > 0 else 0
        }
        
        print(f"\n   :")
        print(f"    Keywords : {metadata_stats['has_keywords']}/{len(samples)} ({result['keywords_ratio']:.1f}%)")
        print(f"    Decision Date : {metadata_stats['has_decision_date']}/{len(samples)}")
        print(f"    Case No : {metadata_stats['has_case_no']}/{len(samples)}")
        
        self.test_results.append(result)
        return result
    
    def test_empty_chunks(self) -> Dict:
        """
         :       
        """
        print("\n=== : /   ===")
        
        self.connect()
        cur = self.conn.cursor()
        
        #   (content_length < 10  drop = TRUE)
        cur.execute("""
            SELECT 
                COUNT(*) FILTER (WHERE content_length < 10 AND drop = FALSE) AS very_short,
                COUNT(*) FILTER (WHERE content_length < 50 AND drop = FALSE) AS short,
                COUNT(*) FILTER (WHERE drop = TRUE) AS dropped,
                COUNT(*) AS total
            FROM chunks
        """)
        
        stats = cur.fetchone()
        cur.close()
        
        very_short, short, dropped, total = stats
        
        result = {
            "test_name": "Empty/Short Chunks Detection",
            "status": "info",
            "very_short_chunks": very_short,
            "short_chunks": short,
            "dropped_chunks": dropped,
            "total_chunks": total,
            "very_short_ratio": round((very_short / total) * 100, 2) if total > 0 else 0,
            "dropped_ratio": round((dropped / total) * 100, 2) if total > 0 else 0
        }
        
        print(f"     (< 10, drop=FALSE): {very_short} ({result['very_short_ratio']:.2f}%)")
        print(f"    (< 50, drop=FALSE): {short}")
        print(f"  Drop  TRUE: {dropped} ({result['dropped_ratio']:.2f}%)")
        print(f"   : {total}")
        
        self.test_results.append(result)
        return result
    
    def run_all_tests(self) -> Dict:
        """  """
        print("=" * 100)
        print("    ")
        print("=" * 100)
        
        try:
            #  
            self.test_chunk_size_distribution()
            self.test_sentence_boundary_preservation()
            self.test_overlap_quality()
            self.test_metadata_extraction()
            self.test_empty_chunks()
            
            #  
            summary = {
                "total_tests": len(self.test_results),
                "tests": self.test_results
            }
            
            print("\n" + "=" * 100)
            print(" ")
            print("=" * 100)
            print(f" : {len(self.test_results)}")
            
            return summary
            
        except Exception as e:
            print(f"\n   : {e}")
            import traceback
            traceback.print_exc()
            return {"status": "error", "message": str(e)}
        
        finally:
            self.close()


if __name__ == "__main__":
    #  
    tester = ChunkingQualityTest(DB_CONFIG)
    results = tester.run_all_tests()
    
    #  
    output_file = "/tmp/chunking_quality_test_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n {output_file} .")
