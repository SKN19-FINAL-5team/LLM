#!/usr/bin/env python3
"""
데이터 변환 결과 시각화 스크립트

데이터베이스에 저장된 변환 결과를 시각적으로 확인합니다.
- 전체 통계
- 문서/청크 분포
- 샘플 데이터
- 데이터 검증

Usage:
    python visualize_transformation.py
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv
from typing import Dict, List
import json

# 환경 변수 로드
load_dotenv()

class TransformationVisualizer:
    """데이터 변환 결과 시각화"""
    
    def __init__(self):
        """데이터베이스 연결 초기화"""
        self.conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5432'),
            database=os.getenv('DB_NAME', 'ddoksori'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', 'postgres')
        )
        self.cur = self.conn.cursor(cursor_factory=RealDictCursor)
    
    def print_header(self, title: str):
        """헤더 출력"""
        print("\n" + "=" * 80)
        print(title.center(80))
        print("=" * 80)
    
    def print_section(self, title: str):
        """섹션 헤더 출력"""
        print("\n" + "-" * 80)
        print(f"[{title}]")
        print("-" * 80)
    
    def show_overall_statistics(self):
        """전체 통계 출력"""
        self.print_header("데이터 변환 결과 통계")
        
        # 1. 문서 통계
        self.print_section("문서 통계")
        self.cur.execute("SELECT COUNT(*) as total FROM documents")
        total_docs = self.cur.fetchone()['total']
        print(f"  총 문서 수: {total_docs:,}개")
        
        # 문서 유형별
        print("\n  문서 유형별:")
        self.cur.execute("""
            SELECT doc_type, COUNT(*) as count
            FROM documents
            GROUP BY doc_type
            ORDER BY count DESC
        """)
        for row in self.cur.fetchall():
            print(f"    - {row['doc_type']:<25} {row['count']:>10,}개")
        
        # 2. 청크 통계
        self.print_section("청크 통계")
        self.cur.execute("SELECT COUNT(*) as total FROM chunks")
        total_chunks = self.cur.fetchone()['total']
        print(f"  총 청크 수: {total_chunks:,}개")
        
        # 활성/비활성 청크
        self.cur.execute("""
            SELECT 
                COUNT(CASE WHEN drop = FALSE THEN 1 END) as active,
                COUNT(CASE WHEN drop = TRUE THEN 1 END) as dropped
            FROM chunks
        """)
        row = self.cur.fetchone()
        print(f"    - 활성 청크: {row['active']:,}개")
        print(f"    - 비활성 청크: {row['dropped']:,}개")
        
        # 청크 유형별
        print("\n  청크 유형별:")
        self.cur.execute("""
            SELECT chunk_type, COUNT(*) as count
            FROM chunks
            WHERE drop = FALSE
            GROUP BY chunk_type
            ORDER BY count DESC
            LIMIT 15
        """)
        for row in self.cur.fetchall():
            chunk_type = row['chunk_type'] or '(NULL)'
            print(f"    - {chunk_type:<25} {row['count']:>10,}개")
        
        # 3. 청크 길이 통계
        self.print_section("청크 길이 통계")
        self.cur.execute("""
            SELECT 
                MIN(content_length) as min_length,
                AVG(content_length) as avg_length,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY content_length) as median_length,
                MAX(content_length) as max_length
            FROM chunks
            WHERE drop = FALSE
        """)
        row = self.cur.fetchone()
        print(f"  - 최소 길이: {row['min_length']:,}자")
        print(f"  - 평균 길이: {row['avg_length']:.0f}자")
        print(f"  - 중앙값: {row['median_length']:.0f}자")
        print(f"  - 최대 길이: {row['max_length']:,}자")
        
        # 4. 출처별 통계
        self.print_section("출처별 통계")
        self.cur.execute("""
            SELECT 
                d.source_org,
                COUNT(DISTINCT d.doc_id) as doc_count,
                COUNT(c.chunk_id) as chunk_count
            FROM documents d
            LEFT JOIN chunks c ON d.doc_id = c.doc_id AND c.drop = FALSE
            GROUP BY d.source_org
            ORDER BY doc_count DESC
        """)
        for row in self.cur.fetchall():
            source = row['source_org'] or '(NULL)'
            print(f"  - {source:<20} 문서: {row['doc_count']:>6,}개  |  청크: {row['chunk_count']:>10,}개")
        
        # 5. 임베딩 통계
        self.print_section("임베딩 통계")
        self.cur.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN embedding IS NOT NULL THEN 1 END) as embedded,
                ROUND(COUNT(CASE WHEN embedding IS NOT NULL THEN 1 END)::numeric / COUNT(*) * 100, 2) as rate
            FROM chunks
            WHERE drop = FALSE
        """)
        row = self.cur.fetchone()
        print(f"  - 총 청크 수: {row['total']:,}개")
        print(f"  - 임베딩 완료: {row['embedded']:,}개")
        print(f"  - 완료율: {row['rate']}%")
    
    def show_sample_data(self, doc_type: str = None, limit: int = 3):
        """샘플 데이터 출력"""
        self.print_header(f"샘플 데이터{f' ({doc_type})' if doc_type else ''}")
        
        # 문서 유형 필터
        where_clause = f"WHERE doc_type = '{doc_type}'" if doc_type else ""
        
        # 샘플 문서 조회
        self.cur.execute(f"""
            SELECT doc_id, doc_type, title, source_org, category_path
            FROM documents
            {where_clause}
            LIMIT {limit}
        """)
        
        for doc_idx, doc in enumerate(self.cur.fetchall(), 1):
            self.print_section(f"문서 {doc_idx}: {doc['doc_id']}")
            print(f"  제목: {doc['title']}")
            print(f"  유형: {doc['doc_type']}")
            print(f"  출처: {doc['source_org']}")
            if doc['category_path']:
                print(f"  분류: {' > '.join(doc['category_path'])}")
            
            # 해당 문서의 청크 조회
            self.cur.execute("""
                SELECT chunk_id, chunk_index, chunk_type, content, content_length, drop
                FROM chunks
                WHERE doc_id = %s
                ORDER BY chunk_index
                LIMIT 5
            """, (doc['doc_id'],))
            
            chunks = self.cur.fetchall()
            print(f"\n  청크 수: {len(chunks)}개")
            
            for chunk_idx, chunk in enumerate(chunks, 1):
                status = " [비활성]" if chunk['drop'] else ""
                print(f"\n  [청크 {chunk_idx}]{status} {chunk['chunk_id']}")
                print(f"    인덱스: {chunk['chunk_index']}")
                print(f"    타입: {chunk['chunk_type']}")
                print(f"    길이: {chunk['content_length']}자")
                
                # 내용 미리보기 (처음 200자)
                content_preview = chunk['content'][:200].replace('\n', ' ')
                print(f"    내용: {content_preview}...")
    
    def show_distribution_by_doc_type(self):
        """문서 유형별 분포"""
        self.print_header("문서 유형별 분포")
        
        self.cur.execute("""
            SELECT 
                d.doc_type,
                COUNT(DISTINCT d.doc_id) as doc_count,
                COUNT(c.chunk_id) as chunk_count,
                AVG(c.content_length) as avg_length
            FROM documents d
            LEFT JOIN chunks c ON d.doc_id = c.doc_id AND c.drop = FALSE
            GROUP BY d.doc_type
            ORDER BY doc_count DESC
        """)
        
        print(f"\n{'문서 유형':<25} {'문서 수':>10} {'청크 수':>12} {'평균 길이':>12}")
        print("-" * 80)
        
        for row in self.cur.fetchall():
            avg_len = row['avg_length'] if row['avg_length'] else 0
            print(f"{row['doc_type']:<25} {row['doc_count']:>10,} {row['chunk_count']:>12,} {avg_len:>11.0f}자")
    
    def show_distribution_by_source(self):
        """출처별 분포"""
        self.print_header("출처별 분포")
        
        self.cur.execute("""
            SELECT 
                d.source_org,
                d.doc_type,
                COUNT(DISTINCT d.doc_id) as doc_count,
                COUNT(c.chunk_id) as chunk_count
            FROM documents d
            LEFT JOIN chunks c ON d.doc_id = c.doc_id AND c.drop = FALSE
            GROUP BY d.source_org, d.doc_type
            ORDER BY d.source_org, d.doc_type
        """)
        
        print(f"\n{'출처':<20} {'문서 유형':<25} {'문서 수':>10} {'청크 수':>12}")
        print("-" * 80)
        
        for row in self.cur.fetchall():
            source = row['source_org'] or '(NULL)'
            print(f"{source:<20} {row['doc_type']:<25} {row['doc_count']:>10,} {row['chunk_count']:>12,}")
    
    def validate_data(self):
        """데이터 검증"""
        self.print_header("데이터 검증")
        
        issues = []
        
        # 1. 청크 인덱스 검증
        self.print_section("청크 인덱스 검증")
        self.cur.execute("""
            SELECT doc_id, COUNT(*) as chunk_count, MAX(chunk_index) as max_index
            FROM chunks
            GROUP BY doc_id
            HAVING COUNT(*) != MAX(chunk_index) + 1
            LIMIT 10
        """)
        invalid_indices = self.cur.fetchall()
        
        if invalid_indices:
            print(f"  ⚠️  인덱스 불일치 발견: {len(invalid_indices)}개 문서")
            for row in invalid_indices[:5]:
                print(f"    - {row['doc_id']}: 청크 수={row['chunk_count']}, 최대 인덱스={row['max_index']}")
            issues.append(f"청크 인덱스 불일치: {len(invalid_indices)}개")
        else:
            print("  ✅ 모든 청크 인덱스가 정상입니다.")
        
        # 2. 중복 chunk_id 검증
        self.print_section("중복 chunk_id 검증")
        self.cur.execute("""
            SELECT chunk_id, COUNT(*) as count
            FROM chunks
            GROUP BY chunk_id
            HAVING COUNT(*) > 1
        """)
        duplicates = self.cur.fetchall()
        
        if duplicates:
            print(f"  ⚠️  중복 chunk_id 발견: {len(duplicates)}개")
            for row in duplicates[:5]:
                print(f"    - {row['chunk_id']}: {row['count']}회 중복")
            issues.append(f"중복 chunk_id: {len(duplicates)}개")
        else:
            print("  ✅ 중복된 chunk_id가 없습니다.")
        
        # 3. NULL 필드 검증
        self.print_section("필수 필드 NULL 검증")
        self.cur.execute("""
            SELECT 
                COUNT(CASE WHEN content IS NULL THEN 1 END) as null_content,
                COUNT(CASE WHEN chunk_type IS NULL THEN 1 END) as null_type
            FROM chunks
        """)
        row = self.cur.fetchone()
        
        if row['null_content'] > 0:
            print(f"  ⚠️  content가 NULL인 청크: {row['null_content']}개")
            issues.append(f"NULL content: {row['null_content']}개")
        else:
            print("  ✅ 모든 청크에 content가 있습니다.")
        
        if row['null_type'] > 0:
            print(f"  ⚠️  chunk_type이 NULL인 청크: {row['null_type']}개")
        else:
            print("  ✅ 모든 청크에 chunk_type이 있습니다.")
        
        # 4. 비정상적으로 짧은 청크
        self.print_section("비정상적으로 짧은 청크 검증")
        self.cur.execute("""
            SELECT chunk_id, content_length, content
            FROM chunks
            WHERE content_length < 10 AND drop = FALSE
            LIMIT 10
        """)
        short_chunks = self.cur.fetchall()
        
        if short_chunks:
            print(f"  ⚠️  10자 미만 청크: {len(short_chunks)}개")
            for row in short_chunks[:3]:
                print(f"    - {row['chunk_id']}: {row['content_length']}자")
                print(f"      내용: {row['content']}")
            issues.append(f"짧은 청크: {len(short_chunks)}개")
        else:
            print("  ✅ 비정상적으로 짧은 청크가 없습니다.")
        
        # 5. 비정상적으로 긴 청크
        self.print_section("비정상적으로 긴 청크 검증")
        self.cur.execute("""
            SELECT chunk_id, content_length
            FROM chunks
            WHERE content_length > 5000 AND drop = FALSE
            LIMIT 10
        """)
        long_chunks = self.cur.fetchall()
        
        if long_chunks:
            print(f"  ⚠️  5000자 초과 청크: {len(long_chunks)}개")
            for row in long_chunks[:5]:
                print(f"    - {row['chunk_id']}: {row['content_length']:,}자")
            issues.append(f"긴 청크: {len(long_chunks)}개")
        else:
            print("  ✅ 비정상적으로 긴 청크가 없습니다.")
        
        # 검증 요약
        self.print_section("검증 요약")
        if issues:
            print(f"  ⚠️  발견된 이슈: {len(issues)}개")
            for issue in issues:
                print(f"    - {issue}")
        else:
            print("  ✅ 모든 검증 통과!")
    
    def show_category_distribution(self):
        """카테고리별 분포"""
        self.print_header("카테고리별 분포 (상위 20개)")
        
        self.cur.execute("""
            SELECT 
                category_path,
                COUNT(*) as count
            FROM documents
            WHERE category_path IS NOT NULL AND array_length(category_path, 1) > 0
            GROUP BY category_path
            ORDER BY count DESC
            LIMIT 20
        """)
        
        print(f"\n{'카테고리 경로':<60} {'문서 수':>10}")
        print("-" * 80)
        
        for row in self.cur.fetchall():
            path = ' > '.join(row['category_path'])
            print(f"{path:<60} {row['count']:>10,}")
    
    def close(self):
        """연결 종료"""
        self.cur.close()
        self.conn.close()

def main():
    """메인 함수"""
    visualizer = TransformationVisualizer()
    
    try:
        # 1. 전체 통계
        visualizer.show_overall_statistics()
        
        # 2. 문서 유형별 분포
        visualizer.show_distribution_by_doc_type()
        
        # 3. 출처별 분포
        visualizer.show_distribution_by_source()
        
        # 4. 카테고리별 분포
        visualizer.show_category_distribution()
        
        # 5. 샘플 데이터 (각 유형별)
        visualizer.show_sample_data(doc_type='law', limit=1)
        visualizer.show_sample_data(doc_type='criteria_resolution', limit=1)
        visualizer.show_sample_data(doc_type='mediation_case', limit=1)
        visualizer.show_sample_data(doc_type='counsel_case', limit=1)
        
        # 6. 데이터 검증
        visualizer.validate_data()
        
        # 완료 메시지
        visualizer.print_header("시각화 완료")
        print("\n데이터 변환 결과 시각화가 완료되었습니다.")
        print("이슈가 발견된 경우 데이터 변환 스크립트를 수정하세요.\n")
        
    finally:
        visualizer.close()

if __name__ == '__main__':
    main()
