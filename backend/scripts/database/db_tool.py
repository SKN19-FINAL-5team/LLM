#!/usr/bin/env python3
"""
데이터베이스 통합 도구
DB 상태 확인, 통계 수집, 연결 테스트, 메타데이터 확인, Vector DB 검사 기능을 통합

사용법:
    python backend/scripts/database/db_tool.py --status
    python backend/scripts/database/db_tool.py --stats
    python backend/scripts/database/db_tool.py --check-law
    python backend/scripts/database/db_tool.py --test-connection
    python backend/scripts/database/db_tool.py --inspect
    python backend/scripts/database/db_tool.py --inspect --check-quality
    python backend/scripts/database/db_tool.py --all
"""

import os
import sys
import json
import psycopg2
import numpy as np
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

# 환경 변수 로드
backend_dir = Path(__file__).parent.parent.parent
env_file = backend_dir / '.env'
if env_file.exists():
    load_dotenv(env_file)
else:
    root_env = backend_dir.parent / '.env'
    if root_env.exists():
        load_dotenv(root_env)
    else:
        load_dotenv()

# DB 연결 정보 (여러 환경 변수 이름 지원)
DB_CONFIG = {
    'host': os.getenv('DB_HOST', os.getenv('POSTGRES_HOST', 'localhost')),
    'port': int(os.getenv('DB_PORT', os.getenv('POSTGRES_PORT', 5432))),
    'database': os.getenv('DB_NAME', os.getenv('POSTGRES_DB', 'ddoksori')),
    'user': os.getenv('DB_USER', os.getenv('POSTGRES_USER', 'postgres')),
    'password': os.getenv('DB_PASSWORD', os.getenv('POSTGRES_PASSWORD', 'postgres'))
}


