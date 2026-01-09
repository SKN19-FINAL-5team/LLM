#!/usr/bin/env python3
"""
청킹 로직 품질 테스트

목적:
1. 청크 크기 분포 분석 (chunk_type별)
2. 의미 경계 보존 확인 (문장 중간 분할 비율)
3. 오버랩 품질 평가 (중첩 구간의 의미 연속성)
4. 메타데이터 추출 정확도 (샘플 청크 수동 검증)
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
    """청킹 품질 테스트 클래스"""
    
    def __init__(self, db_config: Dict):
        self.db_config = db_config
        self.conn = None
        self.test_results = []
    
    def connect(self):
        """DB 연결"""
        if self.conn is None or self.conn.closed:
            self.conn = psycopg2.connect(**self.db_config)
    
    def close(self):
        """DB 연결 종료"""
        if self.conn and not self.conn.closed:
            self.conn.close()
    
    def test_chunk_size_distribution(self) -> Dict:
        """
        테스트 1: 청크 크기 분포 분석 (chunk_type별)
        """
        print("\n=== 테스트 1: 청크 크기 분포 분석 ===")
        
        self.connect()
        cur = self.conn.cursor()
        
        # chunk_type별 통계
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
        
        # 청킹 규칙 (data_transform_pipeline.py 기준)
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
            
            # 규칙 준수 여부
            rule = chunking_rules.get(chunk_type, None)
            if rule:
                within_target = abs(avg - rule['target']) <= rule['target'] * 0.3  # 30% 허용 오차
                within_max = max_len <= rule['max'] * 1.2  # 20% 초과 허용
            else:
                within_target = True
                within_max = True
            
            status = "✅" if (within_target and within_max) else "⚠️"
            
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
        테스트 2: 의미 경계 보존 확인 (문장 중간 분할 비율)
        """
        print("\n=== 테스트 2: 문장 경계 보존 확인 ===")
        
        self.connect()
        cur = self.conn.cursor()
        
        # 랜덤 청크 샘플링
        cur.execute("""
            SELECT chunk_id, content, chunk_type
            FROM chunks
            WHERE drop = FALSE AND content_length > 100
            ORDER BY RANDOM()
            LIMIT %s
        """, (sample_size,))
        
        samples = cur.fetchall()
        cur.close()
        
        # 문장 종결 패턴 (한국어)
        sentence_endings = ['.', '다.', '요.', '까?', '가?', '나?', '요?', '!', '?']
        
        proper_starts = 0  # 문장 시작으로 시작
        proper_ends = 0    # 문장 끝으로 끝남
        
        for chunk_id, content, chunk_type in samples:
            content = content.strip()
            
            # 시작 확인: 첫 문자가 대문자 또는 숫자 또는 한글
            starts_properly = bool(re.match(r'^[A-Z0-9가-힣\[]', content))
            if starts_properly:
                proper_starts += 1
            
            # 끝 확인: 문장 종결 부호로 끝남
            ends_properly = any(content.endswith(end) for end in sentence_endings)
            if ends_properly:
                proper_ends += 1
        
        proper_start_ratio = (proper_starts / sample_size) * 100
        proper_end_ratio = (proper_ends / sample_size) * 100
        
        passed = proper_start_ratio > 70 and proper_end_ratio > 70  # 70% 기준
        
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
        
        print(f"  샘플 크기: {sample_size}개")
        print(f"  적절한 시작: {proper_starts}개 ({proper_start_ratio:.1f}%)")
        print(f"  적절한 끝: {proper_ends}개 ({proper_end_ratio:.1f}%)")
        print(f"  결과: {'✅ PASSED' if passed else '⚠️ WARNING'}")
        
        self.test_results.append(result)
        return result
    
    def test_overlap_quality(self, sample_size: int = 50) -> Dict:
        """
        테스트 3: 오버랩 품질 평가 (중첩 구간의 의미 연속성)
        """
        print("\n=== 테스트 3: 오버랩 품질 평가 ===")
        
        self.connect()
        cur = self.conn.cursor()
        
        # 연속된 청크 쌍 샘플링
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
            # 간단한 오버랩 감지: 청크1의 끝 100자와 청크2의 시작 100자 비교
            overlap = self.find_overlap(content1[-100:], content2[:100])
            
            if overlap > 10:  # 10자 이상 중첩
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
        
        print(f"  샘플 크기: {sample_size}쌍")
        print(f"  오버랩 발견: {overlap_found}쌍 ({overlap_ratio:.1f}%)")
        if avg_overlap > 0:
            print(f"  평균 오버랩 길이: {avg_overlap:.1f}자")
        print(f"  결과: ℹ️ INFO")
        
        self.test_results.append(result)
        return result
    
    def find_overlap(self, str1: str, str2: str) -> int:
        """두 문자열의 최대 오버랩 길이 찾기"""
        max_overlap = 0
        for i in range(1, min(len(str1), len(str2)) + 1):
            if str1[-i:] == str2[:i]:
                max_overlap = i
        return max_overlap
    
    def test_metadata_extraction(self, sample_size: int = 20) -> Dict:
        """
        테스트 4: 메타데이터 추출 정확도
        """
        print("\n=== 테스트 4: 메타데이터 추출 정확도 (샘플 검증) ===")
        
        self.connect()
        cur = self.conn.cursor()
        
        # 메타데이터가 있는 청크 샘플링
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
        
        print(f"\n  샘플 {len(samples)}개 분석:")
        
        for i, (chunk_id, content, chunk_type, metadata) in enumerate(samples[:5], 1):  # 처음 5개만 출력
            print(f"\n  샘플 {i}:")
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
        
        # 전체 샘플 통계
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
        
        print(f"\n  전체 통계:")
        print(f"    Keywords 있음: {metadata_stats['has_keywords']}/{len(samples)} ({result['keywords_ratio']:.1f}%)")
        print(f"    Decision Date 있음: {metadata_stats['has_decision_date']}/{len(samples)}")
        print(f"    Case No 있음: {metadata_stats['has_case_no']}/{len(samples)}")
        
        self.test_results.append(result)
        return result
    
    def test_empty_chunks(self) -> Dict:
        """
        추가 테스트: 빈 청크 또는 너무 짧은 청크 감지
        """
        print("\n=== 추가: 빈/짧은 청크 감지 ===")
        
        self.connect()
        cur = self.conn.cursor()
        
        # 빈 청크 (content_length < 10 또는 drop = TRUE)
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
        
        print(f"  매우 짧은 청크 (< 10자, drop=FALSE): {very_short}개 ({result['very_short_ratio']:.2f}%)")
        print(f"  짧은 청크 (< 50자, drop=FALSE): {short}개")
        print(f"  Drop 플래그 TRUE: {dropped}개 ({result['dropped_ratio']:.2f}%)")
        print(f"  총 청크: {total}개")
        
        self.test_results.append(result)
        return result
    
    def run_all_tests(self) -> Dict:
        """모든 테스트 실행"""
        print("=" * 100)
        print("청킹 로직 품질 테스트 시작")
        print("=" * 100)
        
        try:
            # 테스트 실행
            self.test_chunk_size_distribution()
            self.test_sentence_boundary_preservation()
            self.test_overlap_quality()
            self.test_metadata_extraction()
            self.test_empty_chunks()
            
            # 결과 요약
            summary = {
                "total_tests": len(self.test_results),
                "tests": self.test_results
            }
            
            print("\n" + "=" * 100)
            print("테스트 완료")
            print("=" * 100)
            print(f"총 테스트: {len(self.test_results)}개")
            
            return summary
            
        except Exception as e:
            print(f"\n테스트 실행 중 오류: {e}")
            import traceback
            traceback.print_exc()
            return {"status": "error", "message": str(e)}
        
        finally:
            self.close()


if __name__ == "__main__":
    # 테스트 실행
    tester = ChunkingQualityTest(DB_CONFIG)
    results = tester.run_all_tests()
    
    # 결과 저장
    output_file = "/tmp/chunking_quality_test_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n결과가 {output_file}에 저장되었습니다.")
