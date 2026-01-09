#!/usr/bin/env python3
"""
  
DB  ,  ,  ,  , Vector DB   

:
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

#   
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

# DB   (    )
DB_CONFIG = {
    'host': os.getenv('DB_HOST', os.getenv('POSTGRES_HOST', 'localhost')),
    'port': int(os.getenv('DB_PORT', os.getenv('POSTGRES_PORT', 5432))),
    'database': os.getenv('DB_NAME', os.getenv('POSTGRES_DB', 'ddoksori')),
    'user': os.getenv('DB_USER', os.getenv('POSTGRES_USER', 'postgres')),
    'password': os.getenv('DB_PASSWORD', os.getenv('POSTGRES_PASSWORD', 'postgres'))
}


class DatabaseTool:
    """  """
    
    def __init__(self):
        self.conn = None
        self._connect()
    
    def _connect(self):
        """ """
        try:
            self.conn = psycopg2.connect(**DB_CONFIG)
            # pgvector  
            try:
                from pgvector.psycopg2 import register_vector
                register_vector(self.conn)
            except ImportError:
                pass  # pgvector    
        except Exception as e:
            print(f"   : {e}")
            raise
    
    def check_status(self):
        """   ( check_db_status.py )"""
        cur = self.conn.cursor()
        
        print("=" * 60)
        print("  ")
        print("=" * 60)
        
        # 1. documents  
        print("\n Documents  :")
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
        print(f"  : {total_docs:,}")
        
        # 2. chunks  
        print("\n Chunks  :")
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
        print(f"  : {total_chunks:,}")
        
        # 3.    
        print("\n   :")
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
                kw_display = keywords[:5] if keywords else ["()"]
                print(f"    - keywords: {kw_display}...")
        else:
            print("\n      !")
        
        # 4.  750 
        print("\n  750 :")
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
                    d.title ILIKE '%%'
                    OR d.metadata->>'law_name' ILIKE '%%'
                )
                AND (
                    c.content ILIKE '%750%'
                    OR c.content ILIKE '%750%'
                    OR d.metadata->>'article_no' ILIKE '%750%'
                )
            LIMIT 5
        """)
        
        results = cur.fetchall()
        if results:
            for chunk_id, content, title, metadata in results:
                print(f"\n   : {chunk_id}")
                print(f"     : {title}")
                print(f"     : {content[:100]}...")
        else:
            print("\n     750   !")
            
            #    
            cur.execute("""
                SELECT COUNT(*)
                FROM documents
                WHERE doc_type = 'law' AND title ILIKE '%%'
            """)
            count = cur.fetchone()[0]
            print(f"\n    : {count}")
            
            if count > 0:
                cur.execute("""
                    SELECT 
                        d.doc_id,
                        d.title,
                        COUNT(c.chunk_id) as chunk_count
                    FROM documents d
                    LEFT JOIN chunks c ON d.doc_id = c.doc_id
                    WHERE d.doc_type = 'law' AND d.title ILIKE '%%'
                    GROUP BY d.doc_id, d.title
                """)
                for doc_id, title, chunk_count in cur.fetchall():
                    print(f"    - {title}: {chunk_count} ")
        
        # 5.   
        print("\n   :")
        
        # documents 
        cur.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'documents'
            ORDER BY ordinal_position
        """)
        print("\n  documents :")
        for col_name, data_type in cur.fetchall():
            print(f"    - {col_name}: {data_type}")
        
        # chunks 
        cur.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'chunks'
            ORDER BY ordinal_position
        """)
        print("\n  chunks :")
        for col_name, data_type in cur.fetchall():
            print(f"    - {col_name}: {data_type}")
        
        print("\n" + "=" * 60)
        print("  ")
        print("=" * 60)
        
        cur.close()
    
    def get_stats(self, format='json'):
        """    ( get_db_stats.py )"""
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
                print(f" : {total_docs:,}")
                print(f" : {total_chunks:,}")
                print(f" : {embedded_chunks:,} ({result['embedding_coverage_percent']}%)")
                print(f"\n :")
                for doc_type, count in doc_type_counts.items():
                    print(f"  {doc_type}: {count:,}")
            
            return result
            
        except Exception as e:
            error_result = {'error': str(e)}
            if format == 'json':
                print(json.dumps(error_result, ensure_ascii=False))
            else:
                print(f" : {e}")
            return error_result
        finally:
            cur.close()
    
    def check_law_metadata(self):
        """   ( check_law_metadata.py )"""
        cur = self.conn.cursor()
        
        print("=" * 80)
        print("    ")
        print("=" * 80)
        
        # 1. documents   
        print("\n Documents  - :")
        cur.execute("""
            SELECT doc_id, title, metadata
            FROM documents
            WHERE doc_type = 'law' AND title ILIKE '%%'
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
        
        # 2. chunks  750  
        print("\n\n Chunks  - 750:")
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
                AND d.title ILIKE '%%'
                AND c.content ILIKE '%750%'
            LIMIT 3
        """)
        
        rows = cur.fetchall()
        for i, row in enumerate(rows, 1):
            chunk_id, chunk_type, content, doc_metadata = row
            print(f"\n{i}. chunk_id: {chunk_id}")
            print(f"   chunk_type: {chunk_type}")
            print(f"   content ( 200):\n   {content[:200]}...")
            print(f"\n   document metadata:")
            if doc_metadata:
                print(json.dumps(doc_metadata, indent=4, ensure_ascii=False))
        
        # 3. chunk_id  
        print("\n\n Chunk ID  :")
        cur.execute("""
            SELECT 
                chunk_id,
                chunk_type,
                LEFT(content, 100) as content_preview
            FROM chunks c
            JOIN documents d ON c.doc_id = d.doc_id
            WHERE d.doc_type = 'law' AND d.title ILIKE '%%'
            ORDER BY c.chunk_index
            LIMIT 10
        """)
        
        rows = cur.fetchall()
        for chunk_id, chunk_type, preview in rows:
            print(f"\n  {chunk_id}")
            print(f"    type: {chunk_type}")
            print(f"    preview: {preview}...")
        
        # 4.  JSONL   
        print("\n\n  JSONL  :")
        jsonl_path = backend_dir / "data" / "law" / "Civil_Law_chunks.jsonl"
        
        try:
            if jsonl_path.exists():
                with open(jsonl_path, 'r', encoding='utf-8') as f:
                    # 750   
                    for line in f:
                        data = json.loads(line)
                        if '750' in data.get('index_text', '') or data.get('article_no') == '750':
                            print("\n   :")
                            print(json.dumps(data, indent=4, ensure_ascii=False))
                            break
            else:
                print(f"\n       : {jsonl_path}")
        except Exception as e:
            print(f"\n      : {e}")
        
        print("\n" + "=" * 80)
        print("  ")
        print("=" * 80)
        
        cur.close()
    
    def test_connection(self):
        """   ( test_db_connection.py )"""
        print("=" * 80)
        print("Docker DB  ")
        print("=" * 80)
        
        #   
        print("\n   :")
        print(f"  DB_HOST: {DB_CONFIG['host']}")
        print(f"  DB_PORT: {DB_CONFIG['port']}")
        print(f"  DB_NAME: {DB_CONFIG['database']}")
        print(f"  DB_USER: {DB_CONFIG['user']}")
        print(f"  DB_PASSWORD: {'*' * len(DB_CONFIG['password']) if DB_CONFIG['password'] else '(empty)'}")
        
        #  
        print("\n   ...")
        if self.conn:
            print("   !")
            
            cur = self.conn.cursor()
            
            # pgvector  
            print("\n pgvector  ...")
            cur.execute("SELECT * FROM pg_extension WHERE extname = 'vector';")
            if cur.fetchone():
                print(" pgvector  ")
            else:
                print("  pgvector   .")
            
            #   
            print("\n   ...")
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
                    print(f"   {table}  ")
                else:
                    print(f"   {table}  ")
            
            # documents  
            print("\n Documents  :")
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
                    print(f"  {doc_type or '(NULL)'}: {count:,}")
                    total += count
                print(f"    : {total:,}")
            else:
                print("     .")
            
            # chunks  
            print("\n Chunks  :")
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
                    print(f"  {doc_type or '(NULL)'}: {chunk_count:,} (: {with_embedding:,})")
                    total_chunks += chunk_count
                print(f"    : {total_chunks:,}")
            else:
                print("     .")
            
            #   
            print("\n   :")
            
            #  
            cur.execute("""
                SELECT d.doc_id, d.doc_type, d.metadata->>'law_name' as law_name, c.content
                FROM documents d
                JOIN chunks c ON d.doc_id = c.doc_id
                WHERE d.doc_type = 'law'
                LIMIT 1;
            """)
            law_sample = cur.fetchone()
            if law_sample:
                print("    :")
                print(f"    - : {law_sample[2]}")
                print(f"    - : {law_sample[3][:100]}...")
            else:
                print("      ")
            
            #  
            cur.execute("""
                SELECT d.doc_id, d.doc_type, d.metadata->>'item' as item, c.content
                FROM documents d
                JOIN chunks c ON d.doc_id = c.doc_id
                WHERE d.doc_type LIKE 'criteria%%'
                LIMIT 1;
            """)
            criteria_sample = cur.fetchone()
            if criteria_sample:
                print("    :")
                print(f"    - : {criteria_sample[2]}")
                print(f"    - : {criteria_sample[3][:100]}...")
            else:
                print("      ")
            
            # Full-Text Search 
            print("\n Full-Text Search  ...")
            test_query = ""
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
                print(f"   Full-Text Search  ")
                print(f"    - : '{test_query}'")
                print(f"    -  : {fts_result[1][:100]}...")
            else:
                print(f"    '{test_query}'   ")
            
            cur.close()
            
            print("\n" + "=" * 80)
            print("   !")
            print("=" * 80)
            return True
        else:
            print("   ")
            return False
    
    def inspect_vectordb(self, export_samples=False, check_quality=False):
        """Vector DB   ( inspect_vectordb.py )"""
        cur = self.conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            #  
            print("=" * 80)
            print(" Vector DB ")
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
            
            print(f"\n    :")
            print(f"   :           {stats['total_docs']:,}")
            print(f"   :           {stats['total_chunks']:,}")
            print(f"   :     {stats['embedded_chunks']:,}")
            print(f"   :       {stats['dropped_chunks']:,}")
            
            if stats['total_chunks'] > 0:
                embed_rate = (stats['embedded_chunks'] / stats['total_chunks']) * 100
                print(f"   :     {embed_rate:.2f}%")
            
            print(f"\n   :")
            print(f"  :             {stats['avg_chunk_length']:.0f}")
            print(f"  :             {stats['min_chunk_length']:,}")
            print(f"  :             {stats['max_chunk_length']:,}")
            
            #   
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
                    
                    print(f"\n  :")
                    print(f"  :             {dimension}")
                    print(f"  :             KURE-v1 (Korean Universal Representation)")
            except Exception as e:
                print(f"\n     : {e}")
            
            #   
            print("\n" + "=" * 80)
            print("   ")
            print("=" * 80)
            
            #  
            print("\n   :")
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
            
            print(f"{' ':<25} {' ':>12} {' ':>12} {'':>12}")
            print("-" * 80)
            for row in cur.fetchall():
                print(f"{row['doc_type']:<25} {row['doc_count']:>12,} {row['chunk_count']:>12,} {row['embedded_count']:>12,}")
            
            #  
            print("\n    :")
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
            
            print(f"{' ':<25} {'':>12} {' ':>12} {'':>12}")
            print("-" * 80)
            for row in cur.fetchall():
                print(f"{row['chunk_type']:<25} {row['count']:>12,} {row['avg_length']:>11.0f} {row['embedded_count']:>12,}")
            
            # 
            print("\n  :")
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
            
            print(f"{'':<25} {' ':>12} {' ':>12}")
            print("-" * 80)
            for row in cur.fetchall():
                source = row['source_org'] or '(null)'
                print(f"{source:<25} {row['doc_count']:>12,} {row['chunk_count']:>12,}")
            
            #  
            print("\n" + "=" * 80)
            print("  ")
            print("=" * 80)
            
            cur.execute("""
                SELECT 
                    pg_size_pretty(pg_total_relation_size('documents')) as documents_size,
                    pg_size_pretty(pg_total_relation_size('chunks')) as chunks_size,
                    pg_size_pretty(pg_database_size(current_database())) as total_db_size
            """)
            sizes = cur.fetchone()
            
            print(f"\n  :")
            print(f"  documents:        {sizes['documents_size']}")
            print(f"  chunks:           {sizes['chunks_size']}")
            print(f"   DB:          {sizes['total_db_size']}")
            
            #  
            cur.execute("""
                SELECT 
                    indexrelname as indexname,
                    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
                FROM pg_stat_user_indexes
                WHERE schemaname = 'public'
                ORDER BY pg_relation_size(indexrelid) DESC
            """)
            
            print(f"\n  :")
            for row in cur.fetchall():
                print(f"  {row['indexname']:<40} {row['index_size']}")
            
            #   
            if check_quality:
                print("\n" + "=" * 80)
                print("    ")
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
                    print("    .")
                else:
                    print(f"\n  : {len(samples)}")
                    
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
                    
                    print(f"\n   :")
                    print(f"  Norm :        {np.mean(norm_values):.4f}")
                    print(f"  Norm :    {np.std(norm_values):.4f}")
                    print(f"  Norm :        {np.min(norm_values):.4f} ~ {np.max(norm_values):.4f}")
                    print(f"  Variance :    {np.mean(variance_values):.6f}")
                    print(f"  Variance :    {np.min(variance_values):.6f} ~ {np.max(variance_values):.6f}")
                    
                    print(f"\n   :")
                    if not any(quality_issues.values()):
                        print("     !")
                    else:
                        for issue_type, chunk_ids in quality_issues.items():
                            count = len(chunk_ids)
                            rate = (count / len(samples)) * 100
                            print(f"  {issue_type}: {count} ({rate:.2f}%)")
                            if chunk_ids[:3]:
                                print(f"    : {', '.join(chunk_ids[:3])}")
            
            #   
            if export_samples:
                output_dir = Path("./vectordb_samples")
                output_dir.mkdir(exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                print("\n" + "=" * 80)
                print("   ")
                print("=" * 80)
                print(f" : {output_dir}")
                
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
                
                print(f"    : {output_file}")
                print(f"    {len(chunk_types)}  ,  10 ")
            
            print("\n" + "=" * 80)
            print("  !")
            print("=" * 80)
            
        finally:
            cur.close()
    
    def close(self):
        """ """
        if self.conn:
            self.conn.close()


def main():
    """  """
    parser = argparse.ArgumentParser(
        description='  ',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
 :
  python db_tool.py --status              # DB  
  python db_tool.py --stats               #   (JSON)
  python db_tool.py --check-law           #   
  python db_tool.py --test-connection     #  
  python db_tool.py --inspect             # Vector DB 
  python db_tool.py --inspect --check-quality  # Vector DB  +  
  python db_tool.py --inspect --export-samples # Vector DB  +  
  python db_tool.py --all                 #   
        """
    )
    
    parser.add_argument('--status', action='store_true',
                       help='DB  ')
    parser.add_argument('--stats', action='store_true',
                       help='   JSON ')
    parser.add_argument('--check-law', action='store_true',
                       help='  ')
    parser.add_argument('--test-connection', action='store_true',
                       help='DB  ')
    parser.add_argument('--inspect', action='store_true',
                       help='Vector DB  ')
    parser.add_argument('--check-quality', action='store_true',
                       help='    (--inspect  )')
    parser.add_argument('--export-samples', action='store_true',
                       help='   (--inspect  )')
    parser.add_argument('--all', action='store_true',
                       help='  ')
    
    args = parser.parse_args()
    
    #     
    if not any([args.status, args.stats, args.check_law, args.test_connection, 
                args.inspect, args.all]):
        parser.print_help()
        return
    
    tool = DatabaseTool()
    
    try:
        if args.all:
            #   
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
        print(f"\n  : {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        tool.close()


if __name__ == "__main__":
    main()