class DatabaseTool:
    """데이터베이스 통합 도구"""
    
    def __init__(self):
        self.conn = None
        self._connect()
    
    def _connect(self):
        """데이터베이스 연결"""
        try:
            self.conn = psycopg2.connect(**DB_CONFIG)
            # pgvector 타입 등록
            try:
                from pgvector.psycopg2 import register_vector
                register_vector(self.conn)
            except ImportError:
                pass  # pgvector가 없어도 기본 기능은 동작
        except Exception as e:
            print(f"❌ 데이터베이스 연결 실패: {e}")
            raise
    
    def check_status(self):
        """데이터베이스 상태 확인 (기존 check_db_status.py 기능)"""
        cur = self.conn.cursor()
        
        print("=" * 60)
        print("데이터베이스 상태 확인")
        print("=" * 60)
        
        # 1. documents 테이블 통계
        print("\n📊 Documents 테이블 통계:")
        cur.execute("""
            SELECT 
                doc_type,
                COUNT(*) as count,
                COUNT(CASE WHEN keywords IS NOT NULL THEN 1 END) as with_keywords,
                COUNT(CASE WHEN search_vector IS NOT NULL THEN 1 END) as with_search_vector
            FROM documents
            GROUP BY doc_type
            ORDER BY doc_type
        """)
        
        print("\n{:<30} {:>10} {:>15} {:>20}".format(
            "Doc Type", "Count", "With Keywords", "With Search Vector"
        ))
        print("-" * 80)
        
        total_docs = 0
        for row in cur.fetchall():
            doc_type, count, with_keywords, with_search_vector = row
            total_docs += count
            print("{:<30} {:>10} {:>15} {:>20}".format(
                doc_type or '(NULL)',
                count,
                with_keywords,
                with_search_vector
            ))
        
        print("-" * 80)
        print(f"총 문서 수: {total_docs:,}")
        
        # 2. chunks 테이블 통계
        print("\n📊 Chunks 테이블 통계:")
        cur.execute("""
            SELECT 
                d.doc_type,
                COUNT(*) as chunk_count,
                COUNT(CASE WHEN c.embedding IS NOT NULL THEN 1 END) as with_embedding,
                COUNT(CASE WHEN c.importance_score IS NOT NULL THEN 1 END) as with_importance,
                COUNT(CASE WHEN c.drop = TRUE THEN 1 END) as dropped
            FROM chunks c
            JOIN documents d ON c.doc_id = d.doc_id
            GROUP BY d.doc_type
            ORDER BY d.doc_type
        """)
        
        print("\n{:<30} {:>12} {:>18} {:>18} {:>10}".format(
            "Doc Type", "Chunks", "With Embedding", "With Importance", "Dropped"
        ))
        print("-" * 90)
        
        total_chunks = 0
        for row in cur.fetchall():
            doc_type, chunk_count, with_embedding, with_importance, dropped = row
            total_chunks += chunk_count
            print("{:<30} {:>12} {:>18} {:>18} {:>10}".format(
                doc_type or '(NULL)',
                chunk_count,
                with_embedding,
                with_importance,
                dropped
            ))
        
        print("-" * 90)
        print(f"총 청크 수: {total_chunks:,}")
        
        # 3. 법령 데이터 상세 확인
        print("\n📚 법령 데이터 상세:")
        cur.execute("""
            SELECT 
                d.doc_id,
                d.title,
                COUNT(c.chunk_id) as chunk_count,
                d.keywords
            FROM documents d
            LEFT JOIN chunks c ON d.doc_id = c.doc_id
            WHERE d.doc_type = 'law'
            GROUP BY d.doc_id, d.title, d.keywords
            ORDER BY d.title
            LIMIT 10
        """)
        
        law_docs = cur.fetchall()
        if law_docs:
            for doc_id, title, chunk_count, keywords in law_docs:
                print(f"\n  • {title}")
                print(f"    - doc_id: {doc_id}")
                print(f"    - chunks: {chunk_count}")
                kw_display = keywords[:5] if keywords else ["(없음)"]
                print(f"    - keywords: {kw_display}...")
        else:
            print("\n  ⚠️  법령 문서가 없습니다!")
        
        # 4. 민법 제750조 검색
        print("\n🔍 민법 제750조 검색:")
        cur.execute("""
            SELECT 
                c.chunk_id,
                c.content,
                d.title,
                d.metadata
            FROM chunks c
            JOIN documents d ON c.doc_id = d.doc_id
            WHERE 
                d.doc_type = 'law'
                AND (
                    d.title ILIKE '%민법%'
                    OR d.metadata->>'law_name' ILIKE '%민법%'
                )
                AND (
                    c.content ILIKE '%제750조%'
                    OR c.content ILIKE '%750조%'
                    OR d.metadata->>'article_no' ILIKE '%750%'
                )
            LIMIT 5
        """)
        
        results = cur.fetchall()
        if results:
            for chunk_id, content, title, metadata in results:
                print(f"\n  ✅ 찾음: {chunk_id}")
                print(f"     제목: {title}")
                print(f"     내용: {content[:100]}...")
        else:
            print("\n  ⚠️  민법 제750조를 찾을 수 없습니다!")
            
            # 민법 데이터가 있는지 확인
            cur.execute("""
                SELECT COUNT(*)
                FROM documents
                WHERE doc_type = 'law' AND title ILIKE '%민법%'
            """)
            count = cur.fetchone()[0]
            print(f"\n  민법 문서 수: {count}")
            
            if count > 0:
                cur.execute("""
                    SELECT 
                        d.doc_id,
                        d.title,
                        COUNT(c.chunk_id) as chunk_count
                    FROM documents d
                    LEFT JOIN chunks c ON d.doc_id = c.doc_id
                    WHERE d.doc_type = 'law' AND d.title ILIKE '%민법%'
                    GROUP BY d.doc_id, d.title
                """)
                for doc_id, title, chunk_count in cur.fetchall():
                    print(f"    - {title}: {chunk_count}개 청크")
        
        # 5. 테이블 스키마 확인
        print("\n📋 테이블 컬럼 확인:")
        
        # documents 테이블
        cur.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'documents'
            ORDER BY ordinal_position
        """)
        print("\n  documents 테이블:")
        for col_name, data_type in cur.fetchall():
            print(f"    - {col_name}: {data_type}")
        
        # chunks 테이블
        cur.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'chunks'
            ORDER BY ordinal_position
        """)
        print("\n  chunks 테이블:")
        for col_name, data_type in cur.fetchall():
            print(f"    - {col_name}: {data_type}")
        
        print("\n" + "=" * 60)
        print("✅ 확인 완료")
        print("=" * 60)
        
        cur.close()
    
    def get_stats(self, format='json'):
        """통계 수집 및 출력 (기존 get_db_stats.py 기능)"""
        cur = self.conn.cursor()
        
        try:
            # Get statistics from view (if exists)
            try:
                cur.execute('SELECT * FROM v_data_statistics ORDER BY doc_type, source_org')
                stats = cur.fetchall()
                
                stats_list = []
                for row in stats:
                    doc_type, source_org, doc_count, chunk_count, active_count, avg_len, embedded_count = row
                    stats_list.append({
                        'doc_type': doc_type,
                        'source_org': source_org,
                        'document_count': doc_count,
                        'chunk_count': chunk_count,
                        'active_chunk_count': active_count,
                        'avg_chunk_length': float(avg_len) if avg_len else 0,
                        'embedded_chunk_count': embedded_count
                    })
            except:
                stats_list = []
            
            # Get total counts
            cur.execute('SELECT COUNT(*) FROM documents')
            total_docs = cur.fetchone()[0]
            
            cur.execute('SELECT COUNT(*) FROM chunks WHERE drop=FALSE')
            total_chunks = cur.fetchone()[0]
            
            cur.execute('SELECT COUNT(*) FROM chunks WHERE drop=FALSE AND embedding IS NOT NULL')
            embedded_chunks = cur.fetchone()[0]
            
            # Get doc_type counts
            cur.execute('''
                SELECT doc_type, COUNT(*) 
                FROM documents 
                GROUP BY doc_type 
                ORDER BY doc_type
            ''')
            doc_type_counts = {row[0]: row[1] for row in cur.fetchall()}
            
            result = {
                'total_documents': total_docs,
                'total_active_chunks': total_chunks,
                'total_embedded_chunks': embedded_chunks,
                'embedding_coverage_percent': round(embedded_chunks/total_chunks*100, 2) if total_chunks > 0 else 0,
                'doc_type_counts': doc_type_counts,
                'detailed_stats': stats_list
            }
            
            if format == 'json':
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                print(f"총 문서: {total_docs:,}개")
                print(f"총 청크: {total_chunks:,}개")
                print(f"임베딩된 청크: {embedded_chunks:,}개 ({result['embedding_coverage_percent']}%)")
                print(f"\n문서 유형별:")
                for doc_type, count in doc_type_counts.items():
                    print(f"  {doc_type}: {count:,}개")
            
            return result
            
        except Exception as e:
            error_result = {'error': str(e)}
            if format == 'json':
                print(json.dumps(error_result, ensure_ascii=False))
            else:
                print(f"❌ 오류: {e}")
            return error_result
        finally:
            cur.close()
    
    def check_law_metadata(self):
        """법령 메타데이터 확인 (기존 check_law_metadata.py 기능)"""
        cur = self.conn.cursor()
        
        print("=" * 80)
        print("법령 데이터 메타데이터 구조 확인")
        print("=" * 80)
        
        # 1. documents 테이블의 민법 메타데이터
        print("\n📚 Documents 테이블 - 민법:")
        cur.execute("""
            SELECT doc_id, title, metadata
            FROM documents
            WHERE doc_type = 'law' AND title ILIKE '%민법%'
            LIMIT 1
        """)
        
        row = cur.fetchone()
        if row:
            doc_id, title, metadata = row
            print(f"\n  doc_id: {doc_id}")
            print(f"  title: {title}")
            print(f"\n  metadata:")
            if metadata:
                print(json.dumps(metadata, indent=4, ensure_ascii=False))
            else:
                print("    (NULL)")
        
        # 2. chunks 테이블의 750조 관련 청크
        print("\n\n📄 Chunks 테이블 - 제750조:")
        cur.execute("""
            SELECT 
                c.chunk_id,
                c.chunk_type,
                c.content,
                d.metadata
            FROM chunks c
            JOIN documents d ON c.doc_id = d.doc_id
            WHERE 
                d.doc_type = 'law'
                AND d.title ILIKE '%민법%'
                AND c.content ILIKE '%750조%'
            LIMIT 3
        """)
        
        rows = cur.fetchall()
        for i, row in enumerate(rows, 1):
            chunk_id, chunk_type, content, doc_metadata = row
            print(f"\n{i}. chunk_id: {chunk_id}")
            print(f"   chunk_type: {chunk_type}")
            print(f"   content (첫 200자):\n   {content[:200]}...")
            print(f"\n   document metadata:")
            if doc_metadata:
                print(json.dumps(doc_metadata, indent=4, ensure_ascii=False))
        
        # 3. chunk_id 패턴 분석
        print("\n\n🔍 Chunk ID 패턴 분석:")
        cur.execute("""
            SELECT 
                chunk_id,
                chunk_type,
                LEFT(content, 100) as content_preview
            FROM chunks c
            JOIN documents d ON c.doc_id = d.doc_id
            WHERE d.doc_type = 'law' AND d.title ILIKE '%민법%'
            ORDER BY c.chunk_index
            LIMIT 10
        """)
        
        rows = cur.fetchall()
        for chunk_id, chunk_type, preview in rows:
            print(f"\n  {chunk_id}")
            print(f"    type: {chunk_type}")
            print(f"    preview: {preview}...")
        
        # 4. 원본 JSONL 파일 샘플 확인
        print("\n\n📁 원본 JSONL 파일 샘플:")
        jsonl_path = backend_dir / "data" / "law" / "Civil_Law_chunks.jsonl"
        
        try:
            if jsonl_path.exists():
                with open(jsonl_path, 'r', encoding='utf-8') as f:
                    # 750조 관련 라인 찾기
                    for line in f:
                        data = json.loads(line)
                        if '750조' in data.get('index_text', '') or data.get('article_no') == '제750조':
                            print("\n  ✅ 찾음:")
                            print(json.dumps(data, indent=4, ensure_ascii=False))
                            break
            else:
                print(f"\n  ⚠️  파일을 찾을 수 없습니다: {jsonl_path}")
        except Exception as e:
            print(f"\n  ⚠️  파일 읽기 오류: {e}")
        
        print("\n" + "=" * 80)
        print("✅ 확인 완료")
        print("=" * 80)
        
        cur.close()
    
    def test_connection(self):
        """데이터베이스 연결 테스트 (기존 test_db_connection.py 기능)"""
        print("=" * 80)
        print("Docker DB 연결 테스트")
        print("=" * 80)
        
        # 환경 변수 확인
        print("\n📋 환경 변수 확인:")
        print(f"  DB_HOST: {DB_CONFIG['host']}")
        print(f"  DB_PORT: {DB_CONFIG['port']}")
        print(f"  DB_NAME: {DB_CONFIG['database']}")
        print(f"  DB_USER: {DB_CONFIG['user']}")
        print(f"  DB_PASSWORD: {'*' * len(DB_CONFIG['password']) if DB_CONFIG['password'] else '(empty)'}")
        
        # 연결 확인
        print("\n🔌 데이터베이스 연결 확인...")
        if self.conn:
            print("✅ 데이터베이스 연결 성공!")
            
            cur = self.conn.cursor()
            
            # pgvector 확장 확인
            print("\n📦 pgvector 확장 확인...")
            cur.execute("SELECT * FROM pg_extension WHERE extname = 'vector';")
            if cur.fetchone():
                print("✅ pgvector 확장 설치됨")
            else:
                print("⚠️  pgvector 확장이 설치되지 않았습니다.")
            
            # 테이블 존재 확인
            print("\n📊 테이블 존재 확인...")
            tables = ['documents', 'chunks']
            for table in tables:
                cur.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = %s
                    );
                """, (table,))
                exists = cur.fetchone()[0]
                if exists:
                    print(f"  ✅ {table} 테이블 존재")
                else:
                    print(f"  ❌ {table} 테이블 없음")
            
            # documents 테이블 통계
            print("\n📈 Documents 테이블 통계:")
            cur.execute("""
                SELECT 
                    doc_type,
                    COUNT(*) as count
                FROM documents
                GROUP BY doc_type
                ORDER BY doc_type;
            """)
            rows = cur.fetchall()
            if rows:
                total = 0
                for doc_type, count in rows:
                    print(f"  {doc_type or '(NULL)'}: {count:,}개")
                    total += count
                print(f"  총 문서 수: {total:,}개")
            else:
                print("  ⚠️  문서가 없습니다.")
            
            # chunks 테이블 통계
            print("\n📈 Chunks 테이블 통계:")
            cur.execute("""
                SELECT 
                    d.doc_type,
                    COUNT(*) as chunk_count,
                    COUNT(CASE WHEN c.embedding IS NOT NULL THEN 1 END) as with_embedding
                FROM chunks c
                JOIN documents d ON c.doc_id = d.doc_id
                GROUP BY d.doc_type
                ORDER BY d.doc_type;
            """)
            rows = cur.fetchall()
            if rows:
                total_chunks = 0
                for doc_type, chunk_count, with_embedding in rows:
                    print(f"  {doc_type or '(NULL)'}: {chunk_count:,}개 (임베딩: {with_embedding:,}개)")
                    total_chunks += chunk_count
                print(f"  총 청크 수: {total_chunks:,}개")
            else:
                print("  ⚠️  청크가 없습니다.")
            
            # 샘플 데이터 조회
            print("\n🔍 샘플 데이터 조회:")
            
            # 법령 샘플
            cur.execute("""
                SELECT d.doc_id, d.doc_type, d.metadata->>'law_name' as law_name, c.content
                FROM documents d
                JOIN chunks c ON d.doc_id = c.doc_id
                WHERE d.doc_type = 'law'
                LIMIT 1;
            """)
            law_sample = cur.fetchone()
            if law_sample:
                print("  ✅ 법령 샘플:")
                print(f"    - 법령명: {law_sample[2]}")
                print(f"    - 내용: {law_sample[3][:100]}...")
            else:
                print("  ⚠️  법령 데이터 없음")
            
            # 기준 샘플
            cur.execute("""
                SELECT d.doc_id, d.doc_type, d.metadata->>'item' as item, c.content
                FROM documents d
                JOIN chunks c ON d.doc_id = c.doc_id
                WHERE d.doc_type LIKE 'criteria%%'
                LIMIT 1;
            """)
            criteria_sample = cur.fetchone()
            if criteria_sample:
                print("  ✅ 기준 샘플:")
                print(f"    - 품목: {criteria_sample[2]}")
                print(f"    - 내용: {criteria_sample[3][:100]}...")
            else:
                print("  ⚠️  기준 데이터 없음")
            
            # Full-Text Search 테스트
            print("\n🔎 Full-Text Search 기능 테스트...")
            test_query = "민법"
            cur.execute("""
                SELECT 
                    c.chunk_id,
                    c.content,
                    ts_rank_cd(
                        to_tsvector('simple', c.content),
                        plainto_tsquery('simple', %s)
                    ) AS rank
                FROM chunks c
                JOIN documents d ON c.doc_id = d.doc_id
                WHERE 
                    d.doc_type = 'law'
                    AND to_tsvector('simple', c.content) @@ plainto_tsquery('simple', %s)
                ORDER BY rank DESC
                LIMIT 1;
            """, (test_query, test_query))
            fts_result = cur.fetchone()
            if fts_result:
                print(f"  ✅ Full-Text Search 정상 동작")
                print(f"    - 검색어: '{test_query}'")
                print(f"    - 매칭된 내용: {fts_result[1][:100]}...")
            else:
                print(f"  ⚠️  '{test_query}' 검색 결과 없음")
            
            cur.close()
            
            print("\n" + "=" * 80)
            print("✅ 모든 테스트 완료!")
            print("=" * 80)
            return True
        else:
            print("❌ 데이터베이스 연결 실패")
            return False
    
    def inspect_vectordb(self, export_samples=False, check_quality=False):
        """Vector DB 상세 검사 (기존 inspect_vectordb.py 기능)"""
        cur = self.conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            # 전체 개요
            print("=" * 80)
            print("📊 Vector DB 개요")
            print("=" * 80)
            
            cur.execute("""
                SELECT 
                    COUNT(DISTINCT d.doc_id) as total_docs,
                    COUNT(c.chunk_id) as total_chunks,
                    COUNT(c.embedding) as embedded_chunks,
                    COUNT(CASE WHEN c.drop = TRUE THEN 1 END) as dropped_chunks,
                    AVG(c.content_length) as avg_chunk_length,
                    MIN(c.content_length) as min_chunk_length,
                    MAX(c.content_length) as max_chunk_length
                FROM documents d
                LEFT JOIN chunks c ON d.doc_id = c.doc_id
            """)
            stats = cur.fetchone()
            
            print(f"\n📄 문서 및 청크 통계:")
            print(f"  총 문서:           {stats['total_docs']:,}개")
            print(f"  총 청크:           {stats['total_chunks']:,}개")
            print(f"  임베딩된 청크:     {stats['embedded_chunks']:,}개")
            print(f"  제외된 청크:       {stats['dropped_chunks']:,}개")
            
            if stats['total_chunks'] > 0:
                embed_rate = (stats['embedded_chunks'] / stats['total_chunks']) * 100
                print(f"  임베딩 완료율:     {embed_rate:.2f}%")
            
            print(f"\n📏 청크 길이 통계:")
            print(f"  평균:             {stats['avg_chunk_length']:.0f}자")
            print(f"  최소:             {stats['min_chunk_length']:,}자")
            print(f"  최대:             {stats['max_chunk_length']:,}자")
            
            # 벡터 차원 확인
            try:
                cur.execute("""
                    SELECT embedding
                    FROM chunks
                    WHERE embedding IS NOT NULL
                    LIMIT 1
                """)
                result = cur.fetchone()
                if result:
                    embedding = result['embedding']
                    if hasattr(embedding, '__len__'):
                        dimension = len(embedding)
                    else:
                        dimension = 1024
                    
                    print(f"\n🔢 벡터 정보:")
                    print(f"  차원:             {dimension}")
                    print(f"  모델:             KURE-v1 (Korean Universal Representation)")
            except Exception as e:
                print(f"\n⚠️  벡터 차원 확인 실패: {e}")
            
            # 데이터 분포 통계
            print("\n" + "=" * 80)
            print("📈 데이터 분포 통계")
            print("=" * 80)
            
            # 문서 유형별
            print("\n📁 문서 유형별 분포:")
            cur.execute("""
                SELECT 
                    doc_type,
                    COUNT(DISTINCT d.doc_id) as doc_count,
                    COUNT(c.chunk_id) as chunk_count,
                    COUNT(c.embedding) as embedded_count
                FROM documents d
                LEFT JOIN chunks c ON d.doc_id = c.doc_id
                GROUP BY doc_type
                ORDER BY doc_count DESC
            """)
            
            print(f"{'문서 유형':<25} {'문서 수':>12} {'청크 수':>12} {'임베딩':>12}")
            print("-" * 80)
            for row in cur.fetchall():
                print(f"{row['doc_type']:<25} {row['doc_count']:>12,} {row['chunk_count']:>12,} {row['embedded_count']:>12,}")
            
            # 청크 타입별
            print("\n🏷️  청크 타입별 분포:")
            cur.execute("""
                SELECT 
                    chunk_type,
                    COUNT(*) as count,
                    AVG(content_length) as avg_length,
                    COUNT(embedding) as embedded_count
                FROM chunks
                WHERE drop = FALSE
                GROUP BY chunk_type
                ORDER BY count DESC
            """)
            
            print(f"{'청크 타입':<25} {'개수':>12} {'평균 길이':>12} {'임베딩':>12}")
            print("-" * 80)
            for row in cur.fetchall():
                print(f"{row['chunk_type']:<25} {row['count']:>12,} {row['avg_length']:>11.0f}자 {row['embedded_count']:>12,}")
            
            # 출처별
            print("\n🏢 출처별 분포:")
            cur.execute("""
                SELECT 
                    source_org,
                    COUNT(DISTINCT d.doc_id) as doc_count,
                    COUNT(c.chunk_id) as chunk_count
                FROM documents d
                LEFT JOIN chunks c ON d.doc_id = c.doc_id
                GROUP BY source_org
                ORDER BY doc_count DESC
            """)
            
            print(f"{'출처':<25} {'문서 수':>12} {'청크 수':>12}")
            print("-" * 80)
            for row in cur.fetchall():
                source = row['source_org'] or '(null)'
                print(f"{source:<25} {row['doc_count']:>12,} {row['chunk_count']:>12,}")
            
            # 저장소 정보
            print("\n" + "=" * 80)
            print("💾 저장소 정보")
            print("=" * 80)
            
            cur.execute("""
                SELECT 
                    pg_size_pretty(pg_total_relation_size('documents')) as documents_size,
                    pg_size_pretty(pg_total_relation_size('chunks')) as chunks_size,
                    pg_size_pretty(pg_database_size(current_database())) as total_db_size
            """)
            sizes = cur.fetchone()
            
            print(f"\n📊 테이블 크기:")
            print(f"  documents:        {sizes['documents_size']}")
            print(f"  chunks:           {sizes['chunks_size']}")
            print(f"  전체 DB:          {sizes['total_db_size']}")
            
            # 인덱스 정보
            cur.execute("""
                SELECT 
                    indexrelname as indexname,
                    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
                FROM pg_stat_user_indexes
                WHERE schemaname = 'public'
                ORDER BY pg_relation_size(indexrelid) DESC
            """)
            
            print(f"\n🔍 인덱스 크기:")
            for row in cur.fetchall():
                print(f"  {row['indexname']:<40} {row['index_size']}")
            
            # 임베딩 품질 분석
            if check_quality:
                print("\n" + "=" * 80)
                print("🔍 임베딩 품질 상세 분석")
                print("=" * 80)
                
                cur.execute("""
                    SELECT 
                        chunk_id,
                        chunk_type,
                        content_length,
                        embedding
                    FROM chunks
                    WHERE embedding IS NOT NULL AND drop = FALSE
                    ORDER BY RANDOM()
                    LIMIT 500
                """)
                
                samples = cur.fetchall()
                
                if not samples:
                    print("⚠️  임베딩된 청크가 없습니다.")
                else:
                    print(f"\n📊 분석 샘플: {len(samples)}개")
                    
                    quality_issues = defaultdict(list)
                    norm_values = []
                    variance_values = []
                    
                    for sample in samples:
                        embedding = sample['embedding']
                        
                        if isinstance(embedding, str):
                            embedding = embedding.strip('[]')
                            embedding = [float(x) for x in embedding.split(',')]
                        
                        vec = np.array(embedding, dtype=float)
                        
                        norm = np.linalg.norm(vec)
                        variance = np.var(vec)
                        
                        norm_values.append(norm)
                        variance_values.append(variance)
                        
                        if norm < 0.1:
                            quality_issues['low_norm'].append(sample['chunk_id'])
                        if variance < 0.001:
                            quality_issues['low_variance'].append(sample['chunk_id'])
                        if np.isnan(vec).any():
                            quality_issues['has_nan'].append(sample['chunk_id'])
                        if np.isinf(vec).any():
                            quality_issues['has_inf'].append(sample['chunk_id'])
                    
                    print(f"\n📈 벡터 품질 지표:")
                    print(f"  Norm 평균:        {np.mean(norm_values):.4f}")
                    print(f"  Norm 표준편차:    {np.std(norm_values):.4f}")
                    print(f"  Norm 범위:        {np.min(norm_values):.4f} ~ {np.max(norm_values):.4f}")
                    print(f"  Variance 평균:    {np.mean(variance_values):.6f}")
                    print(f"  Variance 범위:    {np.min(variance_values):.6f} ~ {np.max(variance_values):.6f}")
                    
                    print(f"\n⚠️  품질 이슈:")
                    if not any(quality_issues.values()):
                        print("  ✅ 품질 이슈 없음!")
                    else:
                        for issue_type, chunk_ids in quality_issues.items():
                            count = len(chunk_ids)
                            rate = (count / len(samples)) * 100
                            print(f"  {issue_type}: {count}개 ({rate:.2f}%)")
                            if chunk_ids[:3]:
                                print(f"    샘플: {', '.join(chunk_ids[:3])}")
            
            # 샘플 데이터 추출
            if export_samples:
                output_dir = Path("./vectordb_samples")
                output_dir.mkdir(exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                print("\n" + "=" * 80)
                print("📦 샘플 데이터 추출")
                print("=" * 80)
                print(f"출력 디렉토리: {output_dir}")
                
                cur.execute("""
                    SELECT DISTINCT chunk_type
                    FROM chunks
                    WHERE embedding IS NOT NULL AND drop = FALSE
                """)
                chunk_types = [row['chunk_type'] for row in cur.fetchall()]
                
                samples = {}
                for chunk_type in chunk_types:
                    cur.execute("""
                        SELECT 
                            c.chunk_id,
                            c.chunk_type,
                            c.content,
                            c.content_length,
                            d.doc_type,
                            d.title,
                            d.source_org
                        FROM chunks c
                        JOIN documents d ON c.doc_id = d.doc_id
                        WHERE c.chunk_type = %s AND c.embedding IS NOT NULL AND c.drop = FALSE
                        ORDER BY RANDOM()
                        LIMIT 10
                    """, (chunk_type,))
                    
                    samples[chunk_type] = [dict(row) for row in cur.fetchall()]
                
                output_file = output_dir / f"vectordb_samples_{timestamp}.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(samples, f, ensure_ascii=False, indent=2)
                
                print(f"✅ 샘플 데이터 저장 완료: {output_file}")
                print(f"   총 {len(chunk_types)}개 청크 타입, 각 10개씩 추출")
            
            print("\n" + "=" * 80)
            print("✅ 검사 완료!")
            print("=" * 80)
            
        finally:
            cur.close()
    
    def close(self):
        """연결 종료"""
        if self.conn:
            self.conn.close()


def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(
        description='데이터베이스 통합 도구',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python db_tool.py --status              # DB 상태 확인
  python db_tool.py --stats               # 통계 수집 (JSON)
  python db_tool.py --check-law           # 법령 메타데이터 확인
  python db_tool.py --test-connection     # 연결 테스트
  python db_tool.py --inspect             # Vector DB 검사
  python db_tool.py --inspect --check-quality  # Vector DB 검사 + 품질 분석
  python db_tool.py --inspect --export-samples # Vector DB 검사 + 샘플 추출
  python db_tool.py --all                 # 모든 체크 실행
        """
    )
    
    parser.add_argument('--status', action='store_true',
                       help='DB 상태 확인')
    parser.add_argument('--stats', action='store_true',
                       help='통계 수집 및 JSON 출력')
    parser.add_argument('--check-law', action='store_true',
                       help='법령 메타데이터 확인')
    parser.add_argument('--test-connection', action='store_true',
                       help='DB 연결 테스트')
    parser.add_argument('--inspect', action='store_true',
                       help='Vector DB 상세 검사')
    parser.add_argument('--check-quality', action='store_true',
                       help='임베딩 품질 상세 분석 (--inspect와 함께 사용)')
    parser.add_argument('--export-samples', action='store_true',
                       help='샘플 데이터 추출 (--inspect와 함께 사용)')
    parser.add_argument('--all', action='store_true',
                       help='모든 체크 실행')
    
    args = parser.parse_args()
    
    # 아무 옵션도 없으면 도움말 출력
    if not any([args.status, args.stats, args.check_law, args.test_connection, 
                args.inspect, args.all]):
        parser.print_help()
        return
    
    tool = DatabaseTool()
    
    try:
        if args.all:
            # 모든 체크 실행
            tool.test_connection()
            print("\n")
            tool.check_status()
            print("\n")
            tool.get_stats(format='text')
            print("\n")
            tool.check_law_metadata()
            print("\n")
            tool.inspect_vectordb()
        else:
            if args.status:
                tool.check_status()
            if args.stats:
                tool.get_stats()
            if args.check_law:
                tool.check_law_metadata()
            if args.test_connection:
                tool.test_connection()
            if args.inspect:
                tool.inspect_vectordb(
                    export_samples=args.export_samples,
                    check_quality=args.check_quality
                )
    
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        tool.close()


if __name__ == "__main__":
    main()
