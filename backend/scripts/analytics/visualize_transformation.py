#!/usr/bin/env python3
"""
    

     .
-  
- / 
-  
-  

Usage:
    python visualize_transformation.py
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv
from typing import Dict, List
import json

#   
load_dotenv()

class TransformationVisualizer:
    """   """
    
    def __init__(self):
        """  """
        self.conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5432'),
            database=os.getenv('DB_NAME', 'ddoksori'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', 'postgres')
        )
        self.cur = self.conn.cursor(cursor_factory=RealDictCursor)
    
    def print_header(self, title: str):
        """ """
        print("\n" + "=" * 80)
        print(title.center(80))
        print("=" * 80)
    
    def print_section(self, title: str):
        """  """
        print("\n" + "-" * 80)
        print(f"[{title}]")
        print("-" * 80)
    
    def show_overall_statistics(self):
        """  """
        self.print_header("   ")
        
        # 1.  
        self.print_section(" ")
        self.cur.execute("SELECT COUNT(*) as total FROM documents")
        total_docs = self.cur.fetchone()['total']
        print(f"    : {total_docs:,}")
        
        #  
        print("\n   :")
        self.cur.execute("""
            SELECT doc_type, COUNT(*) as count
            FROM documents
            GROUP BY doc_type
            ORDER BY count DESC
        """)
        for row in self.cur.fetchall():
            print(f"    - {row['doc_type']:<25} {row['count']:>10,}")
        
        # 2.  
        self.print_section(" ")
        self.cur.execute("SELECT COUNT(*) as total FROM chunks")
        total_chunks = self.cur.fetchone()['total']
        print(f"    : {total_chunks:,}")
        
        # / 
        self.cur.execute("""
            SELECT 
                COUNT(CASE WHEN drop = FALSE THEN 1 END) as active,
                COUNT(CASE WHEN drop = TRUE THEN 1 END) as dropped
            FROM chunks
        """)
        row = self.cur.fetchone()
        print(f"    -  : {row['active']:,}")
        print(f"    -  : {row['dropped']:,}")
        
        #  
        print("\n   :")
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
            print(f"    - {chunk_type:<25} {row['count']:>10,}")
        
        # 3.   
        self.print_section("  ")
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
        print(f"  -  : {row['min_length']:,}")
        print(f"  -  : {row['avg_length']:.0f}")
        print(f"  - : {row['median_length']:.0f}")
        print(f"  -  : {row['max_length']:,}")
        
        # 4.  
        self.print_section(" ")
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
            print(f"  - {source:<20} : {row['doc_count']:>6,}  |  : {row['chunk_count']:>10,}")
        
        # 5.  
        self.print_section(" ")
        self.cur.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN embedding IS NOT NULL THEN 1 END) as embedded,
                ROUND(COUNT(CASE WHEN embedding IS NOT NULL THEN 1 END)::numeric / COUNT(*) * 100, 2) as rate
            FROM chunks
            WHERE drop = FALSE
        """)
        row = self.cur.fetchone()
        print(f"  -   : {row['total']:,}")
        print(f"  -  : {row['embedded']:,}")
        print(f"  - : {row['rate']}%")
    
    def show_sample_data(self, doc_type: str = None, limit: int = 3):
        """  """
        self.print_header(f" {f' ({doc_type})' if doc_type else ''}")
        
        #   
        where_clause = f"WHERE doc_type = '{doc_type}'" if doc_type else ""
        
        #   
        self.cur.execute(f"""
            SELECT doc_id, doc_type, title, source_org, category_path
            FROM documents
            {where_clause}
            LIMIT {limit}
        """)
        
        for doc_idx, doc in enumerate(self.cur.fetchall(), 1):
            self.print_section(f" {doc_idx}: {doc['doc_id']}")
            print(f"  : {doc['title']}")
            print(f"  : {doc['doc_type']}")
            print(f"  : {doc['source_org']}")
            if doc['category_path']:
                print(f"  : {' > '.join(doc['category_path'])}")
            
            #    
            self.cur.execute("""
                SELECT chunk_id, chunk_index, chunk_type, content, content_length, drop
                FROM chunks
                WHERE doc_id = %s
                ORDER BY chunk_index
                LIMIT 5
            """, (doc['doc_id'],))
            
            chunks = self.cur.fetchall()
            print(f"\n   : {len(chunks)}")
            
            for chunk_idx, chunk in enumerate(chunks, 1):
                status = " []" if chunk['drop'] else ""
                print(f"\n  [ {chunk_idx}]{status} {chunk['chunk_id']}")
                print(f"    : {chunk['chunk_index']}")
                print(f"    : {chunk['chunk_type']}")
                print(f"    : {chunk['content_length']}")
                
                #   ( 200)
                content_preview = chunk['content'][:200].replace('\n', ' ')
                print(f"    : {content_preview}...")
    
    def show_distribution_by_doc_type(self):
        """  """
        self.print_header("  ")
        
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
        
        print(f"\n{' ':<25} {' ':>10} {' ':>12} {' ':>12}")
        print("-" * 80)
        
        for row in self.cur.fetchall():
            avg_len = row['avg_length'] if row['avg_length'] else 0
            print(f"{row['doc_type']:<25} {row['doc_count']:>10,} {row['chunk_count']:>12,} {avg_len:>11.0f}")
    
    def show_distribution_by_source(self):
        """ """
        self.print_header(" ")
        
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
        
        print(f"\n{'':<20} {' ':<25} {' ':>10} {' ':>12}")
        print("-" * 80)
        
        for row in self.cur.fetchall():
            source = row['source_org'] or '(NULL)'
            print(f"{source:<20} {row['doc_type']:<25} {row['doc_count']:>10,} {row['chunk_count']:>12,}")
    
    def validate_data(self):
        """ """
        self.print_header(" ")
        
        issues = []
        
        # 1.   
        self.print_section("  ")
        self.cur.execute("""
            SELECT doc_id, COUNT(*) as chunk_count, MAX(chunk_index) as max_index
            FROM chunks
            GROUP BY doc_id
            HAVING COUNT(*) != MAX(chunk_index) + 1
            LIMIT 10
        """)
        invalid_indices = self.cur.fetchall()
        
        if invalid_indices:
            print(f"      : {len(invalid_indices)} ")
            for row in invalid_indices[:5]:
                print(f"    - {row['doc_id']}:  ={row['chunk_count']},  ={row['max_index']}")
            issues.append(f"  : {len(invalid_indices)}")
        else:
            print("      .")
        
        # 2.  chunk_id 
        self.print_section(" chunk_id ")
        self.cur.execute("""
            SELECT chunk_id, COUNT(*) as count
            FROM chunks
            GROUP BY chunk_id
            HAVING COUNT(*) > 1
        """)
        duplicates = self.cur.fetchall()
        
        if duplicates:
            print(f"     chunk_id : {len(duplicates)}")
            for row in duplicates[:5]:
                print(f"    - {row['chunk_id']}: {row['count']} ")
            issues.append(f" chunk_id: {len(duplicates)}")
        else:
            print("    chunk_id .")
        
        # 3. NULL  
        self.print_section("  NULL ")
        self.cur.execute("""
            SELECT 
                COUNT(CASE WHEN content IS NULL THEN 1 END) as null_content,
                COUNT(CASE WHEN chunk_type IS NULL THEN 1 END) as null_type
            FROM chunks
        """)
        row = self.cur.fetchone()
        
        if row['null_content'] > 0:
            print(f"    content NULL : {row['null_content']}")
            issues.append(f"NULL content: {row['null_content']}")
        else:
            print("     content .")
        
        if row['null_type'] > 0:
            print(f"    chunk_type NULL : {row['null_type']}")
        else:
            print("     chunk_type .")
        
        # 4.   
        self.print_section("   ")
        self.cur.execute("""
            SELECT chunk_id, content_length, content
            FROM chunks
            WHERE content_length < 10 AND drop = FALSE
            LIMIT 10
        """)
        short_chunks = self.cur.fetchall()
        
        if short_chunks:
            print(f"    10  : {len(short_chunks)}")
            for row in short_chunks[:3]:
                print(f"    - {row['chunk_id']}: {row['content_length']}")
                print(f"      : {row['content']}")
            issues.append(f" : {len(short_chunks)}")
        else:
            print("      .")
        
        # 5.   
        self.print_section("   ")
        self.cur.execute("""
            SELECT chunk_id, content_length
            FROM chunks
            WHERE content_length > 5000 AND drop = FALSE
            LIMIT 10
        """)
        long_chunks = self.cur.fetchall()
        
        if long_chunks:
            print(f"    5000  : {len(long_chunks)}")
            for row in long_chunks[:5]:
                print(f"    - {row['chunk_id']}: {row['content_length']:,}")
            issues.append(f" : {len(long_chunks)}")
        else:
            print("      .")
        
        #  
        self.print_section(" ")
        if issues:
            print(f"     : {len(issues)}")
            for issue in issues:
                print(f"    - {issue}")
        else:
            print("     !")
    
    def show_category_distribution(self):
        """ """
        self.print_header("  ( 20)")
        
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
        
        print(f"\n{' ':<60} {' ':>10}")
        print("-" * 80)
        
        for row in self.cur.fetchall():
            path = ' > '.join(row['category_path'])
            print(f"{path:<60} {row['count']:>10,}")
    
    def close(self):
        """ """
        self.cur.close()
        self.conn.close()

def main():
    """ """
    visualizer = TransformationVisualizer()
    
    try:
        # 1.  
        visualizer.show_overall_statistics()
        
        # 2.   
        visualizer.show_distribution_by_doc_type()
        
        # 3.  
        visualizer.show_distribution_by_source()
        
        # 4.  
        visualizer.show_category_distribution()
        
        # 5.   ( )
        visualizer.show_sample_data(doc_type='law', limit=1)
        visualizer.show_sample_data(doc_type='criteria_resolution', limit=1)
        visualizer.show_sample_data(doc_type='mediation_case', limit=1)
        visualizer.show_sample_data(doc_type='counsel_case', limit=1)
        
        # 6.  
        visualizer.validate_data()
        
        #  
        visualizer.print_header(" ")
        print("\n    .")
        print("      .\n")
        
    finally:
        visualizer.close()

if __name__ == '__main__':
    main()
