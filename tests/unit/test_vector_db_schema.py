#!/usr/bin/env python3
"""
Vector DB   

:
1.    (IVFFlat)
2.    
3.     
4. JSONB    
5.  

 :
-    < 500ms (top_k=10)
-   100%
-   10     < 20%
"""

import psycopg2
import os
import time
import json
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Tuple
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'ddoksori'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'postgres')
}

class VectorDBSchemaTest:
    """Vector DB   """
    
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
    
    def get_random_embedding(self) -> List[float]:
        """    ()"""
        self.connect()
        cur = self.conn.cursor()
        cur.execute("""
            SELECT embedding 
            FROM chunks 
            WHERE embedding IS NOT NULL AND drop = FALSE 
            ORDER BY RANDOM() 
            LIMIT 1
        """)
        result = cur.fetchone()
        cur.close()
        return result[0] if result else None
    
    def test_vector_search_performance(self, top_k: int = 10, iterations: int = 10) -> Dict:
        """
         1:    
        """
        print("\n===  1:    ===")
        
        embedding = self.get_random_embedding()
        if not embedding:
            return {"status": "error", "message": "No embeddings found in database"}
        
        self.connect()
        cur = self.conn.cursor()
        
        query_times = []
        
        for i in range(iterations):
            start_time = time.time()
            
            cur.execute("""
                SELECT 
                    c.chunk_id,
                    c.content,
                    d.doc_type,
                    1 - (c.embedding <=> %s::vector) AS similarity
                FROM chunks c
                JOIN documents d ON c.doc_id = d.doc_id
                WHERE c.drop = FALSE AND c.embedding IS NOT NULL
                ORDER BY c.embedding <=> %s::vector
                LIMIT %s
            """, (embedding, embedding, top_k))
            
            results = cur.fetchall()
            elapsed = (time.time() - start_time) * 1000  # ms
            query_times.append(elapsed)
            
            if i == 0:
                print(f"     : {len(results)} ")
        
        cur.close()
        
        avg_time = statistics.mean(query_times)
        median_time = statistics.median(query_times)
        min_time = min(query_times)
        max_time = max(query_times)
        
        passed = avg_time < 500  # 500ms 
        
        result = {
            "test_name": "Vector Search Performance",
            "status": "passed" if passed else "failed",
            "avg_time_ms": round(avg_time, 2),
            "median_time_ms": round(median_time, 2),
            "min_time_ms": round(min_time, 2),
            "max_time_ms": round(max_time, 2),
            "threshold_ms": 500,
            "iterations": iterations,
            "top_k": top_k
        }
        
        print(f"   : {avg_time:.2f}ms")
        print(f"  : {median_time:.2f}ms")
        print(f"  /: {min_time:.2f}ms / {max_time:.2f}ms")
        print(f"  : {' PASSED' if passed else ' FAILED'}")
        
        self.test_results.append(result)
        return result
    
    def test_metadata_filtering(self) -> Dict:
        """
         2:     
        """
        print("\n===  2:   ===")
        
        embedding = self.get_random_embedding()
        if not embedding:
            return {"status": "error", "message": "No embeddings found"}
        
        self.connect()
        cur = self.conn.cursor()
        
        #  : doc_type 
        test_cases = [
            {
                "name": "doc_type  (law)",
                "filter": "d.doc_type = 'law'",
                "expected_type": "law"
            },
            {
                "name": "doc_type  (mediation_case)",
                "filter": "d.doc_type = 'mediation_case'",
                "expected_type": "mediation_case"
            },
            {
                "name": "source_org  (KCA)",
                "filter": "d.source_org = 'KCA'",
                "expected_org": "KCA"
            }
        ]
        
        filter_results = []
        
        for tc in test_cases:
            start_time = time.time()
            
            cur.execute(f"""
                SELECT 
                    c.chunk_id,
                    d.doc_type,
                    d.source_org,
                    1 - (c.embedding <=> %s::vector) AS similarity
                FROM chunks c
                JOIN documents d ON c.doc_id = d.doc_id
                WHERE c.drop = FALSE 
                    AND c.embedding IS NOT NULL
                    AND {tc['filter']}
                ORDER BY c.embedding <=> %s::vector
                LIMIT 10
            """, (embedding, embedding))
            
            results = cur.fetchall()
            elapsed = (time.time() - start_time) * 1000
            
            #  
            if 'expected_type' in tc:
                correct = all(row[1] == tc['expected_type'] for row in results)
            elif 'expected_org' in tc:
                correct = all(row[2] == tc['expected_org'] for row in results)
            else:
                correct = True
            
            filter_results.append({
                "test_case": tc['name'],
                "passed": correct,
                "time_ms": round(elapsed, 2),
                "results_count": len(results)
            })
            
            print(f"  {tc['name']}: {'' if correct else ''} ({len(results)}, {elapsed:.2f}ms)")
        
        cur.close()
        
        all_passed = all(r['passed'] for r in filter_results)
        avg_time = statistics.mean([r['time_ms'] for r in filter_results])
        
        result = {
            "test_name": "Metadata Filtering",
            "status": "passed" if all_passed else "failed",
            "avg_time_ms": round(avg_time, 2),
            "accuracy": "100%" if all_passed else "< 100%",
            "test_cases": filter_results
        }
        
        print(f"   : {' PASSED' if all_passed else ' FAILED'}")
        
        self.test_results.append(result)
        return result
    
    def test_chunk_relations(self) -> Dict:
        """
         3:     ( )
        """
        print("\n===  3:    ( ) ===")
        
        self.connect()
        cur = self.conn.cursor()
        
        #   
        cur.execute("""
            SELECT chunk_id, doc_id, chunk_index
            FROM chunks
            WHERE drop = FALSE
            ORDER BY RANDOM()
            LIMIT 1
        """)
        
        target_chunk = cur.fetchone()
        if not target_chunk:
            return {"status": "error", "message": "No chunks found"}
        
        chunk_id, doc_id, chunk_index = target_chunk
        
        # get_chunk_with_context  
        start_time = time.time()
        
        cur.execute("""
            SELECT * FROM get_chunk_with_context(%s, %s)
        """, (chunk_id, 2))  # window_size=2
        
        results = cur.fetchall()
        elapsed = (time.time() - start_time) * 1000
        
        cur.close()
        
        passed = elapsed < 100  # 100ms 
        
        result = {
            "test_name": "Chunk Relations (Context Window)",
            "status": "passed" if passed else "failed",
            "time_ms": round(elapsed, 2),
            "window_size": 2,
            "chunks_returned": len(results),
            "threshold_ms": 100
        }
        
        print(f"   : {chunk_id}")
        print(f"   : {len(results)}")
        print(f"   : {elapsed:.2f}ms")
        print(f"  : {' PASSED' if passed else ' FAILED'}")
        
        self.test_results.append(result)
        return result
    
    def test_jsonb_query(self) -> Dict:
        """
         4: JSONB   
        """
        print("\n===  4: JSONB   ===")
        
        self.connect()
        cur = self.conn.cursor()
        
        # JSONB   (decision_date )
        start_time = time.time()
        
        cur.execute("""
            SELECT 
                d.doc_id,
                d.doc_type,
                d.metadata->>'decision_date' AS decision_date,
                COUNT(c.chunk_id) AS chunk_count
            FROM documents d
            LEFT JOIN chunks c ON d.doc_id = c.doc_id AND c.drop = FALSE
            WHERE d.metadata ? 'decision_date'
            GROUP BY d.doc_id, d.doc_type, d.metadata->>'decision_date'
            LIMIT 100
        """)
        
        results = cur.fetchall()
        elapsed = (time.time() - start_time) * 1000
        
        cur.close()
        
        passed = elapsed < 200  # 200ms 
        
        result = {
            "test_name": "JSONB Metadata Query",
            "status": "passed" if passed else "failed",
            "time_ms": round(elapsed, 2),
            "results_count": len(results),
            "threshold_ms": 200
        }
        
        print(f"   : {len(results)} ")
        print(f"   : {elapsed:.2f}ms")
        print(f"  : {' PASSED' if passed else ' FAILED'}")
        
        self.test_results.append(result)
        return result
    
    def test_concurrent_queries(self, num_threads: int = 10) -> Dict:
        """
         5:   (  )
        """
        print(f"\n===  5:   ({num_threads} ) ===")
        
        #    
        print("    ...")
        single_times = []
        for _ in range(10):
            result = self.test_single_query()
            if result:
                single_times.append(result)
        
        single_avg = statistics.mean(single_times)
        
        #   
        print(f"   {num_threads}  ...")
        concurrent_times = []
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(self.test_single_query) for _ in range(num_threads)]
            
            for future in as_completed(futures):
                result = future.result()
                if result:
                    concurrent_times.append(result)
        
        concurrent_avg = statistics.mean(concurrent_times)
        
        #   
        degradation = ((concurrent_avg - single_avg) / single_avg) * 100
        passed = degradation < 20  # 20% 
        
        result = {
            "test_name": "Concurrent Queries",
            "status": "passed" if passed else "failed",
            "single_query_avg_ms": round(single_avg, 2),
            "concurrent_query_avg_ms": round(concurrent_avg, 2),
            "degradation_percent": round(degradation, 2),
            "threshold_percent": 20,
            "num_threads": num_threads
        }
        
        print(f"    : {single_avg:.2f}ms")
        print(f"    : {concurrent_avg:.2f}ms")
        print(f"   : {degradation:.2f}%")
        print(f"  : {' PASSED' if passed else ' FAILED'}")
        
        self.test_results.append(result)
        return result
    
    def test_single_query(self) -> float:
        """   ( )"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            
            #   
            cur.execute("""
                SELECT embedding 
                FROM chunks 
                WHERE embedding IS NOT NULL AND drop = FALSE 
                ORDER BY RANDOM() 
                LIMIT 1
            """)
            embedding = cur.fetchone()[0]
            
            #   
            start_time = time.time()
            
            cur.execute("""
                SELECT c.chunk_id, 1 - (c.embedding <=> %s::vector) AS similarity
                FROM chunks c
                WHERE c.drop = FALSE AND c.embedding IS NOT NULL
                ORDER BY c.embedding <=> %s::vector
                LIMIT 10
            """, (embedding, embedding))
            
            cur.fetchall()
            elapsed = (time.time() - start_time) * 1000
            
            cur.close()
            conn.close()
            
            return elapsed
            
        except Exception as e:
            print(f"    : {e}")
            return None
    
    def test_index_statistics(self) -> Dict:
        """
         :    
        """
        print("\n=== :   ===")
        
        self.connect()
        cur = self.conn.cursor()
        
        #   
        cur.execute("""
            SELECT
                schemaname,
                tablename,
                indexname,
                pg_size_pretty(pg_relation_size(indexname::regclass)) AS index_size
            FROM pg_indexes
            WHERE schemaname = 'public'
                AND tablename IN ('chunks', 'documents')
            ORDER BY tablename, indexname
        """)
        
        indexes = cur.fetchall()
        
        #   
        cur.execute("""
            SELECT
                tablename,
                pg_size_pretty(pg_total_relation_size(tablename::regclass)) AS total_size,
                pg_size_pretty(pg_relation_size(tablename::regclass)) AS table_size
            FROM pg_tables
            WHERE schemaname = 'public'
                AND tablename IN ('chunks', 'documents', 'chunk_relations')
            ORDER BY tablename
        """)
        
        tables = cur.fetchall()
        
        cur.close()
        
        print("  :")
        for idx in indexes:
            print(f"    {idx[2]}: {idx[3]}")
        
        print("\n  :")
        for tbl in tables:
            print(f"    {tbl[0]}: {tbl[1]} (: {tbl[2]})")
        
        result = {
            "test_name": "Index Statistics",
            "indexes": [{"name": idx[2], "size": idx[3]} for idx in indexes],
            "tables": [{"name": tbl[0], "total_size": tbl[1], "table_size": tbl[2]} for tbl in tables]
        }
        
        self.test_results.append(result)
        return result
    
    def run_all_tests(self) -> Dict:
        """  """
        print("=" * 80)
        print("Vector DB    ")
        print("=" * 80)
        
        try:
            #  
            self.test_vector_search_performance()
            self.test_metadata_filtering()
            self.test_chunk_relations()
            self.test_jsonb_query()
            self.test_concurrent_queries()
            self.test_index_statistics()
            
            #  
            passed_count = sum(1 for r in self.test_results if r.get('status') == 'passed')
            total_count = sum(1 for r in self.test_results if 'status' in r)
            
            summary = {
                "total_tests": total_count,
                "passed": passed_count,
                "failed": total_count - passed_count,
                "pass_rate": round((passed_count / total_count) * 100, 2) if total_count > 0 else 0,
                "tests": self.test_results
            }
            
            print("\n" + "=" * 80)
            print("  ")
            print("=" * 80)
            print(f" : {total_count}")
            print(f": {passed_count}")
            print(f": {total_count - passed_count}")
            print(f": {summary['pass_rate']}%")
            
            return summary
            
        except Exception as e:
            print(f"\n   : {e}")
            return {"status": "error", "message": str(e)}
        
        finally:
            self.close()


if __name__ == "__main__":
    #  
    tester = VectorDBSchemaTest(DB_CONFIG)
    results = tester.run_all_tests()
    
    #  
    output_file = "/tmp/vector_db_test_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n {output_file} .")
